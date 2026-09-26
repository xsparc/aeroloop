# Implementation roadmap

Scope revised 2026-09-27: physics simulation replaces PX4 execution; Isaac physics
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
| AL-014 | CUDA arithmetic controls compared with fresh PhysX constant spin | In progress: fixed comparison limits, selected runtime fingerprints and complete retained traces |

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
close it. Sensor noise and delay remain deferred.

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
Next reproduce small-angle integration arithmetic and check the shared runtime
readout path before changing the solver or adding estimator noise/latency.
Preserve the existing controlled-flight baseline and decision 007's criteria.

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
