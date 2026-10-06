# 023: Evaluate scheduled horizontal approach gains

Accepted 2026-10-06 after PR 26, baseline
`2ddf9115eea172b842546a3a9317f0109d0dfed2`.

AL-026 implements the requested ten features as one opt-in controller experiment
and comparison workspace:

1. Smooth horizontal position/velocity gains during the landing approach.
2. Validated live gain/blend telemetry and a received-sample gain history.
3. Paired 3D baseline/candidate playback over eighteen cases.
4. Original-gate change scorecards, including regressions and missing values.
5. Cumulative horizontal squared tracking-error curves from 34 s.
6. Cumulative squared horizontal acceleration-demand curves from 34 s.
7. Axis clipping occupancy and retained actuator-authority inspection.
8. Gust-relative time and gain-ramp, gust, contact and disarm chapters.
9. Cohort summaries and mission-failure/regression filters.
10. Evidence-version-bound review links and numeric comparison export.

AL-025 showed seeds 401 and 503 displaced before first contact. The hypothesis is
that higher horizontal approach gains reduce this displacement, with possible
increased control demand, noise response or overshoot. The
[PX4 tuning guide](https://docs.px4.io/main/en/config_mc/pid_tuning_guide_multicopter)
motivates inspecting tracking, overshoot and noise response when changing gains.
It does not specify these gains or validate this controller architecture.

## Frozen protocol before measurements

Use the AL-024 vertical-decay mode as baseline: 200 Hz physics/control, independent
horizontal noise plus 40 ms transport delay, main sample-hold or 2 s hold-dropout,
ideal attitude/rates/contact supervision. Require `--vertical-decay` for the new
`--approach-gains` flag. No default, Z gain, integral, acceleration limit, native
rate control, trajectory, rotor, wind, contact, sensor or acceptance changes.

While armed, let `u = clamp(t - 34, 0, 1)` and
`blend = u^3 * (10 - 15*u + 6*u^2)`. Horizontal position gain is
`2.5 + 1.5*blend` s^-2; velocity gain is `2.8 + 0.8*blend` s^-1.
Z gains stay 2.5 and 2.8. Disarmed controller outputs remain zero and reported
gains return to their inactive baseline values. Record `[blend, kp, kd]` as
`approach_control`, using recording schema 13 and live schema 9. Reconstruction
must independently check the schedule and resulting commands.

Development seed 83 uses both profiles and is excluded from final results.
Final regression seeds 0, 1, 2 and known stress seeds 401, 503, 607 each use six
fresh candidate flights and six retained AL-024 decay baselines. Additional
predeclared seeds 709, 811, 907 use twelve fresh flights covering both modes and
profiles. Total: 24 fresh final flights plus 12 retained, 18 pairs. No selection
by outcome and no tuning after final measurements. Keep all failed trials.
Freeze clean source before all workers; require identical final source for all
new flights and identical binary, lock and runtime across historical baselines.
Run every worker with monitoring and every outage worker with wall pacing.
Require exact first 6800 samples (t < 34 s) after removing only gain telemetry.

Original mission, same-mode outage-pair and sustained-recovery limits determine
acceptance. Cross-mode metrics are descriptive. Report each cohort separately;
do not promote the candidate to a default merely because some cases improve.
AL-010 yaw refinement stays open. No hardware flight or calibrated wind/sensor
claim is made.

Export every available landing sample from 34 s through the final sample.
Integrate squared horizontal truth-to-target error (m² s) and squared clipped
horizontal commanded acceleration (m²/s³) with left-endpoint rectangles on
[34,t). The terminal sample adds no interval. Demand is not physical energy.
Clipping occupancy is the fraction of observed intervals whose pre-clamp
horizontal demand exceeds 4 m/s² on either axis. Missing coverage is explicit.
Preserve all original gates, same-mode comparisons, source identities and hashes.

Scope: controller scheduling, recording/live schemas, study reconstruction,
demo/export, focused tests and plan/evidence updates. Verify legacy reconstruction,
pre-ramp continuity, disarm, tamper rejection, arithmetic independently, all real
payloads, 3D rendering, filters, links/export and narrow layout. Load only bounded
same-origin integrity-checked JSON. Publish numeric allowlisted evidence; keep
machine paths, logs, private artifacts and simulator assets out of Git.
