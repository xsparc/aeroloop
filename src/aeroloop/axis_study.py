"""Frozen axis availability comparisons using every physics/control sample."""
import math
from pathlib import Path
from .axis_feedback import AXES, PROFILES, configuration
from .evidence import require
from .outage_study import summarize
from .prediction_study import display
from .simulation import encoded, sha256
from .timing_study import read_study
from .wind_mission import evaluation

COHORTS = (("regression", (0, 1, 2)), ("prior-validation", (101, 202, 303)))


def feedback_errors(samples):
    result = []
    for start, end in ((18., 20.), (40., 42.)):
        rows = [s for s in samples if start <= s["time_s"] < end]
        row = {"start_s": start, "end_s": end, "sample_count": len(rows), "complete": len(rows) == 400}
        for name, indices in (("horizontal", (0, 1)), ("vertical", (2,))):
            errors = [math.sqrt(sum((s.get("axis_feedback", s["feedback"])["position_m"][i]-s["position_m"][i])**2 for i in indices)) for s in rows]
            row[name+"_position_rmse_m"] = math.sqrt(sum(e*e for e in errors)/len(errors)) if errors else None
            row[name+"_position_peak_m"] = max(errors, default=None)
        result.append(row)
    return result


def compare_cohort(old, new, before, after, axes, seeds):
    require(set(old) == set(new) == {(p,s) for p in PROFILES for s in seeds}, "incomplete axis cohort")
    for key in ("controller_binary_sha256", "lock_sha256", "versions"):
        require(before[key] == after[key], "axis cohort runtime differs")
    comparisons = []
    for profile in PROFILES:
        for seed in seeds:
            a, b = old[profile, seed], new[profile, seed]
            require(b["config.json"]["axis_feedback_model"] == configuration(axes), "axis study choice differs")
            require(a["config.json"] == {k:v for k,v in b["config.json"].items() if k != "axis_feedback_model"}, "axis study configuration differs")
            stripped = [{k:v for k,v in s.items() if k not in ("axis_observation", "axis_feedback")} for s in b["samples.json"]]
            exact = a["samples.json"] == stripped and a["metrics.json"] == b["metrics.json"] and a["events.json"] == b["events.json"]
            prefix = a["samples.json"][:3600] == stripped[:3600]
            require(prefix and (profile != PROFILES[0] or exact), "axis study changed inactive trace")
            comparisons.append({"profile":profile, "seed":seed, "no_outage_exact_required":profile == PROFILES[0],
                "trace_unchanged":exact, "preoutage_unchanged":prefix,
                "baseline_feedback_errors":feedback_errors(a["samples.json"]),
                "candidate_feedback_errors":feedback_errors(b["samples.json"])})
    return comparisons


def study(baselines, candidates):
    """Directory mappings keyed by cohort and (cohort, fresh axis), respectively."""
    require(set(baselines) == {c for c,_ in COHORTS} and set(candidates) == {(c,a) for c,_ in COHORTS for a in AXES}, "incomplete axis directory matrix")
    reports, documents = [], {}
    frozen = None
    for name, seeds in COHORTS:
        old, clocks = read_study(baselines[name], PROFILES, PROFILES if name == "regression" else PROFILES[1:], 8, seeds)
        before = summarize(old, clocks, 8, PROFILES, seeds)
        for axes in AXES:
            new, clocks = read_study(candidates[name, axes], PROFILES, PROFILES[1:], 10, seeds)
            after = summarize(new, clocks, 10, PROFILES, seeds)
            identity = {k:after[k] for k in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256", "versions")}
            if frozen is None: frozen = identity
            require(identity == frozen, "fresh axis study source differs")
            comparisons = compare_cohort(old, new, before, after, axes, seeds)
            reports.append({"cohort":name, "fresh_axis":axes, "seeds":list(seeds), "baseline":before, "candidate":after,
                            "comparisons":comparisons, "accepted":after["accepted"]})
            documents[name, axes] = old, new
    return {"schema_version":1, "kind":"isaac_axis_availability_study", "axis_models":[configuration(a) for a in AXES],
            "cohorts":reports, "accepted":all(r["accepted"] for r in reports),
            "limitations":["All six seeds were previously tested; no unseen-seed claim",
                "Noiseless zero-delay 50 Hz synthetic channel; not a hardware sensor or fused estimator",
                "Main predictor unchanged; selected output components replaced only at the controller input",
                "Original targets, physics, contact supervision and all acceptance gates unchanged",
                "Ideal attitude and independent yaw refinement remain unresolved; no hardware-flight validation"]}, documents


def axis_display(run):
    shown = display(run)
    if run["manifest.json"]["schema_version"] == 10:
        for s in shown:
            original = run["samples.json"][round(s["time_s"]/.005)]
            s.update({k:original[k] for k in ("axis_observation", "axis_feedback")})
    return shown


def export_demo(report, documents, output):
    output = Path(output); require(not output.exists(), "output already exists; choose a new directory")
    payloads, cases, outcomes, metadata = {}, [], [], []
    profile = PROFILES[1]
    for c, (name, seeds) in enumerate(COHORTS):
        first = report["cohorts"][c*2]
        metadata.append({"id":name, "seeds":list(seeds), "profiles":[profile],
                         "baseline_source":first["baseline"]["source_commit"], "candidate_source":first["candidate"]["source_commit"]})
        for a, axes in enumerate(AXES):
            cohort = report["cohorts"][c*2+a]
            outcomes.append({"cohort":name, "fresh_axis":axes, "profile":profile,
                             **{side:cohort[side]["duration_results"][1] for side in ("baseline", "candidate")}})
            for j, seed in enumerate(seeds):
                sides = []
                for runs in documents[name, axes]:
                    run = runs[profile, seed]; m = run["manifest.json"]; gates = evaluation(run["metrics.json"])
                    gates.insert(0, {"id":"model_bounds", "label":"Model bounds exceeded", "group":"mission",
                        "value":int(m["failure_reason"] == "model_bounds_exceeded"), "unit":"count", "operator":"eq", "limit":0,
                        "status":"failed" if m["failure_reason"] == "model_bounds_exceeded" else "passed"})
                    require((m["status"] == "passed") == all(g["status"] == "passed" for g in gates), "axis demo gates disagree")
                    sides.append({"status":m["status"], "failure_reason":m["failure_reason"], "metrics":run["metrics.json"], "gates":gates, "samples":axis_display(run)})
                file = f"c{c}-a{a}-s{j}.json"
                payloads[file] = encoded({"schema_version":3, "kind":"axis_demo_pair", "cohort":name, "fresh_axis":axes,
                                         "profile":profile, "seed":seed, "baseline":sides[0], "candidate":sides[1]})
                require(len(payloads[file]) <= 4*1024*1024, "axis pair exceeds size budget")
                cases.append({"cohort":name, "fresh_axis":axes, "profile":profile, "seed":seed, "file":file,
                              "sha256":sha256(payloads[file]), "baseline_status":sides[0]["status"], "candidate_status":sides[1]["status"]})
    payloads["study.json"] = encoded(report)
    payloads["index.json"] = encoded({"schema_version":3, "kind":"axis_demo", "cases":cases, "cohorts":metadata, "outcomes":outcomes,
        "study_sha256":sha256(payloads["study.json"]), "baseline_source":metadata[0]["baseline_source"], "candidate_source":metadata[0]["candidate_source"],
        "display":"Recorded 20 Hz display plus event/outage boundaries; acceptance uses all 200 Hz samples"})
    require(len(payloads["index.json"]) <= 16384 and len(payloads["study.json"]) <= 1024*1024 and sum(map(len,payloads.values())) <= 64*1024*1024, "axis demo exceeds size budget")
    output.mkdir(parents=True)
    for name, value in payloads.items(): (output/name).write_bytes(value)
    return sha256(payloads["index.json"])
