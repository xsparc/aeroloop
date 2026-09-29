# Landing capture guard validation

Measured 2026-09-29 under [decision 017](../architecture/decisions/017-landing-capture-guard.md).
Frozen implementation `5db34436c0f4dd0846943d559afc4959cd541d8b`; flight-source digest
`1f6ad6e64b7989b15ddadbfaf3fdb8a90c054b9c831765a0ea287013029ba802`. All fresh captures use this clean revision.
The predictor, physics settings, native rate controller and original scoring limits remain unchanged.

The [full-rate summary](isaac-landing-guard-001.json) separates regression seeds
0/1/2 from previously unused seeds 101/202/303. Twelve fresh guarded regression
flights are compared with twelve retained AL-019 predictor-only flights. Six fresh
predictor-only and six fresh guarded flights form the unseen cohort: 24 new final
flights, 240,024 new control samples, 36 compared recordings. Every flight completed
10,001 samples. Development seed 73 is excluded from these counts.

| Cohort | Outage | Controller | Mission passes | Paired passes | Sustained recovery |
|---|---|---|---:|---:|---:|
| Regression | None | Prediction only | 3/3 | Reference | No outage |
| Regression | 0.5 s | Prediction only | 3/3 | 3/3 | 6/6 |
| Regression | 1 s | Prediction only | 3/3 | 0/3 | 4/6 |
| Regression | 2 s | Prediction only | 0/3 | 0/3 | 0/6 |
| Regression | None | Prediction + guard | 3/3 | Reference | No outage |
| Regression | 0.5 s | Prediction + guard | 3/3 | 3/3 | 6/6 |
| Regression | 1 s | Prediction + guard | 3/3 | 0/3 | 3/6 |
| Regression | 2 s | Prediction + guard | 0/3 | 0/3 | 0/6 |
| Unseen | None | Prediction only | 2/3 | Reference | No outage |
| Unseen | 2 s | Prediction only | 0/3 | 0/3 | 3/6 |
| Unseen | None | Prediction + guard | 2/3 | Reference | No outage |
| Unseen | 2 s | Prediction + guard | 0/3 | 0/3 | 3/6 |

All stress acceptance remains **false**. Mission pass counts do not improve.
One-second regression recovery drops from 4/6 to 3/6 windows. The guard stays opt-in. A successful
touchdown does not override original target tracking, landed-time, final-support
or sustained-recovery failures. No thresholds or deadlines were relaxed.

## Per-seed landing outcomes

The table retains two-second failures and the time at which the guard allowed
descent to resume. A missing resumption means no stable captured-state dwell
completed before physical contact/disarm or the end of the recording.

| Cohort | Seed | Controller | Touchdown horizontal speed (m/s) | Landed time (s) | Guard resume (s) | Mission |
|---|---:|---|---:|---:|---:|---|
| Regression | 0 | Prediction only | 1.351 | 42.220 | — | failed |
| Regression | 1 | Prediction only | 0.551 | 41.395 | — | failed |
| Regression | 2 | Prediction only | 0.563 | 41.530 | — | failed |
| Regression | 0 | Prediction + guard | 0.163 | 47.290 | 44.900 | failed |
| Regression | 1 | Prediction + guard | 0.714 | 42.155 | — | failed |
| Regression | 2 | Prediction + guard | 1.034 | 42.360 | — | failed |
| Unseen | 101 | Prediction only | 1.677 | 43.605 | — | failed |
| Unseen | 202 | Prediction only | 0.935 | 42.165 | — | failed |
| Unseen | 303 | Prediction only | 0.953 | 43.620 | — | failed |
| Unseen | 101 | Prediction + guard | — | — | 49.940 | failed |
| Unseen | 202 | Prediction + guard | 0.256 | 48.070 | 45.480 | failed |
| Unseen | 303 | Prediction + guard | 0.171 | 46.985 | 44.760 | failed |

## Interpretation and continuity

Unseen no-outage seed 101 already fails with prediction alone: touchdown
horizontal speed is 0.541 m/s against the 0.5 m/s limit, and final horizontal
offset is 0.397 m against 0.35 m. The inactive guard exactly retains that failure.
The unseen reference therefore passes two of three missions, not three.

The guard changes commands after capture age reaches 0.6 s during landing
(40.580 s in these outage cases). Holding that command cannot guarantee actual
height while prediction is inaccurate. The regression two-second seeds 1/2
contact the ground before a stable-capture descent resumes, and touchdown
horizontal speed is worse than with prediction alone. Seed 0 improves touchdown
speed but still fails the original overall mission criteria. These outcomes do
not justify enabling the guard by default. Unseen guarded seed 101 never touches
down within 50 s; seed 202 lands after the deadline at 48.070 s. Seed 303 improves
touchdown speed but retains a peak tracking-error failure.

All nine required inactive-guard traces are exactly unchanged after removing
only guard metadata: regression no-outage/500 ms and unseen no-outage. Their
metrics and mission events also match exactly. Every compared sample before
activation is unchanged. Configuration differs only by the explicit guard model;
native controller, dependency lock and simulator versions match. The retained
AL-019 full study revalidates to exactly the same summary.

Development seed 73 activated at 40.580 s, resumed at 46.280 s and landed at
49.010 s. It missed the 48 s landing deadline and failed the fixed final-support
window after the delayed descent.
No parameters were changed after development or after inspecting final outcomes.

## Runtime and demonstration

Runtime: Isaac Sim `6.1.0.0`, Isaac Lab distribution
`17.0.2`, Torch `2.11.0+cu128`.
All new flights were monitored. Both unseen two-second cohorts were paced;
other new flights ran without wall pacing at the same 200 Hz physics/control
cadence. Wall timing excludes interpreter startup and evidence serialization.
The six paced trials measured real-time factors 0.999990–0.999999
and maximum lag 61.669 ms. These are soft real-time observations.

The [working demo](../landing-guard.md) contains 18 paired comparisons with
separate cohort/seed controls, measured 3D poses, synchronized playback, original
scheduled versus commanded altitude, and guard activation/resumption chapters.
Display samples are 20 Hz plus event/outage/guard neighbors; all scores use the
full 200 Hz recordings. All 19 exported payload checksums were independently
verified. Actual measured browser playback and live 3D monitoring were inspected;
failed flights and unavailable transitions remain explicit.

## Verification and limits

- 128 CPU tests: 127 passed; one Windows symbolic-link permission skip.
- Two native CTest checks, 23 frontend tests and three legacy viewer tests passed.
- 27 Chromium browser tests passed; three conditional legacy evidence tests skipped.
- Production build, dependency lock, public-source/privacy and dated AeroLoop
  evidence checks passed. Generic OpenSteward static/strict checks still report
  only their known fixed project-identity constraint; the registry remains AeroLoop.
- Full-rate reconstruction verifies captures, predictor, guard transitions,
  controller setpoints, actuator behavior, wind, mission supervision and metrics.
  Truncated recordings, mixed sources, configuration differences and corrupt
  display data cannot produce accepted comparisons.

Synthetic wind/captures, ideal attitude/rates and contact supervision remain.
The small unseen cohort does not prove robust stability. AL-010 yaw refinement
remains open. This work does not validate hardware flight. The next bounded
investigation should separate loss of altitude feedback from horizontal capture
outages and measure prediction error through premature contact before changing
the descent policy or claiming a failsafe.
