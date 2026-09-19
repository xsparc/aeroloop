# Validation record

## AL-001 foundation

Environment: Windows, Python 3.12.13. Date: 2026-09-20.

- `python tools/aeroloop test --suite cpu`: 5 tests passed.
- `python tools/aeroloop check-lock`: passed structural validation.
- `python tools/aeroloop doctor`: completed; Isaac modules absent; GPU available but unvalidated.
- `cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release`, `cmake --build build`,
  `ctest --test-dir build --output-on-failure`: passed, 1 C++ contract test,
  MSVC 19.51, CMake 3.31.6, Ninja 1.11.1.
- `python tools/check_evidence.py --as-of 2026-09-20`: passed traceability checks.

No Isaac workload, flight, training, public release or website deployment has run.

## AL-002 native controller and CPU physics

Date: 2026-09-20. Same CPU environment as AL-001.

- CMake build with compiler warnings treated as errors: passed.
- CTest: 2 tests passed (frames and rate-controller behavior).
- `python tools/aeroloop test --suite cpu`: 15 tests passed, including analytic
  freefall, hover equilibrium, axis signs, invalid inputs, seed repeatability,
  native lifecycle and timestep convergence.
- `python tools/aeroloop regress`: 15/15 computed trials completed; five seeds per
  hover, position-step and force-pulse scenario. Each full trial retained 7,001 samples.
- Hover steady-window RMSE ranged from 0.0000042 to 0.0000119 m in this ideal model.
  Position-step RMSE was approximately 0.228713 m. Force-pulse peak error was 0.086117 m;
  it remained inside the 0.30 m acceptance band throughout the post-pulse dwell.

These small hover errors reflect perfect state and ideal actuators, not aircraft
performance. Full-resolution data, configuration, source/binary hashes and outcomes
are retained in ignored `runs/`; they are not public source artifacts. PR checks do
not establish Isaac, training, autopilot or real-flight behavior.

## AL-003 evidence export and local replay

Date: 2026-09-20.

- `python tools/aeroloop test --suite cpu`: 32 tests passed, covering source hygiene,
  corrupt checksums, forged metrics, truncated recordings, unknown metadata, fixtures,
  path traversal, frame contracts, failed-trial retention and existing-output protection.
- `node --test web/viewer.test.mjs`: 3 tests passed for interpolation, discontinuous
  targets, endpoints, timestamp order and invalid pose data.
- Three full 35 s recordings were generated and exported. Raw samples remain in the
  bundle for metric reproduction; replay samples are reduced to approximately 20 Hz,
  with event instants and neighboring samples retained.
- Browser checks passed: checksum loading, scenario switching, play/pause, event jumps,
  keyboard scrubbing and URL state. Desktop and 390 px mobile layouts were inspected.
  No browser warnings or errors were reported during those checks.
- Loopback HTTP checks: index returned 200; repository metadata, parent paths and
  encoded parent paths returned 404. Server uses an explicit file allowlist and CSP.

This is a dependency-free local SVG preview. The reusable React/Three.js website
component remains AL-005. Checksums provide integrity, not source authentication.
