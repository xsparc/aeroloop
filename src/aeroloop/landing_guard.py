"""Opt-in descent commands using capture age and captured horizontal stability."""
import math
from .wind_mission import reference_derivatives


def configuration():
    return {"kind":"landing-capture-guard-v1", "trigger_age_s":.6, "fresh_age_s":.02,
            "hold_min_altitude_m":.3, "horizontal_band_m":.2, "horizontal_speed_m_s":.2,
            "stable_dwell_s":.3, "descent_duration_s":4., "descent_end_m":-.03,
            "inputs":"mission-phase-scheduled-target-raw-captures", "scoring":"original-scheduled-target"}


class LandingGuard:
    def __init__(self):
        self.activated = self.resumed = self.stable_since = None
        self.height = None

    def step(self, t, phase, target, observation):
        cfg=configuration()
        velocity, acceleration=reference_derivatives(t) if phase not in ("grounded","landed") else ((0.,)*3,(0.,)*3)
        command=tuple(target)
        mode="inactive"
        dwell=0.
        if phase=="landing":
            age=observation["age_s"]
            if age>=cfg["trigger_age_s"] and (self.activated is None or self.resumed is not None):
                if self.activated is None:self.activated=t
                self.height=max(cfg["hold_min_altitude_m"],target[2])
                self.resumed=self.stable_since=None
            if self.activated is not None:
                if self.resumed is None:
                    stable=(age<cfg["fresh_age_s"]
                            and math.hypot(*observation["position_m"][:2])<=cfg["horizontal_band_m"]
                            and math.hypot(*observation["velocity_m_s"][:2])<=cfg["horizontal_speed_m_s"])
                    self.stable_since=(t if self.stable_since is None else self.stable_since) if stable else None
                    dwell=round(t-self.stable_since,9) if self.stable_since is not None else 0.
                    if dwell>=cfg["stable_dwell_s"]:self.resumed=t
                if self.resumed is None:
                    mode="settling" if age<cfg["fresh_age_s"] else "holding"
                    command=(target[0],target[1],self.height)
                    velocity=acceleration=(0.,)*3
                else:
                    mode="descending"
                    duration=cfg["descent_duration_s"]
                    u=max(0.,min(1.,(t-self.resumed)/duration))
                    delta=cfg["descent_end_m"]-self.height
                    command=(target[0],target[1],self.height+delta*u**3*(10+u*(-15+6*u)))
                    velocity=(0.,0.,delta*30*u*u*(1-u)**2/duration)
                    acceleration=(0.,0.,delta*60*u*(1-u)*(1-2*u)/duration**2)
        elif phase=="landed" and self.activated is not None:
            mode="complete"
        return {"mode":mode,"activated_at_s":self.activated,"resumed_at_s":self.resumed,
                "stable_for_s":dwell,"target_m":command,"target_velocity_m_s":velocity,
                "target_acceleration_m_s2":acceleration}


def validate_guard(value, expected=None):
    from .evidence import keys,require
    from .contracts import finite
    from .frames import vector
    keys(value,{"mode","activated_at_s","resumed_at_s","stable_for_s","target_m","target_velocity_m_s","target_acceleration_m_s2"})
    require(value["mode"] in ("inactive","holding","settling","descending","complete"),"invalid landing guard mode")
    for k in ("activated_at_s","resumed_at_s"):
        require(value[k] is None or finite(value[k]) and 34<=value[k]<=50,"invalid landing guard timestamp")
    require(finite(value["stable_for_s"]) and 0<=value["stable_for_s"]<=.3,"invalid landing guard dwell")
    for k in ("target_m","target_velocity_m_s","target_acceleration_m_s2"):vector(value[k])
    if expected is not None:
        for k in value:
            if k.startswith("target_"):require(all(abs(a-b)<=1e-10 for a,b in zip(value[k],expected[k])),"landing guard command mismatch")
            else:require(value[k]==expected[k],"landing guard transition mismatch")
