# 019: Measure horizontal channel noise and delay

Accepted 2026-09-30 after PR 22, baseline
`0e13ceaa1685d03ef1d766d994a238985ddc12b3`.

AL-022 follows the ideal horizontal availability result with a fixed sensitivity
study. Keep the existing predictor, gains, targets, wind, rotor lag, physics,
contact supervision and all mission, paired and recovery limits unchanged.
The landing guard remains off. No default enablement or physical flight.

Four opt-in horizontal position/velocity channel qualities: ideal, noise, delay,
and noise-delay. All acquire at 50 Hz (phase zero), hold between acquisitions,
and mask altitude as null. Noise is independent per selected component and
acquisition: zero-mean Gaussian sigma 0.01 m position and 0.02 m/s velocity,
clipped at three sigma. Use a private seeded MT19937 stream, seed XOR 0x48515a;
position x/y then velocity x/y. Noise-only and combined share acquisition draws.
Transport delay is eight 200 Hz steps (40 ms); bootstrap with the first capture
at t=0, then deliver the newest capture whose delay has elapsed. Consequently
age is 40–55 ms after startup. No filtering or delay compensation is introduced.
Only delivered horizontal components replace the predictor output. The main
predictor history receives none of this channel's captures.

[PX4's estimator documentation](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf)
describes buffered, time-aligned measurement fusion. [Isaac Lab's noise API](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.utils.html#module-isaaclab.utils.noise)
provides additive Gaussian noise models. These motivate separate noise and
delay tests; the chosen values are sensitivity settings, not sensor calibration.

Freeze before any new measurement:

- Development seed 73, combined quality, both main-channel profiles; excluded.
- Final seeds 0/1/2, all four qualities, no outage and two-second main-channel
  outages at 18 and 40 seconds: 24 new flights at one clean revision.
- All final seeds are regression seeds, previously tested. No unseen claim.
- Monitor every flight and wall-pace all twelve outage flights. Preserve every
  physics step; report wall lag separately from simulation time.
- Require all six new ideal traces, metrics and events to equal retained
  AL-021 horizontal traces after removing only quality labels. Match runtime,
  native binary, lock and common settings across all runs.
- Each quality's outage pairs with its own same-quality no-outage run, preserving
  the existing pair/recovery definitions. Additionally measure truth differences
  against ideal quality, and horizontal/altitude feedback errors in both outages.
- Retain failures and incomplete recordings. Do not tune after final results.

Evidence version 11 and live version 7 strictly reconstruct noise draws, capture
timestamps, delivery age, composite input and controller outputs. Older contracts
remain unchanged. A bounded, checksummed schema-4 demo compares ideal versus
each impaired quality in nine outage pairs; no-outage results remain in the full
report. Acceptance requires cadence/bootstrap/seed/tamper tests, legacy checks,
measured GPU flights, actual live 3D monitoring and functional paired playback.
Stress gates need not pass to complete this diagnostic study. Public artifacts
contain no private host paths or raw flight logs. AL-010 yaw refinement stays open.
