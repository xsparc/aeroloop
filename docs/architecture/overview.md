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
