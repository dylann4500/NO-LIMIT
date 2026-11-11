"""Portal-Agent gate on the local platform stand-in (platform_sim.py): decision parity with the bot's native policy
under every open platform convention, failure and re-delivery semantics, memory, latency and score.
usage: test_adapter.py <dir containing bot.py> [tables]
       test_adapter.py --selftest [tables]    harness check with built-in agents; needs no bot"""
import importlib, json, math, multiprocessing as mp, os, random, sys, zlib
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
SELF = "--selftest" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
if not SELF and not ARGS:
    sys.exit(__doc__)
sys.path[:0] = [os.path.join(HERE, "fake_sdk")] + ([] if SELF else [os.path.abspath(ARGS.pop(0))]) + [HERE]
if not SELF:
    bot = importlib.import_module("bot")
    os.environ["POKER_VARIANT"] = bot.VARIANT  # the engine and opponents must play the bot's game
from poker_agent_sdk import Action, ActionKind as K, Agent
import engine, platform_sim as ps
from field import ARCHETYPES, FIELDS

T = int(ARGS[0]) if ARGS else (200 if SELF else 1000)
M = max(20, T // 8)  # tables per convention combination
PROCS = 4
SEED = 7000
PAY = ps.PAYOUTS
NAMES = list(FIELDS["typical"])
W = [FIELDS["typical"][k] for k in NAMES]


class Native:
    """The bot's own policy on the lab interface, as G in test_bot.py. With SPY on, it notes the engine's Obs so
    the next Policy.safe_decide call from another Policy (the adapter's) can be compared with it field by field."""
    truth = None

    def __init__(self):
        self.p = bot.Policy()

    def act(self, o):
        if SPY:
            Native.truth = (self.p, {f: list(v) if isinstance(v, list) else v for f in FIELDS_CMP for v in [getattr(o, f, None)]})
        return self.p.safe_decide(o)

    def observe(self, seat, street, kind, amount):
        self.p.observe(seat, street, kind)

    def end_hand(self, n):
        self.p.end_hand()


SPY, FIELD_DIFF = False, Counter()
if not SELF:
    FIELDS_CMP = [f for f in getattr(getattr(bot, "State", None), "__slots__", ()) if f in engine.Obs.__slots__]
    _decide = bot.Policy.safe_decide

    def _spy(self, o):
        t = Native.truth
        if t is not None and self is not t[0]:
            Native.truth = None
            try:
                for f, v in t[1].items():
                    if getattr(o, f, None) != v and not (f == "min_raise_to" and not t[1]["can_raise"]):
                        FIELD_DIFF[f] += 1
                for f in ("hands", "vpip", "pf_raise"):  # opponent stats: re-sent events must not count twice
                    a, b = getattr(self, f, None), getattr(t[0], f, None)
                    if isinstance(a, dict) and isinstance(b, dict) and {k: x for k, x in a.items() if x and k != o.seat} \
                            != {k: x for k, x in b.items() if x and k != o.seat}:
                        FIELD_DIFF["stats." + f] += 1
            except Exception:
                FIELD_DIFF["spy error"] += 1
        return _decide(self, o)
    bot.Policy.safe_decide = _spy


# ---- selftest agents --------------------------------------------------------------------------------------
def _k(e):
    return getattr(e.kind, "value", e.kind)


class Ledger(Agent):
    """Check/fold on the portal API only. Rebuilds every stack, bet, the pot and the board from its events, keeps
    them in crc-guarded memory, and raises when the state or a `stack` event disagrees, so lost, repeated or
    misordered events and memory not kept the portal's way surface as crashes. Junk memory stops the audit."""
    conv = ps.CONV

    def act(self, state, memory):
        d = None
        try:
            if memory and int(memory[:8], 16) == zlib.crc32(memory[8:]):
                d = json.loads(memory[8:])
        except ValueError:
            pass
        ev = state.events
        if d is None:
            d = {"L": {str(x.seat): state.config.starting_stack for x in state.seats}, "B": {}, "P": 0, "H": None,
                 "D": [], "S": not memory and bool(ev) and _k(ev[0]) == "hand"}
        L, B = d["L"], d["B"]
        for e in ev:
            k, s, a = _k(e), str(e.seat), e.amount
            if k == "hand":
                if d["S"] and d["H"] is not None and a != d["H"] + 1:
                    raise AssertionError(f"hand {a} after {d['H']}")
                d["H"], d["P"], d["D"] = a, 0, []
                B.clear()
            elif k == "board":
                B.clear()
                d["D"] += e.cards
            elif k in ("blind", "call"):
                L[s] -= a
                B[s] = B.get(s, 0) + a
                d["P"] += a
            elif k == "raise":
                L[s] -= a - B.get(s, 0)
                d["P"] += a - B.get(s, 0)
                B[s] = a
            elif k == "win":
                L[s] += a
            elif k == "stack":
                if d["S"] and L[s] != a:
                    raise AssertionError(f"seat {s}: ledger {L[s]}, stack event {a}")
                L[s] = a
        if d["S"]:
            self.audit(state, d)
        b = json.dumps(d).encode()
        return (Action.check() if state.can(K.CHECK) else Action.fold()), b"%08x" % zlib.crc32(b) + b

    def audit(self, st, d):
        c, L, B, me = self.conv, d["L"], d["B"], str(st.seat)
        for x in st.seats:
            k = str(x.seat)
            if x.stack != L[k] + (B.get(k, 0) if c["stack_includes_bet"] else 0) or x.bet != B.get(k, 0):
                raise AssertionError(f"seat {k}: stack/bet {x.stack}/{x.bet}, ledger {L[k]}/{B.get(k, 0)}")
        pot = d["P"] - (0 if c["pot_includes_bets"] else sum(B.values()))
        cur = max(list(B.values()) + [0 if d["D"] else st.blinds[1]])
        to_call = min(cur - B.get(me, 0), L[me])
        ks = [a.kind for a in st.legal_actions]
        if st.pot != pot or st.to_call != to_call:
            raise AssertionError(f"pot/to_call {st.pot}/{st.to_call}, ledger {pot}/{to_call}")
        if (K.FOLD in ks) != (to_call > 0) or (K.CHECK in ks) != (to_call == 0) or (K.CALL in ks) != (to_call > 0):
            raise AssertionError(f"legal {st.legal_actions} with to_call {to_call}")
        if st.board != d["D"] or st.hand_number != d["H"] or len(set(st.board + st.cards)) != len(st.board) + 2:
            raise AssertionError(f"board {st.board} / hand {st.hand_number}, ledger {d['D']} / {d['H']}")
        h, ev = st.history, st.events
        hf = [e for e in h if c["own_action_in_events"] or e.seat != st.seat or _k(e) not in ps.ACTS]
        cut = max((i for i, e in enumerate(ev) if _k(e) == "hand"), default=None)
        tail = ev[cut:] if cut is not None else ev[-len(hf):]
        if not h or _k(h[0]) != "hand" or h[0].amount != st.hand_number or len(tail) > len(hf) or \
                any(a is not b for a, b in zip(hf[len(hf) - len(tail):], tail)) or (cut is not None and len(tail) != len(hf)):
            raise AssertionError(f"history {h} does not end with this hand's events {tail}")
        P, Bh = 0, {}
        for e in h:
            k, a = _k(e), e.amount
            if k == "board":
                Bh = {}
            elif k in ("blind", "call", "raise"):
                add = a if k != "raise" else a - Bh.get(e.seat, 0)
                P, Bh[e.seat] = P + add, Bh.get(e.seat, 0) + add
        cfg, hpl = st.config, st.config.hands_per_level
        live = [x.seat for x in st.seats if x.status != "busted"]
        if P != d["P"] or st.players_remaining != len(live) or sorted(st.bust_order) != sorted(x.seat for x in st.seats if x.status == "busted") \
                or st.button not in live or st.blinds != cfg.blinds[min(st.blind_level - c["base"], len(cfg.blinds) - 1)] \
                or st.hands_until_next_level != hpl - (st.hand_number - c["base"]) % hpl or cfg.seat != st.seat:
            raise AssertionError(f"history chips {P} vs {d['P']}, or table/tournament fields inconsistent")


class CheckFold:
    def act(self, o):
        return (1, 0) if o.to_call == 0 else (0, 0)


class Bad(Agent):
    """Fails on purpose in every documented way, and checks on its next turn that the platform stored or kept its
    memory and dropped or re-sent its events as the portal says for that failure."""
    r = random.Random(5)
    expect, viol, prev, resent = Counter(), [], {}, 0
    MODES = ["ok"] * 4 + ["notoffered", "floatlow", "floatok", "over", "strkind", "nonaction", "exc", "notuple",
                          "badmem", "bigmem"]

    def act(self, state, memory):
        key, ev = (state.config.table_id, state.seat), state.events
        p = Bad.prev.get(key)
        if p:
            mode, mem_in, mem_out, ev_in, want = p
            kept = memory == mem_in and len(ev) >= len(ev_in) and all(a is b for a, b in zip(ev, ev_in))
            stored = memory == mem_out[: state.config.memory_bytes] and not (ev_in and ev and ev[0] is ev_in[0])
            if mode in ("exc", "notuple", "badmem"):
                if not kept:
                    Bad.viol.append(f"{mode}: memory not kept or events not re-sent")
            elif kept:
                Bad.resent += 1  # only an injected timeout may do this
            elif not stored:
                Bad.viol.append(f"{mode}: returned memory not stored, or events re-sent")
            if want is not None and stored:
                r = next((e for e in ev if e.seat == state.seat and _k(e) == "raise"), None)
                if r is None or type(r.amount) is not int or r.amount != want:
                    Bad.viol.append(f"float raise: played {r}, expected {want}")
        mode = Bad.r.choice(Bad.MODES)
        out, want = b"m%d" % Bad.r.randrange(10 ** 6), None
        rz, ck = state.can(K.RAISE), state.can(K.CHECK)
        a = good = Action.check() if ck else Action.call()
        if mode == "notoffered":
            a = Action.fold() if ck else Action.check()
        elif mode == "floatlow":
            a = Action.raise_to(rz.min_amount - 0.5 if rz else 100.5)
        elif mode == "floatok" and rz:
            a, want = Action.raise_to(rz.min_amount + 0.99), rz.min_amount
        elif mode == "over":
            a = Action.raise_to(rz.max_amount + 1 if rz else 10 ** 9)
        elif mode == "strkind":
            a = Action("check" if ck else "call")
        elif mode == "bigmem":
            out = b"x" * 70000
            Bad.expect["truncated"] += 1
        Bad.expect[{"exc": "error", "notuple": "malformed", "badmem": "malformed"}.get(
            mode, "illegal" if mode in ("notoffered", "floatlow", "over", "strkind", "nonaction") else "ok")] += 1
        Bad.prev[key] = (mode, memory, out, list(ev), want)
        if mode == "exc":
            raise RuntimeError("deliberate")
        if mode == "notuple":
            return good
        if mode == "badmem":
            return good, "not bytes"
        if mode == "nonaction":
            return "call", out
        return a, out


if SELF:
    AGENT, SHADOW = Ledger, CheckFold
else:
    AGENT, SHADOW = bot.Agent, Native


# ---- runs --------------------------------------------------------------------------------------------------
def tables_job(job):
    global SPY
    conv, lo, hi, opt = job
    Ledger.conv = dict(ps.CONV, **conv)
    SPY = opt.get("spy", False) and not SELF
    FIELD_DIFF.clear()
    st, pts = ps.Stats(), []
    pool = [AGENT() for _ in range(3)] if opt.get("pool") else None
    for t in range(lo, hi):
        random.seed(SEED + t)
        pos = random.randrange(8)
        bots = [ARCHETYPES[x]() for x in random.choices(NAMES, W, k=7)]
        if opt.get("engine"):
            bots.insert(pos, SHADOW())
            e, _, s = engine.play_table(bots)
        else:
            bots.insert(pos, ps.Plat(pool or AGENT(), SHADOW()))
            e, _, s = ps.play_platform_table(bots, conv=conv, stats=st, fail_rate=opt.get("fail", 0.0),
                                             garbage=opt.get("garbage", 0.0), frng=random.Random(SEED * 7919 + t),
                                             check=True)
        pts.append(engine.points_for(e, s, PAY)[pos])
    st.extra.update(FIELD_DIFF)
    return st, pts


def run(conv=None, n=T, **opt):
    k = max(1, min(PROCS * 4, n // 5))
    cut = [n * i // k for i in range(k + 1)]
    with mp.get_context("fork").Pool(min(PROCS, k)) as p:
        res = p.map(tables_job, [(conv or {}, cut[i], cut[i + 1], opt) for i in range(k)])
    st, pts = ps.Stats(), []
    for s, q in res:
        st.merge(s)
        pts += q
    return st, pts


def parity(st):
    n = sum(st.cmp.values())
    s = n - sum(st.diff.values())
    return n, s, 100.0 * s / max(1, n)


def failed(st):
    return sum(v for k, v in st.fails.items() if k != "injected")


def mean_se(x):
    m = sum(x) / len(x)
    return m, math.sqrt(sum((v - m) ** 2 for v in x) / max(1, len(x) - 1) / len(x))


def show_fails(st, k=6):
    for why, state, act in st.fail_ex[:k]:
        print(f"   [{why}] {state}\n      returned/raised: {act.strip()}")


def bad_test(tables=60):
    """Three Bad seats with five lab bots: the platform's failure counts must equal what Bad meant to do. A second
    pass injects timeouts: Bad must then see re-sent events with its previous memory, never a mix."""
    ok = True
    for fail in (0.0, 0.1):
        st = ps.Stats()
        Bad.expect, Bad.viol, Bad.prev, Bad.resent = Counter(), [], {}, 0
        for t in range(tables if not fail else tables // 2):
            random.seed(SEED + t)
            bots = [ARCHETYPES[x]() for x in random.choices(NAMES, W, k=5)] + [Bad(), Bad(), Bad()]
            random.shuffle(bots)
            ps.play_platform_table(bots, stats=st, frng=random.Random(t), check=True, fail_rate=fail)
        e = Bad.expect
        got = {k: st.fails[k] for k in ("illegal", "error", "malformed")}
        want = {k: e[k] for k in got}
        print(f"\nBad agent, fail_rate {fail} ({st.decisions} decisions): platform counted {got}, {st.fails['injected']} "
              f"injected, truncated {st.truncated}, re-sent events on {st.redelivered} turns; agent did {want}, oversize "
              f"memory {e['truncated']}, saw re-sent events after a good turn {Bad.resent} times; memory/event violations "
              f"{len(Bad.viol)} {Bad.viol[:3]}; sim violations {len(st.violations)}")
        if fail:
            ok &= 0 < Bad.resent <= st.fails["injected"] and not Bad.viol and not st.violations
        else:
            ok &= got == want and st.truncated == e["truncated"] and not Bad.viol and not st.violations and not Bad.resent
            show_fails(st)
    return ok


def main():
    bad = []
    print(f"{'SELFTEST: Ledger check/fold agent vs CheckFold shadow' if SELF else 'bot: ' + bot.__file__}; "
          f"{T} tables, {M} per convention combination, payouts {PAY}")
    if SELF and not ps.selfcheck(T):
        bad.append("sim differs from engine")
    runs = {}
    # 1. parity
    st0, pts0 = runs["default"] = run({}, T)
    n, s, pc = parity(st0)
    print(f"\n1. Decision parity, default conventions {ps.CONV}: {s}/{n} identical ({pc:.2f}%)")
    print(f"   {'street':8s} {'agent':8s} {'shadow':8s} {'n':>7s} {'differ':>7s}")
    for k in sorted(st0.cmp, key=lambda k: (ps.STREET.index(k[0]), k[1], k[2])):
        print(f"   {k[0]:8s} {k[1]:8s} {k[2]:8s} {st0.cmp[k]:7d} {st0.diff[k]:7d}")
    for x in st0.ex[:3]:
        print("   e.g.", x)
    if pc < 99:
        bad.append(f"parity {pc:.2f}% under default conventions")
    print(f"   all 16 combinations, {M} tables each:")
    print(f"   {'stack+bet':10s}{'pot+bets':10s}{'own evts':10s}{'seat ids':10s}{'decisions':>10s}{'identical':>11s}"
          f"{'failed':>8s}  policy inputs that differ from the engine's Obs (decisions)")
    grid = [(c, ", ".join(f"{k}={v}" for k, v in c.items())) for c in ps.conv_grid()]
    grid += [(dict(base=0), "base=0"), (dict(event_kind="enum"), "event_kind=enum")]
    for c, name in grid:
        st, _ = runs[name] = run(c, M, spy=True)
        n, s, pc = parity(st)
        f = "".join(f"{str(c[k]):10s}" for k in ps.FLAGS) if all(k in c for k in ps.FLAGS) else f"{name:40s}"
        fd = " ".join(f"{k}:{v}" for k, v in st.extra.most_common(4))
        print(f"   {f}{n:10d}{pc:10.2f}%{failed(st):8d}  {fd}" + ("   <99%" if pc < 99 else ""))
        if pc < 99 and st.ex:
            print("      e.g.", st.ex[0])
    # 2. failures injected
    stf, _ = runs["fail_rate=0.05"] = run({}, max(M, T // 2), fail=0.05, pool=True, spy=True)
    n, s, pc = parity(stf)
    print(f"\n2. fail_rate=0.05, a pool of 3 shared Agent copies answering every seat: {stf.fails['injected']} injected "
          f"timeouts, events re-sent on {stf.redelivered} turns; parity {s}/{n} ({pc:.2f}%); "
          f"exceptions {stf.fails['error']}, other failed decisions {failed(stf) - stf.fails['error']}; "
          f"policy inputs or opponent stats that differ: {dict(stf.extra) or 'none'}")
    if any(k.startswith("stats.") for k in stf.extra):
        bad.append("opponent stats differ from the shadow's after re-sent events")
    # 4b. junk memory
    stg, _ = runs["garbage"] = run({}, max(M, T // 4), garbage=0.02)
    # 3. failed decisions without injection
    tot = Counter()
    for name, (st, _) in runs.items():
        tot.update({k: v for k, v in st.fails.items() if k != "injected"})
    print(f"\n3. Failed decisions without injection, all runs: {sum(tot.values())} {dict(tot)}")
    shown = 0
    for name, (st, _) in runs.items():
        if failed(st) and shown < 6:
            print(f"   in run {name}:")
            show_fails(st, 6 - shown)
            shown += min(len(st.fail_ex), 6 - shown)
    if sum(tot.values()):
        bad.append(f"{sum(tot.values())} failed decisions")
    crashes = sum(st.fails["error"] for st, _ in runs.values())
    if crashes:
        bad.append(f"{crashes} exceptions")
    viol = [(name, v) for name, (st, _) in runs.items() for v in st.violations]
    if viol:
        bad.append(f"{len(viol)} sim invariant violations")
        print("   sim invariant violations:", viol[:5])
    # 4. memory
    sizes = [x for name, (st, _) in runs.items() if name != "garbage" for x in st.mem]
    trunc = sum(st.truncated for st, _ in runs.values())
    print(f"\n4. Memory returned: max {max(sizes, default=0)} B, mean {sum(sizes) / max(1, len(sizes)):.0f} B, "
          f"truncated {trunc} times")
    print(f"   junk memory on {stg.garbage} of {stg.decisions} turns: exceptions {stg.fails['error']}, "
          f"illegal or malformed {stg.fails['illegal'] + stg.fails['malformed']}")
    # 5. latency
    L = sorted(st0.lat) or [0]
    q = lambda p: L[min(len(L) - 1, int(p * len(L)))] / 1e3
    print(f"\n5. act latency incl. memory, n={len(L)}: p50 {q(.5):.1f} p99 {q(.99):.1f} p99.9 {q(.999):.1f} "
          f"max {L[-1] / 1e3:.1f} us; over 1 ms: {sum(x > 1e6 for x in L)}, over 500 us: {sum(x > 5e5 for x in L)}")
    # 6. score
    _, pe = run({}, T, engine=True)
    (m0, s0), (me, se) = mean_se(pts0), mean_se(pe)
    dm, ds = mean_se([a - b for a, b in zip(pts0, pe)])
    same = sum(abs(a - b) < 1e-9 for a, b in zip(pts0, pe))
    print(f"\n6. Points vs typical field ({T} tables, same seeds): Agent on platform {m0:.2f} ± {s0:.2f}, native policy "
          f"in engine {me:.2f} ± {se:.2f}, paired difference {dm:+.2f} ± {ds:.2f}; identical result on {same}/{T} tables "
          f"(fair share {sum(PAY) / 8:.2f})")
    if SELF:
        if same != T:
            bad.append("check/fold agent scored differently from its lab twin")
        if not stf.redelivered or not stf.fails["injected"]:
            bad.append("no re-delivery exercised")
        if not bad_test():
            bad.append("bad-agent accounting")
    print("\nPASS" if not bad else "\nFAIL: " + "; ".join(bad))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
