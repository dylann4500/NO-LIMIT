"""Offline preflop work. Only equity.json is read by the playing bot."""
import itertools
import json
import os
import time

import eval7

RANKS = '23456789TJQKA'
FRACTIONS = [.03, .055, .08, .12, .18, .25, .35, .50, .70, 1.0]
# Premiums and common opening combinations, with domination and playability taken
# into account. Raw all-in equity alone over-ranks small pairs in narrow ranges.
PREFIX = '''AA KK QQ AKs JJ AKo AQs TT AJs KQs AQo 99 ATs KJs AJo KQo
88 QJs KTs JTs 77 A9s ATo KJo QTs T9s 66 A8s K9s QJo 55 A7s Q9s
J9s KTo 98s A5s A6s 44 A4s QTo JTo T8s K8s A3s A9o 87s A2s 33
Q8s J8s A8o K7s 97s 22 T7s 76s'''.split()


def code(a, b):
    r1, r2 = sorted((a.rank, b.rank), reverse=True)
    return RANKS[r1] + RANKS[r2] + ('' if r1 == r2 else 's' if a.suit == b.suit else 'o')


def run():
    start = time.perf_counter()
    combos = list(itertools.combinations(eval7.Deck().cards, 2))
    reps = {}
    for a, b in combos:
        reps.setdefault(code(a, b), (a, b))
    full = eval7.HandRange('AA')
    full.hands = [(h, 1.0) for h in combos]
    scores = {}
    for k, h in reps.items():
        e = eval7.py_hand_vs_range_monte_carlo(list(h), full, [], 100000)
        r1, r2 = sorted((h[0].rank, h[1].rank), reverse=True)
        pair = r1 == r2
        suited = h[0].suit == h[1].suit
        gap = r1 - r2
        scores[k] = e + (0.065 * (12-r1)/12 if pair else 0) + (.027 if suited else 0) + (.012 if gap == 1 else .006 if gap == 2 else 0)
    for i, k in enumerate(PREFIX):
        scores[k] = 2 - i * .01
    combos.sort(key=lambda h: scores[code(*h)], reverse=True)
    percentiles = {}
    for i, h in enumerate(combos):
        percentiles[code(*h)] = (i+1)/1326
    result = {k: [round(percentiles[k], 6), []] for k in reps}
    for frac in FRACTIONS:
        hr = eval7.HandRange('AA')
        hr.hands = [(h, 1.0) for h in combos if percentiles[code(*h)] <= frac + .005]
        for k, h in reps.items():
            e = eval7.py_hand_vs_range_monte_carlo(list(h), hr, [], 50000)
            result[k][1].append(round(e, 5))
        print('range', frac, 'elapsed', round(time.perf_counter()-start, 1), flush=True)
    with open(os.path.join(os.path.dirname(__file__), 'equity.json'), 'w') as f:
        json.dump({'fractions': FRACTIONS, 'hands': result}, f, separators=(',', ':'))


if __name__ == '__main__':
    run()
