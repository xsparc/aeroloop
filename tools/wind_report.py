"""Verify a complete clean-revision turbulence suite and write an allowlisted summary."""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aeroloop.contracts import finite, load_json
from aeroloop.evidence import require
from aeroloop.isaac_process import validate_flight_result
from aeroloop.simulation import encoded, sha256
from aeroloop.wind import WIND_SCENARIOS


def report(directory):
    result = load_json(Path(directory) / "result.json")
    runs = validate_flight_result(directory, result)
    cases = {(r["manifest.json"]["scenario"], r["manifest.json"]["seed"]) for r in runs}
    require(cases == {(s, seed) for s in WIND_SCENARIOS for seed in range(5)}, "report requires both modes for seeds 0 through 4")
    require(all(r["manifest.json"]["source_dirty"] is False for r in runs), "report requires clean source revisions")
    provenance_fields = ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256")
    provenance = {k: runs[0]["manifest.json"][k] for k in provenance_fields}
    require(all(all(r["manifest.json"][k] == v for k, v in provenance.items()) for r in runs), "suite source provenance differs")
    require(finite(result.get("wall_time_s")) and result["wall_time_s"] > 0, "invalid wall time")
    entries = []
    for run in sorted(runs, key=lambda r: (r["manifest.json"]["scenario"], r["manifest.json"]["seed"])):
        manifest, samples = run["manifest.json"], run["samples.json"]
        entries.append({**{k: manifest[k] for k in ("run_id", "scenario", "seed", "status", "failure_reason", "config_sha256")},
            "metrics": run["metrics.json"],
            "wind_samples_sha256": sha256(encoded([s["wind_velocity_m_s"] for s in samples])),
            "peak_wind_speed_m_s": max(math.hypot(*s["wind_velocity_m_s"]) for s in samples),
            "peak_drag_force_n": max(math.hypot(*s["external_force_n"]) for s in samples),
            "peak_external_moment_nm": max(math.hypot(*s["external_moment_nm"]) for s in samples),
            "rotor_thrust_range_n": [min(min(s["rotor_thrust_n"]) for s in samples), max(max(s["rotor_thrust_n"]) for s in samples)],
            "allocation_saturated_samples": sum(s["allocation_scale"] < 1.-1e-12 for s in samples)})
    config = runs[0]["config.json"]
    return {"schema_version": 1, "kind": "isaac_turbulence_stabilization_summary", "backend": "isaacsim_physx",
        "source_dirty": False, **provenance, "versions": config["simulator_versions"],
        "model": config["model"], "actuator": config["actuator"], "wind": config["wind"], "physics_options": config["physics_options"],
        "dt_s": config["dt_s"], "duration_s": config["duration_s"], "wall_time_s": result["wall_time_s"],
        "trials": len(entries), "passed": sum(e["status"] == "passed" for e in entries),
        "comparisons": result["comparisons"], "results": entries,
        "interpretation": "Reference completion checks altitude and attitude; horizontal position hold is disabled. Comparison uses identical seeded wind velocity, not identical drag force.",
        "limitations": ["Illustrative temporal OU wind, not Dryden/Von Karman or measured weather",
                        "Perfect state and airborne initial conditions", "No ground contact, battery or propeller aerodynamic model",
                        "No hardware-flight or learned-policy validation"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = report(args.directory)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Verified {summary['passed']}/{summary['trials']} trials and {sum(p['passed'] for p in summary['comparisons'])}/{len(summary['comparisons'])} comparisons.")
