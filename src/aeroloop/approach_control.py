"""Fixed, opt-in horizontal gain schedule for the landing approach."""
from .contracts import ValidationError, finite


def configuration():
    from .wind_mission import control_configuration
    return {**control_configuration(), 'kind': 'approach-gains-v1',
            'horizontal_position_kp': 4., 'horizontal_velocity_kd': 3.6,
            'ramp_start_s': 34., 'ramp_duration_s': 1., 'ramp': 'quintic'}


def parameters(t, armed=True):
    u = max(0., min(1., t-34.)) if armed else 0.
    blend = u*u*u*(10.+u*(-15.+6.*u))
    return (blend, 2.5+1.5*blend, 2.8+.8*blend)


def validate(value, t, phase):
    expected = parameters(t, phase not in ('grounded', 'landed'))
    if (not isinstance(value, (tuple, list)) or len(value)!=3 or not all(finite(v) for v in value)
            or any(abs(a-b)>1e-12 for a,b in zip(value, expected))):
        raise ValidationError('invalid approach gain telemetry')
    return value
