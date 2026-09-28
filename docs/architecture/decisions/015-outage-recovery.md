# 015: Measure longer capture outages and sustained recovery

Accepted 2026-09-28 after PR 18; baseline
`5b5802d0d5c8b89254724bd0cb379f6b6728c499`.

AL-018 measures the existing controller's outage response. Keep the pinned
runtime, native gains, 200 Hz physics/control, rotors, wind and mission gates.
Use 50 Hz position/velocity captures throughout so that a same-seed `sample-hold`
reference isolates missing captures from cadence. Compare `hold-dropout` (250 ms),
`hold-dropout-500ms`, `hold-dropout-1000ms` and `hold-dropout-2000ms`.
Each profile suppresses scheduled captures over [18,18+duration) and
[40,40+duration) simulation seconds. Hold the last successful capture, with no
catch-up delivery, noise, delay, extrapolation or controller mitigation.

Freeze this matrix before development seed 73 and final seeds 0/1/2. Execute
all fifteen final flights from one clean revision, with monitoring and wall
pacing enabled for all. Preserve each failure and incomplete recording. Require
10001 samples for a complete trial, but do not require every stress case to pass
to deliver the study. Infrastructure failure or missing data is not a controller
result. Fresh sample-hold and 250 ms traces must exactly reproduce AL-017.

Report the unchanged mission gates and paired bounds (0.15 m peak position
difference, 0.05 m absolute RMSE change, 0.5 s landed-time change). Keep these
separate from recovery. For each window, inspect truth separation from the
same-seed reference through the next outage start, or recording end. Report
peak separation, samples above 0.05 m, separation at capture restoration and
actual feedback age. Recovery is the start of the **final uninterrupted suffix**
at or below 0.05 m after the outage end. Require at least one full second of
samples in that suffix and a start no later than five seconds after the outage.
A transient return followed by a later excursion does not count as settled.
Missing complete dwell evidence fails. Distinguish never leaving the band from
an exercised return after an excursion; preserve late or absent recovery.

Summarize every duration across all three seeds, with mission, pair and recovery
outcomes. Do not extrapolate a safe duration between tested points or assume
monotonicity. Study delivery means verified measurements and explicit outcomes,
not universal robustness acceptance. If no case leaves the band, record that
limitation without enlarging the frozen matrix. No tuning on final seeds.

Extend the existing strict version-seven recording/version-three live profile
allowlists; the data shape is unchanged. Preserve AL-017 profiles and report
semantics. Live 3D continues to show physics truth, with profile-specific outage
windows and capture age. Inspect a fresh longer-outage flight, and generate a
full-rate comparison figure. Recorded timing replay remains deferred.

Acceptance covers integer capture boundaries, full held-feedback reconstruction,
wrong-profile rejection, recovery re-excursion and truncation, complete study
identity, preserved failing gates, public allowlisting and browser monitoring.
Keep raw traces/logs/figures private. Attitude/rates/acceleration and mission/contact
supervision remain ideal; AL-010 yaw refinement remains open. These synthetic
outages characterize this model only, not a hardware link or stability proof.

Isaac Lab documents independent [sensor update periods](https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.sensors.html#sensor-base).
The explicit sample-and-hold model retains that timing separation while allowing
CPU verification. Outage durations are declared stress choices, not calibrated
sensor values. Controller changes, estimation and runtime mitigation are deferred
until the fixed measurements identify a concrete need.
