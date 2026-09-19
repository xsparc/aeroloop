# 001: Physics simulation without a PX4 flight requirement

Status: accepted

Date: 2026-09-20

The maintainer changed the original planning scope to omit genuine PX4 flights and
rely on physics simulation, while explicitly retaining Isaac simulation and training
in the MVP. This decision supersedes the planning kit's PX4 flight and in-PX4 custom
firmware gates. It does not remove measured simulation evidence or learning gates.

Build a CPU rigid-body model and standalone C++ controller first; then execute the
Isaac physics and learning experiments through their supported environments. Remove
Pegasus and PX4 from the critical path. Keep their integration as optional later work.
Use JSON for the compatibility lock to keep CPU tooling dependency-free.

Tradeoff: CPU experiments establish mathematical behavior in a simplified model only.
They do not establish autopilot integration, high-fidelity aerodynamics or physical
flight safety. Isaac integration remains incomplete until actual execution succeeds.

The initial technology scan confirms that the old Pegasus route adds a Linux-tested
integration dependency and Isaac 5.1 is now unsupported. These are reasons to isolate
candidate environments, not evidence that a newer untested stack works. See the
[direction brief](../../research/2026-09-20-direction.json) and
[compatibility report](../../compatibility.md).
