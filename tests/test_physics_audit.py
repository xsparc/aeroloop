"""Analytical protocol fixtures only; these tests never claim measured GPU evidence."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aeroloop import physics_audit as audit
from aeroloop.contracts import ValidationError, load_json
from aeroloop.physics import Model, State
from aeroloop.simulation import encoded, sha256


def fixture(directory, dt, substep_forces=True):
    directory.mkdir()
    rows, hashes = [], {}
    for case, duration in audit.CASES.items():
        samples, motors, previous_vz = [], (0.,)*4, 0.
        for i in range(round(duration/dt)+1):
            t = round(i*dt, 9)
            s = audit.reference(case, t)
            normal = (0.,)*3
            if case == "floor-drop":
                if s.position[2] <= .05:
                    s = State(position=(0., 0., .05))
                normal = (0., 0., max(0., (s.velocity[2]-previous_vz)/dt+Model().gravity)) if i else (0.,)*3
                previous_vz = s.velocity[2]
            force, torque, motors = audit.inputs(case, s, motors, dt)
            samples.append({"time_s": t, "position_m": s.position, "velocity_m_s": s.velocity,
                "quaternion_wxyz": s.quaternion, "rates_rad_s": s.rates, "force_enu_n": force,
                "torque_flu_nm": torque, "rotor_thrust_n": motors, "contact_normal_force_n": normal})
        data = encoded({"schema_version": 1, "kind": "measured_physics_trace", "case": case, "dt_s": dt, "samples": samples})
        (directory/(case+".json")).write_bytes(data); hashes[case+".json"] = sha256(data)
        m = audit.measurements(case, samples, dt)
        rows.append({"case": case, "metrics": m, "passed": audit.passes(case, m, dt)})
    result = {"schema_version": 1, "kind": audit.KIND, "backend": "isaacsim_physx", "dt_s": dt,
              "configuration": audit.configuration(substep_forces=substep_forces), "provenance": {"source_commit": "a"*40, "source_dirty": False,
              "source_tree_sha256": "b"*64, "lock_sha256": "c"*64}, "versions": {"isaacsim": "6.1", "isaaclab": "17.0", "torch": "2.11"},
              "wall_time_s": 1., "checksums": hashes, "results": rows, "passed": sum(r["passed"] for r in rows), "trials": 6}
    (directory/"result.json").write_bytes(encoded(result))
    return result


class PhysicsAuditTests(unittest.TestCase):
    def test_reference_derivatives_match_independent_acceleration(self):
        h, t = 1e-5, .15
        for case in audit.CASES:
            middle, before, after = (audit.reference(case, at) for at in (t, t-h, t+h))
            for axis in range(3):
                self.assertAlmostEqual((after.position[axis]-before.position[axis])/(2*h), middle.velocity[axis], places=7)
            acceleration = tuple((a-b)/(2*h) for a, b in zip(after.velocity, before.velocity))
            expected = {
                "free-fall": (0., 0., -Model().gravity), "floor-drop": (0., 0., -Model().gravity),
                "tilted-thrust": (0., -Model().gravity/math.sqrt(3), 0.), "yaw-torque": (0.,)*3,
                "rotor-step": (0., 0., 12*(1-math.exp(-t/.03))-Model().gravity),
                "drag-coast": (-.5*1.225*.06*middle.velocity[0]**2, 0., 0.)}[case]
            for a, b in zip(acceleration, expected): self.assertAlmostEqual(a, b, places=7)
        q = audit.reference("yaw-torque", .5).quaternion
        self.assertAlmostEqual(2*math.atan2(q[3], q[0]), .125)
        self.assertEqual(audit.angle_error(q, tuple(-x for x in q)), 0.)

    def test_motor_force_is_for_next_interval_and_rotated_thrust_has_correct_sign(self):
        motors = (0.,)*4
        for i in range(5):
            force, _, motors = audit.inputs("rotor-step", State(), motors, .005)
            self.assertAlmostEqual(force[2], 12*(1-math.exp(-(i+1)*.005/.03)), places=12)
        force, _, _ = audit.inputs("tilted-thrust", audit.initial_state("tilted-thrust"), (0.,)*4, .005)
        self.assertAlmostEqual(force[1], -Model().gravity/math.sqrt(3))
        self.assertAlmostEqual(force[2], Model().gravity)

    def test_complete_matrix_and_contact_impulse_timing(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp)/str(i) for i in range(6)]
            for i, path in enumerate(paths): fixture(path, audit.TIMESTEPS[i%3], i < 3)
            result = audit.report(paths)
            self.assertEqual((result["trials"], result["passed"], result["accepted"]), (36, 36, True))
            _, traces = audit.read_physics(paths[0])
            drop = traces["floor-drop"]
            wrong = copy.deepcopy(drop)
            for i in range(1, len(wrong)):
                wrong[i]["contact_normal_force_n"] = drop[i-1]["contact_normal_force_n"]
            self.assertGreater(audit.measurements("floor-drop", wrong, .005)["peak_vertical_impulse_residual_ns"], 1.)
            with self.assertRaises(ValidationError): audit.report(paths[:2])
            with self.assertRaises(ValidationError): audit.report([paths[0], paths[0], *paths[2:]])

    def test_rejects_tampering_even_with_updated_trace_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"run"; original = fixture(path, .005)
            trace = load_json(path/"rotor-step.json")
            for mutate in (lambda t: t["samples"].pop(), lambda t: t["samples"][1].update(force_enu_n=[0, 0, 100]),
                           lambda t: t.update(private_host="not-public"), lambda t: t["samples"][2].update(time_s=0)):
                changed = copy.deepcopy(trace); mutate(changed); data = encoded(changed)
                (path/"rotor-step.json").write_bytes(data)
                result = copy.deepcopy(original); result["checksums"]["rotor-step.json"] = sha256(data)
                (path/"result.json").write_bytes(encoded(result))
                with self.assertRaises(ValidationError): audit.read_physics(path)
            (path/"rotor-step.json").write_bytes(encoded(trace))
            for mutate in (lambda r: r.update(passed=0), lambda r: r["results"].pop(),
                           lambda r: r["checksums"].update({"../private.json": "d"*64}),
                           lambda r: r["provenance"].update(private_host="not-public")):
                changed = copy.deepcopy(original); mutate(changed)
                (path/"result.json").write_bytes(encoded(changed))
                with self.assertRaises(ValidationError): audit.read_physics(path)

    def test_failed_cases_retained_and_no_dirty_or_mixed_provenance_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp)/str(i) for i in range(6)]
            results = [fixture(p, audit.TIMESTEPS[i%3], i < 3) for i, p in enumerate(paths)]
            trace = load_json(paths[0]/"free-fall.json")
            trace["samples"][-1]["position_m"][0] = 1.
            data = encoded(trace); (paths[0]/"free-fall.json").write_bytes(data)
            results[0]["checksums"]["free-fall.json"] = sha256(data)
            results[0]["results"][0].update(metrics=audit.measurements("free-fall", trace["samples"], .005), passed=False)
            results[0]["passed"] = 5
            (paths[0]/"result.json").write_bytes(encoded(results[0]))
            report = audit.report(paths)
            self.assertEqual(report["passed"], 35); self.assertFalse(report["accepted"])
            for key, value in (("source_dirty", True), ("source_commit", "d"*40)):
                changed = copy.deepcopy(results[2]); changed["provenance"][key] = value
                (paths[2]/"result.json").write_bytes(encoded(changed))
                with self.assertRaises(ValidationError): audit.report(paths)

    def test_refinement_failure_cannot_be_hidden_by_individual_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp)/str(i) for i in range(6)]
            for i, p in enumerate(paths):
                dt = audit.TIMESTEPS[i%3]
                r = fixture(p, dt, i < 3); t = load_json(p/"free-fall.json")
                t["samples"][-1]["position_m"][0] = .001
                data = encoded(t); (p/"free-fall.json").write_bytes(data)
                r["checksums"]["free-fall.json"] = sha256(data)
                r["results"][0]["metrics"] = audit.measurements("free-fall", t["samples"], dt)
                (p/"result.json").write_bytes(encoded(r))
            report = audit.report(paths)
            self.assertEqual(report["passed"], 36); self.assertFalse(report["accepted"])

    def test_worker_routes_physics_and_requires_verified_completion(self):
        from aeroloop.isaac_process import run_worker
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"run"
            def execute(command, timeout):
                self.assertEqual(Path(command[1]).name, "isaac_physics.py")
                fixture(path, .005)
            with patch("aeroloop.isaac_process._execute", side_effect=execute):
                self.assertEqual(run_worker("python", "physics", path)["passed"], 6)


if __name__ == "__main__":
    unittest.main()
