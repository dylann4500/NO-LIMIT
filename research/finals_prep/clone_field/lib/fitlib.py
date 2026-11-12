"""Accumulate per-team behaviour counts from table records (real downloads or simulated logs)."""
import collections
import json

import clonecore as cc

RK = cc.RI


def new_acc():
    return {"cells": {}, "sizes": {}, "stats": {}}


def places_of(hands, n):
    bust = {}
    for hi, h in enumerate(hands):
        sb, sa = h["stacks_before"], h["stacks_after"]
        for s in range(n):
            if sb[s] > 0 and sa[s] == 0 and s not in bust:
                bust[s] = (hi, sb[s])
    final = hands[-1]["stacks_after"]
    keys = [((0, bust[s][0], bust[s][1]) if s in bust else (1, final[s], 0)) for s in range(n)]
    order = sorted(range(n), key=lambda s: keys[s], reverse=True)
    pl = [0] * n
    for p, s in enumerate(order, 1):
        pl[s] = p
    return pl


def add_table(acc, t, names):
    """t: a table record (seats = entry ids or names, hands with events). names: id -> team."""
    seats = [names.get(x, x) for x in t["seats"]]
    n = len(seats)
    hands = t["hands"]
    if not hands:
        return
    C, S, ST = acc["cells"], acc["sizes"], acc["stats"]
    cs = [C.setdefault(x, {}) for x in seats]
    ss = [S.setdefault(x, {}) for x in seats]
    st = [ST.setdefault(x, collections.Counter()) for x in seats]
    Track = cc.Track
    for h in hands:
        sb = h["stacks_before"]
        tr = Track(sb, h["blinds"][1])
        exposed, shown, won = {}, {}, set()
        aggs = [None, None, None, None]
        for e in h["events"]:
            k = e["kind"]
            if k == "fold" or k == "call" or k == "raise" or k == "check":
                s = e["seat"]
                amt = e.get("amount") or 0
                key = tr.key(s)
                a = tr.cls(k, s, amt)
                c = cs[s].get(key)
                if c is None:
                    c = cs[s][key] = [0, 0, 0, 0]
                c[cc.ACT_I[a]] += 1
                if a == "R":
                    sk, v = tr.size(key, amt, s)
                    d = ss[s].get(sk)
                    if d is None:
                        d = ss[s][sk] = {}
                    v = round(v * 20) if v < 20 else 400
                    d[v] = d.get(v, 0) + 1
                tr.apply(k, s, amt)
            elif k == "blind" or k == "ante":
                tr.apply(k, e["seat"], e.get("amount") or 0)
            elif k == "board":
                aggs[tr.street] = tr.aggr
                tr.apply(k, None, 0)
            elif k == "reveal":
                exposed[e["seat"]] = (e.get("cards") or [None])[0]
            elif k == "show":
                shown[e["seat"]] = e.get("cards") or []
            elif k == "win":
                if e.get("amount"):
                    won.add(e["seat"])
        aggs[tr.street] = tr.aggr
        for s in range(n):
            if sb[s] > 0:
                x = st[s]
                x["hands"] += 1
                if tr.vol[s] or tr.raised_pf[s]:
                    x["vpip"] += 1
                if tr.raised_pf[s]:
                    x["pfr"] += 1
                if tr.street >= 1 and not (tr.folded[s] and s not in exposed):
                    x["sawflop"] += 1
        for s, ex in exposed.items():
            kept = shown.get(s)
            if kept and len(kept) == 2 and ex in kept:
                o = kept[0] if kept[1] == ex else kept[1]
                if RK[o[0]] != RK[ex[0]]:
                    st[s]["ex_n"] += 1
                    if RK[ex[0]] < RK[o[0]]:
                        st[s]["ex_low"] += 1
        if len(shown) >= 2:
            for s in shown:
                st[s]["wtsd"] += 1
                if s in won:
                    st[s]["wsd"] += 1
            for street in (0, 1, 2, 3):
                a = aggs[street]
                if a is not None and a in shown:
                    st[a]["sdagg_n%d" % street] += 1
                    if a in won:
                        st[a]["sdagg_w%d" % street] += 1
            a = aggs[3]
            if a is not None and a in shown:      # river bet called: the callers
                for s in shown:
                    if s != a:
                        st[s]["sdcall_n"] += 1
                        if s in won:
                            st[s]["sdcall_w"] += 1
    pts = hands[-1]["equity_after"]
    pl = places_of(hands, n)
    for s in range(n):
        x = st[s]
        p = float(pts[s] or 0.0)
        x["tables"] += 1
        x["pts"] += p
        x["pts2"] += p * p
        x["place%d" % pl[s]] += 1
        x["nhands_tbl"] += len(hands)


def merge(a, b):
    for team, cells in b["cells"].items():
        d = a["cells"].setdefault(team, {})
        for k, v in cells.items():
            c = d.get(k)
            if c is None:
                d[k] = list(v)
            else:
                for i in range(4):
                    c[i] += v[i]
    for team, sz in b["sizes"].items():
        d = a["sizes"].setdefault(team, {})
        for k, hist in sz.items():
            dd = d.setdefault(k, {})
            for v, c in hist.items():
                dd[v] = dd.get(v, 0) + c
    for team, s in b["stats"].items():
        d = a["stats"].setdefault(team, collections.Counter())
        d.update(s)
    return a


def agg(cells, prefix_fn):
    out = [0, 0, 0, 0]
    for k, v in cells.items():
        if prefix_fn(k):
            for i in range(4):
                out[i] += v[i]
    return out


def style(acc, team):
    """Headline style numbers for one team from an accumulator."""
    c = acc["cells"].get(team, {})
    s = acc["stats"].get(team, {})
    o = {}
    hn = max(1, s.get("hands", 0))
    tb = max(1, s.get("tables", 0))
    o["tables"] = s.get("tables", 0)
    o["pts"] = s.get("pts", 0) / tb
    o["pts_se"] = ((s.get("pts2", 0) / tb - o["pts"] ** 2) / tb) ** 0.5 if tb > 1 else 0
    o["vpip"] = s.get("vpip", 0) / hn
    o["pfr"] = s.get("pfr", 0) / hn
    def fr(pred, idx):
        a = agg(c, pred)
        tot = sum(a)
        return (sum(a[i] for i in idx) / tot if tot else float("nan"))
    o["open"] = fr(lambda k: k[0] == "U" and k[1] != "0", (2, 3))
    o["openjam"] = fr(lambda k: k[0] == "U", (3,))
    o["limp"] = fr(lambda k: k[0] == "U" and k[1] not in "0", (1,))
    o["3bet"] = fr(lambda k: k[0] == "O", (2, 3))
    o["fold_to_open"] = fr(lambda k: k[0] == "O", (0,))
    o["fold_to_3bet"] = fr(lambda k: k[0] == "T" and k[1] == "1" and k[2] == "0", (0,))
    o["fold_to_4bet"] = fr(lambda k: k[0] == "T" and k[1] == "1" and k[2] == "1", (0,))
    o["4bet"] = fr(lambda k: k[0] == "T" and k[1] == "1" and k[2] == "0", (2, 3))
    o["call_allin"] = fr(lambda k: k[0] == "A", (1, 2, 3))
    for stt, nm in ((1, "flop"), (2, "turn"), (3, "river")):
        o[nm + "_bet"] = fr(lambda k, stt=stt: k[0] == "K" and k[1] == str(stt), (2, 3))
        o[nm + "_fold_to_bet"] = fr(lambda k, stt=stt: k[0] == "B" and k[1] == str(stt), (0,))
        o[nm + "_raise"] = fr(lambda k, stt=stt: k[0] == "B" and k[1] == str(stt), (2, 3))
    o["sawflop"] = s.get("sawflop", 0) / hn
    o["wtsd"] = s.get("wtsd", 0) / max(1, s.get("sawflop", 0))
    o["wsd"] = s.get("wsd", 0) / max(1, s.get("wtsd", 0))
    o["ex_low"] = s.get("ex_low", 0) / max(1, s.get("ex_n", 0))
    for stt in (0, 1, 2, 3):
        o["sdagg_w%d" % stt] = s.get("sdagg_w%d" % stt, 0) / max(1, s.get("sdagg_n%d" % stt, 0))
    o["sdcall_w"] = s.get("sdcall_w", 0) / max(1, s.get("sdcall_n", 0))
    o["places"] = [s.get("place%d" % i, 0) / tb for i in range(1, 9)]
    o["hands_per_table"] = s.get("nhands_tbl", 0) / tb
    o["hands_alive_per_table"] = s.get("hands", 0) / tb
    return o
