# Isaac execution proposal

Status: ready for environment approval; no Isaac installation or execution performed.

The physics-only MVP still requires actual Isaac simulation and learning. The CPU
preview is working, so the next dependency is an isolated GPU environment.

## Candidate to validate

Use Python 3.12, Isaac Sim Python package `6.1.0.0`, and Isaac Lab `v3.0.0-EA`
at commit `ae37b028ea415c91ea2bc32609efcd759ed2b974`. The official release was
published on 2026-09-16; the tag name explicitly indicates early access despite the
GitHub release not being flagged as a prerelease. Do not call it a validated environment.
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
3. Inspect the pinned quadcopter task's action/observation contract and select its
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
