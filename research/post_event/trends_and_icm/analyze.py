"""Per-table extraction for one round file (avalon's seat). Parallel: worker k handles pairs k, k+W, ...
usage: python -I analyze.py HANDS.jsonl.gz OUT.pkl [WORKERS=6]
Writes a pickle: {"head": {...}, "tables": [per-table dict], "checks": Counter, "examples": {...}}."""
import collections, gzip, json, os, pickle, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icm

RANKS = "23456789TJQKA"; SUITS = "shdc"
from itertools import permutations
PERMS = [dict(zip(SUITS, p)) for p in permutations(SUITS)]
TABLES = "/Users/dylan/Documents/GitHub/nolimit-live/tools/tables_bayarea.json"
CLS = None


def canon(cards):
    best = None
    for m in PERMS:
        k = tuple(sorted((c[0] + m[c[1]] for c in cards), key=lambda c: (RANKS.index(c[0]), c[1]), reverse=True))
        if best is None or k < best:
            best = k
    return "".join(best)


def pairs(path):
    with gzip.open(path, "rt") as f:
        head = json.loads(f.readline())
        prev = None
        for line in f:
            if line.startswith('{"you"'):
                if prev is not None:
                    yield prev, line
                prev = None
            else:
                prev = line


def table(tl, yl, you, chk, exm):
    t = json.loads(tl); y = json.loads(yl)["you"]
    if (y["iteration"], y["table"]) != (t["iteration"], t["table"]):
        chk["pair_mismatch"] += 1; return None
    seats = t["seats"]
    if you not in seats:
        chk["not_our_table"] += 1; return None
    me = seats.index(you)
    if y["seat"] != me:
        chk["seat_mismatch"] += 1
    pay = t["payouts"]; H = t["hands"]; mc = y["cards"]
    if len(mc) != len(H):
        chk["cards_len_ne_hands"] += 1
    r = collections.Counter()
    r["auto"] = len(y.get("automatic") or [])
    if r["auto"] and len(exm.setdefault("auto", [])) < 3:
        exm["auto"].append(y["automatic"][:2])
    spots = []
    bust_hand = None; bust_place = None
    for hi, h in enumerate(H):
        sb, sa = h["stacks_before"], h["stacks_after"]
        if sum(sb) != sum(sa):
            chk["chips_not_conserved"] += 1
        if h["blinds"][2]:
            chk["ante_nonzero"] += 1
        if sb[me] <= 0:
            continue
        n = len(sb); alive = [i for i in range(n) if sb[i] > 0]; na = len(alive)
        if sa[me] == 0 and bust_hand is None:
            bust_hand = h["hand"]
        r["hands"] += 1
        com = [0] * n; tot = [0] * n; blind_amt = [0] * n
        street = 0; folded = set(); vol = set()
        vp = pf = jm = False
        jammer = None; njams = 0; spot = None
        in_hand_at_street = {}
        faced_street = set()
        ev = h["events"]
        for j, e in enumerate(ev):
            k = e["kind"]; s = e.get("seat")
            if k == "board":
                street += 1; com = [0] * n
                in_hand_at_street[street] = [i for i in alive if i not in folded]
                continue
            if k == "prize_the_shover":
                p = ev[j - 1]
                ok = p["kind"] == "raise" and p.get("seat") == s and tot[s] == sb[s]
                chk[f"shover_after_allin_raise_{ok}"] += 1
                continue
            if k == "prize_the_empty_bluffer":
                sd = any(x["kind"] == "show" for x in ev)
                won = any(x["kind"] == "win" and x.get("seat") == s for x in ev)
                chk[f"bluffer street{street} showdown={sd} seat_won={won} prev={ev[j-1]['kind']}"] += 1
                continue
            if k not in ("blind", "fold", "check", "call", "raise"):
                continue
            to_call = max(com) - com[s]
            if k == "blind":
                com[s] += e["amount"]; tot[s] += e["amount"]; blind_amt[s] += e["amount"]; continue
            # decision
            if street == 0 and s == me:
                if k in ("call", "raise"): vp = True
                if k == "raise":
                    pf = True
                    if e["amount"] >= sb[me]: jm = True
                if jammer is not None and spot is None and k in ("fold", "call", "raise") and to_call > 0:
                    # facing a preflop all-in
                    D = sum(com[i] for i in range(n) if i not in (me, jammer))
                    multi = any(i not in (me, jammer) and i not in folded and i in vol for i in alive)
                    Sme, Sj = sb[me], sb[jammer]; E = min(Sme, Sj)
                    base = [sb[i] - com[i] for i in range(n)]
                    fst = list(base); fst[me] = Sme - com[me]; fst[jammer] = Sj + com[me] + D
                    wst = list(base); wst[me] = Sme + E + D; wst[jammer] = Sj - E
                    lst = list(base); lst[me] = Sme - E; lst[jammer] = Sj + E + D
                    # pot to the jammer in the fold world (generic form, equals fst when heads-up)
                    cf = [sb[i] - com[i] for i in range(n)]; cf[jammer] += sum(com)
                    UF = icm.value(sb, cf, pay)[me]
                    UW = icm.value(sb, wst, pay)[me]; UL = icm.value(sb, lst, pay)[me]
                    ULb = 0.0 if lst[me] <= 0 else UL
                    tt = (UF - UL) / (UW - UL) if UW > UL else None
                    tb = (UF - ULb) / (UW - ULb) if UW > ULb else None
                    cd = mc[h["hand"] - 1] if h["hand"] - 1 < len(mc) else None
                    key = canon(cd) if cd and len(cd) == 3 else None
                    cl = CLS.get(key) if key else None
                    spot = dict(alive=na, act=k, UF=UF, UW=UW, UL=UL, t=tt, tbug=tb, covered=Sj >= Sme,
                                multi=multi, njams=njams, bb=sb[me] / h["blinds"][1], jbb=Sj / h["blinds"][1],
                                pct=cl[0] if cl else None, eqw=cl[1] if cl else None, hand=h["hand"],
                                tocall=to_call, com=com[me], later=False)
            elif street == 0 and spot is not None and s not in (me, jammer) and k in ("call", "raise"):
                spot["later"] = True
            if street >= 1 and s == me and to_call > 0 and street not in faced_street and k in ("fold", "call", "raise"):
                faced_street.add(street)
                r["post_face"] += 1; r["post_fold"] += k == "fold"
                if street == 1:
                    hu = len(in_hand_at_street.get(1, [])) == 2
                    r["flop_face"] += 1; r["flop_fold"] += k == "fold"
                    if hu:
                        r["flop_face_hu"] += 1; r["flop_fold_hu"] += k == "fold"
            if k == "fold":
                folded.add(s)
            elif k == "call":
                if e["amount"] > sb[s] - tot[s]:
                    chk["call_exceeds_stack"] += 1
                com[s] += e["amount"]; tot[s] += e["amount"]
                if street == 0: vol.add(s)
            elif k == "raise":
                inc = e["amount"] - com[s]
                if inc > sb[s] - tot[s]:
                    chk["raise_exceeds_stack"] += 1
                com[s] = e["amount"]; tot[s] += inc
                if street == 0:
                    vol.add(s)
                    if s != me and tot[s] == sb[s]:
                        jammer = s; njams += 1
        if spot is not None:
            spot["Uafter"] = h["equity_after"][me]
            spot["Uafter_mine"] = icm.value(sb, sa, pay)[me]
            spot["chips_delta"] = sa[me] - sb[me]
            spots.append(spot)
        r["vpip"] += vp; r["pfr"] += pf; r["jam"] += jm
    last = H[-1]
    pts = last["equity_after"][me]
    alive_end = sum(1 for x in last["stacks_after"] if x > 0)
    if bust_hand is not None:
        place = {50: "1st", 30: "2nd", 20: "3rd", 0: "oom"}.get(round(pts, 6), "bust_tie")
    elif alive_end == 1:
        place = "1st" if round(pts, 6) == 50 else "?"
    else:
        place = "cap"
    return dict(pts=pts, place=place, bust_hand=bust_hand, nh=len(H), last_hand=last["hand"],
                alive_end=alive_end, c=dict(r), spots=spots)


def work(args):
    path, k, W, you = args
    global CLS
    CLS = json.load(open(TABLES))["classes"]
    out = []; chk = collections.Counter(); exm = {}
    for i, (tl, yl) in enumerate(pairs(path)):
        if i % W != k:
            continue
        res = table(tl, yl, you, chk, exm)
        if res is not None:
            out.append(res)
    return out, chk, exm


def main():
    path, outp = sys.argv[1], sys.argv[2]
    W = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    with gzip.open(path, "rt") as f:
        head = json.loads(f.readline())
    you = head["you"]
    with Pool(W) as p:
        R = p.map(work, [(path, k, W, you) for k in range(W)])
    tables = [x for o, _, _ in R for x in o]
    chk = collections.Counter(); exm = {}
    for _, c, e in R:
        chk.update(c)
        for kk, v in e.items(): exm.setdefault(kk, []).extend(v)
    name = {e["entry_id"]: e["team_name"] for e in head["entries"]}
    hd = dict(tournament_id=head["tournament_id"], you=you, team=name.get(you), n_entries=len(head["entries"]))
    with open(outp, "wb") as f:
        pickle.dump(dict(head=hd, tables=tables, checks=chk, examples=exm), f)
    pts = [x["pts"] for x in tables]
    print(path, hd, f"tables={len(tables)} mean pts={sum(pts)/len(pts):.3f}", dict(chk))


if __name__ == "__main__":
    main()
