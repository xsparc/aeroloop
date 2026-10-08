# Implementation roadmap

Scope revised 2026-09-28: physics simulation replaces PX4 execution; Isaac physics
and learning remain in the MVP. Incremental PRs target `main`; after a squash merge,
verify that every reviewed change reached `main` before starting the next slice.
Public deployment and merges are separate decisions.

| Slice | Deliverable and acceptance | State |
|---|---|---|
| AL-001 | CLI doctor, strict lock contract, frame tests, C++/Python CPU path, public source policy | Verified locally |
| AL-002 | Tested C++ rate core running in a CPU rigid-body model; hover, step and force pulse with measured outputs | Verified locally |
| AL-003 | Strict allowlisted export, corruption/privacy tests and accessible local replay | Verified locally |
| AL-004 | Isaac environment smoke, recorded physics, trained hover policy, fresh reload, held-out evaluation | Verified locally: 3/3 physics checks and 20/20 trained held-out trials; public summary validated |
| AL-005A | Reusable React/Three.js viewer with explicit frames, integrity checks and accessible controls | Verified locally: five unit checks and six browser checks |
| AL-005B | Separate website preview PR with immutable viewer and distinct Isaac evidence | Maintainer merged; local and served-site checks pass; hosted Actions execution remains blocked |
| AL-005C | Clean-checkout reproduction audit | Verified: fresh native build, 15/15 CPU trials, Isaac checkpoint reload again 20/20 trained vs 0/20 untrained |
| AL-005D | Post-merge MVP evidence audit and checklist reconciliation | Verified: merged trees match, retained measurements rechecked, 10 live browser checks and 23 served artifact hashes pass |
| AL-006 | Native C++ flight control with four rotors in Isaac PhysX, versioned evidence and local 3D replay | Verified: 15/15 clean-revision PhysX trials, 49 Python checks, two native tests and 3D browser checks |
| AL-007 | Seeded turbulent wind, pressure-centre drag and measured stabilization against a matching reference | Verified: 10/10 clean-revision PhysX trials, 5/5 paired comparisons and eight measured browser checks |
| AL-008 | Ground-contact takeoff, waypoint route, measured landing and 3D replay | Verified: 5/5 clean-revision PhysX missions, four waypoint holds per run, contact-latched landing and measured 3D replay |
| AL-009 | Turbulent takeoff, waypoint route, contact landing and combined 3D replay | Verified: 5/5 clean-revision PhysX missions with wind through landing, four waypoint holds per run and combined 3D replay |
| AL-010 | Independent force/contact accuracy and timestep refinement in Isaac | Harness delivered: 36/36 accuracy cases pass; default yaw refinement fails; numerical acceptance remains open |
| AL-011 | Fixed-cadence PhysX flight-controller study and read-only live 3D monitoring | Verified: 9/9 missions, 6/6 sensitivity comparisons, live GPU 3D and lag reporting |
| AL-012 | Full-rate acceptance explorer, seed/frequency matrix and guided paired 3D | Verified: nine retained missions revalidated, 216 gates, six pair results and measured browser inspection |
| AL-013 | Independent yaw, pose sampling and solver-iteration diagnostics | Verified: 30/30 diagnostic cases, matching read channels and reproduced original refinement failure; AL-010 remains open |
| AL-014 | CUDA arithmetic controls compared with fresh PhysX constant spin | Verified: 18/18 signature comparisons and arithmetic controls; 30/30 fresh physics cases; original refinement still fails |
| AL-015 | Seeded position/velocity noise, 40 ms observation delay and truth-based robustness | Verified: 12/12 PhysX missions, 9/9 robustness pairs, unchanged ideal baseline and live 3D truth/observation monitoring |
| AL-016 | Recorded observation-profile evaluation with paired 3D and explicit truth/feedback timing | Verified: twelve retained flights revalidated, 288 gates, nine pairs, all artifact hashes and measured 3D inspection |
| AL-017 | Fixed feedback cadence and capture outages with measured recovery and live 3D | Verified: 12/12 PhysX missions, 9/9 pairs, 12/12 post-outage dwell gates and unchanged ideal baseline |
| AL-018 | Longer capture outages with sustained recovery, preserved failures and live 3D | Verified study: 15 complete flights; 11 mission, 6/12 pair and 15/24 recovery passes; longer-outage failures retained |
| AL-019 | Bounded predictive feedback with recorded paired outage demo | Verified study: 15 fresh flights; 12 mission, 6/12 pair and 16/24 recovery passes; exact no-outage continuity; long-outage failures retained |
| AL-020 | Capture-aware landing commands and unseen-seed demo | Verified experiment: 24 fresh flights; exact inactive traces; 18 paired demo cases; two-second failures retained, guard stays opt-in |
| AL-021 | Axis-specific feedback availability | Verified: 24 fresh flights; horizontal channel improves mission completion while pair/recovery failures remain |
| AL-022 | Horizontal noise and delay sensitivity | Verified: 24 fresh flights; 23/24 missions and exact ideal continuity; all qualities retain pair/recovery failures |
| AL-023 | Ten-feature flight diagnosis workspace | Verified locally: 24 retained flights, 240,024 full-rate samples, phase-separated landing analysis and working paired 3D; no new flights |
| AL-024 | Vertical disturbance decay and ten-feature descent comparison | Verified experiment: 18 fresh flights, six retained baselines, 12 paired demo cases; candidate 8/12 missions, 5/6 outage pairs, 9/12 recovery windows; remains opt-in |
| AL-025 | Ten-feature landing contact lab | Verified retained-flight analysis: 24 flights, 76,824 landing rows, 72 phase budgets; paired 3D and offline readiness, original failures unchanged |

## Next gate

The maintainer requested further simulation-only drone development with physics
execution and 3D visualization on 2026-09-20. AL-006 implements that extension;
the prior instruction to avoid unrequested feature work does not block this
explicitly requested slice. See [decision 003](../architecture/decisions/003-rotor-flight-control.md)
and the [development workflow](../drone-development.md).

AL-006's [retained regression](../evidence/isaac-rotor-validation.md) passed all
fifteen trials and was merged. The maintainer's subsequent turbulence request
prioritizes AL-007 before takeoff/landing and waypoint work. See
[decision 004](../architecture/decisions/004-turbulence-stabilization.md) and the
[wind demonstration](../turbulence.md). Preserve the established CPU and learning
baselines. The maintainer merged AL-007 and requested autonomous continuation on
2026-09-21. AL-008 now implements ground-contact flight under
[decision 005](../architecture/decisions/005-ground-contact-mission.md), with a
[calm mission workflow](../ground-mission.md).
AL-007's [retained results](../evidence/isaac-wind-validation.md) show 98.7–98.9%
less wind-window position RMSE than the reference across all five seeds.

AL-008 was squash-merged and autonomous continuation was requested on 2026-09-21.
AL-009 combines mission flight and turbulent wind under
[decision 006](../architecture/decisions/006-turbulent-contact-mission.md), with
[its own validation](../evidence/isaac-wind-mission-validation.md) and
[workflow](../wind-mission.md). After merging AL-009, the maintainer prioritized
simulation and physics. AL-010 now measures isolated force, actuator and contact
accuracy at three timesteps under [decision 007](../architecture/decisions/007-physics-accuracy-suite.md).
After AL-010 was merged, the maintainer requested realistic controller testing
and real-time monitoring on 2026-09-22. AL-011 evaluates closed-loop mission timestep
sensitivity with fixed controller and wind timing and a live local dashboard under
[decision 008](../architecture/decisions/008-live-physics-flight-tests.md).
The independent yaw-refinement behavior remains unresolved; this study does not
close it. Sensor noise and delay were deferred to AL-015.

AL-011's [measured study](../evidence/isaac-live-flight-validation.md) passed with
at most 0.858 mm position difference across the compared frequencies. 200 Hz
achieved approximately 1x wall speed; higher frequencies reported their lag.
After AL-011 was merged, the maintainer prioritized evaluation and demonstration
on 2026-09-23. AL-012 now exposes the retained results under
[decision 009](../architecture/decisions/009-evaluation-demonstration.md), with
[a guided explorer](../flight-evaluation.md) and explicit full-rate gates.
After the evaluation explorer merge, the 2026-09-27 continuation delivered
[AL-013 yaw diagnostics](../evidence/isaac-yaw-validation.md). Cached/direct reads
agree; constant-spin drift and solver-iteration sensitivity remain measurable.
The [AL-014 arithmetic study](../evidence/isaac-yaw-arithmetic-validation.md) now
reproduces the constant-spin signature with fast trigonometry in all 18 comparisons.
Keep AL-010 open and the runtime pinned. The [AL-015 observation study](../evidence/isaac-observation-validation.md) now
passes all twelve missions and nine paired checks for fixed position/velocity
noise and 40 ms delay, with ideal attitude/rates and contact supervision. Its ideal
traces exactly preserve the earlier 200 Hz baseline. After the AL-015 merge,
[AL-016 recorded evaluation](../evidence/observation-replay-validation.md) now
exposes all four profiles in paired 3D, retaining full-rate scoring and explicit
truth/feedback timing. The complete study was revalidated without new GPU flights.
AL-017 now isolates capture cadence and missing samples under
[decision 014](../architecture/decisions/014-observation-timing.md), with fixed
50 Hz capture and two 250 ms outage windows. The [measured study](../evidence/isaac-timing-validation.md)
passed all twelve missions and nine pairs, with at most 29.111 mm truth separation.
All AL-017 post-outage dwell checks start inside the 50 mm band. AL-018 extends
that evidence under [decision 015](../architecture/decisions/015-outage-recovery.md)
with fixed longer outages and an equal-cadence reference. Its [measured duration
study](../evidence/isaac-outage-validation.md) exercises three outside-band returns
at 500 ms, while 1/2-second cases expose landing and recovery failures. AL-019 now measures bounded predictive feedback through descent and landing
under [decision 016](../architecture/decisions/016-predictive-outage-demo.md),
with a [repeatable paired demo](../predictive-feedback.md). Preserve the no-outage
and 250/500 ms regressions and all original stress failures. Prediction stays
opt-in until the fixed regression matrix and independent validation justify any
change in defaults. The [measured result](../evidence/isaac-predictor-validation.md)
improves one-second mission completion but still fails long-outage robustness.
AL-020 evaluates capture-aware descent under [decision 017](../architecture/decisions/017-landing-capture-guard.md) with a frozen unseen
seed protocol and a [paired working demo](../landing-guard.md). Its [measured results](../evidence/isaac-landing-guard-validation.md)
show no increase in mission passes: the guard trades touchdown motion against
delay and can worsen contact during a long outage. Unseen seed 101 also exposes
a no-outage baseline failure. Keep the guard experimental; next separate altitude
feedback loss from horizontal capture outages and measure prediction error before
changing descent policy. Retain both observation references and the
original accuracy gates. Any proposed runtime mitigation must pass the original accuracy and
full-flight studies first.

The MVP implementation and maintainer review are complete. The
[post-merge audit](../evidence/mvp-audit.md) records successful live integration
checks and source/evidence continuity. No additional feature is needed to satisfy
the current MVP design.

The remaining validation item is the website's hosted Actions execution. Its
budget currently prevents jobs from starting; rerun the existing workflows when
capacity is restored. Local and live results remain valid but do not substitute
for that hosted result. A versioned release requires a separate decision.

Keep the current model, dependency pins, seed sets and acceptance thresholds.
Reopen implementation for an observed defect or an approved extension, and update
the evidence for every changed claim. Do not expand scope to fill the time while
the hosted gate is blocked.

AL-021 is verified: [24 fresh PhysX flights](../evidence/isaac-axis-validation.md)
separate horizontal and altitude feedback availability under
[ADR 018](../architecture/decisions/018-axis-availability.md). Fresh horizontal
feedback passed 6/6 two-second missions; fresh altitude and retained all-channel
outages passed 0/6. Only 1/6 horizontal no-outage pairs and 7/12 recovery windows
passed. All twelve fresh no-outage traces exactly retained their references;
all six final seeds were previously tested. The paired 3D demo preserves failed
gates, and wall-clock lag reached 0.648 s without skipped physics samples.

This result motivated AL-022's fixed noise and transport-delay study below.
The idealized channel is not a real sensor or fused estimator. All six seeds
were already tested, and AL-010 yaw refinement remains open.

AL-022 is verified under [ADR 019](../architecture/decisions/019-horizontal-channel-quality.md).
The [24-flight quality study](../evidence/isaac-quality-validation.md) exactly
reproduced all six ideal references and passed 23/24 missions. Combined noise and
40 ms delay failed seed 0's final support-position bound (0.35119 m > 0.350 m).
All four qualities passed 0/3 no-outage pairs and 3/6 recovery windows. The
[working paired demo](../horizontal-quality.md) retains those failures and shows
acquisition/delivery age separately from true motion.

Next priority: diagnose the early-touchdown and persistent landing/recovery
differences using active-descent prediction error separately from post-contact,
post-disarm drift. Evaluate any bounded correction against these retained failures
and predeclare an additional seed cohort before viewing its traces. Do not enable
the channel by default, loosen limits, or treat a post-disarm predictor error as an
active control failure. Synthetic sensor settings, ideal attitude/contact
supervision and the unresolved AL-010 yaw-refinement finding remain explicit.

AL-023 delivers the requested [ten-feature diagnosis workspace](../flight-diagnosis.md)
under [ADR 020](../architecture/decisions/020-flight-diagnosis.md). The
[validation record](../evidence/flight-diagnosis-validation.md) preserves all
24 AL-022 flights, failed gates and historical source identity. Each original
physics sample is available in plots and CSV; no new flight or robustness claim
is made. Ideal seed 1 has 0.0694 m peak altitude feedback error during airborne
descent in [40,42), versus 2.2082 m after motors-off. Contact is intermittent,
so per-sample state and pre-first-touchdown windows answer different questions.

Next: use the same-quality no-outage comparison to identify which active-descent
target, state estimate or contact-supervision behavior explains early touchdown.
Predeclare the proposed correction and additional seed cohort before any new
measurement. Retain the combined seed-0 support failure and all pair/recovery
failures as regression cases; do not tune against motors-off drift alone or
relax limits. AL-010 remains open.

AL-024 implements the [ten-feature descent comparison](../descent-comparison.md)
under [ADR 021](../architecture/decisions/021-vertical-disturbance-decay.md).
The [frozen experiment](../evidence/isaac-decay-validation.md) preserves exact
no-outage and pre-outage continuity. It separates full-run acceptance from
contact-aligned diagnostic windows and retains every failed seed.

The regression candidate improves pair acceptance from 0/3 to 2/3 and recovery
from 3/6 to 4/6, but seed 1 still fails. The additional no-outage seeds expose
existing support-position failures: seeds 401 and 503 are already 0.632 m and
0.384 m from home when the motors are commanded off. This is an observation,
not proof of a single cause. Vertical disturbance decay cannot correct those
no-outage failures because it is deliberately inactive there.

Next priority: investigate horizontal position error and momentum at first
contact and at the landed latch, especially on seeds 401/503. Compare active
horizontal control, rotor lag, contact orientation and the existing disarm
criteria before proposing another bounded controller or supervisor change.
Retain the seed-1 prediction regression, use pre-contact metrics separately
from post-disarm drift, and predeclare further seeds before measurements.
Keep the candidate opt-in, all original limits unchanged, and AL-010 open.

AL-025 delivers the [landing contact lab](../landing-contact-lab.md) under
[ADR 022](../architecture/decisions/022-landing-contact-lab.md). Its
[validation](../evidence/landing-contact-validation.md) reconstructs all 24
retained flights and independently checks horizontal landing rows, interval
bookkeeping, 72 phase budgets and offline readiness.

No-outage seeds 401/503 are already 0.574/0.354 m from home at first contact.
Distance increases another 0.058/0.031 m before disarm and 0.029/0.044 m after it.
At disarm they are tilted 13.09/12.54 degrees. These observations prioritize
pre-contact horizontal tracking and contact orientation; changing disarm alone
cannot be assumed to repair the approach. Only 5/24 recorded flights satisfy
the default exploratory readiness predicate before actual disarm. That is an
offline diagnostic count, not a new success rate or a tested alternative policy.

Next: use the full-rate X/Y controller terms and force budget to identify when
the gust overcomes corrective acceleration before contact. Predeclare one bounded
approach-control or trajectory hypothesis and another seed cohort before a new
PhysX experiment. Evaluate original mission, no-outage, pair and recovery gates,
including seed-1 prediction and seeds 401/503. If contact friction is material to
the hypothesis, capture its tangential impulse explicitly instead of treating
the current residual as a measurement. Keep AL-010 open and defaults unchanged.

AL-026 evaluates [scheduled horizontal approach gains](../approach-gain-study.md)
under [ADR 023](../architecture/decisions/023-approach-gain-study.md). The frozen
protocol compares regression, known stress and predeclared additional seeds,
retains failed trials and preserves original limits. Ten features cover the
controller schedule, live gain telemetry, paired 3D, gate changes, squared-error
and demand curves, clipping/allocation inspection, gust chapters, cohort filters
and evidence-bound reviews. The
[measured matrix](../evidence/isaac-approach-validation.md) improves mission
passes from 12/18 to 15/18, with outage pairs 7/9 → 8/9 and recovery
windows 14/18 → 15/18. This is mixed evidence; the candidate stays opt-in
and AL-010 remains open.

Next: separate airborne tracking from contact-to-disarm motion on seeds 401 and
709, which still exceed final support position. Use the new full-rate gain,
demand and outcome evidence to predeclare the next bounded hypothesis and
additional seeds; preserve unresolved pair/recovery failures and all limits.
Do not promote this schedule on mission count alone.

AL-027 delivers the [ten-feature landing response lab](../landing-response-lab.md)
under [ADR 024](../architecture/decisions/024-landing-response-lab.md). It joins
all 36 retained AL-026 flights by seed and separates gain effects from outage
effects on identical recorded windows. [Independent interval validation](../evidence/landing-response-validation.md)
preserves original outcomes and exposes phase duration, work residuals and
acceleration mismatch. There is no new flight or controller acceptance claim.

Next: inspect common pre-contact windows for seeds 401 and 709 alongside their
contact-to-disarm motion, including seed 709's large descriptive outage
interaction. Form a bounded trajectory/control or contact hypothesis using the
original gates and fixed seeds, then predeclare fresh seeds before measurement.
Measure tangential contact impulse if a friction hypothesis is proposed; the
current work residual cannot identify friction. Preserve all unresolved pair
and recovery failures, the opt-in schedule and open AL-010 yaw refinement.

### AL-028: measured contact-friction lab (implemented)

Ten features in ADR 025 are implemented and exercised against the declared
19-flight study: 18 verified recordings, nine mission passes, nine mission
failures and one unverified 1.25 ms capture. All twelve retained trajectory
comparisons match exactly. Direct friction closes 180,000 measured impulse
intervals; original gates and defaults remain unchanged.

Next physics work: isolate the signed normal-force sample at takeoff in the
finest timestep, preserve the original acceptance contract, and determine whether
it reflects sensor reporting or solver behavior before claiming convergence.
Rotational/contact-point work remains unmeasured. AL-010 yaw refinement stays open.
