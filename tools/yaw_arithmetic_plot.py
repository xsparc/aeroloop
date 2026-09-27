"""Plot verified arithmetic controls alongside measured constant-spin PhysX."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop import yaw_arithmetic as audit
from aeroloop import yaw_audit as yaw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.suffix.lower() != ".png": parser.error("Choose a new PNG output path.")
    study, _ = audit.read_study(args.directory)
    probe = audit.read_probe(args.directory/"arithmetic.json")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout="constrained")
    # Show both rates and signs under the existing four-iteration configuration.
    colors = {"physx": "#222222", "library_float32": "#0072B2", "intrinsic_float32": "#D55E00", "library_float64": "#009E73"}
    labels = {"physx": "Measured PhysX", "library_float32": "Library float32", "intrinsic_float32": "Fast intrinsic float32", "library_float64": "Library float64"}
    for column, case in enumerate(audit.CASES):
        for line, dt in enumerate((.005, .00125)):
            ax = axes[line, column]
            row = next(r for r in probe["trials"] if r["case"] == case and r["dt_s"] == dt and r["position_iterations"] == 4)
            _, traces = yaw.read_yaw(args.directory/audit.worker_name(4, dt))
            times = [s["time_s"] for s in traces[case]]
            expected = [yaw.CASES[case][0]*t for t in times]
            values = {"physx": [yaw.yaw(s["quaternion_wxyz"]) for s in traces[case]],
                      **{name: audit.angles(samples) for name, samples in row["methods"].items()}}
            for name, angles in values.items():
                ax.plot(times, [1000*(a-b) for a,b in zip(angles, expected)], color=colors[name],
                        linestyle="--" if name == "intrinsic_float32" else ":" if name == "library_float64" else "-", label=labels[name])
            ax.set(title=f"{case} / {1/dt:g} Hz", xlabel="Simulation time (s)", ylabel="Signed error (mrad)")
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Measured yaw and independent CUDA arithmetic controls", fontsize=16)
    fig.supxlabel(f"Four position iterations shown; all 18 comparisons verified. Fast signature supported: {study['outcomes']['fast_signature_supported']}. Original yaw refinement remains separate.", fontsize=10)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=140, metadata={"Software": "AeroLoop arithmetic study"})
    plt.close(fig)


if __name__ == "__main__":
    main()
