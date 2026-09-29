"""Full-rate capture timing, outage recovery and unchanged mission acceptance."""
import math
from pathlib import Path

from .contracts import load_json
from .evidence import require
from .flight_study import compare, timing
from .isaac_process import validate_flight_result
from .observation_study import observation_metrics
from .simulation import encoded, sha256
from .timing_observation import DT, PROFILES, WINDOWS, configuration

RECOVERY = {"position_difference_m": .05, "dwell_s": 1., "deadline_s": 5.}


def capture_metrics(samples, outage_windows=WINDOWS):
    fresh = [s for s in samples if s["observation"]["source_sequence"] == s["sequence"]]
    windows = []
    for start, end in outage_windows:
        resumed = next((s["time_s"] for s in fresh if s["time_s"] >= end), None)
        before = [s for s in fresh if s["time_s"] < start]
        windows.append({"start_s": start, "end_s": end,
                        "last_capture_before_s": before[-1]["time_s"] if before else None,
                        "first_capture_after_s": resumed})
    return {"captures": len(fresh), "held_control_samples": len(samples)-len(fresh),
            **observation_metrics(samples), "windows": windows}


def recovery_windows(reference, candidate):
    """First complete one-second dwell, expressed relative to each outage end."""
    differences = [math.dist(a["position_m"], b["position_m"]) for a, b in zip(reference, candidate)]
    dwell = round(RECOVERY["dwell_s"]/DT)
    results = []
    for window, (_, end) in enumerate(WINDOWS):
        begin = round(end/DT)
        stop = min(len(differences), round(WINDOWS[window+1][0]/DT) if window+1 < len(WINDOWS) else len(differences))
        recovery = None
        consecutive = 0
        for i in range(begin, stop):
            consecutive = consecutive+1 if differences[i] <= RECOVERY["position_difference_m"] else 0
            if consecutive >= dwell+1:
                recovery = round((i-dwell-begin)*DT, 9)
                break
        results.append({"window_start_s": WINDOWS[window][0], "window_end_s": end,
                        "recovery_time_s": recovery,
                        "passed": recovery is not None and recovery <= RECOVERY["deadline_s"]})
    return results


def read_study(directories, profiles=PROFILES, paced_profiles=("hold-dropout",), version=7):
    require(len(directories) == len(profiles), "one directory required per timing profile")
    runs, clocks = {}, {}
    for directory in directories:
        result = load_json(Path(directory)/"result.json")
        verified = validate_flight_result(directory, result)
        require(len(verified) == 3, "three seeds required per timing profile")
        worker_profiles = set()
        for run, row in zip(verified, result["results"]):
            m, c = run["manifest.json"], run["config.json"]
            require(m["schema_version"] == version and not m["source_dirty"], "clean timing recording required")
            profile = c["observation_model"]["profile"]
            worker_profiles.add(profile)
            key = (profile, m["seed"])
            require(key not in runs, "duplicate timing study case")
            runs[key] = run
            clocks[key] = timing(row.get("timing"), run["samples.json"][-1]["time_s"])
            require(clocks[key]["monitor_enabled"] and (profile not in paced_profiles or clocks[key]["paced"]),
                    "timing study requires monitoring and combined-profile pacing")
        require(len(worker_profiles) == 1, "mixed worker timing profiles")
    require(set(runs) == {(p, seed) for p in profiles for seed in range(3)}, "incomplete timing study matrix")
    return runs, clocks


def summarize(runs, clocks):
    first = runs[("timing-ideal", 0)]
    provenance = {k:first["manifest.json"][k] for k in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256")}
    entries, comparisons = [], []
    common = lambda c: {k:v for k,v in c.items() if k != "observation_model"}
    for profile in PROFILES:
        for seed in range(3):
            run = runs[(profile, seed)]
            m, c = run["manifest.json"], run["config.json"]
            require(all(m[k] == v for k,v in provenance.items()), "timing study source differs")
            require(c["simulator_versions"] == first["config.json"]["simulator_versions"], "timing study runtime differs")
            reference = runs[("timing-ideal", seed)]
            require(common(c) == common(reference["config.json"]), "paired timing configuration differs")
            entries.append({"profile": profile, "seed": seed, "status": m["status"], "failure_reason": m["failure_reason"],
                            "sample_count": len(run["samples.json"]), "config_sha256": m["config_sha256"],
                            "samples_sha256": sha256(encoded(run["samples.json"])), "metrics": run["metrics.json"],
                            "captures": capture_metrics(run["samples.json"]), "timing": clocks[(profile,seed)]})
            if profile != "timing-ideal":
                pair = compare(reference, run)
                recovery = recovery_windows(reference["samples.json"], run["samples.json"]) if "dropout" in profile else []
                comparisons.append({"profile": profile, "seed": seed, "reference_profile": "timing-ideal", **pair,
                                    "recovery_windows": recovery,
                                    "recovery_passed": all(w["passed"] for w in recovery)})
    return {"schema_version": 1, "kind": "isaac_observation_timing_study", "backend": "isaacsim_physx",
            "source_dirty": False, **provenance, "versions": first["config.json"]["simulator_versions"],
            "physics_dt_s": DT, "control_dt_s": DT, "seeds": [0,1,2],
            "profiles": [configuration(p) for p in PROFILES], "recovery_criteria": RECOVERY,
            "trials": len(entries), "passed": sum(r["status"] == "passed" for r in entries),
            "results": entries, "comparisons": comparisons,
            "accepted": all(r["status"] == "passed" and r["sample_count"] == 10001 for r in entries)
                        and all(c["passed"] and c["recovery_passed"] for c in comparisons),
            "limitations": ["Synthetic capture cadence and deterministic outages; no sensor calibration or estimator",
                            "Ideal attitude, rates, acceleration, mission supervisor and contact sensing",
                            "Fixed three-seed robustness and recovery checks, not a stability proof or real-flight validation",
                            "Independent yaw refinement remains unresolved; runtime and physics gates unchanged",
                            "Soft real-time only; wall timing excludes startup and evidence serialization"]}


def report(directories):
    return summarize(*read_study(directories))
