# Capture cadence and outage study

The timing study supplies held position and velocity to the outer trajectory
controller while Isaac PhysX and the native controller continue at 200 Hz.
It isolates capture timing from noise and transport delay. Use the
[observation robustness workflow](observation-robustness.md) for the separate
noise and 40 ms delay study.

| Profile | Capture cadence | Missing captures | Maximum feedback age |
| --- | --- | --- | --- |
| timing-ideal | 200 Hz | None | 0 ms |
| sample-hold | 50 Hz | None | 15 ms |
| dropout | 200 Hz | Two 250 ms windows | 250 ms |
| hold-dropout | 50 Hz | Two 250 ms windows | 275 ms |

Outages cover [18.000,18.250) and [40.000,40.250) simulation seconds, during
waypoint flight and the landing gust. Captures begin at time zero. Each outage
suppresses scheduled captures; the most recent successful position/velocity is
held until the next scheduled sample. Missed captures are never delivered later.
At 50 Hz, capture resumes at 18.260 and 40.260 seconds. Timing is synthetic and
fixed; these parameters do not represent a calibrated hardware sensor or network.

## Execute and inspect

Use the already configured isolated Isaac environment after accepting its terms.
With `OMNI_KIT_ACCEPT_EULA=YES` in the process environment, run development seed 73:

```text
python tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout --seeds 73 --monitor --realtime --output runs/timing-dev
```

Build the browser with `npm run demo:build` in `web/replay`. In another terminal:

```text
python tools/monitor.py runs/timing-dev --port 8774
```

Open the printed loopback URL and enable 3D. Aircraft pose and tracking error use
PhysX truth. The observations panel shows capture cadence, scheduled outage state,
last successful capture and actual source age. **Peak received observation age**
covers only the recent monitor frames; polling can miss the full-rate peak.
Monitor sample age and stale/disconnected status measure wall-clock freshness,
independently of simulated capture outages. The monitor is read-only.

Freeze source before the final matrix. Run all four profiles, each with
`--seeds 0 1 2 --monitor`, in distinct new directories. Add `--realtime` to
`hold-dropout`; keep the default 200 Hz physics. Do not edit tracked files during
capture. Keep every outcome, including exit code 2 for failed mission gates.

```text
python tools/timing_report.py runs/timing-ideal runs/sample-hold runs/dropout runs/hold-dropout --output timing-report.json
python tools/timing_plot.py runs/timing-ideal runs/sample-hold runs/dropout runs/hold-dropout --output timing-plot.png
```

The CPU report verifies all raw recordings, exact timing configuration, source
identity and the complete three-seed matrix. It reconstructs held feedback,
recomputes controller setpoints and preserves unchanged truth-based mission
gates. A complete study includes nine same-seed comparisons against timing-ideal.
Bounds remain 0.15 m peak position difference, 0.05 m absolute RMSE change and
0.5 s absolute landed-time change. Both dropout profiles also need recovery after
each window: position difference at or below 0.05 m for one continuous second,
starting within five seconds of the window end. Missing full dwell data fails.
The report returns 2 when acceptance fails; output files are never overwritten.
Plotting requires Matplotlib, but no GPU is needed to verify or plot retained data.

Version-seven recordings retain full-rate timing evidence. The existing recorded
replay exporters reject this family explicitly; use live 3D and the report/plot
for inspection. Version-six paired noise/delay replay remains supported.
Keep raw traces, logs and figures local.

Attitude/rate/acceleration feedback, mission supervision and contact sensing remain
ideal. No state estimator, hardware validation or general stability proof is
included. AL-010's yaw-refinement gate remains open. See
[decision 014](architecture/decisions/014-observation-timing.md) and
[validation](evidence/isaac-timing-validation.md).
