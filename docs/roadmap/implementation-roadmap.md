# Implementation roadmap

Scope revised 2026-09-20: physics simulation replaces PX4 execution; Isaac physics
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

## Next gate

The maintainer requested further simulation-only drone development with physics
execution and 3D visualization on 2026-09-20. AL-006 implements that extension;
the prior instruction to avoid unrequested feature work does not block this
explicitly requested slice. See [decision 003](../architecture/decisions/003-rotor-flight-control.md)
and the [development workflow](../drone-development.md).

AL-006's [retained regression](../evidence/isaac-rotor-validation.md) passed all
fifteen trials. Review and merge this slice, then specify takeoff/landing and
waypoint acceptance with contact physics as the next incremental slice. Preserve
the established CPU and learning baselines.

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
