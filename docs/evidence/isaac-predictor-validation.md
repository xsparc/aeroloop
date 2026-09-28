# Predictive feedback validation

Measured 2026-09-29 under the frozen [AL-019 protocol](../architecture/decisions/016-predictive-outage-demo.md).
The [full-rate report](isaac-predictor-001.json) contains all thirty baseline and
candidate flights. The [operator workflow](../predictive-feedback.md) exports the
working recorded comparison without an active GPU worker.

## Provenance and continuity

Candidate implementation: `dd4ff60b57ed3fc4e596d4dc6f5fc64679a079a7`, clean.
Flight-source SHA-256:
`990905bf758027ad9fc67494ab9832032cca343dd1ea0414f2118d9bb84dc472`.
Retained baseline: `f30a0e74cd853e3d0ff6331b3e97eb046dddea83`, clean, from
[AL-018](isaac-outage-validation.md). Both cohorts use the same native controller,
dependency lock, model, wind, gains and runtime: Isaac Sim 6.1.0.0, Isaac Lab
distribution 17.0.2 and Torch 2.11.0+cu128. Only predictive feedback differs in
paired configurations. No source or parameter changes occurred during capture.

Development seed 73 completed 10,001 samples with the two-second profile. It
failed touchdown horizontal speed (0.599139 m/s versus 0.5) and final horizontal
position (0.394684 m versus 0.35). It is excluded from the final matrix. No tuning
followed that result. Seeds 0/1/2 are explicit regression seeds, not unseen tests.

All fifteen fresh candidate flights completed 50 simulated seconds and 10,001
control samples each: 150,015 new samples. All thirty full-rate recordings were
reverified before export. A separate report reconstruction matched the exported
report exactly, and its baseline section exactly matched the retained AL-018
report. All three no-outage state/control traces, metrics and events reproduce
AL-018 exactly after removing only the new feedback field.

## Results with unchanged gates

| Outage | Held / predicted missions | Held / predicted pairs | Held / predicted recovery windows | Predicted peak reference separation |
| --- | --- | --- | --- | --- |
| None | 3/3 / 3/3 | Reference | Not applicable | 0 m |
| 250 ms | 3/3 / 3/3 | 3/3 / 3/3 | 6/6 / 6/6 | 0.010863 m |
| 500 ms | 3/3 / 3/3 | 3/3 / 3/3 | 6/6 / 6/6 | 0.045866 m |
| 1 second | 2/3 / 3/3 | 0/3 / 0/3 | 3/6 / 4/6 | 0.292854 m |
| 2 seconds | 0/3 / 0/3 | 0/3 / 0/3 | 0/6 / 0/6 | 1.660774 m |

Candidate totals: 12/15 missions, 6/12 paired checks and 16/24 recovery windows.
Both cohorts are complete; overall stress acceptance remains **false**.
Pair/recovery comparisons use the corresponding controller's no-outage flight.
The no-outage trajectories are identical, so both references are also identical.

At 500 ms, the retained baseline had three excursions beyond the 50 mm band.
Prediction has none: the complete paired trajectories remain inside it. A zero
recovery time here means no outside-band recovery was needed. At one second,
seed 0 now passes its final-position mission gate; seed 1's first-window recovery
improves from 5.245 s to 1.390 s. Landing recovery is still missing for seeds 0/1,
and all three paired checks still fail. Mission success does not imply robustness
acceptance.

All two-second missions still fail. Seed 0 violates peak/RMSE tracking, touchdown
horizontal speed and final horizontal position; seeds 1/2 fail touchdown horizontal
speed at 0.551198/0.562914 m/s against the unchanged 0.5 m/s limit. First-window
returns are 7.410/8.085/5.630 s, all later than the five-second deadline. None
achieves the required final landing-window return.

The predictor can worsen estimation: for seed 1, position-feedback RMSE during
prediction is 0.384888 m, versus 0.301370 m for raw held captures on that same
candidate trajectory. Seed 0 is approximately unchanged; seed 2 improves slightly.
This mixed result rules out default enablement or a general long-outage claim.
At 250 ms, predicted feedback RMSE during missing captures is 1.84-4.11 mm versus
22.50-29.79 mm for held raw captures on the candidate trajectories. At 500 ms it is
9.30-16.03 mm versus 36.39-49.40 mm. These measure feedback accuracy, distinct from
mission tracking and paired-flight separation.

Every candidate was monitored and wall-paced. Real-time factors were
0.9999874-0.9999979; maximum recorded wall lag was 0.065438 s. Startup and evidence
serialization are excluded. This is soft real-time operation, not a timing guarantee.

## Working demo and checks

The local export contains fifteen paired files, thirty trajectories, 720 mission
gates, a full-rate report and a pinned index. It totals 36,787,235 bytes; the largest
pair is 2,459,415 bytes. All sixteen payload hashes were independently verified.
Index SHA-256:
`2b510bd22aed9708f6edd1563220cd57795cfef4cc6b143ea353befb642393bf`.
Display samples are 20 Hz with event/outage neighbors and endpoints; scoring
uses every 200 Hz sample. Raw observations and predictor outputs stay separate.

Actual live development and final seed-0 flights were inspected in 3D during the
18-second outage and after capture resumption, with one canvas and no page errors.
The recorded demo was inspected at 41.250 s and 48 s with two rendered canvases,
the failed mission/recovery outcomes visible, raw capture age and predictive mode
correctly separated. Profile/seed switching, playback and pause were exercised
on measured data; no page errors occurred. The full-rate comparison plot was also
visually inspected. Artifacts and raw logs remain local and ignored.

- CPU: 121 tests total, 120 passed; one existing Windows symlink-permission skip.
- Native: two CTest cases passed; lock checks and three legacy viewer tests passed.
- Frontend: 21 tests passed. Browser: 24 passed, three conditional legacy-fixture
  skips; all four new demo tests passed again after the final outcome-table change.
- Production build passed with existing chunk-size/client-directive warnings.
- Public-source, UTF-8/private-host, staged-diff and dated AeroLoop evidence checks
  passed before measurement and are repeated for closeout.
- Generic OpenSteward static/dated strict checks retain only their known
  `project.identity` constraint requiring the plugin's own project name. AeroLoop
  keeps its correct identity; no generic strict pass is claimed.

## Remaining limits

Prediction remains opt-in. The model has ideal attitude, known rotor output,
synthetic captures and simplified wind/contact. Fixed regression seeds do not
establish an unseen-data result, stability proof or hardware safety. The original
AL-010 yaw-refinement gate remains open; neither the solver nor learned hover
policy changed.

The next bounded investigation should address model uncertainty and stale
feedback during descent/contact, preserving these regressions while adding a
predeclared unseen seed set. Freeze the comparison before measurements; do not
select a model or acceptance threshold from these final results alone.
