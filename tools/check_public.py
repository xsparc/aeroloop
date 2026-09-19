"""Check tracked source for private paths, contact emails and credential material."""
from pathlib import Path
import re
import subprocess

PATTERNS = {
    "private user path": re.compile(r"(?i)(?:[a-z]:[\\/](?:Users|Documents and Settings)[\\/][^\s\"']+|/(?:home|Users)/[^/\s]+/)"),
    "contact email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@(?!users\.noreply\.github\.com\b)[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})\b"),
}


def scan(text):
    return [name for name, pattern in PATTERNS.items() if pattern.search(text)]


def main():
    root = Path(__file__).resolve().parents[1]
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    findings = []
    for name in filter(None, paths):
        path = root / name
        if not path.is_file():
            continue
        if path.is_symlink() or name.startswith((".local/", ".ai/", ".venv/", "runs/")) or path.suffix in (".zip", ".ulg", ".pt", ".pth", ".dll") or path.name.startswith(".env"):
            findings.append(f"{name}: private artifact must not be tracked")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"{name}: binary requires explicit source review")
            continue
        findings.extend(f"{name}: {category}" for category in scan(content))
    print("\n".join(findings) if findings else "Public source checks: passed")
    return bool(findings)


if __name__ == "__main__":
    raise SystemExit(main())
