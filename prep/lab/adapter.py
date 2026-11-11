# ---- platform adapter: the only code that knows the kit's API ---------------------------------
# make_bot.py appends this file to the generated bot, so Policy, State, PAYOUTS, gc and time are in scope.
# Written from docs/portal_getting_started.md before the kit shipped. Check every "KIT:" line at kickoff.
# Per-table state lives only in `memory`: self and globals are unreliable, and any copy may answer any table.
import struct
import poker_agent_sdk as _sdk

_Action = getattr(_sdk, "Action", None)
if _Action is None:  # KIT: where Action lives
    from poker_agent_protocol import Action as _Action

STACK_INCLUDES_BET = False  # KIT: does Seat.stack include that seat's bet this street? Detected at runtime when possible.
POT_INCLUDES_BETS = True  # KIT: does state.pot include this street's bets? Detected at runtime when possible.

_ACT = {"fold": 0, "check": 1, "call": 1, "raise": 2}
_STREET = {0: 0, 3: 1, 4: 2, 5: 3}
_CARD = {r + s: i * 4 + j for i, r in enumerate("23456789TJQKA") for j, s in enumerate("shdc")}
_HDR = b"A1"
_NONE = 0xFFFF
_DISC = VARIANT == "hole3discard"  # KIT: our discard variants (lab/variants/DISCARD.md); discard.py is inlined above


class _Board(list):
    """Board that knows the cards still to come (discard variants), read by equity_vs_range and feature."""
    __slots__ = ("to_come",)


def _kn(k):
    """Kind name from a string or an Enum member: 'raise', 'call', 'ActionKind.RAISE' all work."""
    s = str(getattr(k, "value", k)).lower().rsplit(".", 1)[-1]
    return "raise" if s in ("raise_to", "bet") else s


def _g(o, k, d=None):
    v = o.get(k) if isinstance(o, dict) else getattr(o, k, None)
    return d if v is None else v


def _card(c):
    v = _CARD.get(c)
    if v is None:
        c = str(c).strip()
        r = c[:-1].upper()
        v = _CARD[("T" if r == "10" else r) + c[-1].lower()]
    return v


def _blinds(state):
    b = _g(state, "blinds")
    if b is None:
        cfg = _g(state, "config")
        b = _g(cfg, "blinds")[int(_g(state, "blind_level", 0))]
    if isinstance(b, dict):
        return int(b.get("small", b.get("sb", b.get("small_blind")))), int(b.get("big", b.get("bb", b.get("big_blind"))))
    if isinstance(b, (list, tuple)):
        return int(b[0]), int(b[1])
    return int(_g(b, "small", _g(b, "sb"))), int(_g(b, "big", _g(b, "bb")))


def _load(mem, n):
    """flags, hand, street, hands[], vpip[], pfr[], seen[]; anything unreadable starts the table over."""
    try:
        if mem[:2] == _HDR:
            flags, cnt, hand, street = struct.unpack_from("<BBHB", mem, 2)
            if cnt == n:
                a = struct.unpack_from("<" + "HHHB" * n, mem, 7)
                return flags, hand, street, list(a[0::4]), list(a[1::4]), list(a[2::4]), list(a[3::4])
    except Exception:
        pass
    return 0, _NONE, 0, [0] * n, [0] * n, [0] * n, [0] * n


def _save(flags, hand, street, h, v, r, seen):
    n = len(h)
    a = [0] * (4 * n)
    a[0::4], a[1::4], a[2::4], a[3::4] = [min(x, 65535) for x in h], [min(x, 65535) for x in v], [min(x, 65535) for x in r], seen
    return _HDR + struct.pack("<BBHB", flags, n, hand if 0 <= hand < _NONE else _NONE, street) + struct.pack("<" + "HHHB" * n, *a)


def _street_info(hist, idx):
    """Raises, last raiser and callers on the current street, from this hand's events."""
    raises, agg, callers = 0, -1, 0
    for e in hist:
        k = _kn(_g(e, "kind", ""))
        if k == "board" or k == "hand":
            raises, agg, callers = 0, -1, 0
        elif k == "raise":
            raises += 1
            agg = idx.get(_g(e, "seat"), -1)
        elif k == "call" and (_g(e, "amount", 0) or 0) > 0:
            callers += 1
    return raises, agg, callers


def _order(dealt, btn, street):
    """Seats in acting order for this street, as the lab engine deals them."""
    if btn not in dealt:
        btn = max([x for x in dealt if x < btn] or dealt)
    bi = dealt.index(btn)
    rot = dealt[bi:] + dealt[:bi]
    if len(rot) == 2:
        return rot if street == 0 else rot[::-1]
    return rot[3:] + rot[:3] if street == 0 else rot[1:] + rot[:1]


def _act(state, memory):
    seats = _g(state, "seats")
    n = len(seats)
    ids = [_g(s, "seat") for s in seats]
    idx = {x: i for i, x in enumerate(ids)}
    me = idx[_g(state, "seat")]
    memory = memory or b""
    flags, hand, street, H, V, R, SEEN = _load(memory, n)

    # 1. Opponent stats from the public events since our last turn. The Policy keeps them in dicts and sets;
    #    rebuild those from memory, replay the events, and write them back.
    p = _P
    p.hands, p.vpip, p.pf_raise = dict(enumerate(H)), dict(enumerate(V)), dict(enumerate(R))
    p.seen_h = {i for i in range(n) if SEEN[i] & 1}
    p.seen_vp = {i for i in range(n) if SEEN[i] & 2}
    p.seen_pf = {i for i in range(n) if SEEN[i] & 4}
    start, ante = {}, [0] * n  # stacks at the start of this hand (from the last hand's `stack` events), antes posted
    for e in _g(state, "events", ()):
        k = _kn(_g(e, "kind", ""))
        if k == "hand":
            p.end_hand()
            street = 0
            hand = int(_g(e, "amount", 0) or 0)
            ante = [0] * n
        elif k == "board":
            street = min(3, street + 1)
        elif k in _ACT:
            s = idx.get(_g(e, "seat"))
            if s is not None:
                p.observe(s, street, _ACT[k])
        elif k == "stack" or k == "ante":
            s = idx.get(_g(e, "seat"))
            if s is not None:
                if k == "stack":
                    start[s] = int(_g(e, "amount", 0) or 0)
                else:
                    ante[s] += int(_g(e, "amount", 0) or 0)

    # 2. Normalised decision state, matching the lab engine's Obs field for field.
    status = [_kn(_g(s, "status", "active")) for s in seats]
    raw = [int(_g(s, "stack", 0)) for s in seats]
    bets = [int(_g(s, "bet", 0)) for s in seats]
    legal = {}
    for a in _g(state, "legal_actions", ()):
        legal.setdefault(_kn(a.kind), a)
    ra = legal.get("raise")
    cfg = _g(state, "config")
    # Conventions: bit0/1 stack includes bet (known, value), bit2/3 pot includes bets (known, value).
    # Stack first: preflop, a seat's stack plus antes plus (if excluded) its bet equals its hand-start stack.
    # Hand-start stacks come from the last hand's `stack` events, or the starting stack on the table's first hand.
    if not flags & 1 and not _g(state, "board"):
        if not start and memory[:2] != _HDR and int(_g(state, "hand_number", 0) or 0) <= 1:
            start = {i: int(_g(cfg, "starting_stack", 0) or 0) for i in range(n)}
        for i in start:
            if bets[i] > 0:
                if raw[i] + ante[i] + bets[i] == start[i]:
                    flags |= 1
                    break
                if raw[i] + ante[i] == start[i]:
                    flags |= 3
                    break
    if ra is not None and bets[me] > 0 and not flags & 1:
        if int(ra.max_amount) == raw[me] + bets[me]:
            flags |= 1
        elif int(ra.max_amount) == raw[me]:
            flags |= 3
    sincl = bool(flags & 2) if flags & 1 else STACK_INCLUDES_BET
    pot_raw, sb_total = int(_g(state, "pot", 0)), sum(bets)
    # Pot second, by chip conservation, and only once the stack convention is settled: with it unknown,
    # "stack includes bet, pot excludes bets" and the reverse add up to the same total.
    if flags & 1 and sb_total > 0 and not flags & 4:
        tot = int(_g(cfg, "starting_stack", 0) or 0) * n
        behind_sum = sum(raw) - (sb_total if sincl else 0)
        if behind_sum + pot_raw == tot:
            flags |= 12
        elif behind_sum + pot_raw + sb_total == tot:
            flags |= 4
    pincl = bool(flags & 8) if flags & 4 else POT_INCLUDES_BETS
    o = State()
    o.seat = me
    o.hole = [_card(c) for c in _g(state, "cards")]
    o.board = [_card(c) for c in _g(state, "board", ())]
    o.street = 0 if not o.board else max(1, min(3, len(o.board) - 2))
    if _DISC and o.board:
        b = _Board(o.board)
        b.to_come = discard_to_come(list(_g(state, "board", ())), _g(state, "history"))
        o.board, o.street = b, max(1, min(3, 3 - b.to_come))
    o.stacks = [raw[i] - bets[i] if sincl else raw[i] for i in range(n)]
    o.bets = bets
    o.stack, o.bet = o.stacks[me], bets[me]
    o.to_call = int(_g(state, "to_call", 0))
    o.cur = max(max(bets), o.bet + o.to_call)  # not max(bets): a short all-in blind still sets the full amount
    o.pot = pot_raw if pincl else pot_raw + sb_total
    o.sb, o.bb = _blinds(state)
    o.can_raise = ra is not None
    o.max_raise_to = o.bet + o.stack  # the Policy reads this as "all in" even when raising isn't offered
    o.min_raise_to = int(ra.min_amount) if ra is not None else min(o.cur + o.bb, o.max_raise_to)
    dealt = [i for i in range(n) if status[i] != "busted"]
    o.in_hand = [status[i] in ("active", "all_in", "allin") for i in range(n)]
    o.n_alive, o.n_live = len(dealt), sum(o.in_hand)
    hist = _g(state, "history")
    if hist and _g(hist[0], "kind") is not None:
        o.raises, o.aggressor, o.n_callers = _street_info(hist, idx)
    else:  # no usable history: approximate from the bets on the table
        top = max(bets)
        o.aggressor = bets.index(top) if top > (o.bb if o.street == 0 else 0) and bets.index(top) != me else -1
        o.raises, o.n_callers = int(o.aggressor >= 0), 0
    # Active seats still to act after us before the street closes: up to the last raiser, else to the end.
    order = _order(dealt, idx.get(_g(state, "button"), 0), o.street)
    nb = 0
    if me in order:
        pos, L = order.index(me), len(order)
        if o.aggressor in order:
            js = [(pos + d) % L for d in range(1, L)]
            stop = order.index(o.aggressor)
            if stop in js:
                js = js[: js.index(stop)]
        else:
            js = range(pos + 1, L)
        nb = sum(1 for j in js if status[order[j]] == "active" and o.stacks[order[j]] > 0)
    o.n_behind = nb
    pay = _g(cfg, "payouts")
    if pay and list(pay) != PAYOUTS:
        globals()["PAYOUTS"] = list(pay)

    # 3. Decide and translate. Only offered kinds, integer totals inside the legal range.
    phase = _kn(_g(state, "phase", "betting"))
    da = discard_action(state, _Action, _pc() + DISCARD_BUDGET_S) if "discard_action" in globals() else None
    if da is not None:  # KIT: variant phases. Discard: lab/v2/core/discard.py (its constants hold the kit mapping)
        act = da
    elif phase != "betting":
        act = _auto(state)  # KIT: other variant phases (auction...) go here
    else:
        k, amt = p.safe_decide(o)
        if k == 2 and ra is not None:
            act = _Action.raise_to(int(min(int(ra.max_amount), max(int(ra.min_amount), int(amt)))))
        elif k and "check" in legal:
            act = _Action.check()
        elif k and "call" in legal:
            act = _Action.call()
        elif "fold" in legal:
            act = _Action.fold()
        else:
            act = _auto(state)
    seen = [(i in p.seen_h) | (i in p.seen_vp) << 1 | (i in p.seen_pf) << 2 for i in range(n)]
    H = [p.hands.get(i, 0) for i in range(n)]
    V = [p.vpip.get(i, 0) for i in range(n)]
    R = [p.pf_raise.get(i, 0) for i in range(n)]
    return act, _save(flags, hand, street, H, V, R, seen)


def _auto(state):
    """The platform's own fallback: check if free, else fold, else the first offered kind at its minimum."""
    legal = _g(state, "legal_actions", ())
    for a in legal:
        if _kn(a.kind) == "check":
            return _Action.check()
    for a in legal:
        if _kn(a.kind) == "fold":
            return _Action.fold()
    first = legal[0]
    return _Action(first.kind, first.min_amount)


class Agent(_sdk.Agent):
    def act(self, state, memory):
        try:
            return _act(state, memory)
        except Exception:
            try:
                return _auto(state), memory
            except Exception:
                return _Action.fold(), memory


_P = Policy()


# One throwaway decision at import, so the first real one pays for nothing lazy. Plain objects stand in for
# the SDK's state; only attribute access is used.
class _O:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _warm():
    """UTG facing the blinds at 10/20, button on seat 0."""
    K = getattr(_sdk, "ActionKind", None)
    kinds = [getattr(K, x.upper()) if K else x for x in ("fold", "call", "raise")]
    bet = [0, 10, 20, 0, 0, 0, 0, 0]
    hole = [c for c in ("As", "Kd", "Qh", "Jc", "Ts") if _CARD[c] in DECK][:N_HOLE]
    st = _O(seat=3, cards=hole, board=[], pot=30, to_call=20, history=[], phase="betting", button=0,
            legal_actions=[_O(kind=kinds[0], min_amount=0, max_amount=0), _O(kind=kinds[1], min_amount=20, max_amount=20),
                           _O(kind=kinds[2], min_amount=40, max_amount=2000)],
            seats=[_O(seat=i, stack=2000 - bet[i], bet=bet[i], status="active") for i in range(8)],
            blinds=[10, 20], blind_level=0, events=[_O(kind="hand", seat=None, amount=0, cards=None)],
            config=_O(starting_stack=2000, payouts=list(PAYOUTS), blinds=[[10, 20]]))
    return _act(st, b"")


try:
    _warm()
except Exception:
    pass
gc.collect()
gc.freeze()
