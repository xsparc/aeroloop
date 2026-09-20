"""Four-rotor X allocation and a discrete first-order thrust actuator."""
from dataclasses import dataclass
import math
from .contracts import ValidationError, finite
from .frames import vector


@dataclass(frozen=True)
class RotorModel:
    arm_m: float = .23
    yaw_m: float = .02
    max_rotor_thrust_n: float = 5.
    thrust_time_constant_s: float = .03

    def __post_init__(self):
        if not all(finite(v) and v > 0 for v in (
                self.arm_m, self.yaw_m, self.max_rotor_thrust_n, self.thrust_time_constant_s)):
            raise ValidationError("rotor parameters must be finite and positive")

    @property
    def positions(self):
        a = self.arm_m / math.sqrt(2)
        # FLU: front-left, rear-left, rear-right, front-right.
        return ((a, a, 0.), (-a, a, 0.), (-a, -a, 0.), (a, -a, 0.))

    def wrench(self, thrusts):
        values = vector(thrusts, 4)
        if any(v < 0 or v > self.max_rotor_thrust_n for v in values):
            raise ValidationError("rotor thrust outside actuator bounds")
        return sum(values), (
            sum(position[1]*value for position, value in zip(self.positions, values)),
            sum(-position[0]*value for position, value in zip(self.positions, values)),
            self.yaw_m * sum(sign*value for sign, value in zip((1, -1, 1, -1), values)),
        )

    def allocate(self, thrust, moment):
        if not finite(thrust):
            raise ValidationError("invalid collective thrust")
        x, y, z = vector(moment)
        a = self.arm_m / math.sqrt(2)
        differential = ((x-y)/a+z/self.yaw_m, (x+y)/a-z/self.yaw_m,
                        (-x+y)/a+z/self.yaw_m, (-x-y)/a-z/self.yaw_m)
        differential = tuple(d/4 for d in differential)
        collective = max(0., min(self.max_rotor_thrust_n, thrust/4))
        scale = 1.
        for d in differential:
            if d > 0:
                scale = min(scale, (self.max_rotor_thrust_n-collective)/d)
            elif d < 0:
                scale = min(scale, -collective/d)
        commands = tuple(max(0., min(self.max_rotor_thrust_n, collective+scale*d)) for d in differential)
        # Feedback uses allocation loss, not transient motor lag, to bound the integrator.
        achieved = self.wrench(commands)[1]
        saturation = tuple(1 if wanted-got > 1e-9 else 2 if wanted-got < -1e-9 else 0
                           for wanted, got in zip((x, y, z), achieved))
        return commands, saturation, scale

    def advance(self, previous, commands, dt):
        self.wrench(previous)
        self.wrench(commands)
        if not finite(dt) or not .001 <= dt <= .02:
            raise ValidationError("invalid motor interval")
        blend = -math.expm1(-dt/self.thrust_time_constant_s)
        return tuple(old+blend*(command-old) for old, command in zip(previous, commands))
