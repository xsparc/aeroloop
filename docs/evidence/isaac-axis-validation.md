# Axis availability validation

Validated 2026-09-30 for AL-021 under [ADR 018](../architecture/decisions/018-axis-availability.md).
Implementation: `41e406d3d574fce1a50749110ff50595cec42e14`; flight source digest
`56e5e86aac800993e77ccd7c628d9e24ba8f8a8425b64e077edd032c351930c1`. Every fresh recording reports clean source.
Runtime: Isaac Sim `6.1.0.0`, Isaac Lab distribution
`17.0.2`, PyTorch `2.11.0+cu128`.

Twenty-four final flights retained 240,024 physics/control samples. Twelve
retained predictor-only recordings provide the two-cohort baseline. Seeds
0/1/2 and 101/202/303 were all previously tested; no unseen-seed claim is made.
Development seed 73 was excluded: fresh altitude failed peak-error and
horizontal-touchdown limits, while fresh horizontal feedback passed its mission.
No parameters changed after either development or final results were inspected.

| Cohort | Fresh channel experiment | Side | All missions | Two-second missions | Pairs | Recovery windows |
| --- | --- | --- | --- | --- | --- | --- |
| regression | vertical | baseline | 3/6 | 0/3 | 0/3 | 0/6 |
| regression | vertical | candidate | 3/6 | 0/3 | 0/3 | 0/6 |
| regression | horizontal | baseline | 3/6 | 0/3 | 0/3 | 0/6 |
| regression | horizontal | candidate | 6/6 | 3/3 | 0/3 | 3/6 |
| prior-validation | vertical | baseline | 2/6 | 0/3 | 0/3 | 3/6 |
| prior-validation | vertical | candidate | 2/6 | 0/3 | 0/3 | 3/6 |
| prior-validation | horizontal | baseline | 2/6 | 0/3 | 0/3 | 3/6 |
| prior-validation | horizontal | candidate | 5/6 | 3/3 | 1/3 | 4/6 |

Fresh horizontal feedback passed **6/6** two-second missions, compared with
**0/6** for fresh altitude and **0/6** for the retained baseline. Its horizontal
touchdown speeds were 0.106–0.169 m/s. This is a bounded availability result:
only **1/6** no-outage pairs and **7/12** recovery windows passed, so overall
stress acceptance remains false. Fresh altitude passed 0/6 pairs and 3/12
recovery windows. All twelve fresh no-outage recordings preserve the original
5/6 per-choice mission result, including seed 101's touchdown/support failure.

Mission gates, same-controller no-outage comparisons and sustained recovery
are separate outcomes. Every failed gate remains in the
[complete report](isaac-axis-001.json), including pre-existing no-outage failures.
All stress gates accepted: **false**.

All twelve fresh no-outage traces match their retained references exactly after
removing only the extra channel fields; metrics and events match too. Every
outage trial matches before 18 s. Main predictor, controller gains, wind,
rotors, physics timestep, original targets, contact supervision and deadlines
are unchanged. Full-rate applied horizontal/vertical feedback RMSE and peaks
are reported separately for 18–20 s and 40–42 s.

All flights were monitored; twelve two-second final flights were wall-paced.
Wall timing is soft real-time and excludes startup/serialization. The complete
report retains per-flight timing, including lag and real-time factor. Maximum
lag was 0.648307 s; real-time factor ranged
from 0.993055 to
1.000000. No physics samples were skipped.

Validation: 132 CPU tests (131 passed, one Windows symlink skip), two native
CTest checks, 25 frontend tests, three legacy viewer tests, and 33 browser cases
(30 passed, three conditional legacy-fixture skips). Build and lock checks
passed. Browser tests cover fresh-channel/cohort selection, masked captures,
corrupted evidence, incomplete flights, canceled loads, narrow screens and 3D.
Actual measured playback rendered two 3D canvases with no page errors; channel,
cohort, seed, timeline, chapters and play/pause were exercised. Live development
monitoring showed an active outage and resumed captures with one 3D canvas and
no page errors. Screenshots and the full-rate plot remain local.

The independent raw audit recomputed truth-target metrics and applied-feedback
errors, checked exact continuity, matched retained baseline report rows, verified
all thirteen payload hashes and confirmed the frozen flight source digest.
The actual twelve demo pairs passed the browser contract. Index SHA256:
`9d0b5ebca97610e5b6b6a23bf36c8675caf8437614e557689312d0120cb03eb8`. Exported bundle: 35,348,115 bytes.

AeroLoop's dated evidence and public-source checks pass. The generic OpenSteward
static/strict checker retains its known `project.identity` error because it
requires the plugin's own project name; the AeroLoop identity is preserved.

Limitations: the extra channel is noiseless, zero-delay and synthetic, with
50 Hz holds. It is not a real sensor, fused estimator or hardware validation.
All seeds were already tested. Ideal attitude/contact supervision and unresolved
AL-010 yaw refinement remain. The feature stays opt-in and excludes the landing
guard. Use the [operator guide](../axis-availability.md) to reproduce the demo.
