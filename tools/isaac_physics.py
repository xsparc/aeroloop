"""Run the bounded physics accuracy worker in the isolated Isaac environment."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))


def main():
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise SystemExit("Review NVIDIA's terms and set OMNI_KIT_ACCEPT_EULA=YES before running Isaac.")
    from isaaclab.app import add_launcher_args
    from aeroloop.physics_audit import TIMESTEPS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--physics-dt", type=float, choices=TIMESTEPS, default=.005)
    parser.add_argument("--force-mode", choices=("per-iteration", "per-step"), default="per-iteration")
    add_launcher_args(parser)
    parser.set_defaults(headless=True, visualizer=["none"], device="cuda:0", livestream=0)
    args = parser.parse_args()
    args.kit_args += " --/telemetry/enableAnonymousData=false --/telemetry/enableNVDF=false --/telemetry/enableSentry=false --/telemetry/useOpenEndpoint=false"
    if args.device != "cuda:0" or not args.headless or args.livestream != 0:
        parser.error("This bounded physics suite requires headless cuda:0 with livestream disabled.")
    from aeroloop.isaac_physics import run
    run(args.output, args)


if __name__ == "__main__":
    main()
