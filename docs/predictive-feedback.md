# Predictive feedback and recorded flight demo

AL-019 adds an opt-in translational predictor and a repeatable local comparison
of held captures against predicted feedback. [Decision 016](architecture/decisions/016-predictive-outage-demo.md)
defines the model, frozen parameters and evaluation protocol. Read the
[validation record](evidence/isaac-predictor-validation.md) for measured outcomes.

Physics and native rate control run at 200 Hz; position/velocity captures arrive
at 50 Hz. Prediction uses the last capture, previous applied rotor thrust and
ideal measured attitude. It activates at 20 ms capture age, resets on fresh
captures and expires after 2.1 s. Raw observations remain recorded separately.
It receives no current truth position, velocity, wind or target input. This is
a simplified model observer, with ideal attitude and known actuation.

After the approved isolated Isaac setup, run a development case:

```powershell
$env:OMNI_KIT_ACCEPT_EULA = 'YES'
.venv/Scripts/python.exe tools/isaac.py flight --scenario ground-mission-wind --observation-profile hold-dropout-2000ms --predictive-feedback --seeds 73 --monitor --realtime --output runs/predictor-dev-001
```

The flag requires a 50 Hz outage-study profile. Omit it to retain held-capture
behavior. The live monitor exposes raw age and predictive mode with version-four
telemetry. Its samples are provisional; CPU verification reconstructs every
predictor update and controller setpoint before accepting a recording.

For the fixed regression matrix, use seeds `0 1 2` and each profile in order:
`sample-hold`, `hold-dropout`, `hold-dropout-500ms`, `hold-dropout-1000ms`,
`hold-dropout-2000ms`. Keep monitoring and pacing enabled. Output each profile
to `runs/predictor-<profile>-001`; never overwrite an existing study. Retain failed
outcomes. A worker exit of 2 means measured thresholds failed, not permission to
relax them. Incomplete or corrupt evidence is rejected or explicitly reported.

Export all retained reference and candidate recordings:

```powershell
.venv/Scripts/python.exe tools/prediction_demo.py --baseline runs/outage-sample-hold-001 runs/outage-hold-dropout-001 runs/outage-hold-dropout-500ms-001 runs/outage-hold-dropout-1000ms-001 runs/outage-hold-dropout-2000ms-001 --candidate runs/predictor-sample-hold-001 runs/predictor-hold-dropout-001 runs/predictor-hold-dropout-500ms-001 runs/predictor-hold-dropout-1000ms-001 runs/predictor-hold-dropout-2000ms-001 --output web/replay/public/predictor-demo-001 --report runs/predictor-study-001.json
```

The exporter verifies both full cohorts, matches runtime/native controller and
configuration, compares no-outage traces exactly, and emits checksummed bounded
display files. Exit zero means export succeeded; inspect the report's `accepted`
field for the unchanged stress gates. Display samples are 20 Hz with event/outage
neighbors and endpoints; all scoring uses 200 Hz recordings.

Create ignored `web/replay/public/outage-config.json`, replacing the checksum with
the exporter's printed index SHA-256:

```json
{"baseUrl":"/predictor-demo-001/","indexSha256":"<printed index SHA-256>"}
```

From `web/replay`, run `npm run demo:build`, then
`npx vite preview --host 127.0.0.1 --port 8778 --strictPort` and open
`http://127.0.0.1:8778/outage.html`. The demo works without an active GPU worker.
Select duration and seed, enable paired 3D, press Play or jump to an outage or
landing chapter. Both views share time and speed. Inspect all original mission
gates and download the verified full-rate study. Failed runs remain visible.
The page pauses when hidden/offscreen, starts paused with reduced motion, and
retains trajectory/numeric evidence when WebGL is unavailable.

Keep raw logs, host metadata, artifacts and recordings outside Git. Only sanitized
summary evidence belongs in the public repository. The independent yaw-refinement
finding remains open; these regression cases do not establish hardware safety or
performance on unseen disturbances.

The later [landing-guard experiment](landing-guard.md) adds an opt-in descent command and a separate frozen unseen-seed cohort. It retains the predictor and every original scoring limit; it does not increase mission pass counts.
