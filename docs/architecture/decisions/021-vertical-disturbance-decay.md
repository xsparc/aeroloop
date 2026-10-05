# 021: Test fading vertical disturbance prediction

Accepted 2026-10-06 after PR 24, baseline
`ef5290f41663143fdedd60028fb7c47155035276`.

AL-024 tests one opt-in predictor change and nine related investigation tools.
Retained landing traces show that the main predictor holds a vertical disturbance
estimate through two-second outages, while the physical gust changes. This is a
candidate explanation for velocity error during descent, not proof of causality.

During a missing capture, scale only the vertical disturbance used for propagation
by `exp(-max(0, age_s - 0.015) / 0.2)`. Preserve the learned anchor, horizontal
components, fresh-capture updates, nominal rotor/gravity propagation, expiry and
all original inputs. The first missing scheduled capture has age 0.020 s. Normal
0–15 ms capture holds remain identical. No truth force, future sample, target or
contact signal enters the predictor. Keep the original predictor as the default.
The 0.2 s time constant is fixed before development measurements and matches the
existing disturbance-learning time scale; it is not calibrated wind dynamics.

[Autoregressive models](https://otexts.com/fpp3/AR.html) provide a model for
declining dependence on older state, while [PX4's estimator guide](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf)
describes model propagation between measurements. The proposed exponential
forgetting is an engineering hypothesis, not an implementation of PX4's EKF.

Freeze the experiment before new flights:

- Combined horizontal noise + 40 ms delay only; existing 200 Hz physics/control,
  50 Hz captures, wind/contact mission, two-second outages at 18 and 40 s.
- Development: candidate seed 73, no outage and two-second outage; excluded.
- Regression: candidate seeds 0/1/2, both profiles, against six retained AL-022
  combined-quality baselines. Require exact no-outage and pre-outage continuity
  after removing only decay telemetry.
- Additional predeclared cohort: seeds 401/503/607, baseline and candidate, both
  profiles (12 flights). These seeds have not been inspected before this protocol.
- Total final new recordings: 18. Freeze clean committed source for every worker.
  Monitor all flights; wall-pace all outage flights. No omitted physics steps.
- Preserve every failure. Mission, same-mode outage-pair and sustained-recovery
  acceptance use their existing full-rate definitions. Cross-mode differences
  are descriptive and do not replace acceptance. No tuning after final results.

Ten acceptance features:

1. Opt-in vertical disturbance decay, with strict evidence version 12.
2. Live anchor/effective disturbance and scale telemetry, independently validated.
3. Baseline/candidate paired 3D for both profiles and both declared cohorts.
4. Touchdown-relative playback as well as common simulation time.
5. Truth, feedback and target vertical-velocity comparison.
6. Vertical position, velocity and feedforward control-term inspection.
7. Contact force, clearance, vertical-speed eligibility and dwell inspection.
8. Requested versus realized rotor thrust and wind-force plots.
9. Bounded, reproducible selection links within the local demo.
10. Comparison JSON export including full-rate outcomes and selected-window metrics.

Allowlisted, checksummed, bounded same-origin exports preserve historical sources.
Legacy recordings and demos retain their contracts. CPU reconstruction must reject
rehash tampering of decay state or controller outputs; fresh-capture behavior must
remain identical. Verify actual PhysX flights, live 3D, all demo cases, relative
time bounds, corrupted links/data, exports and mobile layout. Update the plan
with measured results, including regressions. AL-010 remains open. No hardware
flights, releases, default enablement or changes to acceptance limits.
