import gzip, json, sys, collections
P = sys.argv[1]
H = [json.loads(l) for l in gzip.open(P, 'rt')]
tables = collections.defaultdict(list)
for h in H: tables[h['table']].append(h)
print('hands', len(H), 'tables', len(tables))
# blinds schedule
bl = {}
for h in H: bl.setdefault(h['hand'], tuple(h['blinds']))
print('blinds by hand', [(k, bl[k]) for k in sorted(bl) if k % 20 == 1][:16])
last = [max(x['hand'] for x in t) for t in tables.values()]
print('last hand seen per table: mean', sum(last)/len(last), 'max', max(last), 'hist', collections.Counter(min(l//25*25, 250) for l in last))
# our stack trajectory relative to start
traj = collections.defaultdict(list)
for t in tables.values():
    for h in t:
        s = h['stacks'].get(str(h['seat']))
        traj[h['hand'] // 25 * 25].append(s)
print('our avg stack by hand bucket', [(k, round(sum(v)/len(v)), len(v)) for k, v in sorted(traj.items())])
