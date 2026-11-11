"""Portfolio entry default_c: claude_default_c_r3's strategy (lab/field_bots/claude_default_c_r3, variant-ready in core/)
behind the platform shim, which adapts it to whatever conventions the real platform uses. Upload this folder as a zip.
Set the variant in core/engine.py (VARIANT). An optional params.json here overrides the core's module-level constants:
{"PUSH_LIMIT": 9.0, "VT.1": 0.52, ...}."""
import importlib.util, json, os, sys
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
from shim import shimmed

_spec = importlib.util.spec_from_file_location("default_c_core", os.path.join(_here, "core", "agent.py"))
_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)


def params(core, p):
    """{name: new value} for p = {"NAME": v} (a module-level constant of core) or {"NAME.key": v} (one element of a dict
    or list constant; integer keys where they parse). Containers are copied, never changed in place. Bad keys are skipped."""
    out = {}
    for k, v in p.items():
        name, _, key = str(k).partition(".")
        try:
            cur = out[name] if name in out else getattr(core, name)
            if key:
                cur = dict(cur) if isinstance(cur, dict) else list(cur)
                cur[int(key) if key.lstrip("-").isdigit() else key] = v
            else:
                cur = v
            out[name] = cur
        except Exception:
            pass
    return out


try:
    with open(os.path.join(_here, "params.json")) as _f:
        _p = json.load(_f)
    for _k, _v in params(_core, _p.get("mu", _p)).items():  # a tuner output {"mu": {...}} works too
        setattr(_core, _k, _v)
except Exception:
    pass
Agent = shimmed(_core.Agent)


class _O:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _warm():
    """One throwaway decision at import, so the first real one doesn't pay for cold caches: UTG facing the blinds."""
    sdk = sys.modules.get("poker_agent_sdk")
    K = getattr(sdk, "ActionKind", None)
    kinds = [getattr(K, x.upper()) if K else x for x in ("fold", "call", "raise")]
    bet = [0, 10, 20, 0, 0, 0, 0, 0]
    hole = [c for c in ("As", "Kd", "Qh", "Jc") if c[0] not in getattr(_core.E, "DEAD_RANKS", "")][: _core.E.N_HOLE]
    st = _O(seat=3, cards=hole, board=[], pot=30, to_call=20, history=[], phase="betting", button=0, variant=None,
            legal_actions=[_O(kind=kinds[0], min_amount=0, max_amount=0), _O(kind=kinds[1], min_amount=20, max_amount=20),
                           _O(kind=kinds[2], min_amount=40, max_amount=2000)],
            seats=[_O(seat=i, stack=2000 - bet[i], bet=bet[i], status="active", shown_cards=[]) for i in range(8)],
            blinds=[10, 20], blind_level=1, hands_until_next_level=20, hand_number=1, players_remaining=8, bust_order=[],
            time_bank_ms=100, events=[_O(kind="hand", seat=None, amount=1, cards=None)],
            config=_O(starting_stack=2000, payouts=[50, 30, 20, 0, 0, 0, 0, 0], blinds=[[10, 20]], players=8,
                      hands_per_level=20, hand_cap=250, decision_ms=1, time_bank_ms=100, memory_bytes=65536))
    st.can = lambda k: next((a for a in st.legal_actions if a.kind == k), None)
    a = Agent()
    a.act(st, b"")
    # and one flop decision facing a bet, so the first postflop decision doesn't pay for cold evaluator caches
    fl = [c for c in ("7c", "8d", "2h", "Ts", "3c") if c[0] not in getattr(_core.E, "DEAD_RANKS", "")][:3]
    if _core.E.DISCARD:
        fl = fl[:2] + ["9h", "6s"]
    bet = [0, 0, 0, 60, 0, 0, 0, 0]
    ev = [_O(kind=k, seat=sd, amount=am, cards=cd) for k, sd, am, cd in (
        ("hand", None, 1, None), ("blind", 1, 10, None), ("blind", 2, 20, None), ("raise", 3, 60, None),
        ("call", 1, 50, None), ("fold", 2, None, None), ("board", None, None, fl), ("raise", 3, 60, None))]
    st2 = _O(**{k: v for k, v in st.__dict__.items() if k != "can"})
    st2.seat, st2.board, st2.pot, st2.to_call, st2.history, st2.events = 1, fl, 180, 60, ev, ev
    st2.legal_actions = [_O(kind=kinds[0], min_amount=0, max_amount=0), _O(kind=kinds[1], min_amount=60, max_amount=60),
                         _O(kind=kinds[2], min_amount=120, max_amount=1940)]
    st2.seats = [_O(seat=i, stack=(1940 if i in (1, 3) else (1980 if i == 2 else 2000)) - bet[i], bet=bet[i],
                    status="folded" if i not in (1, 3) else "active", shown_cards=[]) for i in range(8)]
    a.act(st2, b"")


try:
    _warm()
except Exception:
    pass
import gc as _gc
_gc.collect()
_gc.freeze()
# Collection pauses were the only decisions over 1 ms on the build box (3 in ~70k, up to 7 ms). A higher threshold
# removed them (max 0.37 ms) while still collecting, should anything in the core ever form reference cycles.
_gc.set_threshold(20000, 50, 100)
