"""Reverify both axis choices and cohorts, then export a pinned local demo."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.axis_study import COHORTS, AXES, study, export_demo
from aeroloop.simulation import encoded

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for cohort, _ in COHORTS:
        for choice in ("baseline", *AXES):
            parser.add_argument(f"--{cohort}-{choice}", type=Path, nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists(): parser.error("Choose new output paths.")
    value = lambda c,a: getattr(args, f"{c}_{a}".replace("-", "_"))
    report, documents = study({c:value(c,"baseline") for c,_ in COHORTS}, {(c,a):value(c,a) for c,_ in COHORTS for a in AXES})
    digest = export_demo(report, documents, args.output)
    with args.report.open("xb") as stream: stream.write(encoded(report))
    for c in report["cohorts"]: print(f"{c['cohort']} {c['fresh_axis']}: {c['candidate']['passed']}/{c['candidate']['trials']} missions; stress accepted {c['accepted']}")
    print(f"Index SHA256: {digest}")
