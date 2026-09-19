# Compatibility evidence

Inspected 2026-09-20. No Isaac workload has executed for this project.

The development host runs Windows with an NVIDIA RTX 5070 reporting 12,227 MiB
VRAM and driver 616.92. Python 3.12.13 and MSVC 14.51 are available. Only the
Docker Desktop WSL distribution is present; it is not a general Linux development
environment. Host names, serials, user paths and contact details are omitted.

Isaac Sim and Isaac Lab are not installed in the CPU environment. The original
5.1.0/2.3.2 combination remains a candidate only. NVIDIA marks Isaac Sim 5.1
unsupported and lists a 16 GB VRAM minimum-class configuration. The current GPU
therefore needs a measured reduced-workload trial before any support claim.
[NVIDIA requirements](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)

PX4 and Pegasus are no longer required by the revised MVP. This removes Pegasus's
Linux-tested transport from the critical path.
[Pegasus installation](https://pegasussimulator.github.io/PegasusSimulator/source/setup/installation.html)

Unblock Isaac using a licensed, compatible installation, validate startup and one
small headless scene, then measure the 32-environment learning workload. Record exact
package/source revisions, configuration hashes, memory peaks and retained logs.
Reconsider a supported Isaac release pairing before installing the legacy candidate.

The follow-up scan found Isaac Sim 6.1.0 and Isaac Lab v3.0.0-EA. The pinned Lab
release explicitly selects Sim 6.1.0.0 and Python 3.12. This is the next candidate to
assess, not a tested upgrade. See the [execution proposal](isaac-next-stage.md).
