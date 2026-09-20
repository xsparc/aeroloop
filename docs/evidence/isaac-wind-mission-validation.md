# Turbulent contact mission validation

AL-009 follows [decision 006](../architecture/decisions/006-turbulent-contact-mission.md).
The final suite passed **5/5 actual Isaac PhysX missions** at clean implementation
commit `19fb20d14a1234a69c0307507a1b7ca27262ae7c`. The
[allowlisted summary](isaac-wind-mission-001.json) retains all trials, events,
full-rate metrics, wind/control/contact configuration and source hashes. Each
trial recorded 10,001 samples over 50 s at 200 Hz (50,005 total). Worker wall time
was 204.559 s. Both the guarded worker and independent report verifier completed
successfully. No gains or acceptance thresholds were tuned on final seeds 0-4.

| Seed | Tracking RMSE, 5-50 s (m) | Peak error (m) | Pre-contact descent (m/s) | Pre-contact horizontal speed (m/s) | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 0.109192 | 0.363917 | 0.065442 | 0.241587 | Passed |
| 1 | 0.115346 | 0.298739 | 0.083150 | 0.062748 | Passed |
| 2 | 0.132522 | 0.380635 | 0.053659 | 0.134850 | Passed |
| 3 | 0.165778 | 0.331575 | 0.072595 | 0.171616 | Passed |
| 4 | 0.123177 | 0.440786 | 0.059471 | 0.110764 | Passed |

Every trial reached all four waypoint holds within 0.35 m for one continuous
second. Dwell began at 7, 15, 23 and 31 s. No unexpected contact occurred between
liftoff and the scheduled descent. Peak tilt was 14.241 degrees and maximum
penetration was below 0.004 mm in this ideal solver setup. These values do not
establish equivalent physical accuracy. No rotor allocation saturation occurred.

First contact and sustained landing are distinct: seed 3 first touched at
40.995 s during the descent gust, while its contact latch disarmed at 43.615 s.
Seed 0 first touched at 42.560 s and latched at 43.555 s. The remaining seeds
latched by 43.660 s. The controller therefore kept running through transient
contact instead of treating a single normal-force sample as completed landing.

Wind remained active through motor-off support. Peak wind speeds were
6.981-8.017 m/s across trials; final-window speeds ranged from 0.498 to 5.792 m/s.
During 48-50 s, the largest absolute mean vertical force-balance error was
0.000009624 N, speed stayed below 0.000206 m/s and rotor thrust below 0.01 N.
Final XY error ranged from 0.040 to 0.300 m, leaving only 0.050 m margin to the
0.35 m gate in seed 3. Initial support also passed with stopped motors. Normal
force excludes friction and is compared with the preceding interval's vertical
drag and rotated rotor thrust, not weight alone. Five seeds cannot establish
broad robustness or a precise-landing capability.

Development seed 73 passed with 0.083500 m RMSE, 7.588 degree peak tilt and
0.076716 m/s descent speed. That dirty-source development capture is retained
separately; it is not part of final acceptance. No gain tuning was needed.

Local verification passed: 69 Python tests, nine React contract tests, three
legacy viewer tests and two native CTest checks. Seven browser checks passed
against the final turbulent mission, seven against the earlier calm mission and
eight against the airborne wind/reference bundle. Three, three and two checks,
respectively, were explicitly skipped because they require another scenario as
the first recording. All 30 retained rotor, wind and calm-mission recordings
revalidated with the new reader. The final schema-5 mixed bundle also displayed
the earlier paired wind comparison without browser errors. Descent and landed
3D views were inspected in light and dark themes. Production build passed with
existing optional Three chunk-size and standalone client-directive advisories.

Public-source checks and the dated AeroLoop evidence registry check pass. Both
static and dated strict generic OpenSteward checks report only their existing
hardcoded `project.identity` mismatch. AeroLoop's real identity is preserved;
no generic strict-check success is claimed. Raw recordings, logs and screenshots
remain ignored; the public summary contains only allowlisted measurements.

This is a temporal OU wind experiment with perfect state and illustrative drag,
cuboid contact geometry and friction. It does not validate atmospheric spectra,
propeller aerodynamics, ground effect, battery behaviour, sensors or hardware.
There is no matched controller ablation for this route. Separate learned-policy,
CPU, airborne-wind and calm-contact evidence retains its original scope.
