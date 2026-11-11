"""Offline preflop equity generation. Run once; never used during a decision."""
import itertools
import json
from pathlib import Path
import eval7

RANKS = '23456789TJQKA'
DECK = [eval7.Card(r+s) for r in RANKS for s in 'cdhs']

def key(a, b):
    x, y = sorted((a.rank, b.rank), reverse=True)
    return RANKS[x]+RANKS[y]+('' if x == y else 's' if a.suit == b.suit else 'o')

def main():
    combos = [(c, 1.0) for c in itertools.combinations(DECK, 2)]
    representatives = {}
    for (a,b), _ in combos:
        representatives[key(a,b)] = [a,b]
    strength = {k: float(eval7.py_hand_vs_range_monte_carlo(h, combos, [], 40000))
                for k,h in representatives.items()}
    ordered = sorted(combos, key=lambda v: strength[key(*v[0])], reverse=True)
    tiers = [.015, .03, .05, .10, .17, .27, .42, .65, 1.0]
    tight = {'0.015':'QQ+,AKs', '0.03':'JJ+,AKs,AKo', '0.05':'99+,AQs+,AQo+'}
    ranges = [eval7.HandRange(tight[str(p)]).hands if str(p) in tight else
              ordered[:round(len(ordered)*p)] for p in tiers]
    eq = {k: [round(float(eval7.py_hand_vs_range_monte_carlo(h, r, [], 24000)), 5)
              for r in ranges] for k,h in representatives.items()}
    out = {'tiers': tiers, 'strength': strength, 'equity': eq, 'tight_ranges': tight}
    Path(__file__).with_name('preflop.json').write_text(json.dumps(out, separators=(',', ':')))
    print('Generated',len(eq),'hands;',len(ordered),'combos')

if __name__ == '__main__':
    main()
