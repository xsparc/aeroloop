"""Fixed capture cadence and outages; hold the last successful truth sample."""
from dataclasses import replace

PROFILES = ("timing-ideal", "sample-hold", "dropout", "hold-dropout")
DT = .005
WINDOWS = ((18., 18.25), (40., 40.25))


def configuration(profile):
    if profile not in PROFILES:
        raise ValueError("unsupported observation timing profile")
    return {"profile": profile, "capture_period_steps": 4 if profile in ("sample-hold", "hold-dropout") else 1,
            "dropout_windows_s": [list(w) for w in WINDOWS] if "dropout" in profile else [],
            "control_dt_s": DT, "channels": "position-velocity", "hold": "last-successful-capture",
            "capture_phase_steps": 0, "noise": "none", "transport_delay_steps": 0,
            "ideal_channels": "attitude-rates-acceleration-supervisor-contact"}


def source_sequence(sequence, profile):
    """Independent integer schedule, including the first post-outage capture."""
    c = configuration(profile)
    period = c["capture_period_steps"]
    source = sequence // period * period
    for start, end in c["dropout_windows_s"]:
        if round(start/DT) <= source < round(end/DT):
            source = (round(start/DT)-1)//period*period
    return source


class TimingObservations:
    def __init__(self, profile, seed):
        self.config = configuration(profile)
        self.sequence = 0
        self.last = None

    def capture(self, truth):
        i, c = self.sequence, self.config
        # Capture is a stateful process; verification also checks its integer schedule.
        t = round(i*DT, 9)
        missing = any(start <= t < end for start, end in c["dropout_windows_s"])
        if i % c["capture_period_steps"] == 0 and not missing:
            self.last = {"profile": c["profile"], "source_sequence": i, "source_time_s": t,
                         "position_m": tuple(truth.position), "velocity_m_s": tuple(truth.velocity)}
        delivered = {**self.last, "age_s": round((i-self.last["source_sequence"])*DT, 9)}
        self.sequence += 1
        return replace(truth, position=delivered["position_m"], velocity=delivered["velocity_m_s"]), delivered
