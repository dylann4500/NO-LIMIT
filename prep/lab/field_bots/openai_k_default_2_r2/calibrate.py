"""Compare tempering strengths on the revealed showdown subset, not tournament scores."""
import analyze_round as ar
import importlib.util,pickle,collections,json,types
src=(ar.ROOT/'agent.py').read_text();records=pickle.load(open(ar.ROOT/'results/snapshots.pkl','rb'))
mods={}
for exponent in (0.,.35,.5,.7):
 m=types.ModuleType('calibration_'+str(exponent));m.__file__=str(ar.ROOT/'agent.py');exec(compile(src.replace('))**.70',f'))**{exponent}'),m.__file__,'exec'),m.__dict__);mods[str(exponent)]=m
out={}
for name,p in mods.items():
 g=collections.defaultdict(lambda:[0,0.,0.,0.,0.])
 for r in records:
  s=r['state'];meta=r['meta'];street=len(s.board)-3
  if street<1 or not s.to_call:continue
  s.events=[];m=p.update(s,r['memory']);h=m['hand'];stats=m['stats'];opps=[v for v in s.seats if v.seat!=s.seat and v.status in ('active','all_in')]
  if not opps:continue
  eq,q,dr,wet,cat,ag=p.equity(s,h,opps,stats,[p.CARD_INDEX[c] for c in s.cards],s.hand_number*923+s.seat)
  if ag.seat not in meta['shows']:continue
  cards=[p.eval7.Card(c) for c in s.cards];vs=[p.eval7.Card(c) for c in meta['shows'][ag.seat]];board=[p.eval7.Card(c) for c in s.board]
  truth=p.eval7.py_hand_vs_range_exact(cards,[(vs,1.)],board) if len(board)==5 else p.eval7.py_hand_vs_range_monte_carlo(cards,[(vs,1.)],board,3000)
  key=f'{street}_{meta["actual"]}';v=g[key];v[0]+=1;v[1]+=eq;v[2]+=truth;v[3]+=(eq-truth)**2;v[4]+=s.to_call*(eq-truth)
 out[name]={k:{'n':v[0],'eq':v[1]/v[0],'truth':v[2]/v[0],'rmse':(v[3]/v[0])**.5,'chip_error':v[4]} for k,v in g.items()}
print(json.dumps(out,indent=2))
