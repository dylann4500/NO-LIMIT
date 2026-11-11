"""Offline counterfactual folds on supplied histories; never a runtime dependency."""
import analyze_round as ar
import importlib.util,pickle,json,collections,sys,time
spec=importlib.util.spec_from_file_location('revised_policy',str(ar.ROOT/'agent.py'));new=importlib.util.module_from_spec(spec);spec.loader.exec_module(new)
records=pickle.load(open(ar.ROOT/'results'/'snapshots.pkl','rb'))
changes=collections.defaultdict(lambda:collections.Counter());timings=[];examples=[];seen=set();seed=7
cal=collections.defaultdict(lambda:[0,0.,0.,0.,0.])
for rec in records:
 s=rec['state'];meta=rec['meta'];m=pickle.loads(rec['memory']);m['seq']-=1;mem=pickle.dumps(m,protocol=4);s.events=[]
 t=time.thread_time_ns();act,ret=new.Agent()._act(s,mem);timings.append((time.thread_time_ns()-t)/1000)
 k=act.kind.value;street=len(s.board)-2 if s.board else 0
 if k!=meta['actual']:
  label=f'{street}_{meta["actual"]}_to_{k}';g=changes[label];g['decisions']+=1
  # Only first divergence in a hand can have a meaningful standalone effect.
  hand=(meta['table'],meta['hand'])
  if hand not in seen and meta['actual'] in ('call','raise') and k=='fold':
   save=(s.seats[s.seat].stack-meta['end'])/s.blinds[1]
   g['fold_vs_actual_saved_bb']+=save;g['hands']+=1
   g['good_folds']+=save>0
   if abs(save)>15:examples.append((save,s.cards,s.board,s.to_call,meta['actual'],meta['net'],meta['table'],meta['hand']))
  seen.add(hand)
 # Compare range equity using revealed opponent cards. This set is selected by
 # reaching showdown and must not be treated as an unbiased whole-field score.
 opps=[x for x in s.seats if x.seat!=s.seat and x.status in ('active','all_in')]
 if s.board and s.to_call and opps:
  mm=new.update(s,mem);hh=mm['hand'];stats=mm['stats'];hi=[new.CARD_INDEX[c] for c in s.cards]
  eq,q,d,w,cat,ag=new.equity(s,hh,opps,stats,hi,s.hand_number*923+s.seat)
  if ag.seat in meta['shows']:
   cards=[new.CARDS[i] for i in hi];vs=[new.eval7.Card(c) for c in meta['shows'][ag.seat]];bd=[new.eval7.Card(c) for c in s.board]
   truth=new.eval7.py_hand_vs_range_exact(cards,[(vs,1.)],bd) if len(bd)==5 else new.eval7.py_hand_vs_range_monte_carlo(cards,[(vs,1.)],bd,2000)
   oe,oq,od,ow,oc,oa=ar.policy.equity(s,hh,opps,stats,hi,s.hand_number*923+s.seat)
   key=f'{street}_{meta["actual"]}';g=cal[key];g[0]+=1;g[1]+=oe;g[2]+=eq;g[3]+=truth;g[4]+=s.to_call*(eq-truth)
result={'changed_actions':dict(changes),'shown_equity':{k:{'n':v[0],'old':v[1]/v[0],'new':v[2]/v[0],'truth':v[3]/v[0],'weighted_error_chips':v[4]} for k,v in cal.items()},'cpu_us':{'p50':sorted(timings)[len(timings)//2],'p99':sorted(timings)[int(.99*len(timings))],'max':max(timings)},'large_fold_examples':sorted(examples,reverse=True)}
print(json.dumps(result,indent=2))
