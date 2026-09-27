# Observation timing study validation

AL-017 measured four capture-timing profiles across seeds 0, 1 and 2 in actual
Isaac Sim PhysX on 2026-09-27, under the frozen
[decision 014](../architecture/decisions/014-observation-timing.md) protocol.
The [full-rate report](isaac-timing-001.json) retains all twelve mission passes,
nine paired robustness passes and twelve post-outage dwell passes across 120012
control samples. Overall bounded timing-study acceptance: **true**.

| Profile | Captures per flight | Maximum feedback age | Position RMSE range (m) | Measured real-time factor |
| --- | --- | --- | --- | --- |
| timing-ideal | 10001 | 0 ms | 0.109192–0.132522 | 1.396–1.416 |
| sample-hold | 2501 | 15 ms | 0.109162–0.132618 | 1.394–1.406 |
| dropout | 9901 | 250 ms | 0.109427–0.131333 | 1.020–1.411 |
| hold-dropout | 2475 | 275 ms | 0.109431–0.131246 | 0.952–1.000 |

Each recording has 10001 control samples. At 50 Hz, capture resumed at 18.260
and 40.260 s after the declared 250 ms windows. Feedback was held until those
scheduled captures; no observations were reconstructed from future state or
replayed after an outage.

The next table gives worst-case absolute differences from same-seed timing-ideal.
Frozen limits remain 150 mm peak truth-position difference, 50 mm position-RMSE
change and 500 ms landed-time change.

| Candidate | Peak truth difference (mm) | RMSE change (mm) | Landed-time change (ms) | Paired passes |
| --- | --- | --- | --- | --- |
| sample-hold | 5.475 | 0.165 | 25.0 | 3/3 |
| dropout | 22.889 | 1.189 | 5.0 | 3/3 |
| hold-dropout | 29.111 | 1.276 | 25.0 | 3/3 |

All twelve outage recovery checks report 0 s. This means a full one-second dwell
inside the 50 mm position-difference band begins at each outage's end. The largest
paired difference anywhere in these recordings was below that band. Thus these
cases demonstrate bounded disturbance tolerance, **not recovery from an excursion
outside the recovery band**. A stronger stress study is needed to exercise that
behavior; no parameter or threshold was adjusted against these final seeds.

## Provenance and timing

All final flights used clean implementation
`3d6e89a8948b384fb102d00bf21c0b7c8d5e5727`, with source digest
`4aad7626bb5a3deca215983f0076909acecc9f4a4450ec29f553c451299e68a4`.
The report retains controller-binary and lock hashes and simulator versions.
Isaac Sim 6.1.0.0, Isaac Lab distribution 17.0.2 and Torch 2.11.0+cu128 used the
existing local GPU environment. Development seed 73 passed before the final
matrix and is excluded from its result.

The three timing-ideal traces exactly reproduce the retained AL-015 ideal
state/control samples after removing the observation field. Shared configuration,
events and metrics also agree exactly. The capture implementation therefore
preserves that reference behavior. Physics, native controller gains, actuator,
wind and original mission gates remain unchanged.

Only hold-dropout is wall paced. Its slowest flight took 52.548 s of measured
loop time for 50 s of simulation, with 2.557 s maximum wall lag. All 10001 control
samples were retained; no solver steps were skipped to catch up. Wall timing
excludes startup and serialization. The monitor demonstrates soft real-time
execution and exposes lag; these results do not establish a hard real-time rate.

## Inspection and regression

Fresh live 3D was inspected during the combined development flight's landing,
final seed 0 hover, seed 1 waypoint/landing flight and seed 2 verified landing.
After seed 1's first outage, the monitor retained a 220 ms received feedback-age
peak and showed resumed captures. Its 10 Hz snapshots and browser polling do not
capture the full-rate 275 ms maximum. The completed seed 2 view showed zero rotor
thrust/command effort and 9.91 N ground support while wind continued. Truth pose,
feedback timing and wall-clock freshness remained distinct.

Six new Python checks cover capture boundaries/counts, held state, resets,
schema/configuration corruption, live source age, complete matrices and recovery
dwell/deadline boundaries. Local regression passed 110 Python tests with one
existing Windows symlink permission skip, two native checks, 17 frontend tests,
three legacy viewer tests and 19 browser checks. Three conditional legacy replay
fixtures were skipped. Browser coverage includes outage/resumption, 3D, stale
monitor updates and rejection of mismatched telemetry versions. Synthetic protocol
fixtures are separate from the fresh GPU measurements.

The production build, dependency lock, UTF-8/public-source scan and dated AeroLoop
evidence checks passed. Existing renderer bundle-size/client-directive warnings
remain. Generic OpenSteward static and strict checks retain only their known
hardcoded project-identity mismatch; the AeroLoop registry remains unchanged.

Raw traces, runtime logs and plots stay local and ignored. Reproduce the report
and figure with the [timing workflow](../observation-timing.md). Version-seven
recorded replay remains explicitly unsupported; live 3D and full-rate reports
provide inspection. Synthetic position/velocity timing, ideal attitude/rate/
acceleration/contact channels and three fixed seeds limit the claim. The original
AL-010 yaw-refinement gate remains open. No hardware flight or new learned-policy
claim is made.
