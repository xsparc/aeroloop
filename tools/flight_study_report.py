"""Validate a three-seed, three-frequency PhysX flight study."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.flight_study import report
from aeroloop.simulation import encoded

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.directories)
    with args.output.open("xb") as stream:
        stream.write(encoded(result))
    print(f"Flight checks: {result['passed']}/{result['trials']}; sensitivity accepted: {result['accepted']}")
    raise SystemExit(0 if result["accepted"] else 2)
