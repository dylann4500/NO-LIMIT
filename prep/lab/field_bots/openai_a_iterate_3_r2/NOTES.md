# openai_a_iterate_3_r2

Upload **agent.py and preflop.json together**. `Agent` is defined at module level. The other Python files and `results/` are development evidence; the bot does not read them.

## Round 1 diagnosis

The supplied leaderboard reports **11.81 +/- 0.58 points per table**, 800 tables, **8.9% wins**, **39.4% top-three finishes**, and **zero failed decisions**. Fair share is 12.5 points. The strongest teams converted many more of their paid finishes into wins.

`analyze.py` independently parses the supplied compressed histories. They cover **120 tables and 17,221 hands**, including hands after our elimination; our seat was alive at the start of **12,869 hands**. This is a sample of the round, not all 800 tables. Across this sample, eight-handed play gained **32,759 chips**; three-handed play lost **70,833**, and heads-up play lost **22,024**. These are descriptive chip totals, not causal estimates or tournament point estimates.

`replay.py` reconstructs observations using only public events and the fake SDK. The original bot folded to **20 of 22 heads-up all-in reraises**, and **38 of 42 three-handed all-in reraises**. Its second-raise range prior remained approximately 8% regardless of short-handed play and effective stack size. In the same histories, revealed heads-up medium-stack reraises included J8o, 83s, 52o and A2s. Reveals select showdown hands, so they establish that the range was too narrow, not an unbiased estimate of its exact width. Example: against repeated heads-up reraises the original folded AJ and 77 at about 30-36 BB.

Most preflop folds were uneventful, so their total chip loss alone does not establish an error. The changes target the specific position, stack and range-model mismatch instead of globally loosening the bot. The original five-to-eight-player preflop range model is retained.

## Changes

- Separate per-seat public statistics for five-to-eight players, three/four players, and heads-up play. Opening opportunities, opening frequency, responses to raises and reraising frequency are tracked separately. Full-table history no longer dominates short-handed estimates.
- Wider short-handed reraising priors that depend on effective stack depth, adjusted by actual observed reraising frequency. Weak revealed opening and reraising hands can widen those ranges. Showdown selection cannot incorrectly narrow them.
- Wider button/small-blind steals, more appropriate cheap big-blind defense, and extra steals against opponents who demonstrably fold too often. Short-stack opening decisions use effective stacks, including when we cover a much shorter opponent.
- Short-stack resteals compare tournament utility for an uncontested pot, a called win and a called loss. Opponents' observed folds to reraises and their estimated continuing range enter the calculation. This calculation is restricted to a single live opponent and 9-25 BB effective stacks.
- More realistic air weights for opponents who bet much more frequently than they check, while retaining made-hand/draw conditioning. Added selective delayed turn bets after an opponent checks through the flop.
- Retained the original legal-action adapter, side-pot eligibility, payout-aware call decisions, river-nut protection, import-time preflop data, per-street equity cache and reserve-bank protection.

All adaptive information travels in per-table memory. No team names, table identities, cross-table learning, opponent code, network access or simulator implementation are used in decisions. `preflop.json` is unchanged from round 1.

## Validation and reproduction

Use the supplied Python from the workspace root:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_iterate_3_r2/analyze.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_iterate_3_r2/replay_compare.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_iterate_3_r2/validate.py
```

The validation script executes the supplied `field_kit/play.py`; it does not read or directly import simulator files. The kit gained an optional `--opponent NAME=BOT_DIR` argument to compare uploaded-style bots through its existing platform wrapper. Normal kit behavior is unchanged. The original bot directory is unchanged.

SDK validation covers 10,000 diverse states normally and again with a 2.5x advancing internal clock, including strict uncaught decision-path execution, legal kinds and raise bounds, side pots, payout conservation, guaranteed finishing prizes, river nuts, and depleted time banks. Targeted regression checks cover short-handed reraises, separate stage statistics, weak-showdown learning, effective-stack opening and the multiway resteal guard.

Earlier exploratory 1,000-table comparisons against the original scored 12.39 vs 12.61, 12.30 vs 12.70, and 12.39 vs 12.61. All had zero failed decisions. These runs informed scope reductions; they do not establish a gain against the original. The kit's check/fold and minimum-raise opponents also differ substantially from the actual round field. Final results and exact runtime-file hashes are recorded below and in `results/manifest.json`.

## Final local results

The following reports all use the delivered runtime files, identified by `results/manifest.json`:

- **1,200 eight-seat tables, four new and four original seats**, seed 20261125: **12.60 +/- 0.26 points** for the new bot versus **12.40 +/- 0.25** for the original. This is a small, statistically inconclusive edge. Upload passed; zero failures.
- **500 heads-up tables against the original**, seed 20261120: **40.00 +/- 0.45 points each**, 250 wins each. Fair share for the actual two-player payouts is 40, despite the kit report's fixed 12.5 label. Upload passed; zero failures.
- **500 default-kit tables**, seed 20261121: **20.78 +/- 0.45 points**. Upload passed; zero failures.
- **200 default-kit tables with 2.5x CPU-cost emulation**, seed 20261122: **20.61 +/- 0.71 points**. Upload passed; zero failures.
- **100 tables against seven minimum raisers**: **34.87 +/- 0.93 points**. Zero failures.
- **50 tables against seven check-or-fold opponents**: **50.00 points**, 50 wins. Zero failures.
- **30/30 upload tests passed**, 300 decisions, zero failures.

Across those six final matches: **1,752,268 decisions, zero illegal actions, exceptions or timeouts**. All +/- figures above are the kit's reported standard errors, not confidence intervals. Maximum observed memory was **1,628 bytes**. Default-kit wall p99 was **332.3 microseconds**; 2.5x emulation p99 was **600.7 microseconds**. The final SDK stress checks had CPU p99 **223.0 microseconds** normally and **181.0 microseconds** with the accelerated internal clock.

The final runtime-file hashes are:

- `agent.py`: `c7bf9ac131070a5d2402cef24506de60c1e99a7a82e5a22d55b859c7c45f11a4`
- `preflop.json`: `e5fc84e6f4d8eea81f198da356b8dfeb4b3365acba6f469e7a4ec71d8ac85d2f`

An earlier resteal version scored 12.88 versus 12.12 over 1,200 tables; its report and hash are saved as exploratory evidence. After restricting that calculation to a single live opponent, the SDK checks and original-bot comparison were repeated on the final source. `exploration_validation.txt` explains the deliberate source-consistency assertion from the intervening edit; `final_validation.txt` and the manifest record the completed final checks. No new tournament-field round has been run, so local improvements should not be interpreted as a guaranteed round-score gain.
