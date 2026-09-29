"""Reverify old/new controller cohorts and export a bounded recorded comparison."""
import math
from pathlib import Path
from .evidence import require
from .outage_study import PROFILES, read_study, summarize
from .timing_study import read_study as read_timing
from .timing_observation import configuration as timing_configuration
from .predictor import configuration
from .simulation import encoded, sha256
from .wind_mission import evaluation


def study(baseline, candidate):
    old, old_clocks = read_study(baseline)
    new, new_clocks = read_timing(candidate, PROFILES, PROFILES, version=8)
    before, after = summarize(old, old_clocks), summarize(new, new_clocks, version=8)
    for key in ("controller_binary_sha256", "lock_sha256", "versions"):
        require(before[key] == after[key], "predictor cohorts have different runtime or native controller")
    pairs = []
    for profile in PROFILES:
        for seed in range(3):
            a, b = old[(profile,seed)], new[(profile,seed)]
            require(a["config.json"] == {k:v for k,v in b["config.json"].items() if k != "feedback_model"}, "predictor cohort configuration differs")
            samples = b["samples.json"]
            active = [s for s in samples if s["feedback"]["mode"] == "predicting"]
            error = lambda field: math.sqrt(sum(math.dist(s["position_m"],s[field]["position_m"])**2 for s in active)/len(active)) if active else 0.
            unchanged = (a["samples.json"] == [{k:v for k,v in s.items() if k != "feedback"} for s in samples]
                         and a["metrics.json"] == b["metrics.json"] and a["events.json"] == b["events.json"])
            pairs.append({"profile": profile, "seed": seed, "baseline_status": a["manifest.json"]["status"],
                          "candidate_status": b["manifest.json"]["status"], "baseline_trace_unchanged": unchanged,
                          "predicted_samples": len(active), "raw_position_rmse_during_prediction_m": error("observation"),
                          "feedback_position_rmse_during_prediction_m": error("feedback")})
    unchanged = all(p["baseline_trace_unchanged"] for p in pairs if p["profile"] == "sample-hold")
    report = {"schema_version":1, "kind":"isaac_predictive_feedback_study", "feedback_model":configuration(),
              "baseline":before, "candidate":after, "comparisons":pairs, "no_outage_unchanged":unchanged,
              "accepted":unchanged and after["accepted"],
              "limitations":["Regression seeds, not unseen validation; no default enablement or hardware claim",
                              "Predictor uses known rotor output and ideal attitude; this is not an IMU or EKF",
                              "Sensor captures remain separate from predicted feedback; failures remain visible"]}
    return report, old, new


def display(run):
    samples = run["samples.json"]
    indices = set(range(0,len(samples),10)) | {len(samples)-1}
    moments = [e["time_s"] for e in run["events.json"]]
    moments += [t for w in timing_configuration(run["config.json"]["observation_model"]["profile"])["dropout_windows_s"] for t in w]
    for t in moments:
        i = round(t/.005)
        indices.update(j for j in (i-1,i,i+1) if 0 <= j < len(samples))
    fields = ("time_s","position_m","target_m","quaternion_wxyz","rotor_thrust_n","wind_velocity_m_s",
              "external_force_n","external_moment_nm","mission_phase","contact_normal_force_n","support_clearance_m","observation")
    return [{**{k:s[k] for k in fields}, "feedback":s.get("feedback", {
             "mode":"held", "position_m":s["observation"]["position_m"],"velocity_m_s":s["observation"]["velocity_m_s"],
             "disturbance_acceleration_m_s2":[0.,0.,0.]})} for i,s in enumerate(samples) if i in indices]


def export_demo(report, old, new, output):
    output = Path(output)
    require(not output.exists(), "output already exists; choose a new directory")
    payloads, cases = {}, []
    for p, profile in enumerate(PROFILES):
        for seed in range(3):
            runs = [old[(profile,seed)],new[(profile,seed)]]
            name = f"p{p}-s{seed}.json"
            sides = []
            for run in runs:
                gates = evaluation(run["metrics.json"])
                m = run["manifest.json"]
                gates.insert(0,{"id":"model_bounds","label":"Model bounds exceeded","group":"mission",
                              "value":int(m["failure_reason"]=="model_bounds_exceeded"),"unit":"count","operator":"eq","limit":0,
                              "status":"failed" if m["failure_reason"]=="model_bounds_exceeded" else "passed"})
                require((m["status"]=="passed")==all(g["status"]=="passed" for g in gates),"demo mission gates disagree")
                sides.append({"status":m["status"],"failure_reason":m["failure_reason"],"metrics":run["metrics.json"],"gates":gates,"samples":display(run)})
            payloads[name] = encoded({"schema_version":1,"kind":"outage_demo_pair","profile":profile,"seed":seed,
                                      "baseline":sides[0],"candidate":sides[1]})
            require(len(payloads[name])<=4*1024*1024,"demo pair exceeds size budget")
            cases.append({"profile":profile,"seed":seed,"file":name,"sha256":sha256(payloads[name]),
                          "baseline_status":sides[0]["status"],"candidate_status":sides[1]["status"]})
    payloads["study.json"] = encoded(report)
    index = {"schema_version":1,"kind":"outage_demo","cases":cases,"study_sha256":sha256(payloads["study.json"]),
             "baseline_source":report["baseline"]["source_commit"],"candidate_source":report["candidate"]["source_commit"],
             "outcomes": [{"profile":p,"baseline":report["baseline"]["duration_results"][i],
                           "candidate":report["candidate"]["duration_results"][i]} for i,p in enumerate(PROFILES)],
             "display":"Recorded 20 Hz display with event/outage boundaries; acceptance uses all 200 Hz samples"}
    payloads["index.json"] = encoded(index)
    require(sum(map(len,payloads.values()))<=64*1024*1024,"demo exceeds size budget")
    output.mkdir(parents=True)
    for name,value in payloads.items(): (output/name).write_bytes(value)
    return sha256(payloads["index.json"])
