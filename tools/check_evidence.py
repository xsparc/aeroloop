"""Validate AeroLoop traceability, references, status and review freshness."""
import argparse
from datetime import date
from pathlib import Path, PurePosixPath
import tomllib


def check(root, as_of):
    data = tomllib.loads((root / "docs/governance/project-evidence.toml").read_text())
    errors = []
    if data.get("schema_version") != 1 or data.get("project") != "aeroloop":
        errors.append("invalid registry identity")
    if data.get("authority", {}).get("dhf_is_authoritative") is not False:
        errors.append("evidence index must be derived")
    if date.fromisoformat(data["review"]["review_due"]) < as_of:
        errors.append("review overdue")
    objective_ids = {r["id"] for r in data["objectives"]}
    requirement_ids = {r["id"] for r in data["requirements"]}
    for group in ("objectives", "requirements", "work_items", "research_decisions"):
        ids = set()
        for record in data.get(group, []):
            identity = record["id"]
            if identity in ids:
                errors.append("duplicate record id")
            ids.add(identity)
            refs = [v for k, v in record.items() if k.endswith("_refs")]
            if "decision_ref" in record:
                refs.append([record["decision_ref"]])
            for items in refs:
                for item in items:
                    path = PurePosixPath(item)
                    resolved = (root / item).resolve()
                    if path.is_absolute() or ".." in path.parts or "\\" in item or ":" in item or not resolved.is_relative_to(root) or not resolved.is_file():
                        errors.append(f"{identity}: unsafe or missing reference")
            if group == "requirements":
                if record["status"] not in ("planned", "implemented", "deferred", "retired"):
                    errors.append(f"{identity}: invalid requirement status")
                if not set(record["objective_ids"]) <= objective_ids:
                    errors.append(f"{identity}: missing objective")
                if record["status"] == "implemented":
                    for key in ("implementation_refs", "verification_refs", "validation_refs", "risk_refs"):
                        if not record.get(key):
                            errors.append(f"{identity}: missing {key}")
            if group == "work_items":
                if not set(record["requirement_ids"]) <= requirement_ids:
                    errors.append(f"{identity}: missing requirement")
                if record["status"] in ("in-progress", "verified", "closed") and not record.get("approval_ref"):
                    errors.append(f"{identity}: missing approval")
                if record["status"] in ("verified", "closed") and not record.get("evidence_refs"):
                    errors.append(f"{identity}: missing evidence")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    failures = check(Path(__file__).resolve().parents[1], args.as_of)
    print("\n".join(failures) if failures else "Evidence index: passed")
    raise SystemExit(bool(failures))
