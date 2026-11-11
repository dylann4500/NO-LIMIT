"""Sampling accuracy against exhaustive river equity; uses no simulator internals."""
import json,math,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"fake_sdk"))
import agent as bot
import eval7
rng=random.Random(66829)
errors=[]
for j in range(1600):
 cards=rng.sample(list(bot.CARDS),7)
 hole=[bot.CARDS[c] for c in cards[:2]]
 board=[bot.CARDS[c] for c in cards[2:]]
 mask=sum(1<<bot.CID[c] for c in cards)
 i=j%7
 width=bot.TIERS[i]
 text=bot.DATA.get('tight_ranges',{}).get(str(width))
 full=eval7.HandRange(text).hands if text else [(list(c),1.0) for c in bot.COMBOS[:max(16,round(1326*width))]]
 true=float(eval7.py_hand_vs_range_exact(hole,full,board))
 predicted=bot.post_equity(hole,board,mask,width,[0]*14,False,0,0)
 errors.append(abs(true-predicted))
errors.sort()
print(json.dumps({"samples":bot.P["samples"],"rivers":len(errors),"mae":sum(errors)/len(errors),"p95_absolute_error":errors[int(len(errors)*.95)],"max_absolute_error":max(errors)}))
