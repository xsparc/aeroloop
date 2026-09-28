# Outage duration and sustained recovery

This study runs the native controller in turbulent Isaac PhysX contact missions
with 50 Hz position/velocity captures and fixed missing-capture windows. Physics
and control continue at 200 Hz. The reference is `sample-hold`, with the same
capture cadence and no outages. Compare `hold-dropout` (250 ms),
`hold-dropout-500ms`, `hold-dropout-1000ms` and `hold-dropout-2000ms`.
Each outage begins at 18 or 40 simulation seconds; capture resumes on its next
scheduled 20 ms boundary. Maximum feedback ages are 275, 515, 1015 and 2015 ms.
The original [timing study](observation-timing.md) retains its separate ideal
reference and first-dwell semantics.

## Reproduce and inspect

Use the configured isolated Isaac environment with its accepted terms and
`OMNI_KIT_ACCEPT_EULA=YES`. First execute the development case:

```text
python tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --seeds 73 --monitor --realtime --output runs/outage-dev
```

Build the browser using `npm run demo:build` in `web/replay`, then start the
read-only monitor in another terminal:

```text
python tools/monitor.py runs/outage-dev --port 8776
```

Open the printed loopback address and enable 3D. Pose and tracking error show
physics truth. The observations panel shows the exact outage windows, source
timestamp and age; wall-clock telemetry freshness is independent. Peak received
age covers monitor frames and may miss the full-rate maximum. A completed
recording with failed mission gates remains visibly failed.

Freeze source before the final matrix. Run **all five profiles**, each with
`--seeds 0 1 2 --monitor --realtime`, into separate new directories. Keep every
result, including mission-failure exit code 2. Exit code 1 is an execution or
verification failure and requires investigation. Do not edit tracked files while
capturing. Verify and plot without needing a GPU:

```text
python tools/outage_report.py runs/outage-reference runs/outage-250 runs/outage-500 runs/outage-1000 runs/outage-2000 --output outage-report.json
python tools/outage_plot.py runs/outage-reference runs/outage-250 runs/outage-500 runs/outage-1000 runs/outage-2000 --output outage-plot.png
```

Plotting needs Matplotlib. Files are never overwritten. The report verifies raw
hashes, exact capture schedules and held values, reconstructed controller inputs,
shared source/runtime/configuration and all fifteen cases. It exits 2 after
writing verified evidence if any stress acceptance gate fails. `complete` means
all traces contain 10001 samples; it does not mean they passed.

## Read the outcomes

Every duration has three mission outcomes and three same-seed comparisons.
Paired bounds remain 0.15 m peak separation, 0.05 m absolute tracking RMSE change
and 0.5 s absolute landed-time change. Outage profiles also have six recovery
windows. Recovery starts at the final continuous return to within 0.05 m of the
reference after outage end, with at least one full second of data and no later
excursion before the next outage or recording end. Its start must be within
five seconds of outage end. Missing complete evidence fails; late or absent
recovery stays visible. `excursion_observed` distinguishes recovery exercised
outside the band from merely remaining within it.

Reports preserve each duration independently. A failed pair can still recover;
a recovered pair can still fail a mission gate. Do not infer a safe outage
duration or a monotonic boundary between tested points. Figures plot full-rate
truth separation and capture age; dashed lines mark outage starts.

Version-seven recordings and version-three live telemetry retain their existing
shape with additional strict profiles. Recorded timing replay remains explicitly
unsupported. Keep raw traces, logs and figures local. Attitude/rates/acceleration,
mission supervision and contact sensing remain ideal. The synthetic outages
do not model calibrated hardware, estimation or a network. Wall pacing is soft
real time and reports lag; AL-010 yaw refinement remains open.

See [decision 015](architecture/decisions/015-outage-recovery.md) and
[measured validation](evidence/isaac-outage-validation.md).
