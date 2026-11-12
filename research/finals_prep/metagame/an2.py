import sys, math
import rep
A = ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "CALLER", "HYPER"]
F = A + ["TOP20", "FULL"]
sfx = sys.argv[1] if len(sys.argv) > 1 else ""
print(f"\n### Matchup table{sfx}: row = the one differing seat (hero), column = the other 7 seats. Points per table (se).")
print("| hero \\ field | " + " | ".join(F) + " | worst | mean of archetype fields |")
print("|---|" + "---|" * (len(F) + 2))
M = {}
for h in A:
    cells = []
    for f in F:
        n = f"mu{sfx}_{h}_in_{f}"
        if rep.have(n):
            m, se, _ = rep.ms(n); M[h, f] = (m, se); cells.append(f"{m:.1f} ({se:.2f})")
        else:
            cells.append("-")
    v = [M[h, f][0] for f in F if (h, f) in M] or [float("nan")]
    va = [M[h, f][0] for f in A if (h, f) in M] or [float("nan")]
    print(f"| {h} | " + " | ".join(cells) + f" | {min(v):.1f} | {sum(va)/len(va):.1f} |")
print("\nBest response per field (paired difference of the best over the runner-up, same deals):")
for f in F:
    r = sorted([h for h in A if (h, f) in M], key=lambda h: -M[h, f][0])
    if len(r) < 2: continue
    d, se, _ = rep.pd(f"mu{sfx}_{r[0]}_in_{f}", f"mu{sfx}_{r[1]}_in_{f}")
    dev = ""
    if f in A and (f, f) in M:
        d2, se2, _ = rep.pd(f"mu{sfx}_{r[0]}_in_{f}", f"mu{sfx}_{f}_in_{f}") if r[0] != f else (0, 0, 0)
        dev = f"; gain from deviating from the field's own style: {d2:+.1f} ±{se2:.1f}"
    print(f"- {f}: " + " > ".join(f"{h} {M[h, f][0]:.1f}" for h in r) + f"; lead {d:+.1f} ±{se:.1f}{dev}")
if "style" in sys.argv:
    KS=["vpip","pfr","open","openjam","limp","3bet","fold_to_3bet","4bet","call_allin","flop_bet","flop_fold_to_bet","turn_fold_to_bet","river_fold_to_bet","wtsd","wsd"]
    for f in ("TOP20", "FULL", "WIDE", "TIGHT"):
        print(f"\nMeasured rates (%) as the hero in the {f} field:\n| archetype | " + " | ".join(KS) + " | 1st/2nd/3rd | hands alive |\n|---|" + "---|"*(len(KS)+2))
        for h in A:
            s = rep.style(f"mu{sfx}_{h}_in_{f}")
            print(f"| {h} | " + " | ".join(f"{s[k]*100:.0f}" for k in KS) + f" | {s['places'][0]*100:.0f}/{s['places'][1]*100:.0f}/{s['places'][2]*100:.0f} | {s['hands_alive_per_table']:.0f} |")
