"""How well does a policy transfer across variants, and what does a stale table cost?
Run under POKER_VARIANT (and optionally POKER_TABLE_FROM)."""
import sys, json, os
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate
if __name__ == "__main__":
    tuned = json.load(open(sys.argv[1]))["mu"]
    H = {"tuned": dict(tuned), "default": {}, "tag": "tag", "nit": "nit", "fold": "fold"}
    P = ["top3", "steep", "linear"]
    v, t = os.environ.get("POKER_VARIANT", "holdem"), os.environ.get("POKER_TABLE_FROM", "-")
    tables = 800 if v == "omaha" else 3000
    for f in ["typical", "holdout"]:
        r, hands = evaluate(H, field=f, payouts=P, tables=tables, seed=31)
        print(f"== variant={v} table_from={t} field={f}")
        for k, row in r.items():
            print("  " + k.ljust(9) + "".join(f"{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f}  " for p in P), flush=True)
