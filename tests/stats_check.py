"""Real-field sanity check (STEERING 19:18): hero VPIP 25-32%, PFR 18-25%, postflop raise share <= 60%.
Usage: python tests/stats_check.py HERO_DIR [--tables N] [--seed S]
Field: HERO, v3_lr(=v3b), station x2, maniac, tag x2, HERO (8 seats). Stats for hero seat (first bot).
Postflop raise share = (bets+raises) / all hero postflop actions (fold/check/call/bet/raise)."""
import argparse, gzip, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PA = os.path.join(ROOT, "starter-kit/.venv/bin/poker-agent")
OPP = os.path.join(ROOT, "tests/opponents")


def run(hero, tables, seed, field):
    tmp = os.path.join(tempfile.mkdtemp(dir=os.environ.get("TMPDIR")), "h.jsonl.gz")
    bots = [hero] + field
    out = subprocess.run([PA, "play", *bots, "--tables", str(tables), "--seed", seed,
                          "--variant", "flop_discard_reveal", "--history", tmp, "--hero", "0"],
                         capture_output=True, text=True, cwd=os.path.join(ROOT, "starter-kit"))
    res = json.loads(out.stdout)
    return tmp, res


def preflop_profile(h, me, alive0, m):
    """First-in open rates by position and BB defence vs a single non-SB open (hero only)."""
    n = len(h["stacks_before"])
    blinds = [(e["seat"], e["amount"]) for e in h["events"] if e["kind"] == "blind"]
    if len(blinds) < 2 or me not in alive0:
        return
    bb = max(blinds, key=lambda x: x[1])[0]
    sb = min(blinds, key=lambda x: x[1])[0]
    behind = 0
    if me != bb:
        for step in range(1, n):
            sidx = (me + step) % n
            if sidx in alive0:
                behind += 1
            if sidx == bb:
                break
    raises, calls = [], 0
    for e in h["events"]:
        k = e["kind"]
        if k == "board":
            return
        if e.get("seat") == me and k in ("fold", "check", "call", "raise"):
            na = len(alive0)
            if not raises and not calls and me != bb:
                if 1 <= behind <= 3 and na >= 6:
                    m["late86_opp"] += 1; m["late86_open"] += k == "raise"
                elif 1 <= behind <= 3 and 3 <= na <= 5:
                    m["late35_opp"] += 1; m["late35_open"] += k == "raise"
                elif behind >= 4:
                    m["ep_opp"] += 1; m["ep_open"] += k == "raise"
            if me == bb and na >= 3 and len(raises) == 1 and not calls and raises[0][0] != sb \
                    and raises[0][1] < h["stacks_before"][raises[0][0]]:
                m["bb_opp"] += 1
                m["bb_fold"] += k == "fold"; m["bb_call"] += k == "call"; m["bb_raise"] += k == "raise"
            return
        if k == "raise":
            raises.append((e["seat"], e["amount"]))
        elif k == "call":
            calls += 1


def stats(path):
    """Hero VPIP/PFR/post-agg + behavior-diff metrics (heads-up flop/turn)."""
    hands = vpip = pfr = p_r = p_c = p_all = 0
    m = dict(hu_face=0, hu_fold=0, vp_opp=0, vp_bet=0, nvp_opp=0, nvp_bet=0,
             late86_opp=0, late86_open=0, late35_opp=0, late35_open=0, ep_opp=0, ep_open=0,
             bb_opp=0, bb_fold=0, bb_call=0, bb_raise=0)
    with gzip.open(path, "rt") as f:
        lines = f.read().splitlines()
    i = 1
    while i + 1 < len(lines):
        t = json.loads(lines[i]); y = json.loads(lines[i + 1])["you"]; i += 2
        me = y["seat"]
        for h in t["hands"]:
            if h["stacks_before"][me] <= 0:
                continue
            hands += 1
            alive = {k for k, x in enumerate(h["stacks_before"]) if x > 0}
            preflop_profile(h, me, alive, m)
            exposed = {}
            board = []
            bc = 0; v = r = False; facing = False
            for e in h["events"]:
                k = e["kind"]; sseat = e.get("seat")
                if k == "board":
                    bc += len(e.get("cards", [])); board += e.get("cards", []); facing = False
                    continue
                if k == "reveal" and e.get("cards"):
                    exposed[sseat] = e["cards"][0]
                    continue
                if k == "fold":
                    alive.discard(sseat)
                if sseat != me:
                    if k == "raise" and bc >= 3:
                        facing = True
                    continue
                if bc == 0:
                    if k in ("call", "raise"):
                        v = True
                    if k == "raise":
                        r = True
                    continue
                if k in ("raise", "call", "check", "fold"):
                    p_all += 1
                if k == "raise":
                    p_r += 1
                elif k == "call":
                    p_c += 1
                street = 1 if bc == 3 else 2 if bc == 4 else 3
                if street in (1, 2) and len(alive) == 2 and k in ("raise", "call", "check", "fold"):
                    opp = next(iter(alive - {me}), None)
                    if facing:
                        m["hu_face"] += 1; m["hu_fold"] += k == "fold"
                    elif street == 1:
                        brs = {c[0] for c in board}
                        vp = opp in exposed and exposed[opp][0] in brs
                        key = "vp" if vp else "nvp"
                        m[key + "_opp"] += 1; m[key + "_bet"] += k == "raise"
                if k == "raise":
                    facing = False
                if k == "fold":
                    alive.discard(me)
            vpip += v; pfr += r
    pc = lambda a, b: 100 * a / max(1, b)
    beh = (pc(m["hu_fold"], m["hu_face"]), m["hu_face"], pc(m["vp_bet"], m["vp_opp"]), m["vp_opp"],
           pc(m["nvp_bet"], m["nvp_opp"]), m["nvp_opp"],
           pc(m["late86_open"], m["late86_opp"]), m["late86_opp"], pc(m["late35_open"], m["late35_opp"]), m["late35_opp"],
           pc(m["ep_open"], m["ep_opp"]), m["ep_opp"],
           pc(m["bb_fold"], m["bb_opp"]), pc(m["bb_call"], m["bb_opp"]), pc(m["bb_raise"], m["bb_opp"]), m["bb_opp"])
    return hands, pc(vpip, hands), pc(pfr, hands), pc(p_r, p_r + p_c), pc(p_r, p_all), beh


def main():
    a = argparse.ArgumentParser(); a.add_argument("hero"); a.add_argument("--tables", type=int, default=150)
    a.add_argument("--seed", default="stats1"); a.add_argument("--pfr-max", type=float, default=25.0)
    a.add_argument("--vpip-max", type=float, default=32.0); x = a.parse_args()
    hero = os.path.abspath(x.hero)
    field = [os.path.join(ROOT, "bots/v3_lr"), f"{OPP}/station", f"{OPP}/station", f"{OPP}/maniac",
             f"{OPP}/tag", f"{OPP}/tag", hero]
    path, res = run(hero, x.tables, x.seed, field)
    n, v, p, rs, agg, beh = stats(path)
    bots = res["bots"]
    fails_by = {k: b["failed_decisions"] for k, b in bots.items() if b["failed_decisions"]}
    fails = sum(fails_by.values())
    hero_fails = sum(v for k, v in fails_by.items() if k.split("#")[0] == os.path.basename(hero))
    ok = 25 <= v <= x.vpip_max and 18 <= p <= x.pfr_max and agg <= 60  # agg = bet+raise share of postflop actions (calibrated: v3b 57.8 local vs 59 real)
    print(f"{os.path.basename(hero):10s} hands={n} VPIP={v:.1f}% PFR={p:.1f}% post_raise_share(bet+raise of actions)={agg:.1f}% "
          f"(raise/(raise+call)={rs:.1f}%) failed={fails} {fails_by} -> {'PASS' if ok else 'FAIL'}")
    print(f"   behavior: HU flop/turn fold-to-bet {beh[0]:.1f}% (n={beh[1]}), HU flop bet into visible pair "
          f"{beh[2]:.1f}% (n={beh[3]}), HU flop bet otherwise {beh[4]:.1f}% (n={beh[5]})")
    print(f"   preflop: late first-in open 8-6 alive {beh[6]:.1f}% (n={beh[7]}), 5-3 alive {beh[8]:.1f}% (n={beh[9]}), "
          f"EP open {beh[10]:.1f}% (n={beh[11]}); BB vs single non-SB open fold/call/raise "
          f"{beh[12]:.0f}/{beh[13]:.0f}/{beh[14]:.0f}% (n={beh[15]})")
    pts = {}
    for k, b in bots.items():
        pts.setdefault(k.split('#')[0], []).append(b["average_points"])
    print("   pts/seat: " + ", ".join(f"{k} {sum(v)/len(v):.2f}" for k, v in pts.items()))
    os.remove(path)
    sys.exit(0 if ok and not hero_fails else 1)


if __name__ == "__main__":
    main()
