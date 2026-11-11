"""Aggregate public actions, chip flows and revealed reraising strength."""
import collections, gzip, json, os, statistics, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'fake_sdk'))
import agent

def main():
    source=os.path.join(os.path.dirname(__file__),'..','openai_k_default_1','round1','hand_history.jsonl.gz')
    counts=collections.Counter(); decisions=collections.defaultdict(collections.Counter)
    net=collections.defaultdict(collections.Counter); tables=set(); strengths=collections.defaultdict(list)
    # A fixed uniform range estimates hand-strength percentiles. Reveals are
    # selected by showdown, so these are descriptive, not unbiased range labels.
    bank=agent._BANKS[-1][:256]
    for line in gzip.open(source,'rt'):
        h=json.loads(line); tables.add(h['table']); counts['recorded_hands']+=1
        hero=h['seat']; active=h['stacks'].get(str(hero),0)>0
        counts['hero_live_hands']+=active
        street=0; bets=collections.Counter(); maximum=0; invested=collections.Counter()
        won=collections.Counter(); entered=False; raised=False; board=[]
        shown={s:c for k,s,a,c in h['events'] if k=='show'}
        for kind,seat,amount,cards in h['events']:
            if kind=='board': street+=1; board+=cards; bets.clear(); maximum=0
            if kind in ('fold','call','check','raise'):
                who='hero' if seat==hero else 'field'
                context='facing' if maximum>bets[seat] else 'free'
                decisions[f'{who}_{context}_s{street}'][kind]+=1
                if seat==hero and street==0 and kind in ('raise','call'):
                    entered=True; raised|=kind=='raise'
                if street and seat!=hero and seat in shown and kind=='raise' and maximum>0:
                    bc=[agent._CARDS[c] for c in board]
                    hc=[agent._CARDS[c] for c in shown[seat]]
                    value=agent.eval7.evaluate(bc+hc); dead=0
                    for c in bc+hc: dead|=c.mask
                    scores=[agent.eval7.evaluate(list(c[0])+bc) for c in bank if not c[1]&dead]
                    strengths[street].append(sum(v<value for v in scores)/len(scores))
            if kind in ('blind','ante','call','raise'):
                added=amount-bets[seat] if kind=='raise' else amount
                invested[seat]+=added
                if kind!='ante': bets[seat]+=added; maximum=max(maximum,bets[seat])
            if kind=='win': won[seat]+=amount
        if active:
            group='raised_preflop' if raised else 'called_preflop' if entered else 'no_voluntary_entry'
            for label in (group,'players_'+str(len(h['stacks']))):
                net[label]['hands']+=1; net[label]['chips']+=won[hero]-invested[hero]
                net[label]['big_blinds']+=(won[hero]-invested[hero])/h['blinds'][1]
    counts['tables_in_histories']=len(tables)
    reveal={s:{'n':len(v),'mean_percentile':statistics.mean(v),'median_percentile':statistics.median(v)}
            for s,v in strengths.items()}
    report={'counts':counts,'decisions':decisions,'net':net,'revealed_reraise_strength':reveal}
    path=os.path.join(os.path.dirname(__file__),'results','field_summary.json')
    with open(path,'w') as out: json.dump(report,out,indent=1)
    print(json.dumps(report,indent=1))

if __name__=='__main__': main()
