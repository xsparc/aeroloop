"""Verify and export the complete twelve-run liftoff probe matrix."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.contact_probe import export
from aeroloop.simulation import encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export(args.sessions, args.output)
    except (OSError, ValueError, TypeError, KeyError):
        raise SystemExit("Contact probe export rejected: inspect the local capture inputs.")
    print(encoded(result).decode(), end="")


if __name__ == "__main__":
    main()
