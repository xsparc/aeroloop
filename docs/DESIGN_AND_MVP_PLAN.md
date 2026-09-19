# AeroLoop design and MVP plan

Updated: 2026-09-20. Status: MVP implemented; release validation pending.

## Scope

Build a physics-based drone control and learning laboratory with recorded browser
replay. A standalone C++ controller must execute in the physics experiment. PX4
flights are omitted by maintainer decision. Isaac Sim execution and Isaac Lab
training remain required. See [decision 001](architecture/decisions/001-physics-first.md).

## Smallest useful path

First implement runnable CPU checks, a bounded rigid-body simulation, real measured
telemetry, strict export and replay. This is an early research preview. Next validate
an Isaac environment, run one physics experiment, and run a small genuine hover
training/evaluation experiment. Prepare a reusable viewer and a separate website
integration change after inspecting that repository's rules. No production deployment
is implied by implementation or PR creation.

## Physics and controller contract

Use ENU world coordinates, FLU body coordinates, SI units and body-to-world wxyz
quaternions. Test frame conversion and known orientations before control tuning.
Integrate Newton-Euler rigid-body equations with normalized quaternions and bounded
step sizes. Label the CPU actuator as ideal body thrust/moments, not a motor model.
Record mass, inertia, gravity, integration step, initial conditions and force events.

The rate controller uses proportional, bounded integral, derivative-on-measurement
and optional feed-forward terms. Validate finite inputs, sample timing, resets and
saturation-aware anti-windup. The update path uses fixed-size state and no allocation,
I/O or blocking. Invalid control output fails the experiment.

## Scenarios and acceptance

Run hover, a one-metre north position step and an eastward 0.5 m/s²-equivalent force
pulse lasting 0.5 s. Repeat each five times with recorded seeds and initial conditions.
Hover target is 1.5 m; measure a 30 s steady-state window. Initial target: position
RMSE <=0.25 m. Disturbance recovery must return within 0.30 m for two seconds within
five seconds after the pulse. Keep failures in every aggregate denominator.
Characterize baseline targets before comparing controller variants. Record threshold
changes before final comparison runs. Command-loss behavior is a later integration
scenario until an external command transport exists.

Metrics use full-resolution ground truth and time-aligned targets. Missing/timeout
values remain null with reasons. Downsample only for display. Report simulator and
model identity; never equate CPU physics to Isaac or hardware validation.

## Isaac and learning gates

Use a separate compatible Isaac Sim/Isaac Lab environment. Candidate versions are
not tested support. Check actual hardware, driver, memory and headless execution.
No license acceptance, driver/OS changes or paid compute are implicit in this plan.

Use the original primitive body-wrench task described in
[decision 002](architecture/decisions/002-isaac-hover-task.md), initially 32 environments,
without cameras. The pinned Lab 3 release removed the older registered direct task.
Record observation order, normalization, thrust/moment scaling,
physics/control intervals, reset distribution and task revision. Train a hover policy,
save it, reload it in a fresh process and compare against a fixed untrained checkpoint.
Evaluate a fixed held-out set of 20 seeds. Target: >=16 successes with no failure
termination and <=0.30 m target error throughout the final two seconds. Preserve
timeouts and failures. A checkpoint or fixture alone is not training evidence.

## Evidence and viewer

Each recorded experiment includes source commit and dirty state, configuration and
dependency-lock hashes, timestamp, seed, controller/model identity, coordinate/units
metadata, outcomes and checksums. Publish only allowlisted fields. Reject fixtures
from release export. Bound payloads and validate identifiers, timestamps, quaternions
and finite values. Checksums detect changes; they do not authenticate a source.

Replay supports play/pause, scrubbing, speed, event markers and synchronized metrics,
with an accessible static summary and permanent recorded-simulation label. It never
sends commands to a simulator. Prefer an original schematic mesh and no third-party
assets. Integrate a reusable React/Three.js component into the existing website only
after inspecting its current content and deployment rules.

## Release gate

The [post-merge audit](evidence/mvp-audit.md) records the implemented MVP and
reviewed website integration. Its read-only live checks pass. The website's
hosted Actions checks remain blocked by an execution budget; they must run before
release validation can close. A versioned release remains a separate decision.

The MVP requires tested CPU code, actual Isaac physics, genuine training/reload/
held-out evaluation, validated public evidence and a reviewed website preview.
Missing Isaac evidence means partial research preview, not completed MVP.
Production publication is a separate milestone. Physical flight, autopilot integration,
policy transfer into PX4, cloud GPU hosting, vision, swarms and hardware certification
remain outside scope.
