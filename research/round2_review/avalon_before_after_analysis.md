# Avalon: before-and-after hand-history analysis

## Main conclusion

The updated bot produced a much better result and fixed several concrete weaknesses. Average points increased from **14.61 to 18.88 per table**, a **4.27-point / 29.2% increase**. The most urgent remaining improvement is to make river bluff selection sensitive to opponents' exposed cards and demonstrated fold behavior. Do not revert the overall update based on isolated losing hands.

These are two different snapshots against a changing field. The comparison documents observed performance and policy changes; it does not causally attribute the entire gain to your update or establish your tournament rank.

## 1. Scope and validation

The first file identifies your entry as `avalon`, entry ID `d34060aa-5692-44c4-bff5-15d7ae072eb1`. The second identifies `avalon` with a new entry ID, `1537e79c-7f79-4551-9190-c49e8ec5b853`. The analysis matches the owner metadata, not a hard-coded ID across files.

| Item | Earlier snapshot | Updated snapshot |
|---|---:|---:|
| Tournament identifier | 5da6d631-2bcf-4fe2-9e7a-01b9e8ecac75 | af2a0969-cd0a-4124-875b-84ff690a2a6d |
| Exported table records | 1,042 | 1,031 |
| Non-filler owner tables analyzed for score | 1,000 | 1,000 |
| Filler owner appearances excluded | 42 | 31 |
| Hands while your bot had a positive starting stack, non-filler tables | 69,657 | 84,544 |
| Your betting decisions, non-filler tables | 97,680 | 104,455 |
| Your recorded flop selections | 15,655 | 13,208 |
| Owner automatic-action records, including fillers | 0 | 0 |

Every analyzed table started with eight seats and used 50/30/20 payouts. Scores come from the owner's final recorded tournament equity, which includes already awarded place points. The term “equity” in those export fields refers to ICM tournament points, not probability of winning the current poker hand.

Hand-level chip changes use authoritative `stacks_before` and `stacks_after`. Reconstructing only bet and win events initially leaves discrepancies because uncalled excess is refunded without a separate listed refund event. Accounting for those returns reconciled every non-filler hand in both datasets. No unexplained chip-accounting discrepancies remained.

Card-strength checks use a best-five-of-five/six/seven evaluator. It was checked against independent five-card-combination enumeration on 3,000 random hands. All 90 earlier guaranteed-losing calls were additionally checked with the independent evaluator. Checks use only cards available at the decision, never opponents' subsequently disclosed hidden cards.

## 2. Results improved substantially

| Metric | Earlier | Updated | Change |
|---|---:|---:|---:|
| Average points/table | 14.61 | 18.88 | +4.27 |
| First place | 19.5% | 26.6% | +7.1 percentage points |
| Top three | 38.1% | 49.0% | +10.9 points |
| Eighth place | 14.1% | 4.5% | -9.6 points |
| Bust by hand 20 | 27.8% | 6.0% | -21.8 points |
| Recorded fallback actions | 0 | 0 | No recorded failures |

Finish counts:

| Place | Earlier | Updated |
|---|---:|---:|
| 1 | 195 | 266 |
| 2 | 114 | 110 |
| 3 | 72 | 114 |
| 4 | 76 | 140 |
| 5 | 89 | 138 |
| 6 | 152 | 111 |
| 7 | 161 | 76 |
| 8 | 141 | 45 |

The updated distribution shifts strongly away from early elimination. More fourth- and fifth-place finishes are not, by themselves, evidence of a new problem: many more games now survive that far.

Approximate table-level 95% mean-score intervals are **13.36-15.86** earlier and **17.56-20.20** updated. Treating snapshots as independent samples gives an approximate interval of **+2.45 to +6.09** for the difference. Shared randomness or other cross-run dependence can change that uncertainty calculation. Neither interval removes the confounding effect of opponents updating their bots.

The equal-share reference is 100 total points divided by eight players, or 12.5. This is a symmetry reference, not a prediction that a particular random-action bot earns 12.5.

## 3. The earlier guaranteed-losing calls are gone

Earlier, your bot made **90 heads-up river calls** where the board plus the opponent's already-exposed card beat your complete retained hand. Those calls cost **71,361 additional chips**, across 86 tables. Twelve of those calls exhausted your remaining stack. The complete hand losses were larger, but earlier sunk contributions are not attributed to the call.

In the updated data, the corresponding check found **zero** such calls. The audit examined 995 earlier heads-up river calls; all updated heads-up river calls were checked using the same procedure. There were 1,112 total river calls earlier and 359 after the update, including multiway calls.

One earlier example: iteration 962, table 5, hand 108. You held `Ac Ah`; the board was `8d 7c Tc 6d 8h`; the opponent had exposed `9d`. Their public information already formed a ten-high straight. Your aces and eights could not win. The bot called its remaining 3,897 chips.

A cheap sufficient guard is:

```
on the river, with one eligible opponent:
    own_rank = evaluate(board + our_retained_pair)
    opponent_public_rank = evaluate(board + opponent_exposed_card)
    if opponent_public_rank > own_rank:
        calling cannot win or tie
```

This uses two evaluations, no range enumeration. The opponent's hidden card can only improve their best-five rank. Strict inequality matters. This guard concerns calling; raising can theoretically win by inducing a fold. Do not apply a simplistic version to multiway side-pot situations.

The separate reverse check found no heads-up river folds of hands guaranteed to beat every legal hidden card, in either snapshot. That is reassuring, but does not prove every fold was good.

## 4. Draw handling and postflop flexibility improved

Earlier, every one of **6,973 high-card-only postflop decisions** was a check or fold. There were no calls or bets with those hands. A high-card-only classification can include excellent draws; it does not mean the hand is worthless.

Among flop decisions facing a bet with a high-card-only four-flush:

| Decision subset | Earlier | Updated |
|---|---:|---:|
| All such opportunities | 255 | 150 |
| Calls | 0 | 118 |
| Folds | 255 | 32 |
| Of these, draws containing the suited ace | 68 | 41 |
| Calls with the suited-ace draw | 0 | 39 |
| Folds with the suited-ace draw | 68 | 2 |

These are decision opportunities, not an unconditional distribution of deals. Some folds are correct because of price, domination, multiway action, or future costs. The important improvement is that the new bot distinguishes draws rather than folding all of them.

The updated bot also raises after facing postflop aggression: **939 of 7,529 facing-bet decisions**, versus **zero of 10,202** earlier. The updated counts are 621 flop raises, 244 turn raises, and 74 river raises. Not every facing-bet state offers a legal raise; these are observed frequencies, not a claim about the exact number of legal raising opportunities.

The earlier bot made every non-all-in postflop bet/raise exactly floor(2/3 of the reconstructed pot): 7,085 such bets. A fixed size can be a sensible abstraction, but combined with rigid hand-category rules it made the overall policy unusually predictable.

## 5. Preflop selection now changes sensibly with table size

VPIP below means the fraction of hands in which your bot voluntarily called or raised preflop. Forced blinds do not count. PFR means the fraction with at least one preflop raise.

| Players alive at start of hand | Earlier VPIP | Updated VPIP | Earlier PFR | Updated PFR |
|---|---:|---:|---:|---:|
| 8 | 38.9% | 20.4% | 25.8% | 13.7% |
| 7 | 39.5% | 22.4% | 28.2% | 15.5% |
| 6 | 40.1% | 25.4% | 29.4% | 19.0% |
| 5 | 37.8% | 29.2% | 28.5% | 22.7% |
| 4 | 37.1% | 35.5% | 28.9% | 28.5% |
| 3 | 33.7% | 41.0% | 27.3% | 34.1% |
| 2 | 29.8% | 39.2% | 23.6% | 34.4% |

The earlier bot actually participated less as the table shortened. The updated bot is substantially tighter at full tables and substantially more active short-handed. That change is consistent with the sharp reduction in early busts, although the logs do not isolate its causal contribution.

Preflop all-in raises increased from 1,220 to 6,202. Most updated instances occurred at no more than 30 effective big blinds; only 33 were above 30 effective big blinds. This is not simply evidence of reckless deep-stack jamming. The decision subsets had positive aggregate observed hand-level ICM changes, but such conditional outcome totals are not estimates of the causal EV of jamming instead of another action.

## 6. Reveal behavior is much less predictable

Among retained pairs with different ranks, the earlier bot exposed the lower card **74.1%** of the time. The updated bot does so **49.7%** of the time. The updated distribution is also close to balanced within major hand-category groups.

The earlier bot always selected a pair in the highest currently available made-hand category. That is not automatically wrong, but it is consistent with underweighting future potential. The updated selection sometimes sacrifices immediate category: for example, 143 selections kept high card when a pair was available. Such departures can be correct when preserving draws.

Do not treat “less often maximizes current hand rank” as proof of worse selection. Selection needs continuation value, not just current five-card rank. A rare updated case discarded a currently made flush; that merits a targeted inspection, but it is not enough by itself to reject the new selector.

## 7. Highest-priority remaining issue: low-success river bluffs into public strength

The updated bot bet or raised in **117 distinct heads-up river hands** where the opponent's board-plus-exposed-card rank already beat your full hand. There was zero showdown equity against that opponent. Only **9 opponents folded**, a success rate of **7.7%**.

From those decision points to the end of the hand, your stack changed by **-42,307 chips in aggregate**. This is the additional result from the river decision onward, not the total losses of the affected hands. It includes folds, calls, raises, and uncalled refunds correctly. Each hand contributes only once.

These actions are bluffs, not mathematically impossible ways to win: the opponent can fold. Nevertheless, the observed response and losses argue against using them automatically. Calling in the same situation is a strict error; bluffing requires a sufficiently credible fold-probability model.

Examples from the updated snapshot:

| Iteration / table / hand | Your retained hand | River board | Opponent exposed | New bet/raise | Result from decision |
|---|---|---|---|---:|---:|
| 109 / 7 / 72 | Jc Js | Th 4d 9h 9s Ac | Ah | 2,646 | -2,626 |
| 684 / 1 / 65 | Kc 6h | 6d Qh 5d 4h As | Qs | 2,519, all-in | -2,519 |
| 859 / 7 / 102 | 2c Jd | 2d 9d Kd Th Kc | 9h | 2,381 | -2,381 |

In the first example, exposed `Ah` guarantees aces and nines, beating your jacks and nines. In the second, exposed `Qs` guarantees a pair of queens, beating your pair of sixes. In the third, exposed `9h` guarantees kings and nines, beating your kings and twos. The first example includes an uncalled refund, explaining why the net cost is slightly below the announced bet.

Recommended policy change: when public information already guarantees your hand loses at showdown, classify the proposed action as a **pure bluff**, regardless of its nominal category (“two pair,” “flush,” etc.). Require opponent-specific evidence of enough folding to justify the price. Default to check/fold against sticky opponents. Do not feed such hands into a value-betting rule merely because their raw category sounds strong.

For a terminal heads-up zero-equity bet of B into pot P, the simple break-even fold probability is B/(P+B), assuming no additional raise branch. Compare that threshold against a conservative context-specific fold estimate. A pooled 7.7% response across varying sizes is not itself a calibrated probability for every individual spot, but it is a strong reason to audit this branch.

Changing this branch would not guarantee recovery of 42,307 chips or any fixed number of tournament points in future runs; opponents and subsequent play change. The number measures what happened in this sample.

## 8. Secondary areas to test

### River defense may now be too conservative in some contexts

The overall river fold rate when facing a bet rose from **33.8% to 65.2%**. The observed opponent pool folded **32.6%** in the updated sample. These are different ranges and histories, so the gap is a diagnostic rather than proof that your bot overfolds.

The updated bot folds 96.1% of the 51 river responses in the greater-than-pot size bucket. That could be excellent against severe underbluffing, or exploitable against aggressive opponents. Do not globally loosen calls: the removal of guaranteed-losing calls is an improvement. Instead, distinguish opponent types, exposed-card blockers, and feasible bluff combinations.

### Turn all-in calls with one pair deserve a focused review

The updated snapshot contains 53 turn all-in calls with one-pair hands. Those hands ended with an aggregate **-37,661 chips** and **-271.35 recorded ICM points** of whole-hand change. This is not the causal EV of calling, because earlier commitments, hand selection, and outcome variance are included. Use it to choose hands for review, especially near the four-player bubble, rather than to impose “never call with one pair.”

### Test high-card continuation-bet frequency

When not facing a flop bet, the updated bot bets **1,730 of 2,457 high-card-only opportunities (70.4%)**. Some of these are useful semibluffs; some are air. Separate strong draws from weak air and compare response-conditioned returns against checking. The data establish a large policy change, not that this frequency is optimal.

## 9. The field is still highly heterogeneous

Across the opponents observed in your non-filler tables, pooled VPIP increased from **24.5% to 26.9%**, and pooled PFR from **16.4% to 18.0%**. This does not prove the field became stronger; more aggression is not synonymous with better play, and the sample is restricted to your tables.

The updated export still contains opponents with zero voluntary preflop participation over thousands of observed hands, alongside opponents entering and raising over 90% of hands. A single average-opponent model loses substantial information.

Use coarse table-local classes with strong shrinkage: extremely tight, aggressive, loose/passive, and unknown. Steal more against demonstrated folders; value bet more and bluff less against demonstrated callers; adjust all-in calling ranges to the particular opponent's observed range. Named opponents in exported logs are useful for offline diagnosis, but deployed seats are anonymized and live learning must reset at each table.

## 10. Recommended next revision

1. **Keep the updated bot as the current champion.** It has stronger observed results and removes specific defects.
2. **Patch the public-strength river-betting branch first.** Zero showdown equity must invoke a bluff model, not a made-hand value rule. Check/fold is the conservative default without demonstrated fold equity.
3. **Retain the corrected river-call guard, draw recognition, short-handed adaptation, and balanced reveal behavior.** No regression was found in those specific checks.
4. **Review the 53 one-pair turn all-in calls and selected large bubble losses.** Compare actual call prices, complete stack vectors, and opponent ranges.
5. **Tune river defense and high-card continuation bets locally, one parameter family at a time.** Preserve a held-out seed set and benchmark against both passive and aggressive opponents.

These histories contain no source code, predicted equities, intended-action probabilities, per-call timings, or full hidden opponent hands on folds. Therefore they cannot establish the precise internal bug, runtime headroom, exploitability, or counterfactual optimal policy. The strongest findings are the exact card-logic checks and the directly observed behavior changes; the remaining recommendations are testable hypotheses.
