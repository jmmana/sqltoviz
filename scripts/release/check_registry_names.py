#!/usr/bin/env python3
"""Query the public PyPI / npm / NuGet registries for the SqlToViz package names (#99).

Read-only HTTP GETs. A 404 only proves the name is not *publicly visible at check time*.
It does NOT prove reservation, scope/org control, trusted-publisher setup or ownership;
those can only be verified in each registry's account settings by the maintainer.
Usage: check_registry_names.py [--json]
"""
import json, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

VERSION = "0.1.0a1"
NPM_VERSION = "0.1.0-alpha.1"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sqltoviz-release-check"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # network failure is reported, never treated as "available"
        return f"ERROR {type(e).__name__}", b""


def main():
    checks = []

    def add(registry, what, url):
        status, body = get(url)
        checks.append({"registry": registry, "check": what, "url": url, "status": status, "body": body})
        return status, body

    # exact project names
    add("PyPI", "project sqltoviz", "https://pypi.org/pypi/sqltoviz/json")
    add("PyPI", f"release sqltoviz=={VERSION}", f"https://pypi.org/pypi/sqltoviz/{VERSION}/json")
    for alt in ("sql-to-viz", "sqlviz", "sqltoviz-core"):
        add("PyPI", f"look-alike {alt}", f"https://pypi.org/pypi/{alt}/json")
    add("npm", "@sqltoviz/core", "https://registry.npmjs.org/@sqltoviz%2fcore")
    add("npm", f"@sqltoviz/core@{NPM_VERSION}", f"https://registry.npmjs.org/@sqltoviz%2fcore/{NPM_VERSION}")
    add("npm", "unscoped sqltoviz", "https://registry.npmjs.org/sqltoviz")
    s, b = add("npm", "search scope:sqltoviz", "https://registry.npmjs.org/-/v1/search?text=scope:sqltoviz&size=20")
    for pid in ("sqltoviz", "sqltoviz.onnx"):
        add("NuGet", f"package id {pid}", f"https://api.nuget.org/v3-flatcontainer/{pid}/index.json")
    add("NuGet", "search q=sqltoviz", "https://azuresearch-usnc.nuget.org/query?q=sqltoviz&take=20&prerelease=true")

    # derived facts for the search endpoints
    for c in checks:
        if c["status"] == 200 and "search" in c["check"]:
            try:
                d = json.loads(c["body"])
                if c["registry"] == "npm":
                    c["hits"] = [o["package"]["name"] for o in d.get("objects", [])]
                else:
                    c["hits"] = [o["id"] for o in d.get("data", [])]
            except Exception:
                c["hits"] = "unparseable"
        c.pop("body")

    out = {"checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "checks": checks}
    if "--json" in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        print(f"Checked at {out['checked_at_utc']}")
        for c in checks:
            extra = f"  hits={c['hits']}" if "hits" in c else ""
            print(f"{c['registry']:6} {str(c['status']):>6}  {c['check']}{extra}")
    errs = [c for c in checks if str(c["status"]).startswith("ERROR")]
    return 2 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
