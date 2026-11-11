import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
def net(h):
    me = h['seat']; s0 = h['stacks'].get(str(me)) or 0
    s1 = None
    for e in h['events']:
        if e[0] == 'stack' and e[1] == me: s1 = e[2]
    return s0, (s1 if s1 is not None else s0) - s0
RANK = '23456789TJQKA'
def cls(c):
    a, b = c
    ra, rb = sorted([a[0], b[0]], key=RANK.index, reverse=True)
    return ra + rb if ra == rb else ra + rb + ('s' if a[1] == b[1] else 'o')
cat = collections.defaultdict(lambda: [0, 0, 0])
by_level = collections.defaultdict(lambda: [0, 0])
vp = collections.Counter(); n = 0
sd = [0, 0, 0]
for h in H:
    s0, d = net(h)
    if s0 <= 0: continue
    me = h['seat']; bb = h['blinds'][1]
    ev = h['events']
    pre = []; street = 0; saw = False; showed = False; allin = False
    for e in ev:
        if e[0] == 'board': street += 1
        if e[1] == me and e[0] in ('fold', 'check', 'call', 'raise'):
            pre.append((street, e[0], e[2]))
        if e[0] == 'show' and e[1] == me: showed = True
    pf = ''.join(a[1][0] for a in pre if a[0] == 0)
    post = ''.join(a[1][0] for a in pre if a[0] > 0)
    key = (pf[:3], 'post' if post else '-', 'SD' if showed else '')
    c = cat[key]; c[0] += 1; c[1] += d / bb; c[2] += d
    by_level[h['blinds'][1]][0] += d; by_level[h['blinds'][1]][1] += 1
    n += 1
    if 'c' in pf or 'r' in pf: vp['vpip'] += 1
    if 'r' in pf: vp['pfr'] += 1
print('hands', n, 'VPIP %.3f PFR %.3f' % (vp['vpip'] / n, vp['pfr'] / n))
print('net by blind level (chips total, hands):', sorted((k, v[0], v[1]) for k, v in by_level.items()))
for k, v in sorted(cat.items(), key=lambda x: x[1][2]):
    if v[0] >= 30: print('%-28s n=%5d  bb/hand %7.2f  total chips %8d' % (k, v[0], v[1] / v[0], v[2]))
