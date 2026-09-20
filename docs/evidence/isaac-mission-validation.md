# Ground-contact mission validation

AL-008 follows [decision 005](../architecture/decisions/005-ground-contact-mission.md).
The final suite passed **5/5 actual Isaac PhysX missions** at clean implementation
commit `d4728f57eb0c0c65e7950987f09337b4597c4fca`. The
[allowlisted summary](isaac-mission-001.json) retains all trials, events, full-rate
metrics, contact parameters and source/configuration hashes. Each trial recorded
10,001 samples over 50 s at 200 Hz (50,005 total); worker wall time was 170.645 s.
The guarded worker and independent report verification both completed successfully.
No gains or acceptance thresholds were tuned against final seeds 0–4.

| Seed | Tracking RMSE, 5–50 s (m) | Peak tracking error (m) | Pre-contact descent speed (m/s) | Outcome |
| --- | ---: | ---: | ---: | --- |
| 0 | 0.212220 | 0.545284 | 0.048367 | Passed |
| 1 | 0.212213 | 0.545272 | 0.048367 | Passed |
| 2 | 0.212227 | 0.545254 | 0.048367 | Passed |
| 3 | 0.212206 | 0.545304 | 0.048367 | Passed |
| 4 | 0.212180 | 0.545278 | 0.048367 | Passed |

Every trial reached all four waypoint holds within 0.15 m for one continuous
second. The recorded waypoint times mark the start of that successful dwell.
Liftoff occurred at 3.600 s, first landing contact at 44.770 s and the motor-disarm
latch at 44.855 s. No unexpected airborne contact occurred. Peak tilt was
1.523428 degrees; maximum collider penetration was below 0.001 mm in this ideal
solver setup. These numerical values do not imply equivalent physical accuracy.

Over the final 48–50 s, mean normal support was 9.806650 N, matching the declared
1 kg weight. Maximum speed was 0.000111 m/s, XY error below 0.000560 m and
rotor thrust below 0.01 N. Initial 1–2 s support also matched weight with stopped
motors. Across the full suite thrust ranged from 0 to 2.513658 N per rotor and
no allocation saturation occurred. Contact normals exclude friction; the reset
sample has zero contact impulse before the first integrated interval. Touchdown
speed uses the preceding sample rather than the velocity already stopped by impact.

The preliminary seed-73 PhysX trial also passed all gates, with 0.545309 m peak
tracking error, 1.523402 degrees peak tilt and 0.048367 m/s touchdown descent
speed. That development capture used a modified working tree and is separate
from the final committed suite. The only seed variation is a small initial XY
offset; this experiment does not establish broad mission robustness.

Local verification passed: 63 Python tests, eight React contract tests, three
legacy viewer tests and two native CTest checks. Seven browser checks passed
against the final mission export, including contact readings, disarm, mobile,
3D lifecycle, event jumps, integrity rejection and fallback. Eight browser checks
passed on the retained wind bundle and six on the CPU bundle. Scenario-specific
checks are explicitly skipped when their recordings are absent. All 15 retained
version 2 rotor runs and 10 version 3 wind runs revalidated with the new reader.
The final version 4 mixed bundle also displayed the existing wind comparison
without browser errors. The 3D route and landed views were inspected in light
and dark themes. Inspection caught and corrected two display-label encoding
errors after the physics capture; no physics change or rerun is attributed to that fix. Production build passed with existing optional Three chunk-size
and standalone client-directive advisories.

Public-source checks and the dated AeroLoop evidence registry check pass. Both
static and dated strict generic OpenSteward checks report only their existing
hardcoded `project.identity` mismatch. AeroLoop's real identity is preserved;
no generic strict-check success is claimed.

This is a calm, perfect-state mission with illustrative cuboid contact geometry,
friction and restitution. Wind during the route, battery, ground effect, sensor
noise and propeller aerodynamics are outside this experiment. The separate
learned-policy task and existing CPU and airborne-wind baselines are unchanged.
