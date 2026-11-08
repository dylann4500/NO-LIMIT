"""usage: python -I rep2.py agg2.json [label] -> AZ check, flop first-in/c-bet by #opps x connect, open/steal by players left"""
import collections, json, statistics as S, sys

A = json.load(open(sys.argv[1])); lab = sys.argv[2] if len(sys.argv) > 2 else ""
you, name, st, sz, pts = A["you"], A["name"], A["st"], A["sz"], A["pts"]
rows = sorted(((S.mean(v), s) for s, v in pts.items() if len(v) >= 30), reverse=True)
top = [s for _, s in rows if s != you][:6]
nm = lambda s: ("US" if s == you else name.get(s, s[:8]))[:12]
g = lambda s, k: st.get(s, {}).get(k, 0)
gg = lambda grp, k: sum(g(s, k) for s in grp)
r = lambda a, b: f"{a / b:4.0%}" if b else "  - "
ntab = {s: len(pts[s]) for s in pts}

print(f"### {lab}: top6 = " + ", ".join(f"{nm(s)} {S.mean(pts[s]):.1f}" for s in top))
who = top + [you]
print("\n-- headline (open% of unopened, fold facing 1 raise, flop first-in bet%, VPIP 8/3/2-handed, chips w/o vs with showdown, bb/table)")
for s in who + ["TOP6"]:
    grp = top if s == "TOP6" else [s]
    nt = sum(ntab.get(x, 0) for x in grp)
    print(f"{('TOP6' if s=='TOP6' else nm(s)):12s} open {r(gg(grp,'open'),gg(grp,'unop'))} fold1raise {r(gg(grp,'face1_fold'),gg(grp,'face1'))} "
          f"flopFirstBet {r(gg(grp,'ff_bet'),gg(grp,'ff_opp'))} cbet {r(gg(grp,'cb'),gg(grp,'cb_opp'))} | VPIP 8h {r(gg(grp,'vpip_8'),gg(grp,'hands_8'))} "
          f"3h {r(gg(grp,'vpip_3'),gg(grp,'hands_3'))} 2h {r(gg(grp,'vpip_2'),gg(grp,'hands_2'))} | noSD {gg(grp,'bb_nosd')/nt:+6.1f} SD {gg(grp,'bb_sd')/nt:+6.1f} bb/table")

print("\n-- open sizes (top 2 bb values) and postflop first-bet size clusters (top 3 pot fractions)")
for s in who:
    z = sz.get(s, {})
    op = sorted(((v, k) for k, v in z.items() if k.startswith("open")), reverse=True)[:2]
    bt = sorted(((v, k) for k, v in z.items() if k.startswith("bet")), reverse=True)[:3]
    no = sum(v for k, v in z.items() if k.startswith("open")); nb = sum(v for k, v in z.items() if k.startswith("bet"))
    print(f"{nm(s):12s} open " + " ".join(f"{k[4:]}bb {v/no:3.0%}" for v, k in op) + " | bets " + " ".join(f"{k[3:]}pot {v/nb:3.0%}" for v, k in bt))

print("\n-- flop FIRST-IN bet% (any player, no bet yet) by #opponents x villain-visible connect (pair/draw/miss)")
hdr = [(no, cc) for no in ("1", "2", "3+") for cc in ("pair", "draw", "miss")]
print(f"{'':12s} " + " ".join(f"{no+'/'+cc:>9s}" for no, cc in hdr))
for s in who + ["TOP6"]:
    grp = top if s == "TOP6" else [s]
    print(f"{('TOP6' if s=='TOP6' else nm(s)):12s} " + " ".join(f"{r(gg(grp,f'ff_bet_{no}_{cc}'),gg(grp,f'ff_opp_{no}_{cc}')):>9s}" for no, cc in hdr))
print("-- flop C-BET% (preflop aggressor, checked to) same split")
for s in who + ["TOP6"]:
    grp = top if s == "TOP6" else [s]
    print(f"{('TOP6' if s=='TOP6' else nm(s)):12s} " + " ".join(f"{r(gg(grp,f'cb_{no}_{cc}'),gg(grp,f'cb_opp_{no}_{cc}')):>9s}" for no, cc in hdr))
print("   opp counts (TOP6 cb): " + " ".join(f"{gg(top,f'cb_opp_{no}_{cc}')}" for no, cc in hdr))

print("\n-- open% of unopened pots by players left; steal% (CO/BTN/SB first-in) by players left")
ns = ["8", "7", "6", "5", "4", "3", "2"]
print(f"{'':12s} " + " ".join(f"{'n'+n:>11s}" for n in ns))
for s in who + ["TOP6"]:
    grp = top if s == "TOP6" else [s]
    print(f"{('TOP6' if s=='TOP6' else nm(s)):12s} " + " ".join(f"{r(gg(grp,'open_'+n),gg(grp,'unop_'+n))}/{r(gg(grp,'steal_'+n),gg(grp,'steal_opp_'+n)) if n!='2' else '  - '}" for n in ns))
print("   (each cell: open%/steal%)")
