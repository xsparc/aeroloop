"""Reverify the four-profile capture timing and outage recovery study."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.simulation import encoded
from aeroloop.timing_study import report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studies", type=Path, nargs=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new report file.")
    result = report(args.studies)
    with args.output.open("xb") as stream:
        stream.write(encoded(result))
    print(f"Verified {result['trials']} flights; {result['passed']} mission passes; timing study accepted: {result['accepted']}")
    raise SystemExit(0 if result["accepted"] else 2)
