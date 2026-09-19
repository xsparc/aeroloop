# AeroLoop

A physics-based flight-control and learning laboratory with a C++ controller,
repeatable simulation experiments and recorded browser replay.

**In development.** The MVP includes Isaac Sim physics and Isaac Lab training.
PX4 flight execution is outside the revised MVP. No physical-flight claims are made.

Python 3.11+ runs the dependency-free CPU tooling directly from a checkout:

```sh
python tools/aeroloop doctor
python tools/aeroloop check-lock
python tools/aeroloop test --suite cpu
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

On Windows use a Visual Studio developer terminal with CMake on PATH. Build tools
can be installed in an isolated environment with `pip install cmake==3.31.6 ninja==1.11.1.4`.
No command installs a simulator, accepts licenses or changes drivers.

See the [MVP plan](docs/DESIGN_AND_MVP_PLAN.md), [roadmap](docs/roadmap/implementation-roadmap.md),
[architecture](docs/architecture/overview.md), [compatibility](docs/compatibility.md) and
[security policy](SECURITY.md). Original code is licensed under Apache-2.0.
