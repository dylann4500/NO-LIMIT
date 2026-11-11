import json, sys
sys.path.insert(0, ".")
if __name__ == "__main__":
    from hero import DEFAULT
    import tune
    start = dict(DEFAULT)
    start.update(json.load(open("tuned_robust.json"))["mu"])
    mu, hist = tune.cem(["typical", "strong", "aggro", "passive"], ["top3", "linear", "steep", "wta"], gens=10, tables=60, procs=10, start=start)
    json.dump({"mu": mu, "hist": hist}, open("tuned_v3.json", "w"), indent=1)
