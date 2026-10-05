# Landing contact lab

Open `/contact.html` to inspect the 24 retained AL-024 PhysX flights as twelve
original/vertical-decay pairs. Start with additional seed 401 without an outage:
both modes have the same failed landing. The failure queue ranks the original
final-support error, while the common timeline connects the map, 3D pose and
full-rate controller/physics diagnostics.

The ten tools are specified in [ADR 022](architecture/decisions/022-landing-contact-lab.md):
failure queue, horizontal map, paired 3D/event playback, horizontal PID terms,
rotor/orientation inspection, momentum budget, contact episodes, phase summaries,
offline readiness audit, and evidence-bound review links/export.

Use **Jump to contact** and **Jump to disarm** on either side, then inspect the
other side at the same simulation time. The map preserves equal X/Y scale and
shows a 0.35 m home circle. That is the final-support limit, not a new approach
gate. The arrow is current velocity scaled by half a second; it is not a future
trajectory. Every numeric row is a recorded 5 ms state; only 3D poses interpolate.

The controller section separates P, D, stored integral, feedforward and clipped
demand on X/Y. Actuator details show all four realized rotor forces and the
requested/realized totals, world force and wrapped yaw/tilt. Motors continue to
produce decaying thrust immediately after the command becomes zero.

Expand the momentum budget and episode ledger to distinguish approach,
contact-to-disarm and disarmed motion. Phase state endpoints are inclusive;
impulses integrate `(start,end]`. Contact episodes use normal force >0.1 N.
Their observed duration excludes any unknown time before first/after last contact
sample; a final episode is right-censored. Continuous eligibility additionally
requires the original clearance and vertical-speed conditions.

The residual horizontal impulse uses the preceding sample's thrust and wind.
It includes contact/solver effects and numerical error, and is not measured
friction. Event cursor speed uses the current state; the original touchdown-speed
gate uses the state before the first contact-force report.

The readiness sliders add exploratory position, horizontal-speed, tilt and dwell
conditions to the existing contact predicate. They inspect truth only through
actual disarm. Changing a slider does not simulate continued control or predict
where another controller would land. An absent qualifying time means only that
the predicate did not occur before recorded disarm. Original acceptance stays
visible and unchanged.

**Share review** stores the case, time, audit settings and index digest in the
URL fragment. Reopening requires the same local bundle. **Export review JSON**
includes both modes' full-rate landing rows, phase budgets, contact episodes,
readiness settings/results, all original gates, same-mode outage/recovery results
and historical provenance. The download contains no local server address or
recording paths. Treat it as descriptive analysis, not a new flight outcome.

## Prepare the local demo

Use the retained directories from [the AL-024 protocol](descent-comparison.md).
No new GPU run is needed. Export re-verifies the original full recordings and
frozen matrix before deriving allowlisted landing diagnostics:

```powershell
.venv/Scripts/python.exe tools/contact_study.py `
  --regression-baseline runs/quality-noise-delay-sample-hold-001 runs/quality-noise-delay-hold-dropout-2000ms-001 `
  --regression-candidate runs/decay-regression-candidate-sample-hold-001 runs/decay-regression-candidate-hold-dropout-2000ms-001 `
  --additional-baseline runs/decay-additional-baseline-sample-hold-001 runs/decay-additional-baseline-hold-dropout-2000ms-001 `
  --additional-candidate runs/decay-additional-candidate-sample-hold-001 runs/decay-additional-candidate-hold-dropout-2000ms-001 `
  --report runs/contact-analysis-001.json --demo web/replay/public/contact-demo-001
```

The exporter refuses existing outputs. Set `web/replay/public/contact-config.json`
with the printed SHA-256 and the same-origin bundle path:

```json
{"baseUrl":"/contact-demo-001/","indexSha256":"<printed index SHA-256>"}
```

In `web/replay`, run `npm run demo:build` and
`npx --no-install vite preview --host 127.0.0.1 --port 8794 --strictPort`, then
open `http://127.0.0.1:8794/contact.html`. Raw recordings and generated bundles
remain local; this public repository provides reproducible code and compact
[validation evidence](evidence/landing-contact-validation.md).

Synthetic sensors, ideal attitude/contact supervision, simplified aerodynamics
and the unresolved AL-010 yaw refinement limit interpretation. All original
failures are retained. This is simulation-only analysis, with no hardware-flight
claim and no new controller robustness result.
