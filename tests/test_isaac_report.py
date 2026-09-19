import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from aeroloop.contracts import ValidationError
from aeroloop.learning import EVALUATION_SEEDS, assess_hover

spec = importlib.util.spec_from_file_location("isaac_report", Path(__file__).resolve().parents[1] / "tools/isaac_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class IsaacReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.training = Path(self.temp.name) / "train"
        self.evaluation = Path(self.temp.name) / "eval"
        self.training.mkdir()
        self.evaluation.mkdir()
        for name in ("untrained.pt", "trained.pt", "config.json"):
            (self.training / name).write_bytes(b"test-only checksum material")
        self.train = {
            "kind": "isaac_hover_training", "backend": "isaacsim_physx",
            "versions": {"isaacsim": "6.1.0.0", "isaaclab": "17.0.2", "torch": "2.11.0+cu128"},
            "checkpoints": {n: report.digest(self.training / n) for n in ("untrained.pt", "trained.pt")},
            "config_sha256": report.digest(self.training / "config.json"), "source_commit": "a" * 40,
            "task_sha256": "b" * 64, "lock_sha256": "c" * 64, "source_dirty": True,
            "seed": 73, "num_envs": 32, "iterations": 2, "transitions": 4096, "wall_time_s": 10.0,
            "private_metadata": "must remain local"}
        (self.training / "result.json").write_text(json.dumps(self.train))
        rows = [[i*0.02, 0, 0, 1.5, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0] for i in range(501)]
        self.measured = {"kind": "isaac_hover_evaluation", "backend": "isaacsim_physx",
                         "split": "held_out", "fresh_process_reload": True,
                         "seeds": list(EVALUATION_SEEDS), "versions": self.train["versions"],
                         "training_result_sha256": report.digest(self.training / "result.json"),
                         "checkpoints": self.train["checkpoints"],
                         "trials": [{"checkpoint": name, "seed": seed, "samples_xyzw": rows,
                                     **assess_hover(rows, False)}
                                    for name in ("untrained.pt", "trained.pt") for seed in EVALUATION_SEEDS],
                         "successes": {"untrained.pt": 20, "trained.pt": 20}, "trained_meets_threshold": True}

    def summarize(self):
        (self.evaluation / "result.json").write_text(json.dumps(self.measured))
        return report.summarize(self.training, self.evaluation)

    def test_public_summary_omits_private_metadata_and_raw_samples(self):
        output = json.dumps(self.summarize())
        self.assertNotIn("private_metadata", output)
        self.assertNotIn("must remain local", output)
        self.assertNotIn("samples_xyzw", output)

    def test_duplicate_seed_and_forged_metric_rejected(self):
        self.measured["trials"][1]["seed"] = EVALUATION_SEEDS[0]
        with self.assertRaises(ValidationError):
            self.summarize()
        self.measured["trials"][1]["seed"] = EVALUATION_SEEDS[1]
        self.measured["trials"][1]["position_rmse_m"] = 0.1
        with self.assertRaises(ValidationError):
            self.summarize()

    def test_changed_checkpoint_rejected(self):
        (self.training / "trained.pt").write_bytes(b"changed checkpoint")
        with self.assertRaises(ValidationError):
            self.summarize()


if __name__ == "__main__":
    unittest.main()
