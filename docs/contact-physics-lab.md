# Contact physics lab

The contact lab measures filtered ground friction in fresh Isaac PhysX flights,
then compares impulse balance, translational work and original mission outcomes.
Its ten features are defined in [ADR 025](architecture/decisions/025-contact-friction-audit.md).
This remains a simulation-only evaluation; scheduled gains are opt-in.

## Capture

Use the already configured isolated Isaac environment. Commit clean source first
and keep it unchanged until every worker completes. A representative fixed-gain
case is:

```sh
python tools/isaac.py flight --output runs/fixed-intact --scenario ground-mission-wind --seeds 1 401 709 1009 --observation-profile sample-hold --predictive-feedback --vertical-decay --fresh-axis horizontal --channel-quality noise-delay --contact-forces --monitor
```

Run a separate `runs/fixed-outage` session with profile `hold-dropout-2000ms` and
`--realtime`. Repeat both profiles into `runs/scheduled-intact` and
`runs/scheduled-outage` with `--approach-gains`. Exit 2 retains valid failed mission
results; exit 1 means the worker or evidence verification did not complete.
Do not drop failed cases from the comparison.

The ideal-feedback numerical sensitivity sweep omits observation/predictor/gain
flags, keeps seed 301, and uses `--physics-dt .005`, `.0025` and `.00125` in three
new sessions. Control remains 200 Hz. Use `--contact-forces --monitor` on each.
These runs characterize numerical sensitivity, not material/airframe calibration.
The excluded development seed is 83.

GPU filtering requires a rigid-body partner in this setup. Opt-in capture uses a
stationary kinematic ground cuboid; its geometry, pose and friction material match
the original static collider. Each sidecar records `ground_kind` explicitly.
Default unfiltered simulations keep their existing ground. Capture checks filtered
normal against aggregate normal and fails on a 64-anchor buffer saturation.

## Export and replay

```sh
python tools/friction_study.py --sessions runs/fixed-intact runs/fixed-outage runs/scheduled-intact runs/scheduled-outage runs/sweep-5000 runs/sweep-2500 --rejected-sessions runs/sweep-1250 --output web/replay/public/friction-demo
```

For the measured seed 301 protocol, the 1.25 ms session is a rejected capture.
`--rejected-sessions` admits only this hash-intact negative-normal rejection and
shows it separately; it never certifies a rejected recording. For an independently
verified sweep, place all completed sessions in `--sessions` instead.

The exporter reconstructs original flight evidence, validates sidecar hashes,
source/runtime identity, force coverage and interval cadence, then prints the
index digest. Existing output is rejected. Raw sessions and the generated bundle
remain ignored. Keep final cohorts separate from development sessions.

Create ignored `web/replay/public/friction-config.json` using that digest:

```json
{"baseUrl":"/friction-demo/","indexSha256":"<index_sha256 from the exporter>"}
```

Run `npm --prefix web/replay run dev -- --port 8800 --strictPort` and open
`http://127.0.0.1:8800/friction.html`. Select a case, set a 5 ms-aligned window,
enable 3D and inspect the force/impulse/work plots. The experiment table always
uses the full 50 s flight; detailed statistics use the selected interval.
The 3D drone and arrows are schematic; vector magnitude caps are stated onscreen.
Original mission failures stay visible.

JSON review downloads retain full traces, unchanged gates, source/runtime identity,
index/case/raw-capture hashes and selected-window metrics. CSV contains measured
interval endpoints `(start,end]`, not an invented interval after the terminal
state. Review links bind case, window and cursor to the exact index digest.

## Live contact monitor

```sh
python tools/monitor.py runs/fixed-intact --port 8801
```

Open `http://127.0.0.1:8801/friction-live.html` while its instrumented worker runs.
It polls the bounded `/api/contact` endpoint and shows force vectors, seed,
simulation time, age and anchor count. Data older than one second is stale,
including completed runs; the main flight monitor distinguishes verified mission
completion/failure. The server serves only explicit assets and validated telemetry
on loopback, rejects cross-origin requests, arbitrary paths and writes, and strips
the private monotonic clock from replies.

## Read the measurements

A force row at t belongs to the preceding 5 ms control interval. The initial row
contains no force interval. Normal/friction forces and applied world force are
averaged across all physics substeps. Three-axis momentum residual is measured
momentum change minus integrated applied, contact and gravity forces.

Horizontal work is mean force dotted with COM displacement. Kinetic change minus
wind, thrust and friction work is a discrete residual; rotational/contact-point
work is not measured. COM friction alignment uses midpoint velocity and omits
speeds below .01 m/s or forces below 1 micro-newton. Friction/normal ratios omit
normal force at or below .1 N. The .5 dynamic and .7 static material coefficients
are references, not new flight gates or calibrated friction estimates.

These small synthetic cohorts retain simplified aerodynamics, ideal attitude and
contact supervision. Neither exact repeatability nor small impulse residuals
establish real-airframe fidelity. AL-010 yaw refinement stays open.
