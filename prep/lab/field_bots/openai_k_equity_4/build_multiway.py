"""Offline correlation calibration against genuinely ranged multiway opponents."""
import json
import random
import time
from pathlib import Path
import eval7
from build_tables import CARDS, key


def main():
    path=Path(__file__).with_name('equity.json')
    data=json.loads(path.read_text())
    groups={}
    combos=[]
    for i,c in enumerate(CARDS):
        for j in range(i):
            k=key(str(c),str(CARDS[j]))
            meta=(i,j,(1<<i)|(1<<j),(c,CARDS[j]),k)
            combos.append(meta);groups.setdefault(k,meta)
    rng=random.Random(414017)
    trials=4000
    out={}
    start=time.perf_counter()
    for width in [.05,.18,.5]:
        pool=[c for c in combos if data['percentile'][c[4]]<=width]
        result={}
        for k,hero in groups.items():
            source=[c for c in pool if not c[2]&hero[2]]
            sums=[0.]*6
            counts=[0]*6
            while min(counts)<trials:
                used=hero[2];villains=[]
                for j in range(7):
                    candidate=None
                    for attempt in range(40):
                        c=source[rng.randrange(len(source))]
                        if not c[2]&used:candidate=c;break
                    if candidate is None:
                        valid=[c for c in source if not c[2]&used]
                        if not valid:break
                        candidate=valid[rng.randrange(len(valid))]
                    used|=candidate[2];villains.append(candidate[3])
                    n=j+1
                    if n<2 or counts[n-2]>=trials:continue
                    # Each opponent count gets its own runout. Future sampled
                    # players must not condition a smaller field's board/ranges.
                    occupied=used;board=[]
                    while len(board)<5:
                        i=rng.randrange(52)
                        if occupied&(1<<i):continue
                        occupied|=1<<i;board.append(CARDS[i])
                    board=tuple(board)
                    hv=eval7.evaluate(hero[3]+board);ties=1
                    for v in villains:
                        score=eval7.evaluate(v+board)
                        if score>hv:break
                        if score==hv:ties+=1
                    else:sums[n-2]+=1/ties
                    counts[n-2]+=1
            wi=data['widths'].index(width)
            result[k]=[data['equity'][k][wi]]+[round(v/trials,6) for v in sums]
        out[str(width)]=result
        print('Built width',width,'elapsed',round(time.perf_counter()-start,1),flush=True)
    data['multiway_ranges']=out
    path.write_text(json.dumps(data,separators=(',',':')))
    print('Updated',path,'in',round(time.perf_counter()-start,1),'seconds',flush=True)


if __name__=='__main__':main()
