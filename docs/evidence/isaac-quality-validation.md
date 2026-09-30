# Horizontal quality validation

Validated 2026-09-30 for AL-022 under [ADR 019](../architecture/decisions/019-horizontal-channel-quality.md).
Implementation `c943f0b17733b8aa22fecc7a93705645c302147a`; flight source digest
`9c12e216fb86126423e2dca9745483974bf7e819a590e7a682805f79942a75b7`. All fresh recordings have clean source.
Runtime: Isaac Sim `6.1.0.0`, Isaac Lab distribution
`17.0.2`, PyTorch `2.11.0+cu128`.

Twenty-four final flights retain 240,024 physics/control samples. Six retained
AL-021 horizontal recordings establish exact ideal reproduction. Final seeds
0/1/2 are previously tested regression seeds. Development seed 73 passed both
combined-quality missions and is excluded from every final result. No parameters
changed after development or final inspection.

| Horizontal quality | No-outage missions | Two-second missions | Same-quality pairs | Recovery windows | Outage accepted |
| --- | --- | --- | --- | --- | --- |
| ideal | 3/3 | 3/3 | 0/3 | 3/6 | false |
| noise | 3/3 | 3/3 | 0/3 | 3/6 | false |
| delay | 3/3 | 3/3 | 0/3 | 3/6 | false |
| noise-delay | 3/3 | 2/3 | 0/3 | 3/6 | false |

Combined noise and delay failed seed 0's final horizontal support-position gate:
0.3511915527 m against the unchanged 0.350 m limit. The same seed measured
0.3434067195 m with ideal quality, 0.3407967490 m with noise alone, and
0.3494516154 m with delay alone. Its other mission gates passed. This is a
measured failure, not a reason to loosen the threshold.

Every quality still failed all three no-outage pair gates and passed only three
of six recovery windows. Landing-time differences of 1.225–2.385 s alone exceed
the existing 0.5 s pair limit. Horizontal noise/latency does not explain away the
underlying outage landing and recovery differences.

The full-window feedback errors include samples after physical contact and
disarming. A post-measurement diagnostic within the 40–42 s window illustrates
why phase matters: ideal seed 1's vertical error peaks at 0.068359 m before its 41.225 s touchdown, but
reaches 2.208247 m at 41.995 s in the landed phase with zero requested thrust.
The predictor has no ground-support model; that later error no longer drives
motors. The original all-window metrics remain intact. This descriptive split
does not change any acceptance criterion.

The [complete report](isaac-quality-001.json) retains every failed gate, no-outage
result, comparison against ideal quality, and per-axis feedback-error window.
Mission success, paired tracking and sustained recovery are distinct outcomes.
All stress gates accepted: **false**. Each outage pairs
with its own same-quality no-outage run; comparisons against ideal quality are
reported separately. The existing 150 mm peak difference, 50 mm RMSE-change and
0.5 s landing-time pair limits are unchanged. Recovery requires the final
uninterrupted 50 mm band for at least one second, starting within five seconds
of capture resumption.

All six new ideal traces, metrics and events exactly match AL-021 after removing
only quality labels. The controller, predictor history, wind, rotor model, physics
cadence, original targets and contact supervisor remain unchanged. Noise is added
only at horizontal acquisition (sigma 0.01 m and 0.02 m/s, clipped at three sigma).
The extra capture age reaches 15 ms for ideal/noise and 55 ms for delayed modes;
bootstrap supplies the first capture at t=0. Main-channel age reaches 2.015 s.

All flights were monitored and all twelve final outage flights were wall-paced.
No physics samples were skipped. Maximum paced lag: 0.095255 s;
real-time factor range: 0.999991–0.999998.
Wall timing is soft real-time and excludes startup and evidence serialization.

Verification: 137 CPU cases (136 passed, one Windows symlink skip), two native
CTest checks, 27 frontend tests, three legacy viewer tests and 36 browser cases
(33 passed, three conditional legacy-fixture skips). Production build, dependency
lock, dated AeroLoop evidence and public-source checks pass. Tests cover seeded
noise, delayed bootstrap/hold, masked components, reconstructed controller input,
rehashed tampering, corrupted or incomplete demo data, canceled loads, legacy
contracts, paired 3D and 320/390 px layout.

Actual development and final monitoring showed an active outage and resumed
captures in a 3D canvas with no page errors. Actual nine-pair playback passed the
frontend contracts; quality/seed selection, timeline, chapters, play/pause and two
3D canvases were exercised, including a narrow viewport. Screenshots and the
full-rate plot stay local.

An independent raw audit recomputed truth-target RMSE, horizontal noise draws and
delivery timestamps, applied-feedback errors, paired peak differences and final
recovery suffixes. It verified all ten payload hashes, exact retained ideal
samples and unchanged published baseline hashes, and the frozen source digest.
Demo index SHA256: `0c5230b171b95d4b6f297b6e716ddf72321511d0e69c3d97439d25280603e412`.
Export size: 31,066,849 bytes. The public report is identical to the verified export.

The generic OpenSteward static and strict checks retain only the known
`project.identity` finding because they require the plugin's own project name.
AeroLoop preserves its real identity; its dated traceability checker passes.

This fixed three-seed sensitivity study does not calibrate a sensor or validate a
fused estimator. Bias, outliers, variable latency, attitude noise and unseen-seed
robustness are not measured. Ideal attitude/contact supervision and independent
AL-010 yaw refinement remain unresolved. The channel stays opt-in. No physical
flights were performed. Use the [operator guide](../horizontal-quality.md) to
reproduce the working demo.
