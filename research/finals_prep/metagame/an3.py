import sys
import rep
A = ["TIGHT", "WIDE", "LIMPSHOVE", "BAL", "CALLER", "HYPER"]
sfx = sys.argv[1] if len(sys.argv) > 1 else ""
def row(label, names, base=None):
    got = {h: rep.ms(n) for h, n in names.items() if rep.have(n)}
    if not got: return
    r = sorted(got, key=lambda h: -got[h][0])
    lead = ""
    if len(r) > 1:
        d, se, _ = rep.pd(names[r[0]], names[r[1]])
        lead = f"{r[0]} by {d:+.1f} ±{se:.1f} over {r[1]}"
    print(f"| {label} | " + " | ".join(f"{got[h][0]:.1f}" if h in got else "-" for h in A) + f" | {lead} |")
def head(t):
    print(f"\n{t}\n| field | " + " | ".join(A) + " | best (paired lead over runner-up) |\n|---|" + "---|" * (len(A) + 1))
head(f"### Share of the top-20 field replaced by one style{sfx} (hero points per table; se about 0.17 at 12,000 tables)")
row("top-20 as is", {h: f"mu{sfx}_{h}_in_TOP20" for h in A})
for x in A[:5]:
    for s in (25, 50):
        row(f"{s}% {x}", {h: f"ch{sfx}_{h}_in_{x}{s}" for h in A})
    row(f"100% {x}", {h: f"mu{sfx}_{h}_in_{x}" for h in A})
head("### Aggressive share (half WIDE, half LIMPSHOVE; AGH = half WIDE, half HYPER) of the top-20 field")
row("0%", {h: f"mu{sfx}_{h}_in_TOP20" for h in A})
for lab in ("AGG25", "AGG50", "AGG75", "AGG100", "AGH50", "AGH100"):
    row(lab, {h: f"{'tg' if not sfx else 'ch'}{sfx}_{h}_in_{lab}" for h in A})
if not sfx:
    TV = ["TIGHT", "TIGHT_c05", "TIGHT_c2", "TIGHT_c4", "TIGHT_s0", "TIGHT_s05", "TIGHT_s2", "TIGHT_o07", "TIGHT_o15"]
    print("\n### Tight variants: points, and paired difference from the default TIGHT (same deals)\n| field | TIGHT | " + " | ".join(TV[1:]) + " | best non-tight |\n|---|" + "---|" * (len(TV) + 1))
    FL = [("top-20", "tg_%s_in_TOP20x", "mu_%s_in_TOP20")] + [(l, "tg_%s_in_" + l, "tg_%s_in_" + l) for l in ("AGG25", "AGG50", "AGG75", "AGG100", "AGH50", "AGH100")] + [("100% " + x, "mu_%s_in_" + x, "mu_%s_in_" + x) for x in ("WIDE", "LIMPSHOVE", "HYPER")]
    for lab, pv, pm in FL:
        b = pm % "TIGHT"
        if not rep.have(b): continue
        cells = [f"{rep.ms(b)[0]:.1f}"]
        for v in TV[1:]:
            n = pv % v
            if rep.have(n):
                d, se, _ = rep.pd(n, b); cells.append(f"{d:+.1f} ±{se:.1f}")
            else: cells.append("-")
        o = [(rep.ms(pm % h)[0], h) for h in ("WIDE", "LIMPSHOVE", "BAL", "HYPER") if rep.have(pm % h)]
        print(f"| {lab} | " + " | ".join(cells) + f" | {max(o)[1]} {max(o)[0]:.1f} |" if o else "")
