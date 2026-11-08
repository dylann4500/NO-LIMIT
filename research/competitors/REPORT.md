# Competitor study: changes for v6+
_Data: r2 (v3, 2,589 tables), r3 (v3b, 10,393), r4 (v4, 12,797) and **o1 = official round 1 (v3b, 20,165 tables)**. Scripts are in `research/competitors/scripts/`; tables are in `out/<round>/`. Every section is time-stamped, and `equity_after` is exactly Malmuth-Harville ICM (max diff 1e-4)._

**Method.** *Forward EV* is the bb a decision of ours won or lost from that point on. A fold scores 0, and check-then-fold scores at least 0, so a negative forward EV is beaten by check/fold.

## ▶ R5 v9s SANITY CHECK (first 1,000 tables, `hands-2390e159`) — 20:55
**Verdict: every v9s rule fired, and none is negative. Switch nothing off for round 6. v10 (mask only at 4-5 alive) is supported.**

Points are ICM points vs the exact fold counterfactual (folds check out at ≈ 0). R4 is the v7 baseline.

| Rule | Fired? R4 → R5 | Points in those spots (± SE) |
|---|---|---|
| HU jam widening (2 alive, 10-20 bb) | 25-50% hands: jam 26% → **63%**, fold 33% → 0%<br>50-75% hands: jam 24% → **84%**, fold 73% → 14% | jams +0.19 ± 0.18 / +0.33 ± 0.15 (fold = 0) |
| HU opens, ace or two broadway (10-40 bb) | raise 69% → **79%**, limp/fold 15% → 0% | raises +0.39 ± 0.06 |
| BB jam vs CO/BTN/SB open (5-8 alive, < 40 bb, qualifying hands) | jam 53% → **59%**, fold 18% → 3% | jams **+1.85 ± 0.18** |

- **HU jams also fire on my weakest band (75-100%):** jam 12% → 30%, at +0.31 ± 0.18. That's still not negative. The bot's percentile metric differs from mine.
- **2-3 alive all-in calls are still suppressed, as expected.**
  - Call rates: top 10% 56%, 10-25% 33%, 25-45% 11%. With the mask off in R2/R3 they were 71-74%, 51-54% and 15-19%.
  - The calls v9s does make win **+1.0 to +3.1 pts** vs folding, which confirms the cost of the bug.
- **4-5 alive mask (the part that stays): neutral to positive.** Per-decision points are 1.84 for top 10%, 0.29 for 10-25% and 0.05 for 25-45%. That is at or above R2/R3 with the mask off (0.99-1.36 / 0.16-0.20 / −0.02-0.08).

## ▶ ROUND-6 SANITY (v9s → v10) — 20:50
**ICM mask: v10 plan confirmed (mask only at 4-5 alive).** [`scripts/icmface.py`, `out/o4p/icmface.txt`]
- **Correction to §B (19:42).** My realized call-minus-fold numbers stand: they use the file's `equity_after` and a fold counterfactual where we stay alive. My *ICM-premium buckets* had the same bust = 0 bug as the SDK, so the "≥ 0.10 premium" spots at 2-3 alive were mis-bucketed. The E4 and 4-bet counterfactuals have the same flaw at 2-3 alive (too pessimistic there); most of those spots are at 6-8 alive.
- **2-3 alive: calls are good, and the mask suppressed them.**
  - With the mask off (R2, R3), heads-up all-in calls beat folding in every strength band:

    | Band | R2 | R3 |
    |---|---|---|
    | top 10% | +2.06 | +2.32 |
    | 10-25% | +0.98 | +1.12 |
    | 25-45% | +0.67 | +0.80 |
    | 45%+ | +0.30 | +0.70 |

    All SEs are ≤ 0.12.
  - Under the buggy mask (R4, v7, first 1,000 tables), call rates fell: top 10% from 71-74% to 51%, 10-25% from 51-54% to 34%, 25-45% from 15-19% to 10%. The bugged v9s is expected to look the same.
- **4-5 alive: the mask is neutral to positive. Keep it.**
  - Points per facing-all-in decision (call share × call EV; fold = 0):

    | Band | R2 (mask off) | R3 (mask off) | R4 (mask on) |
    |---|---|---|---|
    | top 10% | 0.99 | 1.36 | 1.39 |
    | 10-25% | 0.20 | 0.16 | 0.27 |
    | 25-45% | −0.02 | +0.08 | +0.17 |

  - R4 is only 1,000 tables (SE about 0.15-0.3), so this is no worse, not proven better.
- **v9s rules:** see the R5 check below.

## ▶ v9 VERDICT on 2 Curry's 3-bets: **NO RULE, NO ADDENDUM** — 20:31
- **No matched comparison is positive in 2+ rounds.**
  - Inside each of our strength bands, the 3-bet-vs-flat choice is mixed across rounds.
  - Our small 3-bets come almost entirely from top-5% hands, which we never fold (this agrees with Samuel).
  - The only consistent difference, 3-betting top-5% hands instead of flatting them, is worth about +0.05 pts/table. It's below the bar.
- **Points rule out the other candidates.** Flatting 77-99 in position at 8-6 alive loses points vs folding. Folding our 3-bets to a 4-bet is correct (counterfactual in the 20:30 section below).
- **Ship v9 on its set base:** v8b + BB jam widening vs late opens at 5-8 alive.

## ▶ v9 TASK: is 2 Curry's 3-bet game a real, copyable edge? — 20:30
Data: official rounds 1, 2 and 3 (`hands-3e3dcc02`, `547666b1`, `260d2303`; about 20k tables each, about 1,100 per team). There is no R4 official file yet. The two 148-entry 1k-table files are other tournaments, so I skipped them. Scripts: `scripts/threebet.py`, `threebet2.py`, `tbrep*.py`, `tbrange.py`; tables are in `out/o*/threebet*.txt`.

**Verdict: it's real for 2 Curry, but copying it wholesale isn't supported. No 3-bet widening rule for v9.**

| Facing one non-jam open | o1 | o2 | o3 |
|---|---|---|---|
| 2 Curry non-jam 3-bet rate | 38% | 40% | 37% |
| 2 Curry bb per 3-bet (fold = 0) | +2.06 ± 0.18 | +1.94 ± 0.15 | +2.39 ± 0.13 |
| 2 Curry points per 3-bet (fold ≈ −0.02) | +0.44 | +0.37 | +0.53 |
| Openers fold to its 3-bet / it folds to a 4-bet | 79% / 80% | 80% / 83% | 83% / 71% |
| Field bb per non-jam 3-bet | +3.18 | +3.18 | +2.93 |
| **2 Curry vs us, EV per facing-open spot (bb)** | 0.82 vs 0.80 | 0.81 vs 0.71 | 0.98 vs 0.71 |

- **The real edge over us is small and unstable:** +0.02, +0.10 and +0.27 bb per spot. At about 13 spots per table, that is 0.3 to 3.5 bb/table depending on the round.
- **2 Curry's range is wide.** Of its shown 3-bet hands (n = 370-430 per round, and showdowns skew strong), only 47-55% fall in the top 10% of two-card hands, and 14-17% come from the bottom half. Ours are 97-98% top-10%.
- **The wide part can't be copied safely.** We never 3-bet outside our top 15% (n < 30), so there's nothing to measure, and v4's card-independent 3-bets cost −19 bb/table. I don't recommend testing it in a ×6-weight round.
- **Our own top-15% hands, by strength band** (forward bb, then whole-hand points; three rounds):
  - **Top 5%:** we 3-bet 52-75% of the time. A 3-bet beats a flat in chips (+5.2 to +6.3 vs +1.5 to +3.2 bb) and in points (+0.88 to +0.90 vs +0.08 to +0.24).
    - Jams score even more points (+1.3), but they happen at shorter stacks, so this is confounded.
    - Converting the 7-14% of top-5% hands we flat to a non-jam 3-bet is worth only about +0.05 pts/table (small volume). [optional, low priority]
  - **5-10% band (77-99 class), 8-6 players in position:** we fold about 60%. Flats win chips (+0.6 to +1.2 bb) but **lose points against folding** (−0.02 vs +0.045 pts, three rounds). ICM at 8 alive makes folding right. **Don't widen flats.**
  - **15-25% band, 8-6 players in position:** we fold 77-80%. Flats score +0.06 to +0.23 pts against +0.035 for folding, but they're the bot's selected hands. [tentative, no rule]
- **Folding our 3-bets to a 4-bet is not a leak.** [20:30; `scripts/fourbet.py`, `out/o3/fourbet.txt`]
  - We fold 57-62% of our non-jam 3-bets to a 4-bet, while the calls and 5-bets we do make realize +17 to +36 bb.
  - A counterfactual on the folded top-5% hands said otherwise. It valued a 5-bet jam that is always called, ICM-priced, against the 4-bettors' shown hands. Folding came out ahead in the later rounds:

    | Stacks | o1 | o2 | o3 |
    |---|---|---|---|
    | Under 40 bb | −0.01 | −0.56 | −2.07 |
    | 40 bb or more | +0.23 | −0.80 | −1.18 |

  - The hands we continued with score +2.4 to +6.3 under the same model, so the bot's selection works.
  - The estimate is conservative: it ignores 5-bet fold equity, and the shown 4-bet hands skew strong. It's still too weak to justify a rule. **No change.**
- **Other top-two habits at 5-8 alive:**
  - Lemonade's jam-heavy facing-open play (jams 14-22%, +2.3 to +2.8 bb) matches ours (15-16%, +2.3 to +2.5 bb).
  - 2 Curry's discipline vs 4-bets (folds 71-83%) works because it 3-bets wide. Ours is a premium range.
  - Nothing else in two or more rounds is measurably worth points beyond rules already shipped.

## ▶ v8 TASK: should "thin value earns less" become a rule? — 20:03
**Verdict: no new rule for v8 (expected gain of any candidate ≈ 0 or negative).** The only turn/river value bets that lose to checking are heads-up into a visible card that pairs the board. v6’s `visible_pair_rule` already checks those on every street; I verified this in `bots/v6/agent.py`. Everywhere else, betting beats checking in both rounds. [o2 = v5r, 20,184 tables; o1 replicates; `scripts/valuebets.py`, `out/o2/valuebets.txt`]

Measure: our first-in turn/river decisions, forward bb of betting minus checking in the same cell, ± SE.

| Cell (HU) | o2: bet − check | o1 | Status |
|---|---|---|---|
| Turn, opponent's visible card **pairs**, top pair good kicker | **−7.25 ± 2.54** | −4.61 | already in v6 (one pair) |
| Turn, visible **pairs**, middle pair | **−2.98 ± 0.48** | −2.85 | already in v6 |
| Turn, visible **pairs**, no pair | **−2.98 ± 0.28** | −3.79 | already in v6 |
| River, visible **pairs**, our pair higher than theirs | bet +7.5 vs check +6.7 | +6.8 vs +7.1 | ≈ neutral. v6 checks it on every street, including the river, at ~0 cost |
| Turn, visible connects/misses, top pair weak kicker | +10.1 ± 1.1 | +13.0 | keep betting |
| River, visible connects, top pair weak kicker | **+20.4 ± 1.7** | +20.0 | keep betting |
| River, visible connects/misses, middle pair | +7.6 ± 0.5 / +6.5 ± 1.5 | +7.1 / +8.6 | keep betting |
| Turn/river, any non-pair visible card, two pair or better / overpair | +14 to +42 | similar | keep betting |

- **The example rule would lose chips.** "Check top pair with a weak kicker on the river, heads-up, when the visible card connects" would cost 20.4 ± 1.7 bb per spot (o1: 20.0), about −0.5 bb/table.
- **Why showdown income fell anyway.** The 20 fixed stations now call our bets with real hands. When they call, our showdown win rate dropped:

| Our hand | o1 → o2 win rate when they call |
|---|---|
| Middle pair | 37% → 23% |
| Top pair, weak kicker | 56% → 36% |
| Top pair, good kicker | 60% → 43% |
| Two pair or better | 64% → 47% |

  They now look like every other caller (others: 20 / 34 / 41 / 49%). That lowers the EV of both betting and checking, but not the decision between them: bet-minus-check barely moved from o1 to o2.
- **The seat model isn't lagging.**
  - The fixed stations now fold to bets 44% of the time; the prior is 0.45 and the field folds 46%.
  - Each opponent faces about 7-10 bets per table. With prior weight w = 6, the estimate covers 55-60% of the gap within a table.
  - The model tracks fold rate only, and fold rate isn't what changed. Optional: raise `fold_to_bet_prior` from 0.45 to 0.46 to match the field (negligible effect).
- **Watch item, not a rule:** heads-up turn stabs with no pair when the visible card connects or misses now beat checking (o2 +0.93 ± 0.17 / +0.58 ± 0.27). In o1 they didn't (−0.00 / −0.64). That fits the field folding more each round. Promote it only if o3 confirms.
- **Sizing:** bigger bets show higher bb in every value cell, but the bot sizes up with stronger hands and in bigger pots, so this is confounded. No sizing rule.

## ▶ FOR THE v8 BUILD (rules final at 20:25) — 19:57
**1. ⚠ E4 WITHDRAWN: do NOT widen calls of re-jams over our open** [o1; counterfactual equity, calibrated].
- **How I tested it.**
  - Each re-jammer's range is its shown hands at all-in showdowns. That sample is unbiased, because every all-in is shown (32k hands).
  - For spots we called, the predicted ICM gain matches the realized one: +3.0 predicted vs +2.5 realized for top-10% hands, and +1.6 vs +1.1 for 10-25%.
- **Spots we folded would have lost.**
  - Top-10% hands: −0.25 to −2.0 pts vs frequent re-jammers, and −1.3 to −3.2 pts vs others when stacks are over 15 bb.
  - 10-45% hands: −1.5 to −6.6 pts.
  - The only near-zero cells are ≤ 15 bb vs non-frequent jammers (+0.3), and the model's optimism wipes that out.
- **Conclusion:** the bot already picks which re-jams to call well. The earlier "+4 pts per call" figure reflected that selection, not missed value.

**2. The round-2 drop (18.10 → 16.73) is a field shift, not a bot change** [o2 full file, 20,184 tables].
- **Where it went:** our showdown result fell from +11.7 to +4.0 bb/table, while non-showdown stayed flat (+13.6 → +13.9).
- **Not from the calls v6 now folds.** Showdowns where the opponent bet last are flat: −1.45 → −1.56 bb/table.
- **The loss is in pots where we bet last and got called:**
  - postflop all-ins: +13.7 → +8.0, with 20% fewer of them
  - other showdowns: +1.9 → +0.3
- **Twenty former calling stations fixed their bots, and that accounts for −6.9 bb/table.**
  - Their fold-to-bet rose an average of +15.5 points (Hit and Run 23 → 49%, Cal Daddy 17 → 49%, Litmus 40 → 73%), and their scores rose +2.8.
  - The other teams changed −2.4 points on fold-to-bet and −0.3 on score.
- **Implication:** thin value bets now earn less. v6's fold rules are unaffected.

**3. The "new leaders" were noise from the first 1,000 tables.**

| Team | Full o2 score | o1 score |
|---|---|---|
| Golden Knight | 15.96 ± 1.11 | 15.0 |
| durrrr | 15.15 ± 1.02 | 16.4 |
| bill & ted | 17.07 ± 1.09 | 18.3 |

- **The full-file top:** sandylikesfrogs 20.4 ± 1.3, AZ 18.9, 2 Curry 18.8, Lemonade 18.7, Clippers 18.2, Team 72 18.0. We are 13th at 16.73 ± 0.29. Rank correlation from o1 to o2 is +0.83.
- **Only one rule holds across several leaders, and it's already in v6:** 6 of the top 8 fold ≥ 71% to a bettor whose visible card pairs the board (we fold 63%), and 6 of 8 fold to any bet ≥ 52% (we fold 44%).

**4. Steal widening (v7) rechecked on o2: keep it, but restrict the 45-60% band to 8-5 players left.**
- **Our own late opens with 25-45% hands still beat folding:**

| Players left | 25-45% hands | 45-60% hands |
|---|---|---|
| 8-6 | +0.84 bb (+0.13 pts) | +1.25 ± 0.70 |
| 5-4 | +0.64 | +0.79 ± 0.39 |
| 3 | +0.46 | +0.49 ± 0.40 (marginal) |

- **The cross-team gap at 8-6 has closed:** the o2 top 6 make +0.51 bb per opportunity; we make +0.50.

## ▶ User query: do teams oscillate between rounds, and can we exploit it? — 19:53
**No exploitable swing between rounds** [confirmed: 111 teams present in r2, r3, r4, o1 and o2; `scripts/oscillate.py`].

| Stat | Median round-to-round change | Direction flips | "Same as last round" error | "Swings back halfway" error |
|---|---|---|---|---|
| Preflop fold vs one raise | 2.6 pts (noise 0.3) | 59% | **3.0** | 4.8 |
| Open % of unopened pots | 3.0 (noise 0.3) | 59% | **3.3** | 7.0 |
| Flop first-in bet % | 3.5 (noise 0.9) | 56% | **4.6** | 7.7 |
| VPIP | 3.3 (noise 0.3) | 56% | **3.3** | 5.3 |
| Postflop fold to bet | 4.5 (noise 0.9) | 58% | **5.1** | 7.4 |
| Call a jam | 2.8 (noise 0.8) | 65% | **3.0** | 4.3 |

These numbers exclude r4, when our broken v4 distorted every opponent's stats; including it gives the same ranking. Errors are median absolute errors in points.

- **Teams change for real between rounds.** The changes are about 10 times the measurement noise, and they reverse a little more often than chance (56-59% flips, where 50% means no pattern).
- **But betting on a swing-back doubles the forecast error.** "Same as last round" is the best predictor for every stat. The reversals come from a few big jumps, such as bot rewrites or broken bots fixed a round later, not from a regular see-saw.
- **The field drifts instead of oscillating.** Postflop fold-to-bet rose every round (41.1 → 42.7 → 44.6 → 45.1 → 46.3%). Open % crept up (29.7 → 32.9%) and VPIP stayed flat around 27%.
- **What is exploitable:**
  1. **The drift.** Re-tune the bluff and call thresholds from each new round file.
  2. **Within a round, each bot is fixed.** Use live per-seat counts at our table, which are public, shrunk toward the field average. E4's re-jam count is one example.

## ▶ FOR THE v7 BUILD (rules final at 20:05) — 19:47
**1. ICM call mask: KEEP IT ON** [confirmed in o1 (20k tables) and r3].
- Averaged over all ≤5-alive heads-up all-in calls, v3b's calls beat folding by +0.89 ± 0.10 pts.
- That average comes from low-ICM-premium spots, where the mask is a no-op.
- Where the ICM break-even is ≥ 10 points above the chip pot odds (13% of calls), calls lose or break even:
  - postflop: −2.07 ± 0.77
  - 10–25% preflop hands: −0.10 ± 1.00
  - 4 alive with the jammer covering us: −0.74 ± 1.46
- Only top-10% hands still win there (+1.8), and the mask passes those.
- Section B has the details.

**2. Late-position steal widening: GO, scoped.** Checked on official round 1 with our own cards (`out/o1/lateopen.txt`):
- **Rule:**
  - When CO, BTN or SB is first in with ≥3 players left and ≥15 bb, open-raise 2.2–2.5 bb with every top-45% hand, plus the 45–60% band.
  - The 45–60% band means the best two of our three cards have ≥ 0.54 heads-up equity vs a random hand: any pair 33+, any ace, most kings, QJ, QT, J9s+.
  - Don't change early position, and don't change jam/short-stack play.
- **Why:** our current late opens earn more than folding (≈0) in every band, including the ones we rarely open:

  | Players left | 25–45% band: open rate → bb, pts per open | 45–60% band: open rate → bb per open |
  |---|---|---|
  | 8–6 | 34% → +1.08 bb, +0.16 pts (n=10,712) | 3% → +1.13 ± 0.63 |
  | 5–4 | 35% → +0.81 bb, +0.16 pts | 3% → +0.71 ± 0.36 |
  | 3 | 52% → +0.83 bb, +0.16 pts | 6% → +1.06 ± 0.52 |

- **Cross-team:** at 8–6 players, 5 of the 6 top teams open 43–63% from late position and earn +0.74 to +1.03 bb per opportunity. We open 32% and earn +0.57. This holds in r3, r4 and o1.
- **Expected gain:** about +0.3 pts/table, which is half the measured per-open gain to allow for selection.
- **Target:** a late open rate of 50–55% at 8–6 players (now 32%).
- **Test:** VPIP stays ≤ 32% overall, and early-position open % is unchanged.
- **Interaction:** E4 was withdrawn at 19:57. Keep our current re-jam calling.

## A. o1 ranking (19:42) [confirmed]
Our tables only. On this per-table measure we rank 9th: 18.10 ± 0.30. The official 13th probably averages over all tables.

| # | Team | o1 | r4 | r3 | Verdict |
|---|---|---|---|---|---|
| 1 | TeamBallHog | 20.4 ± 1.3 | 21.0 | 22.2 | real (z≈3.4 vs us) |
| 2 | Lemonade | 20.0 ± 1.3 | 20.3 | 18.2 | real; improved from 12.4 in r2 |
| 3 | AZ | 20.0 ± 1.2 | 22.5 | 20.4 | real |
| 4 | Team 72 | 19.4 ± 1.2 | 20.7 | 21.7 | borderline (z≈2.0) |
| 5 | WAYS-ER TEAM | 19.0 ± 1.2 | 18.9 | 15.9 | **new**; rising every round, a real bot upgrade; not separable from us |
| 7 | bill & ted | 18.3 ± 1.1 | 18.6 | 8.5 | **new bot since r4**; not separable |
| – | tuh | 15.6 ± 1.1 | | | **noise**; 18.9 was from the first 1,000 tables |

- **Team points are stable across rounds:** they correlate between rounds at r = +0.76 for r3–o1 and +0.80 for r4–o1.

## B. Should we switch off v5's ICM call mask? (19:42) [confirmed: o1 + r3]
I measured actual ICM points minus the ICM points we'd have had by folding (the jammer takes the pot). This covers our heads-up all-in calls with ≤5 alive.
- **The reviewer's numbers replicate.** All calls gain **+0.89 ± 0.10 pts** (n=20,373). By preflop strength: top 10% +1.76, 10–25% +0.56, 25–45% +0.52, weakest +0.38. Postflop all-in calls gain +0.54. r3 matches.
- **The averages don't cover the spots the mask acts on.** The mask folds only when our equity is below the ICM break-even. 61% of calls have an ICM premium (break-even minus chip pot odds) under 2 points, where v3b's own equity margin already makes the mask a no-op. Where the premium is large, the picture changes:

| ICM premium | Top 10% preflop | 10–25% preflop | Postflop |
|---|---|---|---|
| <0.02 | +1.53 | +0.70 | +1.84 |
| 0.05–0.10 | +2.24 | −0.53 ± 1.06 | +1.41 |
| ≥0.10 (13% of calls) | +1.79 | −0.10 ± 1.00 (r3 −0.28) | **−2.07 ± 0.77** (r3 −0.50) |

- **At the bubble when the jammer covers us** (4 alive, o1+r3, n=396): −0.74 ± 1.46.
- **Verdict: don't switch it off.** Where the mask can bite, calls range from roughly zero to clearly negative. Switching it off risks up to −0.15 pts/table from high-premium postflop calls. Top-10% hands win even there, and their equity normally clears the mask's threshold.

## C. Do the rules hold in o1? (19:42) [confirmed, same v3b bot]
- **Visible-pair leak replicates.** Heads-up flop, the opponent's visible card pairs the board:
  - Calling their bet with a pair higher than their visible pair loses **−7.05 bb** (n=3,638).
  - With tied pairs it loses −6.87.
  - Betting one pair loses −2.2 to −4.0 bb, while checking gains +0.4.
  - The top 8 fold 77% to such a bettor, and every one of them folds ≥63%. We fold 62%.
- **Fold rule replicates.** Calls with air lose −1.7 to −2.2 bb, and calls with middle pair −2.5 to −3.7 bb.
  - Robust totals: bet→check +2.75 and call→fold +4.42 bb/table (r3: 3.19 / 4.57).
  - Every top-8 team folds to bets ≥52% of the time; we fold 43%.
- **Heads-up air c-bets: keep them.** Into a visible card that draws or misses, betting returns +1.1 / +1.3 bb against +0.5 / +0.6 for checking.
- **Steals replicate.** At 8–6 players, from CO/BTN/SB, five of the top 6 open 43–63% and earn +0.74 to +1.03 bb per opportunity. We open 32% and earn +0.57. Lemonade almost never opens.

## D. The new leaders, and the re-jam leak (19:44)
- **Lemonade** plays limp-or-jam: it opens 12% (almost all jams) and re-raises 20% facing a raise (93% of those are jams).
  - It makes +20.1 bb/table without showdown, against +5.1 at showdown, and takes 28% of a stack per table from us.
  - **It re-jams over 20.1% of our opens**, against 1.7% for the field. AZ re-jams 9.8%, BallHog 7.0%, sandylikesfrogs 6.8%.
- **Calls of re-jams over our open** (realized ICM gain on the calls we made). **Superseded 19:57:** the counterfactual shows the spots we folded would have lost, so this is selection, not a leak:

| Our 3-card hand (best 2 cards) | vs frequent re-jammers: we call → call gains | vs others: we call → call gains |
|---|---|---|
| Top 10% (a pair 77+) | **34%** → **+4.0 ± 1.0 pts** (r3: 36% → +3.6) | 48% → +2.1 ± 0.3 |
| 10–25% (66, AJo+, A6s+, KQ, KTs) | 2% → n<20 | 14% → +1.1 ± 0.3 (r3: +1.1) |
| 25–45% (A2s+, A5o+, K7s+, KTo, QTo, JTs) | 0% | 4% → +1.3 ± 0.6 |

  - **By depth:** we call top-10% hands 60% of the time at ≤15 bb but only 24–35% deeper. Even deeper, those calls gain +1.4 to +3.3 pts.
  - We never call with 10–25% hands above 15 bb.
- **WAYS-ER TEAM** opens 51% at 2.2 bb, folds to bets 54%, bets multiway only 4–15% of the time, and wins at showdown (+38.7 bb/table, against −2.0 without).
- **bill & ted** is passive (PFR 5.5%) and folds to bets 62%, finishing 2nd/3rd 20%/15% of the time.
- **Shared by all top 8:** every team folds to bets ≥52% of the time and to a bettor whose visible card pairs the board ≥63%.

## E. Rules, ranked (19:47)
1. **Visible-pair rule (≈ +4 bb/table, ≈ +0.8 pts) [confirmed in r2, r3, o1].**
   - Applies heads-up when the opponent's visible card pairs the board and we hold one pair or air.
   - Never bet; fold to flop and turn bets.
   - Continue only with two pair or better, or a flop flush draw.
2. **Fold air and middle pair to heads-up flop and turn bets otherwise (≈ +2.4 bb) [confirmed in r3 and o1].**
   - Target fold-to-bet of 50–55%.
3. **Widen late-position steals (≈ +0.3 pts/table) [our own o1 opens + 5–6 of 6 top teams in r3, r4 and o1].** See ▶2 at the top.
4. ~~Call re-jams over our open wider~~ **WITHDRAWN 19:57.** The folds were mostly right; see ▶ FOR THE v8 BUILD, item 1.
5. **Keep v5's ICM call mask** (section B).
6. **No new multiway or general c-bet cuts.** Check turn/river air without a draw (≈ +0.7 bb) [tentative].

_Earlier (r3/r4): the AZ 49-table claims held on the full data, except "AZ loses at showdown" (it wins +14.8 bb/table there). We already bet multiway as rarely as the top teams._
