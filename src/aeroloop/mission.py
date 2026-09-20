"""Calm ground-contact mission; targets are commands, never prescribed motion."""
import math
import random

from .frames import rotate
from .physics import State, Model, desired_wrench
from .wind import tilt_degrees

SCENARIO = "ground-mission"
DURATION = 50.
PHASES = ("grounded", "takeoff", "hover", "north", "north_hold", "east", "east_hold",
          "return", "home_hold", "landing", "landed")
WAYPOINTS = ((7., 10., (0., 0., 1.5)), (15., 18., (0., 1., 1.5)),
             (23., 26., (1., 1., 1.5)), (31., 34., (0., 0., 1.5)))


def configuration():
    return {"kind": "calm-contact-mission-v1", "collider_size_m": [.4, .4, .1],
            "ground_size_m": [20., 20., .1], "ground_position_m": [0., 0., -.05],
            "static_friction": .7, "dynamic_friction": .5, "restitution": 0.,
            "contact_offset_m": .001, "rest_offset_m": 0.,
            "contact_force_threshold_n": .1, "landing_clearance_m": .015,
            "landing_speed_m_s": .2, "contact_dwell_s": .05,
            "waypoints": [{"window_s": [a, b], "position_m": list(p)} for a, b, p in WAYPOINTS]}


def initial_state(seed):
    rng = random.Random(seed)
    return State(position=(rng.uniform(-.02, .02), rng.uniform(-.02, .02), .055))


def clearance(position, quaternion):
    # Lowest point of the actual oriented cuboid, not just COM altitude.
    extent = sum(half*abs(rotate(quaternion, axis)[2]) for half, axis in
                 zip((.2, .2, .05), ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))))
    return position[2]-extent


def interpolate(t, a, b, start, end):
    u = max(0., min(1., (t-a)/(b-a)))
    s = u*u*u*(10.+u*(-15.+6.*u))
    return tuple(x+(y-x)*s for x, y in zip(start, end))


def scheduled_target(t):
    ground, home, north, east = (0., 0., .05), (0., 0., 1.5), (0., 1., 1.5), (1., 1., 1.5)
    for end, phase, target in ((2., "grounded", ground),
            (7., "takeoff", interpolate(t, 2., 7., ground, home)), (10., "hover", home),
            (15., "north", interpolate(t, 10., 15., home, north)), (18., "north_hold", north),
            (23., "east", interpolate(t, 18., 23., north, east)), (26., "east_hold", east),
            (31., "return", interpolate(t, 26., 31., east, home)), (34., "home_hold", home),
            (42., "landing", interpolate(t, 34., 42., home, (0., 0., .10)))):
        if t < end:
            return phase, target
    return "landing", interpolate(t, 42., 46., (0., 0., .10), (0., 0., -.03))


class Mission:
    def __init__(self):
        self.contact_since = None
        self.landed = False
        self.liftoff = False
        self.touchdown = False
        self.phase = None
        self.events = []

    def update(self, t, state, normal_force):
        bottom = clearance(state.position, state.quaternion)
        phase, target = scheduled_target(t)
        if t >= 2. and not self.liftoff and bottom > .05:
            self.liftoff = True
            self.events.append({"time_s": t, "type": "liftoff"})
        if t >= 34. and normal_force[2] > .1 and not self.touchdown:
            self.touchdown = True
            self.events.append({"time_s": t, "type": "touchdown"})
        contact = t >= 34. and normal_force[2] > .1 and bottom <= .015 and abs(state.velocity[2]) <= .2
        self.contact_since = (t if self.contact_since is None else self.contact_since) if contact else None
        if self.contact_since is not None and t-self.contact_since >= .05-1e-9:
            self.landed = True
        if self.landed:
            phase, target = "landed", (0., 0., .05)
        if phase != self.phase:
            self.events.append({"time_s": t, "type": phase})
            self.phase = phase
        return phase, target, phase not in ("grounded", "landed"), bottom


def setpoint(state, target, armed):
    return desired_wrench(state, target, Model()) if armed else (0., (0., 0., 0.))


def dwell(samples, start, end, predicate, seconds):
    since = None
    for sample in samples:
        t = sample["time_s"]
        if not start <= t <= end:
            continue
        if predicate(sample):
            since = t if since is None else since
            if t-since >= seconds-1e-9:
                return since
        else:
            since = None
    return None


def mission_metrics(samples):
    liftoff = next((s["time_s"] for s in samples if s["time_s"] >= 2. and s["support_clearance_m"] > .05), None)
    touch_index = next((i for i, s in enumerate(samples) if s["time_s"] >= 34. and s["contact_normal_force_n"][2] > .1), None)
    touchdown = samples[touch_index]["time_s"] if touch_index is not None else None
    # The force at sample i resulted from the preceding physics step.
    approach_speed = max(0., -samples[max(0, touch_index-1)]["velocity_m_s"][2]) if touch_index is not None else None
    landed = next((s["time_s"] for s in samples if s["mission_phase"] == "landed"), None)
    windows = {}
    for label, start, end in (("initial_support", 1., 2.-.005), ("final_support", 48., 50.)):
        window = [s for s in samples if start <= s["time_s"] <= end]
        windows[label] = None if not window else {
            "samples": len(window),
            "mean_normal_force_n": sum(s["contact_normal_force_n"][2] for s in window)/len(window),
            "peak_rotor_thrust_n": max(max(s["rotor_thrust_n"]) for s in window),
            "peak_height_error_m": max(abs(s["position_m"][2]-.05) for s in window),
            "peak_speed_m_s": max(math.hypot(*s["velocity_m_s"]) for s in window),
            "peak_tilt_deg": max(tilt_degrees(s["quaternion_wxyz"]) for s in window),
            "peak_xy_error_m": max(math.hypot(*s["position_m"][:2]) for s in window)}
    return {"liftoff_time_s": liftoff, "touchdown_time_s": touchdown,
            "touchdown_descent_speed_m_s": approach_speed, "landed_time_s": landed,
            "waypoint_reached_s": [dwell(samples, a, b, lambda s, p=p: math.dist(s["position_m"], p) <= .15, 1.) for a, b, p in WAYPOINTS],
            "peak_tilt_deg": max(tilt_degrees(s["quaternion_wxyz"]) for s in samples),
            "max_penetration_m": max(0., -min(s["support_clearance_m"] for s in samples)),
            "unexpected_contact_samples": sum(1 for s in samples if liftoff is not None and liftoff <= s["time_s"] < 34. and s["contact_normal_force_n"][2] > .1),
            **windows}


def outcome(measured):
    m = measured["mission"]
    if (measured["samples"] != 10001 or m["liftoff_time_s"] is None or not 2. <= m["liftoff_time_s"] < 7.
            or any(t is None for t in m["waypoint_reached_s"]) or measured["peak_error_m"] > .8
            or m["peak_tilt_deg"] > 25. or m["max_penetration_m"] > .003 or m["unexpected_contact_samples"]
            or m["touchdown_time_s"] is None or m["touchdown_time_s"] >= 48.
            or m["touchdown_descent_speed_m_s"] > .35 or m["landed_time_s"] is None or m["landed_time_s"] >= 48.):
        return "mission_threshold"
    for label, count in (("initial_support", 200), ("final_support", 401)):
        support = m[label]
        if (support is None or support["samples"] != count or abs(support["mean_normal_force_n"]-Model().gravity) > .05*Model().gravity
                or support["peak_rotor_thrust_n"] > .01
                or (label == "final_support" and (support["peak_height_error_m"] > .003 or support["peak_speed_m_s"] > .05
                    or support["peak_tilt_deg"] > 3. or support["peak_xy_error_m"] > .15))):
            return "mission_support_threshold"
    return None
