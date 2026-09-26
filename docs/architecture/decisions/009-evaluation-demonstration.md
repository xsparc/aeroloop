# 009: Flight evaluation and guided comparison

Accepted 2026-09-23 for the requested evaluation and demonstration improvements.
Baseline: `2c0022690f3a9d4d41ede2a12cad65ba7e0b0f2b`.

Re-evaluate the retained three-seed, three-frequency PhysX study using the full
recording verifier. Expose decision 006's existing mission gates as named results
with measured values and exact limits. Preserve decision 008's sensitivity gates,
all failed trials, historical source identity and the unresolved yaw finding.
No controller tuning, new physics claim or new GPU measurement is included.

Export a separate, bounded evaluation bundle: full-rate metrics and pair results,
plus event-preserving display samples, manifests and events. Raw samples remain
in the original recordings with their hashes. A SHA-256-pinned evaluation index
binds every display document; the browser fetches only the selected pair. Never
present display interpolation as solver output or as the source of acceptance.

Acceptance criteria fixed before implementation:

- Re-verification preserves all nine outcomes and six pair results. Missing
  measurements fail their gates; an incomplete pair has no sensitivity result.
- The explorer shows the complete seed/frequency matrix, individual gate values
  and limits, recorded pacing, source identity and numerical/model limitations.
- A shared timeline compares 200 Hz against 400 or 800 Hz, with optional paired
  3D and chapter seeks for takeoff, route, gust and measured touchdown/settling.
  Playback starts only on request, pauses when hidden/offscreen or when reduced
  motion is enabled, and remains usable without WebGL and on narrow screens.
- Bounded same-origin checksum verification, malformed/failed evidence and
  selection cancellation tests prevent stale or unsupported success displays.
- Retained measured recordings are exercised in a browser separately from
  synthetic UI protocol tests. CPU, browser, privacy and evidence checks pass.

Affected requirements: REQ-WIND-MISSION, REQ-LIVE-FLIGHT-TESTS and the new
REQ-FLIGHT-EVALUATION. Expected changes cover Python evaluation/export, the
standalone replay application, tests and project evidence. Primary risks are
confusing display downsampling with validation and hiding missing/failed data.

The design follows the bounded-input implications of
[Web Crypto digest](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest)
and explicit motion controls described by
[WCAG pause, stop, hide](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html).
