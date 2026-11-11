# openai_b_default_2_r2

Upload payload: `agent.py` and `preflop.json`. The remaining files are development tools and local evidence. The bot uses only standard-library modules, `eval7`, and the documented SDK. It stores table information exclusively in returned memory. The original `openai_b_default_2` directory is unchanged.

## Round-one diagnosis

Round one scored **9.19 points per table**, versus a 12.5 fair share, with **29.0% top-three finishes and no failed decisions**. This was a strategic problem rather than an action-legality problem.

`analyze.py` processes all 17,140 supplied histories from 120 tables; 11,622 hands contain our live seat and private cards. It accounts for posted blinds, incremental calls, street-total raises, wins, and final stacks. Of those live hands:

- 1,753 hands first entered by calling a raise lost **126,392 chips / 969.41 BB** in total and included 54 busts. This category includes blind defense. The loss is descriptive, not a claim that folding every one of those hands would have been better.
- 1,968 first-open hands gained **34,165 chips / 915.27 BB**; 78 first-three-bet hands gained **22,841 chips / 258.78 BB**. Three-betting was extremely scarce, while weak calls created difficult postflop decisions.
- A sharper fold comparison isolates **771 calls below the top 30% of the old preflop strength ordering**: actual net **−96,212 chips**, versus **−65,040** from immediately folding at those decisions. Folding that weak group would have saved **31,172 chips** on the recorded outcomes. The 982 stronger first calls outperformed immediate folding by **17,715 chips**. This is a hindsight chip comparison, not a counterfactual tournament rollout or prize-equity estimate.
- Our observed VPIP/PFR was **33.3% / 17.6%**; many opponents played roughly 20–26% / 14–19%. The data showed excessive weak blind defenses and dominated cold calls.
- Opponents' revealed raises contained much stronger hands than their first bets: only 1 of 164 shown opponent raises was classified as air without a draw. The old likelihood model distinguished a player's second raise from their first raise, but failed to distinguish a first bet from a raise of somebody else's bet.
- Hard preflop range cutoffs excluded some actually revealed weak suited hands, making two-pair and other strong postflop holdings impossible in the model. Sampled river likelihood rounding also distorted small probabilities.
- Three early raises could label a player a maniac and trigger a roughly 100-BB shove with 88. The sample includes exactly such a bust, against a third player's AA. A wide preflop opener was also assumed to raise arbitrarily weak hands after the flop.

`replay.py` reconstructs documented SDK observations from public events and calls our strategy directly, exposing exceptions instead of swallowing them. The original replay matched 99.05% of historical action kinds; Monte Carlo sampling and reconstructed resource limits account for remaining differences. Revealed-hand evidence is selected by reaching showdown and is not an unbiased estimate of all betting ranges.

## Changes

- Tightened deep-stack cold calls and small-blind calls, and priced the poor equity realization of weak offsuit big-blind defenses. Cheap suited/pocket-pair speculative calls retain explicit allowances.
- Expanded ordinary value three-bets to include AK/JJ and appropriate wider-opener hands. Removed unconditional deep-stack shoves solely because an opener was labeled a maniac.
- Corrected opening-order distortion: AA/KK/QQ keep priority instead of suitedness bonuses putting AJs ahead of AA.
- Recorded each bet's street action level and pot fraction. Postflop likelihoods now distinguish bets, raises, and reraises; late large bets and raises receive stronger ranges. True two-pair hands are separated from ordinary top pair.
- Added a small, importance-weighted preflop range tail using stratified samples from the main range and the full deck. Every legal opposing holding remains possible; strong hands made from weak preflop cards no longer have zero probability.
- Accumulated precise likelihood-weighted river showdown and continuing-range equity instead of rounding every likelihood to a few repeated combinations.
- Prevented deep-stack thin value raises with ordinary top pair, while retaining short-stack value aggression and calls that meet the equity/ICM threshold.
- Required more evidence for preflop maniac labels, and separate, much stronger evidence for indiscriminate postflop aggression. A handful of value bets no longer earns that label.
- Calibrated predicted fold chances with public fold observations and increased small continuation-bet frequencies against this often-folding field.

The existing ICM, side-pot, all-in, legality, memory, and soft-deadline protections remain. Maximum payload memory stays comfortably below the free 16-KB allowance.

## Validation

Final results and reproducible commands are recorded below. Intermediate results, including timing failures, are retained in `results/` rather than discarded. Earlier concurrent runs experienced substantial host scheduling pauses, including >200-ms wall-clock decisions, and cannot establish reliable timing or a strategic improvement. The 600-table intermediate old/new comparison was effectively tied (12.45 versus 12.55); it is not evidence of a gain against the live field.

`test_round2.py` covers weak blind defense, ordinary AK three-bets, false maniac detection, opening-hand ordering, bet-versus-raise accounting, and avoiding thin deep-stack river raises. `test_agent.py` retains independent ICM calculations, joint draws, board ties, side pots, event accounting, arbitrary seat IDs/payouts, short raises, and randomized core exceptions/legality checks. The final 24,000 randomized cases passed with no illegal actions or strategy exceptions. At a simulated 2.5x clock, p99 CPU was 0.633 ms (deep) / 0.625 ms (short); maxima were 0.790 / 0.770 ms. Every sampled scaled CPU duration was below the 1-ms allowance. This is CPU-budget evidence, not a measurement on tournament hardware.


## Final local results

These runs all used the final hashed payload, with sequential execution. **All three upload tests passed, with 0/30 failed upload decisions. Across 1,150 tables and 1,152,875 combined SDK match decisions there were zero failures: no illegal actions, exceptions, or timeouts.**

- **Default mix, 500 tables, seed 612:** **21.21 points per bot (SE 0.45)**. Four copies of our bot; two check-or-fold and two min-raiser opponents. 339,227 decisions, zero failures. Local p50/p99 latency 58.0 / 433.4 microseconds; maximum memory 2,057 bytes. `results/final_default_500.json`.
- **Direct round-one comparison, 400 tables, seed 613:** four revised versus four original copies. Revised **12.94 points (SE 0.45)**; original **12.06 (SE 0.44)**. Revised eighth-place finishes fell to 162 versus 238 for the original, across 1,600 seats each. 525,813 combined decisions, zero failures. `results/final_vs_round1_400.json`.
- **Mixed sparring field, 250 tables, seed 614:** two revised copies averaged **19.80 points (SE 0.83)**; tight 12.54, balanced 10.24, loose 7.42. Opponents use frozen round-one opening tables so our edits do not silently change their policy. 287,835 combined decisions, zero failures. `results/final_diverse_250.json`.
- **Final history replay:** all 18,335 reconstructed decisions completed through the strategy core without an exception. Historical action-kind agreement was 93.40%, reflecting the intentional policy changes. `results/final_replay.json` and `results/final_replay.txt`.
- **Final SDK stress:** 12,000 deep plus 12,000 short cases at a simulated 2.5x clock, zero illegal actions and zero strategy exceptions; independent numerical and targeted strategy regressions passed. Reports: `results/final_stress_deep_12000.json`, `results/final_stress_short_12000.json`, `results/regressions.txt`.

The direct comparison favors the revision but is too small to establish a reliable live-field gain. The kit's default opponents are much weaker than the real field; its 21.21-point result does not predict the next tournament score. Wall-clock scheduling outliers remain possible on other hosts, despite zero failures in the final runs. Pre-correction and concurrent results, including failures, remain under `results/` and `results/before_board_pair_fix/`.

Reproduce the final suite from the workspace root:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_2_r2/validate.py
```

Reproduce the history accounting:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_2_r2/analyze.py
```

Exact test commands and payload hashes are in `results/manifest.json`.

Final `agent.py` SHA-256: `7e6718d6936f15101c7ae60432989aeeebde46946b74dede932bbae6d0eb680b`.
