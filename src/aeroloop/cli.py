"""Only implemented commands are exposed."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from .contracts import ValidationError, load_json, validate_lock
from .doctor import probe

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="aeroloop", description="Simulation-only flight-control laboratory")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="inspect capabilities without installing software")
    lock = commands.add_parser("check-lock", help="validate dependency compatibility metadata")
    lock.add_argument("path", nargs="?", type=Path, default=ROOT / "versions.lock.json")
    test = commands.add_parser("test", help="run Python unit and contract tests")
    test.add_argument("--suite", choices=["cpu"], default="cpu")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(probe(), indent=2))
        elif args.command == "check-lock":
            validate_lock(load_json(args.path))
            print("Dependency lock is structurally valid; compatibility is not implied.")
        elif args.command == "test":
            return subprocess.call([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT)
    except (OSError, ValueError) as error:
        print(f"aeroloop: {type(error).__name__}: input invalid or unavailable" if not isinstance(error, ValidationError)
              else f"aeroloop: {error}", file=sys.stderr)
        return 2
    return 0
