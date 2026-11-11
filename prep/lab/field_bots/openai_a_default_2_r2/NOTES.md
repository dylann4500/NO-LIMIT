# Round 2: openai_a_default_2_r2

Runtime entry point: `agent.py`. Its only data dependency is the unchanged
`preflop.json`, loaded relative to the entry point. Dependencies remain the
standard library, `eval7`, and the documented SDK. All learned information is
anonymous and per table, carried in SDK memory. The round-1 folder is unchanged.

## What round 1 showed

The complete leaderboard reported 11.99 points per table (SE 0.59) over 800
tables, versus fair share 12.5. There were no failed decisions. First/second/
third/fourth counts were 74/123/110/137: the bot survived reasonably well but
converted too few tables into wins. The difference from fair share alone is
not statistically decisive.

I wrote `analyze.py` and `replay.py` to inspect the supplied histories and
reconstruct SDK observations using only documented events. The history sample
contains 17,204 hands from 120 tables, of which 12,575 hands include our live
bot; it is a subset of the 800-table leaderboard. No simulator implementation
was read or directly imported. Matches use the kit's `play.py` driver.

Concrete findings:

- **Heads-up position was reversed in the preflop range model.** The old code
  assigned the button the big-blind range width (0.25), while giving the big
  blind 0.56. Its separate opening policy hid this error; defense and equity
  estimation still used the wrong ranges.
- **Short open shoves received deep-stack overbet discounts.** Among the 15
  heads-up shove calls with revealed opponent cards, the old model's average
  opponent range fraction was 0.128, while the revealed hands' average strength
  percentile was 0.575. Estimated hero equity averaged 0.584 versus roughly
  0.697 against the actual revealed hands. These small, selected showdown
  samples are diagnostic evidence, not an unbiased population equity test.
- **The field gave up pots to pressure.** Excluding our own decisions, opponents
  folded 1,539/2,608 (59.0%) responses to medium flop bets, 835/1,395 (59.9%)
  on the turn, and 512/672 (76.2%) on the river. Here medium means the call is
  35% to under 80% of the pot visible at the decision, including the bet.
  These are observational rates, influenced by selection and pot geometry.
- **Our later-street betting was particularly sparse.** When checking was free,
  we bet 196/901 turn opportunities (21.8%) and 132/621 river opportunities
  (21.3%), versus other bots' 37.2% and 27.7%. Checking opponents were not
  reflected in our posterior ranges. The old range model consequently missed
  both thin value and profitable bluff opportunities.
- **Some one-pair hands were raised too hard.** Top pair could meet the old
  value-raise gate, then trigger a stack-sized raise at moderate pot sizes.
  Several revealed examples lost large pots to sets or better kickers. Those
  examples do not mean every such raise was wrong, but justified a more
  conservative raise gate distinct from the ordinary value-bet gate.

Raw findings are in `validation/history_analysis.json` and `diagnostics.txt`.

## Changes

1. Correct heads-up action order and positional opponent ranges. Do not apply
   deep-overbet range discounts to an opening shove committing at least 80%
   of an initial stack of at most 16 BB; use stack- and position-aware floors.
2. Require repeated reraising disproportionate to the number of raising hands
   before declaring a maniac. Several ordinary three-bets are insufficient.
3. Track actual opportunities to fold to a bet separately by street, excluding
   free checks and initial bets. Shrink the anonymous per-opponent observations
   toward field priors; adapt away from bluffing callers and wild raisers.
4. Widen late-position steals when the remaining opponents' response estimates
   support them. Increase heads-up continuation bets, positional turn probes,
   and river bluffs against players likely to fold. Avoid bluffing into an
   all-in opponent. Use approximately half-pot pressure rather than the old
   small continuation-bet sizing.
5. Condition equity on current checks while retaining some strong traps.
   Preserve information from a preceding street's call when capping a checked
   range. This also permits more thin value with medium-strength made hands.
6. Separate betting for value from raising for value. Require stronger equity
   and hand quality to reraise; reduce one-pair bet sizing and automatic jams.

On the same 17,669 reconstructed historical observations, the revision chose
2,571 preflop raises versus 2,278 historical raises, and 808/346/229 flop/turn/
river raises versus 696/224/137. This is a policy comparison on fixed states,
not a counterfactual tournament result.

The legality adapter, ICM calculations, side-pot handling, offline preflop
equities, deadline-limited sampling, and GC restoration remain in place. Below
7 ms of bank, a new emergency sampling tier uses 16 candidate hands, 64
posterior particles, and 160 primary runouts (80 for additional opponents).
The previous below-15-ms tier remains. Maximum observed memory is 2,049 bytes,
below the free 16 KB.

## Validation

All checks below were run sequentially. The first comparison and standard-mix
run preceded only the final below-7-ms sampling refinement; later checks cover
that final refinement as well.

- **Final previous-bot comparison, 200 tables, seed 251:** revision **15.03
  points** (SE 0.68) versus previous version **9.97** (SE 0.56), four seats each.
  Revision finishing counts: `[137,101,107,89,78,88,106,94]`; previous version:
  `[63,99,93,111,122,112,94,106]`. **256,762 decisions, zero failures**, upload
  passed 10/10. Wall p99 266.5 us, p99.9 8,011.2 us, maximum 43.0 ms;
  bank absorbed overruns. Maximum memory 2,049 bytes. Report:
  `validation/final_head_to_head_seed251_200.json`.
- **Previous bot comparison, 150 tables, seed 227:** revision **15.09 points**
  (reported SE 0.79) versus previous bot **9.91** (SE 0.64), four seats each.
  Revision finishing counts: `[106,80,68,67,67,74,69,69]`; previous version:
  `[44,70,82,83,83,76,81,81]`. **194,048 decisions, zero failures.** Upload
  passed, 10/10 decisions. Wall latency p99 194.0 us, p99.9 444.5 us. Report:
  `validation/head_to_head_seed227_150.json`.
- **Standard kit mix, 200 tables, seed 233:** **20.26 points** (SE 0.73);
  check-or-fold 8.97, min-raiser 0.50. **132,897 decisions, zero failures.**
  Upload passed, 10/10 decisions. Wall latency p99 284.5 us, p99.9 4,439.2 us;
  the bank absorbed occasional wall overruns, including a 37.3 ms maximum.
  Report: `validation/final_default_seed233_200.json`. A clean original-bot
  200-table reference run at seed 211 scored 21.01 (SE 0.71); the different
  seed and stochastic equity samples mean this is not a paired comparison.
- **Full historical SDK replay:** 17,669 decisions, **zero illegal actions**;
  CPU p50/p99/p99.9/max = 50/207/249/323 us, wall maximum 11,517.9 us. Maximum
  memory 2,049 bytes. At 2.5x CPU cost, p99.9 is approximately 623 us. Replay
  timings are diagnostic; complete matches enforce the actual time budget.
  Report: `validation/replay_profile.json`.
- **Independent regressions:** **16 tests passed**, including the inherited
  1,800 randomized states and new checks for heads-up position, short-shove
  sizing, regular three-bettor classification, genuine fold opportunities,
  and checked river ranges. Report: `validation/unit_tests.txt`.
- **Final 2.5x CPU slowdown, 100 tables, seed 241:** **20.75 points** (SE 1.01),
  **68,192 decisions, zero failures**; upload passed 10/10. Wall p50 136.3 us,
  p99 2,172.9 us, p99.9 9,302.8 us, maximum 27.8 ms; bank absorbed overruns.
  Maximum memory 2,049 bytes. Report: `validation/final_slow_seed241_100.json`.
  An earlier slowdown run at seed 239, before the below-7-ms refinement, had
  one timeout across 63,457 decisions and wall maximum 57.3 ms; it is retained
  as `validation/slow_seed239_100.json`, not counted as a clean runtime pass.
- **Aggression sensitivity, 100 tables, seed 257:** four revision seats,
  two original-bot seats, and two synthetic `pressure` seats. Revision **12.88
  points** (SE 0.91), original **10.49** (SE 1.10), synthetic pressure **13.76**
  (SE 1.34). **124,566 decisions, zero failures**, upload passed 10/10.
  This deliberately more aggressive mix weakens the advantage relative to
  pure original-bot opposition; it is not evidence that we beat every style.
  Report: `validation/pressure_seed257_100.json`.

The final code's last head-to-head, slowdown, and aggression sensitivity checks
total **449,520 decisions with zero failures**, plus clean upload checks.

Commands (from the workspace root; use the supplied Python environment):

```sh
PYTHONPATH=lab/fake_sdk /Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_default_2_r2/test_agent.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_default_2_r2/compare.py lab/field_bots/openai_a_default_2_r2 --tables 150 --seed 227 --seats self,self,self,self,baseline,baseline,baseline,baseline
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_default_2_r2/compare.py lab/field_bots/openai_a_default_2_r2 --tables 200 --seed 251 --seats self,self,self,self,baseline,baseline,baseline,baseline
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_a_default_2_r2 --tables 200 --seed 233
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_a_default_2_r2/slow_agent --tables 100 --seed 241
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_a_default_2_r2/compare.py lab/field_bots/openai_a_default_2_r2 --tables 100 --seed 257 --seats self,self,self,self,pressure,pressure,baseline,baseline
```

The comparison driver `compare.py` executes the kit's `play.py` with its
existing SDK adapter and registers the previous submitted Agent as a named
opponent. It does not read or directly import simulator modules. Each side
occupies four randomly seated places; reported decision/failure totals include
both versions. `pressure` is an optional synthetic aggressor for sensitivity
checks, not an actual tournament opponent.

`slow_agent/agent.py` is a local test wrapper, not a runtime dependency. It
reduces the internal conditioning deadline by 2.5 and adds 1.5 times measured
decision CPU work to simulate the slower tournament hardware, while leaving
the kit's real 1 ms decision limit and bank unchanged.

The initial concurrent development runs had substantial wall-clock stalls:
`revised_seed211_200.json` had 314 timeouts (maximum latency 230 ms), and
`head_to_head_seed223_300.json` had 270 (maximum 194 ms). They had no illegal
actions or exceptions. Those runs are retained, not treated as runtime passes,
and the remaining match validations are sequential. The latter comparison
favored the revision 14.55 to 10.45 points, but the clean sequential comparison
is the primary result. Arbitrary host descheduling cannot be eliminated by a
Python policy; CPU profiles and the slowdown check measure implementation cost.

These local tests do not establish a round-2 tournament score against the
unavailable live field.
