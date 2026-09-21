"""Independent physics references and strict verification of measured traces."""
from dataclasses import asdict
import math
from pathlib import Path
import re
import subprocess

from .contracts import finite, load_json
from .evidence import keys, require
from .frames import rotate, vector
from .mission import clearance, configuration as contact_configuration
from .physics import Model, State
from .rotors import RotorModel
from .simulation import ROOT, encoded, sha256
from .wind import WindModel

TIMESTEPS = (.005, .0025, .00125)
CASES = {"free-fall": .25, "tilted-thrust": .25, "yaw-torque": .5,
         "rotor-step": .3, "drag-coast": 2., "floor-drop": 2.}
FIELDS = {"time_s", "position_m", "velocity_m_s", "quaternion_wxyz", "rates_rad_s",
          "force_enu_n", "torque_flu_nm", "rotor_thrust_n", "contact_normal_force_n"}
KIND = "isaac_physics_accuracy"


def configuration(contact_mode="predictive-margin", substep_forces=True):
    require(contact_mode in ("discrete", "speculative", "predictive-margin"), "unsupported contact configuration")
    contact = contact_configuration()
    if contact_mode == "predictive-margin":
        contact["contact_offset_m"] = .01
    return {"model": asdict(Model()), "rotors": asdict(RotorModel()),
            "contact": contact, "drag": asdict(WindModel(pressure_centre_m=(0., 0., 0.))),
            "solver": {"type": "TGS", "position_iterations": 4, "velocity_iterations": 1,
                       "gyroscopic_forces": True, "linear_damping": 0., "angular_damping": 0., "sleep_threshold": 0.,
                       **({"external_forces_every_iteration": False} if substep_forces is False else {}),
                       **({"speculative_ccd": True} if contact_mode == "speculative" else {})},
            "force_timing": "sample-i-input-applied-over-next-interval",
            "contact_timing": "sample-i-normal-measured-over-preceding-interval"}


def initial_state(case):
    require(case in CASES, "unsupported physics case")
    return State(position=(0., 0., .55 if case == "floor-drop" else 1.5),
                 velocity=(5., 0., 0.) if case == "drag-coast" else (0.,)*3,
                 quaternion=(math.cos(math.pi/12), math.sin(math.pi/12), 0., 0.) if case == "tilted-thrust" else (1., 0., 0., 0.))


def reference(case, t):
    """Continuous solutions; no reuse of the numerical advance or wrench code."""
    s, g = initial_state(case), Model().gravity
    x, y, z = s.position
    v, q, w = s.velocity, s.quaternion, s.rates
    if case in ("free-fall", "floor-drop"):
        z -= .5*g*t*t; v = (0., 0., -g*t)
    elif case == "tilted-thrust":
        a = -g*math.tan(math.pi/6)
        y = .5*a*t*t; v = (0., a*t, 0.)
    elif case == "yaw-torque":
        q = (math.cos(t*t/4), 0., 0., math.sin(t*t/4)); w = (0., 0., t)
    elif case == "rotor-step":
        tau, force = .03, 12.
        lag = -math.expm1(-t/tau)
        z += .5*(force-g)*t*t-force*tau*(t-tau*lag)
        v = (0., 0., (force-g)*t-force*tau*lag)
    elif case == "drag-coast":
        k = .5*1.225*.06
        x = math.log1p(k*5*t)/k; v = (5/(1+k*5*t), 0., 0.)
    return State((x, y, z), v, q, w)


def inputs(case, state, motors, dt):
    force, torque = (0.,)*3, (0.,)*3
    if case == "tilted-thrust":
        force = rotate(state.quaternion, (0., 0., Model().gravity/math.cos(math.pi/6)))
    elif case == "yaw-torque":
        force = rotate(state.quaternion, (0., 0., Model().gravity)); torque = (0., 0., .04)
    elif case == "rotor-step":
        motors = RotorModel().advance(motors, (3.,)*4, dt)
        thrust, torque = RotorModel().wrench(motors)
        force = rotate(state.quaternion, (0., 0., thrust))
    elif case == "drag-coast":
        drag, torque = WindModel(pressure_centre_m=(0., 0., 0.)).wrench(state.velocity, state.quaternion, state.rates, (0.,)*3)
        force = (drag[0], drag[1], drag[2]+Model().gravity)
    return force, torque, motors


def angle_error(q, expected):
    # Chord distance is stable for tiny differences and quaternion sign changes.
    d = min(math.dist(q, expected), math.dist(q, tuple(-v for v in expected)))
    return 4*math.asin(min(1., d/2))


def measurements(case, samples, dt):
    result = {"samples": len(samples)}
    if case != "floor-drop":
        expected = [reference(case, s["time_s"]) for s in samples]
        for field, attr in (("position_m", "position"), ("velocity_m_s", "velocity"), ("rates_rad_s", "rates")):
            result["peak_"+field+"_error"] = max(math.dist(s[field], getattr(r, attr)) for s, r in zip(samples, expected))
        result["peak_attitude_error_rad"] = max(angle_error(s["quaternion_wxyz"], r.quaternion) for s, r in zip(samples, expected))
        result["peak_contact_normal_n"] = max(math.hypot(*s["contact_normal_force_n"]) for s in samples)
    energy = [.5*sum(v*v for v in s["velocity_m_s"]) for s in samples]
    if case == "drag-coast":
        result["peak_kinetic_energy_increase_j"] = max(0., max(b-a for a, b in zip(energy, energy[1:])))
    if case == "floor-drop":
        touch = next((s["time_s"] for s in samples if s["contact_normal_force_n"][2] > .1), None)
        result["first_contact_s"] = touch
        result["contact_time_error_s"] = abs(touch-math.sqrt(1/Model().gravity)) if touch is not None else None
        result["max_penetration_m"] = max(0., -min(clearance(s["position_m"], s["quaternion_wxyz"]) for s in samples))
        result["peak_vertical_impulse_residual_ns"] = max(abs(
            b["velocity_m_s"][2]-a["velocity_m_s"][2]
            -(a["force_enu_n"][2]-Model().gravity+b["contact_normal_force_n"][2])*dt)
            for a, b in zip(samples, samples[1:]))
        energy = [e+Model().gravity*(s["position_m"][2]-.05)
                  +.5*sum(i*w*w for i, w in zip(Model().inertia, s["rates_rad_s"])) for e, s in zip(energy, samples)]
        result["peak_mechanical_energy_gain_j"] = max(0., max(energy)-energy[0])
        resting = [s for s in samples if s["time_s"] >= 1.5]
        result["rest_height_error_m"] = max(abs(s["position_m"][2]-.05) for s in resting)
        result["rest_speed_m_s"] = max(math.hypot(*s["velocity_m_s"]) for s in resting)
        result["rest_mean_normal_n"] = sum(s["contact_normal_force_n"][2] for s in resting)/len(resting)
    return result


def passes(case, m, dt):
    r = dt/.005
    if case == "floor-drop":
        return (m["contact_time_error_s"] is not None and m["contact_time_error_s"] <= 2*dt+.002
                and m["max_penetration_m"] <= .003 and m["peak_vertical_impulse_residual_ns"] <= .001
                and m["peak_mechanical_energy_gain_j"] <= .02 and m["rest_height_error_m"] <= .001
                and m["rest_speed_m_s"] <= .001 and abs(m["rest_mean_normal_n"]-Model().gravity) <= .01*Model().gravity)
    position, velocity, attitude, rate = .02*r+.00001, .001, .001, .001
    if case == "yaw-torque": position, attitude, rate = .0002, .0015*r+.00002, .0005
    if case == "rotor-step": position, velocity = .01*r+.0001, .04*r+.0001
    if case == "drag-coast": position, velocity = .02*r+.0001, .004*r+.0001
    return (m["peak_position_m_error"] <= position and m["peak_velocity_m_s_error"] <= velocity
            and m["peak_attitude_error_rad"] <= attitude and m["peak_rates_rad_s_error"] <= rate
            and m["peak_contact_normal_n"] <= .0001
            and m.get("peak_kinetic_energy_increase_j", 0.) <= .00001)


def provenance():
    files = sorted([* (ROOT/"src/aeroloop").glob("*.py"), ROOT/"tools/isaac_physics.py", ROOT/"tools/physics_report.py"])
    return {"source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "source_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
            "source_tree_sha256": sha256(b"".join(p.relative_to(ROOT).as_posix().encode()+b"\0"+p.read_bytes()+b"\0" for p in files)),
            "lock_sha256": sha256((ROOT/"versions.lock.json").read_bytes())}


def read_physics(directory):
    directory = Path(directory)
    result = load_json(directory/"result.json")
    keys(result, {"schema_version", "kind", "backend", "dt_s", "configuration", "provenance", "versions",
                  "wall_time_s", "checksums", "results", "passed", "trials"})
    require(type(result["schema_version"]) is int and result["schema_version"] == 1
            and result["kind"] == KIND and result["backend"] == "isaacsim_physx", "invalid physics identity")
    dt = result["dt_s"]
    require(finite(dt) and dt in TIMESTEPS, "unsupported physics timestep")
    # Retain both development failures without rewriting their original settings.
    require(encoded(result["configuration"]) in (encoded(configuration(substep_forces=False)), *(encoded(configuration(mode, True)) for mode in
            ("discrete", "speculative", "predictive-margin"))), "unsupported physics configuration")
    p = result["provenance"]
    keys(p, {"source_commit", "source_dirty", "source_tree_sha256", "lock_sha256"})
    require(type(p["source_dirty"]) is bool and isinstance(p["source_commit"], str)
            and re.fullmatch(r"[0-9a-f]{40}", p["source_commit"]), "invalid source provenance")
    for key in ("source_tree_sha256", "lock_sha256"):
        require(isinstance(p[key], str) and re.fullmatch(r"[0-9a-f]{64}", p[key]), "invalid source hash")
    keys(result["versions"], {"isaacsim", "isaaclab", "torch"})
    require(all(isinstance(v, str) and re.fullmatch(r"[0-9][a-zA-Z0-9.+-]{0,31}", v)
                for v in result["versions"].values()), "invalid simulator version")
    require(finite(result["wall_time_s"]) and result["wall_time_s"] > 0, "invalid physics timing")
    keys(result["checksums"], {case+".json" for case in CASES})
    rows, traces = [], {}
    for case, duration in CASES.items():
        path = directory/(case+".json")
        require(path.stat().st_size <= 8*1024*1024, "oversized physics trace")
        require(sha256(path.read_bytes()) == result["checksums"][path.name], "physics checksum mismatch")
        trace = load_json(path, limit=8*1024*1024)
        keys(trace, {"schema_version", "kind", "case", "dt_s", "samples"})
        require(type(trace["schema_version"]) is int and trace["schema_version"] == 1 and trace["kind"] == "measured_physics_trace"
                and trace["case"] == case and trace["dt_s"] == dt, "physics trace identity mismatch")
        samples, motors = trace["samples"], (0.,)*4
        require(isinstance(samples, list) and len(samples) == round(duration/dt)+1, "incomplete physics trace")
        for i, s in enumerate(samples):
            keys(s, FIELDS)
            require(finite(s["time_s"]) and abs(s["time_s"]-i*dt) <= 1e-9, "unordered physics samples")
            for field in FIELDS-{"time_s"}:
                vector(s[field], 4 if field in ("quaternion_wxyz", "rotor_thrust_n") else 3)
            require(abs(math.hypot(*s["quaternion_wxyz"])-1) <= 1e-6, "invalid physics attitude")
            require(s["contact_normal_force_n"][2] >= -1e-6 and max(abs(v) for v in s["contact_normal_force_n"][:2]) <= 1e-4,
                    "invalid floor normal")
            state = State(tuple(s["position_m"]), tuple(s["velocity_m_s"]), tuple(s["quaternion_wxyz"]), tuple(s["rates_rad_s"]))
            if i == 0:
                initial = initial_state(case)
                require(all(math.dist(getattr(state, k), getattr(initial, k)) <= 1e-6 for k in ("position", "velocity", "quaternion", "rates"))
                        and s["contact_normal_force_n"] == [0., 0., 0.], "physics reset mismatch")
            force, torque, motors = inputs(case, state, motors, dt)
            require(all(math.dist(s[k], expected) <= 1e-9 for k, expected in (
                ("force_enu_n", force), ("torque_flu_nm", torque), ("rotor_thrust_n", motors))), "physics input mismatch")
        m = measurements(case, samples, dt)
        rows.append({"case": case, "metrics": m, "passed": passes(case, m, dt)})
        traces[case] = samples
    require(encoded(result["results"]) == encoded(rows), "physics measurements or outcome mismatch")
    require(type(result["trials"]) is int and result["trials"] == len(CASES)
            and type(result["passed"]) is int and result["passed"] == sum(row["passed"] for row in rows), "false physics aggregate")
    return result, traces


def report(directories):
    require(len(directories) == 2*len(TIMESTEPS), "report requires three timesteps for both force modes")
    runs = [read_physics(p)[0] for p in directories]
    require(runs[0]["provenance"]["source_dirty"] is False, "report requires clean source")
    require(all(encoded(r["configuration"]) in (encoded(configuration()), encoded(configuration(substep_forces=False)))
                for r in runs), "report requires predictive contact margin")
    require(all(r["provenance"] == runs[0]["provenance"] and r["versions"] == runs[0]["versions"] for r in runs), "physics suite provenance differs")
    integrations = []
    for mode in (True, False):
        group = sorted((r for r in runs if r["configuration"]["solver"].get("external_forces_every_iteration", True) == mode), key=lambda r: -r["dt_s"])
        require(tuple(r["dt_s"] for r in group) == TIMESTEPS, "missing or duplicate force-mode/timestep")
        refinement = []
        for case in CASES:
            if case == "floor-drop": continue
            metric = "peak_attitude_error_rad" if case == "yaw-torque" else "peak_position_m_error"
            errors = [next(row["metrics"][metric] for row in r["results"] if row["case"] == case) for r in group]
            refinement.append({"case": case, "metric": metric, "errors": errors,
                               "passed": all(b <= .65*a+.00002 for a, b in zip(errors, errors[1:]))})
        integrations.append({"force_mode": "per-iteration" if mode else "per-step", "configuration": group[0]["configuration"],
            "refinement": refinement, "passed": sum(r["passed"] for r in group),
            "accepted": all(r["passed"] == 6 for r in group) and all(r["passed"] for r in refinement),
            "timesteps": [{k: r[k] for k in ("dt_s", "wall_time_s", "checksums", "results")} for r in group]})
    return {"schema_version": 1, "kind": "isaac_physics_accuracy_summary", "backend": "isaacsim_physx",
            "provenance": runs[0]["provenance"], "versions": runs[0]["versions"],
            "trials": 36, "passed": sum(r["passed"] for r in runs), "integrations": integrations,
            "accepted": all(g["accepted"] for g in integrations),
            "limitations": ["Numerical implementation verification, not physical calibration", "Force-isolation cases, not closed-loop flight convergence",
                            "Illustrative COM drag and cuboid impact; no propeller or ground-effect model",
                            "Per-step force mode is deprecated by PhysX and is diagnostic only"]}
