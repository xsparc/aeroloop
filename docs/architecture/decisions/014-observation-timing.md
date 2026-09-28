# 014: Measure feedback cadence and capture outages

Accepted 2026-09-27 after PR 17; baseline
`4ed026cb822e7cafebac86248819fb2b9ef22446`.

AL-017 tests outer-loop position/velocity feedback timing in fresh turbulent
contact missions. Keep the native controller, 200 Hz control/physics, actuator,
wind, runtime and original mission gates fixed. Attitude, angular rates,
acceleration and mission/contact supervision remain ideal. This is a synthetic
timing stress test, not a calibrated sensor, communications link or estimator.

Freeze four profiles before measuring: `timing-ideal` captures every 5 ms;
`sample-hold` captures every 20 ms; `dropout` captures every 5 ms except during
outages; `hold-dropout` combines 20 ms captures and outages. All capture phases
start at t=0. Outages suppress scheduled captures over [18,18.25) and [40,40.25)
seconds. Retain the last successful sample until the next scheduled capture;
do not replay missed captures, extrapolate state or add noise/transport delay.
Keep source sequence, capture time and actual age visible. Maximum age is 15 ms
for sample-hold, 250 ms for dropout and 275 ms for hold-dropout.

Use version-seven recordings with exact configuration and independent CPU
reconstruction of each held observation and controller setpoint. Preserve all
older schemas, profiles and reports. Extend live telemetry with a distinct
version and show scheduled capture cadence, current outage interval and source
age separately from monitor freshness. Recorded paired replay for this new
family is deferred; its export must fail explicitly. Live 3D uses PhysX truth.

Run development seed 73, then all four profiles across seeds 0/1/2 from one clean
revision. Monitor every trial and wall-pace hold-dropout. Retain failures and
incomplete trials without tuning final seeds. Require all unchanged mission
gates and 10001 control samples. Use the existing 0.15 m peak truth-position
difference, 0.05 m absolute RMSE change and 0.5 s landed-time difference bounds
against same-seed timing-ideal.

For each outage window, report the first post-window time when truth-position
difference from the reference stays at or below 0.05 m for one continuous second.
Recovery time is measured from the window end and must be at most five seconds.
Search only until the next outage or the recording end. Require the entire dwell
interval; absent/incomplete recovery is a failure, not zero. Report actual first
resumed capture and maximum observation age separately. These gates describe
these fixed stress cases, not general stability. The ideal traces must reproduce
the retained AL-015 ideal state/control results after removing observation data.

Acceptance also covers capture boundaries, held identity, restart independence,
altered feedback/configuration rejection, incomplete studies and recovery dwell
boundaries. Inspect fresh live 3D through an outage and resumed capture. Publish
only allowlisted metrics and hashes; keep raw traces/logs/figures local. No change
to the unresolved AL-010 yaw-refinement gate or learned hover policy is included.

Isaac Lab documents separately configured [sensor update periods](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sensors.html#sensor-base).
The explicit CPU sample-and-hold path makes timing reproducible without importing
Isaac during evidence verification. The chosen cadence and outage windows are
declared stress parameters, not values inferred from hardware.
