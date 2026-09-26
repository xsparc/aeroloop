# Physics accuracy validation

AL-010 follows [decision 007](../architecture/decisions/007-physics-accuracy-suite.md).
The final clean-source matrix passed **36/36 individual accuracy cases**, but
**overall refinement acceptance is false**: default TGS yaw error did not shrink
consistently with timestep. The [public summary](isaac-physics-001.json) preserves
this failure, all per-case measurements and both integration modes. AL-010 remains
in progress until the default refinement finding is resolved or independently
explained under a reviewed numerical criterion. No complete acceptance is claimed.

The matrix ran actual Isaac PhysX at implementation commit
`62f63e463a925e4d50aef7ca6a2699e241fabbab`, with 14,876 full-rate samples.
Summed worker wall time was 52.183 s, excluding process startup/shutdown outside
the worker. Isaac Sim 6.1.0.0, Isaac Lab distribution 17.0.2 and Torch 2.11.0+cu128
were used. All six workers retained matching clean-source and lock hashes. The
report independently revalidated traces and exited 2 because refinement failed;
this is a measured rejection, not an incomplete execution. No final-result tuning
or acceptance-threshold relaxation occurred.

Peak errors below are millimetres for position and milliradians for yaw angle.
Each case independently passed its absolute position, velocity, attitude and rate
bounds; refinement compares error after each halving of the timestep.

| Force mode | Case | 200 Hz | 400 Hz | 800 Hz | Refinement |
| --- | --- | ---: | ---: | ---: | --- |
| per-iteration | free-fall | 1.531904 | 0.765984 | 0.384634 | Passed |
| per-iteration | tilted-thrust | 0.884619 | 0.442502 | 0.221771 | Passed |
| per-iteration | yaw-torque | 0.242522 | 0.011929 | 0.216567 | **Failed** |
| per-iteration | rotor-step | 8.102645 | 4.096974 | 2.060522 | Passed |
| per-iteration | drag-coast | 1.842200 | 0.899016 | 0.463187 | Passed |
| per-step | free-fall | 6.129210 | 3.064339 | 1.532023 | Passed |
| per-step | tilted-thrust | 3.538620 | 1.769256 | 0.884589 | Passed |
| per-step | yaw-torque | 1.181065 | 0.481576 | 0.021107 | Passed |
| per-step | rotor-step | 8.716096 | 4.390825 | 2.203215 | Passed |
| per-step | drag-coast | 4.359901 | 2.177894 | 1.088798 | Passed |

The per-step option is a deprecated PhysX diagnostic. Its finer-step yaw error is
smaller, but its coarse-step errors are larger. The default per-iteration force
mode remains unchanged in flight scenes and in the audit command. The observed
yaw discrepancy is in recorded orientation; the default rate error stayed below
0.000006 rad/s. Its root cause has not been isolated. Do not recommend the
deprecated option or a different mission timestep from this diagnostic alone.

Default-mode floor penetration was 1.818799, 0.442999 and 0.003131 mm at
200/400/800 Hz, below the unchanged 3 mm gate. First measured support occurred at
0.320 s, within 0.000671 s of the ideal drop time. Across both modes the largest
vertical impulse/momentum residual was 0.000000530 Ns. Every resting window
passed height, speed and normal-support checks. No drop gained mechanical energy
above its initial value and every drag-coast case dissipated kinetic energy.
Contact peak force is deliberately not treated as timestep-independent.

Development retained two failed 200 Hz drops: the original 1 mm contact offsets
produced 4.061117 mm penetration, and enabling speculative CCD produced identical
measurements. The pinned GPU bridge disables sweep CCD; no effective CCD
improvement is claimed. A 10 mm contact-generation margin per collider, covering
the approximately 16 mm step travel near impact, corrected this bounded drop.
The floor position, physical collider and zero rest offset were preserved. The
reader still validates both original failed configurations; final reports require
the corrected margin. Existing contact-flight scenes retain their original setup.

Local verification: 76 Python tests and two native CTest checks passed. Tests cover
independent reference derivatives, motor interval timing, contact impulse timing,
truncated/modified/private evidence, false aggregates, mixed provenance, omitted
modes/timesteps and refinement failure despite individually passing trials. The
lock check, public-source scan and dated AeroLoop evidence registry check passed.
The measured diagnostic figure was generated with Matplotlib and inspected;
`tools/physics_plot.py` reproduces it from verified retained traces. The existing
3D turbulent mission and mixed-version wind comparison were checked in the local
preview without browser errors; no viewer changes were made.

Generic OpenSteward static and dated strict checks retain only their known
hardcoded `project.identity` mismatch. No generic strict success is claimed.
Raw traces, host logs and diagnostic PNGs remain ignored; the public JSON contains
only declared metadata, measurements and hashes.

Follow-up [yaw diagnostics](isaac-yaw-validation.md) found matching direct/public
pose channels, constant-spin drift and iteration sensitivity. The original yaw
refinement failure is reproduced and remains open. The separate
[closed-loop study](isaac-live-flight-validation.md) measured bounded mission
sensitivity with fixed control cadence. Next investigate small-angle integration
and the shared runtime readout path. These isolated tests do not validate
full-flight convergence, physical calibration, sensors, hardware or learned control.
