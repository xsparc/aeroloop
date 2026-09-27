"""Seeded position/velocity observations, separate from the physics truth."""
from collections import deque
from dataclasses import replace
import random

PROFILES = ("ideal", "noise", "delay", "noise-delay")
DT = .005


def configuration(profile):
    if profile not in PROFILES:
        raise ValueError("unsupported observation profile")
    return {"profile": profile, "position_sigma_m": .01 if "noise" in profile else 0.,
            "velocity_sigma_m_s": .02 if "noise" in profile else 0., "clip_sigma": 3.,
            "delay_steps": 8 if "delay" in profile else 0, "capture_dt_s": DT,
            "startup": "hold-first", "random_stream": "python-mt19937-gauss-xor-0x4f4253",
            "channels": "position-velocity", "ideal_channels": "attitude-rates-acceleration-supervisor-contact"}


class Observations:
    def __init__(self, profile, seed):
        self.config = configuration(profile)
        self.rng = random.Random(seed ^ 0x4f4253)
        self.history = deque(maxlen=self.config["delay_steps"] + 1)
        self.sequence = 0

    def capture(self, truth):
        """Capture now, deliver the oldest retained sample, and preserve ideal channels."""
        c, i = self.config, self.sequence
        def noisy(values, sigma):
            return tuple(v + max(-3*sigma, min(3*sigma, self.rng.gauss(0., sigma)))
                         for v in values) if sigma else tuple(values)
        self.history.append({"profile": c["profile"], "source_sequence": i,
                             "source_time_s": round(i*DT, 9),
                             "position_m": noisy(truth.position, c["position_sigma_m"]),
                             "velocity_m_s": noisy(truth.velocity, c["velocity_sigma_m_s"])})
        delivered = dict(self.history[0])
        delivered["age_s"] = round((i-delivered["source_sequence"])*DT, 9)
        self.sequence += 1
        return replace(truth, position=delivered["position_m"], velocity=delivered["velocity_m_s"]), delivered


def validate_sample(value, sequence, profile=None):
    from .evidence import keys, require
    from .contracts import finite
    from .frames import vector
    keys(value, {"profile", "source_sequence", "source_time_s", "age_s", "position_m", "velocity_m_s"})
    require(value["profile"] in PROFILES and (profile is None or value["profile"] == profile), "observation profile mismatch")
    source = max(0, sequence-configuration(value["profile"])["delay_steps"])
    require(type(value["source_sequence"]) is int and value["source_sequence"] == source,
            "observation source sequence mismatch")
    require(finite(value["source_time_s"]) and value["source_time_s"] == round(source*DT, 9)
            and finite(value["age_s"]) and value["age_s"] == round((sequence-source)*DT, 9), "observation timing mismatch")
    vector(value["position_m"])
    vector(value["velocity_m_s"])


def validate_capture(value, expected, sequence):
    from .evidence import require
    validate_sample(value, sequence, expected["profile"])
    for key in ("position_m", "velocity_m_s"):
        require(all(abs(a-b) <= 1e-12 for a,b in zip(value[key], expected[key])), "observation differs from seeded truth capture")
