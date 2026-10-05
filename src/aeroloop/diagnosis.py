"""Descriptive, full-rate landing diagnostics over verified quality recordings."""
import math
from pathlib import Path

from .axis_feedback import PROFILES
from .channel_quality import QUALITIES
from .evidence import require
from .prediction_study import display
from .quality_study import SEEDS
from .simulation import encoded, sha256
from .wind_mission import evaluation

PHASES = ("other", "airborne-descent", "contact", "motors-off")
COLUMNS = ("time_s", "truth_z_m", "raw_z_m", "predictor_z_m", "applied_z_m",
           "applied_xy_error_m", "applied_z_error_m", "requested_thrust_n", "contact_z_n",
           "main_age_s", "horizontal_age_s", "reference_distance_m", "phase_code")


def phase(sample):
    if sample["mission_phase"] == "landed" and sample["thrust_setpoint_n"] == 0:
        return 3
    if sample["contact_normal_force_n"][2] > .1:
        return 2
    return 1 if sample["mission_phase"] == "landing" else 0


def trace(samples, reference):
    require(all(a["time_s"] == b["time_s"] for a,b in zip(samples, reference)), "diagnosis clocks differ")
    require(len(reference) >= len(samples), "diagnosis reference is truncated")
    return [[s["time_s"], s["position_m"][2], s["observation"]["position_m"][2],
             s["feedback"]["position_m"][2], s["axis_feedback"]["position_m"][2],
             math.dist(s["position_m"][:2], s["axis_feedback"]["position_m"][:2]),
             abs(s["position_m"][2]-s["axis_feedback"]["position_m"][2]),
             s["thrust_setpoint_n"], s["contact_normal_force_n"][2], s["observation"]["age_s"],
             s["axis_observation"]["age_s"], math.dist(s["position_m"], r["position_m"]), phase(s)]
            for s,r in zip(samples, reference)]


def phase_errors(rows, start=40., end=42.):
    window = [r for r in rows if start <= r[0] < end]
    result = []
    for code, name in enumerate(PHASES):
        group = [r for r in window if r[12] == code]
        item = {"phase":name, "samples":len(group)}
        for axis, column in (("horizontal",5), ("vertical",6)):
            peak = max(group, key=lambda r:r[column], default=None)
            item[axis+"_rmse_m"] = math.sqrt(sum(r[column]**2 for r in group)/len(group)) if group else None
            item[axis+"_peak_m"] = peak[column] if peak else None
            item[axis+"_peak_time_s"] = peak[0] if peak else None
        result.append(item)
    return {"start_s":start, "end_s":end, "sample_count":len(window),
            "complete":len(window) == round((end-start)/.005), "groups":result}


def headroom(gate):
    value, limit = gate["value"], gate["limit"]
    if value is None:
        return None
    return {"eq":lambda:-abs(value-limit), "le":lambda:limit-value,
            "lt":lambda:limit-value, "ge":lambda:value-limit,
            "abs_le":lambda:limit-abs(value)}[gate["operator"]]()


def gates(run):
    manifest = run["manifest.json"]
    rows = [{"id":"model_bounds", "label":"Model bounds exceeded", "group":"mission",
             "value":int(manifest["failure_reason"] == "model_bounds_exceeded"), "unit":"count",
             "operator":"eq", "limit":0, "status":"failed" if manifest["failure_reason"] == "model_bounds_exceeded" else "passed"},
            *evaluation(run["metrics.json"])]
    require((manifest["status"] == "passed") == all(g["status"] == "passed" for g in rows), "diagnosis gates disagree")
    return [{**g, "headroom":headroom(g)} for g in rows]


def export_demo(report, documents, output):
    """Call only after quality_study.study has reconstructed the full matrix."""
    output = Path(output)
    require(not output.exists(), "output already exists; choose a new directory")
    require(set(documents) == set(QUALITIES), "incomplete diagnosis quality matrix")
    payloads, cases, diagnostics = {}, [], []
    for q, quality in enumerate(QUALITIES):
        runs = documents[quality]
        require(set(runs) == {(p,s) for p in PROFILES for s in SEEDS}, "incomplete diagnosis cases")
        summary = report["qualities"][q]["summary"]
        require(report["qualities"][q]["quality"] == quality, "diagnosis report order differs")
        for p, profile in enumerate(PROFILES):
            for seed in SEEDS:
                run, reference = runs[profile,seed], runs[PROFILES[0],seed]
                rows = trace(run["samples.json"],reference["samples.json"])
                identifier, reference_id = f"q{q}-p{p}-s{seed}", f"q{q}-p0-s{seed}"
                scored, phases = gates(run), phase_errors(rows)
                comparison = next((c for c in summary["comparisons"] if c["profile"] == profile and c["seed"] == seed), None)
                events = [dict(e) for e in run["events.json"]]
                for name in ("touchdown", "landed"):
                    t = run["metrics.json"]["mission"][name+"_time_s"]
                    if t is not None and not any(e["type"] == name and e["time_s"] == t for e in events):
                        events.append({"type":name, "time_s":t})
                if p:
                    for start,end in ((18.,20.),(40.,42.)):
                        events.extend({"type":label,"time_s":t} for label,t in (("outage-start",start),("outage-end",end)) if t <= rows[-1][0])
                # Retain only the public pose fields needed by the schematic renderer.
                poses = [{k:s[k] for k in ("time_s","position_m","target_m","quaternion_wxyz","mission_phase")} for s in display(run)]
                manifest = run["manifest.json"]
                provenance = {k:manifest[k] for k in ("source_commit","source_tree_sha256","controller_binary_sha256","lock_sha256","config_sha256")}
                provenance.update(samples_sha256=sha256(encoded(run["samples.json"])), versions=summary["versions"], source_dirty=False)
                status = manifest["status"]
                body = {"schema_version":1,"kind":"flight_diagnosis","id":identifier,"quality":quality,"profile":profile,"seed":seed,
                        "reference_id":reference_id,"status":status,"metrics":run["metrics.json"],"failure_reason":manifest["failure_reason"],
                        "columns":list(COLUMNS),"rows":rows,"poses":poses,
                        "events":sorted(events,key=lambda e:e["time_s"]),"gates":scored,"phase_errors":phases,
                        "comparison":comparison,"provenance":provenance}
                data = encoded(body); require(len(data) <= 8*1024*1024, "diagnosis flight exceeds size limit")
                file = identifier+".json"; payloads[file] = data
                support = next(g for g in scored if g["id"] == "final_support_peak_xy_error_m")
                cases.append({"id":identifier,"file":file,"sha256":sha256(data),"quality":quality,"profile":profile,"seed":seed,
                              "reference_id":reference_id,"status":status,"samples":len(rows),"support_headroom_m":support["headroom"]})
                diagnostics.append({"id":identifier,"quality":quality,"profile":profile,"seed":seed,"status":status,
                                    "phase_errors":phases,"support_headroom_m":support["headroom"]})
    analysis = {"schema_version":1,"kind":"isaac_flight_diagnosis","source_commit":report["qualities"][0]["summary"]["source_commit"],
                "new_flights":0,"retained_flights":len(cases),"sample_count":sum(c["samples"] for c in cases),"results":diagnostics}
    payloads["index.json"] = encoded({"schema_version":1,"kind":"flight_diagnosis_index","cases":cases})
    require(len(payloads["index.json"]) <= 32768 and sum(map(len,payloads.values())) <= 128*1024*1024, "diagnosis bundle exceeds size limit")
    output.mkdir(parents=True)
    for name, data in payloads.items(): (output/name).write_bytes(data)
    return sha256(payloads["index.json"]), analysis
