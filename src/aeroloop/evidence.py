"""Fail-closed evidence contracts. Unknown metadata is never published."""
from datetime import datetime
import json
import math
from pathlib import Path
import re
from .contracts import ValidationError, finite, load_json
from .frames import vector
from . import mission, wind_mission
from .simulation import SCENARIOS, ROOT, encoded, metrics, sha256
from .wind import WIND_SCENARIOS, WIND_EVENTS, WindModel, wind_outcome, flight_setpoint

FILES = {"manifest.json", "config.json", "samples.json", "events.json", "metrics.json"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"(?:cpu|isaac)-(hover|position-step|lateral-force-pulse|turbulence-hold|turbulence-attitude-only|ground-mission|ground-mission-wind)-[0-9]{1,10}-[0-9a-f]{12}\Z")
MANIFEST_FIELDS = {"schema_version", "run_id", "kind", "fixture", "captured_at", "experiment", "model", "controller", "scenario", "seed", "source_commit", "source_dirty", "source_tree_sha256", "controller_binary_sha256", "config_sha256", "lock_sha256", "world_frame", "body_frame", "quaternion_order", "units", "status", "failure_reason"}
SAMPLE_FIELDS = {"time_s", "sequence", "position_m", "velocity_m_s", "quaternion_wxyz", "target_m", "rates_rad_s", "rate_setpoint_rad_s", "effort_normalized", "thrust_n", "external_force_n"}
ROTOR_FIELDS = {"thrust_setpoint_n", "rotor_command_n", "rotor_thrust_n", "moment_nm", "allocation_scale"}
WIND_FIELDS = {"wind_velocity_m_s", "external_moment_nm"}
MISSION_FIELDS = {"mission_phase", "contact_normal_force_n", "support_clearance_m"}


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), "unexpected or missing evidence fields")


def validate_manifest(m):
    keys(m, MANIFEST_FIELDS)
    require(type(m["schema_version"]) is int and m["schema_version"] in (1, 2, 3, 4, 5), "unsupported manifest version")
    flight, wind, contact = m["schema_version"] >= 2, m["schema_version"] in (3, 5), m["schema_version"] in (4, 5)
    require(isinstance(m["run_id"], str) and RUN_ID.fullmatch(m["run_id"]), "invalid run identifier")
    require(m["kind"] == "recorded_simulation" and m["fixture"] is False, "fixtures are not publishable evidence")
    for field, value in {"experiment": "isaac-quadrotor" if flight else "cpu-rigid-body", "model": "quadrotor-x-contact-wind-v1" if contact and wind else "quadrotor-x-contact-v1" if contact else "quadrotor-x-wind-v1" if wind else "quadrotor-x-v1" if flight else "ideal-body-wrench-v1", "controller": "rate-pid-v1", "world_frame": "ENU", "body_frame": "FLU", "quaternion_order": "wxyz", "units": "SI"}.items():
        require(m[field] == value, "unsupported evidence convention")
    require(m["scenario"] in ((wind_mission.SCENARIO,) if contact and wind else (mission.SCENARIO,) if contact else WIND_SCENARIOS if wind else SCENARIOS), "unsupported scenario")
    require(type(m["seed"]) is int and 0 <= m["seed"] <= 2**31-1, "invalid seed")
    prefix = "isaac" if flight else "cpu"
    require(m["run_id"].startswith(f"{prefix}-{m['scenario']}-{m['seed']}-"), "run identifier does not match backend, scenario and seed")
    require(isinstance(m["source_commit"], str) and re.fullmatch(r"[0-9a-f]{40}", m["source_commit"]), "invalid source commit")
    require(type(m["source_dirty"]) is bool, "invalid source state")
    for field in ("source_tree_sha256", "controller_binary_sha256", "config_sha256", "lock_sha256"):
        require(isinstance(m[field], str) and HASH.fullmatch(m[field]), "invalid provenance hash")
    require(m["status"] in ("passed", "failed"), "incomplete run")
    require(m["failure_reason"] in (None, "model_bounds_exceeded", "wind_mission_threshold", "wind_mission_support_threshold") if contact and wind else m["failure_reason"] in (None, "model_bounds_exceeded", "mission_threshold", "mission_support_threshold") if contact else m["failure_reason"] in (None, "model_bounds_exceeded", "attitude_altitude_threshold", "turbulence_hold_threshold") if wind else m["failure_reason"] in (None, "model_bounds_exceeded", "hover_threshold", "recovery_threshold", "step_did_not_settle"), "invalid failure reason")
    require((m["status"] == "passed") == (m["failure_reason"] is None), "inconsistent outcome")
    require(isinstance(m["captured_at"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00", m["captured_at"]), "UTC timestamp required")
    try:
        datetime.fromisoformat(m["captured_at"])
    except ValueError as error:
        raise ValidationError("invalid capture timestamp") from error


def validate_config(c, m):
    flight, wind, contact = m["schema_version"] >= 2, m["schema_version"] in (3, 5), m["schema_version"] in (4, 5)
    keys(c, {"model", "initial_state", "dt_s", "duration_s", "scenario", "seed", "controller", "position_kp", "position_kd", "attitude_kp", "rate_gains"} | ({"actuator", "simulator_versions", "physics_options"} if flight else set()) | ({"wind", "trajectory_control" if contact else "horizontal_position_hold"} if wind else set()) | ({"mission"} if contact else set()))
    require(c["scenario"] == m["scenario"] and c["seed"] == m["seed"] and c["controller"] == m["controller"], "configuration mismatch")
    require(finite(c["dt_s"]) and .001 <= c["dt_s"] <= .02 and finite(c["duration_s"]) and 6 <= c["duration_s"] <= 120, "invalid timing")
    require(abs(.5/c["dt_s"]-round(.5/c["dt_s"])) < 1e-7, "unaligned event interval")
    require(abs(c["duration_s"]/c["dt_s"]-round(c["duration_s"]/c["dt_s"])) < 1e-7, "unaligned duration")
    keys(c["model"], {"mass", "inertia", "gravity", "max_thrust", "max_moment"})
    for name in ("mass", "gravity", "max_thrust"):
        require(finite(c["model"][name]) and c["model"][name] > 0, "invalid physical constant")
    for name in ("inertia", "max_moment"):
        require(all(v > 0 for v in vector(c["model"][name])), "invalid physical constant")
    keys(c["initial_state"], {"position", "velocity", "quaternion", "rates", "acceleration"})
    for name, value in c["initial_state"].items():
        vector(value, 4 if name == "quaternion" else 3)
    for name in ("position_kp", "position_kd", "attitude_kp"):
        require(finite(c[name]) and c[name] >= 0, "invalid controller gain")
    keys(c["rate_gains"], {"p", "i", "d", "ff", "integral_limit"})
    for value in c["rate_gains"].values():
        require(all(v >= 0 for v in vector(value)), "invalid rate gain")
    if flight:
        from dataclasses import asdict
        from .physics import Model
        from .rotors import RotorModel
        require(encoded(c["actuator"]) == encoded(asdict(RotorModel())), "unsupported rotor model")
        require(encoded(c["model"]) == encoded(asdict(Model())), "unsupported rotor body model")
        require(c["dt_s"] == .005 and c["duration_s"] == (mission.DURATION if contact else 35.), "unsupported rotor experiment timing")
        substepped = "substeps" in c["physics_options"]
        keys(c["physics_options"], {"gyroscopic_forces"} | ({"physics_dt_s", "substeps", "input_hold", "contact_force"} if substepped else set()))
        if substepped:
            options = c["physics_options"]
            require(wind and contact and type(options["substeps"]) is int and options["substeps"] in (2, 4)
                    and options["physics_dt_s"] == .005/options["substeps"]
                    and options["input_hold"] == "world-force-body-moment"
                    and options["contact_force"] == "interval-mean", "unsupported flight substeps")
        require(c["physics_options"]["gyroscopic_forces"] is True, "gyroscopic forces must be enabled")
        keys(c["simulator_versions"], {"isaacsim", "isaaclab", "torch"})
        for version in c["simulator_versions"].values():
            require(isinstance(version, str) and re.fullmatch(r"[0-9][a-zA-Z0-9.+-]{0,31}", version), "invalid simulator version")
        if contact:
            require(encoded(c["mission"]) == encoded(wind_mission.contact_configuration() if wind else mission.configuration()), "unsupported contact mission")
            require(encoded(c["initial_state"]) == encoded(asdict(mission.initial_state(c["seed"]))), "mission initial condition disagrees with seed")
        if wind or contact:
            require((c["position_kp"], c["position_kd"], c["attitude_kp"]) == (2.5, 2.8, 5.), "unsupported flight gains")
            require(c["rate_gains"] == {"p": [.6]*3, "i": [.1]*3, "d": [.005]*3, "ff": [0.]*3, "integral_limit": [.3]*3}, "unsupported rate gains")
        if wind and contact:
            require(encoded(c["wind"]) == encoded(asdict(wind_mission.wind_model())), "unsupported mission wind")
            require(encoded(c["trajectory_control"]) == encoded(wind_mission.control_configuration()), "unsupported trajectory controller")
        if wind and not contact:
            import random
            from .physics import State
            rng = random.Random(c["seed"])
            initial = State(position=(rng.uniform(-.05, .05), rng.uniform(-.05, .05), 1.5+rng.uniform(-.05, .05)))
            require(encoded(c["initial_state"]) == encoded(asdict(initial)), "wind initial condition disagrees with seed")
            require(encoded(c["wind"]) == encoded(asdict(WindModel())), "unsupported wind model")
            require(c["horizontal_position_hold"] is (m["scenario"] == "turbulence-hold"), "incorrect stabilization mode")


def validate_rotors(sample, config, previous):
    from .rotors import RotorModel
    model = RotorModel(**config["actuator"])
    request = sample["thrust_setpoint_n"]
    require(finite(request) and 0 <= request <= 20., "invalid thrust setpoint")
    require(all(abs(e) <= 1. for e in sample["effort_normalized"]), "invalid controller effort")
    moment = tuple(e*s for e, s in zip(sample["effort_normalized"], config["model"]["max_moment"]))
    commands, _, scale = model.allocate(request, moment)
    applied = model.advance(previous, commands, config["dt_s"])
    thrust, torque = model.wrench(applied)
    expected = {"rotor_command_n": commands, "rotor_thrust_n": applied, "moment_nm": torque}
    for name, values in expected.items():
        measured = vector(sample[name], len(values))
        require(all(abs(a-b) <= 1e-9 for a, b in zip(values, measured)), "rotor evidence disagrees with actuator model")
    require(finite(sample["allocation_scale"]) and abs(sample["allocation_scale"]-scale) <= 1e-9, "invalid allocation scale")
    require(abs(sample["thrust_n"]-thrust) <= 1e-9, "total thrust disagrees with rotors")
    return applied


def validate_wind_wrench(sample, expected_wind, model):
    force, moment = model.wrench(sample["velocity_m_s"], sample["quaternion_wxyz"], sample["rates_rad_s"], expected_wind)
    for name, values in {"wind_velocity_m_s": expected_wind, "external_force_n": force, "external_moment_nm": moment}.items():
        measured = vector(sample[name])
        require(all(abs(a-b) <= 1e-9 for a, b in zip(values, measured)), "wind evidence disagrees with physics inputs")


def validate_wind(sample, expected_wind, scenario):
    from .physics import State, Model
    validate_wind_wrench(sample, expected_wind, WindModel())
    require(sample["target_m"] == [0., 0., 1.5], "incorrect wind experiment target")
    state = State(tuple(sample["position_m"]), tuple(sample["velocity_m_s"]), tuple(sample["quaternion_wxyz"]), tuple(sample["rates_rad_s"]))
    thrust, rate = flight_setpoint(state, sample["target_m"], Model(), scenario)
    require(abs(thrust-sample["thrust_setpoint_n"]) <= 1e-9 and all(abs(a-b) <= 1e-9 for a, b in zip(rate, sample["rate_setpoint_rad_s"])), "control mode disagrees with recorded setpoints")


def validate_mission(sample, route, tracking=None, allocation_saturated=False):
    from .physics import State
    force = vector(sample["contact_normal_force_n"])
    require(-1e-6 <= force[2] <= 10000 and max(abs(v) for v in force[:2]) <= 1e-4, "invalid ground normal force")
    state = State(tuple(sample["position_m"]), tuple(sample["velocity_m_s"]), tuple(sample["quaternion_wxyz"]), tuple(sample["rates_rad_s"]))
    phase, target, armed, bottom = route.update(sample["time_s"], state, force)
    require(sample["mission_phase"] == phase and all(abs(a-b) <= 1e-9 for a, b in zip(vector(sample["target_m"]), target)), "mission phase or target mismatch")
    require(finite(sample["support_clearance_m"]) and abs(sample["support_clearance_m"]-bottom) <= 1e-9, "collider clearance mismatch")
    if tracking:
        thrust, rate, expected = tracking.step(sample["time_s"], state, target, armed, .005, allocation_saturated)
        for field, values in expected.items():
            require(all(abs(a-b) <= 1e-9 for a, b in zip(vector(sample[field]), values)), "trajectory feedback or feedforward mismatch")
    else:
        require(all(v == 0 for v in sample["external_force_n"]), "calm mission has external force")
        thrust, rate = mission.setpoint(state, target, armed)
    require(abs(sample["thrust_setpoint_n"]-thrust) <= 1e-9 and all(abs(a-b) <= 1e-9 for a, b in zip(rate, sample["rate_setpoint_rad_s"])), "mission control setpoint mismatch")
    require(armed or all(v == 0 for v in sample["effort_normalized"]), "disarmed mission commands control effort")


def read_run(directory):
    directory = Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "invalid run directory")
    for name in FILES | {"checksums.json"}:
        require((directory / name).is_file() and not (directory / name).is_symlink(), "missing or linked evidence file")
    checksums = load_json(directory / "checksums.json", 4096)
    keys(checksums, FILES)
    data = {}
    for name in sorted(FILES):
        require(isinstance(checksums[name], str) and HASH.fullmatch(checksums[name]), "invalid checksum")
        require((directory / name).stat().st_size <= 32*1024*1024, "evidence file too large")
        content = (directory / name).read_bytes()
        require(sha256(content) == checksums[name], "checksum mismatch")
        # Parse the same bytes that were hashed, avoiding a second read of mutable input.
        from .contracts import _pairs
        data[name] = json.loads(content, object_pairs_hook=_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValidationError("non-finite JSON")))
    m, c, samples, events = (data[k] for k in ("manifest.json", "config.json", "samples.json", "events.json"))
    validate_manifest(m)
    validate_config(c, m)
    flight, wind, contact = m["schema_version"] >= 2, m["schema_version"] in (3, 5), m["schema_version"] in (4, 5)
    route = mission.Mission() if contact else None
    tracking = wind_mission.TrackingController() if contact and wind else None
    motors = (0.,)*4 if contact else (c["model"]["mass"]*c["model"]["gravity"]/4,)*4
    require(sha256(encoded(c)) == m["config_sha256"], "configuration hash mismatch")
    require(isinstance(samples, list) and 2 <= len(samples) <= 120001, "invalid sample count")
    wind_model = wind_mission.wind_model() if contact and wind else WindModel()
    winds = iter(wind_model.velocities(c["seed"], c["dt_s"], len(samples))) if wind else None
    for i, sample in enumerate(samples):
        keys(sample, SAMPLE_FIELDS | (ROTOR_FIELDS if flight else set()) | (WIND_FIELDS if wind else set()) | (MISSION_FIELDS if contact else set()) | (wind_mission.CONTROL_FIELDS if tracking else set()))
        require(type(sample["sequence"]) is int and sample["sequence"] == i, "missing or unordered samples")
        require(finite(sample["time_s"]) and abs(sample["time_s"] - i*c["dt_s"]) <= 1e-8, "invalid simulation timestamps")
        for name in SAMPLE_FIELDS - {"time_s", "sequence", "thrust_n", "quaternion_wxyz"}:
            vector(sample[name])
        q = vector(sample["quaternion_wxyz"], 4)
        require(abs(math.hypot(*q)-1.) <= 1e-6, "non-unit quaternion")
        require(finite(sample["thrust_n"]) and 0 <= sample["thrust_n"] <= c["model"]["max_thrust"], "invalid thrust")
        require(all(abs(v) <= 1 for v in sample["effort_normalized"]), "invalid normalized effort")
        if flight:
            motors = validate_rotors(sample, c, motors)
        if tracking:
            validate_wind_wrench(sample, next(winds), wind_model)
        elif wind:
            validate_wind(sample, next(winds), m["scenario"])
        if contact:
            validate_mission(sample, route, tracking, i > 0 and samples[i-1]["allocation_scale"] < 1.-1e-12)
        if wind or contact:
            if i == 0:
                for key, initial_key in (("position_m", "position"), ("velocity_m_s", "velocity"), ("quaternion_wxyz", "quaternion"), ("rates_rad_s", "rates")):
                    require(all(abs(a-b) <= 1e-6 for a, b in zip(sample[key], c["initial_state"][initial_key])), "recorded initial state disagrees with seed")
    expected_count = round(c["duration_s"]/c["dt_s"])+1
    require(len(samples) <= expected_count, "recording exceeds duration")
    require(m["status"] != "passed" or len(samples) == expected_count, "truncated successful recording")
    require(isinstance(events, list) and len(events) <= 100, "invalid event count")
    expected_events = []
    for t, kind in (WIND_EVENTS if wind else [(10., "target_step"), (25., "target_step")] if m["scenario"] == "position-step" else [(15., "force_start"), (15.5, "force_end")] if m["scenario"] == "lateral-force-pulse" else []):
        if t <= samples[-1]["time_s"]:
            expected_events.append({"time_s": t, "type": kind})
    if contact:
        expected_events = wind_mission.events(route.events, samples[-1]["time_s"]) if tracking else route.events
    require(events == expected_events, "event sequence mismatch")
    recomputed = metrics(samples, m["scenario"])
    require(encoded(recomputed) == encoded(data["metrics.json"]), "metrics do not match full-resolution samples")
    if wind and not contact:
        reason = "model_bounds_exceeded" if any(s["position_m"][2] <= 0 or math.hypot(*s["position_m"]) > 100 for s in samples) else wind_outcome(recomputed, m["scenario"])
        require(m["failure_reason"] == reason, "wind outcome disagrees with measured gates")
    if contact:
        reason = "model_bounds_exceeded" if any(s["position_m"][2] <= 0 or math.hypot(*s["position_m"]) > 100 for s in samples) else wind_mission.outcome(recomputed) if tracking else mission.outcome(recomputed)
        require(m["failure_reason"] == reason, "mission outcome disagrees with measured gates")
    if m["status"] == "passed":
        require(all(s["position_m"][2] > 0 and math.hypot(*s["position_m"]) <= 100 for s in samples), "successful run violates model bounds")
        if m["scenario"] == "hover":
            require(recomputed["position_rmse_m"] is not None and recomputed["position_rmse_m"] <= .25, "hover gate failed")
        elif m["scenario"] == "lateral-force-pulse":
            require(recomputed["recovery_time_s"] is not None and recomputed["recovery_time_s"] <= 5, "recovery gate failed")
        elif m["scenario"] == "position-step":
            require(recomputed["step_response"]["settling_time_s"] is not None, "step gate failed")
    return data


def replay_document(run):
    """Event-preserving display samples, distinct from full-rate evaluation."""
    m = run["manifest.json"]
    run_id = m["run_id"]
    # Preserve both sides of discontinuities as well as event instants and endpoints.
    samples, events = run["samples.json"], run["events.json"]
    stride = max(1, round(.05 / run["config.json"]["dt_s"]))
    indices = set(range(0, len(samples), stride)) | {len(samples)-1}
    for event in events:
        i = round(event["time_s"] / run["config.json"]["dt_s"])
        indices.update(j for j in (i-1, i, i+1) if 0 <= j < len(samples))
    replay_fields = ("time_s", "position_m", "target_m", "quaternion_wxyz") + (("rotor_thrust_n",) if m["schema_version"] >= 2 else ()) + (("wind_velocity_m_s", "external_force_n", "external_moment_nm") if m["schema_version"] in (3, 5) else ()) + (("mission_phase", "contact_normal_force_n", "support_clearance_m") if m["schema_version"] in (4, 5) else ())
    replay = {"schema_version": m["schema_version"], "kind": "recorded_simulation", "run_id": run_id,
              "samples": [{k: sample[k] for k in replay_fields}
                          for i, sample in enumerate(samples) if i in indices]}
    return replay


def export_bundle(run_directories, output):
    require(1 <= len(run_directories) <= 30, "export requires 1 to 30 runs")
    require(sum((Path(directory) / name).stat().st_size for directory in run_directories for name in FILES) <= 128*1024*1024, "input batch exceeds size budget")
    data = [read_run(path) for path in run_directories]
    ids = [run["manifest.json"]["run_id"] for run in data]
    require(len(ids) == len(set(ids)), "duplicate run identifier")
    output = Path(output)
    require(not output.exists(), "output already exists; choose a new directory")
    payloads, entries = {}, []
    for run in data:
        m = run["manifest.json"]
        run_id = m["run_id"]
        replay = replay_document(run)
        for name, value in {**run, "replay.json": replay}.items():
            payloads[f"{run_id}/{name}"] = encoded(value)
        entries.append({"run_id": run_id, "scenario": m["scenario"], "status": m["status"], "seed": m["seed"]})
    index = {"schema_version": 1, "kind": "recorded_simulation", "release_status": "research_preview", "isaac_validated": False,
             "runs": entries, "checksums": {name: sha256(value) for name, value in payloads.items()}}
    if any(run["manifest.json"]["schema_version"] >= 2 for run in data):
        index["schema_version"] = max(run["manifest.json"]["schema_version"] for run in data)
        del index["isaac_validated"]
        index["learning_validated"] = False
    payloads["index.json"] = encoded(index)
    for name in ("index.html", "viewer.js", "viewer.css"):
        payloads[name] = (ROOT / "web" / name).read_bytes()
    require(sum(map(len, payloads.values())) <= 128*1024*1024, "bundle exceeds size budget")
    output.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return index
