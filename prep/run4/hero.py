"""Parametric candidate policy. Small enough to retune quickly and fast enough for 1 ms."""
import os
import random
from pk import pct, equity_vs_range

R = random.random
FOLD, CALL = (0, 0), (1, 0)
# Chip-EV jam width at about 10 big blinds, by number of players left to act (secondary 9-handed chart).
JAM_CHART = [1.0, 0.69, 0.44, 0.34, 0.27, 0.22, 0.20, 0.18]

DEFAULT = {
    # preflop, deep
    "open_a": 0.08, "open_b": 0.32, "hu_open": 0.70, "hu_jam": 0.65,
    "sh_widen": 2.0, "sh_range": 0.8, "jam_scale": 0.85,
    "call_open": 0.10, "threebet": 0.05, "fourbet": 0.025,
    "open_size": 2.5, "open_limp_add": 1.0, "threebet_mult": 3.0,
    "call_odds": 0.1, "hu_defend": 0.0,
    # How far a seat's looseness can widen the range we assume for it. Low values get run over by constant raisers.
    "width_cap": 2.2,
    "steal_fold_bonus": 0.25,
    # short-stack jam-or-fold
    "jam_m": 12.0, "jam_slope": 0.07, "call_jam": 0.09, "call_jam_short": 0.02,
    # postflop
    "range_unraised": 0.45, "range_bet": 0.28, "range_raise": 0.10,
    "value_eq": 0.70, "bluff_freq": 0.18, "bet_frac": 0.66, "call_margin": 0.04, "raise_eq": 0.82,
    "commit_spr": 1.3,
    # ICM: discount for close spots once few players remain
    "icm_margin": 0.05, "rollouts": 40,
    # within-table adaptation
    "adapt": 1.0,
    # optional v3 features; zero means off
    "bully": 0.0, "cbet_pfr": 0.0, "cap_tight": 0.0,
    # Facing a preflop all-in: equity vs. this seat's observed raising range.
    "eqcall": float(os.environ.get("HERO_EQCALL", 0)), "eqcall_margin": 0.04, "vwidth_mult": 1.2,
}


class Hero:
    def __init__(self, **kw):
        self.p = dict(DEFAULT)
        self.p.update(kw)
        self.vpip = {}
        self.hands = {}
        self.raises = {}
        self.seen_vp = set()
        self.seen_h = set()
        self.last_hand = -1
        self.saw_aggro = 0
        self.aggro_seat = -1
        self.pfr = False
        self.pf_raise = {}
        self.seen_pf = set()

    # ---- opponent tracking; each event is O(1)
    def observe(self, seat, street, kind, amount):
        if street == 0:
            if seat not in self.seen_h:
                self.seen_h.add(seat)
                self.hands[seat] = self.hands.get(seat, 0) + 1
            if kind and seat not in self.seen_vp:
                self.seen_vp.add(seat)
                self.vpip[seat] = self.vpip.get(seat, 0) + 1
        if kind == 2:
            if street == 0 and seat not in self.seen_pf:
                self.seen_pf.add(seat)
                self.pf_raise[seat] = self.pf_raise.get(seat, 0) + 1
            self.saw_aggro += 1
            self.aggro_seat = seat
            self.raises[seat] = self.raises.get(seat, 0) + 1

    def end_hand(self, n):
        self.seen_vp = set()
        self.seen_h = set()
        self.saw_aggro = 0
        self.aggro_seat = -1
        self.pfr = False
        self.seen_pf = set()

    def _vpip(self, s):
        # Bayesian shrink toward 30%
        return (self.vpip.get(s, 0) + 3.0) / (self.hands.get(s, 0) + 10.0)

    def _fold_rate_behind(self, o):
        p = self.p
        if not p["adapt"]:
            return 0.0
        v = []
        for s in range(len(o.stacks)):
            if s != o.seat and o.in_hand[s]:
                v.append(self._vpip(s))
        return 1.0 - (sum(v) / len(v)) if v else 0.0

    def act(self, o):
        if o.street == 0:
            r = self.preflop(o)
            if r[0] == 2:
                self.pfr = True
            return r
        return self.postflop(o)

    def preflop(self, o):
        p = self.p
        hp = pct(o.hole)
        m = (o.stack + o.bet) / float(o.sb + o.bb)
        eff = self._eff_stack(o)
        eff_m = eff / float(o.sb + o.bb)
        few = o.n_alive
        margin = p["icm_margin"] * (1.0 if few <= 4 else 0.0)

        hu = o.n_alive == 2
        sh = 1.0 + p["sh_widen"] * (8 - o.n_alive) / 6.0
        if o.raises == 0:
            behind = o.n_behind
            # short: jam or fold
            if eff_m < p["jam_m"]:
                w = p["jam_scale"] * JAM_CHART[min(behind, 7)] * max(0.25, 1.0 + p["jam_slope"] * (6.67 - eff_m))
                if hu:
                    w = max(w, p["hu_jam"])
                w *= 1.0 + p["steal_fold_bonus"] * (self._fold_rate_behind(o) - 0.6)
                if hp < w:
                    return (2, o.max_raise_to) if o.can_raise else CALL
                return CALL if o.to_call == 0 else FOLD
            w = p["hu_open"] if hu else p["open_a"] + p["open_b"] / (behind + 0.5)
            w *= 1.0 + p["steal_fold_bonus"] * (self._fold_rate_behind(o) - 0.6)
            if p["bully"]:
                avg = o.total_chips / float(o.n_alive)
                w *= 1.0 + p["bully"] * max(-0.5, min(1.5, (o.stack + o.bet) / avg - 1.0))
            if hp < w and o.can_raise:
                return (2, o.bb * (p["open_size"] + p["open_limp_add"] * o.n_callers))
            if o.to_call == 0:
                return CALL
            # complete the small blind cheaply with reasonable hands
            if o.to_call <= o.sb and hp < w * 1.6:
                return CALL
            return FOLD
        # facing a raise
        cost = o.to_call
        all_in_ish = o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur
        odds = cost / float(o.pot + cost)
        if all_in_ish and p["eqcall"] and o.aggressor >= 0:
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            width = max(0.03, min(1.0, rate * p["vwidth_mult"]))
            eq = equity_vs_range(o.hole, [], width, int(p["rollouts"]))
            opp = max(1, o.n_live - 1)
            if opp > 1:
                eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
            return CALL if eq > odds + p["eqcall_margin"] + margin else FOLD
        if all_in_ish:
            aggro = self._raiser_width(o)
            w = p["call_jam"] * aggro * sh - margin * 0.5
            w += p["call_jam_short"] * max(0.0, 8.0 - eff_m)
            w += max(0.0, odds - 0.33) * 0.5
            return CALL if hp < max(0.01, w) else FOLD
        if o.raises >= 2:
            if hp < p["fourbet"] and o.can_raise:
                return (2, o.max_raise_to)
            return CALL if hp < p["fourbet"] * 2 else FOLD
        aggro = self._raiser_width(o) * sh
        if hp < p["threebet"] * aggro and o.can_raise:
            if eff_m < 25:
                return (2, o.max_raise_to)
            return (2, o.cur * p["threebet_mult"])
        # Price matters: a min-raise offers 3-to-1, so defend wider when it is cheap, especially short-handed.
        wd = p["call_open"] * aggro + odds * p["call_odds"]
        if hu:
            wd = max(wd, p["hu_defend"] * (odds / 0.25) if odds >= 0.1 else 0.0)
        if hp < wd and cost < 0.2 * o.stack:
            return CALL
        return FOLD

    def _raiser_width(self, o):
        p = self.p
        if not p["adapt"] or o.aggressor < 0:
            return 1.0
        return max(0.7, min(p["width_cap"], self._vpip(o.aggressor) / 0.3))

    def eq(self, hole, board, width):
        return equity_vs_range(hole, board, width, int(self.p["rollouts"]))

    def _eff_stack(self, o):
        best = 0
        for s in range(len(o.stacks)):
            if s != o.seat and o.in_hand[s]:
                v = o.stacks[s] + o.bets[s]
                if v > best:
                    best = v
        return min(best, o.stack + o.bet)

    def postflop(self, o):
        p = self.p
        # Estimate villain range from the action.
        if o.aggressor >= 0 and o.to_call > 0:
            base = p["range_raise"] if o.raises >= 2 else p["range_bet"]
            if p["adapt"]:
                base *= max(0.7, min(p["width_cap"], self._vpip(o.aggressor) / 0.3))
        else:
            base = p["range_unraised"]
        base = min(1.0, base * (1.0 + p["sh_range"] * (8 - o.n_alive) / 6.0))
        eq = self.eq(o.hole, o.board, base)
        opp = max(1, o.n_live - 1)
        if opp > 1:
            eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
        spr = o.stack / float(max(1, o.pot))
        margin = p["call_margin"] + (p["icm_margin"] if o.n_alive <= 4 else 0.0)
        # Near the cap, survival is what ICM pays for: require more to call off.
        if p["cap_tight"] and o.hand_no >= 180:
            margin += p["cap_tight"]
        if o.to_call == 0:
            if not o.can_raise:
                return CALL
            if eq > p["value_eq"]:
                size = o.pot * p["bet_frac"]
                if spr < p["commit_spr"]:
                    return (2, o.max_raise_to)
                return (2, size)
            bf = p["bluff_freq"] + (p["cbet_pfr"] if self.pfr and o.street == 1 else 0.0)
            if o.n_live == 2 and R() < bf:
                return (2, o.pot * 0.5)
            return CALL
        odds = o.to_call / float(o.pot + o.to_call)
        if eq > p["raise_eq"] and o.can_raise:
            if spr < 2.0:
                return (2, o.max_raise_to)
            return (2, o.cur + o.pot * 0.8)
        return CALL if eq > odds + margin else FOLD
