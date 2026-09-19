# CPU physics model

The CPU model integrates a single rigid body in ENU with a body FLU frame:

`m v_dot = R(q) [0,0,T] + external_force - [0,0,mg]`

`I omega_dot = torque - omega cross (I omega)`

Position uses constant-acceleration integration over each step; velocity and body
rate use explicit updates. Orientation uses the exponential of midpoint body rate
and quaternion normalization. This is a fixed-step approximation, not a high-order
or energy-preserving solver. The default interval is 0.005 s. Tests compare analytic
freefall, hover equilibrium, signs and 0.01/0.005 s closed-loop convergence.

Model constants: mass 1 kg, inertia diagonal (0.02, 0.02, 0.04) kg m², gravity
9.80665 m/s², maximum thrust 20 N and moment scales (0.4, 0.4, 0.2) N m.
The ideal wrench actuator independently bounds thrust and moments. No individual
rotor mixer, motor dynamics, drag, estimator, sensor noise or ground contact is modeled.
The initial state is already airborne; these are hover-response experiments, not takeoff.

Position PD and an attitude error produce bounded body-rate setpoints. The C++
RatePid3Axis runs every physics step through a C ABI. Its fixed-size update has no
allocation or I/O. Allocation occurs once when the simulation creates its controller.
Rate gains use radians/second, seconds and normalized effort; the plant converts
normalized effort to moments using the declared scales. Derivative input is the
previous step's body angular acceleration. The CPU model supplies perfect state.

The hover measurement window is [5,35] s. The position step changes north by one
metre at 10 s and returns at 25 s. The force pulse applies 0.5 N east at 15 s and
ends at 15.5 s. These times align with supported integration intervals. Random seeds
perturb each initial position axis by at most 0.05 m. Failed trials remain recorded.

Results establish behavior only in this model. Isaac physics and learning remain
separate required validations. Equations are based on standard Newton-Euler mechanics;
see [MIT quadrotor dynamics](https://vnav.mit.edu/material/06-Control1-notes.pdf).
