"""Check icm.value / icm.mh against the platform's equity_before / equity_after on a sample of tables.
usage: python -I check_icm.py HANDS.gz NTABLES"""
import gzip, json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icm
f = gzip.open(sys.argv[1], "rt"); f.readline(); N = int(sys.argv[2])
mx_b = mx_a = 0; nb = na = 0; bad = collections.Counter(); ex = []
paidbust = collections.Counter(); multi = []
nt = 0
for line in f:
    if line.startswith('{"you"'):
        continue
    t = json.loads(line); pay = t["payouts"]; nt += 1
    for h in t["hands"]:
        b, a = h["stacks_before"], h["stacks_after"]
        eb = icm.mh(b, pay); nb += 1
        # equity_before for dead seats: platform carries their final result; compare only alive
        d = max(abs(eb[i] - h["equity_before"][i]) for i in range(8) if b[i] > 0) if sum(x > 0 for x in b) > 0 else 0
        mx_b = max(mx_b, d)
        ea = icm.value(b, a, pay); na += 1
        alive = [i for i in range(8) if b[i] > 0]
        da = max(abs(ea[i] - h["equity_after"][i]) for i in alive)
        if da > 1e-3:
            bad["after_mismatch"] += 1
            if len(ex) < 6: ex.append((h["hand"], b, a, [round(x, 3) for x in ea], h["equity_after"]))
        mx_a = max(mx_a, da)
        busted = [i for i in alive if a[i] == 0]; surv = sum(1 for i in alive if a[i] > 0)
        for i in busted:
            place = surv + 1
            if place <= 3:
                paidbust[(len(alive), surv, round(h["equity_after"][i], 2))] += 1
        if len(busted) >= 2 and surv < 3:
            multi.append((b, a, h["equity_after"]))
    if nt >= N:
        break
print(f"tables {nt} hands {nb}: max |MH(before)-equity_before| over alive seats = {mx_b:.5f}")
print(f"max |value(before,after)-equity_after| over seats alive at start = {mx_a:.5f}; mismatches {bad}")
for e in ex: print(" ex", e)
print("bust in a paying place: (alive at start, survivors, platform equity_after of the busted) ->", sorted(paidbust.items()))
print("multi-bust into the money examples:", multi[:3])
