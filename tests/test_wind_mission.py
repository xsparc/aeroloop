import copy
from dataclasses import asdict
import math
import tempfile
import unittest

from aeroloop import mission, wind_mission
from aeroloop.contracts import ValidationError
from aeroloop.evidence import read_run, validate_mission
from aeroloop.physics import Model, State
from aeroloop.rotors import RotorModel
from aeroloop.simulation import encoded, metrics, record, sha256


class WindMissionTests(unittest.TestCase):
    def test_analytic_feedforward_matches_position_derivatives_and_stops_at_holds(self):
        h = 1e-4
        for t in (3., 4.5, 11., 12.5, 19., 20.5, 27., 28.5, 35., 38., 43., 44.):
            p = mission.scheduled_target(t)[1]
            before, after = (mission.scheduled_target(t+delta)[1] for delta in (-h, h))
            velocity, acceleration = wind_mission.reference_derivatives(t)
            for i in range(3):
                self.assertAlmostEqual(velocity[i], (after[i]-before[i])/(2*h), places=7)
                self.assertAlmostEqual(acceleration[i], (after[i]-2*p[i]+before[i])/(h*h), places=5)
        for t in (0., 2., 7., 10., 15., 18., 23., 26., 31., 34., 42., 46., 50.):
            self.assertEqual(wind_mission.reference_derivatives(t), ((0.,)*3, (0.,)*3))

    def test_integral_rejects_bias_is_bounded_and_resets_on_disarm(self):
        controller = wind_mission.TrackingController()
        state = State(position=(-.1, 0., 1.5))
        for _ in range(6000):
            _, _, sample = controller.step(8., state, (0., 0., 1.5), True)
        self.assertEqual(sample['integral_acceleration_m_s2'], (1.5, 0., 0.))
        held = controller.integral
        controller.step(8., State(position=(.1, 0., 1.5)), (0., 0., 1.5), True, allocation_saturated=True)
        self.assertEqual(controller.integral, held)
        controller.step(8., State(position=(.1, 0., 1.5)), (0., 0., 1.5), True)
        self.assertLess(controller.integral[0], held[0])
        thrust, rate, sample = controller.step(44., state, (0., 0., .05), False)
        self.assertEqual((thrust, rate, controller.integral), (0., (0.,)*3, (0.,)*3))
        self.assertTrue(all(v == (0.,)*3 for v in sample.values()))
        controller.step(8., State(position=(-10., 0., 1.5)), (0., 0., 1.5), True)
        self.assertEqual(controller.integral, (0.,)*3)  # acceleration saturation freezes integration

    def test_seeded_wind_continues_during_descent_and_after_disarm(self):
        model = wind_mission.wind_model()
        wind = list(model.velocities(73, .005, 10001))
        self.assertEqual(wind, list(model.velocities(73, .005, 10001)))
        self.assertNotEqual(wind[-1], list(model.velocities(74, .005, 10001))[-1])
        self.assertGreater(max(math.hypot(*v) for v in wind[8000:8401]), 5.)
        self.assertGreater(min(math.hypot(*v) for v in wind[9600:]), 0.)
        events = wind_mission.events([{'time_s': 0., 'type': 'grounded'}], 50.)
        self.assertEqual([e['type'] for e in events], ['grounded', 'wind_start', 'gust_start', 'gust_end'])

    def test_support_force_uses_preceding_applied_interval(self):
        # Analytic fixture: alternating external Z forces exactly balance normals.
        samples = []
        for i in range(10001):
            force = 1. if i % 2 else -1.
            samples.append({'time_s': round(i*.005, 9), 'position_m': [0, 0, .05], 'target_m': [0, 0, .05],
                'velocity_m_s': [0, 0, 0], 'quaternion_wxyz': [1, 0, 0, 0], 'support_clearance_m': 0.,
                'contact_normal_force_n': [0, 0, Model().gravity+force], 'external_force_n': [0, 0, force],
                'thrust_n': 0., 'rotor_thrust_n': [0]*4, 'mission_phase': 'landed' if i > 9000 else 'grounded'})
        measured = wind_mission.metrics(samples)
        for field in ('initial_support', 'final_support'):
            self.assertAlmostEqual(measured[field]['mean_vertical_balance_error_n'], 0., places=12)

    def test_schema_five_verifies_integral_wind_and_outcome(self):
        # Minimal failed protocol fixture; never a claimed physics result.
        state, route, tracking = mission.initial_state(73), mission.Mission(), wind_mission.TrackingController()
        wind = wind_mission.wind_model()
        samples = []
        for i, velocity in enumerate(wind.velocities(73, .005, 2)):
            phase, target, armed, bottom = route.update(i*.005, state, (0.,)*3)
            thrust, rate, control = tracking.step(i*.005, state, target, armed)
            force, moment = wind.wrench(state.velocity, state.quaternion, state.rates, velocity)
            samples.append({'time_s': i*.005, 'sequence': i, 'position_m': state.position,
                'velocity_m_s': state.velocity, 'quaternion_wxyz': state.quaternion, 'rates_rad_s': state.rates,
                'target_m': target, 'rate_setpoint_rad_s': rate, 'effort_normalized': [0]*3,
                'thrust_n': thrust, 'external_force_n': force, 'external_moment_nm': moment,
                'wind_velocity_m_s': velocity, 'thrust_setpoint_n': thrust, 'rotor_command_n': [0]*4,
                'rotor_thrust_n': [0]*4, 'moment_nm': [0]*3, 'allocation_scale': 1., 'mission_phase': phase,
                'contact_normal_force_n': [0]*3, 'support_clearance_m': bottom, **control})
        config = {'model': asdict(Model()), 'initial_state': asdict(state), 'dt_s': .005, 'duration_s': 50.,
            'scenario': wind_mission.SCENARIO, 'seed': 73, 'controller': 'rate-pid-v1',
            'position_kp': 2.5, 'position_kd': 2.8, 'attitude_kp': 5.,
            'rate_gains': {'p': [.6]*3, 'i': [.1]*3, 'd': [.005]*3, 'ff': [0.]*3, 'integral_limit': [.3]*3},
            'actuator': asdict(RotorModel()), 'simulator_versions': {'isaacsim': '6.1', 'isaaclab': '17.0', 'torch': '2.11'},
            'physics_options': {'gyroscopic_forces': True}, 'mission': wind_mission.contact_configuration(),
            'wind': asdict(wind), 'trajectory_control': wind_mission.control_configuration()}
        with tempfile.TemporaryDirectory() as directory:
            path = record({'experiment': 'isaac-quadrotor', 'config': config, 'samples': samples,
                'events': wind_mission.events(route.events, .005), 'metrics': metrics(samples, wind_mission.SCENARIO),
                'status': 'failed', 'failure_reason': 'wind_mission_threshold', 'controller_binary_sha256': 'a'*64}, directory)
            original = read_run(path)
            self.assertEqual(original['manifest.json']['schema_version'], 5)
            for filename, modify in (
                    ('samples.json', lambda s: s[1].update(wind_velocity_m_s=[0, 0, 0])),
                    ('samples.json', lambda s: s[1].update(integral_acceleration_m_s2=[.1, 0, 0])),
                    ('events.json', lambda e: e.pop()),
                    ('metrics.json', lambda m: m['mission'].update(touchdown_time_s=44.))):
                data = copy.deepcopy(original); modify(data[filename])
                for name, value in data.items(): (path/name).write_bytes(encoded(value))
                (path/'checksums.json').write_bytes(encoded({name: sha256(encoded(value)) for name, value in data.items()}))
                with self.subTest(filename=filename), self.assertRaises(ValidationError): read_run(path)


if __name__ == '__main__':
    unittest.main()
