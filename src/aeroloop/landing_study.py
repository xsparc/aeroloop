"""Frozen regression and unseen-seed evaluation of capture-aware descent."""
from pathlib import Path
from .evidence import require
from .landing_guard import configuration
from .outage_study import summarize
from .prediction_study import display
from .simulation import encoded, sha256
from .timing_study import read_study
from .wind_mission import evaluation

COHORTS = (
    ("regression", (0,1,2), ("sample-hold","hold-dropout-500ms","hold-dropout-1000ms","hold-dropout-2000ms")),
    ("unseen", (101,202,303), ("sample-hold","hold-dropout-2000ms")),
)


def compare_cohort(old, new, before, after, seeds, profiles):
    require(set(old) == set(new) == {(p,s) for p in profiles for s in seeds}, "incomplete landing cohort")
    for key in ("controller_binary_sha256","lock_sha256","versions"):
        require(before[key] == after[key], "landing cohorts have different runtime or controller")
    comparisons=[]
    for profile in profiles:
        for seed in seeds:
            a,b=old[profile,seed],new[profile,seed]
            require(a["config.json"] == {k:v for k,v in b["config.json"].items() if k != "landing_guard_model"}, "landing cohort configuration differs")
            samples=b["samples.json"]
            stripped=[{k:v for k,v in s.items() if k != "landing_guard"} for s in samples]
            active=next((s for s in samples if s["landing_guard"]["activated_at_s"] is not None),None)
            resumed=next((s for s in samples if s["landing_guard"]["resumed_at_s"] is not None),None)
            n=active["sequence"] if active else len(samples)
            exact=(a["samples.json"] == stripped and a["metrics.json"] == b["metrics.json"] and a["events.json"] == b["events.json"])
            prefix=(len(a["samples.json"])>=n and a["samples.json"][:n] == stripped[:n])
            required=profile in ("sample-hold","hold-dropout-500ms")
            require(prefix and (not required or exact), "inactive landing guard changed the baseline trace")
            comparisons.append({"profile":profile,"seed":seed,"baseline_status":a["manifest.json"]["status"],
                "candidate_status":b["manifest.json"]["status"],"inactive_trace_required":required,
                "trace_unchanged":exact,"preactivation_unchanged":prefix,
                "activated_at_s":active["time_s"] if active else None,
                "resumed_at_s":resumed["time_s"] if resumed else None,
                "time_until_descent_s":round(resumed["time_s"]-active["time_s"],9) if resumed and active else None,
                "modes_observed":sorted({s["landing_guard"]["mode"] for s in samples})})
    return comparisons


def study(regression_baseline, regression_candidate, unseen_baseline, unseen_candidate):
    documents={};cohorts=[]
    for (name,seeds,profiles),(baseline,candidate) in zip(COHORTS,((regression_baseline,regression_candidate),(unseen_baseline,unseen_candidate))):
        paced=profiles if name=="regression" else ("hold-dropout-2000ms",)
        old,old_clocks=read_study(baseline,profiles,paced,8,seeds)
        new,new_clocks=read_study(candidate,profiles,() if name=="regression" else paced,9,seeds)
        before=summarize(old,old_clocks,8,profiles,seeds)
        after=summarize(new,new_clocks,9,profiles,seeds)
        comparisons=compare_cohort(old,new,before,after,seeds,profiles)
        documents[name]=(old,new)
        cohorts.append({"id":name,"seeds":list(seeds),"baseline":before,"candidate":after,"comparisons":comparisons,
                        "accepted":after["accepted"]})
    # The fresh unseen baseline and both guarded cohorts must share the frozen build.
    for key in ("source_commit","source_tree_sha256","controller_binary_sha256","lock_sha256","versions"):
        require(cohorts[0]["candidate"][key] == cohorts[1]["baseline"][key] == cohorts[1]["candidate"][key], "fresh landing study source differs")
    report={"schema_version":1,"kind":"isaac_landing_guard_study","landing_guard_model":configuration(),
            "cohorts":cohorts,"accepted":all(c["accepted"] for c in cohorts),
            "limitations":["Frozen unseen seeds are a small synthetic sample, not a stability proof",
                "Holding a command cannot guarantee altitude with inaccurate predicted feedback",
                "All scoring uses the original scheduled mission target and deadline",
                "Ideal attitude and contact supervision; independent yaw refinement remains open",
                "No default enablement or hardware-flight validation"]}
    return report,documents


def guard_display(run):
    shown={s["time_s"]:s for s in display(run)}
    samples=run["samples.json"]
    for i,s in enumerate(samples):
        if "landing_guard" not in s:continue
        g=s["landing_guard"]
        if i and (g["mode"],g["resumed_at_s"]) != (samples[i-1]["landing_guard"]["mode"],samples[i-1]["landing_guard"]["resumed_at_s"]):
            for j in (i-1,i,i+1):
                if 0<=j<len(samples):
                    t=samples[j]["time_s"]
                    if t not in shown:
                        template=next(iter(shown.values()))
                        shown[t]={k:samples[j][k] for k in template if k != "landing_guard"}
    for s in shown.values():
        source=samples[round(s["time_s"]/.005)]
        if "landing_guard" in source:s["landing_guard"]=source["landing_guard"]
    return sorted(shown.values(),key=lambda s:s["time_s"])


def export_demo(report, documents, output):
    output=Path(output);require(not output.exists(),"output already exists; choose a new directory")
    payloads={};cases=[];outcomes=[];metadata=[]
    for c,(name,seeds,profiles) in enumerate(COHORTS):
        cohort=report["cohorts"][c]
        metadata.append({"id":name,"seeds":list(seeds),"profiles":list(profiles),
                         "baseline_source":cohort["baseline"]["source_commit"],"candidate_source":cohort["candidate"]["source_commit"]})
        for p,profile in enumerate(profiles):
            outcomes.append({"cohort":name,"profile":profile,**{side:cohort[side]["duration_results"][p] for side in ("baseline","candidate")}})
            for j,seed in enumerate(seeds):
                sides=[]
                for runs in documents[name]:
                    run=runs[profile,seed];m=run["manifest.json"];gates=evaluation(run["metrics.json"])
                    gates.insert(0,{"id":"model_bounds","label":"Model bounds exceeded","group":"mission",
                        "value":int(m["failure_reason"]=="model_bounds_exceeded"),"unit":"count","operator":"eq","limit":0,
                        "status":"failed" if m["failure_reason"]=="model_bounds_exceeded" else "passed"})
                    require((m["status"]=="passed")==all(g["status"]=="passed" for g in gates),"demo gates disagree")
                    sides.append({"status":m["status"],"failure_reason":m["failure_reason"],"metrics":run["metrics.json"],"gates":gates,"samples":guard_display(run)})
                file=f"c{c}-p{p}-s{j}.json"
                payloads[file]=encoded({"schema_version":2,"kind":"landing_demo_pair","cohort":name,"profile":profile,"seed":seed,"baseline":sides[0],"candidate":sides[1]})
                require(len(payloads[file])<=4*1024*1024,"demo pair exceeds size budget")
                cases.append({"cohort":name,"profile":profile,"seed":seed,"file":file,"sha256":sha256(payloads[file]),
                              "baseline_status":sides[0]["status"],"candidate_status":sides[1]["status"]})
    payloads["study.json"]=encoded(report)
    index={"schema_version":2,"kind":"landing_demo","cases":cases,"cohorts":metadata,"outcomes":outcomes,
           "study_sha256":sha256(payloads["study.json"]),"baseline_source":metadata[0]["baseline_source"],"candidate_source":metadata[0]["candidate_source"],
           "display":"Recorded 20 Hz display plus event/outage/guard transitions; acceptance uses all 200 Hz samples"}
    payloads["index.json"]=encoded(index)
    require(len(payloads["index.json"])<=16384 and len(payloads["study.json"])<=1024*1024 and sum(map(len,payloads.values()))<=64*1024*1024,"demo exceeds size budget")
    output.mkdir(parents=True)
    for name,value in payloads.items():(output/name).write_bytes(value)
    return sha256(payloads["index.json"])
