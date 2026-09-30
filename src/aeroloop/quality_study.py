"""Frozen horizontal quality study, evaluated on every physics/control sample."""
from pathlib import Path
from .axis_feedback import PROFILES, configuration as axis_configuration
from .axis_study import feedback_errors
from .channel_quality import QUALITIES, configuration
from .evidence import require
from .flight_study import compare
from .outage_study import summarize
from .prediction_study import display
from .simulation import encoded, sha256
from .timing_study import read_study
from .wind_mission import evaluation

SEEDS = (0, 1, 2)


def without_quality(sample):
    """Normalize only v11 labels for exact v10 ideal reproduction checks."""
    return {**sample, "axis_observation": {k:v for k,v in sample["axis_observation"].items() if k != "quality"},
            "axis_feedback": {**sample["axis_feedback"], "mode": "horizontal-fresh"}}


def study(retained, directories):
    require(set(directories) == set(QUALITIES), "incomplete quality matrix")
    old, old_clocks = read_study(retained, PROFILES, PROFILES[1:], 10, SEEDS)
    before = summarize(old, old_clocks, 10, PROFILES, SEEDS)
    reports, documents, reproduction = [], {}, []
    identity = None
    common = lambda c: {k:v for k,v in c.items() if k != "axis_feedback_model"}
    for quality in QUALITIES:
        runs, clocks = read_study(directories[quality], PROFILES, PROFILES[1:], 11, SEEDS)
        summary = summarize(runs, clocks, 11, PROFILES, SEEDS)
        source = {k:summary[k] for k in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256", "versions")}
        if identity is None: identity = source
        require(source == identity, "quality source or runtime differs")
        require(all(before[k] == summary[k] for k in ("controller_binary_sha256", "lock_sha256", "versions")), "retained quality runtime differs")
        documents[quality] = runs
        comparisons, errors = [], []
        for profile in PROFILES:
            for seed in SEEDS:
                run, prior = runs[profile, seed], old[profile, seed]
                require(run["config.json"]["axis_feedback_model"] == configuration(quality)
                        and prior["config.json"]["axis_feedback_model"] == axis_configuration("horizontal")
                        and common(run["config.json"]) == common(prior["config.json"]), "quality settings differ")
                if quality == "ideal":
                    exact = ([without_quality(s) for s in run["samples.json"]] == prior["samples.json"]
                             and run["metrics.json"] == prior["metrics.json"] and run["events.json"] == prior["events.json"])
                    require(exact, "ideal quality changed retained horizontal flight")
                    reproduction.append({"profile":profile, "seed":seed, "trace_unchanged":exact})
                else:
                    comparisons.append({"profile":profile, "seed":seed, **compare(documents["ideal"][profile, seed], run)})
                errors.append({"profile":profile, "seed":seed, "windows":feedback_errors(run["samples.json"]),
                               "maximum_channel_age_s":max(s["axis_observation"]["age_s"] for s in run["samples.json"])})
        reports.append({"quality":quality, "model":configuration(quality), "summary":summary,
                        "versus_ideal":comparisons, "feedback_errors":errors})
    return {"schema_version":1, "kind":"isaac_horizontal_quality_study", "seeds":list(SEEDS),
            "retained_source":before["source_commit"], "ideal_reproduction":reproduction, "qualities":reports,
            "accepted":all(r["summary"]["accepted"] for r in reports),
            "limitations":["Three previously tested regression seeds, no unseen-seed claim",
                "Synthetic clipped Gaussian noise and fixed delay; not a calibrated hardware sensor or fused estimate",
                "Bootstrap exposes the first capture at t=0 before steady delayed delivery",
                "Predictor, control gains, truth physics, original mission, pair and recovery limits unchanged",
                "Ideal attitude and independent yaw refinement remain unresolved; no hardware-flight validation"]}, documents


def quality_display(run):
    shown = display(run)
    for sample in shown:
        original = run["samples.json"][round(sample["time_s"]/.005)]
        sample.update({k:original[k] for k in ("axis_observation", "axis_feedback")})
    return shown


def export_demo(report, documents, output):
    output = Path(output); require(not output.exists(), "output already exists; choose a new directory")
    payloads, cases, outcomes = {}, [], []
    profile = PROFILES[1]
    for q, quality in enumerate(QUALITIES[1:]):
        outcomes.append({"quality":quality, "profile":profile,
            "baseline":report["qualities"][0]["summary"]["duration_results"][1],
            "candidate":report["qualities"][q+1]["summary"]["duration_results"][1]})
        for seed in SEEDS:
            sides = []
            for mode in ("ideal", quality):
                run = documents[mode][profile, seed]; m = run["manifest.json"]; gates = evaluation(run["metrics.json"])
                gates.insert(0, {"id":"model_bounds", "label":"Model bounds exceeded", "group":"mission",
                    "value":int(m["failure_reason"] == "model_bounds_exceeded"), "unit":"count", "operator":"eq", "limit":0,
                    "status":"failed" if m["failure_reason"] == "model_bounds_exceeded" else "passed"})
                require((m["status"] == "passed") == all(g["status"] == "passed" for g in gates), "quality demo gates disagree")
                sides.append({"status":m["status"], "failure_reason":m["failure_reason"], "metrics":run["metrics.json"],
                              "gates":gates, "samples":quality_display(run)})
            file = f"q{q}-s{seed}.json"
            payloads[file] = encoded({"schema_version":4, "kind":"quality_demo_pair", "quality":quality,
                                     "profile":profile, "seed":seed, "baseline":sides[0], "candidate":sides[1]})
            require(len(payloads[file]) <= 4*1024*1024, "quality pair exceeds size budget")
            cases.append({"quality":quality, "profile":profile, "seed":seed, "file":file, "sha256":sha256(payloads[file]),
                          "baseline_status":sides[0]["status"], "candidate_status":sides[1]["status"]})
    payloads["study.json"] = encoded(report)
    source = report["qualities"][0]["summary"]["source_commit"]
    payloads["index.json"] = encoded({"schema_version":4, "kind":"quality_demo", "cases":cases, "outcomes":outcomes,
        "study_sha256":sha256(payloads["study.json"]), "baseline_source":source, "candidate_source":source,
        "display":"Recorded 20 Hz display plus event/outage boundaries; acceptance uses all 200 Hz samples"})
    require(len(payloads["index.json"]) <= 16384 and len(payloads["study.json"]) <= 1024*1024
            and sum(map(len,payloads.values())) <= 64*1024*1024, "quality demo exceeds size budget")
    output.mkdir(parents=True)
    for name, value in payloads.items(): (output/name).write_bytes(value)
    return sha256(payloads["index.json"])
