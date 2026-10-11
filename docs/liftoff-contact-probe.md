# Liftoff contact probe

The contact probe inspects the first three seconds of the existing turbulent
flight, including the seed-301 liftoff anomaly. It uses the native controller,
rotor dynamics and Isaac Sim PhysX. It is a short diagnostic capture, with no
mission score and no flight certification. Signed measurements are retained.

## Run and inspect

Use the installed isolated Isaac environment and accepted NVIDIA terms described
in [Isaac setup](isaac-next-stage.md). Run each of the three physics timesteps
with both force modes and repeats 1 and 2, in twelve distinct session directories:

```text
python tools/isaac.py contact --output runs/probe-iteration-1250-r1 --physics-dt .00125 --force-mode per-iteration --repeat 1
python tools/isaac.py contact --output runs/probe-step-1250-r1 --physics-dt .00125 --force-mode per-step --repeat 1
```

Repeat for `.005` and `.0025`, and repeat 2. Each process uses fixed seed 301,
200 Hz control, ideal feedback and the same ground/material model. `per-step`
is deprecated by the installed runtime and is only a diagnostic comparison.
Use a clean committed checkout and do not edit tracked source during capture.
The wrapper requires a complete, validated `result.json`, including after a
worker exits with code zero. Existing output directories cannot be reused.

```text
python tools/contact_probe.py --sessions <all twelve session directories> --output web/replay/public/probe-demo-001
```

Create the ignored `web/replay/public/probe-config.json` with `baseUrl` set to
`/probe-demo-001/` and `indexSha256` set to the export's digest. Build the replay
demo with `npm run demo:build` in `web/replay` and serve it on loopback. Open
`/probe.html`. Choose a matrix cell, click a signed-normal incident and enable
3D. The collider, raw contact points and separate friction anchors follow the
same recorded cursor as the force, momentum and clearance plots.

Use **Fit reported contacts** to include anomalous points far from the vehicle;
**Aircraft view** returns to the collider. The contact table computes Euclidean
distance outside the oriented 0.4 by 0.4 by 0.1 m box. It is a geometric diagnostic,
not a new contact rejection threshold. Pink marks downward vertical impulses.
Dashed connectors help locate reports more than 1 cm outside the collider; they
are display guides, not force vectors or physical connections.

## Measurement contract

Rows describe the preceding physics interval, (t-dt,t]. Sensor values are N.
Detailed normal and friction buffers are read with dt=1 to retain N·s. Normal
impulse is scalar impulse times geometric normal, summed over contacts. Friction
is summed over anchors; anchors need not correspond one-to-one with contacts.
All backend arrays are copied before the next buffer query. Capacity saturation
rejects a capture. Negative impulses are diagnostic data, not clipped values.

Momentum uses measured velocity change, mass, gravity, world thrust plus wind,
and the reconstructed impulses. API differences and repeated-run differences
are descriptive; they do not introduce new flight acceptance gates. The UI uses
the oriented cuboid's bottom for clearance. Arrows have a labeled display scale
and cap; contact dots are enlarged. Rendering is a replay of recorded physics.

CSV exports endpoints within (start,end]. JSON exports preserve the full probe,
selected window, source revision and digests. Links restore only when bound to
the current index digest. The browser verifies hashes, schema, cadence, fixed
configuration, summary arithmetic and provenance before displaying a capture.
The exporter requires exactly the declared twelve-case matrix and shared source,
runtime and controller binary. Raw runs and machine logs stay ignored.

No calibrated airframe, angular balance, contact-point energy or numerical
convergence claim. A sensor/raw-buffer agreement identifies reporting agreement;
it does not independently prove the solver's physical validity. Original full
flight gates and the unresolved AL-010 yaw refinement remain unchanged.
