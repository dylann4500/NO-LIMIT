import json, pickle, sys, math
import rep, fitlib
TOP = json.load(open("/Users/samuelchoi/NoLimit/NO-LIMIT/emu/runs/real_field/reference.json"))["teams"]
def corr(xs, ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sum((x-mx)**2 for x in xs)*sum((y-my)**2 for y in ys))
for f in sys.argv[1:]:
    acc = pickle.load(open(f"fields/{f}/acc.pkl","rb"))
    tn = f"e1_{f}_tourney"
    if not rep.have(tn): continue
    T = rep.tourney(tn)
    print(f"\n### {f}: top-20 only vs full field (clone scores; real = that round's real score at our tables, se ~0.6)")
    print("| team | real | sim full | sim top-20 | change | VPIP | PFR | 3-bet | fold to 3-bet | open-jam | limp | call all-in | flop fold |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    rows=[]
    for t in TOP:
        s = fitlib.style(acc, t)
        fn = f"e1_{f}_full_{t.replace(' ','_')}"
        if not rep.have(fn): continue
        fm, fse, _ = rep.ms(fn)
        tm, tse, _ = T[t]
        rows.append((t, s, fm, fse, tm, tse))
    for t, s, fm, fse, tm, tse in sorted(rows, key=lambda r: -(r[4]-r[2])):
        print(f"| {t} | {s['pts']:.1f} | {fm:.1f} | {tm:.1f} | {tm-fm:+.1f} ±{math.hypot(fse,tse):.1f} | {s['vpip']*100:.0f} | {s['pfr']*100:.0f} | {s['3bet']*100:.0f} | {s['fold_to_3bet']*100:.0f} | {s['openjam']*100:.0f} | {s['limp']*100:.0f} | {s['call_allin']*100:.0f} | {s['flop_fold_to_bet']*100:.0f} |")
    d=[r[4]-r[2] for r in rows]
    print("\ncorr(real, sim full) = %.2f; rank order sim top20:"%corr([r[1]['pts'] for r in rows],[r[2] for r in rows]), ", ".join(f"{r[0]} {r[4]:.1f}" for r in sorted(rows,key=lambda r:-r[4])))
    print("correlation of the change with style: " + ", ".join(f"{k} {corr([r[1][k] for r in rows], d):+.2f}" for k in ["vpip","pfr","3bet","fold_to_3bet","fold_to_open","openjam","limp","call_allin","flop_bet","flop_fold_to_bet","turn_fold_to_bet","river_fold_to_bet","wtsd","wsd"]))
    print("corr(sim full, sim top20) = %.2f; sd full %.2f, sd top20 %.2f" % (corr([r[2] for r in rows],[r[4] for r in rows]), (sum((r[2]-sum(x[2] for x in rows)/len(rows))**2 for r in rows)/len(rows))**.5, (sum((r[4]-12.5)**2 for r in rows)/len(rows))**.5))
