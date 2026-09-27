"""Plot truth tracking and observation discrepancy from verified full-rate runs."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.observation_study import read_study, summarize
from aeroloop.observation import PROFILES
import math

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Output exists")
    runs, clocks = read_study(args.directories)
    result = summarize(runs, clocks)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 3, figsize=(14, 9), sharex=True, layout="constrained")
    for seed in range(3):
        for profile in PROFILES:
            samples = runs[(profile,seed)]["samples.json"]
            times = [s["time_s"] for s in samples]
            axes[0,seed].plot(times, [math.dist(s["position_m"],s["target_m"]) for s in samples], label=profile, lw=.9)
            axes[1,seed].plot(times, [math.dist(s["position_m"],s["observation"]["position_m"]) for s in samples], lw=.7)
            axes[2,seed].plot(times, [s["observation"]["age_s"]*1000 for s in samples], lw=1)
        axes[0,seed].set_title(f"Seed {seed}")
        axes[0,seed].axhline(1., ls="--", color="gray", lw=.7)
        axes[2,seed].set_xlabel("Simulation time (s)")
        for row in axes: row[seed].grid(alpha=.2)
    axes[0,0].set_ylabel("Truth tracking error (m)")
    axes[1,0].set_ylabel("Observation position discrepancy (m)")
    axes[2,0].set_ylabel("Observation age (ms)")
    axes[0,0].legend(fontsize=8)
    fig.suptitle(f"PhysX observation robustness: {result['passed']}/12 mission gates; paired bounds {'passed' if result['accepted'] else 'failed'}")
    fig.savefig(args.output, dpi=150)
