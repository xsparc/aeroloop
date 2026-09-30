"""Fixed horizontal capture quality sensitivity; not a calibrated sensor."""
from collections import deque
import random

from .contracts import finite
from .axis_feedback import combine, validate_feedback

QUALITIES = ("ideal", "noise", "delay", "noise-delay")


def configuration(quality):
    from .evidence import require
    require(quality in QUALITIES, "invalid horizontal channel quality")
    return {"kind": "horizontal-quality-v1", "available_axes": "horizontal", "quality": quality,
            "capture_period_steps": 4, "capture_phase_steps": 0, "control_dt_s": .005,
            "position_sigma_m": .01 if "noise" in quality else 0.,
            "velocity_sigma_m_s": .02 if "noise" in quality else 0., "clip_sigma": 3.,
            "transport_delay_steps": 8 if "delay" in quality else 0,
            "startup": "bootstrap-first-capture", "random_stream": "python-mt19937-gauss-xor-0x48515a",
            "source": "synthetic-physics-captures", "usage": "replace-selected-feedback-components"}


def source_sequence(sequence, quality):
    return max(0, sequence-configuration(quality)["transport_delay_steps"])//4*4


class QualityCaptures:
    def __init__(self, quality, seed):
        self.config = configuration(quality)
        self.axes, self.quality, self.sequence = "horizontal", quality, -1
        self.rng = random.Random(seed ^ 0x48515a)
        self.history = deque(maxlen=3)

    def capture(self, truth):
        self.sequence += 1
        if self.sequence % 4 == 0:
            values = {}
            for name, vector, sigma in (("position_m", truth.position, self.config["position_sigma_m"]),
                                        ("velocity_m_s", truth.velocity, self.config["velocity_sigma_m_s"])):
                # Noise drawn once per selected component per acquisition, never for altitude.
                values[name] = tuple(v + max(-3*sigma, min(3*sigma, self.rng.gauss(0., sigma)))
                                     if sigma else v for v in vector[:2]) + (None,)
            self.history.append({"available_axes": self.axes, "quality": self.quality,
                                 "source_sequence": self.sequence,
                                 "source_time_s": round(self.sequence*.005, 9), **values})
        source = source_sequence(self.sequence, self.quality)
        delivered = dict(next(row for row in self.history if row["source_sequence"] == source))
        delivered["age_s"] = round((self.sequence-source)*.005, 9)
        return delivered


def validate_capture(value, sequence, axes=None, expected=None, quality=None):
    from .evidence import keys, require
    keys(value, {"available_axes", "quality", "source_sequence", "source_time_s", "age_s", "position_m", "velocity_m_s"})
    require(value["available_axes"] == "horizontal" and axes in (None, "horizontal"), "quality channel must be horizontal")
    require(value["quality"] in QUALITIES and (quality is None or value["quality"] == quality), "channel quality mismatch")
    source = source_sequence(sequence, value["quality"])
    require(type(value["source_sequence"]) is int and value["source_sequence"] == source
            and finite(value["source_time_s"]) and value["source_time_s"] == round(source*.005, 9)
            and finite(value["age_s"]) and value["age_s"] == round((sequence-source)*.005, 9), "channel delivery cadence mismatch")
    for key in ("position_m", "velocity_m_s"):
        require(isinstance(value[key], (list, tuple)) and len(value[key]) == 3
                and all(finite(v) for v in value[key][:2]) and value[key][2] is None, "invalid horizontal mask")
        if expected is not None:
            require(value["quality"] == expected["quality"] and all(abs(value[key][i]-expected[key][i]) <= 1e-12 for i in (0,1)),
                    "channel differs from seeded acquisition and delay")
