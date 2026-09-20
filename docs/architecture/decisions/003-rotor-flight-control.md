# 003: Develop rotor-actuated flight control in Isaac physics

Accepted 2026-09-20 within the maintainer's simulation-only drone-development request.
Baseline: `c06b2d4173ac4b30836b6c063b5b8fe2bac75089`.

AL-006 connects the existing position/attitude loop and C++ rate controller to a
four-rotor X model in Isaac Sim PhysX, with a local 3D replay of measured poses.
This extends the MVP without replacing its CPU baseline or separate learned policy.
Controller development must execute the physics loop; rendered motion alone is
not a control result.

Keep ENU world, FLU body, 1 kg mass and diagonal inertia (0.02, 0.02, 0.04) kg m².
Rotor order is front-left, rear-left, rear-right, front-right, each 0.23 m from
the centre. Rotor forces point along body +Z. Torque is the sum of `r cross F`
and alternating body reaction torques `(+,-,+,-) * 0.02 m * thrust`.
The reaction-torque signs describe torque on the body, not rotor spin direction.
Each rotor supplies 0 to 5 N. These are declared example parameters, not a
characterized commercial drone.

Allocate collective thrust and body moments through the inverse X mixer.
Preserve bounded collective thrust and uniformly scale the differential commands
when any rotor would saturate. Feed allocation loss back to the rate integrator.
Advance each thrust with a 0.03 s first-order time constant at 200 Hz, using the
exact discrete step response. At each pose sample, compute and record the command
and lagged thrust applied during the following physics interval. Initialize motors
at gravity-balanced thrust for these airborne experiments. No takeoff claim follows.

Isaac integrates the rigid body under the resulting force and torque, with
gyroscopic forces explicitly enabled and recorded in the physics options. No pose
overwrites occur after each trial's initial reset. Apply the disturbance in world
coordinates by explicitly converting it into the body frame. Read body rates and
world velocities from PhysX; convert Lab xyzw poses into normalized public wxyz.
Keep the existing gains and thresholds. Development seed is 73; the final suite
uses seeds 0 through 4 for each of hover, north step and east force-pulse. Each
trial lasts 35 s. Acceptance retains the existing 0.25 m hover RMSE, 0.30 m pulse
recovery band with two-second dwell within five seconds, and two-second step
settling inside 0.02 m. Preserve failed trials and incomplete worker failures.

Version 2 flight-control recordings identify `isaac-quadrotor` and `quadrotor-x-v1`.
They include requested collective, commanded/applied rotor thrust, applied moment,
allocation scale and pinned simulator versions. Export recomputes actuator outputs
and full-resolution metrics. Version 1 CPU records remain readable unchanged.
Learned-policy records remain a separate family and are not accepted as these runs.

The reusable viewer labels the selected physics backend, shows measured attitude
and trajectory in 3D, and exposes each rotor's applied thrust. It remains a local,
read-only replay with bounded, checksummed input and keyboard-accessible controls.
No public website update, live vehicle link, hardware flight, deployment, driver
change or new training run is part of this slice.

Risks: force/torque signs, quaternion order, saturation feedback, motor delay,
mislabelled evidence and GPU lifecycle errors. Validate mixer axes, actuator lag,
invalid inputs, saturation, evidence corruption and backend labels on CPU; then
execute actual PhysX trials and inspect the measured 3D replay. The model omits
propeller aerodynamics, battery effects, sensor noise, state estimation and contact.

References: [MIT quadrotor dynamics](https://vnav.mit.edu/material/06-Control1-notes.pdf),
[pinned Isaac rigid-object API](https://github.com/isaac-sim/IsaacLab/blob/ae37b028ea415c91ea2bc32609efcd759ed2b974/source/isaaclab/isaaclab/assets/rigid_object/base_rigid_object_data.py).
