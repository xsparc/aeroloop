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
    parser.add_argument("--name", default="evidence", help="new local bundle name; never overwrites evidence")
    args = parser.parse_args()
    import re
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", args.name):
        parser.error("Use a short lowercase bundle name.")
    public = ROOT / "web/replay/public"
    output = public / args.name
    export_bundle(args.runs, output)
    (public / "demo-config.json").write_bytes(encoded({
        "baseUrl": f"/{args.name}/", "indexSha256": sha256((output / "index.json").read_bytes())
    }))
    print("Prepared measured physics replay. Enable the 3D view to inspect recorded attitude.")
