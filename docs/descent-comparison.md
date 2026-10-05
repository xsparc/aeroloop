# Vertical prediction and descent comparison

AL-024 adds ten features under [decision 021](architecture/decisions/021-vertical-disturbance-decay.md):

1. An opt-in vertical disturbance decay predictor, leaving the original mode as default.
2. Live learned-anchor, effective-acceleration and decay-scale telemetry.
3. Baseline/candidate 3D comparison across two profiles and two seed cohorts.
4. Common simulation time or each flight's touchdown as the alignment origin.
5. Full-rate truth, feedback, target and error plots for vertical velocity.
6. Vertical P, D, feedforward and clipped-command inspection.
7. Contact force, clearance, velocity eligibility, dwell and landed latch inspection.
8. Requested versus realized rotor thrust, world vertical thrust and wind force.
9. Local selection links bound to the evidence index hash.
10. JSON comparison export with original gates, provenance and measured window summaries.

The numeric plots retain every 200 Hz sample. Poses use 20 Hz plus event boundaries
and interpolate only for 3D display. Contact-aligned views deliberately use different
absolute times; gusts and outages no longer coincide. Links require the same local
demo and evidence version. The browser cannot send flight-control commands.

## Run the experiment

Use the existing isolated Isaac environment and native controller build. Freeze a
clean source commit for all final workers. The following example is a **development**
run, excluded from final acceptance:

```powershell
$env:OMNI_KIT_ACCEPT_EULA = "YES"
.venv/Scripts/python.exe tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --predictive-feedback --fresh-axis horizontal --channel-quality noise-delay --vertical-decay --seeds 73 --monitor --realtime --output runs/decay-development-outage
```

Also run development seed 73 with `sample-hold`. For the final matrix, run the
candidate on seeds 0, 1, 2 and compare with retained AL-022 combined-quality
recordings. Run both modes on the predeclared seeds 401, 503, 607. Every group needs
both `sample-hold` and `hold-dropout-2000ms`; omit `--vertical-decay` for baseline.
Monitor all workers and pace all outage workers. Use separate new output directories.
Do not edit tracked files while a physics worker is running. Exit code 2 retains
completed threshold failures and must not cause a rerun that replaces them.

The monitor uses `tools/monitor.py SESSION --port PORT` after building the replay
assets. Evidence v12 and live v8 add the candidate telemetry. Older evidence and
the baseline predictor remain supported. The recording reader reconstructs the
decay state from captures and previous actuator output before accepting it.

## Prepare the local demo

`tools/decay_study.py` accepts four directory pairs: `--regression-baseline`,
`--regression-candidate`, `--additional-baseline`, `--additional-candidate`.
Within each pair, provide no-outage then outage sessions. Set `--report` to a new
JSON path and `--demo` to a new directory under `web/replay/public/`. The tool
reconstructs all recordings and original gates, checks runtime and source identity,
requires exact normal-capture continuity, and exports only allowlisted data.

Create ignored `web/replay/public/descent-config.json` with exactly `baseUrl`
(the exported directory's same-origin URL) and `indexSha256` (the report's
`demo_index_sha256`). Run `npm run dev -- --port PORT --strictPort` from
`web/replay`, then open `/descent.html`. For a production preview, run
`npm run demo:build` and `node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port PORT --strictPort`.

## Interpret the measurements

The candidate fades only the disturbance used in vertical propagation after the
normal 15 ms hold. It preserves the learned anchor and horizontal prediction.
The fixed 0.2 s time constant is a hypothesis, not a calibrated wind model.

Vertical P/D/feedforward terms are before gravity and are zero while disarmed.
Total thrust also includes horizontal acceleration demand. A zero thrust request
does not instantly remove realized rotor force. Contact force reflects the preceding
physics interval; the independent ideal contact supervisor uses truth and latches
landed after 50 ms of continuous eligibility. That truth is not fed to the predictor.

Window RMSE and thrust impulses are descriptive, using a half-open time interval.
They do not replace the full-run mission, same-mode outage-pair or sustained-recovery
criteria. Failures and incomplete coverage remain visible. Additional seeds provide
a bounded check, not statistical robustness or hardware-flight validation. Synthetic
sensors, ideal attitude/contact supervision and AL-010 yaw refinement remain limitations.
