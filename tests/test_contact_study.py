import copy
import math
import unittest

from aeroloop.contact_study import COLUMNS, trace, phase_metrics, phases
from aeroloop.contracts import ValidationError


def samples():
    """Manufactured interval: 2 N wind for 5 ms, then 100 N for the next step."""
    s = dict(time_s=33.995, position_m=[.1, -.2, .5], velocity_m_s=[.2, -.1, 0],
             quaternion_wxyz=[1., 0., 0., 0.], mission_phase='landing',
             axis_feedback=dict(position_m=[.12, -.18, .5], velocity_m_s=[.3, -.2, 0]),
             target_m=[0., 0., .4], target_velocity_m_s=[0., 0., 0.],
             target_acceleration_m_s2=[.1, -.1, 0.], integral_acceleration_m_s2=[.2, -.3, 0.],
             thrust_n=10., rotor_thrust_n=[2.5]*4, external_force_n=[2., -4., 0.])
    result = [s, copy.deepcopy(s), copy.deepcopy(s)]
    result[1].update(time_s=34., velocity_m_s=[.21, -.12, 0.], external_force_n=[100., 0., 0.])
    result[2].update(time_s=34.005, velocity_m_s=[.71, -.12, 0.], external_force_n=[0., 0., 0.])
    return result


class ContactStudyTests(unittest.TestCase):
    def test_momentum_uses_previous_force_and_preserves_controller_terms(self):
        rows = trace(samples()); self.assertEqual(len(rows), 2)
        self.assertTrue(all(len(r)==len(COLUMNS) for r in rows))
        self.assertAlmostEqual(rows[0][33], -.3)
        self.assertAlmostEqual(rows[0][35], -.84)
        self.assertAlmostEqual(rows[0][37], -.84)
        self.assertAlmostEqual(rows[0][43], math.hypot(.1, -.2))
        self.assertAlmostEqual(rows[0][47], .5*(.21**2+.12**2))
        for r in rows:
            self.assertAlmostEqual(r[48], 0.)
            self.assertAlmostEqual(r[49], 0.)
        # A velocity impulse not explained by the applied forces remains visible.
        source = samples(); source[1]['velocity_m_s'][0] += .03
        self.assertAlmostEqual(trace(source)[0][48], .03)

    def test_rotated_thrust_and_disarmed_terms(self):
        source = samples(); source[1]['quaternion_wxyz'] = [math.cos(.1), 0., math.sin(.1), 0.]
        r = trace(source)[0]
        self.assertAlmostEqual(r[39], 10*math.sin(.2))
        self.assertAlmostEqual(r[40], 0.)
        self.assertAlmostEqual(r[41], math.degrees(.2))
        source[1].update(mission_phase='landed', target_velocity_m_s=[0]*3,
                         target_acceleration_m_s2=[0]*3, integral_acceleration_m_s2=[0]*3)
        r = trace(source)[0]; self.assertEqual(r[33:39], [0]*6)
        self.assertEqual(r[21:25], [2.5]*4)  # Physical rotors may still be spinning.

    def test_phase_endpoints_do_not_double_count_impulse(self):
        rows = trace(samples()); p = phase_metrics(rows, 34., 34.005, True)
        self.assertEqual(p['state_samples'], 2); self.assertTrue(p['complete'])
        self.assertAlmostEqual(p['wind_impulse_n_s'][0], .5)
        self.assertAlmostEqual(p['momentum_change_n_s'][0], .5)
        for a in (0, 1):
            self.assertAlmostEqual(p['momentum_change_n_s'][a], sum(p[k][a] for k in ('thrust_impulse_n_s','wind_impulse_n_s','residual_impulse_n_s')))
        partition = phases(rows, 34., 34.005)
        self.assertEqual(partition['approach']['wind_impulse_n_s'], [0, 0])
        self.assertEqual(partition['disarmed']['state_samples'], 1)
        self.assertFalse(partition['disarmed']['complete'])

    def test_missing_events_empty_and_truncated_windows_are_not_passes(self):
        self.assertIsNone(phase_metrics([], 34., 50., True))
        self.assertIsNone(phase_metrics(trace(samples()), None, 50., True))
        p = phases(trace(samples()), None, None)
        self.assertFalse(p['approach']['complete'])
        self.assertIsNone(p['contact_to_disarm']); self.assertIsNone(p['disarmed'])
        self.assertFalse(phase_metrics(trace(samples()), 34., 50., True)['complete'])
        with self.assertRaises(ValidationError): trace(samples()[1:])
