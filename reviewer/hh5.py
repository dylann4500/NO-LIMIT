"""River bets/raises heads-up where villain's exposed card + board already beats our hand. usage: python -I hh5.py HANDS.gz"""
import gzip, json, sys
from multiprocessing import Pool
import eval7
C = {}
def card(c):
    if c not in C: C[c] = eval7.Card(c)
    return C[c]
def work(pair):
    tl, yl = pair; t = json.loads(tl); y = json.loads(yl)["you"]; me = y["seat"]
    kept = {e["hand"]: e["cards"] for e in y["private_events"] if e["kind"] == "kept"}
    out = []
    for h in t["hands"]:
        kc = kept.get(h["hand"])
        if not kc: continue
        board, shown, folded, street = [], {}, set(), 0
        mybet = None
        for e in h["events"]:
            k, s = e["kind"], e.get("seat")
            if k == "board": board += e.get("cards") or []; street += 1; continue
            if k == "reveal" and s is not None and e.get("cards"): shown[s] = e["cards"][0]
            if k == "fold": folded.add(s)
            if street == 3 and k in ("raise",) and s == me and mybet is None:
                live = [x for x in range(len(t["seats"])) if h["stacks_before"][x] > 0 and x not in folded]
                opp = [x for x in live if x != me]
                if len(opp) == 1 and opp[0] in shown and len(board) == 5:
                    o = opp[0]
                    mine = eval7.evaluate([card(c) for c in kc + board])
                    theirs = eval7.evaluate([card(c) for c in [shown[o]] + board])
                    mybet = (theirs > mine, o, e["amount"])
                continue
            if mybet is not None and s == mybet[1] and k in ("fold", "call", "raise"):
                out.append((mybet[0], k, (h["stacks_after"][me] - h["stacks_before"][me]) / h["blinds"][1]))
                mybet = "done"
                break
    return out
def main():
    with gzip.open(sys.argv[1], "rt") as f:
        f.readline(); L = f.readlines()
    pairs = [(L[i], L[i + 1]) for i in range(0, len(L) - 1, 2) if '"hands"' in L[i][:200] or L[i].startswith('{"variant"')]
    with Pool(8) as p:
        R = [r for rs in p.map(work, pairs, chunksize=64) for r in rs]
    for beaten in (True, False):
        sel = [r for r in R if r[0] == beaten]
        if not sel: continue
        fo = sum(1 for r in sel if r[1] == "fold")
        print(f"{'VILLAIN VISIBLY BEATS US' if beaten else 'not visibly beaten     '}: river bets {len(sel):6d}  villain folds {fo/len(sel):5.1%}  "
              f"our hand result avg {sum(r[2] for r in sel)/len(sel):+6.1f}bb total {sum(r[2] for r in sel):+8.0f}bb")
if __name__ == "__main__":
    main()
