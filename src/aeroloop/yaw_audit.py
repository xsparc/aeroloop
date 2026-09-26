"""Independent references and verification for measured yaw diagnostics."""
from dataclasses import asdict
import math
from pathlib import Path
import re
import subprocess

from .contracts import finite, load_json
from .evidence import keys, require
from .frames import normalize, vector
from .physics import Model
from .physics_audit import TIMESTEPS, angle_error
from .simulation import ROOT, encoded, sha256

KIND = "isaac_yaw_diagnostics"
DURATION = .5
ITERATIONS = (1, 4)
CASES = {"spin-slow": (.05, 0.), "spin-positive": (.5, 0.), "spin-negative": (-.5, 0.),
         "torque-positive": (0., .04), "torque-negative": (0., -.04)}
FIELDS = {"time_s", "position_m", "direct_position_m", "velocity_m_s", "quaternion_wxyz",
          "direct_quaternion_wxyz", "repeat_quaternion_wxyz", "rates_rad_s", "direct_rates_rad_s",
          "force_flu_n", "torque_flu_nm"}


def configuration(iterations, *, legacy_body_rate=False):
    require(type(iterations) is int and iterations in ITERATIONS, "unsupported yaw solver iterations")
    return {"model": asdict(Model()), "duration_s": DURATION, "position_iterations": iterations,
            "velocity_iterations": 1, "solver": "TGS", "external_forces_every_iteration": True,
            "linear_damping": 0., "angular_damping": 0., "sleep_threshold": 0., "gyroscopic_forces": True,
            "gravity_enu_m_s2": [0., 0., -Model().gravity], "initial_position_m": [0., 0., 1.5],
            "sampling": "after-step-update-public-then-direct-then-repeat-host-copies",
            "force_timing": "sample-i-input-applied-over-next-interval",
            **({} if legacy_body_rate else {"public_rate_frame": "world"})}


def reference(case, time_s):
    rate, torque = CASES[case]
    acceleration = torque/.04
    return rate*time_s + .5*acceleration*time_s*time_s, rate+acceleration*time_s


def yaw(q):
    q = normalize(q)
    # Equivalent quaternion signs must produce the same signed small yaw.
    sign = -1 if q[0] < 0 else 1
    return 2*math.atan2(sign*q[3], sign*q[0])


def series(case, samples, dt):
    integrated, rows = 0., []
    for i, s in enumerate(samples):
        expected_angle, expected_rate = reference(case, s["time_s"])
        if i:
            integrated += .5*(samples[i-1]["rates_rad_s"][2]+s["rates_rad_s"][2])*dt
        actual = yaw(s["quaternion_wxyz"])
        rows.append({"time_s": s["time_s"], "signed_yaw_error_rad": actual-expected_angle,
                     "signed_rate_error_rad_s": s["rates_rad_s"][2]-expected_rate,
                     "integrated_rate_residual_rad": actual-integrated})
    return rows


def measurements(case, samples, dt):
    rows = series(case, samples, dt)
    result = {"samples": len(samples), "final_signed_yaw_error_rad": rows[-1]["signed_yaw_error_rad"],
              "final_integrated_rate_residual_rad": rows[-1]["integrated_rate_residual_rad"],
              "peak_yaw_error_rad": max(abs(r["signed_yaw_error_rad"]) for r in rows),
              "peak_rate_error_rad_s": max(math.dist(s["rates_rad_s"], (0., 0., reference(case, s["time_s"])[1])) for s in samples),
              "peak_rate_integral_residual_rad": max(abs(r["integrated_rate_residual_rad"]) for r in rows),
              "peak_position_drift_m": max(math.dist(s["position_m"], (0., 0., 1.5)) for s in samples),
              "peak_speed_m_s": max(math.hypot(*s["velocity_m_s"]) for s in samples),
              "peak_off_axis_quaternion": max(math.hypot(*s["quaternion_wxyz"][1:3]) for s in samples),
              "peak_quaternion_norm_error": max(abs(math.hypot(*s[k])-1) for s in samples
                                                for k in ("quaternion_wxyz", "direct_quaternion_wxyz", "repeat_quaternion_wxyz")),
              "peak_read_position_difference_m": max(math.dist(s["position_m"], s["direct_position_m"]) for s in samples),
              "peak_read_rate_difference_rad_s": max(math.dist(s["rates_rad_s"], s["direct_rates_rad_s"]) for s in samples)}
    for field, metric in (("direct_quaternion_wxyz", "peak_read_angle_difference_rad"),
                          ("repeat_quaternion_wxyz", "peak_repeat_angle_difference_rad")):
        result[metric] = max(angle_error(normalize(s["quaternion_wxyz"]), normalize(s[field])) for s in samples)
    return result


def passes(metrics):
    return (metrics["peak_yaw_error_rad"] <= .002 and metrics["peak_rate_error_rad_s"] <= .0005
            and metrics["peak_position_drift_m"] <= .0002 and metrics["peak_speed_m_s"] <= .001
            and metrics["peak_off_axis_quaternion"] <= 1e-7 and metrics["peak_quaternion_norm_error"] <= 1e-5
            and all(metrics[k] <= 1e-7 for k in ("peak_read_position_difference_m", "peak_read_rate_difference_rad_s",
                                                  "peak_read_angle_difference_rad", "peak_repeat_angle_difference_rad")))


def provenance():
    files = sorted([*(ROOT/"src/aeroloop").glob("*.py"), *(ROOT/"tools"/name for name in
                   ("isaac.py", "isaac_yaw.py", "yaw_report.py"))])
    return {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
            "source_tree_sha256": sha256(b"".join(p.relative_to(ROOT).as_posix().encode()+b"\0"+p.read_bytes()+b"\0" for p in files)),
            "lock_sha256": sha256((ROOT/"versions.lock.json").read_bytes())}


def read_yaw(directory):
    directory = Path(directory)
    result = load_json(directory/"result.json")
    keys(result, {"schema_version", "kind", "backend", "dt_s", "configuration", "provenance", "versions",
                  "wall_time_s", "checksums", "results", "passed", "trials"})
    require(type(result["schema_version"]) is int and result["schema_version"] == 1
            and result["kind"] == KIND and result["backend"] == "isaacsim_physx", "invalid yaw identity")
    dt = result["dt_s"]
    require(finite(dt) and dt in TIMESTEPS, "unsupported yaw timestep")
    # Preserve the initial development trace, which compared body and world rates.
    require(encoded(result["configuration"]) in [encoded(configuration(n, legacy_body_rate=legacy))
            for n in ITERATIONS for legacy in (False, True)], "invalid yaw configuration")
    p = result["provenance"]
    keys(p, {"source_commit", "source_dirty", "source_tree_sha256", "lock_sha256"})
    require(type(p["source_dirty"]) is bool and isinstance(p["source_commit"], str)
            and re.fullmatch(r"[a-f0-9]{40}", p["source_commit"]), "invalid yaw provenance")
    for field in ("source_tree_sha256", "lock_sha256"):
        require(isinstance(p[field], str) and re.fullmatch(r"[a-f0-9]{64}", p[field]), "invalid yaw source hash")
    keys(result["versions"], {"isaacsim", "isaaclab", "torch"})
    require(all(isinstance(v, str) and re.fullmatch(r"[0-9][a-zA-Z0-9.+-]{0,31}", v)
                for v in result["versions"].values()), "invalid yaw versions")
    require(finite(result["wall_time_s"]) and result["wall_time_s"] > 0, "invalid yaw wall timing")
    keys(result["checksums"], {case+".json" for case in CASES})
    rows, traces = [], {}
    for case, (initial_rate, torque) in CASES.items():
        path = directory/(case+".json")
        require(path.stat().st_size <= 2*1024*1024, "oversized yaw trace")
        require(sha256(path.read_bytes()) == result["checksums"][path.name], "yaw checksum mismatch")
        trace = load_json(path, limit=2*1024*1024)
        keys(trace, {"schema_version", "kind", "case", "dt_s", "samples"})
        require(type(trace["schema_version"]) is int and trace["schema_version"] == 1
                and trace["kind"] == "measured_yaw_trace" and trace["case"] == case and trace["dt_s"] == dt,
                "yaw trace identity mismatch")
        samples = trace["samples"]
        require(isinstance(samples, list) and len(samples) == round(DURATION/dt)+1, "incomplete yaw trace")
        for i, s in enumerate(samples):
            keys(s, FIELDS)
            require(finite(s["time_s"]) and abs(s["time_s"]-i*dt) <= 1e-9, "unordered yaw samples")
            for field in FIELDS-{"time_s"}:
                vector(s[field], 4 if "quaternion" in field else 3)
            for field in ("quaternion_wxyz", "direct_quaternion_wxyz", "repeat_quaternion_wxyz"):
                require(abs(math.hypot(*s[field])-1) <= .01, "invalid yaw quaternion")
            require(s["force_flu_n"] == [0., 0., Model().gravity] and s["torque_flu_nm"] == [0., 0., torque], "yaw input mismatch")
            if i == 0:
                require(math.dist(s["position_m"], (0., 0., 1.5)) <= 1e-6
                        and math.dist(s["rates_rad_s"], (0., 0., initial_rate)) <= 1e-6
                        and math.hypot(*s["velocity_m_s"]) <= 1e-6
                        and angle_error(normalize(s["quaternion_wxyz"]), (1., 0., 0., 0.)) <= 1e-6, "yaw reset mismatch")
        metrics = measurements(case, samples, dt)
        rows.append({"case": case, "metrics": metrics, "passed": passes(metrics)})
        traces[case] = samples
    require(encoded(result["results"]) == encoded(rows), "yaw measurements or outcome mismatch")
    require(type(result["trials"]) is int and result["trials"] == len(CASES) and type(result["passed"]) is int
            and result["passed"] == sum(r["passed"] for r in rows), "false yaw aggregate")
    return result, traces


def report(directories):
    require(len(directories) == 6, "yaw report requires six workers")
    runs = [read_yaw(p)[0] for p in directories]
    require(runs[0]["provenance"]["source_dirty"] is False, "yaw report requires clean source")
    require(all(r["configuration"].get("public_rate_frame") == "world" for r in runs), "final yaw report requires matched world-rate channels")
    require(all(r["provenance"] == runs[0]["provenance"] and r["versions"] == runs[0]["versions"] for r in runs), "yaw provenance differs")
    require({(r["dt_s"], r["configuration"]["position_iterations"]) for r in runs}
            == {(dt, n) for dt in TIMESTEPS for n in ITERATIONS}, "missing or duplicate yaw worker")
    groups = []
    for n in ITERATIONS:
        group = sorted((r for r in runs if r["configuration"]["position_iterations"] == n), key=lambda r: -r["dt_s"])
        errors = [next(row["metrics"]["peak_yaw_error_rad"] for row in r["results"] if row["case"] == "torque-positive") for r in group]
        groups.append({"position_iterations": n, "torque_positive_peak_yaw_errors_rad": errors,
                       "original_refinement_passed": all(b <= .65*a+.00002 for a, b in zip(errors, errors[1:])),
                       "workers": [{k: r[k] for k in ("dt_s", "wall_time_s", "checksums", "results")} for r in group]})
    return {"schema_version": 1, "kind": "isaac_yaw_diagnostics_summary", "backend": "isaacsim_physx",
            "provenance": runs[0]["provenance"], "versions": runs[0]["versions"], "trials": 30,
            "passed": sum(r["passed"] for r in runs), "diagnostics_passed": all(r["passed"] == 5 for r in runs),
            "default_yaw_refinement_passed": groups[1]["original_refinement_passed"], "groups": groups,
            "limitations": ["Read-channel agreement does not prove the exact GPU kernel root cause",
                            "One position iteration is diagnostic; flight settings are unchanged",
                            "Absolute diagnostic bounds do not replace decision 007 accuracy gates",
                            "Isolated pure yaw, not full-flight convergence or physical calibration"]}
