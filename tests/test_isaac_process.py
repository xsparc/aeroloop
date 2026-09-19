import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from aeroloop.contracts import ValidationError
from aeroloop.isaac_process import run_worker


class IsaacProcessTests(unittest.TestCase):
    def test_zero_exit_without_completion_artifact_is_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("aeroloop.isaac_process._execute"):
                with self.assertRaises(FileNotFoundError):
                    run_worker("python", "smoke", Path(temp) / "new")

    def test_stale_result_cannot_mask_failed_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch("aeroloop.isaac_process._execute") as process:
                with self.assertRaises(ValidationError):
                    run_worker("python", "smoke", temp)
                process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
