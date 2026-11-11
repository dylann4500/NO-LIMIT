"""Omaha at rollout budgets that actually fit the 1 ms limit, plus measured time per decision."""
import json, os, sys, time, random
os.environ["POKER_VARIANT"] = "omaha"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import evaluate
import pk
if __name__ == "__main__":
    mu = json.load(open("../snap2/tuned_robust.json"))["mu"]
    samples = [random.sample(pk.DECK, 7) for _ in range(300)]
    for r in (4, 8, 16, 40):
        t = time.perf_counter()
        for s in samples:
            pk.equity_vs_range(s[:4], s[4:7], 0.3, r)
        print(f"rollouts {r}: {(time.perf_counter()-t)/300*1e6:.0f} us per equity call (flop, on a busy machine)", flush=True)
    H = {f"r{r}": dict(mu, rollouts=r) for r in (4, 8, 16, 40)}
    H["tag"] = "tag"
    r, _ = evaluate(H, field="holdout", payouts=["top3", "steep"], tables=500, procs=2, seed=11)
    for k, row in r.items():
        print(k.ljust(5), f"top3 {row['top3'][0]:6.2f}±{row['top3'][1]:4.2f}  steep {row['steep'][0]:6.2f}±{row['steep'][1]:4.2f}", flush=True)
