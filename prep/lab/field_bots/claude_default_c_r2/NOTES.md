# claude_default_c_r2 (round 2)

Round-2 version of `claude_default_c`. The round-1 bot is unchanged in `../claude_default_c/`. The round-2 analysis and changes come first; the original round-1 notes follow below.

## Round 1 result and analysis

Round 1 (22 teams, 800 tables): **13.71 ± 0.65**, 7th of 22, against a fair share of 12.5.
- Win rate: 14.5%. The two leaders scored 17.6 with a 25.5% win rate.
- Our finishing places were spread almost evenly.
- 0 failed decisions.

I analysed the 17,289 hand histories with my own scripts:

- **Net chips by blind level:** we won chips at levels 1-5 and lost from level 6 on (60/120 and up). That's the short-stack phase.
- **Biggest leak, folding to raises:** 4,795 folds facing a single raise cost 2,055 BB in posted chips.
  - We folded to raises **83.5%** of the time, the highest in the field.
  - We 3-bet only **5%**. The two leaders 3-bet about 14% and fold about 70%.
- **Field tendencies from the histories:**
  - Opponents open about 30% of unopened pots (more from late position), sizing about 2.2-2.5 BB.
  - Their open-jams are wide: the median shown hand is around the 25th-45th percentile at every stack depth, which means ranges around top 50% or more.
  - Callers of all-ins are tight: median shown hand around the 10th-13th percentile.
- **Our responses to jams and opens:**
  - Facing a jam at 15 BB or less in the BB, we folded 80%. 15% of those folds were top-30% hands.
  - Facing opens at 30 BB or less from the SB or other seats, we folded 84-95%.
- **Cause:** the bot modelled opener ranges as PFR × 1.05 with no position adjustment, and short-stack jam ranges as about 10-25%. That made it far too tight against this field.

## Round 2 changes

1. **New per-seat stats** in memory:
   - first-to-act opportunities in unopened pots, open-raises and open-jams;
   - each seat's last known stack, used to detect jams.
   - Memory is still under 600 bytes.
2. **Opener range = smoothed open frequency × position multiplier.** The prior is 30%. The multiplier depends on how many players were left to act behind the opener: ×1.7 with one left, ×1.45 with two, down to ×0.7 from early seats.
3. **Jam range prior widened to 1.25/sqrt(stack in BB)**, scaled by the seat's observed jam rate (×0.7 to ×2) and by position. Old vs new:

   | Stack | Old | New |
   |---|---|---|
   | 10 BB | 0.25 | 0.40 |
   | 20 BB | 0.15 | 0.28 |

   Re-jams over a raise get ×0.7.

These ranges feed the existing ICM re-shove, 3-bet and all-in call logic, so the bot now re-steals and calls jams wider against this field. Everything else is unchanged.

## Round 2 local results

In my harness, r2 (A) against r1 (B) at the same tables:

| Field | r2 | r1 |
|---|---|---|
| Aggressive (lag ×2, tag, eq, maniac, pushfold), 2,000 tables | **24.2 ± 0.5** | 22.4 ± 0.5 |
| Original mixed field, 2,000 tables | **27.3 ± 0.5** | 24.4 ± 0.5 |
| Self-play, 4 r2 vs 4 r1, 1,500 tables | **15.2 ± 0.2** | 9.8 ± 0.2 |

The self-play gap is r2 exploiting r1's over-folding, the same leak the round-1 field exploited in us.

**`play.py`, 300 tables, seed 2:**
- Upload test passes: 10 decisions, 0 failed.
- self 19.01 ± 0.60, check_or_fold 10.48, min_raiser 1.50.
- Memory max 491 bytes. No illegal actions or exceptions.
- 22 decisions timed out out of 128,213. The machine's load average was 85 at the time (p99 wall time 2.6 ms vs p99 CPU 172 µs).

The bot's own CPU time per decision is p99 172 µs, max 290 µs, the same as round 1.

The slightly lower `play.py` self score than r1 (19.0 vs 20.2) comes from its four copies re-stealing against each other more. That lets check_or_fold ladder up; it isn't a loss against real opponents.

---

# Round 1 notes (claude_default_c)

An ICM-aware tight-aggressive bot for 8-seat NLHE sit-and-gos. Files:

- `agent.py`: the bot (`Agent` at module level).
- `tables.json`: preflop tables it reads at import.
- `build_tables.py`: offline generator for `tables.json` (about 5 s with eval7; not run at import).

## Approach

**Constraints first.** Each decision gets 1 ms on machines about 2.5x slower than the lab machine, plus a 100 ms bank per table. So everything expensive is precomputed. Preflop is pure table lookups. Postflop makes one or two eval7 (C) equity calls per decision, against small sampled ranges. Measured CPU time per decision on this machine:

| Street | p50 | p99 | max |
|---|---|---|---|
| Preflop | 39 µs | 104 µs | about 200 µs |
| Postflop | about 100 µs | 215 µs | 270 µs |

The worst case is therefore about 0.7 ms on the tournament machines. Postflop also has a wall-clock guard: it stops evaluating further villains after 0.45 ms, or 0.2 ms when the time bank is under 25 ms. Any exception falls back to a safe legal action (check, else fold). Every raise is clamped to an int inside `min_amount..max_amount`. Action kinds and statuses are normalised whether the SDK gives Enums or strings.

**Preflop tables.** The 169 hand classes have:
- equity vs 1 and vs 3 random hands;
- a shove ranking (by HU equity);
- an open ranking (a blend that values multiway playability);
- `eq_top[h][p]`: equity of class h against the top-p% range, on a 20-point grid.

**Preflop play.**
- **Push/fold zone** (effective stack ≤ 8.5 BB, or ≤ 11 BB heads-up): computes the ICM $EV of jamming vs folding. Each player behind is modelled separately:
  - The equity they need, given pot odds plus an ICM/risk tightening and a looseness adjustment from their observed VPIP.
  - Their calling width: hands with that much equity against my perceived jamming range, which depends on the effective stack.
  - That width conditioned on the range they've already shown this hand (raiser, limper or unknown).
  - My equity vs their calling range.
- **Deeper, unopened:** opens by position (players left to act), widened against tight blinds. Size is 2.5 BB deep and about 2.2 BB mid-stack. Limpers get iso-raised or overlimped, and the SB completes cheaply when deep.
- **Facing a raise:** the raiser's range comes from their PFR (open) or re-raise frequency (3-bet+), adjusted for raise size.
  - With 30 BB or less: re-jam when shove EV beats folding, otherwise call only cheaply.
  - Deep: 3-bet for value (equity ≥ 0.60 vs their range, or premium hands), set-mine pairs, and call when equity × realization beats pot odds.
  - Against all-ins: an ICM call/fold decision, using Malmuth-Harville on actual stacks and `config.payouts`.
- **ICM:** exact for up to 4 paid places. Deeper payout structures use a stack-skewed approximation for the tail.

**Postflop.**
- **Villain ranges.** Each villain's range starts from their preflop action (raiser, 3-bettor, caller, limper or checked BB) and their smoothed VPIP/PFR/re-raise stats.
- **Narrowing.** The range is then narrowed by their postflop actions:
  - Each bet, raise or call keeps the top fraction of the range by current hand value.
  - The rest is kept at a "bluff weight" learned from their aggression frequency.
- **Equity.** About 110 combos are sampled from that range. The flop and turn use eval7 Monte Carlo; the river is computed exactly. In multiway pots the per-villain equities are combined.
- **Decisions.**
  - Value-bet above an equity threshold for the street (0.50, 0.53 or 0.55), sized 50-90% of the pot, and bigger against players who rarely fold.
  - Bluff or semi-bluff only when a fold-equity EV check (using their fold-to-bet stat) beats checking.
  - Raise above 0.72 equity (0.78 on the river), going all-in when stacks are shallow.
  - Call when equity beats pot odds plus a small margin. For calls that commit a large part of the stack, ICM sets the required equity.

**Memory.** Per-seat counters (hands, VPIP, PFR, re-raise and its opportunities, postflop aggression/passivity, folds to bets, bets faced) are updated from `state.events` each turn. They're stored as compact JSON of about 330 bytes, well under the free 16 KB. Nothing carries across tables.

## Testing

1. **`play.py`** (upload test plus 8-seat tables against `check_or_fold` and `min_raiser`).
2. **My own independent sit-and-go engine**, kept in the session scratchpad and not shipped. It's needed because `play.py`'s opponents are trivial.
   - Same rules: blinds schedule, 20 hands per level, 250-hand cap with an ICM split, strict legality, events/memory semantics.
   - Seven opponent archetypes modelled on typical quick-build bots: Chen-formula preflop and equity-vs-random-hands postflop. They are an equity bot, a TAG, a LAG, a calling station, a nit-shover, a maniac and a push/fold bot.
   - Versions were compared A/B at the same tables (1,000-2,500 tables per test). Self-play fields (4 new vs 4 old) checked that changes aren't just exploits of weak bots.
3. **Config stress test:** winner-take-all, 7-place payouts, 6, 9 and 2 seats, 5,000-chip stacks. No exceptions and 0 failed decisions in any configuration. The bot scored 1.5-3.7x fair share throughout.

Iterations, all in my harness, with points per table and fair share 12.5:

| Change | Mixed field | Self-play |
|---|---|---|
| v1 baseline (first working version) | 20.0 | 10.85 |
| v2: shove EV conditions callers on the range they've already shown (it was treating a raiser's call range as independent of their raise range); tighter postflop raise narrowing | +7.3 over v1 | 14.15 vs 10.85 (v1) |
| Tuning: push/fold at 8.5/11 BB (down from 12.5/15), thinner value thresholds, opens ×1.35 | +3.8 / +1.7 over v2 | neutral |
| v3: perceived jam range uses the effective stack, not my own stack; folding to the pot now assigns the pot to its likely winner (it vanished from the ICM before, which made folding look too good); SB completes instead of folding in push/fold mode | +3.3 / +0.5 over v2 | +0.1 |
| v4: ICM tail for deep payouts; cached kind normalisation; station value-size bonus (+0.2 pot when their fold-to-bet < 0.33) | neutral | neutral |

Variants that didn't help (within noise): a push threshold of 16 BB (worse), raise thresholds ±0.06, and more or less bluffing.

**Final, in my harness:**
- Mixed field (A, eq, tag, lag, station, nit, maniac, pushfold): **34.5 ± 0.5** points per table, which is 2.8x fair share.
- Final vs v1 at the same tables: 29.4 vs 19.4.
- 4 final vs 4 v1: 14.1 vs 10.9.

## Final `play.py` results

`.venv/bin/python lab/field_kit/play.py lab/field_bots/claude_default_c --tables 300 --seed 2`

- **Upload test:** pass. 10 decisions, 0 failed, no crash.
- **self (4 seats): 20.18 ± 0.58** points per table, against a fair share of 12.5.
  - Finishing places 1 to 8: [280, 248, 139, 51, 127, 202, 150, 3].
- **check_or_fold:** 7.97. **min_raiser:** 1.67.
- 135,216 decisions, **0 failed**. Latency p50 36 µs, p99 174 µs. Memory max 333 bytes.

An earlier 500-table run (seed 1) gave self 20.55 ± 0.45. It also had 6 timeouts out of 233,425 decisions. The machine's load average was 126-180 at the time (other jobs), with wall-clock stalls of up to 156 ms. The bot's own CPU time never exceeded 0.27 ms, so these were scheduling stalls, not compute. The rerun above had none.

## Known limitations / ideas

- Multiway postflop equity is a heuristic combination of separate heads-up equities.
- The preflop jam model assumes at most one caller.
- Postflop range narrowing uses hand value on the current board, so draws only enter through the bluff weight.
- Opponent stats start from priors and need about 10-20 hands per seat to matter.
- The harness opponents are my guess at the field. Real AI-built bots may be stronger and tighter, which is why each change was also checked in self-play fields.
