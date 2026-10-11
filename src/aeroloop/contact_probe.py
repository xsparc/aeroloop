"""Bounded signed contact diagnostics; never a flight acceptance artifact."""
from dataclasses import asdict
import math
from pathlib import Path
import re

from .contracts import finite, load_json
from .evidence import keys, require
from .frames import vector
from .mission import clearance
from .physics import Model
from .simulation import encoded, sha256

TIMESTEPS = (.005, .0025, .00125)
MODES = ("per-iteration", "per-step")
CAPACITY = 64
DURATION = 3.
KIND = "isaac_contact_probe"
HASH = re.compile(r"[0-9a-f]{64}")


def configuration(dt, mode):
    from .wind_mission import contact_configuration, wind_model
    return {"physics_dt_s": dt, "control_dt_s": .005, "duration_s": DURATION,
            "seed": 301, "force_mode": mode, "solver": "TGS", "capacity": CAPACITY,
            "ground_kind": "stationary-kinematic", "model": asdict(Model()),
            "contact": contact_configuration(), "wind": asdict(wind_model()),
            "timing": "preceding-physics-interval", "measurement": "signed-diagnostic-only"}


def capture_details(view):
    # Own the arrays before the friction call overwrites shared count/index buffers.
    forces, points, normals, gaps, counts, starts = [x.numpy().copy() for x in view.get_contact_data(dt=1.)]
    count, start = int(counts.reshape(-1)[0]), int(starts.reshape(-1)[0])
    require(counts.size == starts.size == 1 and 0 <= count < CAPACITY and start >= 0
            and start+count <= len(forces), "contact buffer bounds")
    contacts = [[float(forces[i].reshape(-1)[0]), *map(float, points[i]),
                 *map(float, normals[i]), float(gaps[i].reshape(-1)[0])]
                for i in range(start, start+count)]
    forces, points, counts, starts = [x.numpy().copy() for x in view.get_friction_data(dt=1.)]
    count, start = int(counts.reshape(-1)[0]), int(starts.reshape(-1)[0])
    require(counts.size == starts.size == 1 and 0 <= count < CAPACITY and start >= 0
            and start+count <= len(forces), "friction buffer bounds")
    anchors = [[*map(float, forces[i]), *map(float, points[i])] for i in range(start, start+count)]
    return contacts, anchors


def measurements(initial_velocity, rows, dt):
    previous = initial_velocity
    traces = []
    for row in rows:
        normal = [sum(c[0]*c[4+a] for c in row["contacts"]) for a in range(3)]
        friction = [sum(c[a] for c in row["anchors"]) for a in range(3)]
        residual = [Model().mass*(row["velocity"][a]-previous[a])
                    -dt*(row["applied"][a]-(Model().mass*Model().gravity if a == 2 else 0))
                    -normal[a]-friction[a] for a in range(3)]
        traces.append({"time_s": row["time_s"], "normal_impulse": normal,
            "friction_impulse": friction, "residual": residual,
            "normal_error_ns": math.dist(normal, [dt*v for v in row["normal"]]),
            "filter_error_ns": dt*math.dist(row["normal"], row["filtered"]),
            "friction_error_ns": math.dist(friction, [dt*v for v in row["friction"]]),
            "clearance_m": clearance(row["position"], row["quaternion"]),
            "negative": row["normal"][2] < -1e-6 or any(c[0] < -1e-9 for c in row["contacts"])})
        previous = row["velocity"]
    return traces


def summary(traces, rows):
    bad = [r for r in traces if r["negative"]]
    return {"intervals": len(rows), "negative_intervals": len(bad),
        "first_negative_s": bad[0]["time_s"] if bad else None,
        "minimum_normal_z_n": min(r["normal"][2] for r in rows),
        "minimum_contact_impulse_ns": min((c[0] for r in rows for c in r["contacts"]), default=0.),
        "momentum_rms_ns": math.sqrt(sum(sum(v*v for v in r["residual"]) for r in traces)/len(traces)),
        "peak_normal_error_ns": max(r["normal_error_ns"] for r in traces),
        "peak_filter_error_ns": max(r["filter_error_ns"] for r in traces),
        "peak_friction_error_ns": max(r["friction_error_ns"] for r in traces),
        "peak_contacts": max(len(r["contacts"]) for r in rows),
        "peak_anchors": max(len(r["anchors"]) for r in rows)}


def validate(data):
    keys(data, {"schema_version", "kind", "backend", "configuration", "source", "versions",
                "controller_binary_sha256", "repeat", "initial_velocity", "rows", "summary"})
    require(type(data["schema_version"]) is int and data["schema_version"] == 1 and data["kind"] == KIND
            and data["backend"] == "isaacsim_physx", "invalid contact probe identity")
    cfg = data["configuration"]
    require(isinstance(cfg, dict) and cfg.get("physics_dt_s") in TIMESTEPS and cfg.get("force_mode") in MODES,
            "invalid probe settings")
    dt = cfg["physics_dt_s"]
    require(encoded(cfg) == encoded(configuration(dt, cfg["force_mode"])), "unsupported probe configuration")
    require(type(data["repeat"]) is int and data["repeat"] in (1, 2), "invalid probe repeat")
    src = data["source"]
    keys(src, {"source_commit", "source_dirty", "source_tree_sha256", "lock_sha256"})
    require(src["source_dirty"] is False and isinstance(src["source_commit"], str)
            and re.fullmatch(r"[0-9a-f]{40}", src["source_commit"]), "probe requires clean source")
    for value in (src["source_tree_sha256"], src["lock_sha256"], data["controller_binary_sha256"]):
        require(isinstance(value, str) and HASH.fullmatch(value), "invalid probe digest")
    keys(data["versions"], {"isaacsim", "isaaclab", "torch"})
    require(all(isinstance(v, str) and re.fullmatch(r"[0-9][a-zA-Z0-9.+-]{0,31}", v)
                for v in data["versions"].values()), "invalid probe versions")
    vector(data["initial_velocity"], 3)
    require(data["initial_velocity"] == [0., 0., 0.], "invalid probe initial velocity")
    rows = data["rows"]
    require(isinstance(rows, list) and len(rows) == round(DURATION/dt), "incomplete contact probe")
    for i, row in enumerate(rows):
        keys(row, {"time_s", "position", "quaternion", "velocity", "applied", "normal", "filtered", "friction", "contacts", "anchors"})
        require(finite(row["time_s"]) and abs(row["time_s"]-(i+1)*dt) < 1e-9, "invalid probe cadence")
        for field in ("position", "velocity", "applied", "normal", "filtered", "friction", "quaternion"):
            vector(row[field], 4 if field == "quaternion" else 3)
            require(max(abs(v) for v in row[field]) <= 10000, "probe value out of bounds")
        require(abs(math.hypot(*row["quaternion"])-1) < 1e-6, "invalid probe attitude")
        for field, width in (("contacts", 8), ("anchors", 6)):
            require(isinstance(row[field], list) and len(row[field]) < CAPACITY, "probe buffer saturated")
            for contact in row[field]:
                vector(contact, width)
                require(max(abs(v) for v in contact) <= 10000, "invalid probe contact")
                if field == "contacts":
                    require(abs(math.hypot(*contact[4:7])-1) < .001, "invalid geometric normal")
    traces = measurements(data["initial_velocity"], rows, dt)
    require(encoded(data["summary"]) == encoded(summary(traces, rows)), "probe summary mismatch")
    return traces


def write_probe(output, rows, source, versions, binary, dt, mode, repeat):
    data = {"schema_version": 1, "kind": KIND, "backend": "isaacsim_physx",
            "configuration": configuration(dt, mode), "source": source, "versions": versions,
            "controller_binary_sha256": binary, "repeat": repeat, "initial_velocity": [0., 0., 0.], "rows": rows,
            "summary": summary(measurements([0., 0., 0.], rows, dt), rows)}
    validate(data)
    (output/"result.json").write_bytes(encoded(data))


def read_probe(directory):
    path = Path(directory)/"result.json"
    require(not path.is_symlink() and not Path(directory).is_symlink(), "symlink probe forbidden")
    data = load_json(path, limit=16*1024*1024)
    validate(data)
    return data


def export(sessions, destination):
    require(len(sessions) == 12, "probe matrix requires twelve runs")
    data = [read_probe(p) for p in sessions]
    first = data[0]
    require(all(all(r[k] == first[k] for k in ("source", "versions", "controller_binary_sha256")) for r in data),
            "probe matrix provenance differs")
    identity = lambda r: (r["configuration"]["physics_dt_s"], r["configuration"]["force_mode"], r["repeat"])
    require({identity(r) for r in data} == {(dt, mode, repeat) for dt in TIMESTEPS for mode in MODES for repeat in (1, 2)},
            "missing or duplicate probe case")
    comparisons = []
    for dt in TIMESTEPS:
        for mode in MODES:
            a, b = sorted((r for r in data if identity(r)[:2] == (dt, mode)), key=lambda r: r["repeat"])
            comparisons.append({"physics_dt_s": dt, "force_mode": mode,
                "identical_rows": encoded(a["rows"]) == encoded(b["rows"]),
                "peak_position_difference_m": max(math.dist(x["position"], y["position"]) for x, y in zip(a["rows"], b["rows"])),
                "peak_velocity_difference_m_s": max(math.dist(x["velocity"], y["velocity"]) for x, y in zip(a["rows"], b["rows"]))})
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    cases = []
    for r in sorted(data, key=identity):
        dt, mode, repeat = identity(r)
        name = f"{mode}-dt{round(dt*1e6)}-r{repeat}"
        content = encoded(r)
        (destination/(name+".json")).write_bytes(content)
        cases.append({"id": name, "sha256": sha256(content), "physics_dt_s": dt, "force_mode": mode,
                      "repeat": repeat, "summary": r["summary"]})
    index = {"schema_version": 1, "kind": "contact_probe_index", "source": first["source"],
             "versions": first["versions"], "controller_binary_sha256": first["controller_binary_sha256"],
             "cases": cases, "repeatability": comparisons}
    content = encoded(index)
    (destination/"index.json").write_bytes(content)
    return {"cases": 12, "index_sha256": sha256(content), "repeatability": comparisons}
