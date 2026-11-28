#!/usr/bin/env python3
"""Dependency audit gate (#83). Fails on high/critical findings that are not in
.github/security/audit-exceptions.json (or whose exception has expired).

  audit.py npm <dir>          npm audit --json (needs package-lock.json)
  audit.py dotnet <proj>      dotnet list package --vulnerable --include-transitive
  audit.py pip [pip-audit args...]   pip-audit; any known vulnerability fails
                              (PyPI advisories carry no severity, so none is ignored unless excepted)
"""
import datetime, json, pathlib, re, subprocess, sys

EXC = pathlib.Path(__file__).resolve().parents[2] / ".github/security/audit-exceptions.json"
BLOCKING = {"high", "critical"}


def exceptions():
    today = datetime.date.today().isoformat()
    ok, expired = set(), []
    for e in json.loads(EXC.read_text())["exceptions"]:
        (ok.add(e["id"]) if e["expires"] >= today else expired.append(e["id"]))
    return ok, expired


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def finish(findings, tool):
    ok, expired = exceptions()
    bad = [f for f in findings if f[0] not in ok]
    for i in expired:
        print(f"note: exception {i} has expired")
    for f in findings:
        print(("EXCEPTED " if f[0] in ok else "BLOCKING ") + " | ".join(f))
    if bad:
        print(f"FAIL: {len(bad)} unexcepted blocking finding(s) in {tool}")
        sys.exit(1)
    print(f"OK: {tool}: no unexcepted high/critical findings ({len(findings)} excepted)")


def npm(d):
    r = run(["npm", "audit", "--json"], cwd=d)
    data = json.loads(r.stdout)
    if "vulnerabilities" not in data:
        print(r.stdout, r.stderr); sys.exit(2)
    meta = data["metadata"]["vulnerabilities"]
    print(f"npm audit {d}: {meta}")
    findings = []
    for name, v in data["vulnerabilities"].items():
        for via in v["via"]:
            if isinstance(via, dict) and via.get("severity") in BLOCKING:
                gid = via["url"].rsplit("/", 1)[-1]
                findings.append((gid, via["severity"], name, via["title"]))
    finish(findings, f"npm {d}")


def dotnet(proj):
    r = run(["dotnet", "list", proj, "package", "--vulnerable", "--include-transitive"])
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr); sys.exit(2)
    findings = []
    for line in r.stdout.splitlines():
        m = re.search(r">\s+(\S+).*?\s(High|Critical)\s+(https?://\S+)", line)
        if m:
            findings.append((m.group(3).rsplit("/", 1)[-1], m.group(2).lower(), m.group(1), "nuget"))
    finish(findings, f"dotnet {proj}")


def pip(args):
    r = run(["pip-audit", "--format", "json", *args])
    try:
        data = json.loads(r.stdout)
    except ValueError:
        print(r.stdout, r.stderr); sys.exit(2)
    findings = [(v["id"], "n/a", d["name"] + " " + d["version"], "pip") for d in data["dependencies"] for v in d.get("vulns", [])]
    finish(findings, "pip-audit")


if __name__ == "__main__":
    {"npm": lambda: npm(sys.argv[2]), "dotnet": lambda: dotnet(sys.argv[2]), "pip": lambda: pip(sys.argv[2:])}[sys.argv[1]]()
