# Axis availability experiment

This opt-in experiment separates altitude and horizontal feedback availability
during the existing two-second capture outages. An extra noiseless, zero-delay
50 Hz synthetic channel supplies either z position/velocity or x/y
position/velocity. Unavailable components remain masked. The unchanged predictor
supplies the other components. It is not a physical sensor or a fused estimator.

Run from a clean committed checkout after the standard Isaac setup:

```powershell
python tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --predictive-feedback --fresh-axis vertical --seeds 73 --monitor --realtime --output runs/axis-development
python tools/monitor.py runs/axis-development --port 8771
```

Use `horizontal` for the other availability choice; `sample-hold` is the
no-outage reference. `--fresh-axis` excludes `--landing-guard`. All gains, mission
targets, wind, physics, contact supervision and acceptance deadlines stay fixed.
The monitor shows the main predictor estimate and actual applied feedback
separately, including fresh-channel age and horizontal/altitude errors.

The frozen [protocol](architecture/decisions/018-axis-availability.md) measures
24 fresh flights. All six seeds were previously tested. Compare the two choices
against retained predictor-only recordings. Every no-outage trace must remain
exact; all mission failures and incomplete recordings stay in the report.
Two-second trials are wall-paced; every trial is monitored at fixed 200 Hz.

Export only after all workers finish and recordings pass reconstruction:

```powershell
python tools/axis_demo.py --regression-baseline runs/predictor-sample-hold-001 runs/predictor-hold-dropout-2000ms-001 --prior-validation-baseline runs/guard-unseen-baseline-sample-hold-001 runs/guard-unseen-baseline-hold-dropout-2000ms-001 --regression-vertical runs/axis-regression-vertical-sample-hold-001 runs/axis-regression-vertical-hold-dropout-2000ms-001 --regression-horizontal runs/axis-regression-horizontal-sample-hold-001 runs/axis-regression-horizontal-hold-dropout-2000ms-001 --prior-validation-vertical runs/axis-prior-validation-vertical-sample-hold-001 runs/axis-prior-validation-vertical-hold-dropout-2000ms-001 --prior-validation-horizontal runs/axis-prior-validation-horizontal-sample-hold-001 runs/axis-prior-validation-horizontal-hold-dropout-2000ms-001 --output web/replay/public/axis-demo-001 --report runs/axis-study-001.json
```

Create ignored `web/replay/public/axis-config.json` with `baseUrl` set to
`/axis-demo-001/` and `indexSha256` set to the printed SHA256. Then run
`npm run demo:build --prefix web/replay` and a loopback Vite preview from
`web/replay`; open `/axis.html`. Keep generated recordings and bundles local.

Select **Fresh channel**, **Cohort**, and **Seed**, enable paired 3D, then use
**Landing outage** or the timeline. The left shows all-channel outages; the
right shows the selected fresh channel. Numeric values use recorded timestamps;
only display poses interpolate. Acceptance uses every 200 Hz sample. The full
download includes no-outage cases and per-axis error windows as well as all
unchanged mission, paired and sustained-recovery gates.

The 12 displayed pairs have bounded same-origin checksummed loading and retain
the numeric/trajectory fallback. This study cannot establish real-sensor or
hardware-flight performance; ideal attitude and contact supervision remain,
and independent yaw refinement is still open. Measured results live in the
[validation record](evidence/isaac-axis-validation.md).
