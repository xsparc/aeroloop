# Turbulence stabilization validation

AL-007 follows [decision 004](../architecture/decisions/004-turbulence-stabilization.md).
The development pair executed actual Isaac PhysX with seed 73 and unchanged
controller gains. Both 35 s runs completed, with 7,001 samples each. Position-hold
wind-window RMSE was 0.207036 m versus 16.263456 m for the attitude/altitude-only
reference. Held peak error was 0.530380 m, peak tilt 11.708434 degrees, and recovery
was 0.145 s after wind ended. The reference completed its altitude/attitude gates
while drifting; it did not meet the position-hold gates. These preliminary runs
recorded a modified working tree, not the final clean revision.

The final five-seed paired suite is pending. Acceptance is fixed before those
runs: held wind-window RMSE ≤0.5 m, peak error ≤1 m, tilt ≤25 degrees and recovery
within five seconds into a 0.10 m band with two-second dwell. Both modes must
retain altitude within 0.25 m, and each pair must show at least 75% RMSE reduction.

Local verification so far: 57 Python tests, seven viewer contract tests, three
legacy viewer tests and eight browser checks against the measured development
recordings passed. The browser suite found and then verified a fix for stale
comparison state during experiment switching. Two native tests passed after a
fresh build in the Visual Studio developer environment; an earlier ordinary shell
lacked the compiler's standard include setup. The production viewer build passes
with the existing optional Three chunk and standalone client-directive advisories.

Public-source and AeroLoop traceability checks pass. The generic OpenSteward
checker has its previously recorded hardcoded project-identity mismatch; AeroLoop's
identity is retained. No generic strict-check success is claimed.

This is a temporal OU wind engineering test with illustrative drag coefficients,
not a validated atmospheric spectrum or a hardware-flight result. The reference
uses the same wind velocities but experiences different drag as its trajectory
changes. The separate learned policy and existing CPU/Isaac regression evidence
are unchanged.
