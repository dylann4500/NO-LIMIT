"""gen.py -> jobs_*.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
TOP = json.load(open("/Users/samuelchoi/NoLimit/NO-LIMIT/emu/runs/real_field/reference.json"))["teams"]
N = 12000
ARCH = ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "CALLER", "HYPER"]
SET = {"": dict(eps=0.1, beta=[0.06, 0.08, 0.12]), "_bluffy": dict(eps=0.15, beta=[0.1, 0.15, 0.2])}


def allteams(f):
    return [e["team"] for e in json.load(open(f"{HERE}/fields/{f}/field.json"))["entries"]]


def hero(name, f, h, base, mix, n=N, seed="m1", sfx=""):
    return dict(name=name, mode="hero", tables=n, seed=seed, hero=h, base=base, mix=mix, **SET[sfx])


def write(fn, jobs):
    names = [j["name"] for j in jobs]
    assert len(set(names)) == len(names)
    json.dump(jobs, open(f"{HERE}/{fn}", "w"))
    print(fn, len(jobs), "jobs", sum(j["tables"] * (3 if j["mode"] == "tourney" else 1) for j in jobs), "tables")


def matchup(f, sfx, heroes=ARCH, fields=ARCH):
    top = [f"team:{f}:{t}" for t in TOP]
    full = [f"team:{f}:{t}" for t in allteams(f)]
    J = []
    for h in heroes:
        H = f"arch:{f}:{h}"
        for x in fields:
            J.append(hero(f"mu{sfx}_{h}_in_{x}", f, H, [], [[f"arch:{f}:{x}", 1.0]], sfx=sfx))
        J.append(hero(f"mu{sfx}_{h}_in_TOP20", f, H, top, [], sfx=sfx))
        J.append(hero(f"mu{sfx}_{h}_in_FULL", f, H, full, [], sfx=sfx))
    return J


def e1(f, sfx=""):
    top = [f"team:{f}:{t}" for t in TOP]
    full = [f"team:{f}:{t}" for t in allteams(f)]
    J = [dict(name=f"e1_{f}_tourney", mode="tourney", tables=N, seed="m1", entries=top, **SET[sfx])]
    for t in TOP:
        J.append(hero(f"e1_{f}_full_{t.replace(' ', '_')}", f, f"team:{f}:{t}", [x for x in full if not x.endswith(':' + t)], [], n=8000, sfx=sfx))
    return J


def chain(f, sfx, heroes, mixes, tag):
    """mixes: list of (label, [[arch, share], ...]) on the top-20 base"""
    top = [f"team:{f}:{t}" for t in TOP]
    J = []
    for lab, mix in mixes:
        for h in heroes:
            J.append(hero(f"{tag}{sfx}_{h}_in_{lab}", f, f"arch:{f}:{h}", top, [[f"arch:{f}:{a}", s] for a, s in mix], sfx=sfx))
    return J


if __name__ == "__main__":
    write("jobs_e1_r6.json", e1("r6"))
    write("jobs_e1_r1.json", e1("r1"))
    write("jobs_mu.json", matchup("r6", ""))
    # chain grid: each archetype at 25/50% of the top-20 field
    mixes = [(f"{a}{int(s * 100)}", [[a, s]]) for a in ARCH[:5] for s in (0.25, 0.5)]
    write("jobs_chain.json", chain("r6", "", ARCH, mixes, "ch"))
    # tightness: aggressive share = half WIDE, half LIMPSHOVE (and a WIDE-only / shove-only split at 50/100)
    TV = ["TIGHT_c05", "TIGHT_c2", "TIGHT_c4", "TIGHT_s05", "TIGHT_s2", "TIGHT_s0", "TIGHT_o15", "TIGHT_o07"]
    mixes = [(f"AGG{int(a * 100)}", [["WIDE", a / 2], ["LIMPSHOVE", a / 2]]) for a in (0.25, 0.5, 0.75, 1.0)]
    mixes += [(f"AGH{int(a * 100)}", [["WIDE", a / 2], ["HYPER", a / 2]]) for a in (0.5, 1.0)]
    write("jobs_tight.json", chain("r6", "", ARCH + TV, mixes, "tg")
          + chain("r6", "", TV, [("TOP20x", [])], "tg")
          + [j for j in matchup("r6", "", TV, ["WIDE", "LIMPSHOVE", "HYPER"]) if "TOP20" not in j["name"] and "FULL" not in j["name"]])
    write("jobs_bluffy.json", matchup("r6_bluffy", "_bluffy")
          + chain("r6_bluffy", "_bluffy", ARCH, [("WIDE50", [["WIDE", .5]]), ("TIGHT50", [["TIGHT", .5]]), ("AGG50", [["WIDE", .25], ["LIMPSHOVE", .25]]), ("AGG100", [["WIDE", .5], ["LIMPSHOVE", .5]])], "ch")
          + [dict(name="e1_r6_bluffy_tourney", mode="tourney", tables=N, seed="m1", entries=[f"team:r6_bluffy:{t}" for t in TOP], **SET["_bluffy"])])
    # real bots, local
    J = []
    for f in ("r6", "r1"):
        top = [f"team:{f}:{t}" for t in TOP if t != "avalon"]
        full = [f"team:{f}:{t}" for t in allteams(f) if t != "avalon"]
        for b in ("v10", "v6", "v3b"):
            J.append(hero(f"rb_{f}_{b}_in_TOP20", f, "bot:" + b, top, [], n=4000))
            J.append(hero(f"rb_{f}_{b}_in_FULL", f, "bot:" + b, full, [], n=4000))
    for x in ["WIDE", "TIGHT", "LIMPSHOVE", "BAL", "HYPER", "CALLER"]:
        for b in ("v10", "v6"):
            J.append(hero(f"rb_r6_{b}_in_{x}", "r6", "bot:" + b, [], [[f"arch:r6:{x}", 1.0]], n=3000))
    write("jobs_rb.json", J)
