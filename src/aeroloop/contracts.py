"""Strict configuration primitives shared by tools and evidence readers."""
import json
import math
import re
from pathlib import Path


class ValidationError(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key")
        result[key] = value
    return result


def load_json(path, limit=32 * 1024 * 1024):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValidationError("JSON exceeds size limit")
    return json.loads(data, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValidationError("non-finite JSON number")))


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_lock(lock):
    if not isinstance(lock, dict) or set(lock) != {"schema_version", "profiles"} or type(lock["schema_version"]) is not int or lock["schema_version"] != 1:
        raise ValidationError("unsupported lock schema")
    if not isinstance(lock["profiles"], dict) or set(lock["profiles"]) != {"cpu", "isaac"}:
        raise ValidationError("lock requires cpu and isaac profiles")
    for profile in lock["profiles"].values():
        if not isinstance(profile, dict) or set(profile) != {"status", "versions", "evidence"}:
            raise ValidationError("invalid profile fields")
        if profile["status"] not in ("candidate", "validated", "blocked"):
            raise ValidationError("invalid compatibility status")
        if not isinstance(profile["versions"], dict) or not profile["versions"]:
            raise ValidationError("versions must be a nonempty object")
        if not all(re.fullmatch(r"[a-z0-9_-]+", k) and isinstance(v, str) and re.fullmatch(r"[a-zA-Z0-9_.+-]{1,80}", v) for k, v in profile["versions"].items()):
            raise ValidationError("invalid version identifier")
        if not isinstance(profile["evidence"], list):
            raise ValidationError("evidence must be a list")
        for ref in profile["evidence"]:
            if not isinstance(ref, str) or not re.fullmatch(r"docs/[a-zA-Z0-9_./-]+", ref) or ".." in ref:
                raise ValidationError("unsafe evidence reference")
        if profile["status"] == "validated" and not profile["evidence"]:
            raise ValidationError("validated profile requires evidence")
    return lock
