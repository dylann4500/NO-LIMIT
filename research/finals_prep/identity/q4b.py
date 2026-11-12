import pickle, numpy as np
out = pickle.load(open("ledger.pkl", "rb"))
TOP = ["Lemonade", "2 Curry", "avalon", "sandylikesfrogs", "Team 123", "Team 72", "AZ", "pocket rockets", "Team 82", "Gavilan", "TeamBallHog", "thepastaway", "stanford deviants", "Always Folds", "Curious George", "Golden Knight", "nik airball", "one in a krillion", "Chikerbot", "Foldemort"]
def quad(k, T, X=None, late=None):
    """0.5*[(fT-f0)^2-(fT-fX)^2]*(P+B) per chance, summed; points per recognising opponent per table"""
    tot = 0; det = []
    for i, r in enumerate(out[(k, T)]):
        d = r["fT"] - r["f0"]
        if abs(d) < 1e-9: det.append(0); continue
        unit = r["bound"] / abs(d) / 7  # (P+B)*N*slope per opponent
        if late == 10: unit = r["b10"] / abs(d) / 7
        if late == 20: unit = r["b20"] / abs(d) / 7
        fx = r["fT"] if X is None else out[(k, X)][i]["fT"]
        v = 0.5 * (d * d - (r["fT"] - fx) ** 2) * unit
        tot += v; det.append(v)
    return tot, det
K = ["3-bet", "flop bet", "turn bet", "river bet", "BB steal"]
print("QUADRATIC ESTIMATE of value of knowing the seat, points per recognising opponent per table (bluff thresholds spread evenly over hands)")
print(f"{'team':20s} " + " ".join(f"R{k:<5d}" for k in range(1, 7)) + "  mean | linear upper bound mean | R6 split: " + " / ".join(K) + " | R6 if known only after hand 10 / 20")
for T in range(20):
    v = [quad(k, T)[0] for k in range(1, 7)]; b = np.mean([sum(r['bound'] for r in out[(k, T)]) / 7 for k in range(1, 7)])
    print(f"{TOP[T]:20s} " + " ".join(f"{x:6.2f}" for x in v) + f" {np.mean(v):6.2f} | {b:6.2f} | " + " / ".join(f"{x:.2f}" for x in quad(6, T)[1]) + f" | {quad(6, T, late=10)[0]:.2f} / {quad(6, T, late=20)[0]:.2f}")
print("median across the other 19 teams, R6: quad %.2f, linear %.2f" % (np.median([quad(6, T)[0] for T in range(20) if T != 2]), np.median([sum(r['bound'] for r in out[(6, T)]) / 7 for T in range(20) if T != 2])))
print("\nMISIDENTIFICATION (quadratic model): opponent treats our seat (avalon, R6 truth) as team X. Its gain vs treating us as the average finalist, points/table. Negative = its counter is worse against us than no profile at all.")
res = sorted((quad(6, 2, X)[0], TOP[X], quad(6, 2, X)[1]) for X in range(20))
for tot, nm, det in res: print(f"  as {nm:20s} {tot:+6.2f} | " + " / ".join(f"{x:+.2f}" for x in det))
print("\nSame for avalon R1 truth (the over-calling bot):")
res = sorted((quad(1, 2, X)[0], TOP[X]) for X in range(20))
print("  " + ", ".join(f"{nm} {tot:+.2f}" for tot, nm in res))
print("\nStale profile: opponent uses avalon's previous-round rates against this round's avalon (points/table vs average-finalist default)")
for k in range(2, 7):
    tot = 0
    for i, r in enumerate(out[(k, 2)]):
        d = r["fT"] - r["f0"]; unit = r["bound"] / max(1e-9, abs(d)) / 7
        tot += 0.5 * (d * d - (r["fT"] - out[(k - 1, 2)][i]["fT"]) ** 2) * unit
    print(f"  R{k} played with R{k - 1} profile: {tot:+.2f}   (fresh profile: {quad(k, 2)[0]:+.2f})")
