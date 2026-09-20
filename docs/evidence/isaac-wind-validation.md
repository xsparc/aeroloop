# Turbulence stabilization validation

AL-007 follows [decision 004](../architecture/decisions/004-turbulence-stabilization.md).
The final suite passed **10/10 actual PhysX trials and 5/5 paired comparisons**
at clean implementation commit `9ca7c3bcbfda5e0428f25bd34eeca03352cbf373`.
The [allowlisted summary](isaac-wind-001.json) retains every trial, source/config
hash, model parameter and comparison. Each run contains 7,001 full-resolution
samples over 35 s (70,010 total); worker wall time was 238.561 s. The guarded worker
exited successfully, then the independent report command revalidated all ten
recordings. The five pairs have identical full-resolution wind hashes and source
provenance. Controller gains and thresholds were not tuned against final seeds.

| Seed | Position-hold wind RMSE (m) | Reference wind RMSE (m) | RMSE reduction |
| --- | ---: | ---: | ---: |
| 0 | 0.244962 | 20.446814 | 98.80% |
| 1 | 0.244825 | 18.473297 | 98.67% |
| 2 | 0.210782 | 19.646387 | 98.93% |
| 3 | 0.313083 | 24.325707 | 98.71% |
| 4 | 0.220752 | 17.617931 | 98.75% |

All held wind-window RMSE values are below 0.5 m. Worst held peak error was
0.890693 m and peak tilt 16.038129 degrees. Recovery times were 0–0.310 s into
the 0.10 m band with two-second dwell. Zero means the drone was already inside
that band when wind ended; the following dwell was still checked. It does not
mean instantaneous gust rejection. Both modes met the 0.25 m altitude limit.

The strongest sampled wind was 9.167106 m/s; held drag peaked at 2.737113 N.
Applied rotor thrust across the suite ranged from 2.303941 to 2.695848 N.
No allocator saturation occurred in this suite; existing unit tests exercise
saturation. The references kept altitude and attitude while drifting, and did
not meet the held-position gates. Every paired improvement exceeded the fixed
75% RMSE-reduction criterion over 5–25 s.

The earlier development pair executed actual Isaac PhysX with seed 73 and unchanged
controller gains. Both 35 s runs completed, with 7,001 samples each. Position-hold
wind-window RMSE was 0.207036 m versus 16.263456 m for the attitude/altitude-only
reference. Held peak error was 0.530380 m, peak tilt 11.708434 degrees, and recovery
was 0.145 s after wind ended. The reference completed its altitude/attitude gates
while drifting; it did not meet the position-hold gates. These preliminary runs
recorded a modified working tree, not the final clean revision.

Local verification: 57 Python tests, seven viewer contract tests, three legacy
viewer tests and eight browser checks against the final measured recordings
passed. Version 1 CPU and version 2 Isaac compatibility each passed six browser
checks; the two wind-only checks are intentionally skipped on those bundles and
on CPU-only hosted CI. All fifteen retained version 2 runs were revalidated.
The browser suite found and verified fixes for stale comparison state during
experiment switching and insufficient contrast in the new dark-theme panels.
The latter was a presentation-only change after the physics revision above.
Final measured 3D replay was inspected in both themes, including wind and drag
vectors, rotor meters, reference comparison and recovery. Two native tests passed after a
fresh build in the Visual Studio developer environment; an earlier ordinary shell
lacked the compiler's standard include setup. The production viewer build passes
with the existing optional Three chunk and standalone client-directive advisories.
No physics rerun is attributed to those presentation and evidence-only changes.

Public-source and AeroLoop traceability checks pass. The generic OpenSteward
checker has its previously recorded hardcoded project-identity mismatch; AeroLoop's
identity is retained. No generic strict-check success is claimed.

This is a temporal OU wind engineering test with illustrative drag coefficients,
not a validated atmospheric spectrum or a hardware-flight result. The reference
uses the same wind velocities but experiences different drag as its trajectory
changes. The separate learned policy and existing CPU/Isaac regression evidence
are unchanged.
