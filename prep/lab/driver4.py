"""Exploiter-in-the-loop robust training. All environment changes stay inside __main__ and its functions,
because macOS spawned workers re-execute this module's top level."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def L(n):
    return json.load(open(n))["mu"]


def save(n, mu):
    mu = {k: v for k, v in mu.items() if k != "cls"}
    json.dump({"mu": mu}, open(n, "w"), indent=0)


def main(rounds):
    T0 = time.time()
    log = open("progress.log", "a", buffering=1)
    res = open("L1_loop.log", "a", buffering=1)
    say = lambda s: log.write(f"[{(time.time()-T0)/60:5.1f}m] {s}\n")
    import mtune, methods
    from run import evaluate
    os.environ["CAND_TABLE"] = "1"
    cur_path = "tuned_blend.json"
    pool = []
    SEARCH = dict(mtune.BASE_SEARCH)
    SEARCH.update({"eqcall_margin": (-0.05, 0.2), "vwidth_mult": (0.4, 2.5)})
    versions = [cur_path]
    for k in range(rounds + 1):
        # 1. Train an exploiter against the current defender.
        os.environ["CAND_PATH"] = cur_path
        os.environ["EXPLOIT_PATHS"] = ""
        z = {f"w_{i}_{j}": 0.0 for i in range(5) for j in range(methods.N_FEAT)}
        x, lg, used, sec = mtune.tune("cma", "linear0", methods.linear_search(3.0), {**L("tuned_blend.json"), **z}, 120000, seed=100 + k, fields=["all_mirror", "mirror"], payouts=["gym", "top3"], sig0=0.2)
        ep = f"exploit_{k}.json"
        save(ep, x)
        pool.append(ep)
        r, _ = evaluate({"exploiter": dict(x, cls="linear0"), "defender": dict(L(cur_path), cls="table")}, field="all_mirror", payouts=["gym", "top3"], tables=4000, seed=k + 1)
        print(f"round {k}: defender {cur_path}: exploiter at a table of 7 defenders gym {r['exploiter']['gym'][0]:.2f} top3 {r['exploiter']['top3'][0]:.2f}; defender itself {r['defender']['gym'][0]:.2f} (fair 31.9); trained in {sec:.0f}s", file=res)
        say(f"exploiter {k}: {r['exploiter']['gym'][0]:.2f}")
        if k == rounds:
            break
        # 2. Retune the defender with the exploiter pool in the field.
        os.environ["EXPLOIT_PATHS"] = ",".join(pool)
        start = {**L(cur_path), "eqcall": 1.0}
        start.setdefault("width_cap", 2.2); start.setdefault("call_odds", 0.1); start.setdefault("hu_defend", 0.0)
        start.setdefault("eqcall_margin", 0.04); start.setdefault("vwidth_mult", 1.2)
        d, lg, used, sec = mtune.tune("cma", "table", SEARCH, start, 150000, seed=200 + k, fields=["typical", "strong", "aggro", "all_mirror", "mirror", "exploit_mix", "exploit_soft", "runover"], payouts=mtune.ALLP, sig0=0.1)
        cur_path = f"tuned_robust{k+1}.json"
        save(cur_path, d)
        versions.append(cur_path)
        say(f"defender {k+1} {sec:.0f}s")
    say("LOOP DONE")


def final():
    log = open("progress.log", "a", buffering=1)
    from run import evaluate
    H = {"blend": dict(L("tuned_blend.json"), cls="table")}
    for n in (1, 2, 3):
        if os.path.exists(f"tuned_robust{n}.json"):
            H[f"robust{n}"] = dict(L(f"tuned_robust{n}.json"), cls="table")
    H["tag"] = "tag"
    P = ["gym", "top3", "linear", "wta"]
    os.environ["CAND_TABLE"] = "1"
    last = "tuned_robust%d.json" % max(n for n in (1, 2, 3) if os.path.exists(f"tuned_robust{n}.json"))
    os.environ["EXPLOIT_PATHS"] = ",".join(f"exploit_{k}.json" for k in range(4) if os.path.exists(f"exploit_{k}.json"))
    with open("L2_final.log", "w", buffering=1) as f:
        for fld, cand in [("holdout", last), ("holdout_soft", last), ("stress_mix", last), ("stress_3bet", last), ("typical", last), ("strong", last),
                          ("mirror", "tuned_blend.json"), ("mirror", last), ("all_mirror", "tuned_blend.json"), ("all_mirror", last), ("runover", last), ("exploit_soft", last)]:
            os.environ["CAND_PATH"] = cand
            r, _ = evaluate(H, field=fld, payouts=P, tables=6000, seed=4242)
            print(f"\n== field={fld} cand={cand}\n" + "".ljust(10) + "".join(p.rjust(14) for p in P), file=f)
            for k, row in r.items():
                print(k.ljust(10) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in P), file=f)
    log.write("FINAL DONE\n")


if __name__ == "__main__":
    main(int(sys.argv[1]))
    final()
