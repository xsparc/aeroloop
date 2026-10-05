# Architecture

AeroLoop is a simulation-only control and learning laboratory. Explicit maintainer
instructions govern scope; this architecture, the roadmap, accepted decisions,
code/tests and supporting documentation describe the implementation in that order.
The evidence registry is a derived index, not a second source of authority.

The revised MVP has three layers:

1. A fixed-size C++ rate controller and a CPU rigid-body physics harness for rapid
   deterministic feedback. World coordinates are ENU; body coordinates FLU;
   quaternions are wxyz and rotate body into world. All physical quantities use SI.
2. Isaac Sim physics execution and a separate Isaac Lab hover learning experiment.
   Actual training, saved checkpoint reload and held-out evaluation remain required.
3. A local browser replay of checksummed, measured simulation results. No network
   vehicle control or public compute service is provided.

The reusable `web/replay` React component consumes the same CPU export as the
dependency-free local replay. Hosts pin the export index hash; selected documents
are streamed within bounds, checked and validated before display. Three.js is a
lazy peer dependency with an original schematic mesh. Renderer coordinates are
`(east, up, -north)`; recorded attitude is interpolated before this basis change.
Playback pauses offscreen and on page hiding. Static text, controls and the SVG
schematic remain independent of WebGL. See [integration acceptance](../replay-integration.md).

The subsequent [drone-development slice](../drone-development.md) runs the native
controller against a four-rotor X actuator with lag in Isaac PhysX. Version 2
recordings identify this backend and retain rotor commands, applied thrust and
moments. The exporter recomputes these fields, while the viewer shows measured
3D pose, trajectory and rotor thrust. Version 1 CPU and the separate learned
hover task retain their original contracts.

Version 3 adds the explicitly declared temporal wind model, relative-velocity drag
at an offset pressure centre and a same-wind reference with horizontal position
hold disabled. Evidence validates the sampled wind, resulting force/moment and
controller mode before export. The 3D viewer displays wind/drag vectors, follows
the aircraft and offers a verified reference error comparison. See
[decision 004](decisions/004-turbulence-stabilization.md).

Version 4 adds a calm ground-contact mission using the same controller and rotors.
A static floor and cuboid body provide physical support. Measured normal contact
force, oriented clearance and vertical speed drive a landing latch; disarming
requests zero rotor thrust while preserving motor lag. The evidence verifier
reconstructs mission phases, targets, events and gates; the viewer depicts the
collider and route. See [decision 005](decisions/005-ground-contact-mission.md).

Version 5 combines route tracking, wind and physical ground contact. Analytic
trajectory velocity/acceleration and bounded horizontal integral feedback drive
the existing attitude controller, native rate core and rotors. Evidence verifies
the feedback recurrence and interval-aligned support balance. Wind remains active
after contact-latched disarming; the replay shows both wind and support vectors.
See [decision 006](decisions/006-turbulent-contact-mission.md).

The separate [physics accuracy suite](../physics-accuracy.md) verifies force
isolation cases at 200/400/800 Hz against independent continuous-time solutions.
Its strict traces and public summary preserve numerical failures and distinguish
absolute error from timestep refinement. The default TGS mode and a deprecated
per-step force diagnostic are reported separately; neither changes the existing
flight scenes. See [decision 007](decisions/007-physics-accuracy-suite.md).

PX4 flight execution and Pegasus transport are no longer MVP dependencies. No CPU
result can stand in for Isaac validation. The CPU body-wrench model does not model
propeller aerodynamics, individual motors, estimation error, contact or hardware.

The [live flight test station](../live-flight-tests.md) holds controller, wind and
motor updates at 200 Hz while testing PhysX at 200/400/800 Hz. A separate read-only
loopback server serves bounded, provisional snapshots and a live 3D monitor.
Wall pacing reports lag without changing simulation dt or skipping updates.
Full recordings, not live frames, determine mission acceptance. See
[decision 008](decisions/008-live-physics-flight-tests.md).

Runtime Python has no third-party dependencies for CPU work. C++14 builds through
CMake; Isaac retains a separate Python environment. Configuration uses strict JSON
to avoid adding a YAML parser to the CPU trust boundary. Dependency candidates and
validated environments are separate states. Missing capabilities fail their gates.

Public evidence uses constrained identifiers and fields, source/configuration hashes,
frame metadata and finite numeric values. Private inputs and execution state remain
ignored. Public bundles contain no raw host metadata or arbitrary source paths.

See [MVP design](../DESIGN_AND_MVP_PLAN.md), [decision 001](decisions/001-physics-first.md)
and [roadmap](../roadmap/implementation-roadmap.md).

The [flight evaluation explorer](../flight-evaluation.md) re-verifies the complete
study and separates full-rate acceptance from event-preserving display samples.
A compact pinned index binds selected-pair manifests, metrics, events and replay.
The read-only explorer shares one timeline between two optional 3D views and
retains every trial, missing measurement and failure. Decision 009 records this
presentation boundary; it does not extend the numerical accuracy claim.

The [yaw diagnostic suite](../yaw-diagnostics.md) separates constant-spin and
torque responses from flight control, comparing cached and direct world-frame
read channels at three timesteps and two solver iteration counts. Its strict
verifier preserves diagnostic outcomes separately from the original refinement
criterion. It introduces no change to flight scene configuration. See
[decision 010](decisions/010-yaw-orientation-audit.md).

The [arithmetic study](../yaw-arithmetic.md) compares isolated CUDA recurrences
with a fresh full-rate yaw matrix. A CPU verifier separates arithmetic controls,
mechanism evidence and original physics acceptance. Selected runtime fingerprints
and clean source checks bind the captures; the experiment cannot change the
flight backend. See [decision 011](decisions/011-yaw-arithmetic-study.md).

Version 6 adds fixed seeded position/velocity observations and capture delay,
while physics truth continues to determine mission supervision and scoring.
The verifier reconstructs feedback and controller setpoints independently;
the live monitor labels delivered feedback separately from truth. See
[decision 012](decisions/012-observation-robustness.md).

Evaluation schema two reuses the paired explorer for twelve observation flights.
It binds all four fixed profiles and preserves full-rate scores, failed trials
and historical source identity. Pose interpolation is separate from held
feedback snapshots, whose capture and delivery times stay visible. The legacy
single-run exporter remains unchanged. See
[decision 013](decisions/013-observation-replay.md) and the
[observation explorer](../observation-evaluation.md).

Version 7 isolates capture cadence and missing position/velocity samples from
observation noise and transport delay. A fixed capture schedule supplies held
feedback without altering the 200 Hz physics/control clock. Live telemetry
version 3 separates simulated source age from wall-clock monitor freshness;
the full-rate timing report checks paired recovery dwells. Recorded replay of
this family is explicitly unsupported. See
[decision 014](decisions/014-observation-timing.md).

The [outage duration study](../outage-recovery.md) extends the strict timing
profile allowlist without changing recording or live data shapes. An equal-cadence
reference isolates outages of 250/500/1000/2000 ms. Its separate report preserves
mission and paired failures and scores the final uninterrupted recovery interval;
the earlier timing report retains its original first-dwell semantics.


Version 8 adds bounded predictive feedback ahead of the unchanged trajectory
and native rate controllers. The predictor consumes only successful captures,
previous applied rotor thrust and measured attitude. Raw captures remain separate
from estimates; CPU evidence validation reconstructs each update and setpoint.
Live schema four exposes prediction state alongside capture age. A dedicated
checksummed paired export presents retained version-seven and fresh version-eight
flights without changing the older replay contract. Its full-rate outcomes remain
separate from 20 Hz display samples. See [decision 016](decisions/016-predictive-outage-demo.md)
and the [working demo workflow](../predictive-feedback.md).

The opt-in [landing capture guard](decisions/017-landing-capture-guard.md) changes descent commands using capture age and captured horizontal stability. Version-nine evidence preserves original scheduled targets for scoring and reconstructs separate command targets and derivatives. The predictor, physics, contact supervisor and all acceptance limits remain unchanged; the [paired demo](../landing-guard.md) separates regression and previously unseen seed cohorts.

AL-021 adds an opt-in masked 50 Hz synthetic axis channel at the controller
input. Main capture/predictor state is unchanged; version-ten evidence and
version-six live packets record the composite input separately and reconstruct
it before accepting results. See [ADR 018](decisions/018-axis-availability.md).


AL-022 adds the opt-in [horizontal quality model](decisions/019-horizontal-channel-quality.md).
It acquires masked position/velocity at 50 Hz, applies seeded noise at capture,
and delivers buffered captures with a fixed transport delay. Evidence v11
reconstructs that pipeline and controller inputs; live v7 displays delivered age
separately from main captures. The schema-4 paired demo retains full-rate mission,
same-quality outage-pair and sustained-recovery gates. All older contracts remain
available. See the [operator guide](../horizontal-quality.md).

AL-023 adds a separate [flight diagnosis workspace](../flight-diagnosis.md) over
the retained quality matrix. Its bounded schema-one export carries every 200 Hz
numeric sample, separate display poses, original gates and same-quality recovery
results. State-separated errors distinguish airborne descent, contact and
motors-off drift without changing any flight contract. Export reconstructs the
original evidence; the browser validates pinned hashes and derived arithmetic.
See [ADR 020](decisions/020-flight-diagnosis.md).
