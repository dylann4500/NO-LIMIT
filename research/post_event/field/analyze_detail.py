"""Report from out/d{1..6}.pkl (detail.py) and out/r{1..6}.pkl (extract.py).

usage: python -I analyze_detail.py OUTDIR
"""
import os
import pickle
import sys

OUT = sys.argv[1]
D = {}
R = {}
for r in range(1, 7):
    with open(os.path.join(OUT, f"d{r}.pkl"), "rb") as f:
        D[r] = pickle.load(f)
    with open(os.path.join(OUT, f"r{r}.pkl"), "rb") as f:
        R[r] = pickle.load(f)

lines = []


def out(s=""):
    print(s)
    lines.append(s)


out("=== How the field treats avalon's non-jam, unlimped opens (per round)")
out(f"{'R':>2}{'opens/t':>8}{'3b by someone%':>15}{'we fold%':>9}{'we call%':>9}{'we 4b%':>8}{'net bb/t in 3b hands':>21}"
    f"{'net bb/t all opens':>19}{'per-player 3b% vs us':>21}{'field per-player 3b%':>21}")
for r in range(1, 7):
    G = D[r]["G"]
    O = D[r]["O"]
    nt = 20000  # non-filler tables (detail.py skips tables where our seat was a filler)
    nt = sum(1 for row in R[r]["rows"] if row[5][row[4]][0] != "FILLER")
    faced = sum(v.get("faced_our_open", 0) for k, v in O.items() if k != "FILLER")
    got = sum(v.get("got3b", 0) for k, v in O.items() if k != "FILLER")
    you = R[r]["you"]
    C = R[r]["C"]
    f3 = sum(c.get("3b", 0) for e, c in C.items() if e not in (you, "FILLER"))
    fo = sum(c.get("3b_opp", 0) for e, c in C.items() if e not in (you, "FILLER"))
    g3 = G["got3b"]
    out(f"{r:>2}{G['opens'] / nt:>8.1f}{100 * g3 / G['opens']:>15.1f}{100 * G.get('resp_fold', 0) / g3:>9.1f}"
        f"{100 * G.get('resp_call', 0) / g3:>9.1f}{100 * G.get('resp_raise', 0) / g3:>8.1f}{G['net3b_bb'] / nt:>+21.2f}"
        f"{G['open_net_bb'] / nt:>+19.2f}{100 * got / faced:>21.1f}{100 * f3 / fo:>21.1f}")
out("per-player 3b% vs us: 3-bets of our opens / opponents who acted facing our open. Field per-player 3b%: all "
    "non-avalon players facing any single non-jam open (includes ours).")

TEAMS = ["thepastaway", "Lemonade", "2 Curry", "Team 123", "Team 82", "pocket rockets", "JJ", "Chikerbot"]
for r in (6, 5):
    out(f"\n=== R{r}: per opponent: 3-bets vs our opens, and chip flow X->avalon by how the hand ended (chips/table)")
    out(f"{'team':<16}{'tables':>7}{'3b% vs our open':>16}{'n faced':>8}{'we fold%':>9}{'our net bb/t there':>19}"
        f"{'preflop':>9}{'postNoSD':>9}{'showdown':>9}{'total':>8}")
    O, F, T = D[r]["O"], D[r]["F"], D[r]["T"]
    for x in TEAMS:
        o = O.get(x, {})
        f = F.get(x, {})
        t = T.get(x, 0)
        if not t:
            continue
        fa = o.get("faced_our_open", 0)
        g = o.get("got3b", 0)
        out(f"{x:<16}{t:>7}{100 * g / max(1, fa):>16.1f}{fa:>8}{100 * o.get('resp_fold', 0) / max(1, g):>9.1f}"
            f"{o.get('net_bb', 0) / t:>+19.2f}{f.get('preflop', 0) / t:>+9.1f}{f.get('post_noSD', 0) / t:>+9.1f}"
            f"{f.get('showdown', 0) / t:>+9.1f}{sum(f.get(k, 0) for k in ('preflop', 'post_noSD', 'showdown')) / t:>+8.1f}")
    # field average excluding fillers
    tf = sum(v for k, v in T.items() if k != "FILLER")
    agg = {k: sum(F[x].get(k, 0) for x in F if x != "FILLER") for k in ("preflop", "post_noSD", "showdown")}
    out(f"{'avg opp seat':<16}{'':>7}{'':>16}{'':>8}{'':>9}{'':>19}" + "".join(f"{agg[k] / tf:>+9.1f}" for k in agg)
        + f"{sum(agg.values()) / tf:>+8.1f}")

with open(os.path.join(OUT, "report_detail.txt"), "w") as f:
    f.write("\n".join(lines) + "\n")
