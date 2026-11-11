import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
F = collections.Counter(); N = collections.Counter(); R = collections.Counter()
FS = collections.defaultdict(lambda: [0, 0])  # by bet size bucket
for h in H:
    street = 0; cur = 0; bets = collections.Counter(); pot = 0
    for e in h['events']:
        k, s, a, c = e
        if k in ('blind', 'ante'): pot += a; bets[s] += a; cur = max(cur, bets[s])
        if k == 'board': street += 1; cur = 0; bets = collections.Counter()
        if s is None or k not in ('fold', 'check', 'call', 'raise'): continue
        facing = cur - bets[s]
        if street > 0 and facing > 0:
            N['all'] += 1; F['all'] += k == 'fold'; R['all'] += k == 'raise'
            frac = facing / max(1, pot - facing)
            b = '<0.4' if frac < 0.4 else '<0.7' if frac < 0.7 else '<1.1' if frac < 1.1 else '>1.1'
            FS[b][0] += 1; FS[b][1] += k == 'fold'
        if k == 'call': bets[s] += a; pot += a
        if k == 'raise': pot += a - bets[s]; bets[s] = a; cur = max(cur, a)
print('postflop facing bet: n', N['all'], 'fold %.2f raise %.2f' % (F['all'] / N['all'], R['all'] / N['all']))
for b, v in sorted(FS.items()): print('  bet/pot', b, 'n', v[0], 'fold %.2f' % (v[1] / v[0]))
