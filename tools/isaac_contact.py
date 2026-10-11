"""Run a three-second liftoff contact probe in the isolated Isaac environment."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))


def main():
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise SystemExit("Review NVIDIA terms and set OMNI_KIT_ACCEPT_EULA=YES.")
    from isaaclab.app import add_launcher_args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--physics-dt", type=float, choices=(.005, .0025, .00125), default=.005)
    parser.add_argument("--force-mode", choices=("per-iteration", "per-step"), default="per-iteration")
    parser.add_argument("--repeat", type=int, choices=(1, 2), default=1)
    add_launcher_args(parser)
    parser.set_defaults(headless=True, visualizer=["none"], device="cuda:0", livestream=0)
    args = parser.parse_args()
    if args.device != "cuda:0" or not args.headless or args.livestream != 0:
        parser.error("The contact probe requires headless cuda:0 without livestream.")
    args.kit_args += " --/telemetry/enableAnonymousData=false --/telemetry/enableNVDF=false --/telemetry/enableSentry=false --/telemetry/useOpenEndpoint=false"
    args.scenarios, args.seeds = ("ground-mission-wind",), (301,)
    args.monitor = args.realtime = False
    args.observation_profile = None
    args.contact_forces = args.contact_probe = True
    from aeroloop.isaac_flight import flight
    flight(args.output, args)


if __name__ == "__main__":
    main()
