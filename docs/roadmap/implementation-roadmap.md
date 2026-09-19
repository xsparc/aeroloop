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
| AL-005 | Reusable React/Three.js viewer, separate website preview PR, reproduction audit | Planned |

## Next gate

Prepare the reusable viewer and inspect the separate website integration target.
Include the measured Isaac learning summary without treating it as a CPU replay recording.
Perform a clean-checkout reproduction before a release claim.
Reassess the plan after each retained validation result. Do not create
unimplemented CLI commands or mark a future capability passed.
