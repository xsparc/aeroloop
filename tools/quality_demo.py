"""Verify horizontal noise/delay recordings and export the paired demo."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.channel_quality import QUALITIES
from aeroloop.quality_study import study, export_demo
from aeroloop.simulation import encoded

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("retained", *QUALITIES):
        parser.add_argument("--"+name, type=Path, nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists(): parser.error("Choose new output paths.")
    report, documents = study(args.retained, {q:getattr(args,q.replace("-","_")) for q in QUALITIES})
    digest = export_demo(report, documents, args.output)
    with args.report.open("xb") as stream: stream.write(encoded(report))
    for row in report["qualities"]:
        s = row["summary"]
        print(f"{row['quality']}: {s['passed']}/{s['trials']} missions; stress accepted {s['accepted']}")
    print(f"Index SHA256: {digest}")
