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
