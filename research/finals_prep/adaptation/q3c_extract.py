"""Targeted pass: every 3-bet opportunity and every open/steal opportunity of a few named teams, with exact sizes and
in-table history of the faced seat. usage: python3 -I q3c_extract.py HANDS.gz OUT.pkl 'Team A|Team B'"""
import gzip, json, pickle, sys
path, out, names = sys.argv[1], sys.argv[2], sys.argv[3].split("|")
fh = gzip.open(path, "rt"); head = json.loads(fh.readline())
name = {e["entry_id"]: e["team_name"] for e in head["entries"]}
ids = {e["entry_id"]: e["team_name"] for e in head["entries"] if e["team_name"] in names}
AV = name[head["you"]]
rows = []   # 3-bet opps
for line in fh:
    if line.startswith('{"you"'): continue
    if not any(i in line[:700] for i in ids): continue
    t = json.loads(line)
    if "hands" not in t: continue
    seats = t["seats"]; n = len(seats); tm = [None if t["fillers"][i] else name.get(seats[i]) for i in range(n)]
    tg = [i for i in range(n) if tm[i] in names]
    if not tg: continue
    f3n = [0] * n; f3k = [0] * n; opens = [0] * n; dealt = [0] * n; nh = len(t["hands"])
    tb_by = {}  # (actor seat) -> times it has 3-bet each opener seat
    for hi, h in enumerate(t["hands"]):
        bb = h["blinds"][1] or 1; sb = h["stacks_before"]; pl = sum(1 for x in sb if x > 0)
        left = list(sb); com = [0] * n; cur = 0; pfr = 0; opener = -1; open_to = 0; open_ai = False; callers = 0; limp = 0; folded = 0; bbseat = -1; tbs = -1
        for e in h["events"]:
            k = e["kind"]
            if k == "blind":
                s = e["seat"]; a = e["amount"]; left[s] -= a; com[s] += a; cur = max(cur, com[s]); bbseat = s; continue
            if k == "board": break
            if k not in ("fold", "check", "call", "raise"): continue
            s = e["seat"]; a = e.get("amount") or 0
            if pfr == 1 and s != opener and not open_ai and s in tg:
                o = opener
                rows.append((tm[s], tm[o] == AV, tm[o] or "FILLER", k == "raise", round(open_to / bb, 2), hi, nh, f3n[o], f3k[o], opens[o], dealt[o],
                             pl, round((left[s] + com[s]) / bb, 1), round((left[o] + com[o]) / bb, 1), open_behind, callers, s == bbseat,
                             tb_by.get((s, o), 0), k == "raise" and a - com[s] >= left[s]))
            if pfr == 2 and s == opener and cur > com[s]:
                f3n[s] += 1; f3k[s] += k == "fold"
            if k == "fold": folded += 1
            elif k == "call":
                left[s] -= a; com[s] += a
                if pfr == 0: limp += 1
                elif pfr == 1: callers += 1
            elif k == "raise":
                add = min(a - com[s], left[s]); ai = a - com[s] >= left[s]
                left[s] -= add; com[s] += add; cur = max(cur, com[s]); pfr += 1
                if pfr == 1:
                    opener = s; open_to = com[s]; open_ai = ai; open_behind = pl - folded - 1; opens[s] += 1
                elif pfr == 2:
                    tbs = s; tb_by[(s, opener)] = tb_by.get((s, opener), 0) + 1
        for i in range(n):
            if sb[i] > 0: dealt[i] += 1
pickle.dump(rows, open(out, "wb"))
print(out, len(rows))
