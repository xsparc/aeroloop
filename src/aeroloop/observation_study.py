"""Full-rate truth-based robustness reporting for four observation profiles."""
import math
from pathlib import Path
from .contracts import load_json
from .evidence import require
from .flight_study import compare, timing
from .isaac_process import validate_flight_result
from .observation import PROFILES, configuration
from .simulation import encoded, sha256


def observation_metrics(samples):
    result = {"max_age_s": max(s["observation"]["age_s"] for s in samples)}
    for field, unit in (("position_m", "m"), ("velocity_m_s", "m_s")):
        errors = [math.dist(s[field], s["observation"][field]) for s in samples]
        prefix = "position" if field == "position_m" else "velocity"
        result[f"{prefix}_discrepancy_rmse_{unit}"] = math.sqrt(sum(e*e for e in errors)/len(errors))
        result[f"{prefix}_discrepancy_peak_{unit}"] = max(errors)
    return result


def read_study(directories):
    require(len(directories) == 4, "four observation profile directories required")
    runs, clocks = {}, {}
    for directory in directories:
        result = load_json(Path(directory)/"result.json")
        verified = validate_flight_result(directory, result)
        require(len(verified) == 3, "three seeds required per observation profile")
        profiles = set()
        for run, row in zip(verified, result["results"]):
            m, c = run["manifest.json"], run["config.json"]
            require(m["schema_version"] == 6 and not m["source_dirty"], "clean observation recording required")
            profile = c["observation_model"]["profile"]
            profiles.add(profile)
            key = (profile, m["seed"])
            require(key not in runs, "duplicate observation study case")
            runs[key] = run
            clocks[key] = timing(row.get("timing"), run["samples.json"][-1]["time_s"])
            require(clocks[key]["monitor_enabled"] and (profile != "noise-delay" or clocks[key]["paced"]), "study requires monitoring and combined-profile pacing")
        require(len(profiles) == 1, "mixed worker observation profiles")
    require(set(runs) == {(p, seed) for p in PROFILES for seed in range(3)}, "incomplete observation study matrix")
    return runs, clocks


def summarize(runs, clocks):
    first = runs[("ideal", 0)]
    provenance = {k:first["manifest.json"][k] for k in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256")}
    entries, comparisons = [], []
    common = lambda c: {k:v for k,v in c.items() if k != "observation_model"}
    for profile in PROFILES:
        for seed in range(3):
            run = runs[(profile, seed)]
            m, c = run["manifest.json"], run["config.json"]
            require(all(m[k] == v for k,v in provenance.items()), "observation study source differs")
            require(c["simulator_versions"] == first["config.json"]["simulator_versions"], "observation study runtime differs")
            reference = runs[("ideal", seed)]
            require(common(c) == common(reference["config.json"]), "paired observation configuration differs")
            entries.append({"profile": profile, "seed": seed, "status": m["status"], "failure_reason": m["failure_reason"],
                            "sample_count": len(run["samples.json"]), "config_sha256": m["config_sha256"],
                            "samples_sha256": sha256(encoded(run["samples.json"])), "metrics": run["metrics.json"],
                            "observations": observation_metrics(run["samples.json"]), "timing": clocks[(profile,seed)]})
            if profile != "ideal":
                comparisons.append({"profile": profile, "seed": seed, "reference_profile": "ideal", **compare(reference,run)})
    return {"schema_version": 1, "kind": "isaac_observation_robustness_study", "backend": "isaacsim_physx",
            "source_dirty": False, **provenance, "versions": first["config.json"]["simulator_versions"],
            "physics_dt_s": .005, "control_dt_s": .005, "seeds": [0,1,2],
            "profiles": [configuration(p) for p in PROFILES], "trials": len(entries),
            "passed": sum(r["status"] == "passed" for r in entries), "results": entries, "comparisons": comparisons,
            "accepted": all(r["status"] == "passed" and r["sample_count"] == 10001 for r in entries) and all(c["passed"] for c in comparisons),
            "limitations": ["Synthetic position/velocity observations; no calibrated sensor or estimator model",
                            "Ideal attitude, rates, acceleration, mission supervisor and contact sensing",
                            "Fixed three-seed robustness checks, not a stability proof or real-flight validation",
                            "Independent yaw refinement remains unresolved; runtime and physics gates unchanged",
                            "Soft real-time only; wall timing excludes startup and evidence serialization"]}


def report(directories):
    return summarize(*read_study(directories))
