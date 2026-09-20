"""Deterministic scenarios record computed physics, including failed outcomes."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import uuid
from .contracts import ValidationError, finite
from .controller import RateController
from .physics import Model, State, advance, desired_wrench

SCENARIOS = ("hover", "position-step", "lateral-force-pulse")
ROOT = Path(__file__).resolve().parents[2]


def encoded(data):
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def metrics(samples, scenario):
    window = [s for s in samples if s["time_s"] >= 5.]
    error = lambda s: math.dist(s["position_m"], s["target_m"])
    rmse = math.sqrt(sum(error(s)**2 for s in window)/len(window)) if window else None
    recovery = None
    if scenario == "lateral-force-pulse":
        start = None
        for sample in samples:
            t = sample["time_s"]
            if t < 15.5:
                continue
            if error(sample) <= 0.30:
                if start is None:
                    start = t
                if t-start >= 2.0-1e-9:
                    recovery = start-15.5
                    break
            else:
                start = None
    step_metrics = None
    if scenario == "position-step":
        segment = [s for s in samples if 10 <= s["time_s"] < 25]
        t10 = next((s["time_s"] for s in segment if s["position_m"][1] >= .1), None)
        t90 = next((s["time_s"] for s in segment if s["position_m"][1] >= .9), None)
        start, settled = None, None
        for sample in segment:
            if error(sample) <= .02:
                start = sample["time_s"] if start is None else start
                if sample["time_s"]-start >= 2.-1e-9:
                    settled = start-10.
                    break
            else:
                start = None
        step_metrics = {"rise_time_s": None if t10 is None or t90 is None else t90-t10,
                        "settling_time_s": settled, "settling_reason": None if settled is not None else "did_not_settle",
                        "overshoot_m": max(0., max((s["position_m"][1]-1 for s in segment), default=0.))}
    result = {"position_rmse_m": rmse, "measurement_window_s": [5., samples[-1]["time_s"]],
            "peak_error_m": max(error(s) for s in samples), "recovery_time_s": recovery,
            "recovery_reason": None if recovery is not None else "not_applicable" if scenario != "lateral-force-pulse" else "did_not_settle",
            "step_response": step_metrics, "samples": len(samples)}
    from .wind import WIND_SCENARIOS, wind_metrics
    if scenario in WIND_SCENARIOS:
        result["turbulence"] = wind_metrics(samples)
    return result


def simulate(scenario="hover", seed=0, dt=0.005, duration=35.):
    if scenario not in SCENARIOS or type(seed) is not int or not 0 <= seed <= 2**31-1:
        raise ValidationError("invalid scenario or seed")
    if not finite(dt) or not 0.001 <= dt <= 0.02 or not finite(duration) or not 6 <= duration <= 120:
        raise ValidationError("invalid simulation duration or interval")
    if abs(duration / dt - round(duration / dt)) > 1e-7:
        raise ValidationError("duration must be a multiple of the interval")
    if abs(.5 / dt - round(.5 / dt)) > 1e-7:
        raise ValidationError("interval must divide scenario event boundaries")
    rng = random.Random(seed)
    state = State(position=(rng.uniform(-.05, .05), rng.uniform(-.05, .05), 1.5+rng.uniform(-.05, .05)))
    initial = asdict(state)
    model = Model()
    samples, events = [], []
    status, reason = "passed", None
    saturation = (0, 0, 0)
    with RateController() as controller:
        library_hash = sha256(controller.path.read_bytes())
        for step in range(round(duration / dt)+1):
            t = round(step*dt, 9)
            target = (0., 1., 1.5) if scenario == "position-step" and 10 <= t < 25 else (0., 0., 1.5)
            pulse = scenario == "lateral-force-pulse" and 15 <= t < 15.5
            force = (model.mass*.5, 0., 0.) if pulse else (0., 0., 0.)
            if scenario == "position-step" and t in (10., 25.):
                events.append({"time_s": t, "type": "target_step"})
            if scenario == "lateral-force-pulse" and t in (15., 15.5):
                events.append({"time_s": t, "type": "force_start" if t == 15. else "force_end"})
            thrust, rate_setpoint = desired_wrench(state, target, model)
            effort = controller.step(state.rates, rate_setpoint, state.acceleration, dt, saturation)
            samples.append({"time_s": t, "sequence": step, "position_m": state.position,
                            "velocity_m_s": state.velocity, "quaternion_wxyz": state.quaternion,
                            "target_m": target, "rates_rad_s": state.rates, "rate_setpoint_rad_s": rate_setpoint,
                            "effort_normalized": effort, "thrust_n": thrust, "external_force_n": force})
            if state.position[2] <= 0 or math.hypot(*state.position) > 100:
                status, reason = "failed", "model_bounds_exceeded"
                break
            if step < round(duration / dt):
                state = advance(state, model, thrust, effort, force, dt)
                saturation = tuple(1 if value >= 1 else 2 if value <= -1 else 0 for value in effort)
    measured = metrics(samples, scenario)
    if scenario == "hover" and (measured["position_rmse_m"] is None or measured["position_rmse_m"] > .25):
        status, reason = "failed", "hover_threshold"
    if scenario == "lateral-force-pulse" and (measured["recovery_time_s"] is None or measured["recovery_time_s"] > 5):
        status, reason = "failed", "recovery_threshold"
    if scenario == "position-step" and measured["step_response"]["settling_time_s"] is None:
        status, reason = "failed", "step_did_not_settle"
    config = {"model": asdict(model), "initial_state": initial, "dt_s": dt, "duration_s": duration,
              "scenario": scenario, "seed": seed, "controller": "rate-pid-v1",
              "position_kp": 2.5, "position_kd": 2.8, "attitude_kp": 5.0,
              "rate_gains": {"p": [.6]*3, "i": [.1]*3, "d": [.005]*3, "ff": [0.]*3, "integral_limit": [.3]*3}}
    return {"samples": samples, "events": events, "metrics": measured, "config": config,
            "status": status, "failure_reason": reason, "controller_binary_sha256": library_hash}


def record(result, output_root):
    experiment = result.get("experiment", "cpu-rigid-body")
    if experiment not in ("cpu-rigid-body", "isaac-quadrotor"):
        raise ValidationError("unsupported recording experiment")
    rotor_flight = experiment == "isaac-quadrotor"
    from .wind import WIND_SCENARIOS
    wind = result["config"]["scenario"] in WIND_SCENARIOS
    if wind and not rotor_flight:
        raise ValidationError("wind experiments require Isaac rotor physics")
    prefix = "isaac" if rotor_flight else "cpu"
    run_id = f"{prefix}-{result['config']['scenario']}-{result['config']['seed']}-{uuid.uuid4().hex[:12]}"
    directory = Path(output_root) / run_id
    directory.mkdir(parents=True, exist_ok=False)
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=ROOT, text=True).strip())
    # Hash all implementation inputs to retain provenance even for a dirty checkout.
    source_files = sorted([* (ROOT / "src/aeroloop").glob("*.py"), *(ROOT / "firmware/control_core").glob("*.*"), ROOT / "CMakeLists.txt"])
    source_digest = sha256(b"".join(path.relative_to(ROOT).as_posix().encode()+b"\0"+path.read_bytes()+b"\0" for path in source_files))
    manifest = {"schema_version": 3 if wind else 2 if rotor_flight else 1, "run_id": run_id, "kind": "recorded_simulation", "fixture": False,
                "captured_at": datetime.now(timezone.utc).isoformat(), "experiment": experiment,
                "model": "quadrotor-x-wind-v1" if wind else "quadrotor-x-v1" if rotor_flight else "ideal-body-wrench-v1", "controller": "rate-pid-v1", "scenario": result["config"]["scenario"],
                "seed": result["config"]["seed"], "source_commit": source_commit, "source_dirty": dirty,
                "source_tree_sha256": source_digest, "controller_binary_sha256": result["controller_binary_sha256"],
                "config_sha256": sha256(encoded(result["config"])), "lock_sha256": sha256((ROOT / "versions.lock.json").read_bytes()),
                "world_frame": "ENU", "body_frame": "FLU", "quaternion_order": "wxyz", "units": "SI",
                "status": result["status"], "failure_reason": result["failure_reason"]}
    files = {"manifest.json": manifest, **{f"{key}.json": result[key] for key in ("config", "samples", "events", "metrics")}}
    hashes = {}
    for name, data in files.items():
        content = encoded(data)
        (directory / name).write_bytes(content)
        hashes[name] = sha256(content)
    (directory / "checksums.json").write_bytes(encoded(hashes))
    return directory
