"""Player profiles from hand histories: per-player stats, where one bot loses chips, and a field rebuilt from known bots.

usage: hhprofile.py HH... [--compare ours,claude_default_b] [--k 20] [--brief] [--min-hands 0] [--viewer NAME] [--json out]
       hhprofile.py HH... --diagnose [ours] [--top 3]
              chips won/lost by category from that bot's own histories, against the top bots (by leaderboard.json next to
              HH if present, else by chips)
       hhprofile.py HH... --rebuild LIB... [--exclude ours] [--min-hands 300] [--soft 0] [--field-out mix.json]
              match every player in HH to its nearest LIB bot (LIB: hand histories or a --json dump) and print the field
              mix as a FIELDS entry; --soft S spreads each player over library bots by exp(-(d/S)^2/2)
       hhprofile.py HH... --demo
              half of the bots held out as targets, matched against the other half
HH: files or directories of *.jsonl.gz / *.jsonl. read_hands() is the only code that knows the format; tonight point it at
the kit's reader. Records of one hand from several viewers merge. Stats use public events plus each viewer's own cards;
--viewer NAME keeps only that player's records, which is what our real histories give. --stream re-reads the files on each
pass instead of holding every hand in memory (~6 KB a hand; a full round is ~500k hands) and does not merge, so use it on
one team's histories. Rates shrink toward the pooled rate of everyone in the input with --k pseudo-opportunities; the n rows
under each player are opportunities.
Field mixes key library bots as <prefix><bot> (g_<bot> is genfield's archetype): FIELDS["seen"] = json.load(open(mix)).
"""
import argparse, gzip, hashlib, json, math, os, random, statistics, sys
from collections import Counter, defaultdict
from itertools import combinations
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ACTS = ("fold", "check", "call", "raise")
STEAL, BBS = ("CO", "BTN", "SB", "hSB"), ("BB", "hBB")
STREET = ["pre", "flop", "turn", "river"]
JAM = [(8, "<8"), (15, "8-15"), (25, "15-25"), (1e9, "25+")]
DEPTH = [(8, "<8bb"), (15, "8-15bb"), (25, "15-25bb"), (40, "25-40bb"), (1e9, "40+bb")]
HSTR = [(.05, "top 5%"), (.15, "5-15%"), (.30, "15-30%"), (.50, "30-50%"), (2, "50-100%")]
RATES = ["vpip", "pfr", "limp", "3bet", "f3b", "steal", "fts"] + ["jam" + l for _, l in JAM] + [
    "callai", "vpip4", "vpip6+", "callai4", "callai6+", "cbet", "fcb", "aggf", "wtsd", "wsd"]
MAIN = ["vpip", "pfr", "limp", "3bet", "f3b", "steal", "fts", "open", "jam<8", "jam8-15", "jam15-25", "jam25+", "callai",
        "cbet", "fcb", "aggf", "wtsd", "wsd"]  # the stats the field rebuild matches on
band = lambda x, B: next(l for hi, l in B if x < hi)
half = lambda h, salt="": int(hashlib.md5((salt + h["key"][0]).encode()).hexdigest()[:8], 16) % 2  # split by table


# ---- format layer -----------------------------------------------------------------------------------------------------
def _files(paths):
    for p in paths:
        if os.path.isdir(p):
            for r, _, fs in sorted(os.walk(p)):
                yield from (os.path.join(r, f) for f in sorted(fs) if f.endswith((".jsonl.gz", ".jsonl", ".json.gz")))
        else:
            yield p


def read_hands(paths):
    """The only code that knows the hand-history format. Yields one normalized hand per record: key (table, hand number),
    seat (the viewer's), names {seat: name}, sb, bb, stacks {seat: chips at hand start, dealt-in seats only}, hole (the
    viewer's cards or None), ev [(kind, seat, amount, cards)] in order, failed. Kinds: hand ante blind fold check
    call (chips added) raise (total for the street) board (new cards) show win stack; cards are strings like "As"."""
    si = lambda x: None if x is None else int(x)
    for f in _files(paths):
        with (gzip.open if f.endswith(".gz") else open)(f, "rt") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                yield dict(key=(str(r["table"]), r["hand"]), seat=int(r["seat"]), names={int(k): v for k, v in r["names"].items()},
                           sb=r["blinds"][0], bb=r["blinds"][1], stacks={int(k): v for k, v in r["stacks"].items() if v > 0},
                           hole=r.get("hole"), failed=r.get("failed") or [],
                           ev=[(str(e[0]).rsplit(".", 1)[-1].lower(), si(e[1]), e[2], e[3]) for e in r["events"]])


def load(paths):
    """Merged hands: one per (table, hand), with every viewer's own cards in holes and their seats in viewers."""
    H = {}
    for r in read_hands(paths):
        h = H.get(r["key"])
        if h is None:
            h = H[r["key"]] = dict(r, holes={}, viewers=set())
        h["viewers"].add(r["seat"])
        if r["hole"]:
            h["holes"][r["seat"]] = r["hole"]
    return list(H.values())


class Stream:
    """Hands re-read from the files on every pass, unmerged (each hand must appear once). viewer: only its records."""
    def __init__(self, paths, viewer=None):
        self.paths, self.viewer = paths, viewer

    def __iter__(self):
        for r in read_hands(self.paths):
            if self.viewer is None or r["names"].get(r["seat"]) == self.viewer:
                yield dict(r, holes={r["seat"]: r["hole"]} if r["hole"] else {}, viewers={r["seat"]})


def seat_of(h, name):
    return next((s for s, n in h["names"].items() if n == name), None)


def view(hands, name):
    """Only the hands `name` saw, with only its own cards: what its team's histories hold."""
    out = []
    for h in hands:
        s = seat_of(h, name)
        if s in h["viewers"]:
            out.append(dict(h, holes={s: h["holes"][s]} if s in h["holes"] else {}, viewers={s}))
    return out


# ---- cards --------------------------------------------------------------------------------------------------------------
def ci(c):
    return "23456789TJQKA".index(c[0].upper()) * 4 + "shdc".index(c[1].lower())


def pct(hole):
    """Share of starting hands at least this strong (0 = best)."""
    import pk
    return pk.pct([ci(c) for c in hole])


def equity(a, b, board, rng, n=150):
    import pk
    A, B, D = [ci(c) for c in a], [ci(c) for c in b], [ci(c) for c in board]
    rest = [c for c in range(52) if c not in A + B + D]
    k = 5 - len(D)
    runs = combinations(rest, k) if k <= 1 else (rng.sample(rest, k) for _ in range(n))
    w = t = 0
    for r in runs:
        x, y = pk.showdown(A, D + list(r)), pk.showdown(B, D + list(r))
        w += 2 if x > y else 1 if x == y else 0
        t += 2
    return w / t


# ---- one hand -----------------------------------------------------------------------------------------------------------
def positions(h):
    """Seat -> position from the blinds and the preflop acting order (seat numbers may be anonymized)."""
    bl, first = [], []
    for k, s, a, c in h["ev"]:
        if k == "board":
            break
        if k == "blind" and s not in bl:
            bl.append(s)
        elif k in ACTS and s not in first:
            first.append(s)
    seats = list(h["stacks"])
    bbs = bl[1] if len(bl) > 1 else bl[0] if bl else seats[-1]
    sbs = bl[0] if len(bl) > 1 else None
    if len(seats) == 2:
        return {s: "hBB" if s == bbs else "hSB" for s in seats}
    rest = [s for s in first if s not in bl] + [s for s in seats if s not in first and s not in bl]
    lab = ["BB", "SB", "BTN", "CO", "HJ", "LJ"] if sbs is not None else ["BB", "BTN", "CO", "HJ", "LJ"]
    pre = rest + ([sbs] if sbs is not None else []) + [bbs]
    return {s: lab[i] if i < len(lab) else "EP" for i, s in enumerate(reversed(pre))}


def replay(h):
    """Public replay of one hand. Returns (pos, eff, F, spot). F[seat]: st = [(stat, hit)] opportunities, flags for the leak
    breakdown, net chips, and its starting-hand percentile when its cards are shown or are the viewer's. spot: a showdown
    of two players with one all-in, for all-in EV."""
    st, bb = h["stacks"], h["bb"]
    S = list(st)
    n = len(S)
    pos = positions(h)
    eff = {s: min(st[s], max([st[o] for o in S if o != s] or [0])) / bb for s in S}
    left, bet, con = dict(st), dict.fromkeys(S, 0), dict.fromkeys(S, 0)
    F = {s: dict(st=[], dec=False, vol=False, pfr=False, jam=False, jampost=False, callai=False, callai_pre=False,
                 agg=False, called=False, fold=None, cbf=False, flop=False, aggn=0, pas=0) for s in S}
    add = lambda s, k, hit: F[s]["st"].append((k, bool(hit)))
    folded, shown, won, final, seen = set(), {}, Counter(), {}, set()
    street = nr = lim = callers = nst = 0
    cur, cur_by, jam_last, opener, pfa, steal_open, cb = 0, None, False, None, None, False, False
    board, last_board = [], []
    bub = "4" if n == 4 else "6+" if n >= 6 else None
    for k, s, a, c in h["ev"]:
        if k == "board":
            board = board + list(c or [])
            street = {3: 1, 4: 2, 5: 3}.get(len(board), street + 1)
            bet, cur, cur_by, jam_last, nst = dict.fromkeys(S, 0), 0, None, False, 0
            if street == 1:
                for x in S:
                    F[x]["flop"] = x not in folded
            continue
        if s not in F:
            continue
        if k in ("blind", "ante"):
            left[s] -= a
            con[s] += a
            if k == "blind":
                bet[s] += a
                if bet[s] > cur:
                    cur, cur_by = bet[s], s
            continue
        if k == "show":
            shown[s] = c
        elif k == "win":
            won[s] += a
        elif k == "stack":
            final[s] = a
        if k not in ACTS:
            continue
        f = F[s]
        fj = jam_last and cur_by != s and cur > bet[s]  # facing a shove
        last_board = board
        first = street == 0 and not f["dec"]
        if street == 0:
            if first:
                f["dec"], f["vol"], f["first"] = True, k in ("call", "raise"), k
                d = "<15bb" if eff[s] < 15 else "15-25bb" if eff[s] < 25 else "25bb+"
                f["sit"] = "facing a shove" if fj else ("unopened " + d if lim == 0 else "limped pot") if nr == 0 else \
                    "facing an open " + d if nr == 1 else "facing a 3bet+"
                if nr == 0 and pos[s] not in BBS:
                    add(s, "limp", k == "call")
                if nr == 0 and lim == 0 and pos[s] in STEAL:
                    add(s, "steal", k == "raise")
            if nr == 1 and s != opener and ("3", s) not in seen:
                seen.add(("3", s))
                add(s, "3bet", k == "raise")
            if nr == 2 and s == opener and ("f3", s) not in seen:
                seen.add(("f3", s))
                add(s, "f3b", k == "fold")
            if nr == 1 and steal_open and callers == 0 and pos[s] in BBS and s != opener and ("fs", s) not in seen:
                seen.add(("fs", s))
                add(s, "fts", k == "fold")
            if fj and ("ai", s) not in seen:
                seen.add(("ai", s))
                add(s, "callai", k != "fold")
                if bub:
                    add(s, "callai" + bub, k != "fold")
        elif street == 1:
            if s == pfa and nst == 0 and ("cb", s) not in seen:
                seen.add(("cb", s))
                add(s, "cbet", k == "raise")
            if cb and nst == 1 and s != pfa and ("fc", s) not in seen:
                seen.add(("fc", s))
                add(s, "fcb", k == "fold")
        if k == "fold":
            folded.add(s)
            f["fold"] = street
            f["cbf"] = street == 1 and cb and nst == 1
        elif k == "call":
            left[s] -= a
            bet[s] += a
            con[s] += a
            f["called"] = True
            if fj:
                f["callai"] = True
                f["callai_pre"] |= street == 0
            if street == 0:
                callers += 1
                lim += nr == 0
            else:
                f["pas"] += 1
        elif k == "raise":
            d = a - bet[s]
            left[s] -= d
            con[s] += d
            bet[s] = a
            jam = left[s] <= 0 or a >= max([bet[o] + left[o] for o in S if o != s and o not in folded] or [0])
            f["agg"] = True
            if street == 0:
                if nr == 0:
                    opener, steal_open = s, lim == 0 and pos[s] in STEAL
                    if lim == 0 and not jam:
                        f["open"] = a / bb
                nr += 1
                pfa, callers, f["pfr"] = s, 0, True
                f["jam"] |= jam
                if jam and first:
                    f["first"] = "jam"
            else:
                f["aggn"] += 1
                f["jampost"] |= jam
                cb |= street == 1 and nst == 0 and s == pfa
                nst += 1
            cur, cur_by, jam_last = max(cur, a), s, jam
    for s in S:
        f = F[s]
        if f["dec"]:
            for key, hit in (("vpip", f["vol"]), ("pfr", f["pfr"]), ("jam" + band(eff[s], JAM), f["jam"])):
                add(s, key, hit)
            if bub:
                add(s, "vpip" + bub, f["vol"])
        if f["flop"]:
            add(s, "wtsd", s in shown)
        f["wsd"] = s in shown and won[s] - max(0, con[s] - max([con[o] for o in S if o != s] or [0])) > 0
        if s in shown:
            add(s, "wsd", f["wsd"])
        if f["aggn"] + f["pas"]:
            F[s]["st"] += [("aggf", True)] * f["aggn"] + [("aggf", False)] * f["pas"]
        f["net"] = final[s] - st[s] if s in final else won[s] - con[s]
        f["con"] = con[s]
        hole = shown.get(s) or h["holes"].get(s)
        f["pct"] = pct(hole) if hole else None
        f["end_street"], f["shown"] = street, s in shown
    spot = None
    sh = [s for s in S if s in shown]
    if len(sh) == 2 and any(left[s] <= 0 for s in sh):
        cap = min(con[x] for x in sh)
        spot = dict(sh=sh, holes=[shown[x] for x in sh], board=last_board, pot=sum(min(con[i], cap) for i in S),
                    ret=[sum(min(con[i], con[x]) - min(con[i], cap) for i in S) for x in sh], con=[con[x] for x in sh])
    return pos, eff, F, spot


# ---- profiles -----------------------------------------------------------------------------------------------------------
def profile(hands, k=20.0):
    """name -> dict(hands, tables, s={stat: (shrunk value, opportunities)}, raw counts); also returns the pooled prior."""
    P = defaultdict(lambda: dict(c=Counter(), jam=[], call=[], tables=set()))
    for h in hands:
        pos, eff, F, _ = replay(h)
        for s, f in F.items():
            p = P[h["names"].get(s, f"seat{s}")]
            c = p["c"]
            c["hands"] += 1
            p["tables"].add(h["key"][0])
            for key, hit in f["st"]:
                c[key + "#"] += 1
                c[key] += hit
            if "open" in f:
                c["open"] += f["open"]
                c["open#"] += 1
            if f["pct"] is not None:
                if f["jam"]:
                    p["jam"].append(f["pct"])
                if f["callai_pre"]:
                    p["call"].append(f["pct"])
    return shrink({n: dict(raw=dict(p["c"]), tables=len(p["tables"]), jam=p["jam"], call=p["call"]) for n, p in P.items()}, k)


def shrink(P, k):
    pool = Counter()
    for p in P.values():
        pool.update(p["raw"])
    prior = {r: pool[r] / pool[r + "#"] if pool[r + "#"] else 0.0 for r in RATES + ["open"]}
    for p in P.values():
        c = Counter(p["raw"])
        s = p["s"] = {r: ((c[r] + k * prior[r]) / (c[r + "#"] + k), c[r + "#"]) for r in RATES + ["open"]}
        s["af"] = (s["aggf"][0] / max(1e-9, 1 - s["aggf"][0]), s["aggf"][1])
        for key in ("jam", "call"):
            v = p[key]
            s[key + "hand"] = (statistics.median(v) if v else None, len(v))
        p["hands"] = c["hands"]
    return P, prior


GROUPS = [
    ("PREFLOP  (open: avg first-in raise, bb)", [("VPIP", "vpip"), ("PFR", "pfr"), ("limp", "limp"), ("3bet", "3bet"),
                                                 ("F3bet", "f3b"), ("steal", "steal"), ("FtStl", "fts"), ("open", "open")]),
    ("ALL-IN  (jam% by effective stack in bb; jamHd/callHd: median top-x% of known hands jammed / called all-in with)",
     [("j<8", "jam<8"), ("j8-15", "jam8-15"), ("j15-25", "jam15-25"), ("j25+", "jam25+"), ("callAI", "callai"),
      ("jamHd", "jamhand"), ("callHd", "callhand")]),
    ("BUBBLE  (4 players left vs 6+)", [("VPIP4", "vpip4"), ("VPIP6+", "vpip6+"), ("cAI4", "callai4"), ("cAI6+", "callai6+")]),
    ("POSTFLOP", [("cbet", "cbet"), ("Fcbet", "fcb"), ("AF", "af"), ("WTSD", "wtsd"), ("W$SD", "wsd")]),
]


def fmt(key, v):
    if v is None:
        return "-"
    return f"{v:.2f}" if key in ("open", "af") else f"{100 * v:.1f}"


def table(P, hi=(), brief=False, min_hands=0, out=print):
    tty = sys.stdout.isatty()
    B, D, E = ("\033[1m", "\033[2m", "\033[0m") if tty else ("", "", "")
    rows = sorted((n for n in P if P[n]["hands"] >= min_hands or n in hi), key=lambda n: -P[n]["hands"])
    for title, cols in GROUPS:
        out(f"\n{title}\n  {'player':<22}{'hands':>7}{'tbls':>6}" + "".join(f"{c:>8}" for c, _ in cols))
        for n in rows:
            s, mk = P[n]["s"], n in hi
            out(f"{B if mk else ''}{'>' if mk else ' '} {n[:22]:<22}{P[n]['hands']:>7}{P[n]['tables']:>6}"
                + "".join(f"{fmt(k, s[k][0]):>8}" for _, k in cols) + (E if mk else ""))
            if not brief:
                out(f"{D}  {'':<22}{'':>7}{'n':>6}" + "".join(f"{s[k][1]:>8}" for _, k in cols) + E)


# ---- leak diagnosis -----------------------------------------------------------------------------------------------------
def categories(f, pos, eff, s, own):
    fold, end = f["fold"], f["end_street"]
    if fold is not None:
        if fold == 0:
            e = "pre: fold, nothing in" if not f["con"] else "pre: fold blind" if not f["vol"] else "pre: fold after putting chips in"
        else:
            e = "flop: fold to c-bet" if f["cbf"] else STREET[fold] + ": fold"
    else:
        e = ("showdown: won" if f["wsd"] else "showdown: lost") if f.get("shown") else STREET[end] + ": won uncontested"
    if f["jam"]:
        a = "jam preflop"
    elif f["callai"]:
        a = "call an all-in"
    elif f["jampost"]:
        a = "jam postflop"
    elif fold is not None:
        a = ("fold, nothing in" if not f["con"] else "fold the blind") if fold == 0 and not f["vol"] else \
            "raised off (fold after own bet/raise)" if f["agg"] else "fold after calling/checking"
    else:
        a = "showdown, no all-in" if f.get("shown") else "won without showdown"
    return dict(end=e, action=a, spot=f"{f['sit']}: {f['first']}" if f["dec"] else "no preflop decision",
                position=pos[s], depth=band(eff[s], DEPTH), hand="cards not known" if own is None else band(own, HSTR))


def diagnose_all(hands):
    """Per player: dim -> category -> [hands, chips], tables, hands, net, all-in spots. Everything but the starting-hand
    breakdown is public, so it covers opponents too; that one uses only a viewer's own cards."""
    R = defaultdict(lambda: dict(D=defaultdict(lambda: defaultdict(lambda: [0, 0])), tables=set(), hands=0, net=0, spots=[]))
    for h in hands:
        pos, eff, F, spot = replay(h)
        shown = set(spot["sh"]) if spot else set()
        for s, f in F.items():
            r = R[h["names"].get(s, f"seat{s}")]
            r["tables"].add(h["key"][0])
            r["hands"] += 1
            r["net"] += f["net"]
            own = pct(h["holes"][s]) if s in h["viewers"] and h["holes"].get(s) else None
            for dim, cat in categories(f, pos, eff, s, own).items():
                x = r["D"][dim][cat]
                x[0] += 1
                x[1] += f["net"]
            if s in shown:
                i = spot["sh"].index(s)
                r["spots"].append((spot["holes"][i], spot["holes"][1 - i], spot["board"], spot["pot"], spot["ret"][i], spot["con"][i], f["net"]))
    for r in R.values():
        r["tables"] = len(r["tables"])
    return R


def allin_ev(spots, seed=7):
    """(actual, EV) chips summed over heads-up all-in showdowns; EV uses equity when the last chips went in."""
    rng = random.Random(seed)
    act = ev = 0.0
    for a, b, board, pot, ret, con, net in spots:
        act += net
        ev += equity(a, b, board, rng) * pot + ret - con
    return act, ev


def find_board(paths):
    for p in paths:
        d = p if os.path.isdir(p) else os.path.dirname(p)
        for q in (os.path.join(d, "leaderboard.json"), os.path.join(d, "..", "leaderboard.json")):
            if os.path.exists(q):
                return {r["name"]: r for r in json.load(open(q))["board"]}
    return {}


def diagnose(hands, name, top, board, P, out=print):
    R = diagnose_all(hands)
    if name not in R:
        sys.exit(f"{name} not dealt in anywhere")
    others = [n for n in R if n != name and R[n]["tables"] >= max(5, R[name]["tables"] / 5)]
    rank = sorted(others, key=lambda n: -(board[n]["mean"] if n in board else R[n]["net"] / R[n]["tables"]))
    tops = rank[:top]
    pts = lambda n: f"{board[n]['mean']:.2f} pts" if n in board else ""
    cpt = lambda n, x: x / R[n]["tables"]
    me = R[name]
    out(f"\nDIAGNOSIS {name}: {me['tables']} tables, {me['hands']} hands dealt in, net {cpt(name, me['net']):+.0f} chips/table {pts(name)}")
    out("top: " + ", ".join(f"{n} ({cpt(n, R[n]['net']):+.0f} chips/table{', ' + pts(n) if pts(n) else ''})" for n in tops))
    out(f"field = the {len(others)} other players seen at {max(5, me['tables'] // 5)}+ tables. freq = hands per table, chips = net chips per table. "
        "All public except the starting-hand breakdown, which needs the player's own cards")
    leaks = []
    for dim in ("end", "action", "spot", "position", "depth", "hand"):
        cats = sorted({c for n in [name] + others for c in R[n]["D"][dim]}, key=lambda c: R[name]["D"][dim][c][1])
        out(f"\n  {dim:<38}{'freq':>7}{'chips':>8}   {'top freq':>8}{'chips':>8}   {'field':>7}{'chips':>8}   {name + '-top':>9}")
        g = lambda ns, c, i: sum(R[n]["D"][dim][c][i] / R[n]["tables"] for n in ns) / len(ns)
        for c in cats:
            mf, mc = g([name], c, 0), g([name], c, 1)
            tf, tc = g(tops, c, 0), g(tops, c, 1)
            if max(mf, tf) < 0.05:
                continue
            out(f"  {c:<38}{mf:>7.1f}{mc:>8.0f}   {tf:>8.1f}{tc:>8.0f}   {g(others, c, 0):>7.1f}{g(others, c, 1):>8.0f}   {mc - tc:>+9.0f}")
            if dim in ("action", "spot", "position", "depth") and c not in ("won without showdown", "showdown, no all-in"):
                leaks.append((mc - tc, dim, c, mf, mc, tf, tc))
    out(f"\n  ALL-IN LUCK (heads-up all-in showdowns; EV at the moment the last chips went in), chips/table")
    out(f"  {'player':<22}{'spots/tbl':>10}{'actual':>8}{'EV':>8}{'luck':>8}")
    for n in [name] + tops:
        a, e = allin_ev(R[n]["spots"])
        out(f"  {n:<22}{len(R[n]['spots']) / R[n]['tables']:>10.2f}{cpt(n, a):>8.0f}{cpt(n, e):>8.0f}{cpt(n, a - e):>+8.0f}")
    out(f"\n  BIGGEST GAPS TO THE TOP BOTS in the decision breakdowns (chips/table; breakdowns overlap, each sums to the net;")
    out(f"  freq x chips per hand for {name} and the top bots)")
    for i, (d, dim, c, mf, mc, tf, tc) in enumerate(sorted(leaks)[:8]):
        per = lambda x, f: x / f if f else 0
        out(f"  {i + 1}. {dim + ': ' + c:<48} {d:>+6.0f}   {name} {mf:.1f}/tbl x {per(mc, mf):+.0f}   top {tf:.1f}/tbl x {per(tc, tf):+.0f}")
    out("")
    table({n: P[n] for n in [name] + tops if n in P}, hi=(name,), brief=True, out=out)


# ---- field rebuild ------------------------------------------------------------------------------------------------------
def scales(profs):
    """Spread of each MAIN stat across the given profiles, floored, so distances read in units of between-bot spread."""
    return {m: max(0.15 if m == "open" else 0.02, statistics.pstdev([p["s"][m][0] for p in profs])) for m in MAIN}


def dist(p, q, sc, kw=30.0):
    """RMS over MAIN of (difference / spread), each stat weighted by n/(n+kw) with n the pair's effective opportunities,
    so thin stats count less. Returns (distance, the two stats that differ most)."""
    num = den = 0.0
    zs = []
    for m in MAIN:
        (x, nx), (y, ny) = p["s"][m], q["s"][m]
        if nx and ny:
            ne = 1 / (1 / nx + 1 / ny)
            w, z = ne / (ne + kw), (x - y) / sc[m]
            num += w * z * z
            den += w
            zs.append((abs(z), m, x, y))
    return (math.sqrt(num / den) if den else 9e9), sorted(zs, reverse=True)[:2]


def halves(hands, k, salt=""):
    """Profiles on two halves of the tables; dist(half1, half2) / 2 approximates a perfect match's distance at full size."""
    return profile((h for h in hands if half(h, salt)), k)[0], profile((h for h in hands if not half(h, salt)), k)[0]


def rebuild(T, L, prefix="g_", soft=0.0, split=None, out=print):
    """Each target weighs the number of tables it was seen at. Hard (soft=0): all of it goes to its nearest library bot.
    soft=s spreads it over library bots with weight exp(-(d/s)^2 / 2). split: (half1, half2) target profiles for the noise
    column (the distance a perfect match would show). * marks a nearest distance over twice that and over 0.6: no library
    bot plays like the target. Distances are in units of the between-bot spread; two different bots sit near 1."""
    sc = scales(list(T.values()) + list(L.values()))
    mix = Counter()
    out(f"\n{'target':<22}{'hands':>7}{'tbls':>6}  {'nearest':<20}{'d':>5}{'noise':>6}  {'2nd':<20}{'d':>5}   biggest differences (target/match)")
    for t in sorted(T, key=lambda t: -T[t]["hands"]):
        M = sorted((*dist(T[t], q, sc), b) for b, q in L.items())
        (d1, z1, b1), (d2, _, b2) = M[0], M[1] if len(M) > 1 else (float("nan"), [], "-")
        nz = dist(split[0][t], split[1][t], sc)[0] / 2 if split and t in split[0] and t in split[1] else float("nan")
        if soft:
            ws = [math.exp(-0.5 * (d / soft) ** 2) for d, _, _ in M]
            for w, (_, _, b) in zip(ws, M):
                mix[prefix + b] += T[t]["tables"] * w / sum(ws)
        else:
            mix[prefix + b1] += T[t]["tables"]
        diff = ", ".join(f"{m} {fmt(m, x)}/{fmt(m, y)}" for _, m, x, y in z1)
        out(f"{t[:22]:<22}{T[t]['hands']:>7}{T[t]['tables']:>6}  {b1[:20]:<20}{d1:>5.2f}{nz:>6.2f}{'*' if d1 > max(2 * nz, 0.6) else ' '} "
            f"{b2[:20]:<20}{d2:>5.2f}   {diff}")
    tot = sum(mix.values())
    return {k: round(v / tot, 3) for k, v in mix.most_common() if v / tot >= 0.0005}


def lib_profiles(paths, k, exclude):
    if len(paths) == 1 and paths[0].endswith(".json"):
        P, _ = shrink(json.load(open(paths[0])), k)
    else:
        P, _ = profile(load(paths), k)
    return {n: p for n, p in P.items() if n not in exclude}


def demo(hands, k, soft=0.5, ours="ours", out=print):
    """Tables split in two by id. Library: the bots profiled on half A from every viewer. Targets: profiled on half B
    from `ours`'s records only (public cards plus our own), like tonight's real histories."""
    A = lambda h: half(h) == 0
    PA, _ = profile([h for h in hands if A(h)], k)
    hb = [h for h in hands if not A(h)]
    if any(seat_of(h, ours) in h["viewers"] for h in hb):
        hb = view(hb, ours)
    PB, _ = profile(hb, k)
    split = halves(hb, k, "noise")
    bots = sorted(n for n in PA if n != ours and n in PB and PB[n]["hands"] >= 200)
    tgt, lib = bots[0::2], bots[1::2]
    out(f"DEMO: targets from {len(hb)} hands as {ours} saw them (half B of the tables), library from the other {sum(map(A, hands))}")
    out(f"\n1) self-identification: each bot's half-B profile against all {len(bots)} half-A profiles")
    sc = scales([PB[b] for b in bots] + [PA[b] for b in bots])
    hit = 0
    for b in bots:
        M = sorted((dist(PB[b], PA[x], sc)[0], x) for x in bots)
        r = [x for _, x in M].index(b) + 1
        hit += r == 1
        out(f"   {b:<22} nearest {M[0][1]:<20} d={M[0][0]:.2f}   itself d={dict((x, d) for d, x in M)[b]:.2f}, rank {r}"
            f"   2nd-best other d={min(d for d, x in M if x != b):.2f}")
    out(f"   matched itself: {hit}/{len(bots)}")
    out(f"\n2) holdout: targets {', '.join(tgt)}\n   library {', '.join(lib)}")
    mix = rebuild({b: PB[b] for b in tgt}, {b: PA[b] for b in lib}, split=split)
    out(f"\nFIELDS entry (nearest): {json.dumps(mix)}")
    out(f"FIELDS entry (--soft {soft:g}):  {json.dumps(rebuild({b: PB[b] for b in tgt}, {b: PA[b] for b in lib}, soft=soft, out=lambda *_: None))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("hh", nargs="+")
    ap.add_argument("--compare", default="")
    ap.add_argument("--k", type=float, default=20.0)
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("--min-hands", type=int, default=0)
    ap.add_argument("--viewer")
    ap.add_argument("--stream", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--diagnose", nargs="?", const="ours")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--rebuild", nargs="+", metavar="LIB")
    ap.add_argument("--exclude", default="ours")
    ap.add_argument("--prefix", default="g_")
    ap.add_argument("--field-out")
    ap.add_argument("--soft", type=float, default=0.0)
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.stream:
        hands = Stream(a.hh, a.viewer)
    else:
        hands = load(a.hh)
        if a.viewer:
            hands = view(hands, a.viewer)
    if a.demo:
        demo(list(hands), a.k, a.soft or 0.5)
        return
    P, prior = profile(hands, a.k)
    if a.json:
        json.dump({n: dict(raw=p["raw"], tables=p["tables"], jam=p["jam"], call=p["call"]) for n, p in P.items()}, open(a.json, "w"))
    if a.diagnose:
        diagnose(hands, a.diagnose, a.top, find_board(a.hh), P)
        return
    if a.rebuild:
        ex = set(a.exclude.split(","))
        T = {n: p for n, p in P.items() if n not in ex and p["hands"] >= a.min_hands}
        L = lib_profiles(a.rebuild, a.k, ex)
        print(f"FIELD REBUILD: {len(T)} players with {a.min_hands}+ hands matched against {len(L)} library bots")
        mix = rebuild(T, L, a.prefix, a.soft, halves(hands, a.k))
        print(f"\nFIELDS entry: {json.dumps(mix)}")
        if a.field_out:
            json.dump(mix, open(a.field_out, "w"), indent=1)
        return
    print(f"{sum(p['hands'] for p in P.values())} seat-hands, {len(P)} players; rates in %, shrunk toward the pool with k={a.k:g}")
    table(P, hi=set(x for x in a.compare.split(",") if x), brief=a.brief, min_hands=a.min_hands)


if __name__ == "__main__":
    main()
