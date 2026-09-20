# 006: Complete a ground-contact mission under turbulent wind

Accepted 2026-09-21 under the maintainer's post-merge autonomous continuation.
Baseline: `9c308e43a4c07e98610f9279470a83167d85b2b9`.

AL-009 combines the existing ground-contact route with seeded wind in actual
Isaac PhysX. Add `ground-mission-wind` with version 5 evidence and model
`quadrotor-x-contact-wind-v1`. Preserve the original calm, airborne wind, CPU
and learned-policy experiments, their defaults and their acceptance gates.

Use the same 50 s route, 200 Hz physics, body, rotors, floor, friction, seeded
initial XY offsets and contact latch as decision 005. Apply the decision 004
temporal OU wind and relative-velocity pressure-centre drag throughout the
mission: active interval [0,55] s, one-second onset ramp, stronger eastward
half-sine gust over 40-42 s during descent. All other wind parameters stay fixed.
Wind remains active after disarming, including the final support window.
This is an illustrative engineering disturbance, not a calibrated weather model.

The new mission uses analytic velocity and acceleration feedforward from the
quintic position commands, plus position/velocity feedback (Kp=2.5, Kd=2.8).
Horizontal integral feedback (Ki=0.6 per axis, limited to +/-1.5 m/s2) rejects
steady wind bias without reading wind or applied drag. Vertical integral gain
is zero. Reset the integral when disarmed; freeze an axis when its candidate
would drive the +/-4 m/s2 acceleration clamp further into saturation. Freeze
integration on preceding rotor allocation saturation. The existing attitude
gain, native rate controller, motor lag and thrust limits remain unchanged.
Record the integral acceleration and reference velocity/acceleration so export
can recompute every outer-loop command without executing the simulator.

Acceptance, before trials: use development seed 73; freeze source before final
seeds 0-4 and never tune on those final seeds. Retain every failed trial.

- Complete all 50 s and lift off between 2 and 7 s.
- Reach all four waypoint hold windows within 0.35 m for one continuous second.
  This new wind gate is distinct from the calm mission's unchanged 0.15 m gate.
- Tracking RMSE over 5-50 s <=0.5 m; peak error <=1 m; tilt <=25 degrees;
  penetration <=0.003 m; no unexpected contact between liftoff and landing.
- Touch down and latch landing before 48 s. Downward speed immediately before
  first landing contact <=0.35 m/s; horizontal speed <=0.5 m/s.
- During 48-50 s: height 0.05+/-0.003 m, speed <=0.05 m/s, tilt <=3 degrees,
  XY error <=0.35 m, and every rotor <=0.01 N. Initial 1-2 s also requires zero
  thrust. For both support windows, the mean vertical force balance must be
  within 5% of weight, including measured normal force and the preceding
  interval's rotated rotor thrust and external vertical drag. Normal force
  alone need not equal weight under vertical wind.
- Wind must remain present in the captured descent and final support windows;
  verify the exact seeded sequence rather than an invented motion overlay.

Version 5 requires both contact and wind fields, fixed trajectory-control config,
the extra controller samples, all mission and wind events, and independently
recomputed metrics/outcomes. Compare normal force at sample i to applied inputs
at i-1. Existing schema versions remain readable. The 3D viewer combines the
fixed route view, collider, wind/drag/thrust/support vectors, mission phase and
measured landing metrics. It must not display the airborne experiment's 5-25 s
wind timing or claim a matched controller comparison for this new mission.

Affected requirements: REQ-WIND-MISSION, REQ-TURBULENCE, REQ-GROUND-MISSION and
REQ-REUSABLE-REPLAY. Paths: mission/control/physics and evidence modules, Isaac
worker, safe report tool, replay, tests and docs. Test analytic derivatives,
integrator bounds/reset/anti-windup, seed/wrench consistency, contact force timing,
tampered evidence, version compatibility and measured browser behavior. Then run
the actual GPU suite. Risks are controller windup at touchdown, hiding wind during
landing, incorrect force balance and overstating robustness from five seeds.

References: [NASA drag relation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-equation/),
[MIT quadrotor control notes](https://vnav.mit.edu/material/06-Control1-notes.pdf)
and [Isaac contact sensor](https://isaac-sim.github.io/IsaacLab/main/source/overview/core-concepts/sensors/contact_sensor.html).
These support the model/control structure; the specific gains and gates are
project decisions requiring measured validation.
