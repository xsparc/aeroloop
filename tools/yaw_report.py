"""Recompute the complete yaw diagnostic matrix, preserving numerical failures."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.yaw_audit import report
from aeroloop.simulation import encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs=6, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new report output path.")
    result = report(args.directories)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded(result))
    print(f"Yaw diagnostics: {result['passed']}/{result['trials']}; default refinement: {result['default_yaw_refinement_passed']}")
    return 0 if result["diagnostics_passed"] and result["default_yaw_refinement_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
