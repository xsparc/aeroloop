# Horizontal feedback quality

This opt-in experiment tests the extra horizontal position/velocity channel with
fixed noise and delay. It remains synthetic: no real sensor, fusion estimator or
hardware flight is implemented. See the frozen [protocol](architecture/decisions/019-horizontal-channel-quality.md)
and [validation record](evidence/isaac-quality-validation.md).

Use a clean committed checkout and the existing Isaac setup:

```powershell
python tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --predictive-feedback --fresh-axis horizontal --channel-quality noise-delay --seeds 73 --monitor --realtime --output runs/quality-development
python tools/monitor.py runs/quality-development --port 8771
```

Choose `ideal`, `noise`, `delay` or `noise-delay`. Use `sample-hold` for the
same-quality no-outage reference. Without `--channel-quality`, the existing
ideal axis-availability model remains unchanged. Quality requires horizontal
captures and excludes the landing guard. No defaults or acceptance limits change.

Noise is sampled once per 50 Hz acquisition: position sigma 0.01 m and velocity
sigma 0.02 m/s, clipped to three sigma. The separate seeded stream affects only
x/y; altitude remains masked. Delay is 40 ms plus up to 15 ms capture hold.
The first capture is available immediately at startup; steady delayed delivery
begins thereafter. The monitor separates truth, the main predictor and actual
applied feedback, with both channel ages and per-axis position errors.

After all workers finish, export the fixed matrix with paths ordered no-outage
then two-second outage for each quality:

```powershell
python tools/quality_demo.py --retained runs/axis-regression-horizontal-sample-hold-001 runs/axis-regression-horizontal-hold-dropout-2000ms-001 --ideal runs/quality-ideal-sample-hold-001 runs/quality-ideal-hold-dropout-2000ms-001 --noise runs/quality-noise-sample-hold-001 runs/quality-noise-hold-dropout-2000ms-001 --delay runs/quality-delay-sample-hold-001 runs/quality-delay-hold-dropout-2000ms-001 --noise-delay runs/quality-noise-delay-sample-hold-001 runs/quality-noise-delay-hold-dropout-2000ms-001 --output web/replay/public/quality-demo-001 --report runs/quality-study-001.json
```

Create ignored `web/replay/public/quality-config.json` with `baseUrl` set to
`/quality-demo-001/` and `indexSha256` set to the printed SHA256. Run
`npm run demo:build --prefix web/replay`, start a loopback Vite preview from
`web/replay`, and open `/quality.html`. Raw logs and bundles stay local.

Choose **Channel quality** and **Seed**, enable paired 3D, and use **Landing
outage** or scrub the timeline. The left is ideal horizontal feedback; the right
is the selected quality. Both have the same two-second main-channel outage.
Numeric values use recorded timestamps; only display poses interpolate. Mission
and recovery results use every 200 Hz sample. Each quality's outage pairs with
its own no-outage reference for the existing recovery and pair gates; the full
report also measures cross-quality differences against ideal feedback.

All nine outage comparisons remain visible, including failed and incomplete
flights. No-outage results and per-axis error windows are in the verified full
report. Loading remains bounded, same-origin and checksummed. Three regression
seeds and these fixed sensitivity settings cannot establish general robustness;
ideal attitude, simplified wind/contact and AL-010 yaw refinement remain limits.
