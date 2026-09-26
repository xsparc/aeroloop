"""Revalidate the full nine-flight study and prepare its compact local explorer."""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from aeroloop.evaluation import export_evaluation
from aeroloop.simulation import encoded, sha256


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("studies", nargs=3, type=Path, help="200, 400 and 800 Hz result directories")
    parser.add_argument("--name", default="flight-evaluation", help="new local bundle name")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", args.name):
        parser.error("Use a short lowercase bundle name.")
    public = ROOT/"web/replay/public"
    output = public/args.name
    document = export_evaluation(args.studies, output)
    (public/"evaluation-config.json").write_bytes(encoded({
        "baseUrl": f"/{args.name}/", "indexSha256": sha256((output/"evaluation.json").read_bytes())
    }))
    print(f"Revalidated {document['study']['trials']} flights; {document['study']['passed']} passed. Prepared evaluation.html.")
