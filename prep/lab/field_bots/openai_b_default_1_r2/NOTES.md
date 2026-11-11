# openai_b_default_1_r2

Runtime files are `agent.py` and `preflop.json`. Dependencies remain the standard
library, eval7, and the public poker_agent_sdk. The round-one directory was left
unchanged; its agent still hashes to
`5e863281475892ded204ba2260d589f9e33b72ba3e866aa1cfac40b4589241aa`.
No simulator source was inspected or imported by the analysis, tests, or bot.
All simulated matches were run through the supplied public `field_kit/play.py`.

## What round one showed

The leaderboard reports **11.53 ± 0.60 points over 800 tables**, versus 12.5 fair
share, and zero failed decisions. The supplied history is a **120-table subset**:
17,295 hands including hands after our elimination, 11,797 hands with our cards,
and 16,427 recorded decisions. It is not an 800-table hand sample.

`analyze_round.py` reconstructs contributions, chip results, streets, and actions.
`diagnose.py` measures opponent responses and examines revealed hands.

- Across the recorded field, voluntary participants facing a second or later
  preflop raise folded **2,542 / 3,390 = 75.0%** of responses. Our bot folded
  **345 / 423 = 81.6%**. There is room for selective reraises against this field.
- Our hands ending with a preflop raise followed by a fold occurred 316 times
  and lost 714.6 big blinds. This is a loss bucket, not proof that all those
  initial opens were bad. The previous three-betting range was concentrated in
  premiums, often leaving useful blocker hands as passive calls.
- The costly payoff examples included AJ calling a large third barrel on
  A-7-5-5-T, weak aces paying river raises on paired boards, and overpairs
  continuing against increasingly strong ranges. The old posterior considered
  only the latest voluntary action, evaluated it on the current board, and
  reverted to the entire preflop range when fewer than five combinations
  survived. That last fallback could make strong action look weak again.

## Changes and rationale

1. **Sequential postflop ranges.** Condition on up to four recent calls/bets/
   raises, each using the board visible when it happened. Temper earlier
   likelihoods to account for correlated actions. Distinguish ordinary bets
   from raises, and reduce weak hands in large raises and later barrels.
   Replace the sparse-range reset with systematic weighted resampling. A native
   eval7 check established that its equity routines ignore numeric range
   weights, so posterior weights are represented by combination multiplicity.
2. **Selective preflop pressure.** Add three-bets with suited aces, selected
   suited broadways, and some offsuit blockers against wide opens. Use a 75%
   population folding prior, then update from anonymous per-table reraise
   responses. Require favorable immediate fold economics, sufficient effective
   stacks, limited cold callers, and position-dependent mixing. Avoid observed
   maniacs. Expand value three-bets to TT/AQ against sufficiently wide opens.
3. **Control marginal pots.** Check more one-pair flops out of position as the
   preflop caller, and check back some marginal third value barrels. Strong
   hands and aggression against observed maniacs retain their value lines.
4. **Fix paired-board classification.** Two private pairs above a lower board
   pair remain genuine two pair; a board pair alone still does not turn a
   marginal hand into strong private two pair.
5. **Keep timing headroom.** Sequential range work uses at most 96 candidates,
   or 48 with a low time bank, with CPU deadlines. Native runout counts are
   reduced to 384 heads-up / 256 multiway, or 128 with a low bank. Memory schema
   v5 carries two additional opponent reraise-response counters. No runtime
   learning or information is carried between tables.

## Recorded-state checks

`replay.py` reconstructs SDK states and transfers serialized memory between
copies, without a simulator import. `test_round_regressions.py` checks all
**16,427 decisions**, legal raise bounds, zero exception-guard activations,
sequential posterior behavior, the paired-board fix, and three costly river
payoff regressions. The inherited 2,500-state SDK suite passes normally and with
its deadline clock scaled by 2.5.

`check_changes.py` audits changed terminal calls using revealed hands. The
comparison changed **26 historical river calls to folds**: 18 losing calls
avoided and 8 winning calls surrendered. The net immediate chip difference was
**+195.4 big blinds** across those decisions, accounting for both sides. This
is a hindsight diagnostic on fixed recorded states, not a simulated tournament
result, a causal point estimate, or an out-of-sample claim. Actual play would
reach different later states after earlier actions change.

## Final local validation

The final-hash matrix completed **1,300 tables and 781,561 table decisions**, plus
50 matrix upload decisions, with **zero failures**: no illegal actions,
exceptions, or timeouts. All five matrix upload tests passed. An additional **32 / 32 upload seeds**
(701–732, 320 upload decisions) passed with zero failures. Maximum memory
was **2,214 bytes**. `validation_manifest.json` identifies the reports and hashes.

- Standard mix, 600 tables, seed 101: **21.16 ± 0.41 points per self seat**.
  Four copies, two check-or-fold bots, two min-raisers. Median latency 29.2 µs,
  p99 149.1 µs, maximum 390.4 µs. `results_final_mixed.json`.
- Seven copies / one min-raiser, 200 tables, seed 211: **14.21 ± 0.49**.
  `results_final_7_self.json`.
- One copy / seven min-raisers, 200 tables, seed 307: **37.97 ± 0.71**.
  `results_final_7_raisers.json`.
- One copy / seven check-or-fold bots, 100 tables, seed 401:
  **49.69 ± 0.03**; first by stack in all 100. `results_final_7_passive.json`.
- **2.5× CPU stress**, 200 tables, seed 659: **21.89 ± 0.70**, zero failures,
  with the exception guard disabled. Across 134,257 calls including upload,
  charged CPU p99 was 378 µs, maximum 932 µs, and no CPU call exceeded 1 ms.
  Two wall-time calls exceeded 1 ms (maximum reported 1.090 ms); the time bank
  absorbed them. `results_release_slow_machine.json`.

These local opponents do not reproduce the tournament field. The ordinary
mixed score is statistically similar to the previous release's local score;
the motivation for the changes is the field's reraise folding and the
recorded-state payoff audit, not a claimed local-score improvement. Early build
reports are retained separately, including a slowdown probe with one charged
CPU call above 1 ms but no failed decisions. Timing cannot guarantee absence of
OS scheduling stalls on other machines.

## Reproduction

From the workspace root, use
`/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python` as Python and set
`PYTHONDONTWRITEBYTECODE=1` when running tests that load the old agent.

```sh
python lab/field_bots/openai_b_default_1_r2/analyze_round.py
python lab/field_bots/openai_b_default_1_r2/diagnose.py
python lab/field_bots/openai_b_default_1_r2/replay.py
python lab/field_bots/openai_b_default_1_r2/check_changes.py
python lab/field_bots/openai_b_default_1_r2/test_agent.py
python lab/field_bots/openai_b_default_1_r2/test_agent.py --cpu-scale 2.5
python lab/field_bots/openai_b_default_1_r2/test_round_regressions.py
python lab/field_kit/play.py lab/field_bots/openai_b_default_1_r2 --tables 600 --seed 101
python lab/field_kit/play.py lab/field_bots/openai_b_default_1_r2 --tables 200 --seed 211 --seats self,self,self,self,self,self,self,min_raiser
python lab/field_bots/openai_b_default_1_r2/validate_extra.py
python lab/field_bots/openai_b_default_1_r2/test_slow_machine.py --tables 200 --scale 2.5 --seed 659
```

The additional upload harness runs one heads-up table per seed because the
public tester does not support `--tables 0`. See `results_final_uploads.json`
for its separate upload-seed results.

Final agent SHA-256:
`4ae6ecb63a0a8242991c7d2ebd011ecab55af9460fbef109040af6d3f4bc74fa`.
The unchanged equity asset SHA-256:
`36f9b434fbb3f154738f42870ff2af6cb82e90d2ad1bb0c6ebafa2ebdd4aaffa`.
