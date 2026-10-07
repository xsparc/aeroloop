# 024: Diagnose gain and outage response on matched landing intervals

Accepted 2026-10-07 after PR 28, baseline
`cec7e1060f9ab46381fdc222ce6ed336f12323e3`, under the requested ten-feature
implementation and draft PR continuation. AL-027 is one recorded-physics
analysis slice, using all 36 AL-026 flights without changing their outcomes.

## Ten features and acceptance

1. Four-flight, shared-clock 3D playback: fixed/scheduled gains crossed with
   no outage/two-second outages for each of nine seeds.
2. Separate outage response curves and a difference of those differences.
3. Automatically matched pre-contact, armed and post-disarm windows, with
   unavailable phases and truncated recordings explicitly excluded.
4. A 5 ms window editor with interval counts and airborne/contact/disarmed
   exposure, so comparisons cannot silently use different durations.
5. Horizontal translational work and kinetic-energy accounting, separating
   applied wind, realized thrust and unexplained residual.
6. A radial phase portrait showing distance to target and closing velocity.
7. Radial/tangential applied-feedback error decomposition, with the undefined
   direction at the target retained as missing rather than zero.
8. Interval acceleration diagnostics comparing measured velocity change,
   preceding commanded acceleration and preceding applied force.
9. A sortable nine-seed comparison table using the exact same requested window
   for every seed, retaining original mission and outage/recovery outcomes.
10. Digest-bound review links and full-rate CSV/JSON exports with window,
    method, source identity and original acceptance results.

NIST's [factorial example](https://www.itl.nist.gov/div898/handbook/pri/section6/pri615.htm)
distinguishes main and interaction effects and notes the lack of significance
tests when no error degrees of freedom remain. Here we show raw descriptive
contrasts, not fitted coefficients, causal estimates, or confidence intervals.
[PhysX dynamics](https://nvidia-omniverse.github.io/PhysX/physx/5.4.0/docs/RigidBodyDynamics.html)
distinguishes applied forces from contact constraints. Those distinctions
motivate interval accounting; they do not validate this simplified vehicle.

## Numerical contract

Re-use the bounded, hash-verified approach export and its full 42-column landing
rows. Match cohort/seed across both profiles; require matching source identity
within each gain mode, and binary/lock/runtime across all four flights. Retain
historical baseline source identities. Never fetch arbitrary URLs from exports.

The window endpoints are recorded states on the 200 Hz grid. Integrate intervals
`[start,end)` using preceding recorded control/force values and the next state.
All four flights must cover both requested endpoints; otherwise contrasts are
unavailable. Do not shorten the requested window or normalize an incomplete
flight into a complete result. Peaks may include both state endpoints; integrals
and duration never add an interval after the final state.

Pre-contact ends one sample before the earliest first contact among the four
flights. Armed ends one sample before the earliest disarm. Post-disarm begins at
the latest disarm and is unavailable if any disarm is absent. A phase preset
requiring a missing event is unavailable. A normal-force sample >0.1 N at either
endpoint marks a contact-affected interval unless already disarmed at its start.
Otherwise the interval is airborne. These are diagnostic labels, not new gates.

With model mass 1 kg, sum `F_xy(previous) dot delta_position_xy` separately for
wind and realized world thrust. Horizontal kinetic-energy change is the endpoint
difference in `0.5*m*|v_xy|^2`. Residual is that change minus both estimated works.
This is discrete horizontal translational accounting, not total mechanical or
battery energy, and the residual is not measured friction. Contact constraints,
integration and within-step orientation changes may contribute to it.

Measured interval acceleration is `delta_v_xy/dt`; compare it with the preceding
clipped command and `(wind_xy + thrust_xy)/m`. A contact impulse may dominate this
diagnostic. Do not interpret command mismatch as a controller implementation bug.
Radial direction is `(truth_xy-target_xy)/distance`; closing speed is the
negative projection of relative velocity. Applied-feedback position error is
projected onto this radial axis and its counterclockwise tangent. Below 1e-9 m
distance, both projections and closing speed are missing.

For a scalar metric y, fixed outage effect is `y_fixed,outage-y_fixed,intact`;
scheduled effect is analogous. Interaction is scheduled effect minus fixed
effect. Curves of horizontal tracking error and window RMSE contrasts are
separate metrics. Negative error contrasts describe a lower recorded error,
not a pass or general robustness. Both outages (18–20 and 40–42 s) affect each
outage flight, so landing contrasts cannot isolate the second outage causally.

## Scope and verification

Scope: response analysis, browser workspace, reproducible report tool, focused
contract/browser tests, independent arithmetic audit and plan/evidence updates.
No controller, recording, acceptance, simulator dependency or default changes;
no fresh GPU measurement is needed for analysis of these retained flights.
Keep AL-010 open. Before another control experiment, predeclare its hypothesis
and fresh seeds rather than tuning against post-disarm residual alone.

Verify analytic force/work cases, rotated projections, exact window boundaries,
missing/truncated phases, contrast signs, provenance mismatch, corrupt payloads,
stale loads, 3D fallback, all four views, 320 px layout, links and downloads.
Revalidate every actual payload and independently check every derived interval
against the exported numeric rows; preserve the original 12/18 and 15/18 mission
counts. Public reports contain bounded numeric evidence and Git identities only.
