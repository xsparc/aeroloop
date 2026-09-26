"""Strict offline comparison of CUDA arithmetic controls and PhysX yaw traces."""
import hashlib
import math
from pathlib import Path
import re
import tomllib

from . import yaw_audit as yaw
from .contracts import finite, load_json
from .evidence import keys, require
from .frames import vector
from .simulation import ROOT, encoded, sha256

CASES = ("spin-slow", "spin-positive", "spin-negative")
METHODS = ("library_float32", "intrinsic_float32", "library_float64")
EXTENSIONS = ("omni.physx", "omni.physx.gpu", "omni.physx.tensors")
TOOLS = ("yaw_arithmetic.py", "yaw_arithmetic_report.py", "yaw_arithmetic_plot.py")
CONFIGURATION = {"duration_s": .5, "methods": list(METHODS), "fast_math": False,
                 "recurrence": "normalized-pure-yaw-delta-per-iteration-then-outer-compose",
                 "float32_control_limit_rad": 5e-6, "float64_control_limit_rad": 1e-10,
                 "signature_absolute_limit_rad": 5e-6, "signature_relative_limit": .1}


def matrix():
    return [(n, dt, case) for n in yaw.ITERATIONS for dt in yaw.TIMESTEPS for case in CASES]


def worker_name(n, dt):
    return f"physics-{n}-{round(1/dt)}"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tool_checksums():
    return {name: digest(ROOT/"tools"/name) for name in TOOLS}


def hash_value(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value), "invalid arithmetic checksum")


def version(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9][a-zA-Z0-9.+-]{0,31}", value), "invalid arithmetic version")


def installation(isaac_root):
    """Hash selected installed files only. No host path enters the result."""
    result = {}
    for name in EXTENSIONS:
        candidates = list((Path(isaac_root)/"extscache").glob(name+"-[0-9]*"))
        require(len(candidates) == 1, "expected one installed PhysX extension")
        folder = candidates[0]
        manifest = folder/"config/extension.toml"
        row = {"version": tomllib.loads(manifest.read_text(encoding="utf-8"))["package"]["version"],
               "manifest_sha256": digest(manifest), "binaries": {}}
        if name == "omni.physx.gpu":
            for stem in ("PhysXGpu_64", "PhysXDevice64"):
                files = [p for p in (folder/"bin"/(stem+".dll"), folder/"bin"/("lib"+stem+".so")) if p.is_file()]
                require(len(files) == 1, "expected one PhysX GPU binary")
                row["binaries"][files[0].name] = digest(files[0])
        result[name] = row
    validate_installation(result)
    return result


def validate_installation(value):
    keys(value, set(EXTENSIONS))
    for name, row in value.items():
        keys(row, {"version", "manifest_sha256", "binaries"})
        version(row["version"]); hash_value(row["manifest_sha256"])
        require(isinstance(row["binaries"], dict), "invalid binary fingerprints")
        if name == "omni.physx.gpu":
            require(set(row["binaries"]) in ({"PhysXGpu_64.dll", "PhysXDevice64.dll"},
                {"libPhysXGpu_64.so", "libPhysXDevice64.so"}), "unexpected GPU binary fingerprint")
        else:
            keys(row["binaries"], set())
        for value in row["binaries"].values(): hash_value(value)


def angles(samples):
    return [2*math.atan2(z if w >= 0 else -z, abs(w)) for w, z in samples]


def compare(case, dt, iterations, methods, physics):
    times = [i*dt for i in range(len(physics))]
    expected = [yaw.CASES[case][0]*t for t in times]
    measured = [yaw.yaw(s["quaternion_wxyz"]) for s in physics]
    peak = max(abs(a-b) for a,b in zip(measured, expected))
    metrics = {}
    for name in METHODS:
        values = angles(methods[name])
        metrics[name] = {"peak_reference_error_rad": max(abs(a-b) for a,b in zip(values, expected)),
                         "peak_physics_difference_rad": max(abs(a-b) for a,b in zip(values, measured)),
                         "final_signed_reference_error_rad": values[-1]-expected[-1]}
    controls = metrics[METHODS[0]]["peak_reference_error_rad"] <= 5e-6 and metrics[METHODS[2]]["peak_reference_error_rad"] <= 1e-10
    difference = metrics[METHODS[1]]["peak_physics_difference_rad"]
    return {"case": case, "dt_s": dt, "position_iterations": iterations, "samples": len(physics),
            "physics_peak_reference_error_rad": peak, "methods": metrics,
            "controls_passed": controls, "fast_signature_supported": difference <= 5e-6 and difference <= .1*peak}


def read_probe(path):
    result = load_json(path, limit=4*1024*1024)
    keys(result, {"schema_version", "kind", "trials"})
    require(type(result["schema_version"]) is int and result["schema_version"] == 1
            and result["kind"] == "measured_cuda_yaw_arithmetic", "invalid arithmetic trace identity")
    trials = result["trials"]
    require(isinstance(trials, list) and len(trials) == len(matrix()), "incomplete arithmetic matrix")
    for row, (n, dt, case) in zip(trials, matrix()):
        keys(row, {"case", "dt_s", "position_iterations", "methods"})
        require(row["case"] == case and type(row["position_iterations"]) is int
                and row["position_iterations"] == n and finite(row["dt_s"]) and row["dt_s"] == dt, "arithmetic matrix identity mismatch")
        keys(row["methods"], set(METHODS))
        for samples in row["methods"].values():
            require(isinstance(samples, list) and len(samples) == round(.5/dt)+1, "incomplete arithmetic trace")
            for q in samples:
                vector(q, 2)
                require(abs(math.hypot(*q)-1) <= 1e-5, "invalid arithmetic quaternion")
            require(samples[0] == [1., 0.], "arithmetic reset mismatch")
    return result


def outcomes(directory):
    directory = Path(directory)
    paths = [directory/worker_name(n, dt) for n in yaw.ITERATIONS for dt in yaw.TIMESTEPS]
    summary = yaw.report(paths)
    probe = read_probe(directory/"arithmetic.json")
    physics = {}
    for p in paths:
        worker, traces = yaw.read_yaw(p)
        require(p.name == worker_name(worker["configuration"]["position_iterations"], worker["dt_s"]), "mislabeled physics worker")
        physics[(worker["configuration"]["position_iterations"], worker["dt_s"])] = traces
    rows = [compare(row["case"], row["dt_s"], row["position_iterations"], row["methods"],
                    physics[(row["position_iterations"], row["dt_s"])][row["case"]]) for row in probe["trials"]]
    return {"comparisons": rows, "controls_passed": all(r["controls_passed"] for r in rows),
            "fast_signature_supported": all(r["fast_signature_supported"] for r in rows),
            "physics_diagnostics_passed": summary["diagnostics_passed"],
            "default_yaw_refinement_passed": summary["default_yaw_refinement_passed"]}, summary


def read_study(directory):
    directory = Path(directory)
    result = load_json(directory/"result.json", limit=256*1024)
    keys(result, {"schema_version", "kind", "backend", "provenance", "tool_checksums", "configuration", "installation",
                  "arithmetic_runtime", "physics_result_checksums", "arithmetic_sha256", "wall_time_s", "outcomes"})
    require(type(result["schema_version"]) is int and result["schema_version"] == 1
            and result["kind"] == "yaw_arithmetic_study" and result["backend"] == "cuda_arithmetic_vs_physx", "invalid arithmetic study identity")
    require(encoded(result["configuration"]) == encoded(CONFIGURATION), "changed arithmetic configuration")
    validate_installation(result["installation"])
    keys(result["tool_checksums"], set(TOOLS))
    for value in result["tool_checksums"].values(): hash_value(value)
    keys(result["arithmetic_runtime"], {"warp", "cuda_toolkit", "cuda_driver", "compute_capability"})
    for value in result["arithmetic_runtime"].values(): version(value)
    require(finite(result["wall_time_s"]) and result["wall_time_s"] > 0, "invalid study timing")
    keys(result["physics_result_checksums"], {worker_name(n,dt) for n in yaw.ITERATIONS for dt in yaw.TIMESTEPS})
    for name, expected in result["physics_result_checksums"].items():
        require(digest(directory/name/"result.json") == expected, "physics worker checksum mismatch")
    require(digest(directory/"arithmetic.json") == result["arithmetic_sha256"], "arithmetic checksum mismatch")
    measured, summary = outcomes(directory)
    require(encoded(result["provenance"]) == encoded(summary["provenance"]), "arithmetic and physics source differ")
    require(encoded(result["outcomes"]) == encoded(measured), "arithmetic metrics or outcome mismatch")
    return result, summary


def report(directory):
    study, physics = read_study(directory)
    return {**study, "kind": "yaw_arithmetic_summary", "physics_versions": physics["versions"],
            "physics_trials": physics["trials"], "physics_passed": physics["passed"],
            "arithmetic_comparisons": len(matrix()),
            "limitations": ["Arithmetic recurrence is a controlled experiment, not an attested vendor kernel",
                "Matching constant-spin signatures do not prove torque refinement or a validated solver fix",
                "Installation hashes identify selected files, not the loaded instruction path",
                "Original numerical gates and flight settings remain unchanged"]}
