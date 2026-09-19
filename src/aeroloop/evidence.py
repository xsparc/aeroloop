"""Fail-closed evidence contracts. Unknown metadata is never published."""
from datetime import datetime
import json
import math
from pathlib import Path
import re
from .contracts import ValidationError, finite, load_json
from .frames import vector
from .simulation import SCENARIOS, ROOT, encoded, metrics, sha256

FILES = {"manifest.json", "config.json", "samples.json", "events.json", "metrics.json"}
HASH = re.compile(r"[0-9a-f]{64}\Z")
RUN_ID = re.compile(r"cpu-(hover|position-step|lateral-force-pulse)-[0-9]{1,10}-[0-9a-f]{12}\Z")
MANIFEST_FIELDS = {"schema_version", "run_id", "kind", "fixture", "captured_at", "experiment", "model", "controller", "scenario", "seed", "source_commit", "source_dirty", "source_tree_sha256", "controller_binary_sha256", "config_sha256", "lock_sha256", "world_frame", "body_frame", "quaternion_order", "units", "status", "failure_reason"}
SAMPLE_FIELDS = {"time_s", "sequence", "position_m", "velocity_m_s", "quaternion_wxyz", "target_m", "rates_rad_s", "rate_setpoint_rad_s", "effort_normalized", "thrust_n", "external_force_n"}


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def keys(value, expected):
    require(isinstance(value, dict) and set(value) == set(expected), "unexpected or missing evidence fields")


def validate_manifest(m):
    keys(m, MANIFEST_FIELDS)
    require(type(m["schema_version"]) is int and m["schema_version"] == 1, "unsupported manifest version")
    require(isinstance(m["run_id"], str) and RUN_ID.fullmatch(m["run_id"]), "invalid run identifier")
    require(m["kind"] == "recorded_simulation" and m["fixture"] is False, "fixtures are not publishable evidence")
    for field, value in {"experiment": "cpu-rigid-body", "model": "ideal-body-wrench-v1", "controller": "rate-pid-v1", "world_frame": "ENU", "body_frame": "FLU", "quaternion_order": "wxyz", "units": "SI"}.items():
        require(m[field] == value, "unsupported evidence convention")
    require(m["scenario"] in SCENARIOS, "unsupported scenario")
    require(type(m["seed"]) is int and 0 <= m["seed"] <= 2**31-1, "invalid seed")
    require(m["run_id"].startswith(f"cpu-{m['scenario']}-{m['seed']}-"), "run identifier does not match scenario and seed")
    require(isinstance(m["source_commit"], str) and re.fullmatch(r"[0-9a-f]{40}", m["source_commit"]), "invalid source commit")
    require(type(m["source_dirty"]) is bool, "invalid source state")
    for field in ("source_tree_sha256", "controller_binary_sha256", "config_sha256", "lock_sha256"):
        require(isinstance(m[field], str) and HASH.fullmatch(m[field]), "invalid provenance hash")
    require(m["status"] in ("passed", "failed"), "incomplete run")
    require(m["failure_reason"] in (None, "model_bounds_exceeded", "hover_threshold", "recovery_threshold", "step_did_not_settle"), "invalid failure reason")
    require((m["status"] == "passed") == (m["failure_reason"] is None), "inconsistent outcome")
    require(isinstance(m["captured_at"], str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00", m["captured_at"]), "UTC timestamp required")
    try:
        datetime.fromisoformat(m["captured_at"])
    except ValueError as error:
        raise ValidationError("invalid capture timestamp") from error


def validate_config(c, m):
    keys(c, {"model", "initial_state", "dt_s", "duration_s", "scenario", "seed", "controller", "position_kp", "position_kd", "attitude_kp", "rate_gains"})
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
    require(sha256(encoded(c)) == m["config_sha256"], "configuration hash mismatch")
    require(isinstance(samples, list) and 2 <= len(samples) <= 120001, "invalid sample count")
    for i, sample in enumerate(samples):
        keys(sample, SAMPLE_FIELDS)
        require(type(sample["sequence"]) is int and sample["sequence"] == i, "missing or unordered samples")
        require(finite(sample["time_s"]) and abs(sample["time_s"] - i*c["dt_s"]) <= 1e-8, "invalid simulation timestamps")
        for name in SAMPLE_FIELDS - {"time_s", "sequence", "thrust_n", "quaternion_wxyz"}:
            vector(sample[name])
        q = vector(sample["quaternion_wxyz"], 4)
        require(abs(math.hypot(*q)-1.) <= 1e-6, "non-unit quaternion")
        require(finite(sample["thrust_n"]) and 0 <= sample["thrust_n"] <= c["model"]["max_thrust"], "invalid thrust")
        require(all(abs(v) <= 1 for v in sample["effort_normalized"]), "invalid normalized effort")
    expected_count = round(c["duration_s"]/c["dt_s"])+1
    require(len(samples) <= expected_count, "recording exceeds duration")
    require(m["status"] != "passed" or len(samples) == expected_count, "truncated successful recording")
    require(isinstance(events, list) and len(events) <= 100, "invalid event count")
    expected_events = []
    for t, kind in ([(10., "target_step"), (25., "target_step")] if m["scenario"] == "position-step" else [(15., "force_start"), (15.5, "force_end")] if m["scenario"] == "lateral-force-pulse" else []):
        if t <= samples[-1]["time_s"]:
            expected_events.append({"time_s": t, "type": kind})
    require(events == expected_events, "event sequence mismatch")
    recomputed = metrics(samples, m["scenario"])
    require(encoded(recomputed) == encoded(data["metrics.json"]), "metrics do not match full-resolution samples")
    if m["status"] == "passed":
        require(all(s["position_m"][2] > 0 and math.hypot(*s["position_m"]) <= 100 for s in samples), "successful run violates model bounds")
        if m["scenario"] == "hover":
            require(recomputed["position_rmse_m"] is not None and recomputed["position_rmse_m"] <= .25, "hover gate failed")
        elif m["scenario"] == "lateral-force-pulse":
            require(recomputed["recovery_time_s"] is not None and recomputed["recovery_time_s"] <= 5, "recovery gate failed")
        else:
            require(recomputed["step_response"]["settling_time_s"] is not None, "step gate failed")
    return data


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
        # Preserve both sides of discontinuities as well as event instants and endpoints.
        samples, events = run["samples.json"], run["events.json"]
        stride = max(1, round(.05 / run["config.json"]["dt_s"]))
        indices = set(range(0, len(samples), stride)) | {len(samples)-1}
        for event in events:
            i = round(event["time_s"] / run["config.json"]["dt_s"])
            indices.update(j for j in (i-1, i, i+1) if 0 <= j < len(samples))
        replay = {"schema_version": 1, "kind": "recorded_simulation", "run_id": run_id,
                  "samples": [{k: sample[k] for k in ("time_s", "position_m", "target_m", "quaternion_wxyz")}
                              for i, sample in enumerate(samples) if i in indices]}
        for name, value in {**run, "replay.json": replay}.items():
            payloads[f"{run_id}/{name}"] = encoded(value)
        entries.append({"run_id": run_id, "scenario": m["scenario"], "status": m["status"], "seed": m["seed"]})
    index = {"schema_version": 1, "kind": "recorded_simulation", "release_status": "research_preview", "isaac_validated": False,
             "runs": entries, "checksums": {name: sha256(value) for name, value in payloads.items()}}
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
