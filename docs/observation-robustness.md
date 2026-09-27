# Observation robustness in PhysX

The optional `--observation-profile` flag tests outer-loop position and velocity
feedback during the 50-second turbulent contact mission. Omit it for the existing
perfect-state schema-five workflow. Explicit `ideal` selects the new schema with
zero perturbation; `noise`, `delay` and `noise-delay` select the fixed profiles in
[decision 012](architecture/decisions/012-observation-robustness.md).

Noise is captured at 200 Hz using a separate seeded stream, with nominal 0.01 m
position and 0.02 m/s velocity Gaussian standard deviations, clipped at three
standard deviations. Delay is eight samples (40 ms); startup holds the first
capture. The combined profile delays that same captured noise. Every sample
records the delivered vectors, source sequence/time and actual age.

Only the outer trajectory controller receives these vectors. Attitude, angular
rates/acceleration and the contact mission supervisor remain ideal. Wind and drag,
rotor forces, contact and all mission scores use the actual PhysX state. This is
not a calibrated sensor model or a learned policy evaluation. The independent
yaw-refinement finding remains open.

## Run and monitor

Use the existing isolated Isaac installation after accepting its terms. From the
repository root, with `OMNI_KIT_ACCEPT_EULA=YES` in the process environment:

```text
python tools/isaac.py flight --scenario ground-mission-wind --observation-profile noise-delay --seeds 73 --monitor --realtime --output runs/observation-dev
```

Build `web/replay` with `npm run demo:build`, then in another terminal:

```text
python tools/monitor.py runs/observation-dev --port 8771
```

Open `http://127.0.0.1:8771/` and enable 3D. Aircraft pose and tracking error show
physics truth; the observation panel reports delivered feedback age and position/
velocity discrepancy. Live data is provisional; final file verification decides
acceptance. The monitor is read-only and loopback-only. Late wall frames never
skip physics integration or change the timestep.

## Repeat the fixed study

Run one fresh output directory per profile, with `--seeds 0 1 2 --monitor`.
Add `--realtime` for `noise-delay`; keep physics/control at the default 200 Hz.
Do not edit tracked files during capture. Run all four profiles even if a worker
returns status 2: failed mission results remain part of the study.

```text
python tools/observation_report.py runs/observation-ideal runs/observation-noise runs/observation-delay runs/observation-noise-delay --output observation-report.json
python tools/observation_plot.py runs/observation-ideal runs/observation-noise runs/observation-delay runs/observation-noise-delay --output observation-plot.png
```

The report reconstructs captured observations from full-rate truth and seed,
recomputes controller setpoints and unchanged mission gates, requires a complete
clean-source matrix, and compares each perturbed flight with its same-seed ideal
flight. The frozen bounds are 0.15 m peak truth-position difference, 0.05 m
absolute position-RMSE change and 0.5 s landed-time change. A failed comparison
is retained and returns exit code 2. Existing output files are never overwritten.

Keep raw traces and figures local. The [recorded observation explorer](observation-evaluation.md)
revalidates schema-six recordings for paired 3D comparison, with separate truth
and held-feedback readouts. Use its `--observations` export mode; the legacy
single-run replay exporter continues to reject this schema.

See the [retained twelve-flight validation](evidence/isaac-observation-validation.md)
for measured results and the exact source revision. Plotting requires Matplotlib
in the reporting interpreter; GPU execution is not required to verify or plot
existing recordings.
