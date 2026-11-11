import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
PCT = json.load(open('claude_iterate_r2/preflop.json'))['pct']
RANK = '23456789TJQKA'
def cls(c):
    a, b = c
    ra, rb = sorted([a[0], b[0]], key=RANK.index, reverse=True)
    return ra + rb if ra == rb else ra + rb + ('s' if a[1] == b[1] else 'o')
rf = collections.Counter(); rf_bb = collections.defaultdict(list)
allin = []
callers = collections.defaultdict(lambda: [0, 0])  # opp team: faced our shove, called
shovers = []  # (stack_bb of shover, our response)
for h in H:
    me = h['seat']; bb = h['blinds'][1]; st = {int(k): v for k, v in h['stacks'].items()}
    if not st.get(me): continue
    names = h['names']
    street = 0; bets = collections.defaultdict(int); our_raise = None; shows = {}
    seq = []
    for e in h['events']:
        k, s, a, c = e
        if k == 'board': street += 1
        if k == 'show': shows[s] = c
        if street == 0 and k in ('fold', 'call', 'raise', 'check') and s is not None:
            seq.append((s, k, a))
    myacts = [x for x in seq if x[0] == me]
    # opens that got re-raised and we folded
    kinds = ''.join(x[1][0] for x in myacts)
    if kinds.startswith('rf'):
        i = seq.index(myacts[0]); after = [x for x in seq[i+1:] if x[1] == 'raise']
        r = after[0] if after else None
        if r:
            shv = r[2] >= st[r[0]] * 0.95
            rf['shove' if shv else 'raise'] += 1
            rf_bb[('shove' if shv else 'raise')].append(round(min(st[me], st[r[0]]) / bb))
    # our preflop all-in confrontations with showdown
    if me in shows and street >= 0:
        pass
    # when we shove (raise >= 95% of stack) preflop: who calls
    for x in myacts:
        if x[1] == 'raise' and x[2] >= 0.95 * st[me]:
            i = seq.index(x)
            for y in seq[i+1:]:
                if y[0] != me and y[1] in ('call', 'raise', 'fold'):
                    t = names[str(y[0])]
                    callers[t][0] += 1
                    if y[1] != 'fold': callers[t][1] += 1
                    if y[1] != 'fold' and y[0] in shows:
                        allin.append((cls(h['hole']), cls(shows[y[0]]), round(st[me] / bb, 1), t))
print('open-then-fold vs:', rf, {k: (sorted(v)[len(v)//2], len(v)) for k, v in rf_bb.items()})
print('response to OUR shoves by team (faced, continued, rate):')
for t, v in sorted(callers.items(), key=lambda x: -x[1][0]): print('  %-22s %4d %4d %.2f' % (t, v[0], v[1], v[1] / max(1, v[0])))
print('our shove hand pct vs caller pct (median):')
import statistics
print(' ours', statistics.median(PCT[a] for a, b, _, _ in allin), ' callers', statistics.median(PCT[b] for a, b, _, _ in allin), len(allin))
print(' caller pct distribution', sorted(round(PCT[b], 2) for a, b, _, _ in allin)[::max(1, len(allin)//20)])
print(' our pct distribution', sorted(round(PCT[a], 2) for a, b, _, _ in allin)[::max(1, len(allin)//20)])
