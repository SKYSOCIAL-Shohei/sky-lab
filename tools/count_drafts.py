#!/usr/bin/env python3
"""起案された記事の本数を返す。"""
import json, os, sys
p = "work/drafts.json"
n = 0
if os.path.exists(p):
    try:
        n = len(json.load(open(p, encoding="utf-8")).get("drafts", []))
    except Exception:
        n = 0
out = os.environ.get("GITHUB_OUTPUT")
if out:
    open(out, "a", encoding="utf-8").write(
        f"count={n}\nhas_draft={'true' if n else 'false'}\n")
print(f"起案: {n}本")
