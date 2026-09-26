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
