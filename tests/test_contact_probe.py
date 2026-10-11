import copy
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from aeroloop.contact_probe import configuration, measurements, summary, validate, export, read_probe, capture_details
from aeroloop.physics import Model
from aeroloop.simulation import encoded


def fixture(dt=.005, mode="per-iteration", repeat=1):
    row = {"time_s": dt, "position": [0., 0., .05], "quaternion": [1., 0., 0., 0.],
           "velocity": [0., 0., 0.], "applied": [0., 0., 0.], "normal": [0., 0., Model().gravity],
           "filtered": [0., 0., Model().gravity], "friction": [0., 0., 0.],
           "contacts": [[Model().gravity*dt, 0., 0., 0., 0., 0., 1., 0.]], "anchors": []}
    rows = [dict(copy.deepcopy(row), time_s=round((i+1)*dt, 9)) for i in range(round(3/dt))]
    return {"schema_version": 1, "kind": "isaac_contact_probe", "backend": "isaacsim_physx",
            "configuration": configuration(dt, mode), "repeat": repeat,
            "source": {"source_commit": "a"*40, "source_dirty": False, "source_tree_sha256": "b"*64, "lock_sha256": "c"*64},
            "versions": {"isaacsim": "6.1.0.0", "isaaclab": "17.0.2", "torch": "2.11.0+cu128"},
            "controller_binary_sha256": "d"*64, "initial_velocity": [0., 0., 0.],
            "rows": rows, "summary": summary(measurements([0., 0., 0.], rows, dt), rows)}


class ContactProbeTests(unittest.TestCase):
    def test_cli_rejects_silently_ignored_probe_options(self):
        tool = Path(__file__).resolve().parents[1]/"tools/isaac.py"
        for mode, options in (("contact", ["--seeds", "5"]), ("contact", ["--scenario", "hover"]),
                              ("flight", ["--repeat", "2"])):
            result = subprocess.run([sys.executable, str(tool), mode, "--output", "runs/unused-probe-test", *options],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("error:", result.stderr)

    def test_shared_contact_counts_copied_before_friction_read(self):
        class Buffer:
            def __init__(self, values): self.values = values
            def numpy(self): return self
            def copy(self): return Buffer(copy.deepcopy(self.values))
            def reshape(self, _):
                def flat(v):
                    return [n for c in v for n in flat(c)] if isinstance(v, list) else [v]
                return Buffer(flat(self.values))
            @property
            def size(self): return len(self.reshape(-1))
            def __len__(self): return len(self.values)
            def __iter__(self): return iter(self.values)
            def __getitem__(self, i):
                v = self.values[i]
                return Buffer(v) if isinstance(v, list) else v
        class View:
            count, start = Buffer([[1]]), Buffer([[0]])
            def get_contact_data(self, dt):
                self.count.values = [[1]]
                return Buffer([[-.01]]), Buffer([[1.,2.,3.]]), Buffer([[0.,0.,1.]]), Buffer([[.001]]), self.count, self.start
            def get_friction_data(self, dt):
                self.count.values = [[0]]
                return Buffer([[0.,0.,0.]]), Buffer([[0.,0.,0.]]), self.count, self.start
        contacts, anchors = capture_details(View())
        self.assertEqual(contacts, [[-.01, 1.,2.,3.,0.,0.,1.,.001]])
        self.assertEqual(anchors, [])

    def test_exact_signed_impulse_balance(self):
        row = fixture()["rows"][0]
        row.update(normal=[0., 0., -2.], filtered=[0., 0., -2.], friction=[3., 0., 0.],
                   applied=[1., 0., Model().gravity], velocity=[.02, 0., -.01],
                   contacts=[[-.01, 0., 0., 0., 0., 0., 1., 0.]], anchors=[[.015, 0., 0., 0., 0., 0.]])
        trace = measurements([0., 0., 0.], [row], .005)[0]
        self.assertTrue(trace["negative"])
        self.assertEqual(trace["residual"], [0., 0., 0.])
        self.assertEqual(trace["normal_error_ns"], 0.)
        self.assertEqual(trace["friction_error_ns"], 0.)
        self.assertEqual(trace["clearance_m"], 0.)

    def test_strict_probe_and_distinct_diagnostic_status(self):
        data = fixture()
        self.assertEqual(len(validate(data)), 600)
        self.assertNotIn("passed", data)
        for mutation in (lambda d: d["rows"].pop(), lambda d: d["rows"][1].update(time_s=.011),
                         lambda d: d["rows"][0].update(anchors=[[0.]*6]*64),
                         lambda d: d["source"].update(source_dirty=True),
                         lambda d: d["summary"].update(negative_intervals=1),
                         lambda d: d["rows"][0].update(velocity=[True, 0., 0.]),
                         lambda d: d["configuration"].update(seed=1)):
            bad = copy.deepcopy(data)
            mutation(bad)
            with self.assertRaises(ValueError): validate(bad)

    def test_matrix_export_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sessions = []
            for dt in (.005, .0025, .00125):
                for mode in ("per-iteration", "per-step"):
                    for repeat in (1, 2):
                        path = root/str(len(sessions))
                        path.mkdir()
                        (path/"result.json").write_bytes(encoded(fixture(dt, mode, repeat)))
                        sessions.append(path)
            result = export(sessions, root/"bundle")
            self.assertEqual(result["cases"], 12)
            self.assertTrue(all(r["identical_rows"] for r in result["repeatability"]))
            with self.assertRaises(ValueError): export(sessions[:-1], root/"partial")
            with self.assertRaises(ValueError): export([sessions[0]]*12, root/"duplicate")
            data = fixture()
            data["summary"]["intervals"] = 0
            (sessions[0]/"result.json").write_bytes(encoded(data))
            with self.assertRaises(ValueError): read_probe(sessions[0])
