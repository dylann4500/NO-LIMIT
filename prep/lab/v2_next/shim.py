"""Platform shim: run strategy code written against one set of portal conventions on whatever the platform uses.

The portal leaves three things open that silently change a bot's arithmetic: whether Seat.stack includes that seat's
bet this street, whether state.pot includes this street's bets, and whether a seat's own action is echoed in the events
of its next turn. A bot written for one guess loses most of its edge under another without a single error
(claude_default_b: 18 points per table -> 4). The shim detects each convention at runtime, the way lab/adapter.py does,
and hands the wrapped bot a canonical view: stack excludes the bet, pot includes this street's bets, own actions echoed.
Its state rides at the front of `memory`; the wrapped bot's memory passes through untouched.

    from shim import shimmed
    Agent = shimmed(InnerAgent)
"""
import struct

_HDR = b"S1"
_KINDS = ("fold", "check", "call", "raise")
_ACTS = set(_KINDS)


def _kn(k):
    s = str(getattr(k, "value", k)).lower().rsplit(".", 1)[-1]
    return "raise" if s in ("raise_to", "bet") else s


def _g(o, k, d=None):
    v = o.get(k) if isinstance(o, dict) else getattr(o, k, None)
    return d if v is None else v


class _Seat:
    __slots__ = ("seat", "stack", "bet", "status", "shown_cards")

    def __init__(self, s, stack):
        self.seat, self.stack, self.bet = _g(s, "seat"), stack, _g(s, "bet", 0)
        self.status, self.shown_cards = _g(s, "status"), _g(s, "shown_cards", [])


class _Event:
    __slots__ = ("kind", "seat", "amount", "cards")

    def __init__(self, kind, seat, amount, cards=None):
        self.kind, self.seat, self.amount, self.cards = kind, seat, amount, cards


class _View:
    """The platform state with a few fields replaced; everything else, methods included, falls through."""

    def __init__(self, state, **over):
        object.__setattr__(self, "_s", state)
        object.__setattr__(self, "_o", over)

    def __getattr__(self, k):
        o = object.__getattribute__(self, "_o")
        return o[k] if k in o else getattr(object.__getattribute__(self, "_s"), k)


def _split(mem):
    """flags (bit0/1 stack includes bet known/value, bit2/3 pot includes bets, bit4/5 own actions echoed),
    pending own action (kind index or 255, seat, amount), inner memory."""
    mem = bytes(mem or b"")
    if mem[:2] == _HDR and len(mem) >= 11:
        try:
            flags, kind, seat, amount = struct.unpack_from("<BBhi", mem, 2)
            return flags, (kind, seat, amount), mem[10:]
        except Exception:
            pass
    return 0, (255, 0, 0), b"" if mem[:2] == _HDR else mem


def _join(flags, pend, inner):
    return _HDR + struct.pack("<BBhi", flags, *pend) + bytes(inner or b"")


def canon(state, mem):
    """(canonical view, flags, inner memory)."""
    flags, pend, inner = _split(mem)
    seats = list(_g(state, "seats", ()))
    me = _g(state, "seat")
    idx = {_g(s, "seat"): i for i, s in enumerate(seats)}
    n = len(seats)
    raw = [int(_g(s, "stack", 0)) for s in seats]
    bets = [int(_g(s, "bet", 0)) for s in seats]
    events = list(_g(state, "events", ()) or ())
    # Own actions: if we acted last turn, an echoing platform puts our action first among the action events.
    if pend[0] != 255:
        if not flags & 16:
            first = next((e for e in events if _kn(_g(e, "kind", "")) in _ACTS), None)
            flags |= 48 if first is not None and _g(first, "seat") == pend[1] else 16
        if not flags & 32:
            proto = events[0].kind if events else "call"
            k = _KINDS[pend[0]]
            try:
                kind = k if isinstance(proto, str) else type(proto)(k)
            except Exception:
                kind = k
            events.insert(0, _Event(kind, pend[1], pend[2] if pend[0] >= 2 else None))
    # Stack convention first: preflop, a seat's stack plus antes plus (if excluded) its bet equals its hand-start stack.
    if not flags & 1:
        start, ante = {}, [0] * n
        for e in events:
            k = _kn(_g(e, "kind", ""))
            i = idx.get(_g(e, "seat"))
            if k == "hand":
                ante = [0] * n
            elif k == "stack" and i is not None:
                start[i] = int(_g(e, "amount", 0) or 0)
            elif k == "ante" and i is not None:
                ante[i] += int(_g(e, "amount", 0) or 0)
        if not _g(state, "board"):
            if not start and not mem and int(_g(state, "hand_number", 0) or 0) <= 1:
                start = {i: int(_g(_g(state, "config"), "starting_stack", 0) or 0) for i in range(n)}
            for i in start:
                if bets[i] > 0:
                    if raw[i] + ante[i] + bets[i] == start[i]:
                        flags |= 1
                        break
                    if raw[i] + ante[i] == start[i]:
                        flags |= 3
                        break
        if not flags & 1 and me in idx and bets[idx[me]] > 0:
            ra = next((a for a in _g(state, "legal_actions", ()) if _kn(a.kind) == "raise"), None)
            if ra is not None:
                if int(ra.max_amount) == raw[idx[me]] + bets[idx[me]]:
                    flags |= 1
                elif int(ra.max_amount) == raw[idx[me]]:
                    flags |= 3
    sincl = flags & 3 == 3
    pot = int(_g(state, "pot", 0) or 0)
    tb = sum(bets)
    if flags & 1 and tb > 0 and not flags & 4:
        tot = int(_g(_g(state, "config"), "starting_stack", 0) or 0) * n
        behind = sum(raw) - (tb if sincl else 0)
        if behind + pot == tot:
            flags |= 12
        elif behind + pot + tb == tot:
            flags |= 4
    pincl = flags & 12 != 4  # unknown counts as included, the canonical default
    over = {"events": events}
    if sincl:
        over["seats"] = [_Seat(s, raw[i] - bets[i]) for i, s in enumerate(seats)]
    if not pincl:
        over["pot"] = pot + tb
    return _View(state, **over), flags, inner


def _pending(state, action):
    """What our action will look like as an event: kind index, our seat, and its amount (call: chips added)."""
    try:
        k = _kn(action.kind)
        if k not in _ACTS:
            return (255, 0, 0)
        me = _g(state, "seat")
        amt = 0
        if k == "raise":
            amt = int(action.amount)
        elif k == "call":
            mine = next((s for s in _g(state, "seats", ()) if _g(s, "seat") == me), None)
            amt = int(_g(state, "to_call", 0) or 0)
            if mine is not None:
                amt = min(amt, int(_g(mine, "stack", amt)))
        return (_KINDS.index(k), int(me), amt)
    except Exception:
        return (255, 0, 0)


def shimmed(Inner):
    """An Agent class that runs Inner on the canonical view."""
    base = Inner.__mro__[1] if len(Inner.__mro__) > 1 else object

    class Agent(base):
        def __init__(self, *a, **kw):
            self._inner = Inner(*a, **kw)

        def act(self, state, memory):
            try:
                view, flags, inner = canon(state, memory)
            except Exception:
                return self._inner.act(state, memory)
            action, new_inner = self._inner.act(view, inner)
            return action, _join(flags, _pending(state, action), new_inner)

    Agent.__name__ = Inner.__name__
    return Agent
