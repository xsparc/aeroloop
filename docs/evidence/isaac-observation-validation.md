# Observation robustness validation

AL-015 measured four observation profiles across seeds 0, 1 and 2 in actual Isaac
Sim PhysX on 2026-09-27. All flights use the frozen controller, 200 Hz physics,
rotors, wind and contact mission from [decision 012](../architecture/decisions/012-observation-robustness.md).
The [full-rate report](isaac-observation-001.json) retains 12/12 mission
passes and 9/9 paired robustness passes.
Overall bounded robustness acceptance: **true**.

| Profile | Mission passes | Position RMSE range (m) | Measured real-time factor |
| --- | --- | --- | --- |
| ideal | 3/3 | 0.109192–0.132522 | 1.359–1.391 |
| noise | 3/3 | 0.109110–0.132484 | 1.385–1.390 |
| delay | 3/3 | 0.109634–0.133141 | 1.359–1.410 |
| noise-delay | 3/3 | 0.109554–0.133070 | 1.000–1.000 |

All twelve traces contain 10001 control samples (120012 total). The combined
profile is wall paced; the other profiles run as fast as available. Timing excludes
startup and serialization; this remains soft real-time execution.

The next table reports worst-case differences from same-seed ideal feedback.
The predeclared bounds remain 150 mm peak position difference, 50 mm absolute
position-RMSE change and 500 ms absolute landed-time change.

| Profile | Peak truth-position difference (mm) | RMSE change (mm) | Landed-time change (ms) | Paired passes |
| --- | --- | --- | --- | --- |
| noise | 4.821 | 0.211 | 15.0 | 3/3 |
| delay | 29.992 | 0.619 | 35.0 | 3/3 |
| noise-delay | 32.581 | 0.548 | 30.0 | 3/3 |

## Source and interpretation

Every final trial used clean source `27afe01388df4a778bdcb9a7fe7a4d3655739fe3`; controller binary,
source-tree and dependency-lock hashes are retained in the report. Isaac Sim
6.1.0.0, Isaac Lab distribution 17.0.2 and
Torch 2.11.0+cu128 ran on the existing local GPU installation.
Development seed 73 also passed the combined profile before the final matrix;
it is excluded from the twelve-trial result. No controller gain, noise parameter
or acceptance bound was tuned against final seeds.

The three new ideal traces match the retained AL-011 200 Hz baseline exactly
when the new observation field is removed: every state/control sample, shared
configuration, event and metric agrees. Thus the new observation path preserves
that baseline. All original mission gates remain unchanged.

Noise applies only to captured position and velocity. The dedicated seeded stream
uses nominal 0.01 m and 0.02 m/s Gaussian standard deviations clipped at three
standard deviations. Delay holds eight 5 ms samples, including startup hold-first
behavior. The CPU verifier reconstructs delivered vectors from the captured truth
and seed, recomputes outer-controller setpoints and verifies original full-rate
mission metrics. Geometry, forces, safety bounds and scores always use truth.

Attitude/rate/acceleration feedback, the mission supervisor and contact sensing
remain ideal. No IMU/GNSS calibration, state estimator, general stability proof or
hardware flight validation is claimed. AL-010's yaw-refinement gate stays open;
no runtime or solver change is included.

## Verification and follow-up

Local validation passed 102 Python tests with one existing Windows symlink
permission skip; both native C++ tests; 14 frontend tests; three legacy viewer
tests; and 15 browser checks with three conditional fixture skips. The browser
checks include observation-profile/age validation, actual WebGL rendering, truth
tracking scores and reconnect/failure behavior. Public-source, UTF-8, dependency
lock and dated AeroLoop evidence checks passed. Generic OpenSteward static and
strict checks retain their known hardcoded project-identity mismatch.

The actual combined-profile monitor was inspected in 3D during seed 0 landing
at 38.2 s, seed 1 waypoint flight at 13.1 s, and the final verified seed 2 landing
at 50 s. It showed 40 ms observation age, distinct position/velocity discrepancies,
truth pose, changing rotor thrust and measured wall-clock lag. The completed
view showed zero commanded effort and rotor thrust, with physical ground support.

Raw traces, runtime logs and plots remain local and ignored. Use the
[reproduction workflow](../observation-robustness.md) to regenerate the report and
figure. Schema-six replay export is explicitly rejected for now; live 3D and the
full-rate report provide inspection. The next slice should add recorded paired
3D inspection of these fixed observation profiles, preserving their truth-based
gates and visible ideal-channel limitations.
