# Takeoff, waypoint flight and contact landing

`ground-mission` runs the native C++ controller and lagged rotors in actual Isaac
PhysX. The drone starts with stopped motors on a ground collider, climbs to 1.5 m,
visits (0,1,1.5) and (1,1,1.5), returns home and lands. Coordinates are ENU metres.
The 50 s recording includes measured ground support and a contact-latched motor
shutdown. All motion comes from integrated forces and torques.

Use the existing [Isaac setup](isaac-next-stage.md) and build the native controller
first. After accepting NVIDIA's terms, develop with seed 73:

```sh
python tools/isaac.py flight --scenario ground-mission --seeds 73 --output runs/mission-development
```

Freeze the implementation before executing the fixed five-seed suite. Each seed
changes the initial XY offset within ±0.02 m; the route and all gains stay fixed.

```sh
python tools/isaac.py flight --scenario ground-mission --seeds 0 1 2 3 4 --output runs/mission-regression
python tools/mission_report.py runs/mission-regression --output runs/mission-summary.json
```

The guard verifies every full-rate sample and requires all requested runs.
The report requires all five seeds from the same clean source and configuration,
retains failures and emits only public fields. Raw logs and local paths stay ignored.
Choose new output names; existing measurements are never overwritten.

Use the run identifier in `result.json` to prepare the interactive replay:

```sh
python tools/replay_demo.py --name mission-review runs/mission-regression/<mission-run>
cd web/replay
npm run dev
```

Select **Enable 3D view**. The white box is the actual 0.4 × 0.4 × 0.1 m body
collider; the rotor mesh is schematic. The gold route connects commanded waypoints,
the grey path is measured motion, green arrows show rotor thrust and pink shows
measured normal ground support. The small pad is a visual landing marker on the
larger physical floor. Jump to liftoff, touchdown or landed, or scrub to compare
flight with the motor-off resting state. The camera frames both ground and route.

Normal force excludes friction. Clearance is the lowest oriented collider point
above z=0, not COM height. Contact fields and phase hold their most recent measured
sample during display interpolation; all metrics use the original 200 Hz data.
Touchdown speed is taken from the sample immediately before the first landing
contact, avoiding the misleading zero velocity after impact. A landed phase needs
continuous measured support, proximity and low vertical speed before disarming.

[Decision 005](architecture/decisions/005-ground-contact-mission.md) fixes the
timing, geometry and acceptance limits. [Validation](evidence/isaac-mission-validation.md)
records execution evidence. This calm, perfect-state example uses illustrative
contact parameters and omits propeller aerodynamics, ground effect, battery and
hardware. The [wind demonstration](turbulence.md) remains a separate airborne
experiment; it does not establish this route's performance in turbulence.
