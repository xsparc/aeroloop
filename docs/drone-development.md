# Develop flight control with physics and 3D replay

The drone-development path runs the C++ rate controller inside an actual Isaac
Sim PhysX experiment. A four-rotor X allocator converts collective thrust and
moments into individual commands, applies motor lag and thrust limits, then
applies the resulting wrench to the simulated rigid body. The simulator supplies
the next measured pose and velocity. No trajectory is prescribed or animated
into the physics model. See [the model contract](architecture/decisions/003-rotor-flight-control.md).

Build the native controller and prepare the already documented
[isolated Isaac environment](isaac-next-stage.md). NVIDIA license acceptance
remains an explicit user action. With that acceptance in place, the guarded
development command is:

```sh
python tools/isaac.py flight --scenario all --seeds 73 --output runs/drone-development
```

Use seed 73 while making controller changes. Run the fixed comparison suite after
reviewing each change, from a committed checkout, without tuning against its
results:

```sh
python tools/isaac.py flight --scenario all --seeds 0 1 2 3 4 --output runs/drone-regression
```

This executes five initial conditions for each of hover, north position-step and
east force-pulse. Each trial records 35 seconds at 200 Hz. The command verifies
all run contracts, actuator outputs and full-resolution metrics before returning
success. Failed trials remain in the aggregate; an incomplete worker or missing
trial cannot pass. Reusing an output directory is rejected.

## Open the 3D result

Choose the three run directories for one seed from the printed result or
`result.json`. The directory names begin with `isaac-`. Prepare a new named bundle:

```sh
python tools/replay_demo.py --name drone-review runs/drone-regression/<hover-run> runs/drone-regression/<step-run> runs/drone-regression/<pulse-run>
cd web/replay
npm ci --ignore-scripts
npm run dev
```

Open the printed loopback URL and select **Enable 3D view**. Drag to orbit, scroll
to zoom, or use the keyboard-accessible **Orbit view**, **Top view** and **Side
view** buttons. The gold marker is the target, the gold nose indicates body +X,
the grey line is the measured flight path, and green arrows scale with applied
rotor thrust. Rotor meters show newtons. Scrub or jump to an event to inspect the
controller response. The view is recorded simulation; it does not command a
running simulator. Timing and numerical metrics come from retained physics data.

Use a different `--name` for each export. Preparing a bundle changes the local
demo selection without removing earlier results. Playback starts paused and
stops when hidden or offscreen. The SVG view and text controls remain available
if WebGL cannot initialize. No public hosting is needed for this development loop.

Version 1 CPU recordings still load and retain their CPU label. Version 2 rotor
recordings show **Isaac PhysX** and the four-rotor model. Neither recording type
represents the independently trained hover policy.

## Validation and boundaries

The [measured rotor-control suite](evidence/isaac-rotor-validation.md) passed
15/15 trials at a clean committed revision. Its summary and source/configuration
hashes are retained with the experiment.

Run `python tools/aeroloop test --suite cpu`, the C++ CTest checks and
`npm test` in `web/replay` for changes to math, control or evidence. Run
`npm run test:browser` against a prepared hover/step/pulse bundle for viewer changes.
Generic CI runs CPU tests and CPU recordings; local GPU validation must actually
execute `tools/isaac.py flight`. No passing CPU job substitutes for an Isaac run.

The example drone has ideal ground-truth state, a 1 kg rigid body and declared
actuator parameters. The original version 2 suite starts airborne with motors
initialized at hover thrust and omits aerodynamic drag and ground contact.
Battery discharge, sensor noise, estimation and physical flights remain outside
these experiments. The learned-policy task and its retained evidence are unchanged.

The [turbulence demonstration](turbulence.md) adds version 3 wind-relative drag
and pressure-centre torque, paired with a reference that disables horizontal
position hold. The [ground-contact mission](ground-mission.md) adds version 4
calm takeoff, a waypoint route and measured landing from stopped motors. These
are separate experiments with explicit model contracts and acceptance gates.
The default `--scenario all` continues to run the original three airborne cases.
