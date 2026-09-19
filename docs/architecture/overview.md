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

PX4 flight execution and Pegasus transport are no longer MVP dependencies. No CPU
result can stand in for Isaac validation. The CPU body-wrench model does not model
propeller aerodynamics, individual motors, estimation error, contact or hardware.

Runtime Python has no third-party dependencies for CPU work. C++14 builds through
CMake; Isaac retains a separate Python environment. Configuration uses strict JSON
to avoid adding a YAML parser to the CPU trust boundary. Dependency candidates and
validated environments are separate states. Missing capabilities fail their gates.

Public evidence uses constrained identifiers and fields, source/configuration hashes,
frame metadata and finite numeric values. Private inputs and execution state remain
ignored. Public bundles contain no raw host metadata or arbitrary source paths.

See [MVP design](../DESIGN_AND_MVP_PLAN.md), [decision 001](decisions/001-physics-first.md)
and [roadmap](../roadmap/implementation-roadmap.md).
