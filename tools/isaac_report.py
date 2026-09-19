"""Recompute a held-out evaluation and write a small allowlisted public summary."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aeroloop.contracts import ValidationError, finite, load_json
from aeroloop.learning import EVALUATION_SEEDS, assess_hover


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_hash(value, length=64):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{" + str(length) + "}", value):
        raise ValidationError("invalid provenance digest")
    return value


def summarize(training_run, evaluation):
    training = load_json(training_run / "result.json")
    measured = load_json(evaluation / "result.json")
    if (training.get("kind") != "isaac_hover_training" or measured.get("kind") != "isaac_hover_evaluation"
            or training.get("backend") != "isaacsim_physx" or measured.get("backend") != "isaacsim_physx"
            or measured.get("split") != "held_out" or measured.get("fresh_process_reload") is not True
            or measured.get("seeds") != list(EVALUATION_SEEDS)
            or measured.get("training_result_sha256") != digest(training_run / "result.json")):
        raise ValidationError("evaluation does not match the fixed held-out protocol")
    if training.get("checkpoints") != measured.get("checkpoints"):
        raise ValidationError("checkpoint manifest mismatch")
    names = ("untrained.pt", "trained.pt")
    if set(training["checkpoints"]) != set(names):
        raise ValidationError("invalid checkpoint names")
    for name in names:
        if checked_hash(training["checkpoints"][name]) != digest(training_run / name):
            raise ValidationError("checkpoint changed")
    if checked_hash(training["config_sha256"]) != digest(training_run / "config.json"):
        raise ValidationError("training configuration changed")
    if type(training.get("source_dirty")) is not bool:
        raise ValidationError("invalid source state")
    versions = training.get("versions")
    if (not isinstance(versions, dict) or set(versions) != {"isaacsim", "isaaclab", "torch"}
            or versions != measured.get("versions")
            or any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9.+-]{1,50}", v)
                   for v in versions.values())):
        raise ValidationError("invalid or inconsistent package versions")
    for key in ("seed", "num_envs", "iterations", "transitions"):
        if type(training.get(key)) is not int or training[key] < 1:
            raise ValidationError("invalid training count")
    if not finite(training.get("wall_time_s")) or training["wall_time_s"] <= 0:
        raise ValidationError("invalid training duration")
    trials = measured.get("trials")
    if not isinstance(trials, list) or len(trials) != 40:
        raise ValidationError("both checkpoints require all 20 trials")
    seen, summaries = set(), []
    successes = dict.fromkeys(names, 0)
    for trial in trials:
        name, seed = trial.get("checkpoint"), trial.get("seed")
        if type(seed) is not int or name not in names or seed not in EVALUATION_SEEDS or (name, seed) in seen:
            raise ValidationError("unexpected or duplicate trial")
        seen.add((name, seed))
        metrics = assess_hover(trial["samples_xyzw"], trial["failed_termination"])
        if any(trial.get(k) != v for k, v in metrics.items()):
            raise ValidationError("stored metrics disagree with recorded samples")
        successes[name] += metrics["success"]
        summaries.append({"checkpoint": name, "seed": seed, **metrics})
    if successes != measured.get("successes") or measured.get("trained_meets_threshold") is not (successes["trained.pt"] >= 16):
        raise ValidationError("stored aggregate disagrees with trial outcomes")
    return {"schema_version": 1, "kind": "isaac_hover_summary", "backend": "isaacsim_physx",
            "versions": versions, "training_result_sha256": digest(training_run / "result.json"),
            "evaluation_result_sha256": digest(evaluation / "result.json"),
            "source_commit": checked_hash(training["source_commit"], 40),
            "source_dirty": training["source_dirty"], "task_sha256": checked_hash(training["task_sha256"]),
            "lock_sha256": checked_hash(training["lock_sha256"]),
            "config_sha256": training["config_sha256"], "checkpoints": training["checkpoints"],
            "training": {key: training[key] for key in ("seed", "num_envs", "iterations", "transitions", "wall_time_s")},
            "seeds": list(EVALUATION_SEEDS), "successes": successes,
            "trained_meets_threshold": successes["trained.pt"] >= 16, "trials": summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-run", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(args.training_run, args.evaluation)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print("Verified all 40 trial outcomes and wrote the public summary.")


if __name__ == "__main__":
    main()
