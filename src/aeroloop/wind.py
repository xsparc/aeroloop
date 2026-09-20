"""Seeded temporal wind and pressure-centre drag for bounded control experiments."""
from dataclasses import dataclass, replace
import math
import random

from .contracts import ValidationError, finite
from .frames import normalize, rotate, vector
from .physics import cross, desired_wrench

WIND_SCENARIOS = ("turbulence-hold", "turbulence-attitude-only")
WIND_EVENTS = [(5., "wind_start"), (12., "gust_start"), (14., "gust_end"), (25., "wind_end")]


@dataclass(frozen=True)
class WindModel:
    kind: str = "bounded-temporal-ou-v1"
    mean_m_s: tuple = (3., -1., 0.)
    sigma_m_s: tuple = (1.2, 1., .5)
    correlation_s: float = .6
    speed_limit_m_s: float = 12.
    density_kg_m3: float = 1.225
    drag_area_m2: float = .06
    pressure_centre_m: tuple = (0., 0., .03)
    active_s: tuple = (5., 25.)
    ramp_s: float = 1.
    gust_s: tuple = (12., 14.)
    gust_m_s: tuple = (3., 0., 0.)

    def __post_init__(self):
        for value in (self.mean_m_s, self.sigma_m_s, self.pressure_centre_m, self.gust_m_s):
            vector(value)
        for value in (self.active_s, self.gust_s):
            vector(value, 2)
            if value[0] >= value[1]:
                raise ValidationError("invalid wind event interval")
        if self.kind != "bounded-temporal-ou-v1" or any(s < 0 for s in self.sigma_m_s) or not all(
                finite(v) and v > 0 for v in (self.correlation_s, self.speed_limit_m_s, self.density_kg_m3, self.drag_area_m2, self.ramp_s)):
            raise ValidationError("invalid wind model")

    def velocities(self, seed, dt, count):
        """Stationary OU samples; independent of vehicle state and controller mode."""
        if type(seed) is not int or not 0 <= seed <= 2**31-1 or not finite(dt) or not .001 <= dt <= .02 or type(count) is not int or not 1 <= count <= 120001:
            raise ValidationError("invalid wind sequence request")
        rng = random.Random(seed ^ 0x57494E44)
        gust = tuple(rng.gauss(0., sigma) for sigma in self.sigma_m_s)
        decay = math.exp(-dt/self.correlation_s)
        innovation = math.sqrt(1.-decay*decay)
        for step in range(count):
            t = round(step*dt, 9)
            if step:
                gust = tuple(decay*g + innovation*s*rng.gauss(0., 1.) for g, s in zip(gust, self.sigma_m_s))
            envelope = max(0., min(1., (t-self.active_s[0])/self.ramp_s, (self.active_s[1]-t)/self.ramp_s))
            pulse = math.sin(math.pi*(t-self.gust_s[0])/(self.gust_s[1]-self.gust_s[0])) if self.gust_s[0] < t < self.gust_s[1] else 0.
            wind = tuple(envelope*(mean+g+pulse*p) for mean, g, p in zip(self.mean_m_s, gust, self.gust_m_s))
            scale = min(1., self.speed_limit_m_s/max(1e-12, math.hypot(*wind)))
            yield tuple(v*scale for v in wind)

    def wrench(self, velocity, quaternion, rates, wind):
        """Return ENU drag force and FLU moment about the centre of mass."""
        velocity, rates, wind = vector(velocity), vector(rates), vector(wind)
        q = normalize(quaternion)
        point_motion = rotate(q, cross(rates, self.pressure_centre_m))
        relative = tuple(w-v-p for w, v, p in zip(wind, velocity, point_motion))
        force = tuple(.5*self.density_kg_m3*self.drag_area_m2*math.hypot(*relative)*v for v in relative)
        body_force = rotate((q[0], -q[1], -q[2], -q[3]), force)
        return force, cross(self.pressure_centre_m, body_force)


def flight_setpoint(state, target, model, scenario):
    if scenario == "turbulence-attitude-only":
        # Keep the same altitude and attitude loops; remove horizontal P and D only.
        state = replace(state, position=(target[0], target[1], state.position[2]),
                        velocity=(0., 0., state.velocity[2]))
    return desired_wrench(state, target, model)


def tilt_degrees(quaternion):
    z = rotate(quaternion, (0., 0., 1.))[2]
    return math.degrees(math.acos(max(-1., min(1., z))))


def wind_metrics(samples):
    window = [s for s in samples if 5. <= s["time_s"] < 25.]
    error = lambda s: math.dist(s["position_m"], s["target_m"])
    start, recovery = None, None
    for sample in samples:
        t = sample["time_s"]
        if t < 25.:
            continue
        if error(sample) <= .10:
            start = t if start is None else start
            if t-start >= 2.-1e-9:
                recovery = start-25.
                break
        else:
            start = None
    return {"wind_window_s": [5., 25.],
            "wind_position_rmse_m": math.sqrt(sum(error(s)**2 for s in window)/len(window)) if window else None,
            "peak_tilt_deg": max(tilt_degrees(s["quaternion_wxyz"]) for s in samples),
            "peak_altitude_error_m": max(abs(s["position_m"][2]-s["target_m"][2]) for s in samples),
            "recovery_time_s": recovery, "recovery_band_m": .10, "recovery_dwell_s": 2.}


def wind_outcome(measured, scenario):
    wind = measured["turbulence"]
    if wind["peak_tilt_deg"] > 25. or wind["peak_altitude_error_m"] > .25:
        return "attitude_altitude_threshold"
    if scenario == "turbulence-hold" and (wind["wind_position_rmse_m"] is None or
            wind["wind_position_rmse_m"] > .5 or measured["peak_error_m"] > 1. or
            wind["recovery_time_s"] is None or wind["recovery_time_s"] > 5.):
        return "turbulence_hold_threshold"
    return None


def comparisons(results):
    """Summarize available same-seed pairs; callers verify run provenance separately."""
    rows = {(r["scenario"], r["seed"]): r for r in results}
    paired = sorted(seed for scenario, seed in rows if scenario == WIND_SCENARIOS[0] and (WIND_SCENARIOS[1], seed) in rows)
    output = []
    for seed in paired:
        held, reference = (rows[(scenario, seed)] for scenario in WIND_SCENARIOS)
        h, r = (row["metrics"]["turbulence"]["wind_position_rmse_m"] for row in (held, reference))
        ratio = h/r if h is not None and r is not None and r > 0 else None
        output.append({"seed": seed, "hold_run_id": held["run_id"], "reference_run_id": reference["run_id"],
                       "hold_to_reference_rmse_ratio": ratio,
                       "passed": held["status"] == reference["status"] == "passed" and ratio is not None and ratio <= .25})
    return output
