# 005: Ground-contact takeoff, route and landing

Accepted 2026-09-21 under the maintainer's autonomous continuation of simulation-only
drone development after the turbulence merge. Baseline: `c19c74fee2aca16bcb86e1d412f0b5733994993d`.

AL-008 adds one calm `ground-mission` scenario, using the existing native rate
controller, gains, four rotor limits and motor lag in actual Isaac PhysX.
The drone starts at rest with stopped motors, takes off, visits four hover
waypoints and lands on a physical collider. No pose writes follow initial reset.
Wind on a mission, learned control, hardware and website deployment are outside
this slice. The existing airborne experiments and defaults remain available.

The 1 kg body collider is a 0.4 × 0.4 × 0.1 m cuboid; its supported COM is 0.05 m
above the floor. An original static 20 × 20 × 0.1 m cuboid has its top at z=0.
Both use static/dynamic friction 0.7/0.5, restitution zero, contact offset 0.001 m
and rest offset zero. These are illustrative contact parameters. Initialize COM
z=0.055 m, identity orientation, zero velocity and seed-dependent XY offsets
within ±0.02 m. The contact sensor records ENU net **normal** force; this excludes
friction and is not a total contact wrench. Its pinned Lab 3 API is
`net_normal_forces_w`, avoiding the changing `net_forces_w` semantics.

At 200 Hz over 50 s: remain disarmed until 2 s; take off to (0,0,1.5) over
2–7 s; hold until 10 s; move to (0,1,1.5) over 10–15 s and hold until 18 s;
move to (1,1,1.5) over 18–23 s and hold until 26 s; return to (0,0,1.5) over
26–31 s and hold until 34 s. Descend to z=0.10 over 34–42 s, then approach
z=-0.03 over 42–46 s to establish support. Quintic interpolation commands
position targets only; the controller and physics produce all motion. During
landing, normal force >0.1 N, lowest oriented collider clearance ≤0.015 m and
|vertical velocity| ≤0.2 m/s continuously for 0.05 s latch `landed`. The controller
then disarms, resets its integral and requests zero thrust; motor lag still applies.

Acceptance is defined before GPU trials. Develop on seed 73; freeze the source
before final seeds 0–4, with no tuning on those seeds. Retain all failures.

- Complete all 50 s; achieve liftoff (clearance >0.05 m) between 2 and 7 s.
- Reach each waypoint within 0.15 m for one continuous second inside its hold
  window: [7,10], [15,18], [23,26], [31,34].
- Full-run tracking error ≤0.8 m, tilt ≤25 degrees, penetration ≤0.003 m;
  no normal force >0.1 N between liftoff and landing start.
- First landing contact before 48 s with downward speed ≤0.35 m/s measured
  from the preceding physics sample, and latched landing before 48 s.
- Over 48–50 s: COM height 0.05±0.003 m, speed ≤0.05 m/s, tilt ≤3 degrees,
  XY distance ≤0.15 m, rotor thrust ≤0.01 N and mean normal support within 5%
  of weight. Over 1–2 s, also require stopped motors and mean support within 5%.

Version 4 evidence uses `quadrotor-x-contact-v1`. Record phase, measured normal
force and oriented collider clearance. Export verifies fixed configuration,
seeded initial state, targets, arm/disarm commands, rotor dynamics, phase/contact
events and metrics from full-rate data. Force is a PhysX measurement, not a
reconstruction of the contact solver. Replay depicts the actual collider, route,
phase and support readings. Interpolation is for display only.

Affected requirements: REQ-GROUND-MISSION, REQ-DRONE-CONTROL and
REQ-REUSABLE-REPLAY. Expected paths: mission/control and evidence modules, Isaac
worker, replay contracts/scene, CLI, tests and documentation. Verify state-machine
boundaries, uninterrupted contact/waypoint dwell, oriented clearance, pre-impact
speed, tampered evidence, backward compatibility, GPU trials and browser behavior.
Risks include false touchdown from proximity alone, off-by-one force timing,
incorrect support geometry and reporting post-impact velocity as approach speed.

References: [Isaac Lab contact sensor](https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/sensors/contact_sensor.html),
[Lab 3 migration](https://isaac-sim.github.io/IsaacLab/develop/source/migration/migrating_to_isaaclab_3-0.html)
and [Isaac Sim 6.1 contact sensor](https://docs.isaacsim.omniverse.nvidia.com/6.1.0/sensors/isaacsim_sensors_physics_contact.html).
