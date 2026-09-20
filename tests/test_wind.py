import copy
import math
import random
import unittest
from unittest.mock import patch

from aeroloop.contracts import ValidationError
from aeroloop.evidence import validate_wind
from aeroloop.physics import Model, State, desired_wrench
from aeroloop.simulation import metrics
from aeroloop.wind import WindModel, flight_setpoint, wind_outcome, comparisons
from aeroloop.isaac_process import validate_flight_result


class WindTests(unittest.TestCase):
    def test_repeatable_seeded_velocity_and_calm_boundaries(self):
        model = WindModel()
        a = list(model.velocities(73, .005, 7001))
        self.assertEqual(a, list(model.velocities(73, .005, 7001)))
        self.assertNotEqual(a, list(model.velocities(74, .005, 7001)))
        self.assertTrue(all(v == (0., 0., 0.) for i, v in enumerate(a) if i <= 1000 or i >= 5000))
        self.assertTrue(all(math.hypot(*v) <= 12.+1e-12 for v in a))
        self.assertGreater(max(math.hypot(*v) for v in a[2400:2800]), 4.)

    def test_ou_transition_matches_stationary_exact_discretization(self):
        model = WindModel(mean_m_s=(0.,)*3, active_s=(-1., 10.), gust_m_s=(0.,)*3)
        rng = random.Random(5 ^ 0x57494E44)
        first = tuple(rng.gauss(0., s) for s in model.sigma_m_s)
        decay = math.exp(-.005/.6)
        second = tuple(decay*g + math.sqrt(1-decay**2)*s*rng.gauss(0., 1.) for g, s in zip(first, model.sigma_m_s))
        self.assertEqual(list(model.velocities(5, .005, 2)), [first, second])
        for seed, dt, count in ((-1, .005, 2), (True, .005, 2), (0, 0, 2), (0, float('nan'), 2), (0, .005, 0)):
            with self.assertRaises(ValidationError):
                list(model.velocities(seed, dt, count))

    def test_drag_relative_velocity_quadratic_scaling_and_moment_arm(self):
        model = WindModel()
        force, moment = model.wrench((0.,)*3, (1., 0., 0., 0.), (0.,)*3, (4., 0., 0.))
        self.assertAlmostEqual(force[0], .5*1.225*.06*16.)
        self.assertAlmostEqual(moment[1], .03*force[0])
        self.assertEqual(moment[0], 0.)
        self.assertEqual(model.wrench((4., 0., 0.), (1., 0., 0., 0.), (0.,)*3, (4., 0., 0.)), ((0.,)*3, (0.,)*3))
        opposite, _ = model.wrench((4., 0., 0.), (1., 0., 0., 0.), (0.,)*3, (0.,)*3)
        self.assertEqual(opposite[0], -force[0])
        doubled, _ = model.wrench((0.,)*3, (1., 0., 0., 0.), (0.,)*3, (8., 0., 0.))
        self.assertEqual(doubled[0], 4*force[0])
        # Body yaw +90 degrees: east force is -Y body, producing +X moment.
        q = (math.sqrt(.5), 0., 0., math.sqrt(.5))
        yawed, torque = model.wrench((0.,)*3, q, (0.,)*3, (4., 0., 0.))
        self.assertEqual(yawed, force)
        self.assertAlmostEqual(torque[0], moment[1])
        self.assertAlmostEqual(torque[1], 0.)

    def test_rotation_at_pressure_centre_causes_dissipative_moment(self):
        force, moment = WindModel().wrench((0.,)*3, (1., 0., 0., 0.), (0., 2., 0.), (0.,)*3)
        self.assertLess(force[0], 0.)
        self.assertLess(moment[1], 0.)

    def test_reference_removes_horizontal_feedback_but_retains_altitude(self):
        state = State(position=(4., -3., 1.), velocity=(1., 2., -.2))
        target, model = (0., 0., 1.5), Model()
        held = flight_setpoint(state, target, model, 'turbulence-hold')
        self.assertEqual(held, desired_wrench(state, target, model))
        thrust, rate = flight_setpoint(state, target, model, 'turbulence-attitude-only')
        self.assertEqual(rate, (0.,)*3)
        self.assertAlmostEqual(thrust, model.gravity+2.5*.5+2.8*.2)
        self.assertNotEqual(held[1], rate)

    def test_recovery_requires_unbroken_dwell_and_reference_is_not_hold(self):
        # Analytic contract fixture, never claimed as executed physics.
        samples = [{'time_s': i*.5, 'position_m': [0., 0., 1.5], 'target_m': [0., 0., 1.5],
                    'quaternion_wxyz': [1., 0., 0., 0.]} for i in range(71)]
        samples[52]['position_m'][0] = .2  # break recovery at 26 s
        measured = metrics(samples, 'turbulence-hold')
        self.assertEqual(measured['turbulence']['recovery_time_s'], 1.5)
        self.assertIsNone(wind_outcome(measured, 'turbulence-hold'))
        measured['peak_error_m'] = 10.
        measured['turbulence']['wind_position_rmse_m'] = 5.
        measured['turbulence']['recovery_time_s'] = None
        self.assertIsNone(wind_outcome(measured, 'turbulence-attitude-only'))
        self.assertEqual(wind_outcome(measured, 'turbulence-hold'), 'turbulence_hold_threshold')
        rows = [{'scenario': s, 'seed': 0, 'run_id': s, 'status': 'passed',
                 'metrics': {'turbulence': {'wind_position_rmse_m': value}}}
                for s, value in [('turbulence-hold', .2), ('turbulence-attitude-only', 5.)]]
        self.assertTrue(comparisons(rows)[0]['passed'])
        rows[0]['metrics']['turbulence']['wind_position_rmse_m'] = 2.
        self.assertFalse(comparisons(rows)[0]['passed'])

    def test_wind_contract_rejects_forged_force_moment_and_mode(self):
        state = State()
        wind = (4., 1., .5)
        force, moment = WindModel().wrench(state.velocity, state.quaternion, state.rates, wind)
        thrust, rate = flight_setpoint(state, (0., 0., 1.5), Model(), 'turbulence-hold')
        sample = {'position_m': list(state.position), 'velocity_m_s': state.velocity, 'quaternion_wxyz': state.quaternion,
                  'rates_rad_s': state.rates, 'target_m': [0., 0., 1.5], 'wind_velocity_m_s': wind,
                  'external_force_n': force, 'external_moment_nm': moment,
                  'thrust_setpoint_n': thrust, 'rate_setpoint_rad_s': rate}
        validate_wind(sample, wind, 'turbulence-hold')
        for key in ('wind_velocity_m_s', 'external_force_n', 'external_moment_nm', 'rate_setpoint_rad_s'):
            changed = copy.deepcopy(sample)
            changed[key] = [v+.01 for v in changed[key]]
            with self.assertRaises(ValidationError):
                validate_wind(changed, wind, 'turbulence-hold')

    def test_pair_guard_rejects_forged_aggregate_and_mismatched_sources(self):
        # Stubs isolate aggregate checks; read_run's physics contracts have separate tests.
        runs, rows = {}, []
        for scenario, rmse in [('turbulence-hold', .2), ('turbulence-attitude-only', 5.)]:
            identity = f'isaac-{scenario}-0-123456789abc'
            manifest = {'schema_version': 3, 'run_id': identity, 'scenario': scenario, 'seed': 0, 'status': 'passed',
                        **{key: 'a'*64 for key in ('source_commit', 'source_tree_sha256', 'controller_binary_sha256', 'lock_sha256')}, 'source_dirty': False}
            measured = {'turbulence': {'wind_position_rmse_m': rmse}}
            runs[identity] = {'manifest.json': manifest, 'config.json': {'scenario': scenario}, 'metrics.json': measured}
            rows.append({'run_id': identity, 'scenario': scenario, 'seed': 0, 'status': 'passed', 'metrics': measured})
        result = {'schema_version': 1, 'kind': 'isaac_quadrotor_flight', 'backend': 'isaacsim_physx',
                  'results': rows, 'trials': 2, 'passed': 2, 'comparisons': comparisons(rows)}
        with patch('aeroloop.evidence.read_run', side_effect=lambda path: runs[path.name]):
            self.assertEqual(len(validate_flight_result('.', result)), 2)
            for field, value in [('comparisons', []), ('passed', 1), ('trials', 3)]:
                with self.subTest(field=field), self.assertRaises(ValidationError):
                    validate_flight_result('.', {**result, field: value})
            runs[rows[1]['run_id']]['manifest.json']['source_tree_sha256'] = 'b'*64
            with self.assertRaises(ValidationError):
                validate_flight_result('.', result)


if __name__ == '__main__':
    unittest.main()
