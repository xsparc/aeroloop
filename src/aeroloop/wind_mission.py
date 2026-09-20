"""Trajectory tracking and measured contact gates for the turbulent mission."""
import math

from . import mission
from .frames import rotate
from .physics import Model, acceleration_wrench
from .wind import WindModel

SCENARIO = "ground-mission-wind"
EVENTS = [(0., "wind_start"), (40., "gust_start"), (42., "gust_end")]
CONTROL_FIELDS = {"target_velocity_m_s", "target_acceleration_m_s2", "integral_acceleration_m_s2"}


def wind_model():
    return WindModel(active_s=(0., 55.), gust_s=(40., 42.))


def contact_configuration():
    return {**mission.configuration(), "kind": "wind-contact-mission-v1"}


def control_configuration():
    return {"kind": "trajectory-pid-v1", "position_kp": 2.5, "velocity_kd": 2.8,
            "integral_ki": [.6, .6, 0.], "integral_limit_m_s2": [1.5, 1.5, 0.],
            "acceleration_limit_m_s2": 4., "feedforward": True,
            "reset_when_disarmed": True, "freeze_on_allocation_saturation": True}


def reference_derivatives(t):
    """Analytic derivatives of decision 005's quintic position commands."""
    segments = ((2., 7., (0., 0., 1.45)), (10., 15., (0., 1., 0.)),
                (18., 23., (1., 0., 0.)), (26., 31., (-1., -1., 0.)),
                (34., 42., (0., 0., -1.4)), (42., 46., (0., 0., -.13)))
    for start, end, delta in segments:
        if start <= t < end:
            duration, u = end-start, (t-start)/(end-start)
            velocity = 30.*u*u*(1.-u)**2/duration
            acceleration = 60.*u*(1.-u)*(1.-2.*u)/(duration*duration)
            return tuple(d*velocity for d in delta), tuple(d*acceleration for d in delta)
    return (0., 0., 0.), (0., 0., 0.)


class TrackingController:
    def __init__(self):
        self.integral = (0., 0., 0.)

    def step(self, t, state, target, armed, dt=.005, allocation_saturated=False):
        velocity, feedforward = reference_derivatives(t) if armed else ((0.,)*3, (0.,)*3)
        if not armed:
            self.integral = (0., 0., 0.)
            thrust, rate = 0., (0., 0., 0.)
        else:
            cfg = control_configuration()
            error = tuple(p-x for p, x in zip(target, state.position))
            base = tuple(a + cfg["position_kp"]*e + cfg["velocity_kd"]*(v-actual)
                         for a, e, v, actual in zip(feedforward, error, velocity, state.velocity))
            acceleration_limit = cfg["acceleration_limit_m_s2"]
            integral = []
            for i, (old, e, b) in enumerate(zip(self.integral, error, base)):
                limit, gain = cfg["integral_limit_m_s2"][i], cfg["integral_ki"][i]
                candidate = max(-limit, min(limit, old+gain*e*dt))
                clipped_further = (b+candidate > acceleration_limit and e > 0) or (b+candidate < -acceleration_limit and e < 0)
                integral.append(old if allocation_saturated or clipped_further else candidate)
            self.integral = tuple(integral)
            acceleration = tuple(max(-acceleration_limit, min(acceleration_limit, b+i)) + (Model().gravity if axis == 2 else 0.)
                                 for axis, (b, i) in enumerate(zip(base, self.integral)))
            thrust, rate = acceleration_wrench(state, acceleration, Model())
        return thrust, rate, {"target_velocity_m_s": velocity, "target_acceleration_m_s2": feedforward,
                              "integral_acceleration_m_s2": self.integral}


def events(route_events, last_time):
    # Stable ordering: mission transition first if it shares a wind timestamp.
    return sorted([*route_events, *({"time_s": t, "type": k} for t, k in EVENTS if t <= last_time)], key=lambda e: e["time_s"])


def metrics(samples):
    result = mission.mission_metrics(samples, waypoint_band=.35)
    touch = next((i for i, s in enumerate(samples) if s["time_s"] >= 34. and s["contact_normal_force_n"][2] > .1), None)
    result["touchdown_horizontal_speed_m_s"] = math.hypot(*samples[max(0, touch-1)]["velocity_m_s"][:2]) if touch is not None else None
    result["waypoint_band_m"] = .35
    for label, start, end in (("initial_support", 1., 1.995), ("final_support", 48., 50.)):
        window = [(samples[i-1], s) for i, s in enumerate(samples) if i and start <= s["time_s"] <= end]
        if result[label] is not None:
            result[label]["mean_vertical_balance_error_n"] = sum(
                s["contact_normal_force_n"][2] + prev["external_force_n"][2]
                + rotate(prev["quaternion_wxyz"], (0., 0., prev["thrust_n"]))[2] - Model().gravity
                for prev, s in window)/len(window)
    return result


def outcome(measured):
    m = measured["mission"]
    if (measured["samples"] != 10001 or m["liftoff_time_s"] is None or not 2. <= m["liftoff_time_s"] < 7.
            or any(t is None for t in m["waypoint_reached_s"]) or measured["peak_error_m"] > 1.
            or measured["position_rmse_m"] is None or measured["position_rmse_m"] > .5
            or m["peak_tilt_deg"] > 25. or m["max_penetration_m"] > .003 or m["unexpected_contact_samples"]
            or m["touchdown_time_s"] is None or m["touchdown_time_s"] >= 48.
            or m["touchdown_descent_speed_m_s"] > .35 or m["touchdown_horizontal_speed_m_s"] > .5
            or m["landed_time_s"] is None or m["landed_time_s"] >= 48.):
        return "wind_mission_threshold"
    for label, count in (("initial_support", 200), ("final_support", 401)):
        support = m[label]
        if (support is None or support["samples"] != count
                or abs(support["mean_vertical_balance_error_n"]) > .05*Model().gravity
                or support["peak_rotor_thrust_n"] > .01
                or (label == "final_support" and (support["peak_height_error_m"] > .003 or support["peak_speed_m_s"] > .05
                    or support["peak_tilt_deg"] > 3. or support["peak_xy_error_m"] > .35))):
            return "wind_mission_support_threshold"
    return None
