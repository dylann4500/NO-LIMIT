import analyze_round as ar
import pickle,collections,json
R=ar.ROOT
records=pickle.load(open(R/'results'/'snapshots.pkl','rb'))
g=collections.defaultdict(lambda:[0,0.,0.,0.]);big=[];folds=collections.defaultdict(collections.Counter)
for r in records:
 s=r['state'];meta=r['meta'];h=pickle.loads(r['memory'])['hand'];me=s.seats[s.seat];bb=s.blinds[1];cost=s.to_call
 prior=[e for e in s.history if e.seat==s.seat and e.kind in ('fold','call','raise','check')]
 if not s.board and not prior:
  k=ar.policy.hand_key(*(ar.policy.CARD_INDEX[c] for c in s.cards));pct=ar.policy.PERCENTILE[k];typ='pair' if len(k)==2 else k[-1];pos=ar.policy.seat_position(s,s.seat)
  if meta['actual']=='call':
   bbpos='bb' if pos==s.players_remaining-1 else 'sb' if pos==s.players_remaining-2 else 'ip'
   bins=['all',f'type_{typ}',f'pos_{bbpos}',f'n_{s.players_remaining}',f'pct_{int(pct*10)}',f'size_{int(cost/bb)}']
   sunk=h['contrib'].get(s.seat,0)
   inc=(meta['net']+sunk)/bb
   for key in bins:
    row=g[key];row[0]+=1;row[1]+=meta['net']/bb;row[2]+=inc;row[3]+=cost/bb
   big.append((inc,k,cost/bb,meta['net']/bb,meta['table'],meta['hand']))
 # Opponent folding response against our bets; and actual range fraction by action.
 if s.board and meta['actual']=='raise':
  pass
print(json.dumps({k:{'n':v[0],'net_bb':round(v[1],1),'incremental_bb':round(v[2],1),'call_cost_bb':round(v[3],1)} for k,v in g.items()},indent=2))
print('worst',sorted(big)[:30])
