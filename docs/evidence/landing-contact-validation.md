# Landing contact lab validation

AL-025, validated 2026-10-06 under
[ADR 022](../architecture/decisions/022-landing-contact-lab.md).
PR 25 was squash-merged as `3d9ed48f706509cc1cc896b7f5aeea0535b879a1`;
its tree matched the reviewed head before this slice started.

The [analysis report](landing-contact-001.json) re-verifies all 24 retained
AL-024 PhysX flights, including six AL-022 baselines: 240,024 source states and
76,824 full-rate landing rows from 34 through 50 seconds. There are **zero new
flights** and no controller, simulation, sensor, seed or acceptance changes.
The original source, binary, lock, configuration and sample hashes remain
attached to each flight. Every mission, same-mode pair and recovery result is
preserved; this analysis does not create a new acceptance verdict.

The exporter re-ran full recording reconstruction, matrix identity and normal/
pre-outage continuity checks. An independent raw-recording audit checked all
landing columns' source mapping, P/D/integral/feedforward arithmetic, previous
interval force timing, 72 phase budgets and 24 readiness predicates. TypeScript
validated all twelve payloads and independently reproduced every Python phase
summary. Analytic tests distinguish a previous 2 N force from a current 100 N
force and verify that adjacent phase budgets do not double-count impulses.

The no-outage failures separate as follows (candidate exactly matches baseline):

| Seed | First contact distance | Disarm distance | Distance added after disarm | Tilt at disarm | Final support peak |
|---|---:|---:|---:|---:|---:|
| 401 | 0.573809 m | 0.632049 m | 0.029213 m | 13.0868° | 0.661262 m |
| 503 | 0.353559 m | 0.384157 m | 0.043781 m | 12.5443° | 0.427938 m |

Both are already beyond the original 0.350 m final-support position bound at
first contact. Contact-to-disarm distance increases are 0.058240 m and 0.030598 m.
These are diagnostic comparisons to a final-support limit, not new approach
gates. They prioritize pre-contact tracking and contact orientation over an
assumption that delaying disarm alone fixes landing. Normal-force telemetry
does not identify tangential friction; the residual budget remains inferred.

Only 5/24 recorded trajectories satisfy the default exploratory readiness
predicate before actual disarm (0.35 m, 0.2 m/s, 3°, 0.05 s continuous dwell plus
original contact eligibility). This is not an alternative-controller success
rate: another supervisor would change the trajectory, and no such flight has
been simulated. Threshold adjustments never alter original gates.

| Delivered feature | Verification |
|---|---|
| Ranked failure queue | All twelve real pairs loaded; cohort/outcome filters, ranking and stale selection tested |
| Horizontal map | Full-rate truth/feedback, equal scale, home boundary and velocity vector; actual desktop/mobile inspection |
| Paired 3D/event playback | Two contained canvases per actual case; seed 401 disarm jump reaches 41.680 s; playback and 5 ms stepping |
| Horizontal controller terms | Both axes independently compared to raw feedback, recorded integral, reference and original gains |
| Rotor/orientation inspection | Four rotor forces, quaternion rotation, world thrust and previous-force continuity checked |
| Momentum budget | Manufactured motion, all real interval rows and 72 vector budget closures checked |
| Contact episode ledger | Broken contact, singleton duration, eligibility interruptions and terminal censoring tested |
| Phase summaries | All real budgets agree between Python and TypeScript; missing events/empty/truncated windows stay incomplete |
| Offline readiness | All 24 raw-recording predicates independently agree; post-disarm samples excluded; invalid bounds rejected |
| Review links and export | Actual settings/time restore; 6,402 downloaded landing rows retain failures, gates, provenance and settings |

The local bundle totals 151,740,594 bytes, including the index. Index SHA-256:
`1c732be69652cad58349670729278cbb7b2426eaac0591c88dea7c016e82fe28`.
All twelve real cases render paired 3D with zero page errors. The 320 px layout
fits and the review download contains no host paths or server address. Raw
recordings, generated bundles, screenshots and detailed logs remain local.
The working page is `/contact.html`; see the [operator guide](../landing-contact-lab.md).

Local validation: 150 CPU cases (149 passed, one existing Windows symlink skip),
two native CTest cases, 40 frontend contract tests, three legacy viewer tests and
47 browser cases (44 passed, three existing conditional legacy-fixture skips).
TypeScript and the production demo build pass. Vite retains its existing client
directive and renderer-size warnings. The first new browser run used a malformed
test slider value; correcting its numeric spelling made all four new cases pass.

AeroLoop's dated evidence index passes. Static and dated strict OpenSteward
checks retain only the existing `project.identity` mismatch: the generic checker
expects its own plugin identity. AeroLoop's identity remains unchanged.

Residual limits remain synthetic sensors, ideal attitude/contact supervision,
simplified aerodynamics/contact, the small previously tested seed cohorts and
the open AL-010 yaw refinement. This is retained-flight analysis, not a new
robustness result, release or hardware-flight validation.
