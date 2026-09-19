"""Read-only, privacy-preserving capability checks."""
import importlib.util
import platform
import shutil
import subprocess
import sys


def probe():
    capabilities = {
        "python": {"status": "passed" if sys.version_info >= (3, 11) else "blocked",
                   "version": platform.python_version()},
        "platform": {"system": platform.system(), "architecture": platform.machine()},
    }
    for command in ("cmake", "ctest", "ninja", "git", "node"):
        capabilities[command] = {"status": "available" if shutil.which(command) else "missing"}
    for module in ("isaacsim", "isaaclab", "torch"):
        capabilities[module] = {"status": "available" if importlib.util.find_spec(module) else "missing"}
    gpu = {"status": "missing"}
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10, check=True,
            )
            devices = []
            for line in result.stdout.strip().splitlines():
                name, memory, driver = [part.strip() for part in line.split(",")]
                devices.append({"model": name, "vram_mib": int(memory), "driver": driver})
            gpu = {"status": "available", "devices": devices, "workload_validated": False}
        except (OSError, ValueError, subprocess.SubprocessError):
            gpu = {"status": "blocked", "reason": "GPU query failed"}
    capabilities["gpu"] = gpu
    return {"schema_version": 1, "capabilities": capabilities,
            "isaac_validation": "not_run", "installs_performed": False}
