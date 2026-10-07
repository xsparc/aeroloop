# Landing response lab validation

AL-027, 2026-10-07, after merged PR 28 (`cec7e1060f9ab46381fdc222ce6ed336f12323e3`).
Scope is the ten recorded-physics analysis tools in [ADR 024](../architecture/decisions/024-landing-response-lab.md).
No flight controller, physics, original acceptance threshold or default changed.

## Retained evidence and arithmetic

All eighteen AL-026 comparison payloads were hash-verified and strictly validated,
then joined into nine four-flight groups. Source identities match within gain
mode across profiles; binary, dependency lock and runtime match across each group.
All 36 recordings retain their historical clean source identity. This analysis
does not claim a new GPU experiment. Mission passes remain fixed 12/18 and
scheduled 15/18. Same-mode outage pairs remain 7/9 and 8/9; sustained recovery
windows remain 14/18 and 15/18. All failures remain visible.

An independent Python calculation checked every derived radial state, force-work
interval, velocity-difference acceleration, phase assignment and cumulative
energy curve: **115236 states and 115200 intervals**. It recomputed 216 per-flight
summaries over the common, pre-contact, armed, disarmed, gust and 40–43 s windows
using separate formulas and `math.fsum`, then checked both contrast signs.
Absolute and relative comparison tolerances were 2e-9. All checks passed.

The [compact numeric evidence](landing-response-001.json) pins the original
index SHA-256, both payload hashes per seed, all window metrics and original
outcome counts. Full gates and source identities are retained in the reproducible
report and browser JSON export, with the original report linked by the operator guide.

## Recorded observations, not new acceptance

For stress seed 401 over 40–43 s, intact-flight horizontal RMSE changes from
0.513493 m with fixed gains to 0.368016 m with scheduled gains. Fixed outage-minus-
intact RMSE is -0.007435 m; scheduled is +0.002278 m; their difference is
+0.009713 m. Better tracking and a larger outage contrast coexist. Both
candidate missions still fail their original support-position gate.

Additional seed 709 has the largest positive RMSE interaction in this selected
window, +0.034082 m. The fixed and scheduled outage effects are both negative
(-0.118238 m and -0.084156 m); this is not evidence that outages improve control.
These flights have different histories and phase exposures. The next control
hypothesis should use the common pre-contact window and separate post-disarm
motion, with new seeds declared before measurements.

## Demo verification

The production demo loaded all nine seed groups, rendered four actual 3D flights,
showed nine rows in the verified seed table, restored a review at 40.005 s and
exported 2404 numeric rows in both JSON and CSV for the 40–43 s window. Browser
metrics exactly matched the command-line report. Seed 401's common pre-contact
window ends at 41.420 s. No page errors occurred and the page fits 320 px width.
Desktop, four-flight and narrow-layout screenshots were inspected locally.

Contract tests cover constant-force work, preceding-force timing, terminal
interval exclusion, phase exposure, rotated/singular radial directions,
contrast signs, identity mismatches, digest-bound links and export coverage.
Report tests cover pinned hashes, corrupted files and output preservation.
Browser tests cover four-flight playback, phase windows, stale-load rejection,
seed comparison, corrupt/incomplete input, exports and renderer fallback.

Frontend suite: 54/54 passed. Local browser suite: 51 passed, three existing
fixture-dependent replay skips. The production build passed with the existing
renderer-size/directive warnings. The complete CPU suite ran with `PYTHONPATH`
unset: 154 passed and one existing Windows symlink-permission skip. Public-source,
dependency-lock and dated AeroLoop evidence-index checks passed. Generic
OpenSteward static and dated strict checks retain only the known
`project.identity` mismatch requiring the plugin's own name. AeroLoop's identity
is preserved; that generic gate is not claimed green.

The first hosted run exposed a narrow-layout overflow under Linux native control
sizing. The response toolbar now stacks labels over their selects and explicitly
allows controls to shrink within the panel. The narrow browser assertion checks
viewport width and identifies overflowing controls after responsive layout settles.
All four response browser cases passed locally after that correction.

## Limits

Residual work includes unmeasured contact constraints, integration and within-step
orientation effects; it is not measured tangential friction. Horizontal-only
translation excludes rotor electrical work and rotational/vertical energy.
Small synthetic cohorts, ideal attitude/contact supervision, simplified rotors
and wind, and the open AL-010 yaw-refinement finding remain. This slice does not
claim new controller robustness or promote scheduled gains to a default.
