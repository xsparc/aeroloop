import copy
from dataclasses import asdict
import math
import unittest

from aeroloop.contracts import ValidationError
from aeroloop.evidence import validate_rotors
from aeroloop.physics import Model
from aeroloop.rotors import RotorModel


class RotorTests(unittest.TestCase):
    def test_each_rotor_obeys_moment_arm_and_reaction_sign(self):
        model = RotorModel()
        for i, (x, y, _) in enumerate(model.positions):
            thrusts = [0.]*4
            thrusts[i] = 1.
            thrust, moment = model.wrench(thrusts)
            self.assertEqual(thrust, 1.)
            self.assertEqual(moment, (y, -x, .02 * (1 if i % 2 == 0 else -1)))
        self.assertEqual(model.wrench([2.]*4), (8., (0., 0., 0.)))

    def test_mixer_recovers_independent_axes_without_saturation(self):
        model = RotorModel()
        for wanted in ((.1, 0., 0.), (0., -.1, 0.), (0., 0., .05), (.15, -.2, .03)):
            commands, flags, scale = model.allocate(9.80665, wanted)
            thrust, moment = model.wrench(commands)
            self.assertAlmostEqual(thrust, 9.80665)
            for actual, expected in zip(moment, wanted):
                self.assertAlmostEqual(actual, expected)
            self.assertEqual(flags, (0, 0, 0))
            self.assertEqual(scale, 1.)

    def test_desaturation_preserves_collective_and_feedback_direction(self):
        model = RotorModel()
        commands, flags, scale = model.allocate(18., (.4, -.4, .2))
        self.assertTrue(all(0 <= t <= 5 for t in commands))
        thrust, moment = model.wrench(commands)
        self.assertAlmostEqual(thrust, 18.)
        self.assertTrue(0 < scale < 1)
        self.assertEqual(flags, (1, 2, 1))
        for actual, request in zip(moment, (.4, -.4, .2)):
            self.assertAlmostEqual(actual, request*scale)
        self.assertEqual(model.allocate(0., (1., 1., 1.))[0], (0.,)*4)
        self.assertEqual(model.allocate(20., (1., 1., 1.))[0], (5.,)*4)

    def test_motor_step_matches_analytic_response_and_half_steps(self):
        model = RotorModel()
        state = (0.,)*4
        for _ in range(20):
            state = model.advance(state, (4.,)*4, .005)
        self.assertAlmostEqual(state[0], 4*(1-math.exp(-.1/.03)))
        self.assertEqual(len(set(state)), 1)
        a = model.advance((1.,)*4, (3.,)*4, .01)
        b = model.advance(model.advance((1.,)*4, (3.,)*4, .005), (3.,)*4, .005)
        self.assertAlmostEqual(a[0], b[0])

    def test_invalid_actuator_inputs_are_rejected(self):
        model = RotorModel()
        for operation in (lambda: RotorModel(arm_m=0), lambda: RotorModel(yaw_m=float("nan")),
                          lambda: model.allocate(float("inf"), (0, 0, 0)),
                          lambda: model.wrench([-1., 1., 1., 1.]),
                          lambda: model.wrench([1., 1., 6., 1.]),
                          lambda: model.advance((1.,)*4, (2.,)*4, 0)):
            with self.assertRaises(ValidationError):
                operation()

    def test_actuator_evidence_recomputes_commands_lag_and_applied_wrench(self):
        # Synthetic actuator values exercise a contract, never a PhysX execution claim.
        model = RotorModel()
        previous = (9.80665/4,)*4
        config = {"actuator": asdict(model), "model": asdict(Model()), "dt_s": .005}
        effort = (.5, -.4, .1)
        commands, _, scale = model.allocate(10., tuple(e*m for e, m in zip(effort, Model().max_moment)))
        applied = model.advance(previous, commands, .005)
        thrust, moment = model.wrench(applied)
        sample = {"thrust_setpoint_n": 10., "effort_normalized": effort,
                  "rotor_command_n": commands, "rotor_thrust_n": applied,
                  "moment_nm": moment, "thrust_n": thrust, "allocation_scale": scale}
        self.assertEqual(validate_rotors(sample, config, previous), applied)
        for key in ("rotor_command_n", "rotor_thrust_n", "moment_nm"):
            changed = copy.deepcopy(sample)
            changed[key] = [value+.01 for value in changed[key]]
            with self.assertRaises(ValidationError):
                validate_rotors(changed, config, previous)
        changed = {**sample, "allocation_scale": .5}
        with self.assertRaises(ValidationError):
            validate_rotors(changed, config, previous)


if __name__ == "__main__":
    unittest.main()
