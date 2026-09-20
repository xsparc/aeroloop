# Rotor flight-control validation

Measured 2026-09-20 at committed revision
`52f8bae2dd760d50e40e86093d78bd91d618a71e`. Every final trial records
`source_dirty: false` and the same implementation, native controller and lock
hashes. This extends the earlier ideal-wrench experiments with a four-rotor
actuator; it does not change or retrain the learned hover policy.

The C++ rate controller executed in a feedback loop with Isaac Sim 6.1.0.0
PhysX through the pinned Isaac Lab 3 environment. Each body pose came from
the simulator. The four rotor forces, moment arms, reaction torques, thrust
limits and motor lag follow [decision 003](../architecture/decisions/003-rotor-flight-control.md).
Body gyroscopic forces were explicitly enabled. World/body frame conversion,
configured inertia and per-interval actuator telemetry were retained.

## Executed trials

The development seed 73 passed hover, step and pulse before the final suite.
The final configuration explicitly records the gyroscopic-force setting and
uses the unchanged control gains. A separate run then executed seeds 0 through
4 for each scenario, with no gain or threshold changes based on those results:

| Scenario | Passed | Measured result |
|---|---:|---|
| Hover | 5/5 | Steady-window position RMSE 0.000446 to 0.000465 m |
| One-metre north step | 5/5 | Settled inside 0.02 m for two seconds at 3.105 s after the step |
| East force pulse | 5/5 | Maximum position error 0.086344 m; remained inside the 0.30 m recovery band |

Each trial retained 7,001 samples across 35 seconds at 200 Hz. All fifteen trials
completed in 321.44 s wall time on the previously measured local GPU environment.
This timing includes setup and is not a hardware performance benchmark.

Zero reported pulse recovery time means the response never left the specified
band, not instantaneous disturbance rejection. The mild scenarios required at
most 2.748 N from an individual rotor, below its 5 N limit. They did not saturate
the allocator; saturation behavior is covered by the dedicated mixer tests.

The guarded command returned zero after verifying every recording and the
complete requested trial set. The [public summary](isaac-rotor-001.json) was then
constructed by rereading all fifteen raw recordings, recomputing their actuator
outputs and metrics, and checking their manifest hashes and aggregate outcomes.
It retains every trial. Raw samples, logs and execution directories remain local.

## Software and visualization checks

- 49 Python tests passed, including rotor geometry, moment signs, mixing,
  collective-preserving desaturation, motor step response, invalid inputs,
  forged actuator telemetry, backend relabeling and incomplete-worker rejection.
- Both native CTest checks passed. The C++ controller source and gains are unchanged.
- Three legacy replay tests and six reusable-viewer unit/contract checks passed.
- All six browser checks passed with actual Isaac seed-zero recordings and again
  with the retained version 1 CPU recordings. They cover integrity rejection,
  selected-run loading, keyboard scrubbing, camera presets, rotor meters, WebGL
  fallback, responsive layout, offscreen pause and renderer disposal.
- The local 3D output was inspected with actual recorded attitude, an X rotor
  layout, trajectory, target and thrust arrows. The standalone production build
  passed. Its optional Three.js chunk remains lazy-loaded; the bundler reports
  a size advisory for that chunk.

The first development browser check exposed a Vite reload when OrbitControls
was first imported. Explicitly prebundling that dependency fixed the reload;
the complete browser suites above passed after the correction.

## Boundary

These are airborne, ground-truth-state experiments with declared example rotor
parameters. There is no aerodynamic, battery, estimator, ground-contact or
physical-flight validation. The simulation controls the drone state; the browser
only replays those measurements. CPU, native Isaac control and the learned hover
policy remain distinct evidence families. See the [development workflow](../drone-development.md)
to rerun the physics and open the local 3D view.
