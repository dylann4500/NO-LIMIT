"""Analyze supplied public hand histories, without simulator access."""
import gzip,json,collections,os
ROOT=os.path.dirname(__file__)
HISTORY=os.path.join(ROOT,'../openai_a_default_1/round1/hand_history.jsonl.gz')
HANDS=[json.loads(x) for x in gzip.open(HISTORY,'rt')]

def analyze():
    bins=collections.defaultdict(lambda:collections.Counter())
    field=collections.defaultdict(lambda:collections.Counter())
    losses=[];wins=[]; examples=[]
    for h in HANDS:
        hero=h['seat'];n=len(h['stacks']);bb=h['blinds'][1]
        street=0;board=[];bets=collections.defaultdict(int);pot=0;contrib=collections.defaultdict(int)
        acts=collections.defaultdict(list);reveals={}; pfraises=[];prevraise=None;hero_fold=None;allin_street=None
        snap=[]
        for k,s,amount,cards in h['events']:
            if k=='board':board+=cards;street=len(board);bets=collections.defaultdict(int);prevraise=None
            if k in ('blind','ante','call','raise'):
                add=amount-bets[s] if k=='raise' else amount
                pot+=add;contrib[s]+=add
                if k!='ante':bets[s]+=add
                if contrib[s]>=h['stacks'].get(str(s),0) and s==hero:allin_street=street
            if k=='show':reveals[s]=cards
            if k in ('raise','call','check','fold'):
                acts[s].append((street,k,amount))
                f=field[h['names'][str(s)]];f['a'+str(street)+k]+=1
                if street==0 and k=='raise':pfraises.append(s)
                if s==hero:
                    snap.append((street,k,amount,pot,prevraise))
                    if k=='fold':hero_fold=street
                if k=='raise':prevraise=s
        if h['hole'] is None:continue
        end=next(e[2] for e in h['events'] if e[0]=='stack' and e[1]==hero)
        delta=end-h['stacks'][str(hero)]
        hs=acts[hero]
        vp=any(st==0 and k in ('call','raise') for st,k,_ in hs)
        pr=any(st==0 and k=='raise' for st,k,_ in hs)
        groups=['all','players_'+str(n),'vpip_'+str(vp),'pfr_'+str(pr),'fold_'+str(hero_fold),'allin_'+str(allin_street),'show_'+str(hero in reveals)]
        if n==2:groups+=['hu_button_'+str(h['button']==hero)]
        if pr:groups+=['pfr_players_'+str(n)]
        for group in groups:
            b=bins[group];b['hands']+=1;b['chips']+=delta;b['bb']+=delta/bb;b['vpip']+=vp;b['pfr']+=pr;b['shows']+=hero in reveals
        record={'table':h['table'],'hand':h['hand'],'n':n,'hole':h['hole'],'board':board,'delta':delta,'bb':delta/bb,'actions':snap,'reveals':reveals,'names':h['names'],'stacks':h['stacks']}
        if delta<0:losses.append(record)
        if delta>0:wins.append(record)
        # Collect action frequencies for every seat, stratified by live table size.
        for s,aa in acts.items():
            name=h['names'][str(s)];f=field[(name,n)]
            f['hands']+=1;f['vpip']+=any(st==0 and k in ('raise','call') for st,k,_ in aa);f['pfr']+=any(st==0 and k=='raise' for st,k,_ in aa)
            f['bb']+=(next(e[2] for e in h['events'] if e[0]=='stack' and e[1]==s)-h['stacks'][str(s)])/bb
    report={'groups':dict(bins),'field':{str(k):v for k,v in field.items()},'big_losses':sorted(losses,key=lambda x:x['bb'])[:60],'big_wins':sorted(wins,key=lambda x:-x['bb'])[:30]}
    with open(os.path.join(ROOT,'history_analysis.json'),'w') as f:json.dump(report,f,indent=2)
    print(json.dumps(report['groups'],indent=1))
    print('FIELD HU')
    for k,v in field.items():
        if isinstance(k,tuple) and k[1]==2:print(k,dict(v))
    print('LOSSES')
    for h in report['big_losses'][:20]:print(json.dumps(h))
if __name__=='__main__':analyze()
