# Compatibility evidence

Inspected and measured 2026-09-20. Actual headless Isaac PhysX and a small PPO
training pipeline have executed. See [measured evidence](evidence/isaac-validation.md).

The development host runs Windows with an NVIDIA RTX 5070 reporting 12,227 MiB
VRAM and driver 616.92. Python 3.12.13 and MSVC 14.51 are available. Only the
Docker Desktop WSL distribution is present; it is not a general Linux development
environment. Host names, serials, user paths and contact details are omitted.

Isaac Sim and Isaac Lab are installed in a separate environment. The original
5.1.0/2.3.2 combination was not installed. NVIDIA marks Isaac Sim 5.1
unsupported and lists a 16 GB VRAM minimum-class configuration. The current GPU
can execute the measured reduced workload; this does not establish general support.
[NVIDIA requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)

The bundled compatibility checker reports PASSED using its own 10 GB VRAM threshold.
This differs from the current requirements table's 16 GB. Retain that discrepancy
and limit claims to the workloads actually measured here.

PX4 and Pegasus are no longer required by the revised MVP. This removes Pegasus's
Linux-tested transport from the critical path.
[Pegasus installation](https://pegasussimulator.github.io/PegasusSimulator/source/setup/installation.html)

Installation and local tests were explicitly authorized after license review.
The 32-environment training pipeline check passed. Keep exact package/source
revisions, configuration hashes and retained logs with larger experiments.

The follow-up scan found Isaac Sim 6.1.0 and Isaac Lab v3.0.0-EA. The pinned Lab
release explicitly selects Sim 6.1.0.0 and Python 3.12. The measured environment
uses that pairing. The Lab distribution metadata is 17.0.2, while the checkout tag
is 3.0.0-EA. See [execution and reproduction](isaac-next-stage.md).
