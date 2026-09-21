# Verify numerical physics

The accuracy suite isolates gravity, tilted body thrust, yaw torque, motor lag,
quadratic drag and ground impact. It uses actual Isaac PhysX with the drone's
mass, inertia and existing rotor/drag functions. Continuous-time reference
equations are independent of the simulation integrator. This tests numerical
implementation; it does not calibrate an aircraft.

Prepare the [isolated Isaac environment](isaac-next-stage.md) and accept NVIDIA's
terms first. Run development trials, then freeze a clean checkout and execute all
six commands using new output directories:

```sh
python tools/isaac.py physics --physics-dt 0.005 --output runs/physics-200
python tools/isaac.py physics --physics-dt 0.0025 --output runs/physics-400
python tools/isaac.py physics --physics-dt 0.00125 --output runs/physics-800
python tools/isaac.py physics --force-mode per-step --physics-dt 0.005 --output runs/physics-step-200
python tools/isaac.py physics --force-mode per-step --physics-dt 0.0025 --output runs/physics-step-400
python tools/isaac.py physics --force-mode per-step --physics-dt 0.00125 --output runs/physics-step-800
python tools/physics_report.py runs/physics-200 runs/physics-400 runs/physics-800 runs/physics-step-200 runs/physics-step-400 runs/physics-step-800 --output runs/physics-summary.json
```

The default applies forces during each TGS iteration, matching the existing
flight bridge. `per-step` is an explicit diagnostic using a deprecated PhysX
option; it is not a recommended flight configuration. The suite uses a 10 mm
contact-generation margin per collider for the faster drop, with unchanged body
geometry, floor height and zero rest offset. Earlier mission scenes are unchanged.

Each worker requires six complete traces and recomputes inputs and metrics before
returning success. Exit code 2 means measured acceptance failed. The report
requires all three timesteps in both modes, matching clean source/configuration
provenance and versions. It retains failures and writes its summary before
returning 2 if any absolute-error or refinement gate is unmet. A completed report
does not imply acceptance. Never replace a failed trace or weaken its gate.

To generate the diagnostic figure, use the isolated Isaac Python environment,
which already includes Matplotlib, with the same six directories:

```sh
python tools/physics_plot.py runs/physics-200 runs/physics-400 runs/physics-800 runs/physics-step-200 runs/physics-step-400 runs/physics-step-800 --output runs/physics-accuracy.png
```

Plots use verified measured traces. Raw trace files, plots under `runs/` and host
logs remain ignored. Public summaries contain only declared fields and checksums.
The [3D mission replay](wind-mission.md) remains available separately; these force
isolation cases are not closed-loop mission recordings.

[Decision 007](architecture/decisions/007-physics-accuracy-suite.md) specifies all
limits. [Validation](evidence/isaac-physics-validation.md) records the matrix and
open findings, including the default solver's yaw-refinement result. Peak impact
force is not a timestep-independent quantity; use impulse/momentum and resting
support for contact checks. Full mission convergence and physical-model fidelity
require separate studies.
