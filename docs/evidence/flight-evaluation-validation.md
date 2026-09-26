# Flight evaluation explorer validation

Re-evaluated 2026-09-23 after the live study was squash-merged at
`2c0022690f3a9d4d41ede2a12cad65ba7e0b0f2b`.

The full verifier re-read all nine retained PhysX recordings. The resulting study
is structurally identical to `isaac-flight-study-001.json`: 9/9 missions and 6/6
sensitivity pairs pass across 90,009 control samples. The explorer exposes 216
individual gate results (24 per run), preserving the prior thresholds and outcome
precedence. This is re-evaluation of measured source
`1475d81cd7e68b63046eefe01f76eee77fabd971`, not a new GPU experiment.

The compact export contains 37 JSON files, 6,272,496 bytes and 9,283 display
samples. Its 72,693-byte evaluation index has SHA-256
`f1ab85398fae2dfbc330ce171e1a7eb8320eb709512e46ab888b11bc06871b93`.
The index binds display documents and retains the original full-sample hashes.
Raw recordings and screenshots remain local, outside public source.

Actual measured browser inspection covered seed 0 at 200/400 Hz during the
40.000 s landing gust and seed 2 at 200/800 Hz at the candidate's 43.545 s
touchdown. Both 3D canvases rendered, playback advanced to 43.574 s and selection
reset the shared timeline. Desktop and 390 px mobile views had no page errors
or document-level horizontal overflow. Recorded pose, wind and support were
visible; the open yaw finding remained prominent.

Validation includes independent gate boundary tests, missing support and
incomplete-pair handling, failed export preservation, hashes, malformed matrix
rejection, pinned limits/metric agreement, provenance, cancellation, WebGL
fallback, reduced motion, keyboard seeks, offscreen pause and JSON download.
Synthetic browser protocol fixtures are separate from the measured inspection.

Local regression: 86 Python tests passed; one Windows symbolic-link creation test
was skipped because the host disallows it. Both native CTest checks, 13 frontend
contract tests and three legacy viewer tests passed. The complete browser run
passed 14 tests with three skips for scenarios absent from the selected legacy
replay bundle; all five new evaluation browser tests passed. The production demo
build, dependency lock, public-source scan and dated AeroLoop evidence index
checks passed. Existing lazy-renderer bundle-size and client-directive build
warnings remain informational.

The recorded physical limitations remain, including decision 007's unresolved yaw
refinement finding. No controller tuning, physics changes, training or new
GPU execution was performed for this slice.
