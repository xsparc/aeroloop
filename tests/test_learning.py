import unittest

from aeroloop.contracts import ValidationError
from aeroloop.learning import assess_hover


def recording():
    return [[i * 0.02, 0, 0, 1.5, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0] for i in range(501)]


class LearningAcceptanceTests(unittest.TestCase):
    def test_final_window_includes_start_and_end(self):
        rows = recording()
        self.assertTrue(assess_hover(rows, False)["success"])
        for index in (400, 500):
            bad = recording()
            bad[index][1] = 0.31
            self.assertFalse(assess_hover(bad, False)["success"])

    def test_incomplete_and_failed_trials_cannot_pass(self):
        self.assertFalse(assess_hover(recording()[:-1], False)["success"])
        self.assertFalse(assess_hover(recording(), True)["success"])

    def test_bad_time_or_nonfinite_samples_rejected(self):
        for column, value in ((0, 0.031), (1, float("nan"))):
            rows = recording()
            rows[1][column] = value
            with self.assertRaises(ValidationError):
                assess_hover(rows, False)


if __name__ == "__main__":
    unittest.main()
