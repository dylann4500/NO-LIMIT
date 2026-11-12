import json, pickle, os, math
W = os.path.dirname(os.path.abspath(__file__))
ORDER = [("P1","5da6d631"),("P2","af2a0969"),("P3","bd8406dc"),("P4","4d1fe6fb"),("R1","3e3dcc02"),("P5","b3ae5ccd"),
         ("R2","547666b1"),("P6","74eb2fd7"),("R3","260d2303"),("P7","4acb36cf"),("R4","250d256c"),("P8","925e7be1"),
         ("R5","2390e159"),("P9","13040f56"),("R6","729b67f6")]
LAB = dict(ORDER); ID = {v: k for k, v in ORDER}
SCORED = ["R1","R2","R3","R4","R5","R6"]
def api_results():
    """label -> {team: dict(avg, forfeited, tables, moe)}"""
    out = {}
    for f in os.listdir(W + "/api"):
        if f.startswith("res_"):
            d = json.load(open(W + "/api/" + f))
            lab = ID.get(d["tournament_id"][:8])
            out[lab] = {x["team_name"]: dict(avg=x["average_points"], forfeited=x["forfeited"], tables=x["tables"],
                                             moe=x["margin_of_error"]) for x in d["items"]}
    return out
def standings():
    d = json.load(open(W + "/api/standings.json"))["items"]
    return [(x["rank"], x["team_name"], x["total"]) for x in d]
_cache = {}
def load(lab, kind="bay"):
    key = (kind, lab)
    if key not in _cache:
        fid = LAB[lab] if kind == "bay" else lab
        _cache[key] = pickle.load(open(f"{W}/{os.environ.get("OUTDIR","out")}/{kind}_{fid}.pkl", "rb"))
    return _cache[key]
def rate(A, team, m, par=None):
    n = k = 0
    for p in ((0, 1) if par is None else (par,)):
        v = A.get((team, m, p))
        if v: n += v[0]; k += v[1]
    return n, k
