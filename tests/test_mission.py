import copy
from dataclasses import asdict
import math
import tempfile
from unittest.mock import patch
import unittest

from aeroloop import mission
from aeroloop.contracts import ValidationError
from aeroloop.evidence import validate_mission, read_run
from aeroloop.physics import Model, State
from aeroloop.rotors import RotorModel
from aeroloop.simulation import metrics, record, encoded, sha256


class MissionTests(unittest.TestCase):
    def test_oriented_collider_clearance(self):
        self.assertAlmostEqual(mission.clearance((0, 0, .05), (1, 0, 0, 0)), 0.)
        angle = math.pi/4
        self.assertAlmostEqual(mission.clearance((0, 0, 1), (math.cos(angle/2), math.sin(angle/2), 0, 0)), 1-.25/math.sqrt(2))

    def test_schedule_boundaries_and_seeded_ground_start(self):
        self.assertEqual(mission.initial_state(73), mission.initial_state(73))
        self.assertNotEqual(mission.initial_state(73), mission.initial_state(74))
        for t, phase, target in ((0, 'grounded', (0, 0, .05)), (2, 'takeoff', (0, 0, .05)),
                (7, 'hover', (0, 0, 1.5)), (15, 'north_hold', (0, 1, 1.5)),
                (23, 'east_hold', (1, 1, 1.5)), (31, 'home_hold', (0, 0, 1.5)),
                (34, 'landing', (0, 0, 1.5)), (46, 'landing', (0, 0, -.03))):
            actual_phase, actual_target = mission.scheduled_target(t)
            self.assertEqual(actual_phase, phase)
            for a, b in zip(actual_target, target):
                self.assertAlmostEqual(a, b)
        for t in (2, 7, 10, 15, 18, 23, 26, 31, 34, 42, 46):
            self.assertLess(math.dist(mission.scheduled_target(t-1e-5)[1], mission.scheduled_target(t+1e-5)[1]), 1e-6)

    def test_contact_latch_needs_force_proximity_speed_and_unbroken_dwell(self):
        route = mission.Mission()
        ground = State(position=(0, 0, .05))
        self.assertFalse(route.update(0, ground, (0, 0, 9.8))[2])
        route.update(3, State(), (0, 0, 0))
        self.assertTrue(route.update(20, ground, (0, 0, 9.8))[2])
        route.update(42, State(), (0, 0, 1))  # force alone is insufficient
        route.update(43, ground, (0, 0, .2))
        route.update(43.04, ground, (0, 0, 0))  # reset dwell
        self.assertTrue(route.update(43.05, ground, (0, 0, .2))[2])
        self.assertTrue(route.update(43.095, ground, (0, 0, .2))[2])
        phase, target, armed, _ = route.update(43.10, ground, (0, 0, .2))
        self.assertEqual((phase, target, armed), ('landed', (0, 0, .05), False))
        self.assertFalse(route.update(44, ground, (0, 0, 0))[2])
        self.assertEqual(mission.setpoint(ground, target, False), (0, (0, 0, 0)))

    def test_dwell_break_and_preimpact_speed(self):
        # Analytic contract fixtures, not simulator measurements.
        samples = [{'time_s': i*.5, 'ok': i != 2} for i in range(9)]
        self.assertEqual(mission.dwell(samples, 0, 4, lambda s: s['ok'], 1), 1.5)
        samples = []
        for i in range(10001):
            t = round(i*.005, 9)
            z = .05 if t < 2 or t >= 43 else 1.5
            samples.append({'time_s': t, 'position_m': [0, 0, z], 'target_m': [0, 0, z],
                'velocity_m_s': [0, 0, -.31 if t == 42.995 else 0], 'quaternion_wxyz': [1, 0, 0, 0],
                'support_clearance_m': z-.05, 'contact_normal_force_n': [0, 0, 9.80665 if z == .05 else 0],
                'mission_phase': 'landed' if t >= 43.05 else 'landing', 'rotor_thrust_n': [0]*4})
        result = metrics(samples, mission.SCENARIO)
        self.assertEqual(result['mission']['touchdown_descent_speed_m_s'], .31)
        self.assertEqual(result['mission']['touchdown_time_s'], 43)
        self.assertEqual(result['mission']['final_support']['samples'], 401)
        self.assertEqual(mission.outcome(result), 'mission_threshold')  # missed north/east

    def test_short_failed_recording_and_tampering(self):
        # Two synthetic grounded samples exercise the real file/contract boundary.
        state = mission.initial_state(73)
        samples = []
        route = mission.Mission()
        for i in range(2):
            phase, target, _, bottom = route.update(i*.005, state, (0, 0, 0))
            samples.append({'time_s': i*.005, 'sequence': i, 'position_m': state.position,
                'velocity_m_s': state.velocity, 'quaternion_wxyz': state.quaternion, 'rates_rad_s': state.rates,
                'target_m': target, 'rate_setpoint_rad_s': [0]*3, 'effort_normalized': [0]*3,
                'thrust_n': 0., 'external_force_n': [0]*3, 'thrust_setpoint_n': 0.,
                'rotor_command_n': [0]*4, 'rotor_thrust_n': [0]*4, 'moment_nm': [0]*3, 'allocation_scale': 1.,
                'mission_phase': phase, 'contact_normal_force_n': [0]*3, 'support_clearance_m': bottom})
        config = {'model': asdict(Model()), 'initial_state': asdict(state), 'dt_s': .005,
            'duration_s': 50., 'scenario': mission.SCENARIO, 'seed': 73, 'controller': 'rate-pid-v1',
            'position_kp': 2.5, 'position_kd': 2.8, 'attitude_kp': 5.,
            'rate_gains': {'p': [.6]*3, 'i': [.1]*3, 'd': [.005]*3, 'ff': [0.]*3, 'integral_limit': [.3]*3},
            'actuator': asdict(RotorModel()), 'simulator_versions': {'isaacsim': '6.1', 'isaaclab': '17.0', 'torch': '2.11'},
            'physics_options': {'gyroscopic_forces': True}, 'mission': mission.configuration()}
        with tempfile.TemporaryDirectory() as directory:
            path = record({'experiment': 'isaac-quadrotor', 'config': config, 'samples': samples, 'events': route.events,
                'metrics': metrics(samples, mission.SCENARIO), 'status': 'failed', 'failure_reason': 'mission_threshold',
                'controller_binary_sha256': 'a'*64}, directory)
            self.assertEqual(read_run(path)['manifest.json']['schema_version'], 4)
            import json
            original = json.loads((path / "manifest.json").read_bytes())
            original_hashes = json.loads((path / "checksums.json").read_bytes())
            forged = {**original, "status": "passed", "failure_reason": None}
            (path / "manifest.json").write_bytes(encoded(forged))
            (path / "checksums.json").write_bytes(encoded({**original_hashes, "manifest.json": sha256(encoded(forged))}))
            with self.assertRaises(ValidationError):
                read_run(path)
            for field, value in (('mission_phase', 'landed'), ('support_clearance_m', .2),
                    ('contact_normal_force_n', [0, 0, -1]), ('thrust_setpoint_n', 1.), ('effort_normalized', [.1, 0, 0])):
                changed = copy.deepcopy(samples[0]); changed[field] = value
                with self.subTest(field=field), self.assertRaises(ValidationError):
                    validate_mission(changed, mission.Mission())

    def test_report_rejects_missing_dirty_or_mixed_trials_and_omits_unknown_metadata(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("mission_report", Path(__file__).resolve().parents[1] / "tools/mission_report.py")
        reporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(reporter)
        config = {k: {} for k in ("model", "actuator", "mission", "physics_options", "simulator_versions")}
        config.update(dt_s=.005, duration_s=50.)
        runs = [{"manifest.json": {"scenario": mission.SCENARIO, "seed": seed, "source_dirty": False,
                  **{k: "a"*64 for k in ("source_commit", "source_tree_sha256", "controller_binary_sha256", "lock_sha256", "config_sha256")},
                  "run_id": str(seed), "status": "failed", "failure_reason": "mission_threshold", "private_host": "omit"},
                 "config.json": config, "samples.json": [{"rotor_thrust_n": [0]*4, "allocation_scale": 1}],
                 "metrics.json": {}, "events.json": []} for seed in range(5)]
        with patch.object(reporter, "load_json", return_value={"wall_time_s": 1}), patch.object(reporter, "validate_flight_result", return_value=runs):
            self.assertNotIn("private_host", str(reporter.report("unused")))
            runs[0]["manifest.json"]["source_dirty"] = True
            with self.assertRaises(ValidationError): reporter.report("unused")
            runs[0]["manifest.json"]["source_dirty"] = False
            runs[0]["manifest.json"]["source_commit"] = "b"*64
            with self.assertRaises(ValidationError): reporter.report("unused")
            runs.pop(0)
            with self.assertRaises(ValidationError): reporter.report("unused")


if __name__ == '__main__':
    unittest.main()
