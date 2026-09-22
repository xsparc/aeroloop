"""Compare independently verified missions at fixed controller and wind cadence."""
import math
from pathlib import Path
from .contracts import finite, load_json
from .evidence import keys, require
from .isaac_process import validate_flight_result
from .simulation import encoded, sha256


def timing(value, duration):
    keys(value, {"paced", "elapsed_s", "simulation_s", "max_lag_s", "late_steps", "monitor_enabled"})
    require(type(value["paced"]) is bool and type(value["monitor_enabled"]) is bool
            and finite(value["elapsed_s"]) and value["elapsed_s"] > 0
            and value["simulation_s"] == duration and finite(value["max_lag_s"]) and value["max_lag_s"] >= 0
            and type(value["late_steps"]) is int and 0 <= value["late_steps"] <= round(duration/.005)+1,
            "invalid measured flight timing")
    return {**value, "real_time_factor": duration/value["elapsed_s"]}


def compare(reference, candidate):
    left, right = reference["samples.json"], candidate["samples.json"]
    if len(left) != 10001 or len(right) != 10001:
        return {"passed": False, "reason": "incomplete_pair"}
    require(all(a["time_s"] == b["time_s"] and a["wind_velocity_m_s"] == b["wind_velocity_m_s"] for a,b in zip(left,right)), "wind or control cadence differs")
    distance = [math.dist(a["position_m"], b["position_m"]) for a,b in zip(left,right)]
    angle = [2*math.acos(min(1., abs(sum(x*y for x,y in zip(a["quaternion_wxyz"], b["quaternion_wxyz"]))))) for a,b in zip(left,right)]
    lm, rm = reference["metrics.json"], candidate["metrics.json"]
    landed = (abs(lm["mission"]["landed_time_s"]-rm["mission"]["landed_time_s"])
              if lm["mission"]["landed_time_s"] is not None and rm["mission"]["landed_time_s"] is not None else None)
    result = {"peak_position_difference_m": max(distance),
              "position_difference_rmse_m": math.sqrt(sum(d*d for d in distance)/len(distance)),
              "peak_attitude_difference_rad": max(angle),
              "position_rmse_change_m": abs(lm["position_rmse_m"]-rm["position_rmse_m"]),
              "landed_time_change_s": landed}
    result["passed"] = (max(distance) <= .15 and result["position_rmse_change_m"] <= .05
                        and landed is not None and landed <= .5)
    return result


def report(directories):
    require(len(directories) == 3, "three physics frequency directories required")
    runs, timing_rows = {}, {}
    for directory in directories:
        result = load_json(Path(directory)/"result.json")
        verified = validate_flight_result(directory, result)
        require(len(verified) == 3, "three seeds required per frequency")
        for run, row in zip(verified, result["results"]):
            m, c = run["manifest.json"], run["config.json"]
            dt = c["physics_options"].get("physics_dt_s", .005)
            key = (dt, m["seed"])
            require(m["scenario"] == "ground-mission-wind" and key not in runs and not m["source_dirty"], "invalid flight study case")
            runs[key] = run
            timing_rows[key] = timing(row.get("timing"), run["samples.json"][-1]["time_s"])
            require(timing_rows[key]["paced"] and timing_rows[key]["monitor_enabled"], "study requires paced, monitored sessions")
    require(set(runs) == {(dt, seed) for dt in (.005, .0025, .00125) for seed in range(3)}, "incomplete flight study matrix")
    first = runs[(.005, 0)]
    provenance = {key: first["manifest.json"][key] for key in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256")}
    entries, comparisons = [], []
    for (dt, seed), run in sorted(runs.items(), reverse=True):
        m,c = run["manifest.json"], run["config.json"]
        require(all(m[key] == value for key,value in provenance.items()), "flight study source differs")
        reference = runs[(.005, seed)]
        common = lambda config: {k:v for k,v in config.items() if k != "physics_options"}
        require(common(c) == common(reference["config.json"]), "paired flight configuration differs")
        entries.append({"physics_dt_s": dt, "seed": seed, "status": m["status"], "failure_reason": m["failure_reason"],
                        "config_sha256": m["config_sha256"], "samples_sha256": sha256(encoded(run["samples.json"])),
                        "metrics": run["metrics.json"], "timing": timing_rows[(dt,seed)]})
        if dt != .005:
            comparisons.append({"seed": seed, "physics_dt_s": dt, "reference_dt_s": .005, **compare(reference,run)})
    return {"schema_version": 1, "kind": "isaac_flight_timestep_study", "backend": "isaacsim_physx",
            "source_dirty": False, **provenance, "versions": first["config.json"]["simulator_versions"],
            "control_dt_s": .005, "seeds": [0,1,2], "trials": len(entries),
            "passed": sum(r["status"] == "passed" for r in entries), "results": entries,
            "comparisons": comparisons, "accepted": all(r["status"] == "passed" for r in entries) and all(c["passed"] for c in comparisons),
            "limitations": ["Bounded timestep sensitivity, not numerical convergence", "Independent yaw refinement remains unresolved",
                            "Perfect state feedback and simplified wind, rotors and contact", "Wall timing excludes startup and evidence serialization; soft real-time only"]}
