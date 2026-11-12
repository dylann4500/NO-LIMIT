import rep
print("\n### Our real bots (kit code) as the hero; points (se); paired differences on the same deals")
print("| field | v10 | v6 | v3b | v10 - v6 | v10 - v3b |\n|---|---|---|---|---|---|")
for f in ("r6", "r1"):
    for x in ("FULL", "TOP20"):
        c = [rep.ms(f"rb_{f}_{b}_in_{x}") for b in ("v10", "v6", "v3b")]
        d1 = rep.pd(f"rb_{f}_v10_in_{x}", f"rb_{f}_v6_in_{x}"); d2 = rep.pd(f"rb_{f}_v10_in_{x}", f"rb_{f}_v3b_in_{x}")
        print(f"| {f} {x} | " + " | ".join(f"{m:.1f} ({s:.2f})" for m, s, _ in c) + f" | {d1[0]:+.1f} ±{d1[1]:.1f} | {d2[0]:+.1f} ±{d2[1]:.1f} |")
print("\nfailed decisions (timeouts under local load): " + ", ".join(f"{b} {f} {x}: {sum(r[5] for r in rep.R(f'rb_{f}_{b}_in_{x}')['rows'])}" for f in ("r6","r1") for x in ("FULL","TOP20") for b in ("v10","v6","v3b")))
A = ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "CALLER", "HYPER"]
print("\n### Real v10 and v6 against the archetype skeletons in pure fields (3,000 tables; paired difference to the best skeleton on the same deals)")
print("| field | v10 | v6 | best skeleton | v10 - best skeleton | v10 - field's own style |\n|---|---|---|---|---|---|")
for x in A + ["TOP20"]:
    nm = (lambda b: f"rb_r6_{b}_in_{x}")
    best = max(A, key=lambda h: rep.ms(f"mu_{h}_in_{x}")[0])
    d = rep.pd(nm("v10"), f"mu_{best}_in_{x}")
    own = rep.pd(nm("v10"), f"mu_{x}_in_{x}") if x in A else (float("nan"), 0, 0)
    print(f"| {x} | {rep.ms(nm('v10'))[0]:.1f} ({rep.ms(nm('v10'))[1]:.2f}) | {rep.ms(nm('v6'))[0]:.1f} | {best} {rep.ms(f'mu_{best}_in_{x}')[0]:.1f} | {d[0]:+.1f} ±{d[1]:.1f} | {own[0]:+.1f} ±{own[1]:.1f} |")
KS=["vpip","pfr","3bet","fold_to_3bet","call_allin","flop_fold_to_bet","turn_fold_to_bet","river_fold_to_bet","wtsd","wsd"]
print("\nv10 measured rates (%): | field | " + " | ".join(KS) + " | 1st/2nd/3rd |")
for x in ["TOP20","FULL","WIDE","TIGHT","LIMPSHOVE"]:
    s = rep.style(f"rb_r6_v10_in_{x}")
    print(f"| {x} | " + " | ".join(f"{s[k]*100:.0f}" for k in KS) + f" | {s['places'][0]*100:.0f}/{s['places'][1]*100:.0f}/{s['places'][2]*100:.0f} |")
