"""Reconstruct the frozen decay matrix and optionally export a local demo."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from aeroloop.decay_study import COHORTS,study,export_demo
from aeroloop.simulation import encoded


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for cohort in COHORTS:
        for mode in ('baseline','candidate'):p.add_argument('--'+cohort+'-'+mode,type=Path,nargs=2,required=True)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--demo',type=Path)
    args=p.parse_args()
    if args.report.exists():p.error('Report already exists; choose a new file.')
    report,documents=study({c:{m:getattr(args,c+'_'+m) for m in ('baseline','candidate')} for c in COHORTS})
    if args.demo:report['demo_index_sha256']=export_demo(report,documents,args.demo)
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_bytes(encoded(report))
    print('Verified vertical decay study; accepted:',report['accepted'])


if __name__=='__main__':main()
