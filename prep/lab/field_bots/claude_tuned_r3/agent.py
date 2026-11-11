"""claude_tuned_r3: a parameterized No-Limit Hold'em tournament bot.

Design (see NOTES.md):
  * Preflop: hand classes ranked by precomputed equity; opening ranges, 3-bet / call thresholds and sizes are
    tunable numbers. Short-stack and all-in spots are decided by ICM expected points, using precomputed
    equity of every hand class against "top x%" ranges and per-seat fold / raise frequencies read from memory.
  * Postflop: eval7 Monte Carlo equity against a range estimated from the preflop action, narrowed when
    facing bets according to the bettor's observed aggression and the bet size; thresholds are tunable.
  * Memory carries only per-seat frequency counters for the current table (compact JSON).
Every decision is wrapped so any error falls back to check / fold, and every returned action is validated
against the offered legal actions.
"""
import json
import math
import os
import random
import time

import poker_agent_sdk
from poker_agent_sdk import Action

try:
    import eval7
except Exception:  # pragma: no cover - eval7 is available on the real machines
    eval7 = None

# --------------------------------------------------------------------------------------------- parameters
P0 = {
    # opening ranges (top fraction of hands) by players left to act behind me in an unopened pot
    "open_ep": 0.0853, "open_mp": 0.17, "open_co": 0.25, "open_btn": 0.38, "open_sb": 0.6644,
    "open_bb": 2.3,        # open size in big blinds
    "limp_add": 1.0,       # extra big blinds per limper
    "iso_pct": 0.102,       # raise over limpers with the top x
    "limp_pct": 0.30,      # limp behind with the top x when the price is one big blind
    "bb_raise_pct": 0.07,  # raise from the BB over limpers
    "steal_adapt": 0.8,    # widen steals against blinds that over-fold
    # short-stack shove / call model (ICM)
    "shove_bb": 13.0,      # effective stack (bb) at or below which unopened pots are shove-or-fold
    "sc_base": 0.1913,       # prior fraction of hands an opponent calls a 10bb shove with
    "sc_exp": 0.55,        # how the call fraction shrinks with shove size
    "bb_call_mult": 1.35,  # big blind calls wider
    "adapt": 0.8,          # weight on observed frequencies vs priors
    "shove_margin": 0.0,   # required ICM gain (points) to shove
    "ai_call_margin": 0.0,  # required ICM gain (points) to call an all-in
    "sv_base": 0.315,       # prior shove range of an opener shoving 10bb
    "sv_exp": 0.6,
    "behind_pen": 0.15,    # points of margin per live player still behind when calling all-in
    "fold_tax": 0.7,       # big blinds charged to folding in all-in decisions (rising-blind pressure)
    # facing raises (deeper stacks)
    "pfr_prior": 0.20, "rng_mult": 1.32, "rr_mult": 0.3325,
    "tb_eq": 0.60,         # 3-bet for value when equity vs raiser's range >= this
    "tb_mult": 3.0,        # 3-bet size multiplier (x raise)
    "fb_eq": 0.59,         # 4-bet all-in when equity vs 3-bettor >= this
    "call_margin": 0.12,   # preflop call: equity >= price + margin
    "mw": 0.75,            # multiway equity exponent per extra opponent
    "reshove_bb": 25.0,    # re-shove consideration below this effective stack
    "call_3b_frac": 0.35,  # fraction of an opener's range that calls a re-shove
    "commit_frac": 0.5,    # bets/raises above this share of stack become all-in
    # round 2: light 3-bets (the field folds ~75% to 3-bets)
    "l3_pct": 0.32,        # light 3-bet candidates: top x of hands (below the value 3-bet threshold)
    "l3_freq": 0.55,       # base frequency
    "l3_ftmin": 0.5,       # only against openers whose fold-to-raise estimate is at least this
    "l3_maxbb": 8.0,       # opener's raise size (bb) above which we do not light 3-bet
    # round 3: 3-bettor range = observed re-raise frequency (prior x3_prior) x x3_mult
    "x3_on": 0,            # off: tested in round 3 and it lost locally (see NOTES.md)
    "x3_prior": 0.09, "x3_mult": 1.1,
    # postflop
    "mc_iters": 500,
    "vb1": 0.6, "vb2": 0.68, "vb3": 0.70,   # value-bet equity thresholds by street
    "bs1": 0.75, "bs2": 0.575, "bs3": 0.70,   # bet sizes (fraction of pot)
    "bf1": 0.55, "bf2": 0.324, "bf3": 0.45,   # assumed betting-range fraction of a bettor
    "bs_exp": 0.35,        # bigger bets -> narrower range
    "af_adapt": 0.7,       # use observed aggression
    "raise_f": 0.495,       # range narrowing when facing a raise on the street
    "cm1": 0.03, "cm2": 0.01, "cm3": 0.005,    # call margins over pot odds
    "rz1": 0.82, "rz2": 0.84, "rz3": 0.86,   # raise thresholds (equity vs betting range)
    "rz_frac": 0.9,        # raise size: fraction of (pot + call)
    "cbet": 0.85,          # continuation-bet frequency heads-up as preflop raiser
    "bl1": 0.18, "bl2": 0.16, "bl3": 0.08,   # bluff frequency when checked to (<= 2 opponents)
    "bl_max3": 0.25,       # river bluffs only with equity below this
    "fold_adapt": 1.6,     # scale bluffing by opponents' observed fold-to-bet
    "jam_spr": 0.35,        # if stack behind after betting < jam_spr * pot, just jam
}

# priors for opponent stats
W_PRIOR = 6.0
FTR_PRIOR = 0.65   # fold to a preflop raise
VPIP_PRIOR = 0.30
AF_PRIOR = 0.40    # postflop bets+raises / (bets+raises+calls+checks)
FTB_PRIOR = 0.45   # fold to a postflop bet

# --------------------------------------------------------------------------------------------- tables
RANKS = "AKQJT98765432"
_RIDX = {r: i for i, r in enumerate(RANKS)}
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_tables():
    with open(os.path.join(_HERE, "pf_tables.json")) as f:
        return json.load(f)


_T = _load_tables()
CLASSES = _T["classes"]
CIDX = {c: i for i, c in enumerate(CLASSES)}
PCT = _T["pct"]
BUCKETS = _T["buckets"]
EQ_TOP = _T["eq_top"]
EQ_MULTI = _T["eq_multi"]
NB = len(BUCKETS)

# postflop opponent ranges (eval7 HandRange objects built once at import)
POST_BUCKETS = [0.11, 0.2, 0.3, 0.4, 0.6, 1.0]
_ORDER = _T["order"]


def _range_string(x):
    cum, names = 0, []
    sizes = {c: (6 if len(c) == 2 else (4 if c[2] == "s" else 12)) for c in _ORDER}
    for c in _ORDER:
        if cum >= x * 1326 - 1e-6:
            break
        names.append(c)
        cum += sizes[c]
    return ",".join(names)


if eval7 is not None:
    CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in "shdc"}
    POST_RANGES = [eval7.HandRange(_range_string(x)) for x in POST_BUCKETS]
    _MC = eval7.py_hand_vs_range_monte_carlo
    _EXACT = eval7.py_hand_vs_range_exact
else:
    CARD, POST_RANGES, _MC, _EXACT = {}, [], None, None


def hand_class(c1, c2):
    r1, r2 = _RIDX[c1[0]], _RIDX[c2[0]]
    if r1 == r2:
        return CIDX[c1[0] + c2[0]]
    if r1 > r2:
        r1, r2 = r2, r1
    return CIDX[RANKS[r1] + RANKS[r2] + ("s" if c1[1] == c2[1] else "o")]


def eq_top(h, x):
    """Equity of hand class h against the top-x fraction of hands."""
    row = EQ_TOP[h]
    if x <= BUCKETS[0]:
        return row[0]
    if x >= 1.0:
        return row[-1]
    for i in range(1, NB):
        b = BUCKETS[i]
        if x <= b:
            a = BUCKETS[i - 1]
            t = (x - a) / (b - a)
            return row[i - 1] + (row[i] - row[i - 1]) * t
    return row[-1]


# --------------------------------------------------------------------------------------------- ICM
def icm(st, me, pays):
    """Expected payout of player `me` given positive stacks `st` and payouts `pays` (desc, trimmed to len(st))."""
    n = len(st)
    S = 0.0
    for v in st:
        S += v
    x = st[me]
    if x <= 0 or S <= 0:
        return 0.0
    k = len(pays)
    if k > n:
        k = n
    if k == 1:
        return pays[0] * x / S
    p1 = pays[1]
    p2 = pays[2] if k >= 3 else 0.0
    q1 = x / S
    q2 = q3 = 0.0
    for j in range(n):
        if j == me:
            continue
        sj = st[j]
        if sj <= 0:
            continue
        Sj = S - sj
        pj = sj / S
        a2 = pj * x / Sj
        q2 += a2
        if k >= 3:
            acc = 0.0
            for m in range(n):
                if m == me or m == j:
                    continue
                sm = st[m]
                if sm <= 0:
                    continue
                acc += sm / (Sj - sm)
            q3 += a2 * acc
    v = pays[0] * q1 + p1 * q2 + p2 * q3
    if k > 3:
        # places 4..k (only if a round changes the payouts): spread the remaining probability evenly.
        # Cheap approximation that keeps the decision time bounded.
        rest = max(0.0, 1.0 - q1 - q2 - q3)
        v += rest * sum(pays[3:k]) / max(1, n - 3)
    return v


def outcome_value(finals, me_key, pays):
    """finals: dict seat -> chips after the hand. Returns my expected points (busted -> place payout)."""
    alive = [s for s, c in finals.items() if c > 0]
    if finals.get(me_key, 0) <= 0:
        place = len(alive)  # zero-based index of my place (others alive finish above me)
        return pays[place] if place < len(pays) else 0.0
    st = [finals[s] for s in alive]
    return icm(st, alive.index(me_key), pays[:len(alive)])


# --------------------------------------------------------------------------------------------- helpers
def _kn(k):
    if isinstance(k, str):
        return k.lower()
    n = getattr(k, "name", None)
    if isinstance(n, str):
        return n.lower()
    return str(getattr(k, "value", k)).lower()


def _norm_kind(s):
    if "fold" in s:
        return "fold"
    if "check" in s:
        return "check"
    if "call" in s:
        return "call"
    if "raise" in s or "bet" in s:
        return "raise"
    return s


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


class Ctx:
    pass


# --------------------------------------------------------------------------------------------- memory / stats
# per-seat counters: n hands acted preflop, vpip, pfr, faced raise, folded to raise,
#                    post aggressive, post passive, faced bet, folded to bet, re-raised when facing a raise
N_STATS = 10


def load_mem(memory):
    if memory:
        try:
            d = json.loads(memory.decode() if isinstance(memory, (bytes, bytearray)) else memory)
            st = {int(k): v for k, v in d["s"].items()}
            for v in st.values():
                while len(v) < N_STATS:
                    v.append(0)
            return st, d["c"]
        except Exception:
            pass
    return {}, [0, 0, 0, 0, [], [], []]  # [hand, street, raises_pf, bet_on_street, acted, vpip, pfr]


def dump_mem(st, cur):
    return json.dumps({"s": st, "c": cur}, separators=(",", ":")).encode()


def process_events(events, st, cur):
    hand, street, nr, bos, acted, vp, pr = cur
    acted, vp, pr = set(acted), set(vp), set(pr)
    for e in events:
        k = e.kind
        if k.__class__ is not str:
            k = _kn(k)
        if k == "hand":
            hand = e.amount or 0
            street, nr, bos = 0, 0, 0
            acted, vp, pr = set(), set(), set()
            continue
        if k == "board":
            street += 1
            bos = 0
            continue
        if k not in ("fold", "check", "call", "raise"):
            continue
        s = e.seat
        a = st.get(s)
        if a is None:
            a = st[s] = [0] * N_STATS
        if street == 0:
            if s not in acted:
                acted.add(s)
                a[0] += 1
            if nr > 0:
                a[3] += 1
                if k == "fold":
                    a[4] += 1
                elif k == "raise":
                    a[9] += 1
            if k == "call" or k == "raise":
                if s not in vp:
                    vp.add(s)
                    a[1] += 1
                if k == "raise":
                    nr += 1
                    if s not in pr:
                        pr.add(s)
                        a[2] += 1
        else:
            if bos:
                a[7] += 1
                if k == "fold":
                    a[8] += 1
            if k == "raise":
                a[5] += 1
                bos = 1
            elif k == "call" or k == "check":
                a[6] += 1
    return [hand, street, nr, bos, sorted(acted), sorted(vp), sorted(pr)]


def _rate(num, den, prior):
    return (num + prior * W_PRIOR) / (den + W_PRIOR)


# --------------------------------------------------------------------------------------------- agent
class Agent(poker_agent_sdk.Agent):
    def __init__(self, params=None):
        self.P = dict(P0)
        if params:
            self.P.update(params)

    def act(self, state, memory):
        self._t0 = time.perf_counter()
        legal = {}
        try:
            for la in state.legal_actions:
                legal[_norm_kind(_kn(la.kind))] = la
        except Exception:
            pass
        mem_out = memory if memory is not None else b""
        try:
            st, cur = load_mem(memory)
            try:
                cur = process_events(state.events or [], st, cur)
            except Exception:
                pass
            mem_out = dump_mem(st, cur)
            dec, amt = self.decide(state, st, legal)
        except Exception:
            dec, amt = "fold", 0
        return self.to_action(dec, amt, legal), mem_out

    # ------------------------------------------------------------------ legal action construction
    @staticmethod
    def to_action(dec, amt, legal):
        if dec == "raise":
            la = legal.get("raise")
            if la is not None:
                try:
                    lo = int(math.ceil(la.min_amount))
                    hi = int(math.floor(la.max_amount))
                    if lo <= hi:
                        a = int(amt)
                        a = lo if a < lo else (hi if a > hi else a)
                        return Action.raise_to(a)
                except Exception:
                    pass
            dec = "call"
        if dec == "call":
            if "call" in legal:
                return Action.call()
            if "check" in legal:
                return Action.check()
            return Action.fold()
        if "check" in legal:
            return Action.check()
        if "fold" in legal:
            return Action.fold()
        if "call" in legal:
            return Action.call()
        return Action.check()

    # ------------------------------------------------------------------ main decision
    def decide(self, state, stats, legal):
        P = self.P
        c = Ctx()
        c.me = state.seat
        seats = state.seats
        c.seat_obj = {}
        for s in seats:
            c.seat_obj[s.seat] = s
        mine = c.seat_obj[c.me]
        c.bb = float(state.blinds[1]) if state.blinds else 20.0
        c.pot = float(state.pot)
        c.to_call = float(state.to_call or 0)
        c.my_bet = float(mine.bet or 0)
        c.my_stack = float(mine.stack)
        c.my_total = c.my_stack + c.my_bet
        status = {}
        for s in seats:
            status[s.seat] = _kn(s.status)
        c.status = status
        c.alive = [s.seat for s in seats
                   if s.seat == c.me or (status[s.seat] != "busted" and (s.stack + (s.bet or 0)) > 0)]
        c.opps = [s.seat for s in seats if s.seat != c.me and status[s.seat] in ("active", "all_in")]
        c.live_opps = [x for x in c.opps if status[x] == "active"]
        opp_tot = [c.seat_obj[x].stack + (c.seat_obj[x].bet or 0) for x in c.opps]
        c.eff = min(c.my_total, max(opp_tot)) if opp_tot else c.my_total
        try:
            pays = [float(p) for p in state.config.payouts]
        except Exception:
            pays = [50.0, 30.0, 20.0]
        while pays and pays[-1] <= 0:
            pays.pop()
        c.pays = pays or [1.0]
        c.cards = list(state.cards)
        c.board = list(state.board or [])
        c.stats = stats

        # parse this hand's history
        hist = state.history or []
        street = 0
        c.sb_seat = c.bb_seat = None
        c.pf_raises = 0
        c.limpers = 0
        c.pf_raiser = None
        c.pf_callers = 0
        c.st_raises = 0
        c.st_aggr = None
        for e in hist:
            k = e.kind
            if k.__class__ is not str:
                k = _kn(k)
            if k == "blind":
                if c.sb_seat is None:
                    c.sb_seat = e.seat
                else:
                    c.bb_seat = e.seat
            elif k == "board":
                street += 1
                c.st_raises = 0
                c.st_aggr = None
            elif k == "raise":
                if street == 0:
                    c.pf_raises += 1
                    c.pf_raiser = e.seat
                    c.pf_callers = 0
                c.st_raises += 1
                c.st_aggr = e.seat
            elif k == "call" and street == 0:
                if c.pf_raises == 0:
                    c.limpers += 1
                else:
                    c.pf_callers += 1
        if c.bb_seat is None and c.sb_seat is not None:
            # only one blind posted (rare); treat it as the big blind
            c.bb_seat, c.sb_seat = c.sb_seat, None

        if not c.board:
            return self.preflop(state, c)
        return self.postflop(state, c)

    # ------------------------------------------------------------------ opponent models
    def ftr(self, c, seat):
        a = c.stats.get(seat)
        if a is None:
            return FTR_PRIOR
        return _rate(a[4], a[3], FTR_PRIOR)

    def pfr(self, c, seat):
        a = c.stats.get(seat)
        P = self.P
        if a is None:
            return P["pfr_prior"]
        return _rate(a[2], a[0], P["pfr_prior"])

    def vpip(self, c, seat):
        a = c.stats.get(seat)
        if a is None:
            return VPIP_PRIOR
        return _rate(a[1], a[0], VPIP_PRIOR)

    def af(self, c, seat):
        a = c.stats.get(seat)
        if a is None:
            return AF_PRIOR
        return _rate(a[5], a[5] + a[6], AF_PRIOR)

    def ftb(self, c, seat):
        a = c.stats.get(seat)
        if a is None:
            return FTB_PRIOR
        return _rate(a[8], a[7], FTB_PRIOR)

    def raiser_range(self, c, seat, nraises):
        """Estimated fraction of hands `seat` holds after making the latest raise."""
        P = self.P
        prior = P["pfr_prior"]
        obs = self.pfr(c, seat)
        x = prior * (obs / prior) ** P["adapt"] * P["rng_mult"]
        if nraises >= 2 and not P["x3_on"]:
            x *= P["rr_mult"] ** (nraises - 1)
        elif nraises >= 2:
            a = c.stats.get(seat)
            # round 3: the field's 3-bet ranges are much wider than "opening range x rr_mult"; use the seat's
            # observed re-raise frequency when facing a raise
            x3 = _rate(a[9], a[3], P["x3_prior"]) if a is not None else P["x3_prior"]
            x = x3 * P["x3_mult"] * P["rr_mult"] ** (nraises - 2)
        s = c.seat_obj.get(seat)
        if s is not None and c.status.get(seat) == "all_in":
            # an all-in raise: widen with shortness of the shove
            sbb = max(1.0, (s.bet or 0) / c.bb)
            x = max(x, P["sv_base"] * (10.0 / sbb) ** P["sv_exp"] * (obs / prior) ** P["adapt"]
                    * (P["rr_mult"] ** (nraises - 1) if nraises >= 2 else 1.0))
        return _clamp(x, 0.02, 1.0)

    def call_frac(self, c, seat, risk_bb, is_bb):
        P = self.P
        base = P["sc_base"] * (10.0 / max(2.0, risk_bb)) ** P["sc_exp"]
        if is_bb:
            base *= P["bb_call_mult"]
        f = self.ftr(c, seat)
        mult = ((1.0 - f) / (1.0 - FTR_PRIOR)) ** P["adapt"]
        return _clamp(base * mult, 0.02, 0.95)

    # ------------------------------------------------------------------ chip outcome helpers
    def _remaining(self, c):
        """seat -> chips not yet committed to the pot from earlier streets (stack + current bet)."""
        r = {}
        for s in c.alive:
            o = c.seat_obj[s]
            r[s] = float(o.stack) + float(o.bet or 0)
        return r

    def ev_fold(self, c, rem, winner):
        fin = {}
        for s, v in rem.items():
            fin[s] = v - float(c.seat_obj[s].bet or 0)
        if winner is not None and winner in fin:
            fin[winner] = rem[winner] - float(c.seat_obj[winner].bet or 0) + c.pot
        if not c.board:
            # folding a short stack is worth less than its ICM value: blinds keep rising
            fin[c.me] = max(1.0, fin[c.me] - self.P["fold_tax"] * c.bb)
        return outcome_value(fin, c.me, c.pays)

    def ev_allin_vs(self, c, rem, opp, eq):
        """My expected points if I get all-in (or commit) against `opp` heads-up with equity eq."""
        me = c.me
        r_me, r_o = rem[me], rem[opp]
        contested = min(r_me, r_o)
        dead = c.pot - float(c.seat_obj[me].bet or 0) - float(c.seat_obj[opp].bet or 0)
        base = {}
        for s, v in rem.items():
            base[s] = v - float(c.seat_obj[s].bet or 0)
        win = dict(base)
        win[me] = r_me + contested + dead
        win[opp] = r_o - contested
        lose = dict(base)
        lose[me] = r_me - contested
        lose[opp] = r_o + contested + dead
        return eq * outcome_value(win, me, c.pays) + (1.0 - eq) * outcome_value(lose, me, c.pays)

    def ev_steal(self, c, rem):
        fin = {}
        for s, v in rem.items():
            fin[s] = v - float(c.seat_obj[s].bet or 0)
        fin[c.me] = rem[c.me] - c.my_bet + c.pot
        return outcome_value(fin, c.me, c.pays)

    # ------------------------------------------------------------------ preflop
    def preorder(self, c):
        """Seats in preflop action order (after the big blind first, big blind last)."""
        alive = sorted(c.alive)
        if c.bb_seat in alive:
            i = alive.index(c.bb_seat)
            return alive[i + 1:] + alive[:i + 1]
        return alive

    def preflop(self, state, c):
        P = self.P
        h = hand_class(c.cards[0], c.cards[1])
        pct = PCT[h]
        bb = c.bb
        order = self.preorder(c)
        my_i = order.index(c.me) if c.me in order else 0
        behind = [s for s in order[my_i + 1:] if c.status[s] == "active"]
        eff_bb = c.eff / bb
        rem = self._remaining(c)
        n_alive = len(c.alive)

        if c.pf_raises == 0:
            # ---------------- unopened or limped pot
            if c.to_call <= 0:
                # big blind option in a limped pot (or everyone folded/limped to me)
                if eff_bb <= P["shove_bb"] and c.live_opps:
                    if self.shove_ok(c, h, rem, c.live_opps):
                        return "raise", c.my_total
                    return "check", 0
                if pct <= P["bb_raise_pct"]:
                    return "raise", self.size_or_jam(c, c.my_bet + bb * (P["open_bb"] + 1.0 + P["limp_add"] * c.limpers))
                return "check", 0
            if eff_bb <= P["shove_bb"]:
                if self.shove_ok(c, h, rem, behind):
                    return "raise", c.my_total
                # cheap completion from the SB against a passive big blind
                return "fold", 0
            # deeper: raise / limp / fold by position
            nb = len(behind)
            if c.limpers == 0:
                if nb <= 1:
                    op = P["open_sb"]
                elif nb == 2:
                    op = P["open_btn"]
                elif nb == 3:
                    op = P["open_co"]
                elif nb == 4:
                    op = P["open_mp"]
                else:
                    op = P["open_ep"]
                # steal adaptation: blinds that over-fold let us widen late
                if nb <= 3 and behind:
                    fb = 1.0
                    for s in behind:
                        fb *= self.ftr(c, s)
                    fb_prior = FTR_PRIOR ** len(behind)
                    op = op * (1.0 + P["steal_adapt"] * (fb - fb_prior) / max(0.05, 1.0 - fb_prior) * 2.0)
                    op = _clamp(op, 0.02, 1.0)
                if pct <= op:
                    return "raise", self.size_or_jam(c, bb * P["open_bb"])
                return "fold", 0
            # limpers in front
            if pct <= P["iso_pct"]:
                return "raise", self.size_or_jam(c, bb * (P["open_bb"] + 1.0 + P["limp_add"] * c.limpers))
            if pct <= P["limp_pct"] and c.to_call <= bb:
                return "call", 0
            return "fold", 0

        # ---------------- facing a raise
        raiser = c.pf_raiser
        x_r = self.raiser_range(c, raiser, c.pf_raises)
        e = eq_top(h, x_r)
        ncall = c.pf_callers
        e_mw = e ** (1.0 + P["mw"] * ncall) if ncall else e
        price = c.to_call / (c.pot + c.to_call)
        raiser_allin = c.status.get(raiser) == "all_in"
        live_behind = [s for s in behind]

        commit = c.to_call >= P["commit_frac"] * c.my_stack or c.to_call >= c.my_stack
        if raiser_allin or commit or ncall == 0 and c.eff <= c.to_call + c.my_bet:
            # an all-in style decision against the raiser
            ev_f = self.ev_fold(c, rem, raiser)
            ev_c = self.ev_allin_vs(c, rem, raiser, e_mw)
            pen = P["behind_pen"] * len(live_behind) + P["ai_call_margin"]
            if not raiser_allin and c.my_stack > c.to_call:
                # consider re-shoving instead of calling (fold equity)
                q = _clamp(P["call_3b_frac"] * (1.0 + 0.5 * (raiser_allin)), 0.05, 1.0)
                ev_rs = self.ev_reshove(c, rem, raiser, h, x_r, q)
                if ev_rs - pen >= max(ev_f, ev_c - pen) + P["shove_margin"]:
                    return "raise", c.my_total
            if ev_c - pen > ev_f:
                return "call", 0
            return "fold", 0

        if eff_bb <= P["reshove_bb"]:
            ev_f = self.ev_fold(c, rem, raiser)
            q = P["call_3b_frac"] * (1.0 if c.pf_raises == 1 else 1.6)
            q = _clamp(q * ((1.0 - self.ftr(c, raiser)) / (1.0 - FTR_PRIOR)) ** (0.5 * P["adapt"]), 0.05, 1.0)
            ev_rs = self.ev_reshove(c, rem, raiser, h, x_r, q)
            pen = P["behind_pen"] * len(live_behind)
            if ev_rs - pen >= ev_f + P["shove_margin"] and e >= 0.40:
                return "raise", c.my_total
            if e_mw >= price + P["call_margin"] and c.to_call <= 0.2 * c.my_total:
                return "call", 0
            return "fold", 0

        # deep stacks
        if c.pf_raises == 1 and e >= P["tb_eq"]:
            cur_bet = c.my_bet + c.to_call
            tgt = cur_bet * P["tb_mult"] + cur_bet * ncall
            return "raise", self.size_or_jam(c, tgt)
        if c.pf_raises == 1 and ncall == 0 and pct <= P["l3_pct"] and (c.my_bet + c.to_call) <= P["l3_maxbb"] * bb:
            # light 3-bet: the round-1 field folded ~75% to 3-bets
            ft = self.ftr(c, raiser)
            if ft >= P["l3_ftmin"] and random.random() < P["l3_freq"] * min(1.5, ft / FTR_PRIOR):
                cur_bet = c.my_bet + c.to_call
                return "raise", self.size_or_jam(c, cur_bet * P["tb_mult"])
        if c.pf_raises >= 2 and e >= P["fb_eq"]:
            return "raise", c.my_total
        if e_mw >= price + P["call_margin"]:
            return "call", 0
        return "fold", 0

    def size_or_jam(self, c, target):
        """Raise-to target; jam when it would commit too much of the stack."""
        if target >= self.P["commit_frac"] * c.my_total:
            return c.my_total
        return int(target)

    def ev_reshove(self, c, rem, raiser, h, x_r, q):
        ev_win_now = self.ev_steal(c, rem)
        e_call = eq_top(h, max(0.02, x_r * q))
        ev_called = self.ev_allin_vs(c, rem, raiser, e_call)
        return (1.0 - q) * ev_win_now + q * ev_called

    def shove_ok(self, c, h, rem, behind):
        """Unopened (or limped) pot: ICM EV of shoving vs folding / checking."""
        P = self.P
        bb = c.bb
        ev_fold = self.ev_fold(c, rem, c.bb_seat if c.bb_seat != c.me else None)
        if c.to_call <= 0:
            # BB option: folding is checking; approximate the check as the current state
            ev_fold = self.ev_fold_noloss(c, rem)
        p_nobody = 1.0
        ev = 0.0
        # each opponent behind may call; consider at most the first four for speed
        cnt = 0
        for s in behind:
            if s == c.me:
                continue
            cnt += 1
            if cnt > 4:
                break
            r_o = rem.get(s, 0.0)
            risk = min(c.my_total, r_o) / bb
            cf = self.call_frac(c, s, risk, s == c.bb_seat)
            e = eq_top(h, cf)
            ev += p_nobody * cf * self.ev_allin_vs(c, rem, s, e)
            p_nobody *= (1.0 - cf)
        ev += p_nobody * self.ev_steal(c, rem)
        return ev >= ev_fold + P["shove_margin"]

    def ev_fold_noloss(self, c, rem):
        fin = {}
        for s, v in rem.items():
            fin[s] = v
        fin[c.me] = max(1.0, fin[c.me] - self.P["fold_tax"] * c.bb)
        return outcome_value(fin, c.me, c.pays)

    # ------------------------------------------------------------------ postflop
    def opp_range(self, c):
        P = self.P
        x = 1.0
        for s in c.opps:
            if s == c.pf_raiser:
                xs = self.raiser_range(c, s, c.pf_raises)
            elif c.pf_raises > 0:
                xs = _clamp(max(self.vpip(c, s), self.raiser_range(c, c.pf_raiser, c.pf_raises) * 1.6), 0.05, 1.0) \
                    if c.pf_raiser is not None else self.vpip(c, s)
            else:
                xs = max(0.5, self.vpip(c, s))
            if xs < x:
                x = xs
        return x

    def postflop(self, state, c):
        P = self.P
        board = c.board
        street = len(board) - 2  # 1 flop, 2 turn, 3 river
        if street < 1:
            street = 1
        if street > 3:
            street = 3
        n_opp = len(c.opps)
        if n_opp == 0:
            return "check", 0
        x = self.opp_range(c)
        bi = 0
        while bi < len(POST_BUCKETS) - 1 and POST_BUCKETS[bi] < x:
            bi += 1
        hr = POST_RANGES[bi]
        hand = [CARD[c.cards[0]], CARD[c.cards[1]]]
        bd = [CARD[b] for b in board]
        spent = time.perf_counter() - getattr(self, "_t0", time.perf_counter())
        if spent > 0.0002:
            # running slow (busy machine): cheaper estimate against a narrower range
            hr = POST_RANGES[min(bi, 2)]
            eq = _MC(hand, hr, bd, 80)
        elif street == 3:
            eq = _EXACT(hand, hr, bd)
        else:
            eq = _MC(hand, hr, bd, int(P["mc_iters"]))
        mwk = 1.0 + P["mw"] * (n_opp - 1)
        eq_mw = eq ** mwk
        pot = c.pot
        rem_stack = c.my_stack
        sfx = str(street)

        if c.to_call > 0:
            bettor = c.st_aggr if c.st_aggr is not None else (c.opps[0] if c.opps else None)
            bf = c.to_call / max(1.0, pot - c.to_call)
            f = P["bf" + sfx]
            if bettor is not None:
                f *= (self.af(c, bettor) / AF_PRIOR) ** P["af_adapt"]
            f *= (0.5 / max(0.15, bf)) ** P["bs_exp"]
            if c.st_raises >= 2:
                f *= P["raise_f"] ** (c.st_raises - 1)
            f = _clamp(f, 0.06, 1.0)
            e_hu = eq ** (1.0 / f)
            e_bet = e_hu * (eq ** (P["mw"] * (n_opp - 1))) if n_opp > 1 else e_hu
            price = c.to_call / (pot + c.to_call)
            allin_call = c.to_call >= rem_stack
            if allin_call or c.to_call >= 0.5 * rem_stack:
                if n_opp == 1 and bettor is not None and bettor in c.seat_obj:
                    rem = self._remaining(c)
                    ev_f = self.ev_fold(c, rem, bettor)
                    ev_c = self.ev_allin_vs(c, rem, bettor, e_bet)
                    if ev_c > ev_f + P["ai_call_margin"]:
                        return "call", 0
                    return "fold", 0
            if e_bet >= P["rz" + sfx] and c.live_opps and c.st_raises < 4:
                tgt = c.my_bet + c.to_call + P["rz_frac"] * (pot + c.to_call)
                if tgt >= c.my_total - P["jam_spr"] * (pot + 2 * c.to_call):
                    tgt = c.my_total
                return "raise", tgt
            if e_bet >= price + P["cm" + sfx]:
                return "call", 0
            return "fold", 0

        # checked to me / first to act
        if not c.live_opps:
            return "check", 0
        if eq_mw >= P["vb" + sfx]:
            return "raise", self.bet_size(c, P["bs" + sfx])
        if n_opp <= 2:
            fold_mult = 1.0
            for s in c.live_opps:
                fold_mult *= (self.ftb(c, s) / FTB_PRIOR) ** P["fold_adapt"]
            r = random.random()
            if street == 1 and c.pf_raiser == c.me and n_opp == 1:
                if r < P["cbet"] * fold_mult:
                    return "raise", self.bet_size(c, P["bs1"] * 0.85)
            elif street == 3:
                if eq_mw < P["bl_max3"] and r < P["bl3"] * fold_mult:
                    return "raise", self.bet_size(c, P["bs3"])
            else:
                if r < P["bl" + sfx] * fold_mult:
                    return "raise", self.bet_size(c, P["bs" + sfx])
        return "check", 0

    def bet_size(self, c, frac):
        amt = c.pot * frac
        if amt < c.bb:
            amt = c.bb
        tgt = c.my_bet + amt
        if c.my_total - tgt < self.P["jam_spr"] * (c.pot + 2 * amt):
            return c.my_total
        return int(tgt)


# --------------------------------------------------------------------------------------------- warm-up
class _WS:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _warmup():
    """Exercise every code path once at import so the first real decision is not slowed by cold caches."""
    try:
        cfg = _WS(payouts=[50, 30, 20, 0, 0, 0, 0, 0])
        la = [_WS(kind="fold", min_amount=0, max_amount=0), _WS(kind="call", min_amount=0, max_amount=0),
              _WS(kind="raise", min_amount=80, max_amount=1500)]
        seats = [_WS(seat=i, stack=1500 - 100 * i, bet=(10 if i == 1 else 20 if i == 2 else 0),
                     status="active", shown_cards=[]) for i in range(4)]
        hist = [_WS(kind="hand", seat=None, amount=1, cards=None), _WS(kind="blind", seat=1, amount=10, cards=None),
                _WS(kind="blind", seat=2, amount=20, cards=None)]
        for board in ([], ["2c", "7d", "Ts"], ["2c", "7d", "Ts", "Kh"], ["2c", "7d", "Ts", "Kh", "3s"]):
            st = _WS(seat=0, cards=["Ah", "Qd"], board=board, pot=30 if not board else 200, to_call=20,
                     legal_actions=la, history=hist + ([_WS(kind="board", seat=None, amount=None, cards=board)]
                                                       if board else []),
                     seats=seats, button=0, blinds=[10, 20], config=cfg, events=hist)
            a = Agent()
            a.act(st, b"")
            a.decide(st, {}, {"fold": la[0], "call": la[1], "raise": la[2]})
        icm([1000.0, 2000.0, 3000.0, 500.0, 700.0], 0, [50.0, 30.0, 20.0])
    except Exception:
        pass


_warmup()
try:
    import gc
    gc.collect()
    gc.freeze()
except Exception:
    pass
