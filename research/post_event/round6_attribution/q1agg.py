"""Aggregate cells for the write-up: non-SB opens with 10-45% hands, multiway weak/air flop+turn calls, flats with 45%+ hands.
usage: python -I q1agg.py r6 r5"""
import sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from analyze2 import prep, summ  # noqa: E402
for p in sys.argv[1:]:
    d = prep(p); nt = d.tid.nunique()
    cells = {
        "open 10-45% not SB": (d.cls == "PF open") & d.pct.between(0.10, 0.45) & (d.pos != "SB"),
        "open 10-45% not SB, 3-6 alive": (d.cls == "PF open") & d.pct.between(0.10, 0.45) & (d.pos != "SB") & d.alive.between(3, 6),
        "multiway flop/turn call weak/air": d.cls.isin(["Flop call", "Turn call"]) & (d.nopp > 1) & d.hcls.isin(["weak", "air"]),
        "flat 45%+": (d.cls == "PF flat (non-BB)") & (d.pct >= 0.45),
        "BB defense all (call/3bet/jam)": d.cls.isin(["PF BB defend call", "PF BB 3-bet", "PF BB jam vs open"]),
        "HU call-jam at 2 alive": (d.cls == "PF call-jam") & (d.alive == 2),
    }
    print(f"\n{p}")
    for k, m in cells.items():
        s = summ(d[m], nt, "adj")
        u = d[m]["d"].mean()
        print(f"  {k:34s} n={int(s.n):7d} adj {s['mean']:+.3f} [{s.lo:+.3f},{s.hi:+.3f}] unadj {u:+.3f}  per table {s.per_table:+.3f} [{s.pt_lo:+.3f},{s.pt_hi:+.3f}]")
