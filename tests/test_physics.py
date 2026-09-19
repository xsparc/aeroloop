from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aeroloop.contracts import ValidationError
from aeroloop.controller import RateController
from aeroloop.physics import Model, State, advance
from aeroloop.simulation import simulate, metrics


class PhysicsTests(unittest.TestCase):
    def test_freefall_matches_analytic_solution(self):
        state, model = State(position=(0, 0, 20)), Model()
        for _ in range(200):
            state = advance(state, model, 0, (0, 0, 0), (0, 0, 0), .005)
        self.assertAlmostEqual(state.position[2], 20-.5*model.gravity, places=10)
        self.assertAlmostEqual(state.velocity[2], -model.gravity, places=10)

    def test_hover_equilibrium(self):
        state, model = State(), Model()
        result = advance(state, model, model.mass*model.gravity, (0, 0, 0), (0, 0, 0), .005)
        self.assertEqual(result, state)

    def test_force_and_yaw_signs(self):
        result = advance(State(), Model(), Model().gravity, (0, 0, .5), (1, 0, 0), .01)
        self.assertGreater(result.position[0], 0)
        self.assertGreater(result.quaternion[3], 0)
        self.assertAlmostEqual(math.hypot(*result.quaternion), 1.)

    def test_invalid_mass_and_timestep(self):
        with self.assertRaises(ValidationError):
            Model(mass=-1)
        with self.assertRaises(ValidationError):
            advance(State(), Model(), 0, (0, 0, 0), (0, 0, 0), math.nan)

    def test_native_bridge_and_reset(self):
        with RateController() as controller:
            out = controller.step((0, 0, 0), (.5, 0, 0), (0, 0, 0), .005)
            self.assertGreater(out[0], 0)
            self.assertEqual(controller.step((0, 0, 0), (.5, 0, 0), (0, 0, 0), .005, armed=False), (0, 0, 0))
        with self.assertRaises(ValidationError):
            controller.step((0, 0, 0), (0, 0, 0), (0, 0, 0), .005)

    def test_seed_repeatability(self):
        a = simulate(seed=7, duration=6)
        b = simulate(seed=7, duration=6)
        self.assertEqual(a, b)
        self.assertEqual(a["status"], "passed")

    def test_step_and_force_recovery(self):
        for scenario in ("position-step", "lateral-force-pulse"):
            result = simulate(scenario)
            self.assertEqual(result["status"], "passed")
            self.assertLess(math.dist(result["samples"][-1]["position_m"], (0, 0, 1.5)), .05)
            self.assertEqual(len(result["events"]), 2)
            if scenario == "position-step":
                self.assertGreater(result["metrics"]["step_response"]["rise_time_s"], 0)
                self.assertIsNotNone(result["metrics"]["step_response"]["settling_time_s"])

    def test_timestep_convergence(self):
        coarse = simulate("position-step", dt=.01)
        fine = simulate("position-step", dt=.005)
        self.assertLess(abs(coarse["metrics"]["position_rmse_m"]-fine["metrics"]["position_rmse_m"]), .01)

    def test_never_settled_is_null(self):
        result = metrics([{"time_s": t, "position_m": (1, 1, 1), "target_m": (0, 0, 0)} for t in range(36)], "lateral-force-pulse")
        self.assertIsNone(result["recovery_time_s"])
        self.assertEqual(result["recovery_reason"], "did_not_settle")

    def test_invalid_interval_and_short_disturbance_fail(self):
        with self.assertRaises(ValidationError):
            simulate(dt=.003, duration=6)
        self.assertEqual(simulate("lateral-force-pulse", duration=6)["status"], "failed")
