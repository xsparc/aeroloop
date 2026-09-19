# Implementation roadmap

Scope revised 2026-09-20: physics simulation replaces PX4 execution; Isaac physics
and learning remain in the MVP. Small PRs are stacked in dependency order and remain
open for review. Public deployment and merges are separate decisions.

| Slice | Deliverable and acceptance | State |
|---|---|---|
| AL-001 | CLI doctor, strict lock contract, frame tests, C++/Python CPU path, public source policy | Verified locally |
| AL-002 | Tested C++ rate core running in a CPU rigid-body model; hover, step and force pulse with measured outputs | Verified locally |
| AL-003 | Strict allowlisted export, corruption/privacy tests and accessible local replay | Planned |
| AL-004 | Isaac environment smoke, recorded physics, trained hover policy, fresh reload, held-out evaluation | Blocked on environment validation |
| AL-005 | Reusable React/Three.js viewer, separate website preview PR, reproduction audit | Planned |

## Next gate

Complete AL-003 export/replay while the Isaac environment is unavailable. Reassess
the plan after each retained validation result. Do not create
unimplemented CLI commands or mark a future capability passed.
