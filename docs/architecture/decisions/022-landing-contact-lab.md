# 022: Inspect horizontal landing and disarm behavior

Accepted 2026-10-06 after PR 25, baseline
`3d9ed48f706509cc1cc896b7f5aeea0535b879a1`.

AL-025 implements the requested ten new features as one landing contact lab:

1. A failure queue filtered by cohort/outcome and ranked by support-position error.
2. A horizontal landing map with truth, feedback, home boundary and velocity vector.
3. Paired 3D landing playback with a shared 5 ms cursor and contact/disarm jumps.
4. Horizontal P, D, integral, feedforward and clipped-demand inspection on both axes.
5. Four-rotor lag, world thrust direction, tilt and yaw inspection.
6. An interval-correct horizontal momentum budget with an explicit inferred residual.
7. A contact episode ledger separating normal contact from continuous eligibility.
8. Approach, contact-to-disarm and disarmed displacement/energy/impulse summaries.
9. An adjustable offline readiness audit using position, speed, tilt and dwell.
10. Evidence-bound selection links and an export carrying full-rate rows, audit
    settings, original outcomes, provenance and descriptive summaries.

Reconstruct all 24 retained AL-024 flights before export, preserving all gates,
same-mode pair/recovery failures and historical source identities. This analysis
does not change physics, control, sensor settings, defaults or acceptance. There
are no new flights, dependency changes or claims of improved robustness. AL-010
remains open. Implementation touches analysis/export tools, replay UI, focused
tests and project documentation; it does not alter capture or control paths.

The [PhysX dynamics documentation](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/docs/RigidBodyDynamics.html)
describes forces and contact constraints as contributors to velocity changes.
The recorded normal force does not separately measure tangential friction.
For the fixed 1 kg model, compute residual impulse on (t-dt,t] as
`mass * (v[t]-v[t-dt]) - dt * (world_thrust[t-dt] + wind[t-dt])`.
This includes unrecorded contact/solver effects and numerical error. It is not a
friction sensor or proof of causation. Force at t drives the next interval.

Use every recorded sample from 34 s through the last available state. Controller
terms use the applied horizontal feedback and recorded integral, with zero terms
after disarm. The horizontal map's 0.35 m circle is the original final-support
position limit; applying it earlier is diagnostic. Event speed at the contact
sample differs from the existing touchdown-speed gate, which uses the preceding
sample. Preserve both meanings.

Phase state endpoints are inclusive; impulses integrate (start,end], so adjoining
phase intervals never double count. Missing events produce incomplete or absent
windows, not zero-valued passes. Contact episodes are maximal consecutive samples
with normal force >0.1 N; duration is last minus first observed sample time. A
terminal episode is right-censored. Eligibility is the existing vertical/contact
predicate, and its dwell resets on every ineligible sample.

The [PX4 land detector](https://docs.px4.io/main/en/advanced_config/land_detector)
motivates inspecting motion and dwell separately. This project does not implement
that detector. Offline readiness uses recorded truth through the actual disarm
sample only. A first qualifying time means the predicate occurred on that recorded
trajectory; it does not predict a different landing or validate a new supervisor.
Default exploratory bounds are 0.35 m, 0.2 m/s, 3 degrees and 0.05 s continuous
dwell. They do not replace acceptance or issue motor commands.

Validate force timing using independent arithmetic and manufactured motion;
exercise interrupted/terminal contacts, missing events, empty/short recordings,
tampered payloads and out-of-range audit settings. Verify all real payloads in
both languages, paired 3D, export, selection restore, failure filters, playback
and a 320 px layout. Bound same-origin loads and JSON sizes; export allowlisted
numeric fields only, with no host paths or logs. Keep readiness settings in the
URL fragment and exported report; data loading never follows user-provided URLs.
