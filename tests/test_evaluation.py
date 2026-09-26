"""Acceptance boundaries and compact export; UI fixtures are not physics evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from aeroloop.contracts import ValidationError
from aeroloop.evaluation import export_evaluation
from aeroloop.flight_study import compare
from aeroloop.simulation import sha256
from aeroloop.wind_mission import evaluation, outcome

STUDY = Path(__file__).resolve().parents[1]/"docs/evidence/isaac-flight-study-001.json"


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.study = json.loads(STUDY.read_text(encoding="utf-8"))
        self.measured = copy.deepcopy(self.study["results"][0]["metrics"])

    def test_retained_metrics_keep_all_previous_outcomes(self):
        for row in self.study["results"]:
            self.assertIsNone(outcome(row["metrics"]))
            gates = evaluation(row["metrics"])
            self.assertEqual(len(gates), 23)
            self.assertTrue(all(g["status"] == "passed" for g in gates))

    def test_every_original_mission_boundary_is_preserved(self):
        # Independently stated decision 006 limits; exercise both sides of every gate.
        for path, good, bad in (
            ("samples", 10001, 10000), ("mission.liftoff_time_s", 2., 1.999),
            ("mission.liftoff_time_s", 6.999, 7.), ("peak_error_m", 1., 1.0001),
            ("position_rmse_m", .5, .5001), ("mission.peak_tilt_deg", 25., 25.01),
            ("mission.max_penetration_m", .003, .00301), ("mission.unexpected_contact_samples", 0, 1),
            ("mission.touchdown_time_s", 47.999, 48.), ("mission.landed_time_s", 47.999, 48.),
            ("mission.touchdown_descent_speed_m_s", .35, .35001),
            ("mission.touchdown_horizontal_speed_m_s", .5, .50001),
            ("mission.initial_support.samples", 200, 199), ("mission.final_support.samples", 401, 400),
            ("mission.initial_support.mean_vertical_balance_error_n", -.05*9.80665, -.491),
            ("mission.final_support.mean_vertical_balance_error_n", .05*9.80665, .491),
            ("mission.initial_support.peak_rotor_thrust_n", .01, .01001),
            ("mission.final_support.peak_rotor_thrust_n", .01, .01001),
            ("mission.final_support.peak_height_error_m", .003, .00301),
            ("mission.final_support.peak_speed_m_s", .05, .05001),
            ("mission.final_support.peak_tilt_deg", 3., 3.01),
            ("mission.final_support.peak_xy_error_m", .35, .35001),
        ):
            for value, passed in ((good, True), (bad, False), (None, False)):
                m = copy.deepcopy(self.measured)
                node = m
                for key in path.split(".")[:-1]:
                    node = node[key]
                node[path.split(".")[-1]] = value
                with self.subTest(path=path, value=value):
                    self.assertEqual(outcome(m) is None, passed)
                    self.assertEqual(all(g["status"] == "passed" for g in evaluation(m)), passed)
        self.measured["mission"]["waypoint_reached_s"][2] = None
        self.assertEqual(outcome(self.measured), "wind_mission_threshold")

    def test_missing_support_and_incomplete_pair_never_pass(self):
        self.measured["mission"]["final_support"] = None
        self.assertEqual(outcome(self.measured), "wind_mission_support_threshold")
        self.assertEqual(sum(g["status"] == "not_measured" for g in evaluation(self.measured)), 7)
        self.assertEqual(compare({"samples.json": [{}]}, {"samples.json": [{}]}),
                         {"passed": False, "reason": "incomplete_pair"})

    def test_export_binds_display_files_and_preserves_failure_without_overwrite(self):
        # Mock only the already-verified input boundary. Poses are synthetic protocol data.
        runs = {}
        for i, row in enumerate(self.study["results"]):
            manifest = {"schema_version": 5, "run_id": f"isaac-ground-mission-wind-{row['seed']}-{i:012x}",
                        "scenario": "ground-mission-wind", **{k: row[k] for k in ("seed", "status", "failure_reason")}}
            samples = [{"time_s": n*.005, "position_m": [0, 0, .05], "target_m": [0, 0, .05],
                        "quaternion_wxyz": [1, 0, 0, 0], "rotor_thrust_n": [0]*4, "wind_velocity_m_s": [0]*3,
                        "external_force_n": [0]*3, "external_moment_nm": [0]*3, "mission_phase": "grounded",
                        "contact_normal_force_n": [0, 0, 9.81], "support_clearance_m": 0.} for n in range(12)]
            runs[(row["physics_dt_s"], row["seed"])] = {"manifest.json": manifest, "metrics.json": row["metrics"],
                "config.json": {"dt_s": .005}, "events.json": [{"time_s": .025, "type": "takeoff"}], "samples.json": samples}
        row = self.study["results"][0]
        row.update(status="failed", failure_reason="wind_mission_threshold")
        row["metrics"]["mission"]["touchdown_time_s"] = None
        runs[(row["physics_dt_s"],row["seed"])]["manifest.json"].update(status="failed", failure_reason=row["failure_reason"])
        with tempfile.TemporaryDirectory() as directory, patch("aeroloop.evaluation.read_study", return_value=(runs, {})), \
                patch("aeroloop.evaluation.summarize", return_value=self.study):
            target = Path(directory)/"bundle"
            result = export_evaluation([], target)
            self.assertEqual(len(result["cases"]), 9)
            self.assertEqual(result["cases"][0]["status"], "failed")
            for name, digest in result["checksums"].items():
                self.assertEqual(sha256((target/name).read_bytes()), digest)
                self.assertNotIn(Path(name).name, ("samples.json", "config.json"))
            replay = json.loads(next(target.glob("*/replay.json")).read_text(encoding="utf-8"))
            self.assertEqual([s["time_s"] for s in replay["samples"]], [0., .02, .025, .03, .05, .055])
            with self.assertRaises(ValidationError):
                export_evaluation([], target)
            row["status"] = "passed"
            runs[(row["physics_dt_s"],row["seed"])]["manifest.json"].update(status="passed", failure_reason=None)
            with self.assertRaises(ValidationError):
                export_evaluation([], Path(directory)/"invalid")
            self.assertFalse((Path(directory)/"invalid").exists())
