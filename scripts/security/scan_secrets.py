#!/usr/bin/env python3
"""Lightweight secret scan over tracked files (#83) - a fast first line, complementary to gitleaks (full git history).
Pattern-based, so it can miss secrets (limitations in docs/security.md). Exit 1 on any hit."""
import pathlib, re, subprocess, sys

PATTERNS = {
    "private key block": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----",
    "AWS access key id": r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "GitHub token": r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{50,}\b",
    "npm token": r"\bnpm_[A-Za-z0-9]{36}\b",
    "PyPI token": r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,}",
    "NuGet API key": r"\boy2[a-z0-9]{43}\b",
    "Slack token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "Google API key": r"\bAIza[0-9A-Za-z_-]{35}\b",
    "generic assignment": r"(?i)\b(?:api[_-]?key|secret|passwd|password|token)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{20,}['\"]",
}
ALLOW = "secret-scan: allow"  # inline marker for reviewed false positives
root = pathlib.Path(__file__).resolve().parents[2]
files = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True).stdout.split("\0")
hits = []
for f in filter(None, files):
    p = root / f
    if f.endswith((".onnx", ".png", ".jpg", ".svg", ".woff2", ".lock")) or p.stat().st_size > 2_000_000 or f.endswith("scan_secrets.py"):
        continue
    try:
        text = p.read_text(errors="strict")
    except (UnicodeDecodeError, OSError):
        continue
    for n, line in enumerate(text.splitlines(), 1):
        if ALLOW in line:
            continue
        for name, rx in PATTERNS.items():
            if re.search(rx, line):
                hits.append(f"{f}:{n}: {name}")
print("\n".join(hits) or "no pattern matches in tracked files")
sys.exit(1 if hits else 0)
