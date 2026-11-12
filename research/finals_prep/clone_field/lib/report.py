"""report.py [--real ACC.pkl] LABEL=OUT.pkl ...   first is the paired baseline."""
import pickle, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitlib

args = sys.argv[1:]
real = None
if args[0] == "--real":
    real = pickle.load(open(args[1], "rb"))
    args = args[2:]
runs = []
for a in args:
    lab, p = a.split("=", 1)
    d = pickle.load(open(p, "rb"))
    runs.append((lab, d))
base = {r[0]: r[2] for r in runs[0][1]["rows"]}
KS = ["vpip", "pfr", "3bet", "fold_to_3bet", "fold_to_4bet", "call_allin", "flop_bet", "flop_fold_to_bet",
      "turn_fold_to_bet", "river_fold_to_bet", "wtsd", "wsd"]
print(f"{'bot':10s} {'n':>5s} {'pts':>6s} {'se':>5s} {'d_vs_first':>10s} {'se':>5s} {'fail':>9s} {'t/s':>5s} | " + " ".join(f"{k[:9]:>9s}" for k in KS) + " | places 1-8")
if real:
    s = fitlib.style(real, "avalon")
    print(f"{'REAL':10s} {s['tables']:5d} {s['pts']:6.2f} {s['pts_se']:5.2f} {'':>10s} {'':>5s} {'':>9s} {'':>5s} | " + " ".join(f"{s[k]:9.3f}" for k in KS) + " | " + " ".join(f"{x:.3f}" for x in s["places"]))
for lab, d in runs:
    rows = d["rows"]
    n = len(rows)
    m = sum(r[2] for r in rows) / n
    se = (sum((r[2] - m) ** 2 for r in rows) / (n - 1) / n) ** 0.5
    diffs = [r[2] - base[r[0]] for r in rows if r[0] in base]
    dm = sum(diffs) / len(diffs)
    dse = (sum((x - dm) ** 2 for x in diffs) / (len(diffs) - 1) / len(diffs)) ** 0.5
    s = fitlib.style(d["acc"], "HERO")
    fl = f"{sum(r[5] for r in rows)}/{sum(r[6] for r in rows) // 1000}k"
    print(f"{lab:10s} {n:5d} {m:6.2f} {se:5.2f} {dm:+10.2f} {dse:5.2f} {fl:>9s} {n / d['elapsed']:5.1f} | " + " ".join(f"{s[k]:9.3f}" for k in KS) + " | " + " ".join(f"{x:.3f}" for x in s["places"]))
