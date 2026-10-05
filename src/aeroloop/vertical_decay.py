"""Opt-in vertical disturbance forgetting; no additional sensor or truth inputs."""
import math
from .predictor import Predictor, configuration as original_configuration


def configuration():
    return {**original_configuration(), "kind":"vertical-disturbance-decay-v1",
            "decay_tau_s":.2,"decay_after_age_s":.015,"decay_axes":"vertical",
            "anchor_update":"unchanged-consecutive-captures"}


def scale_for_age(age):
    return math.exp(-max(0.,age-.015)/.2)


class VerticalDecay(Predictor):
    def step(self, observation, previous=None):
        anchor = self.disturbance
        held = observation["source_sequence"] == self.last_source
        scale = scale_for_age(observation["age_s"]) if held else 1.
        self.disturbance = (anchor[0],anchor[1],anchor[2]*scale)
        value = super().step(observation, previous)
        if held:
            self.disturbance = anchor
        self.telemetry = {"kind":"vertical-disturbance-decay-v1", "scale":scale,
                          "anchor_z_m_s2":self.disturbance[2],
                          "effective_z_m_s2":value["disturbance_acceleration_m_s2"][2]}
        return value


def validate_decay(value, observation, feedback, expected=None):
    from .evidence import keys, require
    from .contracts import finite
    keys(value,{"kind","scale","anchor_z_m_s2","effective_z_m_s2"})
    require(value["kind"] == "vertical-disturbance-decay-v1", "invalid decay kind")
    require(all(finite(value[k]) for k in ("scale","anchor_z_m_s2","effective_z_m_s2")), "invalid decay values")
    require(abs(value["anchor_z_m_s2"]) <= 4 and 0 < value["scale"] <= 1
            and abs(value["scale"]-scale_for_age(observation["age_s"])) < 1e-12
            and abs(value["effective_z_m_s2"]-value["anchor_z_m_s2"]*value["scale"]) < 1e-12
            and value["effective_z_m_s2"] == feedback["disturbance_acceleration_m_s2"][2], "inconsistent decay telemetry")
    if expected is not None:
        require(value == expected, "decay telemetry differs from reconstruction")
