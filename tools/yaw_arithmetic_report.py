"""Recompute arithmetic comparisons without importing CUDA or Isaac."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.yaw_arithmetic import report
from aeroloop.simulation import encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Choose a new report output path.")
    result = report(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded(result))
    outcome = result["outcomes"]
    print(f"Controls: {outcome['controls_passed']}; signature: {outcome['fast_signature_supported']}; original refinement: {outcome['default_yaw_refinement_passed']}")
    return 0 if all(outcome[k] for k in ("controls_passed", "physics_diagnostics_passed", "default_yaw_refinement_passed")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
