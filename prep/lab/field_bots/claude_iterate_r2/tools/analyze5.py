import gzip, json, sys, collections
H = [json.loads(l) for l in gzip.open(sys.argv[1], 'rt')]
T = collections.defaultdict(lambda: collections.Counter())
for h in H:
    st = {int(k): v for k, v in h['stacks'].items()}; bb = h['blinds'][1]
    names = {int(k): v for k, v in h['names'].items()}
    end = {e[1]: e[2] for e in h['events'] if e[0] == 'stack'}
    seen = set(); vp = set(); pr = set(); street = 0; post_bets = collections.Counter(); post_acts = collections.Counter()
    for e in h['events']:
        k, s, a, c = e
        if k == 'board': street += 1
        if s is None or k not in ('fold', 'check', 'call', 'raise'): continue
        if street == 0:
            seen.add(s)
            if k in ('call', 'raise'): vp.add(s)
            if k == 'raise': pr.add(s)
        else:
            post_acts[s] += 1
            if k == 'raise': post_bets[s] += 1
    for s in seen:
        t = T[names[s]]
        t['n'] += 1; t['vpip'] += s in vp; t['pfr'] += s in pr
        t['pa'] += post_acts[s]; t['pb'] += post_bets[s]
        bucket = 'deep' if st[s] / bb > 25 else 'short'
        t['net_' + bucket] += (end.get(s, st[s]) - st[s]) / bb; t['n_' + bucket] += 1
print('%-22s %6s %5s %5s %6s %8s %8s' % ('team', 'hands', 'vpip', 'pfr', 'postAgg', 'bb/h deep', 'bb/h short'))
for name, t in sorted(T.items(), key=lambda x: -(x[1]['net_deep'] + x[1]['net_short']) / x[1]['n']):
    print('%-22s %6d %5.2f %5.2f %6.2f %8.2f %8.2f' % (name, t['n'], t['vpip'] / t['n'], t['pfr'] / t['n'], t['pb'] / max(1, t['pa']), t['net_deep'] / max(1, t['n_deep']), t['net_short'] / max(1, t['n_short'])))
