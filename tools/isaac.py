"""Launch an isolated Isaac worker and require its completed result artifact."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aeroloop.isaac_process import run_worker
from aeroloop.simulation import SCENARIOS
from aeroloop.wind import WIND_SCENARIOS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("smoke", "train", "evaluate", "flight", "physics", "yaw"))
    executable = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    parser.add_argument("--python", type=Path, default=ROOT / ".local/IsaacLab/.venv" / executable)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--training-run", type=Path)
    parser.add_argument("--split", choices=("validation", "held_out"), default="validation")
    parser.add_argument("--num-envs", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--scenario", choices=(*SCENARIOS, *WIND_SCENARIOS, "ground-mission", "ground-mission-wind", "all", "turbulence"), default="all")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(5)))
    parser.add_argument("--physics-dt", type=float, choices=(.005, .0025, .00125), default=.005)
    parser.add_argument("--force-mode", choices=("per-iteration", "per-step"), default="per-iteration")
    parser.add_argument("--solver-iterations", type=int, choices=(1, 4), default=4)
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--realtime", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new session directory.")
    if args.mode != "yaw" and args.solver_iterations != 4:
        parser.error("Solver iteration diagnostics require yaw mode.")
    if args.mode == "yaw" and args.force_mode != "per-iteration":
        parser.error("Yaw diagnostics retain default per-iteration forces.")
    if (args.monitor or args.realtime) and (args.mode != "flight" or args.scenario != "ground-mission-wind"):
        parser.error("Monitoring and pacing require flight --scenario ground-mission-wind.")
    options = []
    if args.mode == "physics":
        options = ["--physics-dt", str(args.physics_dt), "--force-mode", args.force_mode]
    if args.mode == "yaw":
        options = ["--physics-dt", str(args.physics_dt), "--solver-iterations", str(args.solver_iterations)]
    if args.mode == "train":
        options = ["--num-envs", str(args.num_envs), "--iterations", str(args.iterations)]
    elif args.mode == "evaluate":
        if args.training_run is None:
            parser.error("evaluate requires --training-run")
        options = ["--training-run", str(args.training_run.resolve()), "--split", args.split]
    elif args.mode == "flight":
        if not 1 <= len(args.seeds) <= 5 or len(set(args.seeds)) != len(args.seeds) or any(seed < 0 or seed > 2**31-1 for seed in args.seeds):
            parser.error("Use one to five distinct nonnegative 32-bit seeds.")
        if args.physics_dt != .005 and args.scenario != "ground-mission-wind":
            parser.error("Flight substeps require ground-mission-wind.")
        options = ["--scenario", args.scenario, "--seeds", *(str(seed) for seed in args.seeds), "--physics-dt", str(args.physics_dt)]
        options += (["--monitor"] if args.monitor else []) + (["--realtime"] if args.realtime else [])
    try:
        result = run_worker(args.python, args.mode, args.output, options, args.timeout)
    except (OSError, ValueError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        if args.monitor:
            from aeroloop.live import finish_monitor
            finish_monitor(args.output, False)
        print(f"Isaac worker did not complete: {type(exc).__name__}. Inspect the local log.", file=sys.stderr)
        return 1
    print(f"Completed {result['kind']}. See {args.output / 'result.json'}.")
    if args.mode == "flight":
        from aeroloop.contracts import load_json
        if any(load_json(args.output / row["run_id"] / "config.json")["physics_options"].get("physics_dt_s", .005) != args.physics_dt
               for row in result["results"]):
            if args.monitor:
                from aeroloop.live import finish_monitor
                finish_monitor(args.output, False)
            return 1
        scenarios = SCENARIOS if args.scenario == "all" else WIND_SCENARIOS if args.scenario == "turbulence" else (args.scenario,)
        if {(row["scenario"], row["seed"]) for row in result["results"]} != {(scenario, seed) for scenario in scenarios for seed in args.seeds}:
            print("Isaac flight did not retain the complete requested trial set.", file=sys.stderr)
            if args.monitor:
                from aeroloop.live import finish_monitor
                finish_monitor(args.output, False)
            return 1
        if args.monitor:
            from aeroloop.live import finish_monitor
            finish_monitor(args.output, result["passed"] == result["trials"])
    if args.mode == "evaluate" and not result["trained_meets_threshold"]:
        return 2
    if args.mode == "physics" and (result["dt_s"] != args.physics_dt or result["passed"] != result["trials"]
            or result["configuration"]["solver"].get("external_forces_every_iteration", True) != (args.force_mode == "per-iteration")):
        return 2
    if args.mode == "yaw" and (result["dt_s"] != args.physics_dt or result["passed"] != result["trials"]
            or result["configuration"]["position_iterations"] != args.solver_iterations):
        return 2
    if args.mode == "flight" and result["passed"] != result["trials"]:
        return 2
    if args.mode == "flight" and any(not pair["passed"] for pair in result.get("comparisons", [])):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
