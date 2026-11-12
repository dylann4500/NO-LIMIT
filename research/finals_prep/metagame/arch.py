"""Build archetype parameter tables in fields/<field>/arch/ from a calibrated field.
usage: python arch.py <field>
WIDE = 2 Curry's clone, LIMPSHOVE = Lemonade's clone, HYPER = thepastaway's clone (exemplars, unchanged),
BAL = mean of the top-20 teams' calibrated cells, TIGHT* and CALLER = BAL with preflop/all-in cells rewritten."""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = json.load(open("/Users/samuelchoi/NoLimit/NO-LIMIT/emu/runs/real_field/reference.json"))["teams"]


def team_params(d, F, adj, team):
    e = [x for x in F["entries"] if x["team"] == team][0]
    p = json.load(open(os.path.join(d, e["folder"], "params.json")))
    p["cells"] = dict(p["cells"], **adj.get(team, {}))
    return p


def mean_params(ps):
    out = {"cells": {}, "sizes": {}}
    for k in ps[0]["cells"]:
        v = [sum(p["cells"][k][i] for p in ps) / len(ps) for i in range(4)]
        out["cells"][k] = [round(x, 4) for x in v]
    for k in ps[0]["sizes"]:
        out["sizes"][k] = [round(sum(p["sizes"][k][i] for p in ps) / len(ps), 3) for i in range(len(ps[0]["sizes"][k]))]
    out["ex_low"] = sum(p["ex_low"] for p in ps) / len(ps)
    return out


def cap(x, hi=0.97):
    return max(0.0, min(hi, x))


def tight(bal, calloff=1.0, shove=1.0, openw=1.0, post=None):
    """Fold a lot; raise a narrow range; call off / jam with strong hands; shove-or-fold under 16 bb."""
    p = copy.deepcopy(bal)
    C = p["cells"]
    OPEN = {5: .08, 4: .10, 3: .13, 2: .18, 1: .22, 0: .06}
    JB = {0: .45, 1: .28, 2: .18}
    JP = {5: .6, 4: .75, 3: .9, 2: 1.2, 1: 1.5, 0: .5}
    for k in list(C):
        c = k[0]
        if c == "U":
            pos, sb, al = int(k[1]), int(k[2]), int(k[3])
            if sb >= 3:
                w = cap(OPEN[pos] * openw * (1.5 if al else 1.0))
                C[k] = [0, 1 - w, w, 0] if pos == 0 else [1 - w, 0, w, 0]
            else:
                w = cap(JB[sb] * JP[pos] * (1.4 if al else 1.0) * shove)
                C[k] = [0, 1 - w, 0, w] if pos == 0 else [1 - w, 0, 0, w]
        elif c == "O":
            role, sb = int(k[1]), int(k[2])
            if sb >= 3:
                r, cl = (.04, .03) if role == 0 else (.04, .07) if role == 1 else (.03, .10)
                r, cl = r * openw, cl * openw
                C[k] = [1 - r - cl, cl, r, 0]
            else:
                j = cap({0: .20, 1: .12, 2: .08}[sb] * shove)
                C[k] = [1 - j, 0, 0, j]
        elif c == "T":
            raised, lvl = int(k[1]), int(k[2])
            if raised:
                C[k] = [.75, .10, 0, .15] if lvl == 0 else [.55, .10, 0, .35]
            else:
                C[k] = [.88, .04, 0, .08]
        elif c == "A":
            cb, raised, al = int(k[1]), int(k[2]), int(k[3])
            if raised:
                x = cap({0: .9, 1: .7, 2: .5, 3: .4, 4: .33}[cb] * calloff * (1.3 if al else 1.0))
            else:
                x = cap({0: .30, 1: .14, 2: .09, 3: .06, 4: .04}[cb] * calloff * (1.5 if al else 1.0))
            C[k] = [1 - x, x, 0, 0]
    for k in C:
        C[k] = [round(v, 4) for v in C[k]]
    return p


def tight_noshove(bal):
    """TIGHT but short stacks keep the deep-stack plan (small raises, no shove-or-fold)."""
    p = tight(bal)
    C = p["cells"]
    for k in list(C):
        if k[0] == "U" and int(k[2]) < 3:
            C[k] = list(C[k[:2] + "3" + k[3]]) if (k[:2] + "3" + k[3]) in C else C[k]
        elif k[0] == "O" and int(k[2]) < 3:
            C[k] = list(C[k[:2] + "3"]) if (k[:2] + "3") in C else C[k]
    return p


def caller(bal):
    p = copy.deepcopy(bal)
    C = p["cells"]
    for k in list(C):
        c = k[0]
        f = C[k]
        if c == "U":
            C[k] = [0, .9, .1, 0] if k[1] == "0" else [.40, .50, .10, 0]
        elif c == "O":
            C[k] = [.40, .55, .05, 0]
        elif c == "T":
            C[k] = [.35, .60, .05, 0]
        elif c == "A":
            x = {0: .7, 1: .5, 2: .4, 3: .3, 4: .25}[int(k[1])]
            C[k] = [1 - x, x, 0, 0]
        elif c == "B":
            nf = f[0] * 0.5
            C[k] = [nf, f[1] + f[0] - nf, f[2], f[3]]
        elif c == "K":
            r, j = f[2] * 0.6, f[3] * 0.6
            C[k] = [0, 1 - r - j, r, j]
        C[k] = [round(v, 4) for v in C[k]]
    return p


def main(field):
    d = os.path.join(HERE, "fields", field)
    F = json.load(open(os.path.join(d, "field.json")))
    adj = json.load(open(os.path.join(d, "adj.json")))
    os.makedirs(os.path.join(d, "arch"), exist_ok=True)
    tp = {t: team_params(d, F, adj, t) for t in TOP}
    bal = mean_params(list(tp.values()))
    A = {"WIDE": tp["2 Curry"], "LIMPSHOVE": tp["Lemonade"], "HYPER": tp["thepastaway"], "BAL": bal,
         "TIGHT": tight(bal), "CALLER": caller(bal),
         "TIGHT_c05": tight(bal, calloff=0.5), "TIGHT_c2": tight(bal, calloff=2.0), "TIGHT_c4": tight(bal, calloff=4.0),
         "TIGHT_s05": tight(bal, shove=0.5), "TIGHT_s2": tight(bal, shove=2.0), "TIGHT_s0": tight_noshove(bal),
         "TIGHT_o15": tight(bal, openw=1.5), "TIGHT_o07": tight(bal, openw=0.7)}
    for n, p in A.items():
        json.dump(p, open(os.path.join(d, "arch", n + ".json"), "w"))
    print(field, "wrote", sorted(A))


if __name__ == "__main__":
    main(sys.argv[1])
