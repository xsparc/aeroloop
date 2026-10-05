"""Isaac worker for recorded, rotor-actuated native flight control."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise SystemExit("Review NVIDIA's terms and set OMNI_KIT_ACCEPT_EULA=YES before running Isaac.")
    from isaaclab.app import add_launcher_args
    from aeroloop.simulation import SCENARIOS
    from aeroloop.wind import WIND_SCENARIOS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scenario", choices=(*SCENARIOS, *WIND_SCENARIOS, "ground-mission", "ground-mission-wind", "all", "turbulence"), default="all")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(5)))
    parser.add_argument("--physics-dt", type=float, choices=(.005, .0025, .00125), default=.005)
    from aeroloop.observation import ALL_PROFILES
    parser.add_argument("--observation-profile", choices=ALL_PROFILES)
    parser.add_argument("--predictive-feedback", action="store_true")
    parser.add_argument("--vertical-decay", action="store_true")
    parser.add_argument("--fresh-axis", choices=("vertical", "horizontal"))
    parser.add_argument("--channel-quality", choices=("ideal", "noise", "delay", "noise-delay"))
    parser.add_argument("--landing-guard", action="store_true")
    parser.add_argument("--monitor", action="store_true")
    parser.add_argument("--realtime", action="store_true")
    add_launcher_args(parser)
    parser.set_defaults(headless=True, visualizer=["none"], device="cuda:0", livestream=0)
    args = parser.parse_args()
    from aeroloop.outage_study import PROFILES as OUTAGE_PROFILES
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
    if args.observation_profile and (args.scenario != "ground-mission-wind" or args.physics_dt != .005):
        parser.error("Observation profiles require the 200 Hz turbulent contact flight mission.")
    if (args.physics_dt != .005 or args.monitor or args.realtime) and args.scenario != "ground-mission-wind":
        parser.error("Substeps, monitoring and pacing require ground-mission-wind.")
    if len(args.seeds) > 5 or len(set(args.seeds)) != len(args.seeds) or any(s < 0 or s > 2**31-1 for s in args.seeds):
        parser.error("Use one to five distinct nonnegative 32-bit seeds.")
    if args.device != "cuda:0" or not args.headless or args.livestream != 0:
        parser.error("The bounded flight worker requires headless cuda:0 with livestream disabled.")
    args.scenarios = SCENARIOS if args.scenario == "all" else WIND_SCENARIOS if args.scenario == "turbulence" else (args.scenario,)
    args.kit_args += " --/telemetry/enableAnonymousData=false --/telemetry/enableNVDF=false --/telemetry/enableSentry=false --/telemetry/useOpenEndpoint=false"
    from aeroloop.isaac_flight import flight
    flight(args.output, args)


if __name__ == "__main__":
    main()
