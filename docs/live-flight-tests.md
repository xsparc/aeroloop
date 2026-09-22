# Live physics flight tests

The local flight test monitor observes the native controller flying the turbulent
takeoff, waypoint and landing mission in actual Isaac PhysX. It shows measured 3D
pose, wind, tracking error, commanded/measured body rates, rotor thrust, ground
support and simulation timing while the worker is running.

Build the existing native controller and complete the Isaac setup described in
[drone development](drone-development.md). Build the dashboard:

```sh
cd web/replay
npm ci --ignore-scripts --no-audit --no-fund
npm run demo:build
```

From the repository root, start the read-only monitor in one terminal. Its session
directory may not exist yet. Open the printed loopback URL (default port 8771).

```sh
python tools/monitor.py runs/live-flight-001
```

In another terminal, with the Isaac license environment configured, run:

```sh
python tools/isaac.py flight --scenario ground-mission-wind --seeds 73 --physics-dt .0025 --monitor --realtime --output runs/live-flight-001 --timeout 300
```

Each run needs a new output directory. Select **Enable 3D** to follow the aircraft;
orbit, top and side cameras remain available. The viewer sends no flight commands.
Stop the monitor with Ctrl+C when finished. It retains the final session status
while running; refreshing the page does not restart the simulation.

`--physics-dt` accepts `.005`, `.0025` or `.00125` for this mission. Control, wind
and motor updates remain at 200 Hz. World force and body moment are held over each
control interval; contact force is the preceding interval mean. The optional
`--realtime` flag paces against monotonic wall time without dropping simulation
steps. If the host cannot keep up, lag grows and the real-time factor falls below
1. These are soft real-time diagnostics, not hardware timing guarantees.

The live snapshot is replaced every 0.1 simulation seconds. Browser polling may
skip intermediate frames; its chart keeps at most 300 received samples. A quiet
running worker becomes stale after one wall second. Disconnection, startup,
verification, completed validation and failure have distinct labels. The final
label is set by the parent only after validating the retained flight evidence.
`live.json` is local operational state, not public proof of acceptance.

## Fixed-cadence comparison

Run the declared seeds at each physics frequency using the same clean revision:

```sh
python tools/isaac.py flight --scenario ground-mission-wind --seeds 0 1 2 --physics-dt .005 --monitor --realtime --output runs/flight-study-200 --timeout 900
python tools/isaac.py flight --scenario ground-mission-wind --seeds 0 1 2 --physics-dt .0025 --monitor --realtime --output runs/flight-study-400 --timeout 900
python tools/isaac.py flight --scenario ground-mission-wind --seeds 0 1 2 --physics-dt .00125 --monitor --realtime --output runs/flight-study-800 --timeout 900
python tools/flight_study_report.py runs/flight-study-200 runs/flight-study-400 runs/flight-study-800 --output runs/flight-study-summary.json
```

The report verifies all nine recordings, exact wind/control timing, source hashes
and unchanged non-timing configuration before comparing trajectories. Failed
mission or sensitivity gates remain in the report and return exit code 2.
[Decision 008](architecture/decisions/008-live-physics-flight-tests.md) fixes the
acceptance limits. Decision 007's independent yaw-refinement failure remains open;
successful missions do not establish solver convergence. Sensor noise, estimator
delay, calibrated aerodynamics, battery effects and hardware tests remain outside
this slice.
