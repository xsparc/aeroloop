# Takeoff and landing in turbulent wind

`ground-mission-wind` combines the physical floor and route of the calm mission
with seeded wind-relative drag. Isaac PhysX integrates the native controller's
four lagged rotor forces through takeoff, four waypoint holds and contact landing.
Wind stays active throughout the 50 s run, including after motor shutdown. A
40–42 s gust challenges the descent.

Prepare the [isolated Isaac environment](isaac-next-stage.md), accept NVIDIA's
terms and build the native controller first. Use seed 73 for development. Freeze
the source and gains before the final five-seed suite:

```sh
python tools/isaac.py flight --scenario ground-mission-wind --seeds 73 --output runs/wind-mission-development
python tools/isaac.py flight --scenario ground-mission-wind --seeds 0 1 2 3 4 --output runs/wind-mission-regression
python tools/mission_report.py runs/wind-mission-regression --scenario ground-mission-wind --output runs/wind-mission-summary.json
```

Always choose new output directories. The report requires seeds 0 through 4 from
one clean source revision, retains failed trials and emits allowlisted fields.
Full-rate verification reconstructs the seeded wind, drag, trajectory feedforward,
bounded horizontal integral feedback, rotor commands, contact latch and metrics.
The controller receives pose and velocity, without direct wind compensation.

Prepare a replay using the run identifier in `result.json`:

```sh
python tools/replay_demo.py --name wind-mission-review runs/wind-mission-regression/<mission-run>
cd web/replay
npm run dev
```

Select **Enable 3D view**. The white box shows the collider, gold marks the
commanded route, green arrows show rotor thrust, violet shows wind, orange shows
drag and pink shows normal ground support. Scrub to 41 s for the descent gust and
49 s for the resting drone with stopped motors and continuing wind. The camera
frames the route and ground. No simulator runs in the browser.

The waypoint acceptance band is 0.35 m for this scenario; the calm mission retains
its 0.15 m band. Landing speed uses the sample before first contact. Ground-support
validation includes the preceding interval's applied vertical drag and thrust,
because the normal force alone need not equal weight in wind. Contact excludes
friction in the reported normal-force vector.

[Decision 006](architecture/decisions/006-turbulent-contact-mission.md) fixes the
model and gates; [validation](evidence/isaac-wind-mission-validation.md) records
measured results. The temporal OU wind is not a validated atmospheric spectrum.
Perfect state, illustrative cuboid contact and friction, and simplified drag omit
sensor delay, ground effect, propeller aerodynamics and battery behaviour. This
experiment does not evaluate a learned policy or establish physical-flight safety.
