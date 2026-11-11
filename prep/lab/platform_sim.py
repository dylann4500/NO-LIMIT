"""Local stand-in for the tournament platform, to test a portal Agent before the kit ships.

play_platform_table plays one table under engine.play_table's exact rules and returns the same result. A seat
is a lab bot (engine Obs interface) or a portal agent: anything with act(state, memory) -> (Action, bytes),
optionally wrapped as Plat(agent, shadow) to compare it with a lab policy on the same decisions. Portal seats get
what docs/portal_getting_started.md describes: events since their last successful turn, memory truncated at
config.memory_bytes, strict legality, and check-or-fold on a failed decision. Conventions the portal leaves open
are switches in `conv` (see CONV). Run this file to check it against engine.play_table.
"""
import inspect, math, operator, os, random, sys, time, traceback
from collections import Counter
from enum import Enum
HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.join(HERE, "fake_sdk")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import poker_agent_sdk as sdk
from poker_agent_sdk import ActionKind as K, Config, Event, LegalAction, Seat, State
import pk, engine
from engine import Obs, SCHEDULE_DEFAULT, FOLD, CALL, RAISE

CONV = {
    "stack_includes_bet": False,  # Seat.stack counts that seat's bet this street
    "pot_includes_bets": True,  # state.pot counts this street's bets
    "own_action_in_events": True,  # a seat's own fold/check/call/raise is in the events of its next turn
    "seat_ids": "index",  # or "shuffled": distinct random ints 0-99, fixed per table
    "base": 1,  # first hand_number and blind_level (0 or 1)
    "event_kind": "str",  # or "enum": Event.kind is a plain Enum member whose value is the name
}
FLAGS = ("stack_includes_bet", "pot_includes_bets", "own_action_in_events", "seat_ids")
PAYOUTS = list(engine.EVENT.get("points") or [50, 30, 20, 0, 0, 0, 0, 0])
CARD = [r + s for r in "23456789TJQKA" for s in "shdc"]  # lab card c -> "23456789TJQKA"[c >> 2] + "shdc"[c & 3]
STREET = ("preflop", "flop", "turn", "river")
ACTS = ("fold", "check", "call", "raise", "discard")
EventKind = Enum("EventKind", {k.upper(): k for k in ("hand", "ante", "blind", "fold", "check", "call", "raise",
                                                      "board", "show", "win", "stack", "discard")})
_FRNG = random.Random(20261106)
_ns = time.perf_counter_ns


class Stats:
    """Per-run counters, summed over tables and merged across processes."""
    def __init__(self):
        self.decisions = self.redelivered = self.truncated = self.garbage = self.shadow_err = self.discards = 0
        self.lat, self.mem, self.fail_ex, self.ex, self.violations, self.dlat = [], [], [], [], [], []
        self.fails, self.cmp, self.diff, self.extra = Counter(), Counter(), Counter(), Counter()
        self.seat_n, self.seat_fails, self.seat_slow = Counter(), Counter(), Counter()  # by seat id

    def merge(self, o):
        for k, v in vars(o).items():
            a = getattr(self, k)
            if isinstance(v, (Counter, list)):
                a += v
            else:
                setattr(self, k, a + v)
        return self


class Plat:
    """A portal agent at one seat (a list means a pool of copies, one picked per decision), plus an optional
    lab-policy shadow that sees the engine's Obs and events and is compared on every decision."""
    def __init__(self, agent, shadow=None):
        self.agent, self.shadow = agent, shadow


def is_portal(b):
    if isinstance(b, (Plat, sdk.Agent)):
        return True
    try:
        return len(inspect.signature(b.act).parameters) == 2
    except (TypeError, ValueError, AttributeError):
        return False


def legal_move(a, legal):
    """Engine move for a portal Action if the portal accepts it, else None. No clamping."""
    if not isinstance(a, sdk.Action):
        return None
    la = next((x for x in legal if x.kind == a.kind), None)
    if la is None:
        return None
    if la.kind == K.RAISE:
        try:
            to = operator.index(a.amount)
        except TypeError:
            try:
                to = math.floor(a.amount)  # floats, NumPy's too, round down
            except (TypeError, ValueError, OverflowError):
                return None
        return (RAISE, to) if la.min_amount <= to <= la.max_amount else None
    return (FOLD, 0) if la.kind == K.FOLD else (CALL, 0)


def move_name(kind, to_call):
    return "fold" if kind == FOLD else "raise" if kind == RAISE else "check" if to_call == 0 else "call"


def norm_lab(m, o):
    """A lab move as the engine plays it (test_parity.py normalisation)."""
    k, a = m
    if k == RAISE:
        return (CALL, 0) if not o.can_raise else (RAISE, int(min(o.max_raise_to, max(o.min_raise_to, a))))
    return (CALL, 0) if k == FOLD and o.to_call == 0 else (k, 0)


def srepr(x, k=300):
    try:
        return repr(x)[:k]
    except Exception as e:
        return f"<{type(x).__name__}, repr raised {e!r}>"


def fmt_state(st):
    return (f"seat {st.seat} hand {st.hand_number} cards {st.cards} board {st.board} pot {st.pot} to_call {st.to_call} "
            f"legal {st.legal_actions} button {st.button} seats {[(x.seat, x.stack, x.bet, x.status) for x in st.seats]} "
            f"events {len(st.events)} memory_in {st.memory_in!r:.80}")


def _garbage(r, mem):
    k = r.randrange(5)
    if k == 0:
        return b""
    if k == 1:
        return mem[: r.randrange(len(mem) + 1)]
    if k == 2 and mem:
        b = bytearray(mem)
        for _ in range(1 + r.randrange(8)):
            b[r.randrange(len(b))] = r.randrange(256)
        return bytes(b)
    if k == 3:
        return r.randbytes(65536)
    return r.randbytes(r.randrange(1, 300))


def replay(events, ids, start):
    """Stacks rebuilt from an event stream alone. Returns (stacks by seat id, mismatches at `stack` events)."""
    L, B, bad = {i: start for i in ids}, {}, 0
    for e in events:
        k, s, a = getattr(e.kind, "value", e.kind), e.seat, e.amount
        if k in ("hand", "board"):
            B = {}
        elif k == "ante":
            L[s] -= a
        elif k in ("blind", "call"):
            L[s] -= a
            B[s] = B.get(s, 0) + a
        elif k == "raise":
            L[s] -= a - B.get(s, 0)
            B[s] = a
        elif k == "win":
            L[s] += a
        elif k == "stack":
            bad += L[s] != a
            L[s] = a
    return L, bad


def play_platform_table(bots, schedule=SCHEDULE_DEFAULT, rng=random, conv=None, stats=None, fail_rate=0.0,
                        garbage=0.0, frng=None, check=False, enforce_time=False, hh=None, **cfg):
    """engine.play_table with portal seats. Returns (finish_groups, hands, survivors) exactly as engine does.
    fail_rate: chance a portal decision is treated as a timeout (action and memory discarded, events re-sent).
    garbage: chance the memory handed to a portal seat is replaced by junk. frng drives both, seat ids and
    table_id, so the game RNG sees the same draws as engine.play_table. check: audit chips every decision and
    hand, replay the event log to the true stacks, and verify each portal seat's delivered event stream.
    cfg overrides state.config fields (e.g. memory_bytes=1024). hh: a list that gets one dict per hand (seat ids, button,
    blinds, starting stacks, every seat's hole cards, the public event log and failed decisions); the league writes
    these as hand histories and filters them to what each team would see."""
    C = dict(CONV, **(conv or {}))
    if set(C) != set(CONV):
        raise ValueError(f"unknown conv keys {set(C) - set(CONV)}")
    START, MAXH, HPL = engine.START, engine.MAX_HANDS, engine.HANDS_PER_LEVEL
    sib, pib, own, base = C["stack_includes_bet"], C["pot_includes_bets"], C["own_action_in_events"], C["base"]
    st_ = stats if stats is not None else Stats()
    fr = frng or _FRNG
    n = len(bots)
    plat = {i: b if isinstance(b, Plat) else Plat(b) for i, b in enumerate(bots) if is_portal(b)}
    ids = fr.sample(range(100), n) if C["seat_ids"] == "shuffled" else list(range(n))
    KIND = {k: EventKind(k) if C["event_kind"] == "enum" else k for k in EventKind._value2member_map_}
    conf = dict(table_id=f"t{fr.randrange(10 ** 9):09d}", variant=pk.VARIANT, players=n, starting_stack=START,
                blinds=[list(x) for x in schedule], hands_per_level=HPL, hand_cap=MAXH, payouts=list(PAYOUTS),
                decision_ms=1, time_bank_ms=100, memory_bytes=65536)
    conf.update(cfg)
    cfgs = {s: Config(**dict(conf, seat=ids[s])) for s in plat}
    limit = conf["memory_bytes"]
    mem = {s: b"" for s in plat}
    queue = {s: [] for s in plat}
    bank = {s: float(conf["time_bank_ms"]) for s in plat}
    seen = {s: [] for s in plat}
    log = []
    hfail = []
    h0 = 0
    hooks = [plat[i].shadow if i in plat else b for i, b in enumerate(bots)]
    hooks = [b for b in hooks if b is not None]
    obs_t = [b for b in hooks if hasattr(b, "observe")]

    def emit(kind, s=None, amount=None, cards=None, act=False):
        e = Event(KIND[kind], None if s is None else ids[s], amount, cards)
        log.append(e)
        for p, q in queue.items():
            if own or not act or p != s:
                q.append(e)

    def status(i):
        return "busted" if start_stack[i] <= 0 else "folded" if not in_hand[i] else "all_in" if stacks[i] <= 0 else "active"

    def platform_move(s, o, street, board):
        p = plat[s]
        to_call = o.to_call
        legal = [LegalAction(K.FOLD)] if to_call > 0 else []
        legal.append(LegalAction(K.CALL if to_call else K.CHECK))
        if o.can_raise:
            legal.append(LegalAction(K.RAISE, o.min_raise_to, o.max_raise_to))
        state = State(
            seat=ids[s], cards=[CARD[c] for c in holes[s]], board=[CARD[c] for c in board],
            pot=o.pot if pib else o.pot - sum(bets), to_call=to_call, legal_actions=legal, history=log[h0:],
            phase="betting", variant=None,
            seats=[Seat(ids[i], stacks[i] + bets[i] if sib else stacks[i], bets[i], status(i)) for i in range(n)],
            button=ids[button], blind_level=lvl + base, blinds=[sb, bb], hands_until_next_level=HPL - hand_no % HPL,
            hand_number=hand_no + base, players_remaining=m, bust_order=[ids[x] for g in eliminated for x in g],
            config=cfgs[s], time_bank_ms=int(bank[s]), events=list(queue[s]))
        sm = None
        if p.shadow is not None:
            rs = random.getstate()
            try:
                sm = norm_lab(p.shadow.act(o), o)
            except Exception:
                st_.shadow_err += 1
            random.setstate(rs)  # the agent sees the same random draws as its shadow
        agent = fr.choice(p.agent) if isinstance(p.agent, list) else p.agent
        mi = mem[s]
        if garbage and fr.random() < garbage:
            mi = _garbage(fr, mi)
            st_.garbage += 1
        err = None
        t0 = _ns()
        try:
            ret = agent.act(state, mi)
        except Exception as e:
            ret, err = None, "".join(traceback.format_exception(e)[-3:])
        dt = _ns() - t0
        st_.lat.append(dt)
        bank[s] -= max(0.0, dt / 1e6 - conf["decision_ms"])
        parsed = isinstance(ret, (tuple, list)) and len(ret) == 2 and isinstance(ret[1], (bytes, bytearray, memoryview))
        try:
            move = legal_move(ret[0], legal) if parsed else None
        except Exception:  # e.g. a kind whose == raises
            move = None
        why = None
        if err is not None:
            why = "error"
        elif enforce_time and bank[s] < 0:
            why, bank[s] = "timeout", 0.0
        elif fail_rate and fr.random() < fail_rate:
            why = "injected"
        elif not parsed:
            why = "malformed"
        elif move is None:
            why = "illegal"
        if parsed:
            nm = bytes(ret[1])
            st_.mem.append(len(nm))
        if why in (None, "illegal"):
            if len(nm) > limit:
                nm = nm[:limit]
                st_.truncated += 1
            mem[s] = nm
            seen[s] += queue[s]
            queue[s] = []
        else:
            st_.redelivered += 1
        st_.decisions += 1
        st_.seat_n[ids[s]] += 1
        if dt > conf["decision_ms"] * 1e6:
            st_.seat_slow[ids[s]] += 1
        if sm is not None:
            pn = (move_name(move[0], to_call) if move else "invalid") if parsed else "error"
            key = (STREET[street], pn, move_name(sm[0], to_call))
            st_.cmp[key] += 1
            if move != sm:
                st_.diff[key] += 1
                if len(st_.ex) < 20:
                    st_.ex.append(dict(
                        key=key, platform=srepr(ret[0]) if parsed else err, shadow=sm, hand=hand_no, seat=s,
                        hole=[CARD[c] for c in o.hole], board=[CARD[c] for c in o.board], pot=o.pot, to_call=to_call,
                        cur=o.cur, stack=o.stack, bet=o.bet, raises=o.raises, n_alive=o.n_alive, n_live=o.n_live,
                        n_behind=o.n_behind, aggressor=o.aggressor, raise_range=(o.min_raise_to, o.max_raise_to) if o.can_raise else None))
        if why:
            st_.fails[why] += 1
            st_.seat_fails[(ids[s], why)] += 1
            if hh is not None:
                hfail.append([ids[s], why])
            if why != "injected" and sum(1 for x in st_.fail_ex if x[0] == why) < 5:
                state.memory_in = mi
                st_.fail_ex.append((why, fmt_state(state), err if err else srepr(ret)))
            return (CALL, 0) if to_call == 0 else (FOLD, 0)
        return move

    def platform_discard(s, o):
        """A portal seat's discard (discard variant): phase "discard", one legal kind DISCARD whose amount is the index
        into state.cards of the card to drop (fake_sdk). A failed decision takes the automatic choice, card 0."""
        p = plat[s]
        hole = holes[s]
        legal = [LegalAction(K.DISCARD, 0, len(hole) - 1)]
        state = State(
            seat=ids[s], cards=[CARD[c] for c in hole], board=[CARD[c] for c in o.board], pot=o.pot if pib else o.pot - sum(bets),
            to_call=0, legal_actions=legal, history=log[h0:], phase="discard", variant=None,
            seats=[Seat(ids[i], stacks[i] + bets[i] if sib else stacks[i], bets[i], status(i)) for i in range(n)],
            button=ids[button], blind_level=lvl + base, blinds=[sb, bb], hands_until_next_level=HPL - hand_no % HPL,
            hand_number=hand_no + base, players_remaining=m, bust_order=[ids[x] for g in eliminated for x in g],
            config=cfgs[s], time_bank_ms=int(bank[s]), events=list(queue[s]))
        agent = fr.choice(p.agent) if isinstance(p.agent, list) else p.agent
        mi = mem[s]
        if garbage and fr.random() < garbage:
            mi = _garbage(fr, mi)
            st_.garbage += 1
        err = None
        t0 = _ns()
        try:
            ret = agent.act(state, mi)
        except Exception as e:
            ret, err = None, "".join(traceback.format_exception(e)[-3:])
        dt = _ns() - t0
        st_.lat.append(dt)
        st_.dlat.append(dt)
        bank[s] -= max(0.0, dt / 1e6 - conf["decision_ms"])
        parsed = isinstance(ret, (tuple, list)) and len(ret) == 2 and isinstance(ret[1], (bytes, bytearray, memoryview))
        idx = None
        if parsed:
            try:
                a = ret[0]
                if isinstance(a, sdk.Action) and a.kind == K.DISCARD:
                    i = operator.index(a.amount)
                    if 0 <= i < len(hole):
                        idx = i
            except Exception:
                idx = None
        why = None
        if err is not None:
            why = "error"
        elif enforce_time and bank[s] < 0:
            why, bank[s] = "timeout", 0.0
        elif fail_rate and fr.random() < fail_rate:
            why = "injected"
        elif not parsed:
            why = "malformed"
        elif idx is None:
            why = "illegal"
        if why in (None, "illegal"):
            nm = bytes(ret[1])
            st_.mem.append(len(nm))
            if len(nm) > limit:
                nm = nm[:limit]
                st_.truncated += 1
            mem[s] = nm
            seen[s] += queue[s]
            queue[s] = []
        else:
            st_.redelivered += 1
        st_.decisions += 1
        st_.discards += 1
        st_.seat_n[ids[s]] += 1
        if dt > conf["decision_ms"] * 1e6:
            st_.seat_slow[ids[s]] += 1
        if why:
            st_.fails[why] += 1
            st_.seat_fails[(ids[s], why)] += 1
            if hh is not None:
                hfail.append([ids[s], why])
            if why != "injected" and sum(1 for x in st_.fail_ex if x[0] == why) < 5:
                state.memory_in = mi
                st_.fail_ex.append((why, fmt_state(state), err if err else srepr(ret)))
            return 0
        return idx

    # ---- engine.play_table, with events and portal seats --------------------------------------------------
    stacks = [START] * n
    button = rng.randrange(n)
    eliminated = []
    total = START * n
    deck = pk.DECK
    NH = pk.N_HOLE
    DISC = pk.DISCARD
    showdown = pk.showdown
    o = Obs()
    o.total_chips = total
    hand_no = 0
    lvl = sb = bb = m = 0
    start_stack, in_hand, holes, bets = stacks[:], [False] * n, {}, [0] * n
    while hand_no < MAXH:
        alive = [i for i in range(n) if stacks[i] > 0]
        if len(alive) <= 1:
            break
        lvl = min(hand_no // HPL, len(schedule) - 1)
        sb, bb = schedule[lvl]
        button = (button + 1) % n
        while stacks[button] <= 0:
            button = (button + 1) % n
        bi = alive.index(button)
        rot = alive[bi:] + alive[:bi]
        m = len(rot)
        if m == 2:
            sb_seat, bb_seat = rot[0], rot[1]
            pre_order = [rot[0], rot[1]]
            post_order = [rot[1], rot[0]]
        else:
            sb_seat, bb_seat = rot[1], rot[2]
            pre_order = rot[3:] + rot[:3]
            post_order = rot[1:] + rot[:1]
        start_stack = stacks[:]
        cards = rng.sample(deck, 5 + NH * m)
        full_board = cards[:5]
        holes = {s: cards[5 + NH * j : 5 + NH * (j + 1)] for j, s in enumerate(rot)}
        in_hand = [stacks[i] > 0 for i in range(n)]
        bets = [0] * n
        contrib = [0] * n

        def post(s, a):
            a = min(a, stacks[s])
            stacks[s] -= a
            bets[s] += a
            contrib[s] += a
            emit("blind", s, a)

        h0 = len(log)
        if hh is not None:
            hfail.clear()
            rec = {"hand": hand_no + base, "button": ids[button], "blinds": [sb, bb], "stacks": {ids[i]: stacks[i] for i in rot},
                   "holes": {ids[x]: [CARD[c] for c in holes[x]] for x in rot}}
        emit("hand", amount=hand_no + base)
        post(sb_seat, sb)
        post(bb_seat, bb)
        live = m
        shared = full_board
        for street, nb in ((0, 0), (1, 3), (2, 4), (3, 5)):
            if live <= 1:
                break
            board = full_board[:nb]
            order = pre_order if street == 0 else post_order
            if DISC and street:  # discard variant, as engine.play_table: flop, discards in postflop order, turn, river
                if street == 1:
                    shared = full_board[:pk.FLOP_N]
                    emit("board", cards=[CARD[c] for c in shared])
                    for s in order:
                        if in_hand[s]:
                            engine.discard_obs(o, s, holes[s], shared, street, contrib, stacks, bets, in_hand, m, live,
                                               hand_no, button, sb, bb)
                            if s in plat:
                                i = platform_discard(s, o)
                            else:
                                i = engine.lab_discard(bots[s], o)
                            c = holes[s].pop(i)
                            if pk.DISCARD_TO_BOARD:
                                shared.append(c)
                            emit("discard", s, cards=[CARD[c]], act=True)
                else:
                    c = full_board[pk.FLOP_N + street - 2]
                    shared.append(c)
                    emit("board", cards=[CARD[c]])
                board = pk.Board(shared, 3 - street)
            if street == 0:
                cur = bb
                last_raise = bb
            else:
                if not DISC:
                    emit("board", cards=[CARD[c] for c in full_board[(0, 0, 3, 4)[street]:nb]])
                cur = 0
                last_raise = bb
                for i in range(n):
                    bets[i] = 0
                can_bet = sum(1 for s in order if in_hand[s] and stacks[s] > 0)
                if can_bet < 2:
                    continue
            raises = 0
            aggressor = -1
            to_act = len(order)
            idx = 0
            callers = 0
            first_in = True
            while to_act > 0 and live > 1:
                s = order[idx % len(order)]
                idx += 1
                to_act -= 1
                if not in_hand[s] or stacks[s] <= 0:
                    continue
                to_call = min(cur - bets[s], stacks[s])
                others = sum(1 for x in order if x != s and in_hand[x] and stacks[x] > 0)
                if to_call == 0 and others == 0:
                    continue
                o.seat = s
                o.hole = holes[s]
                o.board = board
                o.street = street
                o.pot = sum(contrib)
                o.to_call = to_call
                o.cur = cur
                o.stack = stacks[s]
                o.bet = bets[s]
                o.max_raise_to = bets[s] + stacks[s]
                o.min_raise_to = min(cur + last_raise, o.max_raise_to)
                o.can_raise = others > 0 and stacks[s] > to_call
                o.sb, o.bb = sb, bb
                o.hand_no = hand_no
                o.button = button
                o.stacks = stacks
                o.bets = bets
                o.in_hand = in_hand
                o.n_alive = m
                o.n_live = live
                o.raises = raises
                o.aggressor = aggressor
                o.first_in = first_in
                o.n_callers = callers
                nbh = 0
                L = len(order)
                for j in range(idx, idx + to_act):
                    x = order[j % L]
                    if in_hand[x] and stacks[x] > 0:
                        nbh += 1
                o.n_behind = nbh
                if check and sum(stacks) + sum(contrib) != total:
                    st_.violations.append(f"chips {sum(stacks)}+{sum(contrib)} != {total} at hand {hand_no}")
                if s in plat:
                    kind, amt = platform_move(s, o, street, board)
                else:
                    try:
                        kind, amt = bots[s].act(o)
                    except Exception:
                        kind, amt = (CALL, 0) if to_call == 0 else (FOLD, 0)
                if kind == FOLD and to_call == 0:
                    kind = CALL
                if kind == RAISE and not o.can_raise:
                    kind = CALL
                if kind == FOLD:
                    in_hand[s] = False
                    live -= 1
                    ev = (s, street, 0, 0)
                    emit("fold", s, act=True)
                elif kind == CALL:
                    stacks[s] -= to_call
                    bets[s] += to_call
                    contrib[s] += to_call
                    if to_call > 0:
                        callers += 1
                    ev = (s, street, 1, to_call)
                    if to_call:
                        emit("call", s, to_call, act=True)
                    else:
                        emit("check", s, act=True)
                else:
                    to = int(amt)
                    if to < o.min_raise_to:
                        to = o.min_raise_to
                    if to > o.max_raise_to:
                        to = o.max_raise_to
                    add = to - bets[s]
                    stacks[s] -= add
                    bets[s] = to
                    contrib[s] += add
                    if to - cur >= last_raise:
                        last_raise = to - cur
                    cur = max(cur, to)
                    raises += 1
                    aggressor = s
                    first_in = False
                    to_act = len(order) - 1
                    ev = (s, street, 2, to)
                    emit("raise", s, to, act=True)
                for b in obs_t:
                    b.observe(*ev)
        # settle
        if live == 1:
            w = next(i for i in rot if in_hand[i])
            stacks[w] += sum(contrib)
            emit("win", w, sum(contrib))
        else:
            vals = {}
            for s in rot:
                if in_hand[s]:
                    vals[s] = showdown(holes[s], shared)
                    emit("show", s, cards=[CARD[c] for c in holes[s]])
            remaining = contrib[:]
            pots = []
            while True:
                pos = [c for c in remaining if c > 0]
                if not pos:
                    break
                lv = min(pos)
                pot = 0
                elig = []
                for i in range(n):
                    if remaining[i] > 0:
                        pot += lv
                        remaining[i] -= lv
                        if i in vals:
                            elig.append(i)
                if not elig:
                    elig = list(vals)
                best = max(vals[i] for i in elig)
                winners = [i for i in elig if vals[i] == best]
                share = pot // len(winners)
                award = {w: share for w in winners}
                for w in winners[: pot - share * len(winners)]:
                    award[w] += 1
                for w, a in award.items():
                    stacks[w] += a
                if pots and pots[-1][0] == winners:  # consecutive layers with the same winners form one pot
                    for w, a in award.items():
                        pots[-1][1][w] += a
                else:
                    pots.append((winners, award))
            for winners, award in pots:
                for w in winners:
                    emit("win", w, award[w])
        for s in rot:
            emit("stack", s, stacks[s])
        if hh is not None:
            rec["events"] = [[getattr(e.kind, "value", e.kind), e.seat, e.amount, e.cards] for e in log[h0:]]
            rec["failed"] = list(hfail)
            hh.append(rec)
        if check and sum(stacks) != total:
            st_.violations.append(f"chips {sum(stacks)} != {total} after hand {hand_no}")
        for b in hooks:
            if hasattr(b, "hand_result"):
                b.hand_result(stacks, start_stack)
            if hasattr(b, "end_hand"):
                b.end_hand(hand_no)
        hand_no += 1
        busted = [i for i in alive if stacks[i] <= 0]
        if busted:
            busted.sort(key=lambda i: start_stack[i])
            groups = {}
            for i in busted:
                groups.setdefault(start_stack[i], []).append(i)
            for k in sorted(groups):
                eliminated.append(groups[k])
    if check:
        L, bad = replay(log, ids, START)
        if bad or any(L[ids[i]] != stacks[i] for i in range(n)):
            st_.violations.append(f"event replay: {bad} stack mismatches, final {L} vs {stacks}")
        for s in plat:
            want = [e for e in log if own or e.seat != ids[s] or getattr(e.kind, "value", e.kind) not in ACTS]
            got = seen[s] + queue[s]
            if len(got) != len(want) or any(a is not b for a, b in zip(got, want)):
                st_.violations.append(f"seat {s}: delivered {len(got)} events, expected {len(want)}")
    survivors = {i: stacks[i] for i in range(n) if stacks[i] > 0}
    return eliminated, hand_no, survivors


def conv_grid():
    """The 16 combinations of the four open conventions."""
    out = []
    for k in range(16):
        out.append({"stack_includes_bet": bool(k & 1), "pot_includes_bets": not k & 2,
                    "own_action_in_events": not k & 4, "seat_ids": "shuffled" if k & 8 else "index"})
    return out


def selfcheck(tables=300, seed=1, out=print):
    """Lab-only tables give engine.play_table's exact results; chips and event replays hold on every hand."""
    from field import ARCHETYPES, FIELDS
    from hero import Hero
    names = sorted(set(FIELDS["typical"]) | set(FIELDS["holdout"]) | {"squeezer", "trapper", "sticky"})
    grid = conv_grid() + [dict(base=0, event_kind="enum")]
    diff = 0
    st = Stats()
    for t in range(tables):
        def mk():
            random.seed(seed + t)
            r = random.Random(seed + t)
            bots = [ARCHETYPES[r.choice(names)]() for _ in range(7)] + [Hero()]
            r.shuffle(bots)
            return bots
        a = engine.play_table(mk())
        b = play_platform_table(mk(), conv=grid[t % len(grid)], stats=st, check=True, frng=random.Random(t))
        diff += a != b
    out(f"sim vs engine.play_table, lab bots only: {tables} tables, {diff} differ; "
        f"chip/replay violations {len(st.violations)} {st.violations[:3]}")
    return diff == 0 and not st.violations


if __name__ == "__main__":
    sys.exit(0 if selfcheck(int(sys.argv[1]) if len(sys.argv) > 1 else 300) else 1)
