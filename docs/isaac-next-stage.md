# Isaac execution and reproduction

Status: installation authorized and completed; headless PhysX smoke passed.
The 256-environment PPO run completed, and its saved policy passed 20/20 fixed
held-out trials after a fresh-process reload. See [evidence](evidence/isaac-validation.md).

The physics-only MVP requires actual Isaac simulation and learning. This environment
is separate from the dependency-free CPU preview.

## Candidate to validate

Use Python 3.12, Isaac Sim Python package `6.1.0.0`, and Isaac Lab `v3.0.0-EA`
at commit `ae37b028ea415c91ea2bc32609efcd759ed2b974`. The official release was
published on 2026-09-16; the tag name explicitly indicates early access despite the
GitHub release not being flagged as a prerelease. Local measurements do not establish
support for every workload or remove the early-access status.
The pinned Lab project declares Python >=3.12,<3.13, Isaac Sim 6.1.0.0 and PyTorch
2.11.0. Follow that tag's dependency configuration, not the older `main` installation
page, which still describes Python 3.11 and Isaac Sim 5.1.

Sources: [release](https://github.com/isaac-sim/IsaacLab/releases/tag/v3.0.0-EA),
[pinned dependency declarations](https://github.com/isaac-sim/IsaacLab/blob/ae37b028ea415c91ea2bc32609efcd759ed2b974/pyproject.toml),
[Isaac Python installation](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/install_python.html).

## Local execution boundary

Create the Isaac environment and pinned upstream checkout under ignored local project
storage, separate from the working CPU environment. Install only from the official
project and package registries. No global driver, OS, license, network exposure or
paid-service changes are included. Keep experiment logging local and disable optional
cloud experiment trackers. Never commit vendor installers, assets or checkpoints.

NVIDIA requires license acceptance before use. The maintainer must review the
[Isaac license index](https://docs.isaacsim.omniverse.nvidia.com/latest/common/legal.html),
[additional software/materials terms](https://www.nvidia.com/en-us/agreements/enterprise-software/isaac-sim-additional-software-and-materials-license/)
and [Omniverse licensing](https://docs.omniverse.nvidia.com/usd/latest/common/NVIDIA_Omniverse_License_Agreement.html).
No tool in this repository accepts those terms on the maintainer's behalf.

## Measured acceptance sequence

1. Verify packages and exact source revisions, then run the vendor compatibility checker.
2. Run a single small headless physics scene with no cameras. Record memory use and
   wall/simulation timing. The available GPU has approximately 12 GB VRAM; current
   published requirements list 16 GB. Capacity remains an experiment, not a guarantee.
3. Inspect the pinned task APIs and select the
   explicit Isaac physics backend. The new Lab release also has Kit-less backends;
   those must not silently replace the required Isaac Sim experiment.
4. Adapt the task to the agreed fixed hover target, confirm one environment, then try
   32 headless environments. Reduce count if necessary and retain the reason.
5. Train locally, retain configuration and checkpoint hashes, reload in a fresh process,
   and evaluate the fixed 20-seed set against an untrained checkpoint. Fix the seeds and
   success rule before training comparison. Record failures and memory limits.
6. Extend evidence contracts for the measured Isaac run and learning family, then
   prepare the reusable website viewer and separate preview integration.

Do not promote the compatibility lock or MVP status until these producing commands
and their retained artifacts exist. If early-access dependencies fail, record the
failure and reassess a supported pairing before trying another version.

## Reproduce locally

After reviewing and accepting the terms, clone the official repository at
`v3.0.0-EA` into `.local/IsaacLab` and verify commit
`ae37b028ea415c91ea2bc32609efcd759ed2b974`. Use Python 3.12 and the upstream frozen
lockfile; keep `UV_CACHE_DIR` and `UV_PROJECT_ENVIRONMENT` inside ignored `.local/`.
On Windows, long paths must already be enabled. No project command changes that OS setting.

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.local/uv-cache'
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) '.local/IsaacLab/.venv'
uv sync --project .local/IsaacLab --frozen --extra isaacsim --python 3.12
# Set this only after personally reviewing and accepting NVIDIA's terms:
$env:OMNI_KIT_ACCEPT_EULA = 'YES'
python tools/isaac.py smoke --output runs/isaac-smoke
python tools/isaac.py train --num-envs 32 --iterations 2 --output runs/isaac-training-check
python tools/isaac.py train --num-envs 256 --iterations 500 --output runs/isaac-hover
python tools/isaac.py evaluate --training-run runs/isaac-hover --split validation --output runs/isaac-validation
python tools/isaac.py evaluate --training-run runs/isaac-hover --split held_out --output runs/isaac-held-out
python tools/isaac_report.py --training-run runs/isaac-hover --evaluation runs/isaac-held-out --output runs/isaac-public-summary.json
```

Use a new output directory for every command. `tools/isaac.py` launches a separate
process, enforces a timeout, and requires a completed result artifact even if Kit
returns exit code zero after a startup error. An evaluation below the success threshold
returns status 2 and retains its results. Inspect `result.json`, not only the exit code.
The underlying workers are implementation details; use the guarded entry point.

Training records the initial and final checkpoint hashes, source revision, dirty flag,
task and lock hashes, configuration, step count and elapsed time. Evaluation records
all 20 trials for both checkpoints and checks task/checkpoint consistency before loading.
Do not reuse held-out seeds for tuning. Full-resolution learning trajectories use
explicit xyzw labels and are separate from the CPU replay format. Training artifacts
are not yet accepted by the public CPU exporter.
The separate summary tool checks checkpoint/configuration digests, trial completeness,
seed coverage and recomputed metrics, then emits only allowlisted summary fields.
Review the generated summary before publishing it; raw logs and checkpoints remain local.
