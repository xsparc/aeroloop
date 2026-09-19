"""World ENU/body FLU, quaternion wxyz (body to world), SI units."""
import math
from .contracts import ValidationError, finite


def vector(values, size=3):
    if not isinstance(values, (tuple, list)) or len(values) != size or not all(finite(v) for v in values):
        raise ValidationError("invalid finite vector")
    return tuple(float(v) for v in values)


def ned_to_enu(values):
    n, e, d = vector(values)
    return e, n, -d


def frd_to_flu(values):
    f, r, d = vector(values)
    return f, -r, -d


def multiply(a, b):
    w, x, y, z = a
    v, i, j, k = b
    return (w*v-x*i-y*j-z*k, w*i+x*v+y*k-z*j,
            w*j-x*k+y*v+z*i, w*k+x*j-y*i+z*v)


def normalize(q):
    q = vector(q, 4)
    norm = math.hypot(*q)
    if norm < 1e-12 or not math.isfinite(norm):
        raise ValidationError("degenerate quaternion")
    return tuple(v / norm for v in q)


def rotate(q, v):
    q = normalize(q)
    v = vector(v)
    return multiply(multiply(q, (0, *v)), (q[0], -q[1], -q[2], -q[3]))[1:]


def ned_frd_to_enu_flu(q):
    root = math.sqrt(0.5)
    return normalize(multiply(multiply((0, root, root, 0), normalize(q)), (0, 1, 0, 0)))
