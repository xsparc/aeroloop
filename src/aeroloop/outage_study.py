"""Fixed outage-duration study with failure-preserving sustained recovery."""
import math

from .evidence import require
from .flight_study import compare
from .simulation import encoded, sha256
from .timing_observation import DT, OUTAGE_DURATIONS, configuration
from .timing_study import RECOVERY, capture_metrics, read_study as read_timing_study

PROFILES = ("sample-hold", "hold-dropout", *OUTAGE_DURATIONS)


def recovery_windows(reference, candidate, windows):
    """Final in-band suffix: later re-excursions invalidate earlier brief dwells."""
    require(all(a["time_s"] == b["time_s"] for a, b in zip(reference, candidate)), "recovery cadence differs")
    distance = [math.dist(a["position_m"], b["position_m"]) for a, b in zip(reference, candidate)]
    band, dwell = RECOVERY["position_difference_m"], round(RECOVERY["dwell_s"]/DT)
    rows = []
    for j, (start, end) in enumerate(windows):
        begin = round(end/DT)
        limit = round(windows[j+1][0]/DT) if j+1 < len(windows) else 10001
        stop = min(len(distance), limit)
        # A truncated recording cannot establish the final suffix through the horizon.
        complete = stop == limit
        above = [i for i in range(round(start/DT), stop) if distance[i] > band]
        post = [i for i in above if i >= begin]
        settled = max(begin, post[-1]+1 if post else begin)
        recovery = round((settled-begin)*DT, 9) if complete and stop-settled >= dwell+1 else None
        resumed = next((s for s in candidate[begin:stop]
                        if s["observation"]["source_sequence"] == s["sequence"]), None)
        rows.append({"window_start_s": start, "window_end_s": end,
                     "horizon_end_s": round((limit-1)*DT, 9), "complete_horizon": complete,
                     "peak_position_difference_m": max(distance[round(start/DT):stop], default=None),
                     "samples_above_band": len(above), "post_outage_samples_above_band": len(post),
                     "excursion_observed": bool(above),
                     "first_resumed_capture_s": resumed["time_s"] if resumed else None,
                     "difference_at_resumed_capture_m": distance[resumed["sequence"]] if resumed else None,
                     "recovery_time_s": recovery,
                     "passed": recovery is not None and recovery <= RECOVERY["deadline_s"]})
    return rows


def read_study(directories):
    return read_timing_study(directories, profiles=PROFILES, paced_profiles=PROFILES)


def summarize(runs, clocks, version=7):
    require(set(runs) == set(clocks) == {(p,s) for p in PROFILES for s in range(3)}, "incomplete outage study matrix")
    first = runs[(PROFILES[0], 0)]
    provenance = {k: first["manifest.json"][k] for k in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256")}
    entries, comparisons, durations = [], [], []
    common = lambda c: {k:v for k,v in c.items() if k != "observation_model"}
    for profile in PROFILES:
        windows = configuration(profile)["dropout_windows_s"]
        for seed in range(3):
            run, reference = runs[(profile,seed)], runs[(PROFILES[0],seed)]
            m, c = run["manifest.json"], run["config.json"]
            require(m["schema_version"] == version and not m["source_dirty"] and m["seed"] == seed
                    and c["observation_model"] == configuration(profile), "outage study identity differs")
            require(all(m[k] == v for k,v in provenance.items()), "outage study source differs")
            require(c["simulator_versions"] == first["config.json"]["simulator_versions"], "outage study runtime differs")
            require(common(c) == common(reference["config.json"]), "paired outage configuration differs")
            entries.append({"profile": profile, "seed": seed, "status": m["status"], "failure_reason": m["failure_reason"],
                            "sample_count": len(run["samples.json"]), "config_sha256": m["config_sha256"],
                            "samples_sha256": sha256(encoded(run["samples.json"])), "metrics": run["metrics.json"],
                            "captures": capture_metrics(run["samples.json"], windows), "timing": clocks[(profile,seed)]})
            if windows:
                recovery = recovery_windows(reference["samples.json"], run["samples.json"], windows)
                comparisons.append({"profile": profile, "seed": seed, "reference_profile": PROFILES[0],
                                    **compare(reference, run), "recovery_windows": recovery,
                                    "recovery_passed": all(w["passed"] for w in recovery)})
        rows = [r for r in entries if r["profile"] == profile]
        pairs = [r for r in comparisons if r["profile"] == profile]
        recovery = [w for r in pairs for w in r["recovery_windows"]]
        durations.append({"profile": profile, "duration_s": windows[0][1]-windows[0][0] if windows else 0.,
                          "mission_passes": sum(r["status"] == "passed" for r in rows),
                          "pair_passes": sum(r["passed"] for r in pairs), "pair_count": len(pairs),
                          "recovery_passes": sum(w["passed"] for w in recovery), "recovery_count": len(recovery),
                          "excursion_windows": sum(w["excursion_observed"] for w in recovery),
                          "accepted": all(r["status"] == "passed" and r["sample_count"] == 10001 for r in rows)
                                      and all(r["passed"] and r["recovery_passed"] for r in pairs)})
    return {"schema_version": 1, "kind": "isaac_outage_duration_study", "backend": "isaacsim_physx",
            "source_dirty": False, **provenance, "versions": first["config.json"]["simulator_versions"],
            "physics_dt_s": DT, "control_dt_s": DT, "seeds": [0,1,2], "reference_profile": PROFILES[0],
            "profiles": [configuration(p) for p in PROFILES],
            "recovery_criteria": {**RECOVERY, "method": "final-uninterrupted-in-band-suffix"},
            "trials": len(entries), "passed": sum(r["status"] == "passed" for r in entries),
            "complete": all(r["sample_count"] == 10001 for r in entries),
            "results": entries, "comparisons": comparisons, "duration_results": durations,
            "accepted": all(r["accepted"] for r in durations),
            "limitations": ["Synthetic outages; fixed durations and three seeds do not establish a safe duration or stability proof",
                            "Ideal attitude, rates, acceleration, mission supervisor and contact sensing",
                            "Paired mission bounds and settled recovery are separate outcomes; failures are retained",
                            "Independent yaw refinement remains unresolved; runtime and physics gates unchanged",
                            "Soft real-time only; wall timing excludes startup and evidence serialization"]}


def report(directories):
    return summarize(*read_study(directories))
