"""Verify the retained decay matrix and export the landing contact lab."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from aeroloop.decay_study import COHORTS, study
from aeroloop.contact_study import export_demo
from aeroloop.simulation import encoded


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for cohort in COHORTS:
        for mode in ('baseline', 'candidate'):
            p.add_argument('--'+cohort+'-'+mode, type=Path, nargs=2, required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--demo', type=Path, required=True)
    args = p.parse_args()
    if args.report.exists() or args.demo.exists():
        p.error('Output exists; choose new report and demo paths.')
    report, documents = study({c: {m: getattr(args, c+'_'+m) for m in ('baseline', 'candidate')} for c in COHORTS})
    result = export_demo(report, documents, args.demo)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(encoded(result))
    print('Verified retained landing diagnostics; index SHA-256:', result['demo_index_sha256'])


if __name__ == '__main__':
    main()
