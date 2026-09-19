"""Launch an isolated Isaac worker and require its completed result artifact."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aeroloop.isaac_process import run_worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("smoke", "train", "evaluate"))
    executable = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    parser.add_argument("--python", type=Path, default=ROOT / ".local/IsaacLab/.venv" / executable)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--training-run", type=Path)
    parser.add_argument("--split", choices=("validation", "held_out"), default="validation")
    parser.add_argument("--num-envs", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=300)
    args = parser.parse_args()
    options = []
    if args.mode == "train":
        options = ["--num-envs", str(args.num_envs), "--iterations", str(args.iterations)]
    elif args.mode == "evaluate":
        if args.training_run is None:
            parser.error("evaluate requires --training-run")
        options = ["--training-run", str(args.training_run.resolve()), "--split", args.split]
    try:
        result = run_worker(args.python, args.mode, args.output, options, args.timeout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Isaac worker did not complete: {type(exc).__name__}. Inspect the local log.", file=sys.stderr)
        return 1
    print(f"Completed {result['kind']}. See {args.output / 'result.json'}.")
    if args.mode == "evaluate" and not result["trained_meets_threshold"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
