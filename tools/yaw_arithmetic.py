"""Measure a bounded CUDA arithmetic probe and fresh isolated PhysX yaw matrix."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from aeroloop import yaw_audit as yaw
from aeroloop import yaw_arithmetic as audit
from aeroloop.evidence import require
from aeroloop.isaac_process import run_worker
from aeroloop.simulation import encoded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("Choose a new study directory.")
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        parser.error("Review NVIDIA terms and set OMNI_KIT_ACCEPT_EULA=YES before running Isaac.")
    source, tool_hashes = yaw.provenance(), audit.tool_checksums()
    require(source["source_dirty"] is False, "Freeze the study at a clean commit before measuring")
    isaac_root = Path(importlib.util.find_spec("isaacsim").origin).parent
    installed = audit.installation(isaac_root)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    def guard():
        require(source == yaw.provenance() and tool_hashes == audit.tool_checksums(), "Study source changed during measurement")
        require(installed == audit.installation(isaac_root), "PhysX installation changed during measurement")
    hashes = {}
    for n in yaw.ITERATIONS:
        for dt in yaw.TIMESTEPS:
            guard()
            name = audit.worker_name(n, dt)
            run_worker(Path(sys.executable), "yaw", args.output/name,
                       ["--physics-dt", str(dt), "--solver-iterations", str(n)], timeout=600)
            hashes[name] = audit.digest(args.output/name/"result.json")
    # Import CUDA only after the isolated physics workers have released their contexts.
    import warp as wp
    wp.config.kernel_cache_dir = str(ROOT/".local/warp-yaw-arithmetic")
    wp.init()
    from aeroloop import yaw_arithmetic_gpu as gpu
    wp.set_module_options({"fast_math": False, "enable_backward": False}, module=gpu)
    trials = []
    for n, dt, case in audit.matrix():
        methods = {name: gpu.capture(yaw.CASES[case][0], dt, n, mode) for mode, name in enumerate(audit.METHODS)}
        trials.append({"case": case, "dt_s": dt, "position_iterations": n, "methods": methods})
    (args.output/"arithmetic.json").write_bytes(encoded({"schema_version": 1, "kind": "measured_cuda_yaw_arithmetic", "trials": trials}))
    guard()
    outcomes, _ = audit.outcomes(args.output)
    result = {"schema_version": 1, "kind": "yaw_arithmetic_study", "backend": "cuda_arithmetic_vs_physx",
              "provenance": source, "tool_checksums": tool_hashes, "configuration": audit.CONFIGURATION,
              "installation": installed, "arithmetic_runtime": {"warp": wp.__version__,
                  "cuda_toolkit": ".".join(map(str,wp.get_cuda_toolkit_version())),
                  "cuda_driver": ".".join(map(str,wp.get_cuda_driver_version())),
                  "compute_capability": str(wp.get_device("cuda:0").arch)},
              "physics_result_checksums": hashes, "arithmetic_sha256": audit.digest(args.output/"arithmetic.json"),
              "wall_time_s": time.perf_counter()-started, "outcomes": outcomes}
    (args.output/"result.json").write_bytes(encoded(result))
    audit.read_study(args.output)
    print(f"Arithmetic controls: {outcomes['controls_passed']}; fast signature: {outcomes['fast_signature_supported']}; original refinement: {outcomes['default_yaw_refinement_passed']}", flush=True)
    return 0 if all(outcomes[k] for k in ("controls_passed", "physics_diagnostics_passed", "default_yaw_refinement_passed")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
