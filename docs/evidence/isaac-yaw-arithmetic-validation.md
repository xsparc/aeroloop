# Measured yaw arithmetic controls

The [decision 011](../architecture/decisions/011-yaw-arithmetic-study.md) study
completed on 2026-09-27. **All 18 constant-spin comparisons support the declared
fast-trigonometry signature**, and both arithmetic controls pass. All 30 fresh
PhysX diagnostic cases pass their absolute bounds. **The original default yaw
refinement criterion still fails**, so AL-010 numerical acceptance remains open.

The study ran at clean revision `d74a6dc1077510c3a9c3c571f5af7e010f525b73`, source
digest `cbd24e572fa48f83755c0e0c0d44cdbee6f6d9a4eb0c1bffe1c09586a27305eb`.
It recorded 7,030 PhysX samples and 12,654 arithmetic quaternion samples.
The 102.530 s study wall time includes six serial worker launches, verification,
fingerprinting and the CUDA probe. The [public summary](isaac-yaw-arithmetic-001.json)
contains all 18 comparisons, source/tool hashes and selected installation hashes.

## Results

Each row below covers all three rates: +0.05, +0.5 and -0.5 rad/s. Errors are
maximum absolute differences over the full 0.5 s traces, in microradians.

| Position iterations | Physics Hz | Fast intrinsic vs PhysX | Library float32 vs analytic |
| ---: | ---: | ---: | ---: |
| 1 | 200 | 0.079122 | 0.060458 |
| 1 | 400 | 0.125885 | 0.077476 |
| 1 | 800 | 0.170317 | 0.148120 |
| 4 | 200 | 0.066399 | 0.060458 |
| 4 | 400 | 0.214902 | 0.123159 |
| 4 | 800 | 0.448755 | 0.153497 |

The largest fast-intrinsic disagreement with PhysX was 4.488e-7 rad, below the
fixed 5e-6 rad bound. The largest disagreement relative to that case's PhysX
reference error was 1.018%, below the fixed 10% bound. Library float32 stayed
within 1.535e-7 rad of the analytic reference; library float64 stayed within
3.331e-16 rad. The measured PhysX constant-spin drift reached 4.313e-4 rad.

Every sample in all 30 new physics traces equals the corresponding retained
AL-013 sample exactly. This includes torque, direct/public/repeated read channels
and inputs. The original torque refinement failure therefore reproduces again.
No reference, threshold, force mode, timestep or flight scene was changed.

## Interpretation and limits

The controlled recurrence changes only scalar precision and trigonometry while
composing normalized pure-yaw rotations. Fast float32 sine/cosine reproduces the
measured constant-spin error pattern; library float32 and float64 remain close
to the analytic solution. This supports fast-trigonometry error as a mechanism
for these constant-spin results, rather than generic float32 storage precision
alone. The signed comparison figure was generated from verified traces and
visually inspected; fast-intrinsic and measured curves closely overlap.

The public [TGS accumulation source](https://github.com/NVIDIA-Omniverse/PhysX/blob/main/physx/source/gpusolver/src/CUDA/solverMultiBlockTGS.cu)
calls the fast intrinsic. NVIDIA's [floating-point guidance](https://docs.nvidia.com/cuda/floating-point/index.html)
explains why operation choice and compilation affect numerical results. These
sources and the measured match do not attest the installed instruction path.
The recurrence is original pure-yaw arithmetic, not the whole PhysX solver.
Torque substep rates are unobserved and no torque-kernel reproduction is claimed.
No vendor library was patched and no general solver fix was validated.

The measured environment used Isaac Sim 6.1.0.0, Isaac Lab distribution 17.0.2,
Torch 2.11.0+cu128 and Warp 1.16.0. Warp reported CUDA toolkit 12.9, driver API
13.4 and compute capability 120. Selected PhysX core/GPU/tensor extension
manifests report 110.3.2; the Windows GPU library file-version metadata reports
5.9.1.0. Manifest and GPU binary hashes remained unchanged around measurement.
These are selected installation identities, not a complete dependency inventory
or proof of which native module supplied every instruction.

## Verification and next development

Five new CPU tests cover independent reference endpoints/signs, full matrices,
retained hypothesis/control failures, malformed or private trace fields, reset
and norm errors, false outcomes, mixed source and bounded installation identities.
Full local CPU validation passed 97 tests, with one existing Windows symbolic-link
permission skip. Dependency lock, public-source, UTF-8 and dated AeroLoop evidence
checks passed. Generic OpenSteward static and strict checks retain only their
known hardcoded project-identity mismatch.

The study and offline report deliberately return exit 2 while the original
refinement flag is false. The new diagnostic delivery is complete; the physics
acceptance criterion is not waived. Raw traces, logs, kernel caches and figures
remain local and ignored. The unchanged [3D flight evaluation](../flight-evaluation.md)
continues to expose the earlier full-flight sensitivity results.

Keep the runtime pinned and the numerical limitation visible. The next flight
study can now address the previously deferred sensor noise and observation delay,
with truth kept separate from controller observations. Any later runtime or solver
mitigation must rerun the original accuracy and controlled-flight studies before
it can replace the current baseline.
