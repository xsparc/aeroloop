"""Synthetic protocol tests; no fixture is presented as a GPU measurement."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop import yaw_arithmetic as audit
from aeroloop import yaw_audit as yaw
from aeroloop.contracts import ValidationError
from aeroloop.simulation import encoded
from test_yaw_audit import fixture as physics_fixture


def fixture(root):
    hashes = {}
    for n in yaw.ITERATIONS:
        for dt in yaw.TIMESTEPS:
            name = audit.worker_name(n, dt)
            physics = physics_fixture(root/name, dt, n)
            hashes[name] = audit.digest(root/name/"result.json")
    trials = []
    for n, dt, case in audit.matrix():
        samples = [[math.cos(yaw.CASES[case][0]*i*dt/2), math.sin(yaw.CASES[case][0]*i*dt/2)] for i in range(round(.5/dt)+1)]
        trials.append({"case": case, "dt_s": dt, "position_iterations": n,
                       "methods": {name: copy.deepcopy(samples) for name in audit.METHODS}})
    probe = {"schema_version": 1, "kind": "measured_cuda_yaw_arithmetic", "trials": trials}
    (root/"arithmetic.json").write_bytes(encoded(probe))
    installation = {name: {"version": "110.3.2", "manifest_sha256": "a"*64, "binaries": {}} for name in audit.EXTENSIONS}
    installation["omni.physx.gpu"]["binaries"] = {"PhysXGpu_64.dll": "b"*64, "PhysXDevice64.dll": "c"*64}
    result = {"schema_version": 1, "kind": "yaw_arithmetic_study", "backend": "cuda_arithmetic_vs_physx",
              "provenance": physics["provenance"], "tool_checksums": {name: "a"*64 for name in audit.TOOLS},
              "configuration": audit.CONFIGURATION, "installation": installation,
              "arithmetic_runtime": {"warp": "1.16.0", "cuda_toolkit": "12.9", "cuda_driver": "13.4", "compute_capability": "120"},
              "physics_result_checksums": hashes, "arithmetic_sha256": audit.digest(root/"arithmetic.json"),
              "wall_time_s": 1., "outcomes": audit.outcomes(root)[0]}
    (root/"result.json").write_bytes(encoded(result))
    return result, probe


class YawArithmeticTests(unittest.TestCase):
    def test_reference_signs_and_complete_comparison(self):
        self.assertAlmostEqual(audit.angles([[math.cos(-.125), math.sin(-.125)]])[0], -.25)
        self.assertAlmostEqual(audit.angles([[-math.cos(-.125), -math.sin(-.125)]])[0], -.25)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); fixture(root)
            summary = audit.report(root)
            self.assertEqual(summary["arithmetic_comparisons"], 18)
            self.assertEqual(summary["physics_passed"], 30)
            self.assertTrue(summary["outcomes"]["controls_passed"])

    def test_failed_signature_and_control_are_retained_independently(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); result, probe = fixture(root)
            row = probe["trials"][0]
            for name in ("intrinsic_float32", "library_float64"):
                angle = .025 + .0001
                row["methods"][name][-1] = [math.cos(angle/2), math.sin(angle/2)]
            (root/"arithmetic.json").write_bytes(encoded(probe))
            result["arithmetic_sha256"] = audit.digest(root/"arithmetic.json")
            result["outcomes"] = audit.outcomes(root)[0]
            (root/"result.json").write_bytes(encoded(result))
            report = audit.report(root)
            self.assertFalse(report["outcomes"]["fast_signature_supported"])
            self.assertFalse(report["outcomes"]["controls_passed"])
            self.assertTrue(report["outcomes"]["default_yaw_refinement_passed"])

    def test_trace_completeness_order_bounds_and_private_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, probe = fixture(root)
            mutations = [lambda p: p["trials"].pop(),
                lambda p: p["trials"].reverse(),
                lambda p: p["trials"][0]["methods"]["library_float32"].pop(),
                lambda p: p["trials"][0]["methods"]["library_float32"].__setitem__(0,[0.,1.]),
                lambda p: p["trials"][0]["methods"]["library_float32"].__setitem__(1,[2.,0.]),
                lambda p: p["trials"][0].update(host="private")]
            for mutate in mutations:
                changed = copy.deepcopy(probe); mutate(changed)
                (root/"arithmetic.json").write_bytes(encoded(changed))
                with self.assertRaises(ValidationError): audit.read_probe(root/"arithmetic.json")

    def test_result_corruption_false_outcomes_and_mixed_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); result, _ = fixture(root)
            for mutate in [lambda r: r.update(host="private"),
                lambda r: r["provenance"].update(source_commit="b"*40),
                lambda r: r["outcomes"].update(controls_passed=False),
                lambda r: r["configuration"].update(float32_control_limit_rad=1.),
                lambda r: r.update(arithmetic_sha256="0"*64),
                lambda r: r["physics_result_checksums"].update({"physics-1-200":"0"*64}),
                lambda r: r["installation"]["omni.physx.gpu"]["binaries"].update({"private-path":"a"*64}),
                lambda r: r["arithmetic_runtime"].update(warp="private/value")]:
                changed = copy.deepcopy(result); mutate(changed)
                (root/"result.json").write_bytes(encoded(changed))
                with self.assertRaises(ValidationError): audit.read_study(root)

    def test_installation_fingerprints_are_bounded_and_identify_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in audit.EXTENSIONS:
                folder = root/"extscache"/(name+"-110.3.2")
                (folder/"config").mkdir(parents=True)
                (folder/"config/extension.toml").write_text('[package]\nversion="110.3.2"\n',encoding="utf-8")
                if name == "omni.physx.gpu":
                    (folder/"bin").mkdir()
                    for binary in ("PhysXGpu_64.dll", "PhysXDevice64.dll"):
                        (folder/"bin"/binary).write_bytes(b"synthetic binary identity fixture")
            before = audit.installation(root)
            (root/"extscache/omni.physx.gpu-110.3.2/bin/PhysXGpu_64.dll").write_bytes(b"changed")
            self.assertNotEqual(before, audit.installation(root))
            (root/"extscache/omni.physx-110.3.3").mkdir()
            with self.assertRaises(ValidationError): audit.installation(root)
