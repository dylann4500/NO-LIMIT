import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
PCT = json.load(open('claude_iterate_r3/preflop.json'))['pct']
RANK = '23456789TJQKA'
def cls(c):
    a, b = c
    ra, rb = sorted([a[0], b[0]], key=RANK.index, reverse=True)
    return ra + rb if ra == rb else ra + rb + ('s' if a[1] == b[1] else 'o')
NP = int(sys.argv[2]) if len(sys.argv) > 2 else 2
cat = collections.defaultdict(lambda: [0, 0.0])
opp_open = collections.Counter(); opp_vs_open = collections.Counter()
examples = []
for h in H:
    me = h['seat']; st = {int(k): v for k, v in h['stacks'].items() if v}
    if len(st) != NP or not st.get(me): continue
    bb = h['blinds'][1]
    end = {e[1]: e[2] for e in h['events'] if e[0] == 'stack'}
    d = (end.get(me, st[me]) - st[me]) / bb
    pos = 'BTN' if h['button'] == me else 'BB' if NP == 2 else 'oth'
    acts = []; street = 0; shows = {}
    for e in h['events']:
        if e[0] == 'board': street += 1
        if e[0] == 'show': shows[e[1]] = e[3]
        if e[1] == me and e[0] in ('fold', 'call', 'raise', 'check'):
            acts.append(e[0][0] + ('' if street == 0 else str(street)))
        if e[1] != me and e[1] is not None and street == 0 and e[0] in ('fold', 'call', 'raise', 'check'):
            opp_open[(pos, e[0])] += 1
    key = (pos, ' '.join(acts[:4]))
    cat[key][0] += 1; cat[key][1] += d
    if d < -8 and len(examples) < 25:
        examples.append((pos, cls(h['hole']), round(min(st.values()) / bb, 1), [(e[0], 'me' if e[1] == me else e[1], e[2] and round(e[2] / bb, 1), e[3]) for e in h['events'] if e[0] not in ('stack', 'hand', 'blind')], {('me' if k == me else k): cls(v) for k, v in shows.items()}))
print('opp first preflop action by our position:', dict(opp_open))
for k, v in sorted(cat.items(), key=lambda x: x[1][1]):
    if v[0] >= 8: print('%-30s n=%4d  net bb %8.1f  per hand %6.2f' % (k, v[0], v[1], v[1] / v[0]))
for x in examples[:18]: print(x)
