"""Q2b: equity of the hands we folded heads-up to a first bet (flop/turn/river) vs a villain range built from the
field's own called-bet showdowns, and (Q4) how opponents respond to a bet from exposed vs hidden top pair.

Villain range for a fold: exposed card E known; hidden card H drawn from the unseen deck, reweighted so the class
mix of (E,H)+board matches the field's showdown class mix for bettors that were called on that street with the
same exposure type (vtype: 0 exposed card unpaired, 1 pairs top board rank, 2 pairs a lower rank).
Showdown-selected ranges under-represent abandoned bluffs (our equity is understated); raw equity ignores
future betting/realization (overstated). Also reported vs a uniform hidden card ("bets any hidden card").
Call EV (chips, check-down assumption) = eq*(P+2b) - b.
usage: python -I q2b.py HANDS.gz OUTPREFIX [nproc]"""
import collections, gzip, json, os, pickle, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval7  # noqa: E402
from extract import hand_class, pairs, card, size_bucket  # noqa: E402

RANKS = "23456789TJQKA"; RK = {r: i for i, r in enumerate(RANKS)}
DECK = [r + s for r in RANKS for s in "shdc"]
CLS = ["air", "fd", "weak", "top", "over", "strong"]
G = {}


def vtype(E, board):
    br = [c[0] for c in board]
    if E[0] not in br:
        return 0
    return 1 if RK[E[0]] == max(RK[r] for r in br) else 2


def init(you):
    G["you"] = you


def work(pair):
    tl, yl = pair
    t = json.loads(tl); y = json.loads(yl)["you"]; me = y["seat"]; N = len(t["seats"])
    kept = {e["hand"]: e["cards"] for e in y["private_events"] if e["kind"] == "kept"}
    disc = {e["hand"]: e["cards"] for e in y["private_events"] if e["kind"] == "discarded"}
    SDc = collections.Counter(); RESP = collections.Counter(); spots = []
    for h in t["hands"]:
        sb_, sa = h["stacks_before"], h["stacks_after"]; bb = h["blinds"][1] or 1
        alive = [i for i in range(N) if sb_[i] > 0]
        shown = {e["seat"]: e["cards"] for e in h["events"] if e["kind"] == "show" and e.get("cards")}
        com = [0] * N; st = [0] * N; cur = 0; street = 0; board = []; folded = set(); exposed = {}
        pending = None; called = []
        for e in h["events"]:
            k = e["kind"]; s = e.get("seat")
            if k == "board":
                street += 1; board = board + (e.get("cards") or []); st = [0] * N; cur = 0; pending = None; continue
            if k == "reveal" and e.get("cards"):
                exposed[s] = e["cards"][0]; continue
            if k == "blind":
                com[s] += e["amount"]; st[s] += e["amount"]; cur = max(cur, st[s]); continue
            if k not in ("fold", "check", "call", "raise"):
                continue
            if pending is not None and s == pending["target"]:
                p = pending; pending = None
                if k != "check":
                    resp = "fold" if k == "fold" else ("call" if k == "call" else "raise")
                    b, P, bettor = p["b"], p["P"], p["bettor"]
                    # Q4: bettor's exposed card vs top pair
                    if p["street"] == 1:
                        if bettor == me and kept.get(h["hand"]) and hand_class(kept[h["hand"]], board) == "top":
                            RESP[("us_hidden_top", resp)] += 1
                        elif bettor != me and bettor in exposed and vtype(exposed[bettor], board) == 1:
                            RESP[("field_exposed_top", resp)] += 1
                    if resp == "call":
                        called.append((bettor, p["street"], list(board), exposed.get(bettor)))
                    if s == me and resp == "fold" and kept.get(h["hand"]) and bettor in exposed:
                        others = [c for i, c in exposed.items() if i not in (me, bettor)]
                        spots.append(dict(street=p["street"], kc=kept[h["hand"]], dc=disc.get(h["hand"], []), board=list(board),
                                          E=exposed[bettor], others=others, P=P, b=b, bb=bb, vt=vtype(exposed[bettor], board),
                                          cls=hand_class(kept[h["hand"]], board), sizeb=size_bucket(b / P if P else None)))
            if k == "fold":
                folded.add(s)
            elif k == "call":
                com[s] += e["amount"]; st[s] += e["amount"]
            elif k == "raise":
                P_before = sum(com); inc = e["amount"] - st[s]
                others_bet = sum(1 for i, v in enumerate(st) if i != s and v > 0)
                com[s] += inc; st[s] = e["amount"]; cur = max(cur, e["amount"])
                live = [i for i in alive if i not in folded]
                if street > 0 and len(live) == 2 and others_bet == 0:
                    tg = [i for i in live if i != s][0]
                    if com[tg] < sb_[tg]:
                        pending = dict(bettor=s, target=tg, street=street, P=P_before, b=inc)
        for bettor, stv, bd, E in called:
            if bettor in shown and len(shown[bettor]) == 2 and E:
                SDc[(stv, vtype(E, bd), hand_class(shown[bettor], bd))] += 1
    return SDc, RESP, spots


def mc(args):
    sp, pemp = args
    board = sp["board"]; E = sp["E"]
    dead = set(sp["kc"]) | set(sp["dc"]) | set(board) | {E} | set(sp["others"])
    cand = [c for c in DECK if c not in dead]
    cl = {H: hand_class([E, H], board) for H in cand}
    cnt = collections.Counter(cl.values())
    pe = pemp.get((sp["street"], sp["vt"]), {})
    tot = sum(pe.get(c, 0) for c in cnt)
    hero = [card(c) for c in sp["kc"]]; bc = [card(c) for c in board]
    out = {}
    for nm in ("emp", "uni"):
        if nm == "emp" and tot > 0:
            rng = [((card(E), card(H)), pe.get(cl[H], 0) / tot / cnt[cl[H]]) for H in cand if pe.get(cl[H], 0) > 0]
        else:
            rng = [((card(E), card(H)), 1.0) for H in cand]
        if len(board) == 5:
            hv = eval7.evaluate(hero + bc); w = s = 0.0
            for (a, b2), wt in rng:
                vv = eval7.evaluate([a, b2] + bc)
                s += wt * (1.0 if hv > vv else 0.5 if hv == vv else 0.0); w += wt
            out[nm] = s / w
        else:
            out[nm] = eval7.py_hand_vs_range_monte_carlo(hero, rng, bc, 600)
    P, b = sp["P"], sp["b"]
    return dict(street=sp["street"], vt=sp["vt"], cls=sp["cls"], sizeb=sp["sizeb"], odds=b / (P + 2 * b),
                eq_emp=out["emp"], eq_uni=out["uni"], ev_emp=(out["emp"] * (P + 2 * b) - b) / sp["bb"],
                ev_uni=(out["uni"] * (P + 2 * b) - b) / sp["bb"])


def main():
    path, out = sys.argv[1], sys.argv[2]; nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    with gzip.open(path, "rt") as f:
        hdr = json.loads(f.readline())
    SD = collections.Counter(); RESP = collections.Counter(); SP = []; nt = 0
    with Pool(nproc, initializer=init, initargs=(hdr["you"],)) as p:
        for sd, rs, sp in p.imap_unordered(work, pairs(path, 0), chunksize=8):
            SD.update(sd); RESP.update(rs); SP.extend(sp); nt += 1
    pemp = collections.defaultdict(dict)
    for (stv, vt, c), n in SD.items():
        pemp[(stv, vt)][c] = pemp[(stv, vt)].get(c, 0) + n
    print(f"{nt} tables; field called-bet showdown class mix by (street, exposure type):")
    for key in sorted(pemp):
        tot = sum(pemp[key].values())
        print(f"  street {key[0]} vtype {key[1]} n={tot:6d}: " + " ".join(f"{c} {pemp[key].get(c,0)/tot:5.1%}" for c in CLS))
    print("Q4: opponent response to a HU flop first bet:")
    for grp in ("us_hidden_top", "field_exposed_top"):
        tot = sum(v for (g, r), v in RESP.items() if g == grp)
        print(f"  {grp:18s} n={tot:6d} " + " ".join(f"{r} {RESP[(grp, r)]/tot:5.1%}" for r in ("fold", "call", "raise")))
    with Pool(nproc) as p:
        R = p.map(mc, [(s, dict(pemp)) for s in SP], chunksize=64)
    pickle.dump({"R": R, "pemp": dict(pemp), "RESP": dict(RESP), "nt": nt}, open(out + "_q2b.pkl", "wb"))
    import pandas as pd
    d = pd.DataFrame(R)
    d["call_emp"] = d.eq_emp > d.odds; d["call_uni"] = d.eq_uni > d.odds
    print(f"\nour HU folds to a first bet: n={len(d)} ({len(d)/nt:.2f}/table)")
    g = d.groupby(["street", "vt", "cls"]).agg(n=("odds", "size"), odds=("odds", "mean"), eq_emp=("eq_emp", "mean"), eq_uni=("eq_uni", "mean"),
                                              share_eq_gt_odds=("call_emp", "mean"), ev_emp_bb=("ev_emp", "mean"), ev_uni_bb=("ev_uni", "mean"))
    g["ev_emp_bb_per_table"] = g["n"] * g["ev_emp_bb"] / nt
    print(g[g.n >= 100].round(3).to_string())
    for stv in (1, 2, 3):
        x = d[d.street == stv]
        pos = x[x.ev_emp > 0]
        print(f"street {stv}: folds {len(x)}, eq>odds (emp range) {x.call_emp.mean():.1%}, sum positive call EV {pos.ev_emp.sum()/nt:+.2f} bb/table, "
              f"net call EV if all called {x.ev_emp.sum()/nt:+.2f} bb/table; uniform-hidden range eq>odds {x.call_uni.mean():.1%}")


if __name__ == "__main__":
    main()
