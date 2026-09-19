"""Dependency-free acceptance rules for recorded hover-learning evaluations."""
import math

from .contracts import ValidationError, finite

CONTROL_DT = 0.02
EPISODE_SECONDS = 10.0
EVALUATION_SEEDS = tuple(range(10000, 10020))
VALIDATION_SEEDS = tuple(range(500, 520))


def assess_hover(rows, failed):
    """A failure or incomplete episode cannot pass, including after an auto-reset."""
    if type(failed) is not bool or not isinstance(rows, list) or not rows:
        raise ValidationError("invalid hover evaluation")
    for index, row in enumerate(rows):
        if (not isinstance(row, list) or len(row) != 14
                or not all(finite(v) for v in row)
                or abs(row[0] - index * CONTROL_DT) > 1e-6):
            raise ValidationError("invalid hover sample or time sequence")
    if len(rows) > 501:
        raise ValidationError("hover evaluation is longer than the fixed episode")
    errors = [math.dist(row[1:4], (0.0, 0.0, 1.5)) for row in rows]
    complete = len(rows) == 501
    final_max = max(errors[400:]) if complete else None
    return {"failed_termination": failed, "complete": complete,
            "position_rmse_m": math.sqrt(sum(e*e for e in errors) / len(errors)),
            "final_two_seconds_max_error_m": final_max,
            "success": complete and not failed and final_max <= 0.30}
