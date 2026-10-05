# Vertical prediction and descent comparison validation

Protocol: [ADR 021](../architecture/decisions/021-vertical-disturbance-decay.md).
The original predictor remains the default. The fixed candidate is an experiment;
completion of the study does not imply all numerical acceptance gates passed.

Source: `b75bcc85474626e60beee3f6a83b6f0e27874b40`, clean for all 18 new final flights.
Flight source digest: `ee1f83b3e9e3809e5654a29c452d05ad7666537679e29402de3cef9e1d2db32e`.
Six regression baselines retain their AL-022 source. Development seed 73 ran both
profiles and passed both missions; it is excluded from every final count. All
outage flights were wall-paced and all workers recorded monitor timing.

## Original acceptance results

| Cohort | Mode | Profile | Missions | Outage pairs | Recovery windows |
|---|---|---|---|---|---|
| regression | baseline | sample-hold | 3/3 | 0/0 | 0/0 |
| regression | baseline | hold-dropout-2000ms | 2/3 | 0/3 | 3/6 |
| regression | candidate | sample-hold | 3/3 | 0/0 | 0/0 |
| regression | candidate | hold-dropout-2000ms | 3/3 | 2/3 | 4/6 |
| additional | baseline | sample-hold | 1/3 | 0/0 | 0/0 |
| additional | baseline | hold-dropout-2000ms | 1/3 | 3/3 | 5/6 |
| additional | candidate | sample-hold | 1/3 | 0/0 | 0/0 |
| additional | candidate | hold-dropout-2000ms | 1/3 | 3/3 | 5/6 |

Zero pair/recovery denominators mean not applicable for the no-outage reference.
Each mode is compared with its own no-outage flight of the same seed. The study
retains the 0.15 m peak separation, 0.05 m RMSE-change and 0.5 s landing-shift
limits, and the 0.05 m sustained-recovery band with a 5 s deadline.

All six candidate no-outage flights exactly reproduce their matching baseline
samples, events and metrics after removing only decay telemetry. Every outage
pair exactly matches its baseline through the 3,600 samples before 18 s.

## Diagnostic interpretation

The machine-readable [report](isaac-decay-001.json) includes original full-rate outcomes,
cross-mode descriptive measurements and separately audited pre-contact velocity
errors. The common pre-touchdown window begins at 40 s and ends at the earlier
of either flight's first touchdown and 42 s. This avoids measuring a candidate's
post-contact drift against a baseline still in flight. It is descriptive, not a
new acceptance criterion. The demo also shows the complete landing window,
including rotor spin-down and contact dwell.

## Verification

- CPU suite: 146 cases; the single sandbox socket-bind failure passed when the seven monitor tests were rerun with loopback access. One Windows symlink case remains skipped.
- Native CTest: 2/2 passed. Frontend contracts: 34/34 passed.
- Browser suite: 40 passed, three existing conditional legacy-fixture skips.
- Production demo build, dependency lock, public-source and project-evidence checks passed.
- Independent raw/export audit checked all 240,024 scalar rows, control terms, world thrust, contact dwell, decay arithmetic, checksums and common pre-touchdown window arithmetic.
- Every real pair passed the browser contract and rendered two 3D canvases. Touchdown alignment, restored selection links, playback and JSON download were exercised. The 320 px layout fit without horizontal overflow.
- Actual final PhysX monitoring rendered 3D during both outages and after capture resumption, with no browser errors.
- The generic OpenSteward static/strict checker retains its known `project.identity` mismatch: it requires its own project name. AeroLoop's project-specific strict evidence check passes. No identity was changed to suppress this limitation.

All local raw recordings, logs, screenshots and generated bundles remain ignored.
The public report contains allowlisted source hashes, versions and measurements.

## Limits and follow-up

No gain, threshold or decay tuning followed final measurements. The predeclared
additional seeds are a small bounded check. Synthetic noise/delay, ideal attitude,
rates and contact supervision, simplified aerodynamics and unresolved AL-010 yaw
refinement prevent a hardware-flight or general robustness claim. See the updated
[roadmap](../roadmap/implementation-roadmap.md) for the next measured priority.
