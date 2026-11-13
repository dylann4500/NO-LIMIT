## Rig prompt test (Part 3): report

I ran it clean-room. I read only the prompt, the starter kit and the download. Clock: started 16:24:30 and stopped building at 16:54 (about 30 of the 60 minutes). Every item ran locally on at most 4 processes. Nothing used Modal: it isn't installed in the kit's .venv, and it wasn't allowed today. About 1,100 lines of code are in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/prompttest/rig/rig/`. That folder holds runner.py, spar.py, replay.py, fanout.py, stats.py, clone_agent.py, clonefield.py and tester.py. The bots are in `.../prompttest/rig/bots/` and the candidates in `.../prompttest/rig/candidates/`.

Caveat on timing: I'm an agent working with no human in the loop. A day-of agent will be slower, because it has to coordinate with the team and the machine is shared.

### 1. Item by item

**Item 1, local match runner: done (about 2 minutes once the kit was read).**
- **How it works:**
  - It runs bots in-process (an async `act` that returns `Reply`), not through `poker-agent play`, which starts subprocesses.
  - It drives `SitAndGo` + `poker_engine.play.play_table` + `table_points`.
  - Any `TableRules` field can be set (JSON passed to `rules_from_dict`), the variant is pinned to `flop_discard_reveal`, and rows are kept per table.
  - It reports failed decisions and p99/max latency per bot.
- **Pairing:**
  - Every candidate plays the same table seeds in the same seat. The engine deals each hand from `seed:hand:N` by position from the button, so the cards really are the same.
  - Determinism checked: two runs with the same seed gave identical output for deterministic bots.
- **Trustworthy?** Yes, but pairing barely reduces noise. On the clone field the paired SE was 0.89 against 0.71 for one bot alone, about √2 larger: once one decision differs, busts and seating diverge. You need lots of tables, not clever pairing.
- **Speed:** 20–31 hero-tables per second on 4 cores against simple bots, and about 7 per second against the clones.
- Example (400 tables, sparring field):
```
live        pts/table 21.325 ± 1.091  failed 0/50941  p99 0.022ms
cand_tight  pts/table 25.125 ± 1.038  failed 0/70641  | paired vs live: +3.800 ± 1.035 (z +3.7)
cand_loose  pts/table 17.150 ± 1.087  failed 0/38961  | paired vs live: -4.175 ± 0.903 (z -4.6)
```

**Item 2, Modal fan-out: written but not run on Modal, so unverified.**
- `fanout.py` builds the image from the kit's requirements plus the SDK, adds the bot folders last, and `.map`s shards of 100 tables.
- Its `--local` path (the same shard function) works: 400 tables × 4 candidates in 51 seconds.
- **Not verified:** that the image builds, container start time, and the 20,000 × 4 in five minutes target. My estimate is about 80,000 hero-tables over roughly 100 containers at about 6 per second each, which is 2–3 minutes plus start-up. Locally the same job would take 45–65 minutes.
- **Caveat:** latency measured inside containers means nothing, so fan-out runs have timing enforcement off.

**Item 3, sparring bots: done (about 3 minutes).** There are four (station, shover, nit, 3-bettor), each played as 7 copies, plus a mixed field. It worked and caught real holes:
```
== vs spar_nit (200 tables)
live        19.550 ± 1.608
cand_tight  23.750 ± 1.595 | paired vs live: +4.200 ± 1.531 (z +2.7)
cand_loose  11.050 ± 1.381 | paired vs live: -8.500 ± 1.540 (z -5.5)
```

**Item 4, replay testing: done (about 4 minutes), and the numbers are trustworthy.**
- **How it works:**
  - It rebuilds each table in the real engine with a rigged deck: our cards, the board, and opponents' exposed or shown cards, with random filler for unknown cards.
  - The deal order is found by probing: card k goes to position p at `deck[k*n+p]`, then burn, flop, burn, turn, burn, river.
  - It replays every logged action and asks each candidate at each of our decisions, including select.
  - It checks the stacks every hand. Result: 1,012 tables and 134,032 hands with zero drift, in 71 seconds on 4 processes.
- **Two caveats:**
  - The outcome column is observational, not a counterfactual.
  - Candidates that use unseeded `random` show spurious differences.
- Example (candidate against our live folder, `--vs-first`, 300 tables):
```
gen_10: 35930 decisions, 5084 differ (14.1%), 16.9 per table
situation                n  differ  pts/hand same  pts/hand differs  top changes (live->cand)
preflop/unopened/15bb+ 13553 13.5%   0.108   0.243  call->fold:1218, raise->call:567
preflop/unopened/<15bb   821 34.6%   0.105  -0.000  fold->allin:119, call->allin:106
flop/checked-to/15bb+   2263 23.9%   0.155   0.604  check->raise:298, raise->check:243
```

**Item 5, cloned field: partly done (about 15 minutes including runs). It is not trustworthy, and the prompt's own check says so.**
- **What ran:**
  - Fitting 127 clones from the download (5 seconds).
  - Calibration at 400–800 tables per iteration, not 10,000; each iteration took about 60 seconds.
  - Bluff variants, adaptive clones, and paired evaluation.
- **Calibration** (measured/simulated, after 2 damped iterations). Preflop open rates match; conditional rates don't:
```
clone            open/early  open/late  vs_open:fold  vs_3bet:fold  bet/flop   vs_bet/flop:fold  river_bet_sd_win
c_avalon         0.20/0.21   0.30/0.30  0.70/0.70     0.80/1.00     0.87/0.88  0.33/0.40         0.57/0.58
c_avisioner      0.01/0.02   0.15/0.17  0.96/0.96     0.90/0.60     0.44/0.38  0.34/0.21         0.73/0.56
c_Poker_Slugs    0.26/0.27   0.56/0.55  0.87/0.87     0.70/0.74     0.38/0.34  0.81/1.00         0.74/0.68
```
- **The live-bot check fails.** I didn't have avalon's real bot, so I used avalon's clone as the stand-in. It scored 12.18 ± 0.66 points per table against a real 18.44. By the prompt's rule, don't trust this round's clone field.
- **Candidate verdicts across the three opponent models** (paired against live, 600 tables):

| Clone variant | cand_tight | cand_loose |
|---|---|---|
| Bluff 0.0 | +1.78 ± 0.86 | −2.50 ± 0.84 |
| Bluff 0.3 | +1.33 ± 0.88 | −2.13 ± 0.89 |
| Adaptive | +3.80 ± 0.84 | −2.30 ± 0.87 |

  The direction held in every model. The size did not.

**Item 5b, candidate generator: done, but too noisy locally.** I made 12 random style-parameter sets and ran them through the item 6 tester at 300 tables, where the paired SE is about 1.3, too large to separate them.

**Items 6 and 7, candidates/ tester with one-line verdicts: done (5 minutes to run 13 candidates).** It runs the clone field, a fresh-deals rerun of the top two, sparring, replay difference and latency. No candidate passed my bar (fresh rerun z > 2, no sparring loss, zero failures):
```
gen_02  replay differs 37.3% | clone +2.37±1.26 | fresh +2.03±1.18 | spar +6.20±2.35 | p99 0.02ms max 4.9ms fails 0 | no
gen_10  replay differs 37.0% | clone +1.67±1.29 | fresh +2.17±1.28 | spar +7.20±2.30 | p99 0.02ms max 2.5ms fails 0 | no
gen_11  replay differs 43.4% | clone -4.33±1.33 | fresh    n/a     | spar -7.50±2.35 | ... | no
```

### 2. Realistic order on the day
- **First 30 minutes (minutes 15–45 of the build):** item 1 (in-process runner with paired SE, failures and latency), then item 3 (sparring), then a minimal item 7 that compares a candidates/ folder against live using sparring plus runner. None of these needs a download. If a practice-round download exists, also do item 4: it's cheap (about 5 minutes to build, 1 minute to run) and has no model error.
- **By the end of the build hour:** item 2 on Modal, but only after someone has confirmed `modal` is installed and the image builds. Item 6 picking up candidates/ automatically.
- **Only between later rounds:** item 4 on each new download, item 5 (fit, calibration of 10,000 or more tables, bluff and adaptive variants), item 5b. Item 5 needs Modal to be useful: locally each 10,000-table calibration iteration is about 15 minutes. Its first-round result will probably fail the live-bot check anyway.

### 3. Critique of the prompt (quote, then proposed wording)
1. "We have a Modal workspace signed in on this machine; use it for anything that takes more than a minute locally, and start the image build first"
   - Problem: it sends the agent to infrastructure before there is a runner, and `modal` isn't in the kit's .venv.
   - Proposed: "First build item 1 locally and get correct numbers. Then wrap its shard function for Modal (check `python -c 'import modal'` first). Kick off the image build in the background once the runner works."
2. "A local match runner on the kit's engine"
   - Problem: it gives no API, so the agent may wrap `poker-agent play`, which runs subprocesses (2 per bot) and is slow.
   - Proposed: "Run bots in-process: an object with `async def act(state, memory)` returning `poker_agent_protocol.runner.Reply(action, memory, bank_ms)`. Play with `poker_engine.play.play_table(SitAndGo(rules=TableRules(variant='flop_discard_reveal'), variant=load_variant(...), table_id, seed), bots)` and score with `poker_engine.scoring.table_points(result, table.payouts)`. Use `rules_from_dict` for settable rules. Use a `ProcessPoolExecutor` with an `if __name__ == '__main__'` guard (macOS spawns)."
3. "a seed so two candidates can play the SAME deals (paired)"
   - Problem: it implies pairing buys precision. It barely does here (measured paired SE was 1.25× one bot's own SE).
   - Proposed: "Same table seed means the same cards by position each hand. Report paired SE, but expect little variance reduction: SE is about 13/√tables. Seed any bot RNG from table_id and hand so reruns are exact."
4. "every table rule from state.config settable"
   - Problem: `TableConfig` is a subset of the rules.
   - Proposed: "every `TableRules` field (including payout_total, resampling, icm_luck_correction)".
5. "report where it acts differently from the live bot"
   - Problem: the download contains the bot that was live then, which may not be today's live bot.
   - Proposed: "Compare each candidate (a) with the logged actions and (b) with the current live bot folder on the same reconstructed states. Rebuild states in the engine with a rigged deck (deal order: card k to position p at deck[k·n+p], then burn/flop/burn/turn/burn/river). Fill unknown cards at random, check the stacks every hand, and drop tables that drift. The outcome column is observational, not counterfactual."
6. "Make each clone take its aggressive actions with its strongest hands … at the measured rates"
   - Problem: it misses the key detail, that the percentile must be within the range that reached the spot. My unconditional version gave vs-3bet fold 0.27 against 0.80 real.
   - Proposed: "…rank hand strength within the range the clone would hold at that point, and calibrate the fold/call/raise split, not only the raise rate."
7. "first play our LIVE bot against the clones and compare … with the real ones"
   - Problem: it only works if the live bot is the one that played the download. Also, with one round of data the check will likely fail; my stand-in clone scored 12.2 against 18.4 real.
   - Proposed: "…If the live bot changed since the download, use the bot that played it. Expect this check to fail in round 1; then report clone results only as warnings."
8. "Part 6" and "A fuller ordering test is pending": the agent never sees Part 6. Drop them from the pasted text.
9. Item 7's "fit to ship"
   - Problem: no criterion is given.
   - Proposed: "Challenger = fresh-deals paired difference > 2 SE, no sparring loss > 2 SE, zero failed decisions, `poker-agent check` passes, and p99 latency under 0.5 ms timed on an idle core (in-process timings under load are not the platform's)."
10. Item 2's "Never upload hand histories anywhere"
    - Problem: it doesn't say whether stats derived from them (clone params.json files, which describe other teams' play) may be uploaded to Modal.
    - Proposed: say whether they may, explicitly.
11. Length: item 5 alone has about ten sub-tasks. Split the prompt into a build-hour brief (items 1, 3, 7) and a between-rounds brief (4, 5, 5b, 2 at scale).

### 4. The single most valuable change
Give the agent a short build-hour brief with the engine API spelled out and one deliverable: `rig/compare.py LIVE CAND… --tables N --field …`. It should run bots in-process through `SitAndGo` + `play_table` + `table_points`, use the same table seeds for every candidate, and print points per table with paired SEs, failed decisions and p99 latency against the kit examples and four sparring bots. Item 4 joins as soon as a download exists. Modal, the cloned field and the generator move to a separate between-rounds prompt. With the API given I had a working runner in about 2 minutes and sparring results in about 4. Item 5's open-ended work (15 minutes for an uncalibrated field that failed its own live-bot check) would otherwise eat the build hour. And without Modal working, nothing in item 5 or 5b reaches the precision needed to pick a challenger before the first scored round.
