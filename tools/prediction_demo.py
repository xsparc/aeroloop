"""Verify predictive flights and prepare a pinned, repeatable local 3D demo."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.prediction_study import study, export_demo
from aeroloop.simulation import encoded

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline",type=Path,nargs=5,required=True)
    parser.add_argument("--candidate",type=Path,nargs=5,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.report.exists():parser.error("Choose new report and demo output paths.")
    report,old,new=study(args.baseline,args.candidate)
    digest=export_demo(report,old,new,args.output)
    with args.report.open("xb") as stream:stream.write(encoded(report))
    print(f"Verified candidate missions: {report['candidate']['passed']}/15; all stress gates accepted: {report['accepted']}")
    print(f"Index SHA256: {digest}")
