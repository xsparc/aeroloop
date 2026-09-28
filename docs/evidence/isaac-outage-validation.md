# Outage duration validation

Measured 2026-09-28 under [decision 015](../architecture/decisions/015-outage-recovery.md).
All fifteen final PhysX flights completed with 10001 samples each (150015 total).
Eleven passed mission gates, six of twelve paired comparisons passed, and fifteen
of twenty-four sustained-recovery windows passed. The complete study deliberately
reports **accepted: false**. AL-018 delivers verified failure evidence; it does
not establish robustness across every tested duration.

## Frozen source and execution

Implementation revision `f30a0e74cd853e3d0ff6331b3e97eb046dddea83`; source digest
`72a8f0ca006b9e6d3268db8117af0f015234643d61eaf04c11944a20f8f5794e`.
Isaac Sim 6.1.0.0, Isaac Lab distribution 17.0.2 and Torch 2.11.0+cu128 were used.
The native controller, gains, 200 Hz control/physics, rotors, wind, mission gates
and runtime stayed fixed. All profiles capture at 50 Hz and use seeds 0/1/2.
Every flight enabled monitoring and wall pacing. Development seed 73 is excluded
from the final matrix; its complete 2-second flight also failed mission gates.
No final-seed tuning, replacement trials or threshold relaxation occurred.

The three fresh sample-hold traces and three fresh 250 ms traces **exactly match**
AL-017 in every state/control/observation sample, configuration, metric and event.
The earlier AL-017 timing report also re-verifies to an identical document.
The new comparison reference is sample-hold, not timing-ideal, so paired differences
isolate outages from capture cadence. Source fingerprints stayed unchanged through
capture and post-capture verification.

## Measured outcomes

The [generated report](isaac-outage-001.json) was independently regenerated from
all full-rate recordings and matched the first report exactly. Failed gates and
absent measurements remain in the public summary; raw logs and traces remain local.

| Outage duration | Mission passes | Pair passes | Recovery passes | Windows outside 50 mm | Peak paired separation |
| --- | --- | --- | --- | --- | --- |
| Reference, no outage | 3/3 | N/A | N/A | N/A | 0 |
| 250 ms | 3/3 | 3/3 | 6/6 | 0/6 | 27.226 mm |
| 500 ms | 3/3 | 3/3 | 6/6 | 3/6 | 96.569 mm |
| 1 s | 2/3 | 0/3 | 3/6 | 6/6 | 363.259 mm |
| 2 s | 0/3 | 0/3 | 0/6 | 6/6 | 2124.871 mm |

For 500 ms, three windows exercise recovery beyond the band. Their final
uninterrupted return begins 0.870, 0.965 and 1.125 seconds after outage end.
The other three stay inside the band. Every return includes a complete one-second
dwell and no subsequent excursion through the observation horizon.

At 1 second, seed 0 exceeds the final horizontal-position limit: 0.360229 m
versus 0.350 m. All three seeds exceed the 0.15 m paired peak bound. Seed 1's
first-window return takes 5.245 s, missing the five-second deadline; seeds 0/1
never establish an in-band final suffix after the landing outage. Seed 2 passes
both recovery checks despite failing the paired peak bound.

At 2 seconds, all seeds exceed the 0.5 m/s touchdown horizontal-speed limit:
1.527481, 0.538769 and 0.955399 m/s. Seed 0 additionally fails peak tracking error,
RMSE and final horizontal position; seed 1 fails peak tracking error; seed 2 fails
final horizontal position. The first-window returns take 7.125, 9.020 and 8.965 s,
all late. No seed establishes the required final in-band suffix after the landing
outage. This separates eventual return, timely recovery and mission acceptance.

Per-flight capture counts are 2501/2475/2451/2401/2301 for the reference through
2 seconds. Maximum feedback ages are 15/275/515/1015/2015 ms, matching the frozen
schedule. Pacing achieved real-time factors 0.9999898–0.9999995; maximum recorded
wall lag was 0.025290 s. Startup and evidence serialization are excluded. This
is a soft real-time observation, not a hard timing guarantee or performance
improvement over prior studies.

## Inspection and checks

The actual 2-second development flight was inspected in browser 3D during its
18 s outage and after captures resumed. The final seed-0 flight was inspected
at 19.6 s with 1620 ms feedback age and again at 20.1 s with fresh observations.
Each inspection had one rendered canvas and zero page errors. The final monitor
retains the completed seed-2 state and the failed study outcome. The full-rate
comparison figure was generated from verified data and visually inspected.

- CPU: 115 tests total, 114 passed; one existing Windows symlink-permission skip.
- Native: two CTest cases passed. Dependency lock and three legacy viewer tests passed.
- Frontend: 18 tests passed; browser: 20 passed, three conditional legacy-fixture skips.
- Production build passed with existing chunk-size/client-directive warnings.
- Public-source, UTF-8/private-host, staged-diff and AeroLoop dated evidence checks passed.
- Generic OpenSteward static and dated strict checks report only the known
  `project.identity` constraint requiring its own project name. AeroLoop keeps
  its correct identity; no generic strict pass is claimed.

## Scope and next step

These discrete durations and three wind seeds do not establish a safe outage
limit, monotonic boundary or stability proof. Position/velocity feedback is
synthetic; attitude/rates/acceleration and mission/contact supervision remain
ideal. Recorded timing replay is still deferred. The original AL-010 yaw-refinement
gate remains open; this work changes neither the solver nor the learned hover policy.

The next bounded controller investigation should address stale-feedback behavior
through descent and landing, using these retained failures as regression cases.
Compare any mitigation against the unchanged controller under a protocol frozen
before further measurements, including no-outage and 250/500 ms regressions.
Do not tune on these final seeds or promote the 500 ms result to a general limit.
