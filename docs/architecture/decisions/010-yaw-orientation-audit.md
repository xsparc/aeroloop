# 010: Isolate yaw integration and pose sampling

Accepted 2026-09-27 under the requested autonomous development continuation.
Baseline: `2149c644c05e81792be1e302ea6fed00571bf307`.

Investigate decision 007's open yaw-refinement finding with a separate headless
PhysX experiment. Preserve the controller, mission scenes, dependency pins,
learning task and original numerical acceptance criteria. No hardware work or
runtime/vendor patch is included.

Run five 0.5 s cases: constant yaw rates +0.05, +0.5 and -0.5 rad/s, plus constant
body yaw torques +0.04 and -0.04 Nm from rest. Use the existing 1 kg cuboid with
Izz = 0.04 kg m², zero damping/sleep threshold, gyroscopic forces, gravity and
body +Z weight compensation. There is no floor contact. Set initial pose and
velocity once per case; never prescribe motion during integration.

Keep default TGS per-iteration force application and one velocity iteration.
Compare one and four position iterations at 200/400/800 Hz in six isolated
workers (30 cases). Four is the existing flight setting; one is diagnostic only.
Collect every step after `sim.step` and `body.update`: public cached pose/rate,
direct PhysX tensor pose/rate, and a repeated public quaternion read. Copy each
channel to host memory before another read can mutate shared device buffers.
Both rate channels use the world frame, which equals the body yaw axis in these
pure-yaw cases. The first development run compared body and world rates and
exceeded the 1e-7 read-channel gate through their float conversion difference.
Retain that failed trace under its original configuration; final reports require
the explicit matched-world-frame configuration. No acceptance limit changed.

Metrics include signed yaw error against the continuous solution, rate error,
quaternion norm, read-channel disagreement and yaw minus the trapezoidal integral
of measured rate. The latter is a diagnostic, not a replacement reference.
For pure yaw, signed angle is 2*atan2(qz,qw); all cases remain far from wrapping.
Retain sign and time history instead of only absolute maxima.

Acceptance declared before new GPU measurements:

- Complete finite traces, exact inputs/configuration and clean matching source
  across the six workers. Recompute all metrics/outcomes; retain failed cases.
- Read-channel/repeated-read differences <= 1e-7 rad or rad/s; quaternion norm
  error <= 1e-5; peak position drift <= 0.2 mm and speed <= 1 mm/s.
- Diagnostic absolute bounds: yaw error <= 2 mrad and rate error <= 0.5 mrad/s.
  These do not replace decision 007's tighter timestep-dependent yaw gates.
- Report the original four-iteration positive-torque refinement test unchanged:
  next peak yaw error <= 0.65*previous + 0.00002 rad. Keep AL-010 open if it fails.
- CPU tests reject corrupt, incomplete, mixed-provenance and invented outcomes.
  Freeze implementation before final GPU runs; inspect plots from verified data.

Affected requirement: REQ-PHYSICS-ACCURACY. Expected paths: independent yaw audit,
optional worker/launcher, report/plot tools, tests, roadmap and evidence registry.
Risks are cached buffers masquerading as fresh measurements, overstating a
backend diagnosis, and confusing iteration sensitivity with an approved fix.

The pinned Lab implementation documents pull-to-refresh pose caching and stable
device views. Compare those reads with the underlying tensor API. NVIDIA's
[rigid-body API](https://github.com/NVIDIA-Omniverse/PhysX/blob/main/physx/include/PxRigidDynamic.h)
describes initial angular velocity and solver iteration settings. Public
[integration source](https://github.com/NVIDIA-Omniverse/PhysX/blob/main/physx/source/lowleveldynamics/src/DyBodyCoreIntegrator.h)
is useful context, but is not proof of the exact GPU kernel in the installed
binary. Measurements must distinguish observation from a proposed root cause.
