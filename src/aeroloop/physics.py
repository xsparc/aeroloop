"""Newton-Euler body-wrench model. No motor, sensor or aerodynamic fidelity claim."""
from dataclasses import dataclass
import math
from .contracts import ValidationError, finite
from .frames import multiply, normalize, rotate, vector


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


@dataclass
class State:
    position: tuple = (0., 0., 1.5)
    velocity: tuple = (0., 0., 0.)
    quaternion: tuple = (1., 0., 0., 0.)
    rates: tuple = (0., 0., 0.)
    acceleration: tuple = (0., 0., 0.) # body angular acceleration


@dataclass(frozen=True)
class Model:
    mass: float = 1.0
    inertia: tuple = (0.02, 0.02, 0.04)
    gravity: float = 9.80665
    max_thrust: float = 20.0
    max_moment: tuple = (0.4, 0.4, 0.2)

    def __post_init__(self):
        vector(self.inertia)
        vector(self.max_moment)
        if not all(finite(v) and v > 0 for v in (self.mass, self.gravity, self.max_thrust, *self.inertia, *self.max_moment)):
            raise ValidationError("model parameters must be finite and positive")


def advance(state, model, thrust, effort, force, dt):
    if not finite(dt) or not 0.001 <= dt <= 0.02 or not finite(thrust):
        raise ValidationError("invalid physics step")
    effort, force = vector(effort), vector(force)
    p, v, w = vector(state.position), vector(state.velocity), vector(state.rates)
    q = normalize(state.quaternion)
    thrust_world = rotate(q, (0, 0, max(0., min(model.max_thrust, thrust))))
    a = tuple((thrust_world[i] + force[i]) / model.mass - (model.gravity if i == 2 else 0) for i in range(3))
    gyro = cross(w, tuple(model.inertia[i] * w[i] for i in range(3)))
    alpha = tuple((max(-1., min(1., effort[i])) * model.max_moment[i] - gyro[i]) / model.inertia[i] for i in range(3))
    new_w = tuple(w[i] + alpha[i]*dt for i in range(3))
    middle = tuple((w[i] + new_w[i]) * 0.5 for i in range(3))
    angle = math.hypot(*middle) * dt
    scale = dt * 0.5 if angle < 1e-10 else math.sin(angle * 0.5) * dt / angle
    dq = (math.cos(angle * 0.5), *(r * scale for r in middle))
    result = State(tuple(p[i]+v[i]*dt+0.5*a[i]*dt*dt for i in range(3)),
                   tuple(v[i]+a[i]*dt for i in range(3)), normalize(multiply(q, dq)), new_w, alpha)
    vector(result.position); vector(result.velocity); vector(result.rates)
    return result


def desired_wrench(state, target, model):
    # Position PD determines a desired thrust direction; orientation error yields body rates.
    acceleration = tuple(max(-4., min(4., 2.5*(target[i]-state.position[i])-2.8*state.velocity[i]))
                         + (model.gravity if i == 2 else 0.) for i in range(3))
    magnitude = math.hypot(*acceleration)
    z = tuple(a / magnitude for a in acceleration)
    x_raw = cross((0., 1., 0.), z)
    x = tuple(a / math.hypot(*x_raw) for a in x_raw)
    y = cross(z, x)
    columns = [rotate(state.quaternion, axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    errors = [cross(actual, desired) for actual, desired in zip(columns, (x, y, z))]
    world_error = tuple(sum(error[i] for error in errors)*0.5 for i in range(3))
    q = state.quaternion
    body_error = rotate((q[0], -q[1], -q[2], -q[3]), world_error)
    setpoint = tuple(max(-3., min(3., 5.*v)) for v in body_error)
    thrust = model.mass * sum(acceleration[i] * columns[2][i] for i in range(3))
    return max(0., min(model.max_thrust, thrust)), setpoint
