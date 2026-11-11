#!/usr/bin/env python3
"""Rebuild the workspace from the prompt document. usage: python3 extract.py BUILD_PROMPT.md <target_dir>"""
import os, re, sys
doc, out = sys.argv[1], sys.argv[2]
text = open(doc, encoding="utf-8").read()
n = 0
for m in re.finditer(r"<!-- FILE: (\S+) -->\n````[a-z]*\n(.*?)\n````", text, flags=re.S):
    path = os.path.join(out, m.group(1))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(m.group(2) + "\n")
    if path.endswith(".sh"):
        os.chmod(path, 0o755)
    n += 1
print(f"wrote {n} files under {out}")
