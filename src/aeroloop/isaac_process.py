"""CPU-side guard around optional Isaac workers, including abnormal Kit shutdowns."""
from pathlib import Path
import os
import signal
import subprocess

from .contracts import ValidationError, load_json

ROOT = Path(__file__).resolve().parents[2]
KINDS = {"smoke": "isaac_physics_smoke", "train": "isaac_hover_training",
         "evaluate": "isaac_hover_evaluation", "flight": "isaac_quadrotor_flight"}


def _execute(command, timeout):
    process = subprocess.Popen(command, cwd=ROOT, start_new_session=os.name != "nt")
    try:
        code = process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # Windows venv launchers can create a second Python process. Stop that owned
        # process tree too, so a timed-out test does not leave a GPU worker running.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        raise
    if code:
        raise subprocess.CalledProcessError(code, command)


def run_worker(python, mode, output, options=(), timeout=3600):
    if mode not in KINDS or timeout <= 0:
        raise ValidationError("invalid Isaac worker request")
    output = Path(output).resolve()
    # An old successful result must never mask a failed new process.
    if output.exists():
        raise ValidationError("Isaac output directory already exists")
    script = ROOT / "tools" / ("isaac_smoke.py" if mode == "smoke" else "isaac_flight.py" if mode == "flight" else "isaac_train.py")
    command = [str(Path(python).resolve()), str(script)]
    if mode in ("train", "evaluate"):
        command.append(mode)
    command.extend(["--output", str(output), *options])
    _execute(command, timeout)
    # Kit can report exit 0 after a failed startup. Require the completed artifact too.
    result = load_json(output / "result.json")
    if result.get("schema_version") != 1 or result.get("kind") != KINDS[mode]:
        raise ValidationError("missing or invalid Isaac completion artifact")
    if result.get("backend") != "isaacsim_physx":
        raise ValidationError("Isaac worker used a different physics backend")
    if mode == "smoke" and result.get("passed") is not True:
        raise ValidationError("Isaac physics smoke failed")
    if mode == "flight":
        from .evidence import RUN_ID, read_run
        rows = result.get("results")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 15 or type(result.get("trials")) is not int or result["trials"] != len(rows):
            raise ValidationError("incomplete flight result")
        seen, passed = set(), 0
        for row in rows:
            identity = row.get("run_id") if isinstance(row, dict) else None
            if not isinstance(identity, str) or not RUN_ID.fullmatch(identity) or not identity.startswith("isaac-") or identity in seen:
                raise ValidationError("invalid flight run identity")
            seen.add(identity)
            run = read_run(output / identity)
            manifest = run["manifest.json"]
            if manifest["run_id"] != identity or any(manifest[key] != row.get(key) for key in ("scenario", "seed", "status")) or run["metrics.json"] != row.get("metrics"):
                raise ValidationError("flight summary disagrees with recording")
            passed += manifest["status"] == "passed"
        if type(result.get("passed")) is not int or result["passed"] != passed:
            raise ValidationError("flight aggregate disagrees with outcomes")
    return result
