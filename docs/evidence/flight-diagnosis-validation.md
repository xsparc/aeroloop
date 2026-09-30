# Flight diagnosis validation

AL-023, validated 2026-10-01 under [ADR 020](../architecture/decisions/020-flight-diagnosis.md).
PR 23 was squash-merged as `5bf7af8ee25558c72ca4cd1eb400a15fa2b3369d`;
its tree exactly matched the reviewed head before this slice started.

The [diagnostic report](flight-diagnosis-001.json) reuses all 24 AL-022 PhysX
flights (240,024 samples), recorded at clean source
`c943f0b17733b8aa22fecc7a93705645c302147a`. There are **zero new flights**.
The original physics/control, seed cohort and all acceptance limits are unchanged.
Export re-ran the full recording reconstruction, quality matrix and six retained
ideal-reference reproduction checks. All 23/24 mission, 0/12 outage-pair and
12/24 recovery-window pass counts remain unchanged.

All 96 phase groups were independently recalculated from original full-rate
samples, along with all exported numeric columns, poses and original metrics.
Each [40,42) window has 400 samples, assigned once to airborne descent, contact,
motors-off or other. For ideal seed 1, these counts are 246, 11, 143 and 0.
Its peak altitude feedback errors are 0.0693753 m during airborne descent,
0.0741807 m during contact, and 2.2082473 m with the motors off. The airborne
peak differs from the earlier pre-first-touchdown statistic because contact can
be intermittent. This distinction is descriptive, not a causal finding.

The combined-quality seed-0 final support error remains 0.3511916 m against
the 0.350 m bound, giving **-0.0011916 m headroom**. It is the default demo
selection. No-outage flights pair only with themselves for display and explicitly
have no outage-pair/recovery verdict. No failed case is hidden or reclassified.

The ten implemented tools and their checks are:

| Feature | Validation |
|---|---|
| Case matrix | All 24 actual cases loaded; quality/profile/outcome filters and headroom sorting exercised |
| Same-quality paired 3D | Two correctly contained canvases for every actual case; same seed/quality/source enforced |
| Full-rate plots | Every original 5 ms numeric row independently checked; shared cursor, keyboard and playback exercised |
| Event navigation | Actual ideal seed-1 landed jump reached exactly 41.285 s |
| Phase error metrics | Independent 96-group arithmetic; precedence, intermittent contact, empty and truncated windows tested |
| Feedback layers | Raw/predictor/applied/truth toggles; applied altitude bound to the original predictor output |
| Gate headroom | Original 24 gates retained per case; signed, strict, equality and missing-value semantics checked |
| Recovery inspection | Original final-suffix arithmetic reconstructed; corrupted/incomplete horizons reject success |
| Provenance | All payload hashes and historical source/runtime bindings checked; unknown provenance fields rejected |
| Numeric CSV | Actual 40–43 s export contained 601 data rows; inclusive boundaries and numeric-only columns tested |

The local bundle is 46,164,404 bytes. Its index SHA256 is
`2611d88a8012f9e5d5b5d4e47c04b3c8c5d53edbce2055b8cb7a0040a8809a04`.
All 24 payloads pass the browser contract and reference consistency checks.
Actual 3D playback, 320 px layout and screenshots were inspected with zero
page errors. The loopback demo is `/diagnosis.html`; see the
[operator guide](../flight-diagnosis.md) to reproduce it. Generated bundles,
screenshots and detailed logs remain local.

Local validation: 141 CPU cases (140 passed, one Windows symlink skip), two native
CTest cases, 30 frontend tests, three legacy viewer tests, and 40 browser cases
(37 passed, three existing conditional legacy-fixture skips). TypeScript and the
production demo build pass. The browser tests include corruption, interrupted
loads, incomplete evidence, accessible controls, 3D containment and mobile layout.

AeroLoop's evidence index passes at 2026-10-01. Static and dated strict
OpenSteward checks each report only the existing `project.identity` mismatch.

Residual limits: synthetic sensors, simplified wind/contact, ideal attitude and
supervision, previously tested seeds, and the open AL-010 yaw refinement issue.
No new GPU run is needed for this analysis-only change. This is not a new
controller robustness result or a hardware-flight claim. The generic OpenSteward
checker retains its known project-identity incompatibility; AeroLoop's identity
is preserved rather than relabeled to satisfy that unrelated check.
