import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
F = collections.defaultdict(lambda: [0, 0])
OR = collections.defaultdict(lambda: [0, 0])  # open raise freq by table size (first-in)
for h in H:
    n = len([v for v in h['stacks'].values() if v]); grp = 'HU' if n == 2 else '3h' if n == 3 else '4-5' if n <= 5 else '6-8'
    street = 0; cur = 0; bets = collections.Counter(); pot = 0; opened = False
    for e in h['events']:
        k, s, a, c = e
        if k in ('blind', 'ante'): pot += a; bets[s] += a; cur = max(cur, bets[s])
        if k == 'board': street += 1; cur = 0; bets = collections.Counter()
        if s is None or k not in ('fold', 'check', 'call', 'raise'): continue
        if street == 0 and not opened and s != h['seat']:
            OR[grp][0] += 1; OR[grp][1] += k == 'raise'
        if street == 0 and k == 'raise': opened = True
        facing = cur - bets[s]
        if street > 0 and facing > 0 and s != h['seat']:
            F[grp][0] += 1; F[grp][1] += k == 'fold'
        if k == 'call': bets[s] += a; pot += a
        if k == 'raise': pot += a - bets[s]; bets[s] = a; cur = max(cur, a)
print('opp fold-to-postflop-bet by table size:', {g: (v[0], round(v[1] / v[0], 2)) for g, v in F.items()})
print('opp first-in raise freq by table size:', {g: (v[0], round(v[1] / v[0], 2)) for g, v in OR.items()})
