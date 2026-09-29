# 017: Capture-aware landing commands and unseen-seed evaluation

Accepted 2026-09-29 after PR 20, baseline
`141e3a998592042d2f8d68fd85ca4d842e726f21`.

AL-020 adds an opt-in landing command guard on top of the unchanged AL-019
predictor. During the landing phase, capture age of at least 0.6 s activates a
hold command at the greater of 0.30 m or the scheduled command altitude. This
threshold leaves the retained no-outage/250/500 ms behavior unchanged. The guard
does not read current truth position/velocity, wind, contact force or future data.
It receives the existing mission phase, scheduled target, and raw captures.

After captures resume with age below 20 ms, require captured horizontal distance
to home at most 0.20 m and horizontal speed at most 0.20 m/s continuously for
0.30 s. Reset that dwell whenever freshness or either condition fails. Then
command a four-second quintic descent from the hold altitude to -0.03 m, with
analytic velocity/acceleration feedforward. A renewed 0.6 s age returns to hold.
The existing contact supervisor retains disarm authority; the guard never rearms
a landed vehicle. No deadline extension or recovery teleport is permitted.

Record the guard's command and state separately in version-nine evidence. The
sample's original `target_m` stays the scheduled mission target: all existing
tracking, contact, touchdown, final-support, paired and sustained-recovery gates
remain unchanged. Thus delaying descent can still fail timing or trajectory
comparisons even when touchdown improves. CPU validation reconstructs guard
transitions and actual controller commands, including feedforward. Older schemas
and the predictor remain unchanged. The guard stays opt-in.

The [PX4 position-estimation guidance](https://docs.px4.io/main/en/config/safety#position-estimation-failsafes)
distinguishes data timeout, estimate validity and available fallback modes. It
does not validate this guard: predicted altitude/position can be wrong during an
outage. This is a simulation experiment, not a hardware failsafe or PX4 flight.

Freeze these parameters before development seed 73 at two seconds. Then capture
one clean revision with no final-matrix tuning:

- Regression seeds 0/1/2: no outage, 500 ms, one second and two seconds, guard on;
  compare with retained AL-019 predictor-only recordings (twelve fresh flights).
- Previously unused seeds 101/202/303: no outage and two seconds, predictor-only
  and guarded (twelve fresh flights). Do not inspect those wind traces beforehand.
- Monitor every flight. Pace both unseen two-second cohorts; other fresh flights
  may run faster than wall time at the same fixed 200 Hz physics/control cadence.
  Report timing separately. Match runtime/native controller/lock and configuration
  except the explicit guard flag; require coherent provenance within each cohort.
- Require exact inactive-guard traces after removing only guard state, including
  regression no-outage/500 ms and unseen no-outage. Require all regression samples
  before activation to match the retained predictor.

Preserve all failed/incomplete outcomes. Report per-seed mission gates, original
target errors, touchdown velocities, guard transitions, time to stable captures,
same-controller no-outage differences and unchanged recovery windows. Keep
regression and unseen cohorts separate. No aggregate score may hide either.
Study delivery does not require every stress case to pass.

Extend the working paired demo with guarded commands, activation/resumption
chapters and explicit cohort selection. Retain bounded checksummed same-origin
loading, stale-load cancellation, keyboard controls, reduced-motion/visibility
behavior and numeric/trajectory fallback. Show scheduled targets separately from
guard commands; keep full-rate acceptance separate from display samples.

Validate boundary activation, interrupted capture dwell, quintic derivatives,
repeated outages, disarm precedence, strict evidence reconstruction, untouched
legacy schemas, failed/incomplete export, actual GPU flights and measured paired
3D playback. Keep AL-010 yaw refinement open; no solver or learning-policy change.
