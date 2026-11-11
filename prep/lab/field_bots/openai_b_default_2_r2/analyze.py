"""Analyze supplied public histories without accessing simulator implementation."""
import gzip, json, collections, os

HERE = os.path.dirname(__file__)
SOURCE = os.path.join(HERE, '../openai_b_default_2/round1/hand_history.jsonl.gz')
groups = collections.defaultdict(lambda: [0, 0, 0., 0, 0])
actions = collections.defaultdict(lambda: [0, 0., 0., 0])
opps = collections.defaultdict(lambda: collections.Counter())
losses = []
failures = 0
for line in gzip.open(SOURCE, 'rt'):
    h = json.loads(line)
    if str(h['seat']) not in h['stacks']: continue
    me = h['seat']; start = h['stacks'][str(me)]; bb = h['blinds'][1]
    bets = collections.defaultdict(int); put = collections.defaultdict(int)
    board = []; raises = 0; tag = None; first = None; hero_actions = []
    reveals = {}; win = 0; end = start; folded = False; pre_actions = []
    last_aggr = None; last_street = 0; jamstreet = None
    failures += len(h['failed'])
    for k,s,a,c in h['events']:
        if k == 'board': board += c; bets.clear(); last_aggr = None
        street = 0 if not board else len(board)-2
        if k in ('blind','ante','call','raise'):
            add = a-bets[s] if k == 'raise' else a
            pot = sum(put.values()); cost = max(bets.values(),default=0)-bets[s]
            if s == me and k in ('call','raise'):
                if not street:
                    pre_actions.append((k,a,raises,cost))
                    if tag is None: tag = 'open' if k == 'raise' and not raises else 'threebet' if k == 'raise' else 'coldcall' if raises else 'limp'
                hero_actions.append([street,k,a,add,pot,cost,list(board)])
                actions[(street,k,tag)][0] += 1
                if put[s]+add >= start: jamstreet = street
            put[s] += add
            if k != 'ante': bets[s] += add
            if k == 'raise':
                if not street: raises += 1
                last_aggr = s
        elif k == 'fold' and s == me:
            folded = True; last_street = street
            if tag is None: tag = 'fold_raised' if raises else 'fold_unopened'
            hero_actions.append([street,k,0,0,sum(put.values()),max(bets.values(),default=0)-bets[s],list(board)])
        elif k == 'check' and s == me:
            if not street and tag is None: tag = 'BB_check'
        elif k == 'show': reveals[s] = c
        elif k == 'win' and s == me: win += a
        elif k == 'stack' and s == me: end = a
    delta = end-start
    category = tag or 'none'
    for g in [('preflop',category),('end',('fold_'+str(last_street)) if folded else 'showdown' if reveals else 'uncontested'),('jam',str(jamstreet)),('players',str(len(h['stacks'])))]:
        v = groups[str(g)]; v[0]+=1;v[1]+=delta;v[2]+=delta/bb;v[3]+=int(end==0);v[4]+=int(delta>0)
    for street,k,a,add,pot,cost,b in hero_actions:
        v=actions[(street,k,category)];v[1]+=delta/bb;v[2]+=add/bb;v[3]+=int(delta<0)
    if delta < -300:
        losses.append(dict(table=h['table'],hand=h['hand'],hole=h['hole'],start=start,bb=bb,net=delta,netbb=delta/bb,tag=category,actions=hero_actions,reveals=reveals,events=h['events']))
    # Public field tendencies, normalized by observed hands for each seat.
    for sid,name in h['names'].items():
        if sid not in h['stacks']: continue
        sid=int(sid);o=opps[name];o['hands']+=1;vol=False;pr=False;st=0;bet=collections.defaultdict(int);mx=0
        for k,s,a,c in h['events']:
            if k=='board':st+=1;bet.clear();mx=0
            if k=='blind':bet[s]+=a;mx=max(mx,bet[s])
            if s!=sid: 
                if k=='raise':bet[s]=a;mx=max(mx,a)
                elif k=='call':bet[s]+=a
                continue
            if k in ('fold','call','raise','check'):
                if mx>bet[s]:o['pf_face' if st==0 else 'post_face']+=1;o['pf_fold' if st==0 else 'post_fold']+=k=='fold'
                if st==0 and k in ('call','raise'):vol=True;pr |= k=='raise'
                if st>0 and k!='fold':o['post_'+k]+=1
            if k=='raise':bet[s]=a;mx=max(mx,a)
            elif k=='call':bet[s]+=a
        o['vpip']+=vol;o['pfr']+=pr

report={'failures':failures,'groups':dict(groups),'actions':{str(k):v for k,v in actions.items()},'opponents':dict(opps),'largest_losses':sorted(losses,key=lambda x:x['net'])[:40],'largest_bb_losses':sorted(losses,key=lambda x:x['netbb'])[:40]}
with open(os.path.join(HERE,'results/history_analysis.json'),'w') as f:json.dump(report,f,indent=1)
print('GROUPS: hands, net chips, net BB, busts, wins')
for k,v in groups.items():print(k,v)
print('FIELD: name, hands, VPIP%, PFR%, post fold%, raises/calls/checks')
for name,v in opps.items():print(name,v['hands'],round(v['vpip']/v['hands']*100,1),round(v['pfr']/v['hands']*100,1),round(v['post_fold']/max(1,v['post_face'])*100,1),v['post_raise'],v['post_call'],v['post_check'])
print('LARGE LOSSES')
for x in sorted(losses,key=lambda x:x['netbb'])[:25]:print({k:v for k,v in x.items() if k!='events'})
