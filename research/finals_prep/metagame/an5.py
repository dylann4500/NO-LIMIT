import rep
H = ["TIGHT", "WIDE", "LIMPSHOVE", "BAL"]
print("\n### Fields mixed from the three main styles (quarters of the 7 opponents' seats on average; 8,000 tables, se about 0.2)")
print("| field: tight/wide/limp-shove | TIGHT | WIDE | LIMPSHOVE | BAL | best (paired lead) |\n|---|---|---|---|---|---|")
rows = []
for a in range(5):
    for b in range(5 - a):
        c = 4 - a - b
        if max(a, b, c) == 4: continue
        n = {h: f"sx_{h}_in_T{a}W{b}L{c}" for h in H}
        if not all(rep.have(x) for x in n.values()): continue
        m = {h: rep.ms(n[h])[0] for h in H}
        r = sorted(H, key=lambda h: -m[h])
        d, se, _ = rep.pd(n[r[0]], n[r[1]])
        rows.append((a, b, c, m))
        print(f"| {a*25}/{b*25}/{c*25} | " + " | ".join(f"{m[h]:.1f}" for h in H) + f" | {r[0]} by {d:+.1f} ±{se:.1f} over {r[1]} |")
print("\n### Seed check (fresh deals, seed m2) and clone setting")
print("| row | setting | TIGHT | WIDE | LIMPSHOVE | BAL | HYPER |\n|---|---|---|---|---|---|---|")
for lab, pat in (("top-20, seed m1", "mu{s}_{h}_in_TOP20"), ("top-20, seed m2", "seed2{s}_{h}_in_TOP20"), ("50% WIDE, seed m1", "ch{s}_{h}_in_WIDE50"), ("50% WIDE, seed m2", "seed2{s}_{h}_in_WIDE50")):
    for s, sl in (("", "standard"), ("_bluffy", "bluffy")):
        names = [pat.format(s=s, h=h) for h in ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "HYPER"]]
        print(f"| {lab} | {sl} | " + " | ".join(f"{rep.ms(x)[0]:.1f}" if rep.have(x) else "-" for x in names) + " |")
print("\n### Drift: archetypes and field both from round 1 (top-20 only)")
print("| | TIGHT | WIDE | LIMPSHOVE | BAL | HYPER |\n|---|---|---|---|---|---|")
print("| r1 | " + " | ".join(f"{rep.ms(f'r1a_{h}_in_TOP20')[0]:.1f}" if rep.have(f'r1a_{h}_in_TOP20') else "-" for h in ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "HYPER"]) + " |")
print("| r6 | " + " | ".join(f"{rep.ms(f'mu_{h}_in_TOP20')[0]:.1f}" for h in ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "HYPER"]) + " |")
print("\n### Tight variants under the bluffy setting: paired difference from default TIGHT")
print("| field | TIGHT | TIGHT_c2 | TIGHT_c4 | TIGHT_s0 | TIGHT_o07 |\n|---|---|---|---|---|---|")
for x, pat in (("top-20", "tg_bluffy_%s_in_TOP20x"), ("100% WIDE", "mu_bluffy_%s_in_WIDE"), ("100% LIMPSHOVE", "mu_bluffy_%s_in_LIMPSHOVE"), ("100% HYPER", "mu_bluffy_%s_in_HYPER")):
    b = "mu_bluffy_TIGHT_in_TOP20" if x == "top-20" else pat % "TIGHT"
    c = []
    for v in ["TIGHT_c2", "TIGHT_c4", "TIGHT_s0", "TIGHT_o07"]:
        if rep.have(pat % v):
            d, se, _ = rep.pd(pat % v, b); c.append(f"{d:+.1f} ±{se:.1f}")
        else: c.append("-")
    print(f"| {x} | {rep.ms(b)[0]:.1f} | " + " | ".join(c) + " |")
