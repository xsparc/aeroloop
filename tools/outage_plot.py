"""Plot full-rate truth separation and capture age, including outage windows."""
import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.outage_study import PROFILES, read_study, summarize


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studies", type=Path, nargs=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new figure file.")
    runs, clocks = read_study(args.studies)
    result = summarize(runs, clocks)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), sharex=True)
    for seed in range(3):
        reference = runs[("sample-hold", seed)]["samples.json"]
        for profile in PROFILES[1:]:
            samples = runs[(profile, seed)]["samples.json"]
            paired = list(zip(reference, samples))
            axes[0, seed].plot([s["time_s"] for _,s in paired],
                               [math.dist(a["position_m"], b["position_m"])*1000 for a,b in paired], label=profile)
            axes[1, seed].plot([s["time_s"] for s in samples], [s["observation"]["age_s"]*1000 for s in samples], label=profile)
        axes[0, seed].set_title(f"Wind seed {seed}")
        axes[0, seed].axhline(150, color="red", linestyle=":", label="peak bound" if seed == 0 else None)
        axes[0, seed].axhline(50, color="gray", linestyle=":", label="recovery band" if seed == 0 else None)
        axes[1, seed].set_xlabel("Simulation time (s)")
        for ax in axes[:, seed]:
            ax.grid(alpha=.25)
            for start in (18,40):
                ax.axvline(start,color="black",alpha=.4,linestyle="--")
    axes[0,0].set_ylabel("Truth separation from 50 Hz reference (mm)")
    axes[1,0].set_ylabel("Delivered capture age (ms)")
    axes[0,0].legend(fontsize=8)
    fig.suptitle(f"Measured PhysX outage duration study — all stress gates accepted: {result['accepted']}\nSynthetic timing only; ideal attitude/rates/contact; yaw refinement remains open", fontsize=12)
    fig.tight_layout()
    fig.savefig(args.output, dpi=160)
    print("Verified outage duration figure written.")
