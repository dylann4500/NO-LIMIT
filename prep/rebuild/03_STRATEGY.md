# 03 · Strategy spec (the design that won our simulations)

An equity + ICM + opponent-model bot. Numbers are the tuned values; treat them as starting points.

## Building blocks
- **Hand classes:** 169 in hold'em (pairs, suited, offsuit). Each class has a strength percentile `pct`: the fraction of starting hands at least as strong, by equity against a blend of random and top-15% ranges.
- **`eq_pre(class, w)`:** precomputed equity of a class against the top-w range, for w in {0.04, 0.07, 0.10, 0.14, 0.19, 0.25, 0.32, 0.40, 0.50, 0.62, 0.78, 1.0}, interpolated between grid points.
- **Utility of a final stack distribution:** a blend of ICM equity and chip share, `λ·ICM + (1-λ)·(payout_sum · my_share)`.
  - λ = 1 with ≤4 players left, 0.8 with 5, 0.65 with 6, and 0.5 with 7-8.
  - Compute ICM exactly with a recursive Malmgren-Harville over the payouts; it's fast for 3 paid places.
- **Opponent stats per seat,** kept in memory, are all shrunk toward a prior with weight about 6:
  - VPIP, open-raise rate, 3-bet rate, calls against all-ins
  - fold to postflop bets (prior 0.48), bet frequency when checked to (prior 0.40), raise frequency facing bets (prior 0.06)
  - folds to raises and to 3-bets
  - Count a hand's actions only after the hand ends, or a raise widens its own range mid-hand.

## Opponent range model (preflop)
- **An opener's range** is their observed open rate × a seat factor POSF by the number of seats between them and the big blind. That's {0 or 1 seats: 2.0, 2: 1.5, 3: 1.2, 4: 1.0, 5: 0.85, 6: 0.75, 7: 0.7}.
- **A 3-bettor's range** is their observed 3-bet rate. A 4-bettor gets their 3-bet range × 0.55, unless they 3-bet more than 40% of the time.
- **A shover's range** is at least `shove_width(bb)` × the seat factor. `shove_width` interpolates (bb, width): (1.5, 0.85), (3, 0.60), (5, 0.42), (8, 0.30), (10, 0.24), (13, 0.18), (16, 0.13), (20, 0.09), (30, 0.05), and 0.04 above.
  - **The real field shoves much wider:** about 40-60% at ≤20 bb (see `04_FIELD.md`). Widen these, scaled by each shover's observed rate.
- **Callers:** VPIP (×1.3 + 0.1 if they limped).

## Preflop: unopened pot
- **Effective stack** is min(ours, the biggest other stack), in big blinds.
- **Push/fold zone:** at ≤14 bb, or ≤18 bb when there are no limpers and at most 2 players behind. Compare the utility of shoving against folding:
  - Walk the players left to act. For each, estimate the chance they call: the fraction of hands with enough equity against our perceived range at their pot odds (+0.03 on the bubble), divided by their range width and blended with their observed calls against all-ins.
  - Then score win and lose against their calling range, plus everyone folding (we win the pot).
  - Our perceived range is `shove_width(bb)` × {1 behind: 2.2, 2: 1.5, 3: 1.2}.
  - Shove if U(shove) > U(fold); otherwise check if free, else fold.
- **Big blind option:** raise to (3.5 + limpers) bb with pct ≤ 0.12 when there are limpers (≤ 0.30 when not), otherwise check.
- **Open range by players left behind:** {1: 0.50, 2: 0.42, 3: 0.30, 4: 0.23, 5: 0.19, 6: 0.16, 7: 0.14}.
  - Steal adjustment: multiply by (0.75 + 0.6 · P(all behind fold)), and if that probability is above 0.55 with ≤3 behind, open at least that wide.
  - With limpers: raise to (3 + limpers) bb with pct ≤ 0.55·w, or limp along with pct ≤ min(0.45, 1.1·w) when deep (>25 bb), otherwise fold.
- **Open size:** 2.2 bb with ≥3 behind, 2.5 with 2, 3.0 with 1, and 2.1 when under 25 bb. The small blind can complete heads-up against the big blind with pct ≤ 0.62 when deep.

## Preflop: facing a raise
- **Equity:** e = eq_pre(class, villain width). With extra players in the pot, raise it to the power (1 + 0.7·others).
- **Committed** means to_call ≥ 40% of our stack, the villain is all-in, or eff ≤ 25 bb:
  - **Villain all-in or no raise allowed:** call if U(call) > U(fold), using exact ICM heads-up.
  - **Otherwise:** compare re-shoving (allin_ev, our perceived width shove_width·0.7) against folding. Flat only if to_call < 25% of our stack and 0.85·e ≥ pot odds with pct ≤ 0.5.
- **Deep:**
  - **Value re-raise** when e ≥ 0.57 + 0.03·(raises − 1) and e ≥ 0.5: to 3.0× (in position) or 3.5× the raise, plus 1 bb per caller. Go all-in if that's over 35% of our stack.
  - **Light 3-bet:** with one raise, no others in, deep (>40 bb), pct in (0.08, 0.22), and an opener who folds to raises more than 55% of the time, 3-bet to 3.2× the raise 35% of the time. The field folds to 3-bets about 75-80%, so this can go higher (see `04_FIELD.md`).
  - **Call** when e × R ≥ pot odds and pct ≤ 0.5, where R = (0.86 in position / 0.72 out) − 0.04 per player behind, +0.07 for a pair or suited hand with ≥15× implied odds.

## Postflop
- **Main villain:** the last raiser this street; otherwise the preflop aggressor; otherwise the tightest remaining opponent.
- **Villain range:** start from their preflop width, then **narrow by their actions this hand** (keep fraction `keep`):
  - Each bet multiplies keep by min(1, ka × size_k × street_k).
    - ka = clamp(1.15·betfreq + 0.1, 0.25, 1).
    - size_k is 1.0 for bets under 0.45 pot, 0.8 under 0.8, 0.6 under 1.5, and 0.5 above.
    - street_k is {flop 1.0, turn 0.88, river 0.78}.
  - Each raise multiplies keep by clamp(1.3·raisefreq + 0.05, 0.08, 1) × street_k.
  - Each call multiplies keep by clamp(1 − fold_to_bet + 0.1, 0.35, 1).
  - keep ≥ 0.06.
  - Implementation: sort the sampled range by hand strength on this board, keep the top `keep` fraction, and add back every 6th hand of the rest as bluffs and draws (every 25th after a big bet or a raise from a non-maniac).
- **Equity:** Monte Carlo against that range, sampling about 110 hands and running 380 iterations. Use 60/200 when the time bank is below 30 ms, and 50/150 if 0.35 ms have already gone. Multiway, raise it to the power (1 + 0.75·(opponents − 1)).
- **Facing a bet:**
  - **Committed** (to_call ≥ 40% of our stack, or the remaining stack is under 30% of the pot after calling): heads-up, use the exact ICM call EV; multiway, need e ≥ odds + 0.03. If it's good and e ≥ 0.6, shove.
  - **Raise for value** when e ≥ 0.84 on the river (0.78 earlier) + 0.05 per extra opponent, to call + 0.85·pot; all-in if that's over 55% of our stack.
  - **Call** when e × R ≥ odds + margin, where R is 1.0 on the river and 0.9 earlier, and the margin 0.02 and 0.03.
- **Not facing a bet:** pick check or a bet size by EV.
  - F = ∏ each opponent's fold-to-bet rate. As preflop aggressor on the flop, F × 1.12 (cap 0.97).
  - Check EV = e × R × pot, where R is 0.92 with nobody left to act after us and 0.82 otherwise.
  - Bet sizes are 0.33, 0.5, 0.75 and 1.0 pot. **Pot-sized bets are for value only** (e ≥ 0.55).
  - For each size, F_b = min(0.97, F × (0.85 + 0.45·min(1, B/pot))). The equity when called is e^(1 + F_b + 0.5·min(1.5, B/pot)). EV = F_b·pot + (1 − F_b)·(e_called·(pot + 2B) − B).
  - Take the best if it beats checking by more than 0.01·pot. Shove when the stack is ≤1.3·pot and e ≥ 0.7.

## Discard or other extra phases
Pick the discard that maximises equity of the remaining hand against a range (enumerate the options, deadline about 0.3 ms). That beat "drop the lowest card" by 2 equity points per hand in MIT's 2026 rules (discards go face up to the board; showdown is the best 5 of 2 + board).
