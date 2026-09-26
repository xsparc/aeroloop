"""Analytical protocol fixtures; these tests do not represent GPU measurements."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop import yaw_audit as audit
from aeroloop.contracts import ValidationError, load_json
from aeroloop.isaac_process import run_worker
from aeroloop.physics import Model
from aeroloop.simulation import encoded, sha256


def fixture(directory, dt=.005, iterations=4):
    directory.mkdir()
    rows, hashes = [], {}
    for case, (_, torque) in audit.CASES.items():
        samples = []
        for i in range(round(.5/dt)+1):
            t = round(i*dt, 9)
            angle, rate = audit.reference(case, t)
            q = [math.cos(angle/2), 0., 0., math.sin(angle/2)]
            samples.append({"time_s": t, "position_m": [0., 0., 1.5], "direct_position_m": [0., 0., 1.5],
                "velocity_m_s": [0., 0., 0.], "quaternion_wxyz": q, "direct_quaternion_wxyz": q,
                "repeat_quaternion_wxyz": q, "rates_rad_s": [0., 0., rate], "direct_rates_rad_s": [0., 0., rate],
                "force_flu_n": [0., 0., Model().gravity], "torque_flu_nm": [0., 0., torque]})
        data = encoded({"schema_version": 1, "kind": "measured_yaw_trace", "case": case, "dt_s": dt, "samples": samples})
        (directory/(case+".json")).write_bytes(data); hashes[case+".json"] = sha256(data)
        metrics = audit.measurements(case, samples, dt)
        rows.append({"case": case, "metrics": metrics, "passed": audit.passes(metrics)})
    result = {"schema_version": 1, "kind": audit.KIND, "backend": "isaacsim_physx", "dt_s": dt,
        "configuration": audit.configuration(iterations), "provenance": {"source_commit": "a"*40,
        "source_dirty": False, "source_tree_sha256": "b"*64, "lock_sha256": "c"*64},
        "versions": {"isaacsim": "6.1", "isaaclab": "17.0", "torch": "2.11"}, "wall_time_s": 1.,
        "checksums": hashes, "results": rows, "passed": 5, "trials": 5}
    (directory/"result.json").write_bytes(encoded(result))
    return result


def replace_trace(path, case, samples, result):
    trace = load_json(path/(case+".json")); trace["samples"] = samples
    content = encoded(trace); (path/(case+".json")).write_bytes(content)
    result["checksums"][case+".json"] = sha256(content)
    row = next(row for row in result["results"] if row["case"] == case)
    row["metrics"] = audit.measurements(case, samples, result["dt_s"])
    row["passed"] = audit.passes(row["metrics"])
    result["passed"] = sum(row["passed"] for row in result["results"])
    (path/"result.json").write_bytes(encoded(result))


class YawAuditTests(unittest.TestCase):
    def test_independent_endpoint_values_derivative_and_quaternion_sign(self):
        expected = {"spin-slow": (.025, .05), "spin-positive": (.25, .5), "spin-negative": (-.25, -.5),
                    "torque-positive": (.125, .5), "torque-negative": (-.125, -.5)}
        for case, endpoint in expected.items():
            self.assertEqual(audit.reference(case, .5), endpoint)
            h, t = 1e-5, .2
            self.assertAlmostEqual((audit.reference(case, t+h)[0]-audit.reference(case, t-h)[0])/(2*h), audit.reference(case, t)[1], places=10)
            q = [math.cos(endpoint[0]/2), 0., 0., math.sin(endpoint[0]/2)]
            self.assertAlmostEqual(audit.yaw(q), endpoint[0])
            self.assertEqual(audit.yaw(q), audit.yaw([-v for v in q]))

    def test_complete_matrix_and_original_refinement_not_hidden_by_absolute_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp)/str(i) for i in range(6)]
            results = [fixture(p, audit.TIMESTEPS[i%3], 1 if i<3 else 4) for i,p in enumerate(paths)]
            self.assertTrue(audit.report(paths)["default_yaw_refinement_passed"])
            result, traces = audit.read_yaw(paths[-1])
            samples = traces["torque-positive"]
            # Full-rate synthetic bias passes absolute diagnostic limits but fails refinement.
            for s in samples:
                angle = audit.reference("torque-positive", s["time_s"])[0]+.001*s["time_s"]
                q = [math.cos(angle/2), 0., 0., math.sin(angle/2)]
                for k in ("quaternion_wxyz", "direct_quaternion_wxyz", "repeat_quaternion_wxyz"): s[k] = q
            replace_trace(paths[-1], "torque-positive", samples, result)
            summary = audit.report(paths)
            self.assertEqual(summary["passed"], 30)
            self.assertFalse(summary["default_yaw_refinement_passed"])
            with self.assertRaises(ValidationError): audit.report(paths[:3])
            with self.assertRaises(ValidationError): audit.report([paths[0], paths[0], *paths[2:]])
            results[0]["provenance"]["source_dirty"] = True
            (paths[0]/"result.json").write_bytes(encoded(results[0]))
            with self.assertRaises(ValidationError): audit.report(paths)

    def test_read_channels_and_rate_integral_reveal_misalignment(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"case"; result = fixture(path)
            _, traces = audit.read_yaw(path)
            samples = traces["spin-positive"]
            self.assertLess(audit.measurements("spin-positive", samples, .005)["peak_rate_integral_residual_rad"], 1e-14)
            samples[-1]["direct_quaternion_wxyz"] = samples[-2]["direct_quaternion_wxyz"]
            replace_trace(path, "spin-positive", samples, result)
            verified, _ = audit.read_yaw(path)
            self.assertEqual(verified["passed"], 4)
            self.assertGreater(verified["results"][1]["metrics"]["peak_read_angle_difference_rad"], .002)

    def test_corruption_private_fields_missing_samples_and_false_success_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"case"; original = fixture(path)
            trace = load_json(path/"torque-positive.json")
            for mutate in (lambda t: t["samples"].pop(), lambda t: t.update(host="private"),
                           lambda t: t["samples"][1].update(time_s=0.),
                           lambda t: t["samples"][2].update(torque_flu_nm=[0., 0., .05])):
                changed = copy.deepcopy(trace); mutate(changed); content = encoded(changed)
                (path/"torque-positive.json").write_bytes(content)
                result = copy.deepcopy(original); result["checksums"]["torque-positive.json"] = sha256(content)
                (path/"result.json").write_bytes(encoded(result))
                with self.assertRaises(ValidationError): audit.read_yaw(path)
            (path/"torque-positive.json").write_bytes(encoded(trace))
            for mutate in (lambda r: r.update(passed=4), lambda r: r["results"].pop(),
                           lambda r: r["provenance"].update(host="private"),
                           lambda r: r["results"][0]["metrics"].update(peak_yaw_error_rad=1.)):
                changed = copy.deepcopy(original); mutate(changed); (path/"result.json").write_bytes(encoded(changed))
                with self.assertRaises(ValidationError): audit.read_yaw(path)

    def test_initial_development_configuration_is_readable_but_not_final(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp)/str(i) for i in range(6)]
            results = [fixture(p, audit.TIMESTEPS[i%3], 1 if i<3 else 4) for i,p in enumerate(paths)]
            results[0]["configuration"] = audit.configuration(1, legacy_body_rate=True)
            (paths[0]/"result.json").write_bytes(encoded(results[0]))
            audit.read_yaw(paths[0])
            with self.assertRaises(ValidationError): audit.report(paths)

    def test_launcher_requires_a_verified_completion_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/"worker"
            with patch("aeroloop.isaac_process._execute", side_effect=lambda command, timeout: fixture(output)) as execute:
                result = run_worker(Path(sys.executable), "yaw", output, ["--physics-dt", ".005"])
            self.assertEqual(result["passed"], 5)
            self.assertTrue(execute.call_args.args[0][1].endswith("isaac_yaw.py"))
            with self.assertRaises(ValidationError): run_worker(Path(sys.executable), "yaw", output)
