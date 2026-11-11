"""Answer Q1-Q4 from out/r{1..6}.pkl produced by extract.py.

usage: python -I analyze.py OUTDIR
Points for opponents are over tables shared with avalon only.
"""
import collections
import math
import os
import pickle
import statistics as stt
import sys

OUT = sys.argv[1]
ROUNDS = [1, 2, 3, 4, 5, 6]
MIN_T = 100   # min shared tables for a team to be ranked
OFFICIAL = {  # R1..R6 official scores (from the task brief)
    "2 Curry": [20.40, 20.24, 21.15, 20.47, 20.41, 20.08],
    "Lemonade": [19.78, 19.34, 20.67, 20.62, 20.09, 19.61],
    "AZ": [21.22, 19.44, 17.93, 19.06, 18.04, 17.27],
    "sandylikesfrogs": [20.65, 19.72, 18.33, 18.30, 18.49, 16.87],
    "Team 72": [22.19, 20.23, 17.89, 17.86, 17.83, 17.39],
    "avalon": [18.10, 16.73, 19.05, 18.26, 17.95, 17.53],
}


def mean(v):
    return sum(v) / len(v) if v else float("nan")


def sd(v):
    return stt.pstdev(v) if len(v) > 1 else float("nan")


def pct(a, b):
    return 100.0 * a / b if b else float("nan")


def hist_median(h):
    tot = sum(h.values())
    if not tot:
        return float("nan")
    acc = 0
    for k in sorted(h):
        acc += h[k]
        if acc >= tot / 2:
            return k
    return float("nan")


def load(r):
    with open(os.path.join(OUT, f"r{r}.pkl"), "rb") as f:
        d = pickle.load(f)
    names = dict(d["names"])
    # disambiguate duplicate names
    cnt = collections.Counter(names.values())
    for e, nm in list(names.items()):
        if cnt[nm] > 1:
            names[e] = f"{nm}#{e[:4]}"
    d["nm"] = lambda e, names=names: "FILLER" if e == "FILLER" else names.get(e, e[:8])
    d["names2"] = names
    return d


D = {r: load(r) for r in ROUNDS}


def team_points(d):
    """team -> list of pts on shared tables; avalon pts list; per-table rows."""
    you = d["you"]
    P = collections.defaultdict(list)
    for it, tb, nh, alive, me, srows in d["rows"]:
        for (e, pts, pl, *_rest) in srows:
            if e == "FILLER":
                continue
            P[e].append(pts)
    return P


def ranking(d, P):
    you = d["you"]
    rows = [(mean(v), len(v), e) for e, v in P.items() if len(v) >= MIN_T and e != you]
    rows.sort(reverse=True)
    return rows


PTS = {r: team_points(D[r]) for r in ROUNDS}
RANK = {r: ranking(D[r], PTS[r]) for r in ROUNDS}


def stat_line(c):
    h = max(1, c.get("hands", 0))
    g = lambda k: c.get(k, 0)
    return {
        "VPIP": pct(g("vpip"), h), "PFR": pct(g("pfr"), h), "RFI": pct(g("rfi"), g("rfi_opp")),
        "limp1st": pct(g("limp_first"), g("rfi_opp")),
        "3bet": pct(g("3b"), g("3b_opp")), "3b_vBTN": pct(g("3bbtn"), g("3bbtn_opp")),
        "jam": pct(g("jam"), h), "openjam": pct(g("openjam"), h),
        "callJam": pct(g("call_jam"), g("face_jam")), "F3B": pct(g("f3b"), g("f3b_opp")),
        "F2flopBet": pct(g("ff_fold"), g("ff_face")), "F2postBet": pct(g("fold_bet"), g("face_bet")),
        "postAgg": pct(g("post_agg"), g("post_act")),
        "AF": g("post_agg") / g("post_call") if g("post_call") else float("nan"),
        "cbet": pct(g("cb"), g("cb_opp")), "cbetHU": pct(g("cb_hu"), g("cb_opp_hu")),
        "cbetMW": pct(g("cb_mw"), g("cb_opp_mw")),
        "sawFlop": pct(g("saw_flop"), h), "WTSD": pct(g("wtsd"), g("saw_flop")), "W$SD": pct(g("wsd"), g("wtsd")),
        "expLow_sd": pct(g("ex_sd_low"), g("ex_sd_np")), "expPair_sd": pct(g("ex_sd_pairing"), g("ex_sd_onepair")),
        "expLow_all": pct(g("ex_all_low"), g("ex_all_np")), "expPair_all": pct(g("ex_all_pairing"), g("ex_all_onepair")),
        "n_hands": g("hands"), "n_ff": g("ff_face"), "n_3bopp": g("3b_opp"), "n_cb": g("cb_opp"),
        "n_exsd": g("ex_sd_np"), "n_exsd_pair": g("ex_sd_onepair"),
        "flopJamBet": pct(g("betjam_s1"), g("bets_s1")),
    }


def pooled(d, ents):
    c = collections.Counter()
    for e in ents:
        c.update(d["C"].get(e, {}))
    return c


def out(fh, s=""):
    print(s)
    fh.write(s + "\n")


# ---------------------------------------------------------------- Q1
def q1(fh):
    out(fh, "=== Q1 FIELD EVOLUTION (non-avalon, non-filler seats, pooled by hands; opp pts on shared tables)")
    hdr = ["R", "tables", "teams", "VPIP", "PFR", "RFI", "3bet", "3bvBTN", "jam", "callJam", "F2flop", "F2post", "pAgg", "AF",
           "cbet", "WTSD"]
    out(fh, " ".join(f"{x:>7}" for x in hdr))
    for r in ROUNDS:
        d = D[r]
        ents = [e for e in d["C"] if e not in (d["you"], "FILLER")]
        s = stat_line(pooled(d, ents))
        vals = [r, len(d["rows"]), len(RANK[r]), s["VPIP"], s["PFR"], s["RFI"], s["3bet"], s["3b_vBTN"], s["jam"],
                s["callJam"], s["F2flopBet"], s["F2postBet"], s["postAgg"], s["AF"], s["cbet"], s["WTSD"]]
        out(fh, " ".join(f"{v:>7.1f}" if isinstance(v, float) else f"{v:>7}" for v in vals))
    # team-median version (each team weighted equally)
    out(fh, "\nteam-median (teams >= %d tables): VPIP PFR 3bet jam F2flop pAgg" % MIN_T)
    for r in ROUNDS:
        d = D[r]
        L = [stat_line(d["C"][e]) for _, _, e in RANK[r]]
        md = lambda k: stt.median([x[k] for x in L if not math.isnan(x[k])])
        out(fh, f"R{r}: " + " ".join(f"{k} {md(k):5.1f}" for k in ["VPIP", "PFR", "3bet", "jam", "F2flopBet", "postAgg"]))

    out(fh, "\nfield toughness (opp pts on shared tables; teams >= %d tables)" % MIN_T)
    out(fh, f"{'R':>2} {'fish<3':>6} {'fishSeat%':>9} {'fishPts':>7} {'<6pts':>5} {'sdTeam':>6} {'top10':>6} {'bot10':>6} "
            f"{'fishDon/t':>9} {'bot10Don/t':>10} | {'avPts':>6} {'avChipsBot10/seat':>17} {'avChipsOther/seat':>17} "
            f"{'av_bb_bot10/seat':>16} {'av_bb_other/seat':>16} | slope pts/fishSeat  slope pts/bot10Seat")
    for r in ROUNDS:
        d = D[r]
        you = d["you"]
        R = RANK[r]
        mpts = {e: m for m, n, e in R}
        fish = {e for e, m in mpts.items() if m < 3}
        weak6 = {e for e, m in mpts.items() if m < 6}
        bot10 = {e for _, _, e in R[-10:]}
        top10 = R[:10]
        seats = fishseats = 0
        fd = bd = 0.0
        fb = [0.0, 0, 0.0]  # chips, seat-count, bb
        fo = [0.0, 0, 0.0]
        av = []
        xf, xb = [], []
        for it, tb, nh, alive, me, srows in d["rows"]:
            nf = nb = 0
            for i, (e, pts, pl, flow, flow_bb, flow_v, nboth, nbv, bh) in enumerate(srows):
                if i == me:
                    av.append(pts)
                    continue
                if e == "FILLER":
                    continue
                seats += 1
                if e in fish:
                    fishseats += 1
                    fd += 12.5 - pts
                    nf += 1
                if e in bot10:
                    bd += 12.5 - pts
                    nb += 1
                    fb[0] += flow; fb[1] += 1; fb[2] += flow_bb
                else:
                    fo[0] += flow; fo[1] += 1; fo[2] += flow_bb
            xf.append(nf); xb.append(nb)
        nt = len(d["rows"])

        def slope(x, y):
            mx, my = mean(x), mean(y)
            vx = sum((a - mx) ** 2 for a in x)
            b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / vx if vx else float("nan")
            res = [c - my - b * (a - mx) for a, c in zip(x, y)]
            se = math.sqrt(sum(z * z for z in res) / (len(x) - 2) / vx) if vx else float("nan")
            return b, se
        bf, sef = slope(xf, av)
        bb_, seb = slope(xb, av)
        allm = [m for m, n, e in R]
        out(fh, f"{r:>2} {len(fish):>6} {pct(fishseats, seats):>9.1f} {mean([mpts[e] for e in fish]) if fish else float('nan'):>7.2f} "
                f"{len(weak6):>5} {sd(allm):>6.2f} {mean([m for m, n, e in top10]):>6.2f} {mean([m for m, n, e in R[-10:]]):>6.2f} "
                f"{fd / nt:>9.2f} {bd / nt:>10.2f} | {mean(av):>6.2f} {fb[0] / max(1, fb[1]):>17.1f} {fo[0] / max(1, fo[1]):>17.1f} "
                f"{fb[2] / max(1, fb[1]):>16.2f} {fo[2] / max(1, fo[1]):>16.2f} | {bf:+.2f}±{sef:.2f}  {bb_:+.2f}±{seb:.2f}")
    out(fh, "fishDon/t, bot10Don/t: points given up per table (sum of 12.5-pts over those seats). avChips*/seat: net chips "
            "avalon took per (table, seat) from that group (proportional winner/loser split, hands both had chips in).")


# ---------------------------------------------------------------- Q2
def h2h(fh, r, teams_by_name):
    d = D[r]
    you = d["you"]
    nm = d["nm"]
    av_all = []
    per = collections.defaultdict(lambda: {"av": [], "x": [], "flow": [], "flow_bb": [], "flow_v": [], "nboth": 0, "nbv": 0})
    for it, tb, nh, alive, me, srows in d["rows"]:
        av = srows[me][1]
        av_all.append(av)
        seen = set()
        for i, (e, pts, pl, flow, flow_bb, flow_v, nboth, nbv, bh) in enumerate(srows):
            if i == me or e == "FILLER":
                continue
            p = per[e]
            if e not in seen:
                p["av"].append(av)
                seen.add(e)
            p["x"].append(pts); p["flow"].append(flow); p["flow_bb"].append(flow_bb); p["flow_v"].append(flow_v)
            p["nboth"] += nboth; p["nbv"] += nbv
    A = mean(av_all)
    out(fh, f"\n--- R{r}: avalon overall {A:.2f} pts/table over {len(av_all)} tables (sd {sd(av_all):.1f})")
    out(fh, f"{'team':<18}{'ourRk':>6}{'n':>6}{'X pts':>7}{'av@X':>7}{'diff':>7}{'±SE':>6}{'chips X->av /t':>15}{'±SE':>6}"
            f"{'bb/t':>7}{'vpipBoth chips/t':>17}{'hands both/t':>13}")
    rankpos = {e: i + 1 for i, (_, _, e) in enumerate(RANK[r])}
    byname = {nm(e): e for e in per}
    for name in teams_by_name:
        e = byname.get(name)
        if e is None:
            out(fh, f"{name:<18} not seated with us")
            continue
        p = per[e]
        n = len(p["av"])
        diff = mean(p["av"]) - A
        se = sd(av_all) / math.sqrt(n)
        fse = sd(p["flow"]) / math.sqrt(len(p["flow"]))
        out(fh, f"{name[:17]:<18}{rankpos.get(e, '-'):>6}{n:>6}{mean(p['x']):>7.2f}{mean(p['av']):>7.2f}{diff:>+7.2f}{se:>6.2f}"
                f"{mean(p['flow']):>+15.1f}{fse:>6.1f}{mean(p['flow_bb']):>+7.2f}{mean(p['flow_v']):>+17.1f}{p['nboth'] / len(p['flow']):>13.1f}")
    # who took most from us
    L = [(mean(p["flow"]), sd(p["flow"]) / math.sqrt(len(p["flow"])), mean(p["flow_bb"]), len(p["flow"]), nm(e), mean(p["av"]) - A)
         for e, p in per.items() if len(p["flow"]) >= MIN_T]
    L.sort()
    out(fh, f"biggest takers from avalon in R{r} (chips/table, ±SE, bb/table, n, av pts diff at their tables):")
    for f, se, fbb, n, name, df in L[:8]:
        out(fh, f"   {name[:20]:<20} {f:+7.1f} ±{se:4.1f}  {fbb:+6.2f}bb  n={n:<5} avDiff {df:+.2f}")
    out(fh, "biggest givers:")
    for f, se, fbb, n, name, df in L[-5:][::-1]:
        out(fh, f"   {name[:20]:<20} {f:+7.1f} ±{se:4.1f}  {fbb:+6.2f}bb  n={n:<5} avDiff {df:+.2f}")
    tot = sum(sum(p["flow"]) for p in per.values()) / len(av_all)
    out(fh, f"total net chips avalon took per table from all seats: {tot:+.1f}")


def q2(fh):
    out(fh, "\n=== Q2 HEAD-TO-HEAD (top-10 opponents by our-file R6 points; same teams in R5)")
    top = [D[6]["nm"](e) for _, _, e in RANK[6][:10]]
    out(fh, "R6 top-10 (shared tables): " + ", ".join(f"{D[6]['nm'](e)} {m:.2f}" for m, n, e in RANK[6][:10]))
    for r in (6, 5):
        h2h(fh, r, top)


# ---------------------------------------------------------------- Q3
def places(d, e):
    pl = collections.Counter()
    pts = []
    busts = []
    n = 0
    for it, tb, nh, alive, me, srows in d["rows"]:
        for (x, p, place, flow, fbb, fv, nb, nbv, bh) in srows:
            if x != e:
                continue
            n += 1
            pl[place] += 1
            pts.append(p)
            if bh is not None:
                busts.append(bh + 1)
    return n, pl, pts, busts


def q3(fh):
    out(fh, "\n=== Q3 STYLE, R6 (and R5 for the same teams)")
    for r in (6, 5):
        d = D[r]
        nm = d["nm"]
        byname = {nm(e): e for e in d["C"]}
        want = ["2 Curry", "thepastaway", "Lemonade", "Team 82", "avalon"]
        ents = [byname.get(w) for w in want]
        field = [e for e in d["C"] if e not in (d["you"], "FILLER")]
        cols = [(w, e) for w, e in zip(want, ents) if e] + [("FIELD", None)]
        S = {w: stat_line(d["C"][e] if e else pooled(d, field)) for w, e in cols}
        out(fh, f"\nR{r}" + "".join(f"{w[:11]:>12}" for w, _ in cols))
        keys = ["VPIP", "PFR", "RFI", "limp1st", "3bet", "3b_vBTN", "jam", "openjam", "callJam", "F3B", "F2flopBet",
                "F2postBet", "cbet", "cbetHU", "cbetMW", "postAgg", "AF", "sawFlop", "WTSD", "W$SD", "flopJamBet",
                "expLow_sd", "expPair_sd", "expLow_all", "expPair_all"]
        for k in keys:
            out(fh, f"{k:<12}" + "".join(f"{S[w][k]:>12.1f}" for w, _ in cols))
        for k in ["n_hands", "n_3bopp", "n_ff", "n_cb", "n_exsd", "n_exsd_pair"]:
            out(fh, f"{k:<12}" + "".join(f"{S[w][k]:>12d}" for w, _ in cols))
        # bet sizes
        def hm(e, m):
            if e:
                return hist_median(d["H"].get(e, {}).get(m, {}))
            h = collections.Counter()
            for x in field:
                h.update(d["H"].get(x, {}).get(m, {}))
            return hist_median(h)
        out(fh, f"{'openSize bb':<12}" + "".join(f"{hm(e, 'open_bb') / 10:>12.1f}" for w, e in cols))
        for st in (1, 2, 3):
            out(fh, f"{'bet%pot s' + str(st):<12}" + "".join(f"{hm(e, f'bet_s{st}') * 5:>12.0f}" for w, e in cols))
        # places
        for w, e in cols:
            if not e:
                continue
            n, pl, pts, busts = places(d, e)
            out(fh, f"  {w[:14]:<14} n={n:<5} pts {mean(pts):5.2f}±{sd(pts) / math.sqrt(n):.2f}  1st {pct(pl[1], n):4.1f}%  "
                    f"2nd {pct(pl[2], n):4.1f}%  3rd {pct(pl[3], n):4.1f}%  ITM {pct(pl[1] + pl[2] + pl[3], n):4.1f}%  "
                    f"bust {pct(len(busts), n):4.1f}% (median hand {stt.median(busts) if busts else float('nan'):.0f})  "
                    f"pts>=45 {pct(sum(1 for p in pts if p >= 45), n):4.1f}%  pts<0.5 {pct(sum(1 for p in pts if p < 0.5), n):4.1f}%")
    out(fh, "exp*_sd: showdown hands only (kept cards visible). expLow: exposed card is the lower rank (non-pairs). "
            "expPair: when exactly one kept card pairs the flop, exposed that one. *_all: avalon all hands (private kept cards).")


# ---------------------------------------------------------------- Q4
def spearman(a, b):
    common = [k for k in a if k in b]
    ra = {k: i for i, k in enumerate(sorted(common, key=lambda k: -a[k]))}
    rb = {k: i for i, k in enumerate(sorted(common, key=lambda k: -b[k]))}
    n = len(common)
    d2 = sum((ra[k] - rb[k]) ** 2 for k in common)
    return 1 - 6 * d2 / (n * (n * n - 1)), n


def q4(fh):
    out(fh, "\n=== Q4 CONSISTENCY (shared-table points; teams >= %d tables; avalon ranked with its own full-file avg)" % MIN_T)
    byround = {}
    for r in ROUNDS:
        d = D[r]
        nm = d["nm"]
        m = {nm(e): mm for mm, n, e in RANK[r]}
        m["avalon"] = mean([row[5][row[4]][1] for row in d["rows"]])
        byround[r] = m
    names = set().union(*[set(byround[r]) for r in ROUNDS])
    top10 = {r: [k for k in sorted(byround[r], key=lambda k: -byround[r][k])][:10] for r in ROUNDS}
    cnt = collections.Counter(k for r in ROUNDS for k in top10[r])
    out(fh, "top-10 appearances (rounds, then rank by round):")
    for k, c in cnt.most_common():
        if c < 3:
            continue
        ranks = []
        for r in ROUNDS:
            order = sorted(byround[r], key=lambda x: -byround[r][x])
            ranks.append(str(order.index(k) + 1) if k in byround[r] else "-")
        out(fh, f"   {k[:20]:<20} {c}/6  ranks {' '.join(f'{x:>3}' for x in ranks)}  pts "
                + " ".join(f"{byround[r].get(k, float('nan')):5.2f}" for r in ROUNDS))
    out(fh, "rank correlation between consecutive rounds (Spearman, common teams): "
            + "  ".join(f"R{r}-R{r + 1} {spearman(byround[r], byround[r + 1])[0]:+.2f}" for r in ROUNDS[:-1]))
    # shared-table vs official
    out(fh, "\nshared-table estimate vs official (per round), for the top 6:")
    for k, offs in OFFICIAL.items():
        out(fh, f"   {k:<16}" + " ".join(f"{byround[r].get(k, float('nan')):5.2f}/{offs[r - 1]:5.2f}" for r in ROUNDS))
    # noise model for the final standings: avalon's own per-table sd and table count per round
    w = ROUNDS
    out(fh, "\nnoise in weighted totals (weights 1..6). Per-round SE = sd(pts per table)/sqrt(N tables).")
    var_av = 0.0
    for r in ROUNDS:
        d = D[r]
        av = [row[5][row[4]][1] for row in d["rows"]]
        var_av += (r ** 2) * (sd(av) ** 2) / len(av)
        out(fh, f"   R{r}: avalon N={len(av)} mean {mean(av):.3f} (official {OFFICIAL['avalon'][r - 1]}) sd {sd(av):.2f} "
                f"SE {sd(av) / math.sqrt(len(av)):.3f}")
    se_tot = math.sqrt(var_av)
    out(fh, f"   SE of one team's weighted total if it plays as many tables as avalon: {se_tot:.2f}; SE of a difference: "
            f"{se_tot * math.sqrt(2):.2f}")
    fin = [("AZ", 383.96), ("sandylikesfrogs", 381.95), ("Team 72", 381.25), ("avalon", 376.71)]
    for i in range(len(fin)):
        for j in range(i + 1, len(fin)):
            dd = fin[i][1] - fin[j][1]
            out(fh, f"   {fin[i][0]} - {fin[j][0]}: {dd:+.2f}  z={dd / (se_tot * math.sqrt(2)):.1f}")
    # per-team sd on shared tables for those teams (to check equal-sd assumption)
    for r in (1, 6):
        d = D[r]
        nm = d["nm"]
        P = PTS[r]
        out(fh, f"   R{r} per-table sd on shared tables: " + ", ".join(
            f"{nm(e)} {sd(v):.1f}" for e, v in P.items() if nm(e) in OFFICIAL and e != d['you']))


def main():
    with open(os.path.join(OUT, "report.txt"), "w") as fh:
        for r in ROUNDS:
            out(fh, f"R{r}: tournament {D[r]['tournament_id']} tables {len(D[r]['rows'])} validation {D[r]['V']}")
        q1(fh)
        q2(fh)
        q3(fh)
        q4(fh)


if __name__ == "__main__":
    main()
