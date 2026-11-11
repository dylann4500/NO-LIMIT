import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
PCT = json.load(open('claude_iterate_r3/preflop.json'))['pct']
RANK = '23456789TJQKA'
def cls(c):
    a, b = c
    ra, rb = sorted([a[0], b[0]], key=RANK.index, reverse=True)
    return ra + rb if ra == rb else ra + rb + ('s' if a[1] == b[1] else 'o')
byn = collections.defaultdict(lambda: collections.Counter())
tables = collections.defaultdict(list)
for h in H: tables[h['table']].append(h)
hu = collections.Counter()
for t in tables.values():
    t.sort(key=lambda h: h['hand'])
    for h in t:
        me = h['seat']; st = {int(k): v for k, v in h['stacks'].items() if v}
        if not st.get(me): continue
        n = len(st); bb = h['blinds'][1]
        end = {e[1]: e[2] for e in h['events'] if e[0] == 'stack'}
        d = end.get(me, st[me]) - st[me]
        acts = ''.join(e[0][0] for e in h['events'] if e[1] == me and e[0] in ('fold', 'call', 'raise', 'check'))
        c = byn[n]; c['hands'] += 1; c['net'] += d / bb; c['stack_bb'] += st[me] / bb
        c['vpip'] += ('c' in acts[:2] or 'r' in acts[:2]); c['fold_first'] += acts[:1] == 'f'
        c['avg_bb_all'] += (sum(st.values()) / n) / bb
    # heads-up outcome
    last = t[-1]; st = {int(k): v for k, v in last['stacks'].items() if v}
    huh = [h for h in t if len([1 for v in h['stacks'].values() if v]) == 2 and h['stacks'].get(str(h['seat']))]
    if huh:
        end = {e[1]: e[2] for e in t[-1]['events'] if e[0] == 'stack'}
        me = t[-1]['seat']
        first = huh[0]; s0 = first['stacks'][str(me)] / sum(v for v in first['stacks'].values() if v)
        won = end.get(me, 0) > 0 and len([1 for v in end.values() if v]) == 1
        hu['reached'] += 1; hu['won'] += won; hu['chipshare_at_start'] += s0; hu['hands'] += len(huh)
        hu['capped'] += (len([1 for v in end.values() if v]) > 1)
print('players_remaining: hands, net bb/hand, our avg bb, field avg bb, vpip, fold-first')
for n in sorted(byn):
    c = byn[n]; k = c['hands']
    print(' %d: %5d  %6.2f  %6.1f %6.1f  %.2f %.2f' % (n, k, c['net'] / k, c['stack_bb'] / k, c['avg_bb_all'] / k, c['vpip'] / k, c['fold_first'] / k))
print('HU:', dict(hu), 'win rate', hu['won'] / max(1, hu['reached'] - hu['capped']), 'avg start share', hu['chipshare_at_start'] / max(1, hu['reached']))
