# Yaw integration diagnostics

Use this separate experiment to investigate signed yaw error without retuning a
flight controller. It initializes a freely rotating body or applies constant yaw
torque in actual Isaac PhysX. Public cached and direct tensor reads are recorded
after each simulation step. Both angular-rate channels use world coordinates.

The isolated Isaac environment and previously accepted NVIDIA terms are required.
Set `OMNI_KIT_ACCEPT_EULA=YES` after reviewing the terms. Run from a clean commit:

```sh
python tools/isaac.py yaw --physics-dt .005 --solver-iterations 4 --output runs/yaw-4-200
python tools/isaac.py yaw --physics-dt .0025 --solver-iterations 4 --output runs/yaw-4-400
python tools/isaac.py yaw --physics-dt .00125 --solver-iterations 4 --output runs/yaw-4-800
python tools/isaac.py yaw --physics-dt .005 --solver-iterations 1 --output runs/yaw-1-200
python tools/isaac.py yaw --physics-dt .0025 --solver-iterations 1 --output runs/yaw-1-400
python tools/isaac.py yaw --physics-dt .00125 --solver-iterations 1 --output runs/yaw-1-800
python tools/yaw_report.py runs/yaw-4-200 runs/yaw-4-400 runs/yaw-4-800 runs/yaw-1-200 runs/yaw-1-400 runs/yaw-1-800 --output runs/yaw-summary.json
```

Use new output directories. Each worker retains all five traces, their checksums,
source identity, fixed configuration, versions and independently recomputable
metrics. A worker exits 2 on a measured diagnostic failure; the files remain
available. A missing or invalid completion artifact is an execution failure.
The report requires the complete six-worker matrix at one clean source revision,
rejects forged aggregates and exits 2 if the original default refinement gate
or any absolute diagnostic gate fails. Do not remove failed trials.

Use `tools/yaw_plot.py` with the same six directories and `--output runs/yaw.png`
in an environment with Matplotlib to inspect the signed full-rate errors. The
existing [3D flight evaluation](flight-evaluation.md) remains the mission
demonstration; these isolated diagnostics are not mission recordings.

The analytic reference is theta = omega0*t + torque*t²/(2*Izz), with Izz=0.04.
The rate-integral residual uses trapezoidal integration of measured angular rate
as a separate consistency diagnostic. Pose agreement only rules out disagreement
between the sampled API paths; it does not prove the internals of the GPU solver.
One position iteration is an experiment, not a recommended flight configuration.
All bounds and scope are fixed in [decision 010](architecture/decisions/010-yaw-orientation-audit.md).

See the [measured validation](evidence/isaac-yaw-validation.md) for the retained
30-case matrix and the distinction between diagnostic success and the still-open
default refinement finding.
