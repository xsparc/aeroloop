"""Plot verified physics traces with Matplotlib from the optional Isaac environment."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.physics_audit import read_physics, reference, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs=6, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.suffix.lower() != ".png":
        parser.error("Choose a new PNG output path.")
    summary = report(args.directories)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
    colors = {"free-fall": "#0072B2", "tilted-thrust": "#009E73", "rotor-step": "#D55E00", "drag-coast": "#CC79A7"}
    for group in summary["integrations"]:
        diagnostic = group["force_mode"] == "per-step"
        style = "--" if diagnostic else "-"
        frequencies = [1/r["dt_s"] for r in group["timesteps"]]
        for item in group["refinement"]:
            if item["case"] == "yaw-torque":
                axes[0, 1].plot(frequencies, [e*1000 for e in item["errors"]], style+"o", label=group["force_mode"])
            else:
                label = item["case"]+(" (diagnostic)" if diagnostic else "")
                axes[0, 0].plot(frequencies, [e*1000 for e in item["errors"]], style+"o", color=colors[item["case"]], label=label)
        penetration = [next(r["metrics"]["max_penetration_m"] for r in t["results"] if r["case"] == "floor-drop") for t in group["timesteps"]]
        axes[1, 1].plot(frequencies, [e*1000 for e in penetration], style+"o", label=group["force_mode"])
    for directory in args.directories:
        result, traces = read_physics(directory)
        if result["configuration"]["solver"].get("external_forces_every_iteration", True):
            drop = traces["floor-drop"]
            axes[1, 0].plot([s["time_s"] for s in drop], [1000*(s["position_m"][2]-.05) for s in drop], label=f"{1/result['dt_s']:g} Hz")
    times = [.29+i*.0001 for i in range(701)]
    axes[1, 0].plot(times, [max(0., 1000*(reference("floor-drop", t).position[2]-.05)) for t in times], "k:", label="Ideal non-bouncing drop")
    axes[1, 0].axhline(0., color="#555555", linewidth=.8)
    axes[1, 0].set(xlim=(.30, .35), ylim=(-5, 60), xlabel="Time (s)", ylabel="COM height above resting height (mm)", title="Default solver: contact approach")
    axes[0, 0].set(title="Peak position error", xlabel="Physics frequency (Hz)", ylabel="Error (mm)", yscale="log")
    axes[0, 1].set(title="Yaw angle error", xlabel="Physics frequency (Hz)", ylabel="Peak error (mrad)")
    axes[1, 1].axhline(3., color="#555555", linestyle=":", label="3 mm acceptance limit")
    axes[1, 1].set(title="Drop penetration (no monotonicity requirement)", xlabel="Physics frequency (Hz)", ylabel="Maximum penetration (mm)")
    for ax in axes.flat:
        ax.grid(alpha=.25); ax.legend(fontsize=8, ncols=2 if ax is axes[0, 0] else 1)
    fig.suptitle(f"AeroLoop measured PhysX accuracy: {summary['passed']}/{summary['trials']} individual cases passed", fontsize=16)
    fig.supxlabel("Solid: default per-iteration forces. Dashed: deprecated per-step diagnostic. Numerical verification, not aircraft calibration.", fontsize=10)
    fig.savefig(args.output, dpi=160, metadata={"Software": "AeroLoop physics audit"})
    plt.close(fig)


if __name__ == "__main__":
    main()
