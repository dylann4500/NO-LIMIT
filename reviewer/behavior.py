"""Behavior profile of the hero in a hand history, and a diff between two profiles.
usage: python -I behavior.py BASE_HIST CAND_HIST   (gzip JSONL, portal or local format)
Prints frequencies side by side; FLAGS any decision frequency that moved > 10 points
(n >= 150) and any VPIP/PFR outside the real-field sane band. Exit code 1 if flagged."""
import collections, gzip, json, sys


def profile(path):
    with gzip.open(path, "rt") as f:
        hdr = json.loads(f.readline()); lines = [l for l in f if not l.startswith('{"you"')]
    you = hdr["you"]; c = collections.Counter(); hands = vpip = pfr = 0
    for l in lines:
        t = json.loads(l)
        if "hands" not in t or you not in t["seats"]:
            continue
        me = t["seats"].index(you)
        for h in t["hands"]:
            sb_ = h["stacks_before"]
            if sb_[me] <= 0:
                continue
            hands += 1
            live = sum(1 for x in sb_ if x > 0)
            grp = "8-6" if live >= 6 else "5-4" if live >= 4 else "3-2"
            street = 0; raises = 0; acted = False; vp = pf = False; bet_on = False; flop_done = False
            for e in h["events"]:
                k, s = e["kind"], e.get("seat")
                if k == "board":
                    street += 1; bet_on = False; continue
                if s is None or k not in ("fold", "check", "call", "raise"):
                    continue
                if street == 0:
                    if s == me:
                        if k in ("call", "raise"): vp = True
                        if k == "raise": pf = True
                        if not acted:
                            acted = True
                            ctx = "unopened" if raises == 0 else "vs_raise" if raises == 1 else "vs_3bet"
                            a = ("jam" if e["amount"] >= sb_[me] else "raise") if k == "raise" else k
                            c[(grp, ctx, a)] += 1; c[(grp, ctx, "n")] += 1
                    if k == "raise":
                        raises += 1
                elif street == 1 and s == me and not flop_done:
                    flop_done = True
                    ctx = "flop_facing_bet" if bet_on else "flop_no_bet"
                    c[(grp, ctx, k)] += 1; c[(grp, ctx, "n")] += 1
                if street > 0 and k == "raise":
                    bet_on = True
            vpip += vp; pfr += pf
    out = {"VPIP": vpip / max(1, hands), "PFR": pfr / max(1, hands), "_hands": hands}
    for (g, ctx, a), v in c.items():
        if a != "n":
            out[f"{g} {ctx} {a}"] = (v / c[(g, ctx, "n")], c[(g, ctx, "n")])
    return out


def main():
    base, cand = profile(sys.argv[1]), profile(sys.argv[2])
    flags = []
    print(f"hands: base {base['_hands']}  cand {cand['_hands']}")
    for k in ("VPIP", "PFR"):
        print(f"  {k:28s} base {base[k]:6.1%}  cand {cand[k]:6.1%}")
    if not 0.22 <= cand["VPIP"] <= 0.35: flags.append(f"VPIP {cand['VPIP']:.0%} outside 22-35%")
    if not 0.17 <= cand["PFR"] <= 0.27: flags.append(f"PFR {cand['PFR']:.0%} outside 17-27%")
    keys = sorted(k for k in set(base) | set(cand) if not k.startswith("_") and k not in ("VPIP", "PFR"))
    for k in keys:
        b, n_b = base.get(k, (0.0, 0)); c, n_c = cand.get(k, (0.0, 0))
        mark = ""
        if min(n_b, n_c) >= 150 and abs(c - b) > 0.10:
            mark = "  <== MOVED"; flags.append(f"{k}: {b:.0%} -> {c:.0%}")
        if max(b, c) >= 0.02:
            print(f"  {k:28s} base {b:6.1%} (n={n_b:5d})  cand {c:6.1%} (n={n_c:5d}){mark}")
    print("BEHAVIOR:", "FLAGGED: " + "; ".join(flags) if flags else "OK (no unintended shifts)")
    sys.exit(1 if flags else 0)


if __name__ == "__main__":
    main()
