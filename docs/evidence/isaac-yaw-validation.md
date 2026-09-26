# Measured yaw integration and pose sampling

The [decision 010](../architecture/decisions/010-yaw-orientation-audit.md) matrix
completed on 2026-09-27: **30/30 absolute diagnostic cases passed**, while the
**original default yaw-refinement criterion remains false**. AL-013's diagnostic
delivery is complete; AL-010 numerical acceptance remains open. The separate
2 mrad diagnostic bound does not replace decision 007's timestep-dependent gates.

Six actual GPU workers at clean implementation revision
`d25c94ea6b0a3cab974526c20912edb7d034b60e` retained 7,030 full-rate samples. The
implementation digest is
`c293956baaaf2cb91db2360dab04718e837dc02a700b1700d239d11dcde07cfd`.
Isaac Sim 6.1.0.0, Isaac Lab distribution 17.0.2 and Torch 2.11.0+cu128 match the
prior study. Summed worker wall time was 27.450 s, excluding interpreter/import
startup outside the worker. The [public summary](isaac-yaw-001.json) preserves
checksums, all outcomes, signed metrics and both iteration configurations.

Final signed yaw errors in milliradians at 0.5 s:

| Case | 1 iter, 200 Hz | 1 iter, 400 Hz | 1 iter, 800 Hz | 4 iter, 200 Hz | 4 iter, 400 Hz | 4 iter, 800 Hz |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Spin +0.05 rad/s | -0.019344 | -0.056795 | -0.131718 | -0.131698 | -0.131698 | -0.431346 |
| Spin +0.5 rad/s | -0.007776 | -0.044371 | -0.118716 | -0.118775 | -0.118523 | -0.118464 |
| Spin -0.5 rad/s | +0.007776 | +0.044371 | +0.118716 | +0.118775 | +0.118523 | +0.118464 |
| Torque +0.04 Nm | +1.236063 | +0.592537 | +0.242157 | +0.242522 | +0.011929 | -0.216567 |
| Torque -0.04 Nm | -1.236063 | -0.592537 | -0.242157 | -0.242522 | -0.011929 | +0.216567 |

All direct/public/repeated orientation differences were zero at every recorded
sample. Public/direct world-rate and position differences were also zero. The
maximum rate error was 0.000005305 rad/s and maximum quaternion norm error was
0.0000001043. Position drift was zero, with peak linear speed 0.000001042 m/s.
The normalized four-iteration positive-torque quaternions match every sample of
the prior decision 007 traces exactly at each frequency.

## Interpretation

The error is already present in the direct tensor pose; neither AeroLoop's
quaternion normalization nor disagreement between these pose getters explains
it. Constant-spin cases show accumulated orientation drift without applied yaw
torque, a flight controller or rotor dynamics. Positive/negative cases mirror
one another. The signed residual against integrated measured rate follows the
orientation error, while measured rate stays much closer to its reference.

Changing the iteration count changes these errors, but is not a general fix:
one iteration increases coarse-step torque error even though its torque series
passes the original refinement formula. Four iterations and the original force
mode remain unchanged in flight scenes. No new full-flight convergence claim
or revised acceptance threshold is introduced.

These observations narrow the next investigation to orientation integration or
the readout path shared by both getters. They do not identify an exact GPU
kernel defect. Current public
[GPU TGS integration source](https://github.com/NVIDIA-Omniverse/PhysX/blob/main/physx/source/gpusolver/src/CUDA/integration.cuh)
composes an accumulated delta quaternion with the body orientation, but that
source is not an attestation of the kernel in the installed binary. A focused
reproduction of small-angle arithmetic and the corresponding runtime version is
the next step before proposing a vendor/runtime change.

The initial development run compared public body-frame rates with direct
world-frame rates. Float conversion differences up to 0.000000209 rad/s made
four of five read-channel gates fail. Those traces remain retained and readable
under their original configuration. Final reporting requires explicitly matched
world-rate channels; the 1e-7 threshold was not relaxed.

## Verification

The report independently revalidated all six workers and returned exit 2 for
the preserved refinement failure. The signed-error figure was generated from
verified traces using `tools/yaw_plot.py` and visually inspected. Raw traces,
host logs and figures remain local and ignored; the public summary contains
only declared numeric evidence and provenance.

Local CPU validation passed 92 tests, with one Windows symbolic-link permission
skip, plus both native CTest checks. Six new tests cover independent analytic
endpoints/derivatives, quaternion signs, complete matrices, read disagreement,
missing or corrupted samples, altered inputs, private metadata, false success,
legacy development configuration and validated worker completion. The dependency
lock, public-source and dated AeroLoop evidence checks passed. Generic
OpenSteward checks retain their known hardcoded project-identity mismatch.

The retained mission evaluation was also opened in Chromium at the 40 s landing
gust: both 3D canvases rendered with no page errors. These are the earlier nine
mission recordings, not new flight-controller trials. No controller, mission
physics setting, dependency, training or hardware configuration changed.
