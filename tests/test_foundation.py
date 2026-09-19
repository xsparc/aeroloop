import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aeroloop.contracts import ValidationError, load_json, validate_lock
from aeroloop.doctor import probe
from aeroloop.frames import ned_to_enu, frd_to_flu, ned_frd_to_enu_flu, normalize, rotate


class FoundationTests(unittest.TestCase):
    def test_frame_axes_and_roundtrips(self):
        self.assertEqual(ned_to_enu((1, 0, 0)), (0, 1, 0))
        self.assertEqual(ned_to_enu((0, 0, -2)), (0, 0, 2))
        self.assertEqual(ned_to_enu(ned_to_enu((1, 2, 3))), (1, 2, 3))
        self.assertEqual(frd_to_flu(frd_to_flu((1, 2, 3))), (1, 2, 3))
        for actual, expected in zip(rotate(ned_frd_to_enu_flu((1, 0, 0, 0)), (1, 0, 0)), (0, 1, 0)):
            self.assertAlmostEqual(actual, expected)

    def test_quaternion_rejects_invalid_numbers(self):
        for q in [(0, 0, 0, 0), (1, 0, math.nan, 0), (True, 0, 0, 0)]:
            with self.assertRaises(ValidationError):
                normalize(q)

    def test_lock_does_not_validate_without_evidence(self):
        lock = load_json(Path(__file__).resolve().parents[1] / "versions.lock.json")
        validate_lock(lock)
        lock["profiles"]["isaac"]["status"] = "validated"
        lock["profiles"]["isaac"]["evidence"] = []
        with self.assertRaises(ValidationError):
            validate_lock(lock)

    def test_json_duplicate_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for content in ['{"a":1,"a":2}', '{"a":NaN}']:
                path.write_text(content)
                with self.assertRaises(ValidationError):
                    load_json(path)

    @patch("aeroloop.doctor.shutil.which", return_value=None)
    @patch("aeroloop.doctor.importlib.util.find_spec", return_value=None)
    def test_doctor_missing_gpu_is_not_validation(self, *_):
        result = probe()
        self.assertEqual(result["capabilities"]["gpu"]["status"], "missing")
        self.assertEqual(result["isaac_validation"], "not_run")
        self.assertFalse(result["installs_performed"])
