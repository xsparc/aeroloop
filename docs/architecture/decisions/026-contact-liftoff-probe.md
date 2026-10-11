# 026: Inspect contact impulses at liftoff

Accepted 2026-10-11 under the post-PR-31 ten-feature implementation and draft
PR request. Baseline `56c7df609d54f212d289958d177e2578d4378b87`.

AL-029 isolates the negative ground normal observed in AL-028. It adds:

1. A bounded three-second probe using the existing native controller, turbulent
   mission, seed 301, ideal feedback and stationary kinematic ground.
2. Physics-substep contact impulses, points, normals and separation distances.
3. Friction-anchor impulses and positions with independent capacity checks.
4. Aggregate, filtered and reconstructed contact-force cross-checks.
5. Substep translational momentum balance and signed-normal incident detection.
6. A matrix of 5, 2.5 and 1.25 ms physics with TGS external forces applied every
   iteration or once per step; control remains 200 Hz.
7. Two fresh runs of each matrix cell and numerical repeatability comparisons.
8. Incident navigation, focused time windows and detailed contact tables.
9. Synchronized 3D collider/contact replay and force, clearance and balance plots.
10. Hash-verified bundles, numerical CSV/JSON exports and digest-bound review links.

## Boundary and acceptance

The probe uses the original flight loop but stops before mission scoring and
recording. Its separate diagnostic schema permits signed measurements and never
certifies a flight. Original flight contracts, controller defaults, materials,
dependency pins and acceptance limits remain unchanged. No physical flights.
AL-010 remains open. Requirements: REQ-DRONE-CONTROL, REQ-FLIGHT-EVALUATION and
REQ-REUSABLE-REPLAY. Main paths: `contact_probe.py`, the existing Isaac worker,
CLI adapters, replay workspace, focused tests and evidence documents.

Commit clean capture source before running any worker. Execute all twelve
declared cases, retaining failures; do not select a better seed. Compare the
default-mode control-rate states to the retained seed-301 captures over [0,3].
If source repair is necessary, record excluded development attempts and rerun
the entire final matrix from one clean revision. No convergence or sensor-versus-
solver causal conclusion without supporting measurements.

## Measurement and risks

The [tensor API](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/107.3/extensions/runtime/source/omni.physics.tensors/docs/api/python.html)
uses `dt` to convert impulses to forces. Read detailed buffers with `dt=1` to
retain impulses. Copy all returned buffers before another API call: installed
backend contact/friction counts share storage. Reconstruct normal impulse as
sum(scalar impulse * geometric normal) and friction impulse by summing anchors.
Compare each to the sensor force multiplied by the physics timestep.
Substep momentum residual is mass * velocity change minus applied force impulse,
normal impulse, friction impulse and gravity impulse. Row t covers (t-dt,t].
Negative measurements remain visible, including those that violate flight rules.

The deprecated per-step force option is a diagnostic comparison, not a proposed
default. The [PhysX dynamics reference](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/docs/RigidBodyDynamics.html)
describes contact patches and friction anchors; contact points and anchors must
not be treated as interchangeable. Backend API agreement does not independently
validate the solver. No physical calibration, angular momentum or contact energy
claim. Signed impulses alone do not establish an attractive physical force.

Validate synthetic signed impulses, buffer lifetime and bounds, corrupted or
incomplete captures, exact cohort coverage, frontend contracts, actual measured
browser replay/mobile/exports, independent arithmetic and retained trajectories.
Run CPU/native/frontend/browser/build/privacy/project-evidence checks and record
the generic governance checker's known project-identity incompatibility.
