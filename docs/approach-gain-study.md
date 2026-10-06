# Horizontal approach gain study

AL-026 provides the ten controller, monitoring and evaluation features in
[decision 023](architecture/decisions/023-approach-gain-study.md). The scheduled
horizontal gains blend over 34–35 s, from position 2.5 to 4.0 s^-2 and velocity
2.8 to 3.6 s^-1. Altitude control, integral limits, physics, synthetic feedback
and original acceptance gates are fixed. This mode remains opt-in.

Use the existing isolated Isaac installation and native controller. Commit the
complete source before workers and leave tracked files unchanged during them.
Development seed 83 is excluded from the final cohorts:

```powershell
$env:OMNI_KIT_ACCEPT_EULA = "YES"
.venv/Scripts/python.exe tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --predictive-feedback --fresh-axis horizontal --channel-quality noise-delay --vertical-decay --approach-gains --seeds 83 --monitor --realtime --output runs/approach-development-outage
```

Also use `sample-hold`. Final candidate seeds are regression 0/1/2, known stress
401/503/607, and predeclared additional 709/811/907. Retain AL-024 vertical-decay
baselines for regression/stress; run both modes for additional seeds. Omit only
`--approach-gains` for baseline. Every session uses monitoring and outage sessions
use pacing. Completed threshold failures return exit 2; retain them without
replacement. Do not overwrite output directories.

Build browser assets with `npm run demo:build` from `web/replay`. The live server
is `tools/monitor.py SESSION --port PORT`; it shows provisional gain blend and
current gains alongside 3D physics truth, rotors, feedback and wall-clock lag.
Received history can skip samples. Recording v13 reconstructs the complete
schedule and commands; live v9 validates each received schedule value.

## Export and view the comparison

Run `tools/approach_study.py` with six directory-pair arguments:
`--regression-baseline`, `--regression-candidate`, `--stress-baseline`,
`--stress-candidate`, `--additional-baseline`, `--additional-candidate`.
Each takes the no-outage session then its outage session. Supply a new `--report`
JSON path and a new `--demo` directory below `web/replay/public/`.
The exporter reconstructs all 36 flights, verifies fixed source/runtime settings,
and requires exact pre-ramp continuity through t<34 s for all eighteen pairs.

Create ignored `web/replay/public/approach-config.json` with exactly `baseUrl`
(the same-origin exported directory) and `indexSha256` (the report's
`demo_index_sha256`). Start `npm run dev -- --port PORT --strictPort` from
`web/replay` and open `/approach.html`. A production preview uses
`npm run demo:build` then
`node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port PORT --strictPort`.

Cohort outcomes and failed/regressed filters retain every result. Paired 3D and
full-rate curves share one cursor, with optional time relative to the 40 s gust.
Jump to the ramp, gust, contact or disarm; compare all original gates and margins.
Links bind the case/cursor/time origin to the index digest. JSON exports carry
the 42-column landing rows, gain settings, original outcomes and provenance.

Cumulative squared error is in m² s; squared acceleration demand is in m²/s³,
not joules. Both integrate left-endpoint values on [34,t), excluding an extra
terminal interval. Clipping occupancy counts observed intervals exceeding the
4 m/s² horizontal axis clamp. Allocation scale reports retained authority when
motor allocation saturates, not spare thrust capacity. Missing coverage remains
explicit. Same-mode outage pair/recovery gates remain independent of descriptive
cross-mode improvements. Ideal attitude and contact supervision, synthetic wind
and channels, limited cohorts and open AL-010 yaw refinement bound interpretation.

[Measured results](evidence/isaac-approach-validation.md): mission passes 12/18 →
15/18, outage pairs 7/9 → 8/9, recovery windows 14/18 → 15/18.
Every failure is retained. The candidate is experimental and remains opt-in.
