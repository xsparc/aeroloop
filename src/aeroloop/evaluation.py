"""Compact, verified flight-study evaluation and event-preserving demonstration."""
from pathlib import Path

from .evidence import replay_document, require
from .flight_study import read_study, summarize
from .simulation import encoded, sha256
from .wind_mission import evaluation


def export_evaluation(directories, output):
    output = Path(output)
    require(not output.exists(), "output already exists; choose a new directory")
    runs, timing_rows = read_study(directories)
    summary = summarize(runs, timing_rows)
    payloads, cases = {}, []
    for row in summary["results"]:
        run = runs[(row["physics_dt_s"], row["seed"])]
        manifest = run["manifest.json"]
        gates = evaluation(row["metrics"])
        # Bounds are verified independently by read_run; retain that outcome too.
        gates.insert(0, {"id": "model_bounds", "label": "Model bounds exceeded", "group": "mission",
                         "value": int(manifest["failure_reason"] == "model_bounds_exceeded"), "unit": "count",
                         "operator": "eq", "limit": 0,
                         "status": "failed" if manifest["failure_reason"] == "model_bounds_exceeded" else "passed"})
        require((manifest["status"] == "passed") == all(g["status"] == "passed" for g in gates), "gate outcome differs")
        entry = {key: manifest[key] for key in ("run_id", "scenario", "seed", "status")}
        cases.append({**entry, **row, "gates": gates})
        for name, value in {"replay.json": replay_document(run),
                            **{name: run[name] for name in ("manifest.json", "metrics.json", "events.json")}}.items():
            payloads[f"{entry['run_id']}/{name}"] = encoded(value)
    document = {"schema_version": 1, "kind": "flight_evaluation", "study": summary,
                "cases": cases, "checksums": {name: sha256(value) for name, value in payloads.items()},
                "display": "Event-preserving 20 Hz replay; evaluation uses all 200 Hz control samples"}
    payloads["evaluation.json"] = encoded(document)
    require(len(payloads["evaluation.json"]) <= 256*1024, "evaluation index exceeds size budget")
    require(sum(map(len, payloads.values())) <= 16*1024*1024, "evaluation bundle exceeds size budget")
    output.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return document
