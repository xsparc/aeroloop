# Reusable viewer validation

Recorded 2026-09-20 against main baseline `853b5e1` plus the viewer change.

The TypeScript library build and standalone production build pass on Node 22.16.0.
Five unit tests cover frame basis and known yaw/roll, shortest-arc quaternion
interpolation and target discontinuities, server rendering, same-origin URLs, and
bounded streaming with checksum rejection. Six Chromium browser tests use the
actual exported hover, north-step and east-force-pulse recordings, not fixtures.
They cover selected-only requests, keyboard scrubbing, event controls, offscreen
pause, StrictMode/remount, corruption rejection, stale requests, reduced motion,
WebGL fallback and 3D mount/disposal, plus mobile/tablet/wide light/dark layouts.

The first browser run caught the clock's implicit live status competing with the
verification message. The clock now uses non-live text; the verification result
remains the sole status message. The corrected suite passes. GPU-unavailable tests
deliberately trigger renderer errors and verify the retained fallback.

The local demo production bundle is about 66 kB gzip initially, with a separate
131 kB gzip renderer loaded only when 3D is enabled. The production bundler warns
about the raw renderer chunk size and the demo's client directive; the reusable
library is emitted separately by TypeScript and retains its client directive.
Payload budgets and website integration are separate validation checkpoints.

No Isaac task, policy, acceptance threshold or measured result changed. The viewer
does not display Isaac trajectories. No deployment or merge was performed.
