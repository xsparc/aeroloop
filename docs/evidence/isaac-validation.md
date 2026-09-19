# Isaac execution evidence

Measured 2026-09-20 on Windows with an RTX 5070 (12,227 MiB) and driver 616.92.
This is reduced-workload evidence, not a claim that the host meets NVIDIA's published
16 GB minimum configuration or that physical flight has been validated.

The isolated installation used the official Isaac Lab `v3.0.0-EA` checkout at
`ae37b028ea415c91ea2bc32609efcd759ed2b974` and `uv sync --frozen --extra isaacsim`.
Installed packages report Isaac Sim 6.1.0.0, torch 2.11.0+cu128 and RSL-RL 5.4.1.
The Lab Python distribution reports **17.0.2** internally; this differs from the
repository release tag and must not be confused with an alternative release.

The installed vendor compatibility checker reports **PASSED**. Its bundled check
uses a 10 GB VRAM threshold, while the [current requirements page](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)
lists 16 GB. Both facts are retained; the successful reduced-workload tests remain
the basis of this project's compatibility claim. The checker command was
`isaacsim isaacsim.exp.compatibility_check --no-window --/app/quitAfter=60` in the
isolated environment, with optional telemetry disabled.

## Physics smoke

The retained `isaac-smoke-002` result contains three actual GPU PhysX experiments
using an original 1 kg rigid body with explicit diagonal inertia. At 0.005 s steps:

| Check | Duration | Position error against analytic expectation | Result |
|---|---:|---:|---|
| Free fall | 0.25 s | 0.000385 m | Pass |
| Gravity-balanced body thrust | 1.00 s | 0.000000 m | Pass |
| Thrust after +90° roll | 0.25 s | 0.000544 m | Pass |

Startup plus the checks took 34.76 s. The result's PyTorch allocation counter measures
only PyTorch tensors and is not total simulator VRAM. During the later 256-environment
training run, `nvidia-smi` observed 3,660 MiB total device use, including other desktop
processes; this is a sample, not a measured process peak.

The first smoke failed before simulation because importing scene modules before
Kit preloaded conflicting USD DLLs. Its log remains local. Moving scene imports
inside the launched runtime fixed the conflict. Kit returned zero after that failed
startup, so the parent command now also requires a newly produced completion artifact.

## Learning pipeline

A 32-environment, two-iteration PPO check completed 4,096 transitions and saved
untrained and trained checkpoints. This verifies the execution pipeline only.
A separate 256-environment, 500-iteration run completed 8,192,000 transitions in
603.63 s including startup. Both checkpoints were reloaded in a fresh process for
each evaluation split, with no policy or task tuning between splits:

| Split | Untrained successes | Trained successes |
|---|---:|---:|
| Development: seeds 500–519 | 0 / 20 | 20 / 20 |
| Held-out: seeds 10000–10019 | 0 / 20 | 20 / 20 |

The worst final-window error across all trained held-out trials was 0.0510 m,
against the predeclared 0.30 m limit. Mean full-episode position RMSE was 0.1402 m.
Each success completed 10 s without a failure termination. Every untrained failure
remains in the denominator. The two-iteration pipeline-check policy failed 20/20
development trials, as expected from an undertrained policy; those results are retained.

The [public summary](isaac-hover-001.json) contains all 40 held-out trial metrics,
checkpoint/configuration hashes and source provenance. `tools/isaac_report.py`
recomputed the metrics from full-resolution samples and verified checkpoint hashes
before constructing this allowlisted summary. It excludes raw logs, arbitrary metadata,
paths and sample payloads. Hashes detect changes; they do not authenticate a producer.
The source was a dirty working tree: the recorded task hash identifies the exact task
file in this change. The subsequent [clean-checkout reproduction](reproduction.md)
reloaded the same checkpoints and repeated the held-out evaluation successfully.

The first development reload exposed an inference-mode reset error; evaluation now
performs seeded resets inside inference mode. The complete development and held-out
comparisons above ran after that correction, with the original checkpoints unchanged.

The [task decision](../architecture/decisions/002-isaac-hover-task.md) fixes the model,
reset distribution, reward, observation/action contract, seed sets and acceptance
rule. The CPU-only acceptance tests cover incomplete episodes, failure flags,
non-finite samples and both boundaries of the final two-second window.

Raw startup logs, environment paths, TensorBoard files, checkpoints and trajectories
remain ignored local artifacts. The public CPU replay/export schema intentionally
does not accept these different learning records yet.
