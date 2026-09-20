"""Verify all five contact missions and publish only allowlisted measurements."""
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
from aeroloop.mission import SCENARIO
from aeroloop import wind_mission
from aeroloop.simulation import encoded, sha256


def report(directory, scenario=SCENARIO):
    require(scenario in (SCENARIO, wind_mission.SCENARIO), "unsupported mission report scenario")
    windy = scenario == wind_mission.SCENARIO
    result = load_json(Path(directory) / "result.json")
    runs = validate_flight_result(directory, result)
    require({(r["manifest.json"]["scenario"], r["manifest.json"]["seed"]) for r in runs}
            == {(scenario, seed) for seed in range(5)}, "report requires mission seeds 0 through 4")
    require(all(r["manifest.json"]["source_dirty"] is False for r in runs), "report requires clean source revisions")
    fields = ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256")
    provenance = {k: runs[0]["manifest.json"][k] for k in fields}
    require(all(all(r["manifest.json"][k] == v for k, v in provenance.items()) for r in runs), "suite source provenance differs")
    common = lambda r: {k: v for k, v in r["config.json"].items() if k not in ("seed", "initial_state")}
    require(all(common(r) == common(runs[0]) for r in runs), "suite configuration differs")
    require(finite(result.get("wall_time_s")) and result["wall_time_s"] > 0, "invalid wall time")
    entries = []
    for run in sorted(runs, key=lambda r: r["manifest.json"]["seed"]):
        manifest, samples = run["manifest.json"], run["samples.json"]
        entries.append({**{k: manifest[k] for k in ("run_id", "scenario", "seed", "status", "failure_reason", "config_sha256")},
            "metrics": run["metrics.json"], "events": run["events.json"],
            "rotor_thrust_range_n": [min(min(s["rotor_thrust_n"]) for s in samples), max(max(s["rotor_thrust_n"]) for s in samples)],
            "allocation_saturated_samples": sum(s["allocation_scale"] < 1.-1e-12 for s in samples)})
        if windy:
            final_winds = [math.hypot(*s["wind_velocity_m_s"]) for s in samples if s["time_s"] >= 48.]
            entries[-1].update(
                wind_samples_sha256=sha256(encoded([s["wind_velocity_m_s"] for s in samples])),
                peak_wind_speed_m_s=max(math.hypot(*s["wind_velocity_m_s"]) for s in samples),
                peak_descent_wind_m_s=max((math.hypot(*s["wind_velocity_m_s"]) for s in samples if s["time_s"] >= 34.), default=None),
                final_wind_speed_range_m_s=[min(final_winds), max(final_winds)] if final_winds else None)
    config = runs[0]["config.json"]
    return {"schema_version": 1, "kind": "isaac_turbulent_mission_summary" if windy else "isaac_ground_mission_summary", "backend": "isaacsim_physx",
        "source_dirty": False, **provenance, "versions": config["simulator_versions"],
        **{k: config[k] for k in ("model", "actuator", "mission", "physics_options", "dt_s", "duration_s")},
        **({k: config[k] for k in ("wind", "trajectory_control")} if windy else {}),
        "wall_time_s": result["wall_time_s"], "trials": len(entries),
        "passed": sum(e["status"] == "passed" for e in entries), "results": entries,
        "interpretation": "Contact force is the measured ENU net normal force, excluding friction. Touchdown descent speed uses the preceding physics sample; rotor commands go to zero after continuous contact latches landing.",
        "limitations": ["Temporal OU wind and perfect state" if windy else "Calm air and perfect state", "Illustrative cuboid contact geometry and friction",
                        "No battery, propeller aerodynamics or ground effect", "No hardware-flight or learned-policy validation"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--scenario", choices=(SCENARIO, wind_mission.SCENARIO), default=SCENARIO)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = report(args.directory, args.scenario)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Verified {summary['passed']}/{summary['trials']} ground-contact missions.")
