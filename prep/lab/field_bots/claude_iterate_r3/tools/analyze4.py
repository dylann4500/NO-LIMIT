import gzip, json, sys, collections, statistics
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
PCT = json.load(open('claude_iterate_r3/preflop.json'))['pct']
RANK = '23456789TJQKA'
def cls(c):
    a, b = c
    ra, rb = sorted([a[0], b[0]], key=RANK.index, reverse=True)
    return ra + rb if ra == rb else ra + rb + ('s' if a[1] == b[1] else 'o')
sh = collections.defaultdict(list)
callpct = collections.defaultdict(list)
facing_us = collections.defaultdict(lambda: [0, 0])
for h in H:
    me = h['seat']; bb = h['blinds'][1]; st = {int(k): v for k, v in h['stacks'].items()}
    shows = {e[1]: e[3] for e in h['events'] if e[0] == 'show'}
    raises = 0
    for e in h['events']:
        k, s, a, c = e
        if k == 'board': break
        if k == 'raise':
            raises += 1
            if s != me and st.get(s) and a >= 0.95 * st[s]:
                bbs = st[s] / bb
                key = ('open' if raises == 1 else 're') + ('<=12' if bbs <= 12 else '<=25' if bbs <= 25 else '>25')
                sh[key].append(PCT[cls(shows[s])] if s in shows else None)
print('opponent preflop shoves: key, count, shown, median shown pct, 75th pct')
for k, v in sorted(sh.items()):
    sv = sorted(x for x in v if x is not None)
    print('  %-10s %4d shown %4d  med %.2f  p75 %.2f' % (k, len(v), len(sv), sv[len(sv)//2] if sv else -1, sv[int(len(sv)*.75)] if sv else -1))
