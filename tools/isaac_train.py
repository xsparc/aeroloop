"""Train or evaluate the camera-free AeroLoop hover policy in a pinned Isaac environment."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    if os.environ.get("OMNI_KIT_ACCEPT_EULA") != "YES":
        raise SystemExit("Review NVIDIA's terms and set OMNI_KIT_ACCEPT_EULA=YES before running Isaac.")
    from isaaclab.app import add_launcher_args, launch_simulation
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("train", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--training-run", type=Path)
    parser.add_argument("--split", choices=("validation", "held_out"), default="validation")
    parser.add_argument("--num-envs", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=300)
    add_launcher_args(parser)
    parser.set_defaults(headless=True, visualizer=["none"], device="cuda:0", livestream=0)
    args = parser.parse_args()
    args.kit_args += " --/telemetry/enableAnonymousData=false --/telemetry/enableNVDF=false --/telemetry/enableSentry=false --/telemetry/useOpenEndpoint=false"
    if (not 1 <= args.num_envs <= 1024 or not 1 <= args.iterations <= 5000
            or args.device != "cuda:0" or args.livestream != 0 or not args.headless):
        parser.error("Use 1..1024 environments, 1..5000 iterations, headless cuda:0 and no livestream.")
    if args.mode == "evaluate" and args.training_run is None:
        parser.error("evaluate requires --training-run")

    import torch
    from isaaclab_physx.physics import PhysxCfg
    from aeroloop.isaac_runtime import versions
    from aeroloop.learning import assess_hover, EVALUATION_SEEDS, VALIDATION_SEEDS, CONTROL_DT

    torch.set_num_threads(4)
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    with launch_simulation(PhysxCfg(), args):
        from rsl_rl.runners import OnPolicyRunner
        from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, handle_deprecated_rsl_rl_cfg
        from aeroloop.isaac_hover import HoverCfg, HoverEnv, runner_config
        cfg = HoverCfg()
        cfg.scene.num_envs = args.num_envs if args.mode == "train" else 1
        config = handle_deprecated_rsl_rl_cfg(runner_config(args.iterations),
                                            importlib.metadata.version("rsl-rl-lib")).to_dict()
        env = HoverEnv(cfg)
        wrapped = RslRlVecEnvWrapper(env, clip_actions=1.0)
        runner = OnPolicyRunner(wrapped, config,
                                log_dir=str(args.output / "logs") if args.mode == "train" else None,
                                device="cuda:0")
        if args.mode == "train":
            source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            source_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
            write_json(args.output / "config.json", config)
            runner.save(str(args.output / "untrained.pt"))
            runner.learn(args.iterations, init_at_random_ep_len=True)
            runner.save(str(args.output / "trained.pt"))
            result = {"schema_version": 1, "kind": "isaac_hover_training", "task_revision": 1,
                      "backend": "isaacsim_physx", "versions": versions(),
                      "source_commit": source_commit, "source_dirty": source_dirty,
                      "lock_sha256": digest(ROOT / "versions.lock.json"),
                      "task_sha256": digest(ROOT / "src/aeroloop/isaac_hover.py"),
                      "seed": 73, "num_envs": args.num_envs, "iterations": args.iterations,
                      "transitions": args.num_envs * args.iterations * config["num_steps_per_env"],
                      "checkpoints": {name: digest(args.output / name)
                                      for name in ("untrained.pt", "trained.pt")},
                      "config_sha256": digest(args.output / "config.json"),
                      "wall_time_s": time.perf_counter() - start}
        else:
            training = json.loads((args.training_run / "result.json").read_text(encoding="utf-8"))
            if training["task_sha256"] != digest(ROOT / "src/aeroloop/isaac_hover.py"):
                raise ValueError("Task changed since training; refuse mismatched evaluation")
            seeds = EVALUATION_SEEDS if args.split == "held_out" else VALIDATION_SEEDS
            trials = []
            for name in ("untrained.pt", "trained.pt"):
                checkpoint = args.training_run / name
                if digest(checkpoint) != training["checkpoints"][name]:
                    raise ValueError("Checkpoint checksum mismatch")
                # Avoid the runner's unrestricted pickle loader. Only tensor/primitive state is accepted.
                saved = torch.load(checkpoint, weights_only=True, map_location="cuda:0")
                runner.alg.load(saved, load_cfg={"actor": True, "critic": True}, strict=True)
                policy = runner.get_inference_policy(device="cuda:0")
                for seed in seeds:
                    with torch.inference_mode():
                        wrapped.env.reset(seed=seed)
                    state = torch.cat(env.state(), dim=-1)[0].cpu().tolist()
                    rows = [[0.0, *state]]
                    failed = False
                    with torch.inference_mode():
                        for step in range(500):
                            action = policy(wrapped.get_observations())
                            wrapped.step(action)
                            rows.append([(step + 1) * CONTROL_DT, *env.measured_state[0].cpu().tolist()])
                            failed = bool(env.reset_terminated[0])
                            if failed:
                                break
                    trial = {"checkpoint": name, "seed": seed,
                             **assess_hover(rows, failed), "samples_xyzw": rows}
                    trials.append(trial)
                    print(json.dumps({k: v for k, v in trial.items() if k != "samples_xyzw"}), flush=True)
            successes = {name: sum(t["success"] for t in trials if t["checkpoint"] == name)
                         for name in ("untrained.pt", "trained.pt")}
            result = {"schema_version": 1, "kind": "isaac_hover_evaluation", "task_revision": 1,
                      "backend": "isaacsim_physx", "versions": versions(), "fresh_process_reload": True,
                      "training_result_sha256": digest(args.training_run / "result.json"),
                      "checkpoints": training["checkpoints"], "split": args.split,
                      "seeds": list(seeds), "trials": trials, "successes": successes,
                      "trained_meets_threshold": successes["trained.pt"] >= 16,
                      "wall_time_s": time.perf_counter() - start}
        write_json(args.output / "result.json", result)
        env.close()


if __name__ == "__main__":
    main()
