# Capture-aware landing experiment

AL-020 adds `--landing-guard` to the existing predictive-feedback flight mode.
[Decision 017](architecture/decisions/017-landing-capture-guard.md) fixes the
parameters and regression/unseen protocol. The guard is opt-in and requires
`--predictive-feedback` with a 50 Hz capture profile.

During landing, capture age of at least 0.6 s pauses commanded descent at a
minimum altitude of 0.30 m. Fresh captures must show horizontal distance and speed
at most 0.20 m and 0.20 m/s for 0.30 s before a four-second quintic descent resumes.
The contact supervisor keeps disarm authority. The original scheduled target,
mission deadline and every scoring limit stay unchanged. A delayed descent can
therefore improve touchdown while failing tracking or timing gates.

After the approved isolated Isaac setup, capture a development case:

```powershell
$env:OMNI_KIT_ACCEPT_EULA = 'YES'
.venv/Scripts/python.exe tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --predictive-feedback --landing-guard --seeds 73 --monitor --realtime --output runs/guard-dev-001
.venv/Scripts/python.exe tools/monitor.py runs/guard-dev-001 --port 8781
```

The read-only loopback monitor exposes version-five telemetry: raw capture age,
predictor mode, guard mode, commanded altitude and original scheduled altitude.
Enable 3D to inspect the measured pose. Samples are provisional until full-rate
CPU reconstruction verifies the completed recording.

Freeze a clean revision before the final matrix. Run regression seeds `0 1 2`
with guard enabled on `sample-hold`, `hold-dropout-500ms`,
`hold-dropout-1000ms`, `hold-dropout-2000ms`, saving each profile under
`runs/guard-regression-<profile>-001`. Then run previously unused seeds
`101 202 303` for `sample-hold` and `hold-dropout-2000ms` with and without the
guard under `runs/guard-unseen-candidate-<profile>-001` and
`runs/guard-unseen-baseline-<profile>-001`. Monitor every flight and pace both
unseen two-second cohorts. Retain failed and incomplete outcomes. Do not adjust
parameters after inspecting the final matrix.

Export against the retained predictor-only regression recordings:

```powershell
.venv/Scripts/python.exe tools/landing_demo.py --regression-baseline runs/predictor-sample-hold-001 runs/predictor-hold-dropout-500ms-001 runs/predictor-hold-dropout-1000ms-001 runs/predictor-hold-dropout-2000ms-001 --regression-candidate runs/guard-regression-sample-hold-001 runs/guard-regression-hold-dropout-500ms-001 runs/guard-regression-hold-dropout-1000ms-001 runs/guard-regression-hold-dropout-2000ms-001 --unseen-baseline runs/guard-unseen-baseline-sample-hold-001 runs/guard-unseen-baseline-hold-dropout-2000ms-001 --unseen-candidate runs/guard-unseen-candidate-sample-hold-001 runs/guard-unseen-candidate-hold-dropout-2000ms-001 --output web/replay/public/landing-demo-001 --report runs/landing-study-001.json
```

Export success means evidence was verified, not that all stress gates passed.
Inspect `accepted` and the separate cohort outcomes. The exporter requires exact
inactive-guard traces, unchanged preactivation samples, matched configuration and
runtime, and one frozen source for all fresh cohorts. It keeps the original
full-rate scoring and preserves guard transitions in the display samples.

Create ignored `web/replay/public/landing-config.json` using the printed checksum:

```json
{"baseUrl":"/landing-demo-001/","indexSha256":"<printed index SHA-256>"}
```

From `web/replay`, run `npm run demo:build`, then
`npx vite preview --host 127.0.0.1 --port 8783 --strictPort` and open
`http://127.0.0.1:8783/landing.html`. Select cohort, outage and seed, enable paired
3D, and use the guard/descent chapters or synchronized playback. The scene's
target remains the original schedule; commanded altitude is shown separately.
Inspect all gates or download the verified study. No active GPU worker is needed
for recorded playback. Data is checksummed, bounded and loaded from the same
origin; failures remain visible and WebGL has a numeric/trajectory fallback.

Holding a command does not ensure actual altitude when the predicted state is
wrong. This experiment uses ideal attitude and supervision with synthetic wind,
captures and contact. It is not a hardware failsafe. Keep raw logs, recordings
and host metadata out of Git. See the [validation record](evidence/isaac-landing-guard-validation.md).
