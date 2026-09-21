"""Verify three physics timesteps in two force modes and emit a public audit."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.physics_audit import report
from aeroloop.simulation import encoded


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs=6, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = report(args.directories)
    with args.output.open("xb") as stream:
        stream.write(encoded(summary))
    print(f"Verified {summary['passed']}/{summary['trials']} physics cases; refinement accepted: {summary['accepted']}.")
    raise SystemExit(0 if summary["accepted"] else 2)
