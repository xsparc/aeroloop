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


def evaluation(measured):
    """Decision 006 gates, evaluated on full-rate metrics (never display samples)."""
    m = measured["mission"]
    rows = []

    def gate(identity, label, value, unit, operator, limit, group="mission"):
        present = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        passed = present and {"eq": lambda: value == limit, "le": lambda: value <= limit,
                              "lt": lambda: value < limit, "ge": lambda: value >= limit,
                              "abs_le": lambda: abs(value) <= limit}[operator]()
        rows.append({"id": identity, "label": label, "group": group, "value": value if present else None,
                     "unit": unit, "operator": operator, "limit": limit,
                     "status": "passed" if passed else "failed" if present else "not_measured"})

    gate("samples", "Control samples", measured["samples"], "count", "eq", 10001)
    gate("liftoff_start", "Liftoff earliest", m["liftoff_time_s"], "s", "ge", 2.)
    gate("liftoff_end", "Liftoff deadline", m["liftoff_time_s"], "s", "lt", 7.)
    gate("waypoints", "Waypoint dwells reached", sum(t is not None for t in m["waypoint_reached_s"]), "count", "eq", 4)
    for identity, label, value, unit, operator, limit in (
        ("peak_error", "Peak position error", measured["peak_error_m"], "m", "le", 1.),
        ("rmse", "Position RMSE", measured["position_rmse_m"], "m", "le", .5),
        ("tilt", "Peak tilt", m["peak_tilt_deg"], "deg", "le", 25.),
        ("penetration", "Peak penetration", m["max_penetration_m"], "m", "le", .003),
        ("contact", "Unexpected contact samples", m["unexpected_contact_samples"], "count", "eq", 0),
        ("touchdown", "Touchdown deadline", m["touchdown_time_s"], "s", "lt", 48.),
        ("descent", "Touchdown descent speed", m["touchdown_descent_speed_m_s"], "m/s", "le", .35),
        ("horizontal", "Touchdown horizontal speed", m["touchdown_horizontal_speed_m_s"], "m/s", "le", .5),
        ("landed", "Landed deadline", m["landed_time_s"], "s", "lt", 48.),
    ):
        gate(identity, label, value, unit, operator, limit)
    for label, count in (("initial_support", 200), ("final_support", 401)):
        support = m[label] or {}
        for field, description, unit, operator, limit in (
            ("samples", "samples", "count", "eq", count),
            ("mean_vertical_balance_error_n", "mean vertical balance error", "N", "abs_le", .05*Model().gravity),
            ("peak_rotor_thrust_n", "peak rotor thrust", "N", "le", .01),
        ) + ((
            ("peak_height_error_m", "peak height error", "m", "le", .003),
            ("peak_speed_m_s", "peak speed", "m/s", "le", .05),
            ("peak_tilt_deg", "peak tilt", "deg", "le", 3.),
            ("peak_xy_error_m", "peak horizontal error", "m", "le", .35),
        ) if label == "final_support" else ()):
            gate(f"{label}_{field}", f"{label.replace('_', ' ').capitalize()}: {description}",
                 support.get(field), unit, operator, limit, "support")
    return rows


def outcome(measured):
    rows = evaluation(measured)
    for group, reason in (("mission", "wind_mission_threshold"), ("support", "wind_mission_support_threshold")):
        if any(row["status"] != "passed" for row in rows if row["group"] == group):
            return reason
    return None
