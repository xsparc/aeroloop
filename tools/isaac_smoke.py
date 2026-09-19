"""Run using the separately installed, pinned Isaac environment."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    # Acceptance is a maintainer action. This tool never sets the acceptance flag.
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise SystemExit("Review NVIDIA's terms and set OMNI_KIT_ACCEPT_EULA=YES before running Isaac.")
    from isaaclab.app import add_launcher_args
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    add_launcher_args(parser)
    parser.set_defaults(headless=True, visualizer=["none"], device="cuda:0", livestream=0)
    args = parser.parse_args()
    args.kit_args += " --/telemetry/enableAnonymousData=false --/telemetry/enableNVDF=false --/telemetry/enableSentry=false --/telemetry/useOpenEndpoint=false"
    if args.device != "cuda:0" or not args.headless or args.livestream != 0:
        parser.error("This bounded smoke requires headless cuda:0 with livestream disabled.")
    from aeroloop.isaac_runtime import smoke
    smoke(args.output, args)


if __name__ == "__main__":
    main()
