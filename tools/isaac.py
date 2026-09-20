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
    parser.add_argument("mode", choices=("smoke", "train", "evaluate", "flight"))
    executable = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    parser.add_argument("--python", type=Path, default=ROOT / ".local/IsaacLab/.venv" / executable)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--training-run", type=Path)
    parser.add_argument("--split", choices=("validation", "held_out"), default="validation")
    parser.add_argument("--num-envs", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--scenario", choices=("hover", "position-step", "lateral-force-pulse", "all"), default="all")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(5)))
    args = parser.parse_args()
    options = []
    if args.mode == "train":
        options = ["--num-envs", str(args.num_envs), "--iterations", str(args.iterations)]
    elif args.mode == "evaluate":
        if args.training_run is None:
            parser.error("evaluate requires --training-run")
        options = ["--training-run", str(args.training_run.resolve()), "--split", args.split]
    elif args.mode == "flight":
        if not 1 <= len(args.seeds) <= 5 or len(set(args.seeds)) != len(args.seeds) or any(seed < 0 or seed > 2**31-1 for seed in args.seeds):
            parser.error("Use one to five distinct nonnegative 32-bit seeds.")
        options = ["--scenario", args.scenario, "--seeds", *(str(seed) for seed in args.seeds)]
    try:
        result = run_worker(args.python, args.mode, args.output, options, args.timeout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Isaac worker did not complete: {type(exc).__name__}. Inspect the local log.", file=sys.stderr)
        return 1
    print(f"Completed {result['kind']}. See {args.output / 'result.json'}.")
    if args.mode == "flight":
        scenarios = ("hover", "position-step", "lateral-force-pulse") if args.scenario == "all" else (args.scenario,)
        if {(row["scenario"], row["seed"]) for row in result["results"]} != {(scenario, seed) for scenario in scenarios for seed in args.seeds}:
            print("Isaac flight did not retain the complete requested trial set.", file=sys.stderr)
            return 1
    if args.mode == "evaluate" and not result["trained_meets_threshold"]:
        return 2
    if args.mode == "flight" and result["passed"] != result["trials"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
