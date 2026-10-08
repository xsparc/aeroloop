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
from aeroloop.observation import ALL_PROFILES


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
    parser.add_argument("--observation-profile", choices=ALL_PROFILES)
    parser.add_argument("--predictive-feedback", action="store_true")
    parser.add_argument("--vertical-decay", action="store_true")
    parser.add_argument("--approach-gains", action="store_true")
    parser.add_argument("--fresh-axis", choices=("vertical", "horizontal"))
    parser.add_argument("--channel-quality", choices=("ideal", "noise", "delay", "noise-delay"))
    parser.add_argument("--landing-guard", action="store_true")
    parser.add_argument("--contact-forces", action="store_true")
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--realtime", action="store_true")
    args = parser.parse_args()
    if args.observation_profile and (args.scenario != "ground-mission-wind" or args.physics_dt != .005 or args.mode != "flight"):
        parser.error("Observation profiles require the 200 Hz turbulent contact flight mission.")
    from aeroloop.outage_study import PROFILES as OUTAGE_PROFILES
    if args.contact_forces and (args.scenario != "ground-mission-wind" or args.mode != "flight"):
        parser.error("Contact forces require turbulent ground flight.")
    if args.approach_gains and not args.vertical_decay:
        parser.error("Approach gains require --vertical-decay and its fixed horizontal quality.")
    if args.vertical_decay and (not args.predictive_feedback or args.channel_quality != "noise-delay"):
        parser.error("Vertical decay requires predictive feedback and noise-delay horizontal quality.")
    if args.channel_quality and args.fresh_axis != "horizontal":
        parser.error("Channel quality requires --fresh-axis horizontal.")
    if args.fresh_axis and (not args.predictive_feedback or args.landing_guard or args.observation_profile not in ("sample-hold", "hold-dropout-2000ms")):
        parser.error("Fresh-axis ablation requires predictive feedback, no landing guard, and no outage or two-second outages.")
    if args.landing_guard and not args.predictive_feedback:
        parser.error("Landing guard requires predictive feedback.")
    if args.predictive_feedback and args.observation_profile not in OUTAGE_PROFILES:
        parser.error("Predictive feedback requires a 50 Hz outage-study profile.")
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
        if args.observation_profile:
            options += ["--observation-profile", args.observation_profile]
        if args.predictive_feedback:
            options += ["--predictive-feedback"]
        if args.contact_forces:
            options += ["--contact-forces"]
        if args.approach_gains:
            options += ["--approach-gains"]
        if args.vertical_decay:
            options += ["--vertical-decay"]
        if args.fresh_axis:
            options += ["--fresh-axis", args.fresh_axis]
        if args.channel_quality:
            options += ["--channel-quality", args.channel_quality]
        if args.landing_guard:
            options += ["--landing-guard"]
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
        if any((config := load_json(args.output / row["run_id"] / "config.json"))["physics_options"].get("physics_dt_s", .005) != args.physics_dt
               or config.get("observation_model", {}).get("profile") != args.observation_profile
               or ("feedback_model" in config) != args.predictive_feedback
               or (config.get("feedback_model", {}).get("kind") == "vertical-disturbance-decay-v1") != args.vertical_decay
               or (config.get("trajectory_control", {}).get("kind") == "approach-gains-v1") != args.approach_gains
               or config.get("axis_feedback_model", {}).get("available_axes") != args.fresh_axis
               or config.get("axis_feedback_model", {}).get("quality") != args.channel_quality
               or ("landing_guard_model" in config) != args.landing_guard
               for row in result["results"]):
            if args.monitor:
                from aeroloop.live import finish_monitor
                finish_monitor(args.output, False)
            return 1
        if args.contact_forces:
            from aeroloop.contact_forces import read_capture
            try:
                for row in result["results"]:
                    read_capture(args.output, row["run_id"])
            except (OSError, ValueError, TypeError, KeyError):
                if args.monitor:
                    from aeroloop.live import finish_monitor
                    finish_monitor(args.output, False)
                print("Contact capture did not verify.", file=sys.stderr)
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
