# 016: Bounded predictive feedback and a repeatable 3D demo

Accepted 2026-09-29 after PR 19, baseline
`1e0d65130bfb313da2b9b8ec09e29874dc7a734b`.

AL-019 adds an opt-in model predictor ahead of the unchanged trajectory/rate
controllers. Its only translational inputs are successful position/velocity
captures and previous applied rotor thrust. Previous measured attitude rotates
thrust into world coordinates; subtract gravity and integrate at 200 Hz with
constant-acceleration position integration. It does not receive current truth
position/velocity, wind, external forces, future samples or mission targets.

At consecutive 20 ms captures, estimate disturbance acceleration from the
velocity innovation minus integrated thrust/gravity, low-pass with a 0.2 s time
constant and clamp each axis to ±4 m/s². Hold that estimate across missing
captures; do not update it from the first post-outage velocity jump. Reset
position/velocity to each successful capture. Return the original held capture
while age is below 20 ms, preserving the no-outage trajectory exactly. Use the
prediction from 20 ms through 2.1 s; beyond that explicit horizon return held
feedback and mark it expired. These constants are frozen before measurements.

Keep raw captures separate from predictive feedback in version-eight recordings.
CPU verification reconstructs the predictor from prior samples and validates
every resulting controller setpoint. Older recordings remain unchanged. The
method is a declared model observer with ideal attitude and known actuator
output, not an IMU simulation, EKF, calibrated estimator or hardware failsafe.
PX4's [estimator documentation](https://docs.px4.io/main/en/advanced_config/tuning_the_ecl_ekf)
supports the general use of propagation between observations; it does not validate
this simpler model or authorize PX4 execution.

Run development seed 73 with the 2-second profile. Then freeze one clean source
revision and run the existing five-profile/three-seed matrix with prediction,
monitoring and pacing. Seeds 0/1/2 are explicit regression cases, not unseen
validation. Compare with all retained AL-018 recordings after full verification,
matching runtime, gains, wind, cadence, configuration and native binary. Source
revisions intentionally differ; each cohort must be internally consistent.
No tuning against the final matrix. Require exact no-outage state/control
reproduction after removing only the new feedback field.

Preserve original mission gates and existing 50 mm/one-second/five-second recovery
criterion against the no-outage reference. Report each old/new mission outcome,
tracking error, touchdown speed, landed time, peak reference separation and
recovery windows. Preserve regressions, incomplete runs and failed bounds. Study
delivery does not imply all stress gates pass or authorize default enablement.

Deliver a working local recorded demo: five outage choices, three seeds,
synchronized baseline/candidate 3D, play/pause/speed/scrubbing, outage and landing
chapters, explicit raw age/predictive state, and full-rate outcomes. CPU export
verifies raw evidence first; a pinned same-origin index binds bounded pair files.
Display data are sampled, not used for acceptance. Preserve outage boundaries,
mission events and endpoints. Fail closed on bad hashes or contracts; cancel
stale loads, respect reduced motion and pause hidden/offscreen playback. Retain
a numeric/trajectory fallback without WebGL. Export no host metadata or raw logs.

Validate analytic propagation, fresh/reset/expiry behavior, corruption rejection,
baseline continuity, reporting of failures, browser controls/integrity and actual
measured 3D playback. Keep AL-010 yaw refinement open and the runtime pinned.
