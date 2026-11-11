"""Round 1 public-history analysis; no simulator imports."""
import collections as C
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HANDS = [json.loads(x) for x in gzip.open(ROOT.parent/'openai_a_default_2/round1/hand_history.jsonl.gz','rt')]

def analyze():
    groups=C.defaultdict(lambda:[0,0,0,0])
    field=C.defaultdict(C.Counter)
    losses=[];wins=[];shown=[]
    for h in HANDS:
        seat=h['seat'];n=sum(v>0 for v in h['stacks'].values());bb=h['blinds'][1]
        end={s:a for k,s,a,c in h['events'] if k=='stack'}
        present=seat in end
        delta=end.get(seat,0)-h['stacks'].get(str(seat),0)
        board=[];bets=C.Counter();con=C.Counter();actions=[];pfr=[]
        street=0;raises=0;participated=set();pre_raises=set();foldstreet=None;allinstreet=None;laststreet=0
        reveals={s:c for k,s,a,c in h['events'] if k=='show'}
        for s,v in h['stacks'].items():
            if v>0:field[h['names'][s]]['hands']+=1
        for k,s,a,c in h['events']:
            if k=='board':street+=1;board+=c;bets.clear();raises=0
            if k in ('blind','ante','call','raise'):
                add=max(0,a-bets[s]) if k=='raise' else a
                con[s]+=add
                if k!='ante':bets[s]+=add
                if k in ('call','raise'):
                    if street==0:participated.add(s)
                    if k=='raise':
                        if street==0:pre_raises.add(s);pfr.append(s)
                        else:field[h['names'][str(s)]][f'bet_s{street}']+=1
                        raises+=1
                    elif street:field[h['names'][str(s)]][f'call_s{street}']+=1
                if s==seat and k in ('call','raise') and con[s]>=h['stacks'][str(s)]:allinstreet=street
            if s==seat and k in ('fold','call','check','raise'):
                actions.append([street,k,a]);laststreet=street
                if k=='fold':foldstreet=street
            if k=='fold' and street:field[h['names'][str(s)]][f'fold_s{street}']+=1
        for s in participated:field[h['names'][str(s)]]['vpip']+=1
        for s in pre_raises:field[h['names'][str(s)]]['pfr']+=1
        if not present:continue
        labels=[f'n={n}',f'last_street={laststreet}',f'bb={bb}',f'fold={foldstreet}',f'allin={allinstreet}']
        labels+=['pre_raise' if seat in pre_raises else 'pre_call' if seat in participated else 'pre_fold/check']
        if seat in pre_raises:labels+=['pre_reraise' if pfr[0]!=seat else 'pre_open']
        for key in labels:
            g=groups[key];g[0]+=1;g[1]+=delta;g[2]+=delta/bb;g[3]+=int(end[seat]==0)
        desc=dict(table=h['table'],hand=h['hand'],n=n,bb=bb,stack=h['stacks'][str(seat)],delta=delta,hole=h['hole'],board=board,actions=actions,shows={h['names'][str(s)]:c for s,c in reveals.items()},allin=allinstreet)
        (losses if delta<0 else wins).append(desc)
        if allinstreet is not None:shown.append(desc)
    result=dict(hands=len(HANDS),tables=len(set(h['table'] for h in HANDS)),maxhand=max(h['hand'] for h in HANDS),groups=dict(sorted(groups.items())),field=field,losses=sorted(losses,key=lambda h:h['delta'])[:60],wins=sorted(wins,key=lambda h:-h['delta'])[:25],allins=shown)
    (ROOT/'validation/history_analysis.json').write_text(json.dumps(result,indent=2))
    print('HANDS',result['hands'],'TABLES',result['tables'],'MAXHAND',result['maxhand'])
    print('GROUP [hands, chips, bb, busts]')
    for k,v in result['groups'].items():print(k,[round(x,2) for x in v])
    print('FIELD')
    for name,st in sorted(field.items()):print(name,dict(st), 'vpip',round(st['vpip']/st['hands'],3),'pfr',round(st['pfr']/st['hands'],3))
    print('LOSSES')
    for h in result['losses'][:25]:print(h)

if __name__=='__main__':analyze()
