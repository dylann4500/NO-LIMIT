# claude_icm: notes

An ICM-aware sit-and-go bot for 8-max NLHE with 50/30/20 payouts. Files:

- `agent.py`: the bot (`Agent` at module level).
- `preflop.json`: tables built offline and read at import.
- `build_tables.py`: the offline builder for `preflop.json`. The bot never imports it.

## Approach

**Budget.** Each decision gets 1 ms, the real machines are about 2.5x slower than this one, and the upload test runs with no time bank. Nothing expensive happens at decision time. Preflop work is table lookups plus closed-form ICM. Postflop uses one small eval7 Monte Carlo per villain. Measured CPU time per decision here is p50 about 30 µs, p99 about 100 µs, p99.9 about 150 µs and worst case about 0.3 ms in fuzzing, so roughly 0.75 ms worst case on the real machines. An import-time warm-up runs the preflop, flop and river paths once, and `gc.freeze()` runs after import.

**Preflop tables (offline).** The 169 hand classes are ranked by a blend of equity vs random and equity vs a top-20% range. Each class also has its heads-up all-in equity vs the top-X% ranges (X = 2 to 100, interpolated to every integer percent). From these we derive a "rational caller" table: given the pot odds a caller faces and the range they think we shove, it gives the share of hands that call.

**ICM.** This is Malmuth-Harville equity for our own seat only. The 3-payout case is closed form at about 2 µs for 8 players. Larger payout lists use a pruned recursion, and payouts are read from `state.config.payouts`. When we bust, we get the payout for our finishing place. Pure ICM ignores future blind pressure, so the value we use is a blend of ICM and chip-linear value:

- The ICM weight is 0.6 with 7 or more players left, 0.72 with 6, 0.85 with 5, and 1.0 from the bubble (4 players) down.
- It is also 1.0 in the last 25 hands before the hand cap, where survivors are paid by ICM.
- It is reduced when our own M is below 8.

**All-in decisions (the core).** These cover open shoves, reshoves, and calling or overshoving an all-in. Each one is a direct ICM EV comparison against folding:

- EV(shove) = P(everyone folds) × value(we win the pot) + Σ over potential callers of P(v is the first caller) × [eq × value(win) + (1 − eq) × value(lose)].
- Final stacks are computed exactly for the matched amount. Busting players leave the ICM pool, which is what produces bubble behaviour.
- A villain's call probability comes from pot odds plus a survival tax (largest on the bubble when we cover them) and our perceived shove range. It is blended with that villain's observed fold-to-raise rate.
- Our equity is measured against the villain's calling range, not against random hands.
- A villain's shove range is estimated from his depth and position and blended with his observed raise frequency.

**When the all-in model applies:**

- Unopened pots with an effective stack of 10bb or less (14bb or less from the cutoff, button or small blind).
- Facing a raise with an effective stack of 20bb or less (32bb or less vs a 3-bet).
- Any time we face an all-in, or a call would commit us.

**Deep-stack preflop.** Opening ranges depend on how many players are left to act, and widen when the players behind fold a lot (observed). They tighten on the bubble when we are medium-stacked and widen when we are the big stack. We iso-raise limpers. Facing an open, we 3-bet for value when our equity vs the raiser's estimated range is 0.60 or more, and call on pot odds with a realization factor (more in position, set-mining with pairs). Facing a 3-bet, we 4-bet shove with strong equity or call with pairs and premiums.

**Postflop.**

- We estimate equity by Monte Carlo against each villain's range, which comes from his preflop action this hand and his VPIP/PFR. The range is a band of the ranking, sub-sampled to at most 140 combos so the eval7 call stays at about 20 µs. On the river we use exact hand strength.
- Facing a bet, equity is discounted by raising it to the power 1 + k. k grows with bet size, the street, and whether he raised us or called earlier streets. k shrinks toward 0 for opponents with high observed postflop aggression, so maniacs get called down and passive bettors get respected.
- For calls that commit us, the required equity is the ICM break-even.
- Strong hands are value-bet at 55-90% of the pot, or shoved when the stack-to-pot ratio is low. We raise for value at an adjusted equity of 0.80 or more.
- We c-bet as preflop raiser, at a frequency set by the villain's observed fold-to-bet rate, and bluff the river only into proven folders. We bluff less into maniacs.

**Opponent model (memory).** Per seat we count hands, VPIP, PFR, preflop raises faced and folded, 3-bets, postflop bets/calls/checks/folds, and postflop bets faced and folded. All counts carry priors. They are rebuilt incrementally from `state.events` with a small per-hand context stored in memory, so re-delivered events after a failure stay consistent. The memory is a `marshal`-encoded dict of 750 bytes or less; anything unreadable resets it.

**Safety.**

- Every action is checked against `legal_actions`. Action kinds and seat statuses are normalized whether they arrive as strings or enums.
- `raise_to` always gets an int clamped to `[min, max]`.
- Any exception falls back to check, or fold if checking isn't offered.
- No state is kept on `self` or in globals between calls.

## What I tested

1. **Probe** of the state, history and event formats (stack excludes the current bet, `raise` amounts are street totals, blind order).
2. **Scenario tests** of the push and call ranges, using hand-built states. Before the fixes, 8-handed button shoves at 10bb were 15%, heads-up 10bb shoves were 100%, and the big blind called a 10bb button shove with only 7.5%. The fixes:
   - Apply the bubble tax only near the bubble.
   - Use perceived ranges that depend on position.
   - Make villains' shove-range guesses depend on depth and position.
   - Blend ICM with chip value.

   Results after the fixes:

   | Spot | Result |
   |---|---|
   | Heads-up shove at 10bb | 54% |
   | Big blind call vs a 10bb button shove, 8 players | 16% |
   | Bubble, medium stack vs a big-stack shove while a short stack exists | Calls only QQ+ |
   | Bubble big stack, shove | 54% |
3. **Fuzz test.** 4000 random states covering 2, 3, 6, 8 and 9 players, enum statuses, antes, odd payouts (`[100]`, `[65,35]`, 4 places, fractions, `None`), garbage memory and inconsistent histories, run with exceptions re-raised. Every action was legal. This found and fixed two bugs: a KeyError on seats outside the alive set, and a `dict(**{int: ...})` TypeError that had silently disabled shoving from the big blind against limpers.
4. **Mixed-field A/B harness.** This was a wrapper agent kept outside this folder. It seats a different personality in each `self` seat and logs results, using ICM of the final snapshot for survivors. The personalities:
   - this bot;
   - a chip-EV variant (no ICM);
   - a LAG chip-EV variant;
   - a push/fold-chart "pusher";
   - a nit;
   - a calling station;
   - a min-raising maniac.

   Parameter A/B runs of 500-800 tables each tried ICM weight ×0.5/×1.4/×1.7, opening ranges ×1.3, a weaker postflop discount and combinations. All differences stayed within about 2 standard errors (±0.65 to 1.0 points), so the defaults stayed as designed.
5. **Latency.** The machine was heavily shared during testing (load average 75-139), which shows up as wall-clock spikes for every bot, including the trivial built-ins in the harness. Per-decision CPU time (`thread_time`) is p50 30 µs and p99 about 100 µs. cProfile-driven fixes were a kind-normalization cache and switching memory from JSON to `marshal`, which roughly halved the median.

## Final results

Run with `.venv/bin/python lab/field_kit/play.py lab/field_bots/claude_icm ...`. Fair share is 12.5 points per seat.

| Setup | Tables | Our points | Others |
|---|---|---|---|
| Default (4 self, 2 check_or_fold, 2 min_raiser), seed 1 | 400 | **20.86 ± 0.51** (places 1/2/3: 388/343/184 of 1600) | check_or_fold 7.54, min_raiser 0.75 |
| 1 self, 4 check_or_fold, 3 min_raiser, seed 2 | 300 | **29.67 ± 1.42** (1st in 59%) | check_or_fold 12.5, min_raiser 6.78 |
| 1 self vs 7 check_or_fold, seed 5 | 100 | **50.0** (won every table) | check_or_fold 7.14 |
| 1 self vs 7 min_raiser, seed 6 | 300 | **37.45 ± 0.65** (top 3 in 299 of 300) | min_raiser 8.94 |
| Mixed-field harness (one seat each) | 1000 | **20.98 ± 0.64** | LAG-chipEV 19.6, chipEV 17.2, nit 13.7, pusher 13.0, station 1.6, maniac 0.8 |

- **Upload test:** passes (heads-up vs check-or-fold, 1 ms, no bank, 0 failures).
- **Failed decisions:** 0 of 196,981 in the default 400-table run.
- **Memory:** 749 bytes maximum.

## Known limitations / ideas

- Postflop range narrowing is a heuristic exponent, not Bayesian range filtering.
- Multiway all-in equity is approximated as (product of heads-up equities) raised to 0.85.
- There is no explicit heads-up deep strategy beyond the generic deep and push/fold logic.
- Shown cards at showdown are not used for modelling yet.

---

# Round 2 changes (claude_icm_r2)

Round 1 result: 13.43 points per table, 8th of 22. The top team scored 17.6, and fair share is 12.5. Our finishing places were 123/99/81/79/83/94/110/131: we finished last at 131 of 800 tables, more often than any other top-10 team.

## What the round-1 histories showed

I analyzed `round1/hand_history.jsonl.gz` with my own scripts: 120 tables, 12,284 of our hands.

- **Results by stage.** In bb per hand at our tables:

  | Stage | Us | Top teams |
  |---|---|---|
  | Early (6+ players) | +0.09 | +0.21 to +0.35 |
  | Mid (4-5 players) | **-0.10** | +0.18 to +0.36 |
  | Late (3 or fewer) | +0.05 | +0.27 to +0.37 |

  The winners shove 16-34% of hands in mid/late play and we were their target.
- **Opponents shove much wider than the model assumed.** The shown hands of called shoves give these hand percentiles (our ranking):

  | Shove type | Median | 75th percentile | Implied range |
  |---|---|---|---|
  | Open-shove | 20-36 | 43-53 | about 40% or wider |
  | Reshove over an open | 15 | 33-47 | about 30% |
  | 4-bet or more | 1-2 | | tight |

  The model had assumed about 24% for a 10bb open-shove and only **8%** for a reshove.
- **We folded too much to all-ins.** In mid/late play we folded to an all-in 434 times. When we did call, we won +1.85 to +2.09bb per call.
- **Flat-calling raises lost.** With 5 or fewer players, our flat calls of non-all-in raises averaged -1.84bb from the big blind and -2.55bb from other seats (150 hands). Early cold calls outside the big blind averaged -0.67bb.
- **Opening then folding to a re-raise** cost -664bb over 272 hands. The field re-raises 29% of our opens at 15-25bb and 37% below 15bb. Opens are still net positive (+0.6bb each). The wider calling ranges above mean we now call more of these reshoves.
- **Our shoves themselves were fine.** Every shove category was chip-positive. The field folds to reshoves often (only 11-13% call at 15bb or more), so I left the shove model alone.

## Changes

1. `pf_range_of`: villains' open-shove range is estimated as `(30 + 100/bb) × position` (about 40% at 10bb), blended with observed raise frequency. Reshoves over an open are estimated at `26 + 40/bb` (about 30%). The 3-bet prior went from 8% to 12%, and `shove_guess` from 0.8 to 1.0.
2. With 5 or fewer players there is no flat-calling a raise. It becomes a reshove-or-fold decision through the ICM all-in model, now used up to 25bb (was 20bb). The one exception is the big blind with a clear equity surplus.
3. Early cold calls outside the big blind need 5 points more equity.

ICM behaviour where it matters is unchanged. A medium stack on the bubble facing a big stack while a short stack exists still calls only JJ+.

Effect on scenario ranges:

| Spot | r1 | r2 |
|---|---|---|
| Big blind call vs a 10bb button shove, 8 players | 16% | 26.5% |
| Bubble short stack vs a covering shove | 4% | 9% |
| Bubble big stack with a short stack (the ICM spot above) | 1.4% | 1.8% |

## Local results (r2)

- **Upload test:** passes.
- **Fuzz test:** 4000 random states, all actions legal, worst CPU time 0.25 ms.
- **Default `play.py`:** 400 tables, seed 1. self 20.64 ± 0.51 (r1: 20.86 ± 0.51, so no change within noise). 0 illegal actions. 21 wall-clock timeouts, all from machine load (load average above 100). CPU time per decision is unchanged at p50 of about 30 µs.
- **A/B harness, r2 vs r1 at the same tables:**
  - Lineup with two wide shovers, a pusher, a chip-EV variant, a nit and a station: +0.67 (1000 tables).
  - Lineup with two of each version, two wide shovers, a LAG and a pusher: -0.59 (800 tables).

  Both are within noise. These synthetic opponents don't reproduce the field's open-then-fold-to-reshove dynamics, so the evidence for r2 is the round-1 data above, not this harness.

---

# Round 3 changes (claude_icm_r3)

Round 2 result (r2): 13.89 points per table, 8th of 22. Round 1 was 13.43, so the difference is within noise. We still finished last at 125 of 800 tables.

## What the round-2 histories showed

10,506 of our hands, analyzed with the same scripts as before.

**By stage.** In bb per hand at our tables:

| Stage | Round 1 | Round 2 |
|---|---|---|
| Mid (4-5 players) | -0.10 | 0.00 (the r2 fix worked) |
| Early (6+ players) | +0.09 | -0.17 |
| Late (3 or fewer) | +0.05 | -0.09 |

Early losses were concentrated in deep play: at 70bb or more we lost -0.36 bb per hand over 3,173 hands.

**Deep-stack showdowns lose.** At 40bb or deeper:

| Line | Hands | bb per hand |
|---|---|---|
| Called a raise preflop, went to showdown | 116 | -2.99 |
| Opened, went to showdown | 76 | -3.94 |

By made hand, at 40bb or deeper:

| Hand | Showdowns | Won | bb per hand |
|---|---|---|---|
| Two pair | 62 | 42% | -11.1 |
| Trips | 11 | 45% | -13.1 |
| Top pair | 18 | 61% | -9.0 |

**River.**

| Line | Hands | Won | Total |
|---|---|---|---|
| We called a river bet | 18 | 17% | -386bb |
| We raised the river and got called | 4 | 0% | -354bb |

**The field's late-street bets are value-heavy.** The field's postflop aggression is about 0.31. Of the river bets that reached showdown (435 hands), 63% were two pair or better and only 7% were high card. Our discount on facing bets was too gentle on the turn and river.

**Deep flat calls.** Preflop calls of a raise lost -1.06bb each (447 hands).

## Changes

1. **Postflop discount on facing a bet.** Our equity is raised to the power 1 + k before comparing with pot odds.

   | Term | r2 | r3 |
   |---|---|---|
   | Street multiplier (flop/turn/river) | 0.7 / 0.9 / 1.1 | 0.8 / 1.2 / 1.7 |
   | Base | 0.3 + 0.45 × bet/pot | 0.4 + 0.55 × bet/pot |
   | Bonus when he raised our bet | +0.35t | +0.5t |
   | Bonus per earlier call | +0.10t | +0.15t |
   | Passive-player weight t | (0.72 − aggression) / 0.45 | (0.80 − aggression) / 0.45 |

   Maniacs, with aggression above 0.8, still get no discount, so behaviour against `min_raiser` is unchanged.
2. **River value-raise bar** goes from 0.80 to 0.87 adjusted equity (multiway from 0.85 to 0.92).
3. **Deep flat calls.** Big-blind defense uses realization 0.80 (was 0.85) and hands in the top 45%. Cold calls from other seats need 8 points more equity (was 5) and hands in the top 30%.

## Local results (r3)

- **Upload test:** passes.
- **Fuzz test:** 4000 random states, all actions legal, worst CPU time 0.27 ms.
- **Default `play.py`:** 400 tables, seed 1. self 20.34 ± 0.51 (r2: 20.64 ± 0.51, within noise). 0 illegal actions. 26 wall-clock timeouts, all from machine load (load average about 150). CPU time is unchanged at p50 of about 27 µs.
- **A/B harness, r3 vs r2 at the same tables, 1000 tables each:**
  - Lineup of 2× r3, 2× r2, chip-EV, LAG, nit and wide shover: **+1.28** (r3 13.65 ± 0.40 vs r2 12.37 ± 0.39).
  - Lineup of r3, r2, chip-EV, LAG, nit, pusher, wide shover and station: **+2.24** (r3 17.08 ± 0.61 vs r2 14.84 ± 0.59).

  Unlike the round-2 A/B, both runs favour the new version. Together that is about 3 standard errors.
