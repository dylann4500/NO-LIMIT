"""Round-to-round protocols through a simulated T1-T6 whose field improves. Environment changes stay inside functions."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HID = {1: ("early_buggy", "tuned_blend.json"), 2: ("typical", "tuned_blend.json"), 3: ("strong", "tuned_blend.json"), 4: ("stress_mix", "tuned_robust3.json"), 5: ("mirror", "tuned_meta1.json"), 6: ("hidden", "tuned_robust2.json")}
def L(n): return json.load(open(n))["mu"]
def save(n, mu): json.dump({"mu": {k: v for k, v in mu.items() if k != "cls"}}, open(n, "w"), indent=0)

def main():
    import mtune
    from run import evaluate
    T0 = time.time()
    plog = open("progress.log", "a", buffering=1)
    lf = open("P_protocols.log", "a", buffering=1)
    os.environ["CAND_TABLE"] = "1"
    os.environ["EXPLOIT_PATHS"] = "exploit_0.json,exploit_1.json,exploit_2.json,exploit_3.json"
    SEARCH = dict(mtune.BASE_SEARCH)
    SEARCH.update({"eqcall_margin": (-0.05, 0.25), "vwidth_mult": (0.3, 2.5)})
    FLD = ["typical", "strong", "aggro", "all_mirror", "mirror", "exploit_soft", "runover"]
    def score(mu, t, seed):
        f, c = HID[t]
        os.environ["CAND_PATH"] = c
        r, _ = evaluate({"x": dict(mu, cls="table")}, field=f, payouts=["gym"], tables=5000, seed=seed)
        return r["x"]["gym"][0]
    for seed in (1, 2):
        for proto in ["frozen", "refresh", "league", "lastfield", "gated"]:
            cur = L("tuned_final.json"); hist = []; scores = []
            path = f"pv_{proto}_{seed}_0.json"; save(path, cur); hist.append(path)
            for t in range(1, 7):
                scores.append(score(cur, t, seed * 100 + t))
                if t == 6 or proto == "frozen":
                    continue
                if proto == "league":
                    os.environ["CAND_LEAGUE"] = ",".join(hist); os.environ["CAND_PATH"] = hist[-1]
                    flds = ["typical", "strong", "aggro", "all_league", "league_mix", "exploit_soft", "runover"]
                elif proto == "lastfield":
                    os.environ["CAND_PATH"] = HID[t][1]
                    flds = [HID[t][0], HID[t][0], "typical", "exploit_soft"]
                else:
                    os.environ["CAND_PATH"] = hist[-1]
                    flds = FLD
                x, log, used, sec = mtune.tune("cma", "table", SEARCH, cur, 30000, seed=seed * 10 + t, fields=flds, payouts=["gym", "top3", "steep"], sig0=0.06)
                x.pop("cls", None)
                if proto == "gated":
                    os.environ["CAND_PATH"] = hist[-1]
                    keep = 0.0
                    for f in ["holdout", "stress_mix"]:
                        r, _ = evaluate({"new": dict(x, cls="table"), "old": dict(cur, cls="table")}, field=f, payouts=["gym"], tables=4000, seed=t * 7 + seed)
                        keep += r["new"]["gym"][0] - r["old"]["gym"][0]
                    if keep < 0:
                        x = cur
                cur = x
                path = f"pv_{proto}_{seed}_{t}.json"; save(path, cur); hist.append(path)
            w = sum((i + 1) * s for i, s in enumerate(scores)) / 21.0
            print(f"seed {seed} {proto:10} weighted {w:6.2f}  rounds {[round(s,1) for s in scores]}", file=lf)
            plog.write(f"[{(time.time()-T0)/60:5.1f}m] protocol {proto} seed {seed} weighted {w:.2f}\n")
    plog.write("PROTOCOLS DONE\n")

if __name__ == "__main__":
    main()
