# Flight diagnosis workspace

The workspace adds ten inspection tools to the retained horizontal-quality
experiment. It loads actual Isaac Sim / PhysX recordings and preserves failed
missions. This is recorded playback, not a live simulation or new validation
cohort. See [ADR 020](architecture/decisions/020-flight-diagnosis.md) and the
[validation record](evidence/flight-diagnosis-validation.md).

| Tool | Use |
|---|---|
| Case matrix | Filter 24 flights by quality, outage profile and outcome; sort by support-position headroom |
| Same-quality 3D | Compare with the same seed and quality without main-channel outages |
| Full-rate plots | Inspect each 5 ms sample with a shared cursor, playback, speed and editable window |
| Event navigation | Jump to exact recorded touchdown, landed, route and outage timestamps |
| Phase error summary | Separate airborne descent, contact and motors-off errors in [40,42) s |
| Feedback layers | Toggle truth, raw capture, predictor and applied altitude |
| Gate headroom | See all 24 unchanged mission gates with signed allowance and native units |
| Recovery inspection | Inspect same-quality pair failures and final uninterrupted recovery horizons |
| Provenance | Inspect source/binary/lock/sample hashes, runtime and sample coverage |
| Window CSV | Export every numeric sample in the selected inclusive time interval |

Prepare the retained [quality study](horizontal-quality.md) first. The exporter
reconstructs every original recording, repeats the ideal-reference comparison,
and checks the fixed four-quality matrix before writing anything:

```powershell
python tools/diagnosis_demo.py --retained runs/axis-regression-horizontal-sample-hold-001 runs/axis-regression-horizontal-hold-dropout-2000ms-001 --ideal runs/quality-ideal-sample-hold-001 runs/quality-ideal-hold-dropout-2000ms-001 --noise runs/quality-noise-sample-hold-001 runs/quality-noise-hold-dropout-2000ms-001 --delay runs/quality-delay-sample-hold-001 runs/quality-delay-hold-dropout-2000ms-001 --noise-delay runs/quality-noise-delay-sample-hold-001 runs/quality-noise-delay-hold-dropout-2000ms-001 --output web/replay/public/diagnosis-demo-001 --report runs/diagnosis-study-001.json
```

Use new output paths on every export. Create ignored
`web/replay/public/diagnosis-config.json` with `baseUrl` equal to
`/diagnosis-demo-001/` and `indexSha256` equal to the printed digest. Then:

```powershell
npm run demo:build --prefix web/replay
cd web/replay
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 8790 --strictPort
```

Open `/diagnosis.html`. The initial selection is the combined-quality seed-0
outage flight, including its failed support gate. Enable paired 3D and press
Play. Select ideal seed 1 with two-second outages, jump to **landed**, and inspect
the motors-off phase to see why large late predictor errors need separate
interpretation. The no-outage selection explicitly compares a reference with
itself; it does not claim pair or recovery success.

Numeric values use the preceding original sample. Plots and CSV retain every
200 Hz point; only the schematic 3D poses interpolate between display samples.
CSV endpoints are inclusive, while the fixed phase summary is [40,42). Phase
codes are 0 other, 1 airborne descent, 2 contact, 3 motors-off. Empty groups and
truncated horizons remain unmeasured or failed. Contact can be intermittent, so
airborne-descent samples can occur after the first touchdown timestamp.
Motors-off means landed with zero requested thrust; residual physical rotor
thrust can decay after that command.

Signed gate headroom is a distance to the original bound, not a confidence
interval or a cross-unit ranking. Strict less-than gates fail at zero headroom;
equality gates pass only at zero. Sorting uses only final support XY headroom
in metres. Mission, pair and recovery are separate outcomes.

Exports contain allowlisted numerical data and source identity, no host paths.
The browser checks pinned hashes, bounded same-origin payloads, complete matrix
identity and internal consistency. A checksum pins bytes; it is not independent
physical validation. The full recording validator runs during export. Keep
generated bundles, logs and screenshots local.
