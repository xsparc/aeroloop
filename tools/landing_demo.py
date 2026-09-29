"""Reverify regression/unseen landing cohorts and export a pinned local demo."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.landing_study import study,export_demo
from aeroloop.simulation import encoded

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name,count in (("regression-baseline",4),("regression-candidate",4),("unseen-baseline",2),("unseen-candidate",2)):
        parser.add_argument("--"+name,type=Path,nargs=count,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.report.exists():parser.error("Choose new output paths.")
    report,documents=study(args.regression_baseline,args.regression_candidate,args.unseen_baseline,args.unseen_candidate)
    digest=export_demo(report,documents,args.output)
    with args.report.open("xb") as stream:stream.write(encoded(report))
    for c in report["cohorts"]:print(f"{c['id']}: {c['candidate']['passed']}/{c['candidate']['trials']} missions; stress acceptance {c['accepted']}")
    print(f"Index SHA256: {digest}")
