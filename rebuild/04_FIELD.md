# 04 · What the field does, and what beats it

Measured over 56 AI-built bots: Claude and Codex teams building "the strongest bot", three generations improving from their own hand histories, plus mock rounds of up to 8,000 tables.

## The field converges
- **Same model, same design.** Most bots from the same frontier model build almost the same thing:
  - ICM push/fold at about 8-17 bb
  - eval7 Monte Carlo against ranges narrowed by betting
  - fold-rate-based c-betting and bluffing
  - per-seat stats in memory
- **OpenAI-written bots scored below Claude-written ones** in every round: 8-12.5 against 13-18 points per table.

## Habits we measured (exploit these)
- **Postflop bets get folded to 50-70% of the time:** about 49% against small bets, 65% against medium and 76% against big. Bets when checked to won 81-96% of the time. **Bet more** as long as the opponent folds.
- **Big turn and river bets and raises are almost always real:** 59-100% two pair or better, and only 1-7% air. **Calling down a raise with one pair was the single biggest leak** in every team's histories. Fold one pair to raises and big late bets unless that player raises a lot.
- **Shoves are wide:** open-shoves and re-jams were about 40-60% of hands at ≤20 bb, and about 85% deeper, from shown hands. Most bots (and our starting assumptions) used 10-25%. **Call shoves wider,** scaled by the shover's observed rate.
- **Our shoves get through:** opponents folded to our re-shoves 83-91% of the time, and re-shoves won +1.5 to +3 bb each, even with weak hands.
- **3-bets fold out:** openers folded 75-80% to 3-bets. Light 3-bets won about +2-3 bb each.
- **Heads-up and short-handed they open much wider:** raise-first-in was about 26% at 6-8 players, 37% at 4-5, 54% three-handed and 71% heads-up. **Track open rates separately by table size,** or heads-up raises look tight and you fold the big blind too much.
- **Preflop flat calls of raises lost money** at most stack depths: re-raise or fold instead, except cheap big-blind defence.

## What the field learns between rounds (plan for T4-T6)
- **Generation 1:** over-folded and used textbook ranges, so a tight bot gets run over. Our first bot was too tight (opened small, folded 95% to 3-bets, c-bet 25%, folded the big blind 86% of the time to steals) and finished last.
- **Generation 2:** found the over-folding and the "big bets are strong" pattern. It bets and bluffs more, calls down less and calls shoves wider. **A bot that stood still fell from 1st to 5th.**
- **Generation 3:** tightened opens (it gets re-raised 40-50% of the time now), re-jams wider, and stops bluffs that risk the tournament.

## The best design depends on the blind schedule
In 3,000- to 8,000-table leagues against the latest field:
- **Slower blinds:** the equity/ICM design in `03_STRATEGY.md` won or tied.
- **Faster blinds** (more levels, reaching 1000/2000 by hand about 240): a more exploitative variant was about +1 point. It has richer per-seat stats, narrower postflop raise ranges, deep all-ins read as about the top 6%, and 4-bets only with JJ+/AK.
- **Decide once the kit gives the real schedule,** by running both against your field.

## Things that didn't help
- **Tuning thresholds against hand-written opponents.** That overfits; tuned bots lost 2-12 points on realistic fields.
- **Hardening against "exploiter" bots** trained against us. It cost 4-9 points elsewhere.
- **Tuning the strong design's 17 numeric constants.** No measurable gain. Gains come from strategy changes driven by real hand histories.
