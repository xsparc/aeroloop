# Landing response lab

The response lab groups the 36 AL-026 recorded PhysX flights into nine seeds,
each with fixed/scheduled gains and intact/two-second-outage feedback. It adds
the [ten tools in ADR 024](architecture/decisions/024-landing-response-lab.md)
without running another flight or changing the controller. Open `/response.html`
from the approach study to inspect all four flights at one simulation time.

## Run the working demo

Prepare the verified [approach export](approach-gain-study.md), including its
ignored `web/replay/public/approach-config.json`. Both workspaces use that same
digest-pinned bundle; there is no second copy or separate runtime to install.
From `web/replay`, run `npm run build`, `npm run demo:build`, then:

```sh
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 8798 --strictPort
```

Open `http://127.0.0.1:8798/response.html`. Choose a seed, select the requested
window, and enable four-flight 3D. Plots keep every recorded interval; only
3D playback interpolates. Per-flight original gates and source hashes remain
available below each view. Missing coverage disables combined comparisons.

**All pre-contact** uses a common interval ending one sample before the earliest
contact. **All armed** similarly ends before the earliest disarm.
**All disarmed** starts at the latest disarm. Missing events make the relevant
preset unavailable. Custom windows and the gust preset can include different
physical phases, so inspect airborne/contact/disarmed duration for each cell.
An interval is contact-affected when either endpoint has normal force >0.1 N,
unless its starting state was already disarmed.

Outage effects subtract the intact metric from the outage metric within a
gain mode. The interaction subtracts the fixed-gain effect from the scheduled
effect. Window RMSE contrasts and pointwise distance contrasts are different
quantities. Neither replaces mission, outage-pair or recovery acceptance.
Both outages influence the landing history; these comparisons do not isolate
the second outage's causal effect or establish population robustness.

The radial portrait shows distance against closing speed. Closing is positive
toward the moving target. Applied-feedback error is projected onto the outward
radial direction and its counterclockwise tangent. The direction is undefined
within 1 nm of the target; plots break there and CSV fields remain empty.

Work accounting uses the previous sample's wind/thrust force dotted with the
observed horizontal displacement. Kinetic change uses endpoint velocities for
the 1 kg model. The unexplained residual is **not measured friction**, and this
is not battery energy or a full mechanical-energy balance. Acceleration uses
velocity change over the next 5 ms interval; contact impulses and actuator
dynamics can make it differ from the commanded acceleration.

**Compare nine seeds** applies the exact requested window to every seed and
verifies all inputs before showing a complete sortable table. Switching the
window clears that table. Selecting a row changes the four-flight view without
changing the shared window. A phase window chosen for one seed need not be the
same phase on another seed; the table retains airborne duration.

## Reproduce and export

The JSON review binds the seed, window, cursor, method and four source identities
to the index digest; it retains original gates and all available window rows.
The CSV preserves all 42 input columns plus radial and interval diagnostics.
The terminal state has empty next-interval fields. Each row identifies the
requested window and whether that flight fully covers it. Use JSON to retain
explicit empty flights and acceptance details. Review links require the same
bundle on the receiving machine; they do not upload data.

After `npm run build` in `web/replay`, generate a nine-seed numeric report from
the repository root. Pass the actual pinned digest, never an unverified checksum:

```sh
node tools/response_report.mjs --bundle web/replay/public/approach-demo-001 --index-sha256 e7f4214d26f3ec65d263278e9d5a3aae1aab4a1d37bc685f3a1de57ff9fb0b83 --start 40 --end 43 --output runs/response-report-001.json
```

The tool bounds file sizes, rejects linked evidence files, verifies hashes and
strict contracts, and refuses an existing output. Reports omit the bundle's
local filesystem path. Raw recordings, generated bundles, screenshots and
private verification logs remain ignored. See [validation](evidence/landing-response-validation.md).
