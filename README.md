# AeroLoop

A physics-based flight-control and learning laboratory with a C++ controller,
repeatable simulation experiments and recorded browser replay.

**Simulation-only MVP implemented.** CPU control, Isaac Sim physics, Isaac Lab
training and the reviewed website replay are validated in the
[MVP audit](docs/evidence/mvp-audit.md). Hosted website validation remains blocked
by its Actions budget; a versioned release is pending. PX4 flight execution is
outside scope. No physical-flight claims are made.

For continued drone development, use the [Isaac flight-control and 3D workflow](docs/drone-development.md).
It runs the C++ controller with four bounded rotors and motor lag in PhysX, then
opens the measured trajectory and attitude in an interactive local 3D replay.
The [turbulence demonstration](docs/turbulence.md) adds seeded wind and drag,
with a matching reference that makes the effect of position hold visible.

Python 3.11+ runs the dependency-free CPU tooling directly from a checkout:

```sh
python tools/aeroloop doctor
python tools/aeroloop check-lock
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
python tools/aeroloop test --suite cpu
python tools/aeroloop simulate --scenario hover --seed 0
python tools/aeroloop regress
```

On Windows use a Visual Studio developer terminal with CMake on PATH. Build tools
can be installed in an isolated environment with `pip install cmake==3.31.6 ninja==1.11.1.4`.
No command installs a simulator, accepts licenses or changes drivers.

Simulation writes checksummed runs under ignored `runs/`. Each trial runs the native
C++ controller against a CPU rigid body at 200 Hz; `regress` retains five seeds for
each of three scenarios. See [model assumptions](docs/physics-model.md). These CPU
results do not satisfy the separate Isaac physics or training gates.

The optional [Isaac workflow](docs/isaac-next-stage.md) uses an isolated, pinned
environment. Headless GPU physics and actual PPO training have run successfully:
the saved policy passed 20/20 held-out hover trials after a fresh-process reload,
versus 0/20 for the untrained policy. See [measured evidence](docs/evidence/isaac-validation.md)
and the [task contract](docs/architecture/decisions/002-isaac-hover-task.md).

Export one or more run directories printed by `simulate` or `regress`, then open
the loopback URL printed by `showcase`:

```sh
python tools/aeroloop verify-run runs/<run-id>
python tools/aeroloop export runs/<run-id> --output showcase/preview
python tools/aeroloop showcase --bundle showcase/preview
node --test web/viewer.test.mjs
python tools/check_public.py
```

Use a new output directory for each export. The exporter rejects fixtures, unknown
metadata, changed checksums and metrics that disagree with full-resolution samples.
Failed trials remain exportable and visibly labeled. The preview offers playback,
keyboard scrubbing, event jumps, experiment selection and static outcome summaries.
It loads no external scripts, assets or analytics. Press Ctrl+C to stop the preview.

The [reusable React/Three.js viewer](web/replay/README.md) adds optional 3D attitude,
verified selected-run loading, offscreen pause and a standalone demo. Hosts pin an
immutable evidence index. A [clean-checkout audit](docs/evidence/reproduction.md)
reproduced all fifteen CPU trials and the saved Isaac policy evaluation. The
[website integration checkpoint](docs/evidence/website-preview.md) records local
and served-site validation, with the remaining hosted-check limitation.

See the [MVP plan](docs/DESIGN_AND_MVP_PLAN.md), [roadmap](docs/roadmap/implementation-roadmap.md),
[architecture](docs/architecture/overview.md), [compatibility](docs/compatibility.md) and
[security policy](SECURITY.md). Original code is licensed under Apache-2.0.
