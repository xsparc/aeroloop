"""Synthetic 50 Hz axis availability ablation; not a hardware sensor model."""
from .contracts import finite
from .frames import vector

AXES = ("vertical", "horizontal")
PROFILES = ("sample-hold", "hold-dropout-2000ms")


def configuration(axes):
    from .evidence import require
    require(axes in AXES, "invalid fresh axes")
    return {"kind": "fresh-axis-ablation-v1", "available_axes": axes,
            "capture_period_steps": 4, "capture_phase_steps": 0, "control_dt_s": .005,
            "noise": "none", "transport_delay_steps": 0,
            "source": "synthetic-physics-captures", "usage": "replace-selected-feedback-components"}


def selected(axes, i):
    return (i == 2) if axes == "vertical" else (i < 2)


class AxisCaptures:
    def __init__(self, axes):
        configuration(axes)
        self.axes, self.sequence, self.values = axes, -1, None

    def capture(self, truth):
        self.sequence += 1
        source = self.sequence // 4 * 4
        if self.sequence == source:
            # Only the explicitly selected components cross the capture boundary.
            self.values = {k: tuple(v if selected(self.axes, i) else None for i, v in enumerate(values))
                           for k, values in (("position_m", truth.position), ("velocity_m_s", truth.velocity))}
        return {"available_axes": self.axes, "source_sequence": source,
                "source_time_s": round(source*.005, 9), "age_s": round((self.sequence-source)*.005, 9),
                **self.values}


def combine(prediction, capture):
    axes = capture["available_axes"]
    return {"mode": axes+"-"+capture.get("quality", "fresh"), **{k: tuple(capture[k][i] if selected(axes, i) else prediction[k][i]
        for i in range(3)) for k in ("position_m", "velocity_m_s")}}


def validate_capture(value, sequence, axes=None, expected=None):
    from .evidence import keys, require
    keys(value, {"available_axes", "source_sequence", "source_time_s", "age_s", "position_m", "velocity_m_s"})
    require(value["available_axes"] in AXES and (axes is None or value["available_axes"] == axes), "fresh axes mismatch")
    source = sequence // 4 * 4
    require(type(value["source_sequence"]) is int and value["source_sequence"] == source
            and finite(value["source_time_s"]) and value["source_time_s"] == round(source*.005, 9)
            and finite(value["age_s"]) and value["age_s"] == round((sequence-source)*.005, 9), "axis capture cadence mismatch")
    for k in ("position_m", "velocity_m_s"):
        require(isinstance(value[k], (list, tuple)) and len(value[k]) == 3, "invalid masked capture")
        for i, v in enumerate(value[k]):
            require(finite(v) if selected(value["available_axes"], i) else v is None, "unavailable axis must be null")
            if expected is not None and v is not None:
                require(abs(v-expected[k][i]) <= 1e-12, "axis capture differs from acquisition truth")


def validate_feedback(value, capture, prediction):
    from .evidence import keys, require
    expected = combine(prediction, capture)
    keys(value, expected)
    require(value["mode"] == expected["mode"], "axis feedback mode mismatch")
    for k in ("position_m", "velocity_m_s"):
        require(all(abs(a-b) <= 1e-12 for a, b in zip(vector(value[k]), expected[k])), "axis composite feedback mismatch")
