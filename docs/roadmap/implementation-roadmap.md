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
| AL-005B | Separate website preview PR with immutable viewer and distinct Isaac evidence | Draft prepared; local checks pass, maintainer review and hosted Actions budget gate pending |
| AL-005C | Clean-checkout reproduction audit | Verified: fresh native build, 15/15 CPU trials, Isaac checkpoint reload again 20/20 trained vs 0/20 untrained |

## Next gate

Review the separate website draft and resolve its hosted Actions budget gate.
The reusable viewer, distinct Isaac evidence and clean-checkout reproduction are
implemented and validated locally. Retain those records and finish preview review
before a release claim. Do not add scope while these final review gates are pending.
Reassess the plan after each retained validation result. Do not create
unimplemented CLI commands or mark a future capability passed.
