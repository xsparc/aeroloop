# 018: Separate horizontal and altitude feedback availability

Accepted 2026-09-29 after PR 21, baseline
`3d0ede1616d8c62cd38d111546010bec66f06d12`.

AL-021 isolates feedback availability before changing the descent policy. Add an
opt-in, noiseless 50 Hz synthetic capture channel with zero transport delay and
phase zero. Select either vertical position/velocity or horizontal
position/velocity. Mask unavailable components as null; hold captures between
updates. Replace only the selected components of the unchanged AL-019 predictor
output. The main predictor continues to receive its original full-vector
captures; the extra channel never enters its disturbance history. Record both
estimates and the actual composite controller input separately.

This is an availability ablation, not a rangefinder, GNSS, barometer or fused
estimator implementation. [PX4's estimator documentation](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf)
describes separate height sources and consistency checks. [Isaac Lab's sensor
API](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sensors.html#sensor-base)
supports acquisition periods distinct from physics ticks. These motivate the
experiment; neither validates this deliberately idealized channel.

The flag requires predictive feedback, fixed 200 Hz turbulent contact physics,
and either no outage or two-second main-channel outages at 18 and 40 seconds.
It excludes the landing guard. Keep gains, targets, rotor lag, wind, contact
supervision, metrics, paired/recovery gates and deadlines unchanged. No default
enablement, solver change, learning change or hardware flight. AL-010 stays open.

Freeze the following protocol before development seed 73 and final measurement:

- Development: both axis choices at two seconds, excluded from final results.
- Final: both choices, both profiles, regression seeds 0/1/2 and previously
  tested validation seeds 101/202/303: 24 fresh flights at one clean revision.
  The latter seeds were unseen in AL-020; they are not unseen here.
- Compare against retained predictor-only AL-019 regression and AL-020
  validation recordings. Require matching native/runtime/lock/common settings.
- Monitor every flight; wall-pace all twelve two-second flights. Keep capture,
  control and physics cadence fixed. Report wall timing separately.
- Require exact no-outage traces after removing only the new channel fields,
  and exact traces before the first outage. Retain all failed/incomplete runs;
  do not tune after inspecting final results.
- Compute horizontal and vertical applied-feedback errors from full-rate truth
  in each outage window, alongside unchanged mission, pair and recovery gates.

Use evidence version ten and live version six with strict masked-capture,
cadence, composite-input and controller reconstruction. Preserve older formats.
Extend the bounded, checksummed paired 3D demo with cohort and fresh-channel
selection, numeric feedback errors and explicit synthetic-channel labeling.
Acceptance requires reconstruction/tamper/cadence tests, legacy checks, actual
GPU measurements and working 3D playback; it does not require every stress gate
to pass. No personal host metadata or raw recordings enter the public repository.
