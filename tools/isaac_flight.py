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
    add_launcher_args(parser)
    parser.set_defaults(headless=True, visualizer=["none"], device="cuda:0", livestream=0)
    args = parser.parse_args()
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
