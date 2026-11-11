"""Does tunable price-aware defense help in the tournament format, not just against Slumbot?
Local heads-up pools cannot show this alone, so include min-raising opponents."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["CAND_PATH"] = "tuned_blend.json"; os.environ["CAND_TABLE"] = "1"
from run import evaluate
if __name__ == "__main__":
    b = json.load(open("tuned_blend.json"))["mu"]
    H = {"blend": dict(b, cls="table")}
    for d in (0.2, 0.4, 0.6):
        H[f"hu_def_{d}"] = dict(b, cls="table", hu_defend=d)
    H["odds_0.5"] = dict(b, cls="table", call_odds=0.5)
    H["odds_1.0"] = dict(b, cls="table", call_odds=1.0)
    H["odds1_hu.5"] = dict(b, cls="table", call_odds=1.0, hu_defend=0.5)
    P = ["gym", "top3", "linear", "wta"]
    for f in ["holdout", "stress_mix", "mirror", "all_mirror"]:
        r, _ = evaluate(H, field=f, payouts=P, tables=3000, procs=2, seed=77)
        print(f"== {f}")
        for k, row in r.items():
            print("  " + k.ljust(12) + "".join(f"{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
