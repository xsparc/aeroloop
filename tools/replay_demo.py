"""Prepare the standalone viewer with freshly validated, measured recordings."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aeroloop.evidence import export_bundle
from aeroloop.simulation import encoded, sha256


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path)
    args = parser.parse_args()
    public = ROOT / "web/replay/public"
    output = public / "evidence"
    export_bundle(args.runs, output)
    (public / "demo-config.json").write_bytes(encoded({
        "baseUrl": "/evidence/", "indexSha256": sha256((output / "index.json").read_bytes())
    }))
    print("Prepared validated viewer demo; CPU recordings only.")
