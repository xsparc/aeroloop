"""Plot signed errors from verified measured yaw traces; never hides failed cases."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.yaw_audit import CASES, read_yaw, report, series


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
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), layout="constrained")
    colors = {.005: "#0072B2", .0025: "#D55E00", .00125: "#009E73"}
    for directory in args.directories:
        result, traces = read_yaw(directory)
        dt, count = result["dt_s"], result["configuration"]["position_iterations"]
        style = "-" if count == 4 else "--"
        for ax, case in zip(axes.flat, CASES):
            rows = series(case, traces[case], dt)
            ax.plot([r["time_s"] for r in rows], [1000*r["signed_yaw_error_rad"] for r in rows],
                    style, color=colors[dt], label=f"{1/dt:g} Hz / {count} iterations")
            ax.set(title=case, xlabel="Simulation time (s)", ylabel="Signed yaw error (mrad)")
        rows = series("torque-positive", traces["torque-positive"], dt)
        axes[1, 2].plot([r["time_s"] for r in rows], [1000*r["integrated_rate_residual_rad"] for r in rows],
                        style, color=colors[dt], label=f"{1/dt:g} Hz / {count} iterations")
    axes[1, 2].set(title="Positive torque: pose minus integrated rate", xlabel="Simulation time (s)", ylabel="Residual (mrad)")
    for ax in axes.flat:
        ax.axhline(0., color="#777777", linewidth=.6); ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(f"AeroLoop measured yaw diagnostics: {summary['passed']}/30 absolute checks; default refinement {summary['default_yaw_refinement_passed']}", fontsize=15)
    fig.supxlabel("Solid: existing 4 position iterations. Dashed: 1-iteration diagnostic. Measured orientation, not a controller or solver fix.", fontsize=11)
    fig.savefig(args.output, dpi=140, metadata={"Software": "AeroLoop yaw diagnostics"})
    plt.close(fig)


if __name__ == "__main__":
    main()
