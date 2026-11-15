# What changed in the bundle on 15 November (morning of the Finals)

Two sets of changes, both approved by Dylan and Samuel. The script tests pass after each (228 of 228). To see every
changed line: `git diff ca2cccd..HEAD -- finals_pack ':!finals_pack/prep'` in the team repo.

## Zips

| File (in `nolimit-live/`) | What it is |
|---|---|
| `avalon-finals-starting-bundle.zip` (also in `~/Downloads`) | Everything on this page |
| `avalon-finals-starting-bundle-b1b6.zip` | Set 1 only |
| `avalon-finals-starting-bundle-saturday.zip` | Saturday's bundle, the one the full rehearsal ran on |

If anything on this page looks wrong on the morning, use an earlier zip: each is complete by itself.

## Set 1, applied 03:55: the six fixes from the rehearsal review

Listed with their reasons in `prep/REHEARSAL_REVIEW_15NOV.md`, section 3B. In short:

1. The decision rules no longer say "(the last-rounds bar)" in the no-practice-day section, and that section states
   it does not apply on a day with practice rounds.
2. Hard rule 1: failed decisions are judged against the kit's `check_or_fold` bot in the same run, not against zero.
3. BUILDER puts an upload request in a message of its own.
4. RESEARCH puts BUILDER's question to Samuel in BUILDER's words.
5. The tester's heads-up run uses the real table's settings, not a two-seat table.
6. `START.md`: the starters you pasted for the rehearsal, with the decision rules excepted from "suggestions" and
   subagents on Opus at high effort; `/compact` when each scored round starts; roles stay background subagents.

## Set 2, applied 04:25: four items from the overnight analysis

### 2a. Fingerprinting (`strategy/FINGERPRINTING.md`, with `scout.md`, `stylist.md`, `PLAN.md` and the clock's text brought into line)

- **No accuracy or confidence bar.** Section 2's numbers are "reported, not gates". The 55% field-wide bar, the 50%
  per-team recall bar and the 0.6 confidence bar are gone. Reason: in play, bars of 0.4, 0.6 and 0.8 cost 0.3, 1.0
  and 1.4 points a table, and the old rule did worse than not using identity at all.
- **The response is weighted by confidence and blended with the seat's own actions.** The page gives the formula and
  starting strengths per spot (10 when unsure), and says to count in context.
- **Changes go through an expected-value comparison** with a margin of about a quarter of a big blind, from hand 1.
- **Two profiles per team and an unknown class** built from the field's rates. A seat is also scored on its last 20
  hands, to catch a mid-table change.
- **A direction test before any release with it on**, because a reversed sign costs 1 to 2 points a table and no
  accuracy number shows it.
- **It is written as an option in two steps**, after the base bot is right: seat counts with the field's rates
  first, identity once two rounds of files exist. BUILDER and Dylan decide whether it earns its place.
- **Naive Bayes stays**, without the chip-rounding token. No trained model beat it.

**One choice I made inside what you agreed:** the cap on how far a profile may shift a frequency is 20 points (it was
10). The play test found a 10-point cap cost 0.3 to 0.6 points a table and recommended none, or none tighter than
20; the value analysis found a cap halves the damage of a sign error. Twenty is the loosest value both support. Say
if you want 10 back, or none.

**Not changed:** section 4 (opponents adapting within a table), section 5 (have they profiled us) and section 6
(disguise). The reaction rules found overnight (re-raising a seat more after it folds) are not in the bundle yet:
that waits for the ladder test and your decision.

### 2b. The test rig on many-core Modal containers (`tester.md`, `CLAUDE.md` hard rule 8, one phrase in `RESEARCH.md`)

- Ask for 32 cores a container and keep a pool of 32 workers alive across calls. Many small calls, a short shutdown
  window, no 64-core containers, never leave big containers warm.
- A 20,000-table paired run is then about half a minute (error about ±0.11 points a table); use it for a verdict that
  decides a scored round.
- More tables remove noise, not bias: between designs the practice round stays the judge.
- The container caps are unchanged (40 for the rig, 20 for theory, 20 shared). Saturday's one-core figures stay in
  the file as the fallback. Nothing above 15 containers was tested.

### 2c. Memory (`CLAUDE.md`, the laptop-load paragraph)

Read a hand file as a stream, one table at a time; never a whole round in memory and never in several processes at
once. The laptop has 24 GB.

### 2d. Timeouts (`CLAUDE.md` section 8, `platform.md`)

- One timeout empties a table's bank, and after that every slow decision at that table fails.
- Never switch to a weaker fallback on the bank's level alone; if there is a fallback, start it on failures actually
  seen. In the paired test a bank-triggered fallback lost 3.2 points at every table with one timeout.
- A scattered failed decision cost about 0.25 points at its table.
- The rehearsal kit allowed 2 ms of delivery grace on top of 1 ms; the real platform's is unknown, so plan for 1 ms.

## Not applied

- Reaction rules and the fold-then-punish play; where to draw the line between heuristics and the combined method
  (both wait for the ladder test).
- A probe arm in practice rounds (no decision).
- The watcher printing "None" as the rank before round 1 (cosmetic).
- The twelve reviewer proposals in section 3C of the rehearsal review.

## What none of this has had

A timed rehearsal. Saturday's bundle did. Set 2 is written as options and facts for the sessions to use, and the
core workflow (who does what, when, and how a bot is chosen) is as rehearsed apart from the six fixes in set 1.
