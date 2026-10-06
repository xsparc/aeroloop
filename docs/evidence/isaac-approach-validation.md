# Approach gain study validation

Measured 2026-10-06–07 under [ADR 023](../architecture/decisions/023-approach-gain-study.md)
and the requested ten-feature continuation after PR 26. The candidate remains
opt-in. All-cohort acceptance: **false**.

## Frozen implementation and matrix

All 24 fresh final flights and both excluded development flights used clean
source `0417cc04c3a0111ef6169bf504e7443a2cf0bc99`. Retained regression/stress
baselines are the twelve AL-024 vertical-decay flights from clean source
`b75bcc85474626e60beee3f6a83b6f0e27874b40`. All modes share the verified native
controller binary, dependency lock and actual runtime recorded in the
[complete numeric report](isaac-approach-001.json).

Development seed 83 passed both profiles and is excluded. Final seeds are 0/1/2,
401/503/607 and predeclared 709/811/907, each with no outage and 2 s outages.
The additional cohort has fresh baseline and candidate runs. All 36 final/reference
flights contain 10001 samples. The first 6800 samples (t < 34 s) of each of the
18 pairs match exactly after removing only candidate gain telemetry: 122400
paired samples. No gain tuning, changed threshold or discarded failure followed
measurement. All workers monitored; all outage workers paced.

## Original acceptance results

Counts below are baseline → scheduled gains. Each cohort includes six missions,
three same-mode outage pairs and six sustained-recovery windows.

| Cohort | Missions | Outage pairs | Recovery windows |
|---|---|---|---|
| regression | 6/6 → 6/6 | 2/3 → 2/3 | 4/6 → 4/6 |
| stress | 2/6 → 4/6 | 3/3 → 3/3 | 5/6 → 6/6 |
| additional | 4/6 → 5/6 | 2/3 → 3/3 | 5/6 → 5/6 |

Totals: missions **12/18 → 15/18**, outage pairs **7/9 → 8/9**,
recovery windows **14/18 → 15/18**. Original limits remain authoritative;
mission completion alone does not establish paired consistency or recovery.

No-outage seed 503's final support-position error decreases from 0.42794 m to
0.33822 m, crossing the original 0.35 m limit. Seed 401 decreases from 0.66126 m
to 0.45748 m and still fails. Additional candidate seed 709 has 0.36129 m support
error and still fails. These are fixed-case observations, not a robustness claim.

For no-outage seed 401, the 34–50 s squared tracking-error integral falls from
3.89275 to 1.90275 m² s, while squared acceleration demand rises from 9.86384 to
11.59166 m²/s³. That illustrates the tradeoff visible in the new plots. These
windows include contact and disarmed states; they do not normalize airborne time.
No original mission gate changes from passed to failed/missing in this matrix,
although some continuous margins decrease. Regression seed 1 still fails its
same-mode outage pair. Landing-outage recovery remains unestablished for
regression seeds 0/1 and additional seed 709 through the complete horizon.

## Demonstration and arithmetic verification

The export contains 18 comparison payloads and 115236 full-rate landing rows.
Its index SHA-256 is `e7f4214d26f3ec65d263278e9d5a3aae1aab4a1d37bc685f3a1de57ff9fb0b83`.
All payload hashes and strict TypeScript contracts pass. An independent raw-sample
calculation checks every effective gain, clipped demand and tracking error, and
recomputes squared-error/demand integrals with separate summation for all 36
flights. The terminal sample adds no interval; clipping occupancy counts only
observed intervals. Command-demand integral is not physical energy.

The real demo loads all 18 pairs without page errors, renders both 3D scenes,
restores a gust-relative selection, exports 6402 landing rows with original gates
and provenance, and fits a 320 px viewport. The regression filter agrees with
the verified index. Screenshots, raw recordings, monitor captures and generated
bundles stay local and ignored.

The actual development monitor received 196 validated frames through
50 s, with a rendered drone, gain ramp and gust capture. The final paced monitor
received 567 frames across seeds 709/811/907. Both rendered 3D
and reported no page errors. Live samples are provisional and may skip physics
steps; full-rate recordings determine acceptance. Wall timing, including lag,
is retained per flight in the report; this is soft real-time execution.

## Checks and remaining limits

- CPU: 155 tests, 154 passed and one existing Windows symlink-permission skip.
- Native C++: 2/2; legacy viewer: 3/3.
- Frontend contracts: 46/46; browser: 47 passed, three existing fixture-dependent skips.
- Production demo build passed; existing renderer-size/directive warnings remain.
- Public-source scan, dependency-lock structure and dated AeroLoop evidence index pass.
- Generic OpenSteward static and dated strict checks retain only the known
  `project.identity` mismatch requiring the plugin's own name. AeroLoop's identity
  remains unchanged; that generic gate is not claimed green.

Small fixed cohorts, synthetic wind/noise/delay, ideal attitude/rates/contact
supervision and simplified rotor/contact models limit interpretation. AL-010 yaw
refinement remains open. Defaults and physical-flight scope are unchanged.

## Clean-checkout test imports

The PR 27 and merge CI runs exposed missing checkout import setup in the two
new approach test modules. The earlier local CPU run inherited `PYTHONPATH`,
which masked the problem. With that variable unset, discovery reproduced both
`ModuleNotFoundError` failures before any approach test could run. Both modules
now locate `src` relative to their own file, following the existing test-suite
convention and removing dependence on discovery order or shell configuration.
This repair changes test imports only; the frozen flight implementation and
recorded physics evidence above are unchanged.

Revalidation with `PYTHONPATH` unset: the complete CPU command passed 154 tests
with the same Windows symlink-permission skip, and isolated discovery of the
approach study module passed. Public-source, dependency-lock and dated project
evidence checks passed; the generic identity mismatch remains as documented.
