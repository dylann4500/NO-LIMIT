"""Debug: print hands where replayed stacks + wins != stacks_after."""
import gzip, json, sys
f = gzip.open(sys.argv[1], 'rt'); f.readline()
shown = 0
for line in f:
    o = json.loads(line)
    if 'hands' not in o: continue
    n = len(o['seats'])
    for h in o['hands']:
        sb, sa = h['stacks_before'], h['stacks_after']
        left = list(sb); com = [0]*n; won = [0]*n
        for e in h['events']:
            k = e['kind']; s = e.get('seat'); a = e.get('amount') or 0
            if k == 'blind': left[s] -= a; com[s] += a
            elif k == 'board': com = [0]*n
            elif k == 'call': left[s] -= a; com[s] += a
            elif k == 'raise': left[s] -= a - com[s]; com[s] = a
            elif k == 'win': won[s] += a
        bad = [i for i in range(n) if sb[i] > 0 and left[i] + won[i] != sa[i]]
        if bad:
            print('seats', bad, 'sb', sb, 'sa', sa, 'left', left, 'won', won)
            print([ (e['kind'], e.get('seat'), e.get('amount')) for e in h['events'] if e['kind'] not in ('stack','select','reveal')])
            shown += 1
            if shown >= 4: sys.exit()
