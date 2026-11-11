"""Parallel tournament runner. Each table: `hero_spec` at one seat, seven field bots."""
import math, os, random, sys, time, json
from multiprocessing import Pool
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import play_table, points_for, SCHEDULE_DEFAULT
from field import ARCHETYPES, FIELDS
from hero import Hero

# Guesses at the point table. The real one is announced at kickoff, so test across all of these.
PAYOUTS = {
    "top3": [50, 30, 20, 0, 0, 0, 0, 0],
    "top4": [45, 25, 18, 12, 0, 0, 0, 0],
    "steep": [100, 50, 30, 20, 10, 5, 2, 0],
    "linear": [7, 6, 5, 4, 3, 2, 1, 0],
    "wta": [100, 0, 0, 0, 0, 0, 0, 0],
    "gym": [100, 60, 40, 25, 15, 10, 5, 0],
}


# The announced table, when event_config.json exists.
from engine import EVENT
if EVENT.get("points"):
    PAYOUTS["real"] = list(EVENT["points"])


class _Folder:
    """A portal bot folder, loaded once per process like a field bot (genfield.load): its agent module, the strategy
    module that agent.py loads as `_core`, and the core's attributes as loaded (params.json applied), which every
    parameter set starts from. Parameter sets put their values on the shared core per decision (see _Bound)."""
    def __init__(self, d):
        import types, genfield
        name = "hero_" + os.path.basename(d)
        genfield.load(name, d)
        self.mod = sys.modules["genbot_" + name]
        self.core = self.mod._core
        self.base = dict(vars(self.core))
        self.ns = types.SimpleNamespace(**self.base)
        self.active = {}

    def attrs(self, p):
        """{core attribute: value} for parameters p, built from the loaded values by the folder's own agent.params,
        which skips bad keys silently; here they raise, so a tuner never spends a dimension on a missing constant."""
        for k in p:
            name, _, key = str(k).partition(".")
            cur = self.base.get(name)
            i = int(key) if key.lstrip("-").isdigit() else key
            if name not in self.base or key and not (isinstance(cur, dict) and i in cur or isinstance(cur, list) and isinstance(i, int) and -len(cur) <= i < len(cur)):
                raise KeyError(f"parameter {k!r}: no such constant in {self.core.__file__}")
        return self.mod.params(self.ns, p)

    def activate(self, attrs):
        for k in self.active:
            if k not in attrs:
                setattr(self.core, k, self.base[k])
        for k, v in attrs.items():
            setattr(self.core, k, v)
        self.active = attrs


class _Bound:
    """A portal agent for one parameter set. Processes are single-threaded, so setting its values on the shared core
    when another set played the last decision here is safe; the check costs nothing when the same set plays on."""
    def __init__(self, f, attrs):
        self.f, self.attrs, self.a = f, attrs, f.mod.Agent()

    def act(self, state, memory):
        if self.f.active is not self.attrs:
            self.f.activate(self.attrs)
        return self.a.act(state, memory)


_FOLDERS, _PSETS = {}, {}


def _folder(d):
    d = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), d))
    f = _FOLDERS.get(d)
    if f is None:
        f = _FOLDERS[d] = _Folder(d)
    return f


def portal_params(spec):
    """The parameters of a portal hero spec: spec["p"], plus any keys other than cls, dir and p (mtune's flat dicts)."""
    p = dict(spec.get("p") or {})
    p.update((k, v) for k, v in spec.items() if k not in ("cls", "dir", "p"))
    return p


def portal(spec):
    """{"cls": "portal", "dir": "v2", "p": {"PUSH_BB": 12, "POSF.3": 1.1}}: the portal-API bot in lab/<dir> as it
    would upload, with p overriding its strategy constants, seated as the platform runs it (two copies, timed)."""
    from platform_sim import Plat
    p = portal_params(spec)
    key = (spec["dir"], json.dumps(p, sort_keys=True))
    pool = _PSETS.get(key)
    if pool is None:
        f = _folder(spec["dir"])
        attrs = f.attrs(p)
        pool = _PSETS[key] = [_Bound(f, attrs), _Bound(f, attrs)]
        if len(_PSETS) > 64:
            _PSETS.pop(next(iter(_PSETS)))
    return Plat(pool)


def portal_defaults(d, keys):
    """The core's own values for parameter keys, without params.json: a fresh copy of the core module, read once."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("hero_defaults", _folder(d).core.__file__)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = {}
    for k in keys:
        name, _, key = k.partition(".")
        v = getattr(m, name)
        out[k] = v[int(key) if key.lstrip("-").isdigit() else key] if key else v
    return out


def make(spec):
    if isinstance(spec, dict):
        c = spec.get("cls")
        if c == "portal":
            return portal(spec)
        if c == "table":
            from strength import HeroTable
            return HeroTable(**{k: v for k, v in spec.items() if k != "cls"})
        if c:
            import methods
            return methods.CLASSES[c](**{k: v for k, v in spec.items() if k != "cls"})
        return Hero(**spec)
    return ARCHETYPES[spec]()


def time_limits():
    """(decision_ms, time_bank_ms) for portal seats: the platform's 1 and 100 scaled by FIELD_TIME_SCALE (default 0.4),
    because this Mac is about 2.5x faster than the tournament machines."""
    k = float(os.environ.get("FIELD_TIME_SCALE", "0.4"))
    return 1.0 * k, 100.0 * k


def play(bots, schedule=SCHEDULE_DEFAULT, frng=None, stats=None):
    """engine.play_table, or platform_sim's table (same rules, timed) when a seat is a portal bot: a g_* archetype or a
    portal hero (make({"cls": "portal", ...})), all under the same time_limits()."""
    P = sys.modules.get("platform_sim")
    if P is None or not any(P.is_portal(b) for b in bots):
        return play_table(bots, schedule)
    dm, tb = time_limits()
    return P.play_platform_table(bots, schedule, frng=frng, stats=stats, enforce_time=True, decision_ms=dm, time_bank_ms=tb)


def _work(a):
    heroes, field, payout_names, tables, seed, schedule = a
    random.seed(seed)
    fr = random.Random(f"frng{seed}")
    names = list(FIELDS[field])
    weights = [FIELDS[field][k] for k in names]
    out = {h: {p: [0.0, 0.0] for p in payout_names} for h in heroes}
    fails = {h: {} for h, s in heroes.items() if isinstance(s, dict) and s.get("cls") == "portal"}
    hands = 0
    for t in range(tables):
        for h, spec in heroes.items():
            seats = random.choices(names, weights, k=7)
            bots = [make(s) for s in seats]
            pos = random.randrange(8)
            bots.insert(pos, make(spec))
            st = sys.modules["platform_sim"].Stats() if h in fails else None
            elim, nh, surv = play(bots, schedule, fr, st)
            if st is not None:  # the hero's own decisions and failed ones (seat ids are table indexes here)
                c = fails[h]
                c["decisions"] = c.get("decisions", 0) + st.seat_n[pos]
                for (sid, why), k in st.seat_fails.items():
                    if sid == pos:
                        c[why] = c.get(why, 0) + k
            hands += nh
            for pn in payout_names:
                v = points_for(elim, surv, PAYOUTS[pn])[pos]
                c = out[h][pn]
                c[0] += v
                c[1] += v * v
    return out, hands, fails


def evaluate(heroes, field="typical", payouts=("top3", "linear", "steep"), tables=2000, procs=10, seed=7, schedule=SCHEDULE_DEFAULT, fails=None):
    """Returns {hero: {payout: (mean, stderr)}}. fails: a dict that gets each portal hero's decision and failure counts."""
    FIELDS[field]  # registers generated fields here, so the workers started below load the same bots
    per = max(1, tables // procs)
    jobs = [(heroes, field, list(payouts), per, seed * 1000 + i, schedule) for i in range(procs)]
    with Pool(procs) as pool:
        res = pool.map(_work, jobs)
    tot = per * procs
    final = {}
    for h in heroes:
        final[h] = {}
        for p in payouts:
            s = sum(r[0][h][p][0] for r in res)
            s2 = sum(r[0][h][p][1] for r in res)
            mean = s / tot
            var = max(0.0, s2 / tot - mean * mean)
            final[h][p] = (mean, math.sqrt(var / tot))
    if fails is not None:
        for r in res:
            for h, c in r[2].items():
                for k, v in c.items():
                    fails.setdefault(h, {})[k] = fails.setdefault(h, {}).get(k, 0) + v
    return final, sum(r[1] for r in res)


if __name__ == "__main__":
    t0 = time.time()
    heroes = {k: k for k in ARCHETYPES}
    heroes["HERO"] = {}
    res, hands = evaluate(heroes, tables=int(sys.argv[1]) if len(sys.argv) > 1 else 300)
    dt = time.time() - t0
    print(f"{hands} hands in {dt:.1f}s = {hands/dt:.0f} hands/s")
    fair = {p: sum(v) / 8 for p, v in PAYOUTS.items()}
    for h, r in sorted(res.items(), key=lambda x: -x[1]["top3"][0]):
        print(h.ljust(10), "  ".join(f"{p}:{m:6.2f}±{s:4.2f} (fair {fair[p]:.1f})" for p, (m, s) in r.items()))
