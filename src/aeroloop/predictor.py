"""Bounded translational prediction from captures and known actuator output."""
import math
from .frames import rotate
from .physics import Model


def configuration():
    return {"kind": "rotor-motion-predictor-v1", "dt_s": .005, "activate_age_s": .02,
            "horizon_s": 2.1, "disturbance_tau_s": .2, "disturbance_limit_m_s2": 4.,
            "inputs": "captures-previous-thrust-previous-attitude", "expiry": "hold-capture"}


class Predictor:
    def __init__(self):
        self.position = self.velocity = self.last_velocity = None
        self.last_source = None
        self.nominal_integral = (0.,)*3
        self.disturbance = (0.,)*3

    def step(self, observation, previous=None):
        """No current truth, force or target input is accepted by this interface."""
        c, model = configuration(), Model()
        dt = c["dt_s"]
        if previous is not None and self.position is not None:
            thrust, attitude = previous
            nominal = tuple(a-(model.gravity if j == 2 else 0.)
                            for j,a in enumerate(rotate(attitude,(0.,0.,thrust/model.mass))))
            acceleration = tuple(a+b for a,b in zip(nominal,self.disturbance))
            self.position = tuple(p+v*dt+.5*a*dt*dt for p,v,a in zip(self.position,self.velocity,acceleration))
            self.velocity = tuple(v+a*dt for v,a in zip(self.velocity,acceleration))
            self.nominal_integral = tuple(v+a*dt for v,a in zip(self.nominal_integral,nominal))
        source = observation["source_sequence"]
        if source != self.last_source:
            elapsed = (source-self.last_source)*dt if self.last_source is not None else None
            if elapsed == .02:
                residual = tuple((v-old-impulse)/elapsed for v,old,impulse in
                                 zip(observation["velocity_m_s"],self.last_velocity,self.nominal_integral))
                alpha, limit = 1-math.exp(-elapsed/c["disturbance_tau_s"]), c["disturbance_limit_m_s2"]
                self.disturbance = tuple(old+alpha*(max(-limit,min(limit,a))-old) for old,a in zip(self.disturbance,residual))
            self.position, self.velocity = tuple(observation["position_m"]), tuple(observation["velocity_m_s"])
            self.last_source, self.last_velocity = source, self.velocity
            self.nominal_integral = (0.,)*3
        age = observation["age_s"]
        active = c["activate_age_s"] <= age <= c["horizon_s"]
        return {"mode": "predicting" if active else "expired" if age > c["horizon_s"] else "capture",
                "position_m": self.position if active else tuple(observation["position_m"]),
                "velocity_m_s": self.velocity if active else tuple(observation["velocity_m_s"]),
                "disturbance_acceleration_m_s2": self.disturbance}


def validate_feedback(value, expected=None):
    from .evidence import keys, require
    from .frames import vector
    keys(value, {"mode", "position_m", "velocity_m_s", "disturbance_acceleration_m_s2"})
    require(value["mode"] in ("capture", "predicting", "expired"), "invalid predictive feedback mode")
    for key in ("position_m", "velocity_m_s", "disturbance_acceleration_m_s2"):
        vector(value[key])
        if expected is not None:
            require(all(abs(a-b)<=1e-10 for a,b in zip(value[key],expected[key])), "predictive feedback differs from reconstruction")
    require(all(abs(a)<=4 for a in value["disturbance_acceleration_m_s2"]), "invalid disturbance estimate")
    if expected is not None:
        require(value["mode"] == expected["mode"], "predictive feedback mode differs")
