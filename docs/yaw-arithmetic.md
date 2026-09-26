# Yaw arithmetic study

Use this experiment to compare freely rotating PhysX bodies with independent
CUDA quaternion arithmetic. It does not run a replacement solver or alter flight
settings. Read [decision 011](architecture/decisions/011-yaw-arithmetic-study.md)
for the fixed hypothesis limits and the distinction from AL-010 acceptance.

Use the existing isolated Isaac environment with NVIDIA terms accepted, from a
clean Git commit. Warp is already included there; no extra dependency is needed.
On Windows:

```powershell
$env:OMNI_KIT_ACCEPT_EULA = "YES"
.local/IsaacLab/.venv/Scripts/python.exe tools/yaw_arithmetic.py --output runs/yaw-arithmetic-001
.venv/Scripts/python.exe tools/yaw_arithmetic_report.py runs/yaw-arithmetic-001 --output runs/yaw-arithmetic-summary.json
.local/IsaacLab/.venv/Scripts/python.exe tools/yaw_arithmetic_plot.py runs/yaw-arithmetic-001 --output runs/yaw-arithmetic.png
```

Use the corresponding `bin/python` executables on Linux. The installation
fingerprint supports the named Windows DLLs and Linux shared libraries; missing
or ambiguous components stop measurement. Choose fresh output paths. Partial
workers and failed outcomes stay available; never reuse their directory.

The first command runs six isolated PhysX workers serially, then an actual CUDA
arithmetic probe. Source and selected installation hashes are checked before
each worker and after capture. The probe composes normalized pure-yaw rotations
using library float32, fast-intrinsic float32 and library float64 sine/cosine.
All 18 constant-spin traces are compared at full rate. Torque remains in the
30-case physics matrix but is excluded from the arithmetic recurrence.

The CPU report rechecks physics traces, hashes, matrix/configuration identities
and all comparison metrics without loading Isaac or CUDA. Both execution and
report commands exit 2 if original yaw refinement, arithmetic controls or physics
diagnostic gates fail, while preserving their result files. The hypothesis flag
is an observation and is not a substitute for the original refinement gate.

A matching arithmetic signature supports a numerical mechanism; it does not
identify the installed binary's exact instruction path or validate a runtime
patch. Selected extension manifests and GPU libraries are fingerprinted, without
host paths. Raw traces, runtime logs and generated figures remain local.
The existing [paired 3D mission evaluation](flight-evaluation.md) continues to
show the unchanged controlled-flight baseline.
