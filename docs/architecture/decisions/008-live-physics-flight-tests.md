# 008: Live monitoring and fixed-cadence physics flight tests

Accepted 2026-09-22 for the requested simulation and real-time monitoring work.
Baseline: `1e762cb35fdecd40bf450aaa95ddcd828a80eee0`.

## Scope and timing

Run the existing turbulent takeoff, waypoint and contact-landing mission with
the native rate controller, four lagged rotors and PhysX. Keep control, motor
updates, wind generation and recorded state at 200 Hz. Integrate each held
input with one, two or four PhysX steps (200/400/800 Hz). Rotor thrust and body
moment are held over the control interval. The sampled external world force
is held in world coordinates, transformed at each substep; its sampled body
moment is held in body coordinates. Contact normal force is averaged over the
preceding control interval, preserving its integrated impulse.

The 200 Hz baseline remains byte-compatible in configuration with earlier flight
recordings. Substepped recordings explicitly identify their physics timestep,
input hold and contact averaging in `physics_options`. No controller tuning,
force-mode switch, contact-margin change, sensor noise or training is included.
This is a timestep sensitivity study, not a proof of numerical convergence.
Decision 007's default yaw-refinement failure remains open.

## Live boundary

A worker may atomically replace a bounded, allowlisted local snapshot at 10 Hz
of simulation time. A separate loopback-only server exposes only that snapshot
and built monitor assets. The dashboard polls at most four times per second,
shows measured 3D pose, errors, wind, rotor effort, support and wall-clock speed,
and labels samples provisional until the parent validates completed recordings.
There is no browser command channel, arbitrary file serving or external service.
Slow clients cannot queue work in the control loop. Atomic local file writes do
add measurable overhead; monitoring is optional.

Optional wall-clock pacing uses a monotonic clock, never changes the integration
step and never skips control updates. A slow host falls behind and reports lag.
This is soft real-time observation, not a hard real-time controller guarantee.
The monitor marks running data stale after one second without a fresh worker
snapshot; network loss, failed validation and completed sessions are distinct.

## Acceptance fixed before GPU measurements

- Development seed 73; final seeds 0, 1, 2 at all three physics frequencies.
  Preserve every failed result. Do not tune gates against final trials.
- Every final trial must satisfy decision 006's unchanged mission gates and
  contain 10,001 control samples. Initial conditions, wind sequences, controller,
  source and all non-timing configuration must match within each seed.
- For each seed, compare 400 and 800 Hz to 200 Hz at identical control timestamps.
  Record position/attitude differences, RMSE change and landing-time change.
  Bounded sensitivity requires peak position difference <= 0.15 m, position
  RMSE change <= 0.05 m and landed-time change <= 0.5 s. Failure is retained and
  keeps numerical acceptance open; monotonic refinement is not asserted.
- A live GPU session must show advancing measured samples and 3D pose before
  completion. Browser tests cover stale data, malformed data, loss/reconnection,
  failed and verified completion, bounded history and resource cleanup.
- HTTP tests reject unexpected Host/Origin, non-allowlisted paths, writes and
  symlinks; responses prohibit framing/cross-origin access and disable caching.
- Report measured real-time factor and lag without requiring every frequency
  to achieve 1x on the available GPU. Full evidence verification remains separate
  from the lossy live view. Tests, privacy and evidence gates must pass.

## Basis and limits

Isaac Lab distinguishes control/action cadence from physics decimation in its
[direct environment tutorial](https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/create_direct_rl_env.html).
The monitor uses elapsed monotonic time, consistent with the semantics described
for [browser performance timing](https://developer.mozilla.org/en-US/docs/Web/API/Performance/now).
Existing temporal wind, perfect state, illustrative contact/drag and actuator
models remain limitations. Live rendering does not constitute a sensor model,
physical calibration, learned-policy validation or hardware-flight evidence.
