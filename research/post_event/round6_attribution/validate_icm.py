"""Check our ICM against the server's equity_after (alive seats and busted seats), and our points/table.
usage: python -I validate_icm.py HANDS.gz NTABLES"""
import gzip, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from icm import icm_one, u_after

path, ntab = sys.argv[1], int(sys.argv[2])
maxerr_alive = 0.0; nb = 0; bust_mis = []; pts = []; sumchk = []
with gzip.open(path, "rt") as f:
    hdr = json.loads(f.readline()); you = hdr["you"]; cnt = 0
    for line in f:
        t = json.loads(line)
        if "hands" not in t:
            continue
        cnt += 1
        if cnt > ntab:
            break
        pay = t["payouts"]; me = t["seats"].index(you)
        pts.append(t["hands"][-1]["equity_after"][me])
        tot = 0.0
        for h in t["hands"]:
            sb_, sa, ea = h["stacks_before"], h["stacks_after"], h["equity_after"]
            st = {i: v for i, v in enumerate(sa) if v > 0}
            for i in st:
                maxerr_alive = max(maxerr_alive, abs(icm_one(st, i, pay) - ea[i]))
            for i in range(8):
                if sb_[i] > 0 and sa[i] == 0:
                    nb += 1
                    mine = u_after(sb_, sa, i, pay)
                    if abs(mine - ea[i]) > 1e-3:
                        bust_mis.append((h["hand"], sum(1 for v in sa if v > 0), sb_, sa, ea[i], mine))
            if sb_[me] > 0:
                ub = icm_one({i: v for i, v in enumerate(sb_) if v > 0}, me, pay)
                ua = u_after(sb_, sa, me, pay)
                tot += ua - ub
        sumchk.append((tot + 12.5, t["hands"][-1]["equity_after"][me]))
print(f"tables {cnt-1}: max |ICM - equity_after| alive seats = {maxerr_alive:.5f}; busts {nb}, mismatching {len(bust_mis)}")
for b in bust_mis[:8]:
    print("  bust mismatch: hand", b[0], "alive after", b[1], "sb", b[2], "sa", b[3], "server", b[4], "ours", round(b[5], 3))
print("our points/table (server last equity_after):", sum(pts) / len(pts))
print("max |12.5+sum(U_after-U_before) - final|:", max(abs(a - b) for a, b in sumchk))
