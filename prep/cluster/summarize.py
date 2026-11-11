"""One line per finished job: holdout and stress scores before and after tuning, and the verdict.
usage: .venv/bin/python cluster/summarize.py"""
import glob, os, re
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
print(f"{'job':<28} {'holdout old':>11} {'new':>7} {'stress old':>10} {'new':>7}  verdict")
for log in sorted(glob.glob(os.path.join(OUT, "*.log"))):
    t = open(log).read()
    r = {m[0]: (float(m[1]), float(m[2])) for m in re.findall(r"^(\w+)\s+old\s+([\d.]+)±[\d.]+\s+new\s+([\d.]+)", t, re.M)}
    h, s = r.get("holdout", (0, 0)), r.get("stress_mix", (0, 0))
    v = "promote" if "VERDICT: promote" in t else "keep old" if "KEEP OLD" in t else "running/failed"
    print(f"{os.path.basename(log)[:-4]:<28} {h[0]:>11.2f} {h[1]:>7.2f} {s[0]:>10.2f} {s[1]:>7.2f}  {v}")
