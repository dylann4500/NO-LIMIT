# claude_iterate: notes

## Approach

`agent.py` with `preflop.json`. The JSON holds precomputed tables made by `tools/precompute.py` using eval7.

- **Opponent model (in `memory`).** Each seat gets counters, updated from `state.events`: VPIP, PFR, open-raise
  rate, fold/3-bet when facing a raise, how often it continues against big raises or shoves, postflop bet,
  raise and fold-to-bet rates. Rates are smoothed toward priors for a typical tight-aggressive bot, so early
  hands get sensible defaults. Memory is a `marshal`'d dict of about 1 KB. A bad or empty memory resets to a
  fresh state.
- **Ranges.** An opponent's range in a hand is the top-x% of hands, with x taken from its observed frequency
  for the action it took (open, 3-bet, 4-bet, call, limp, check). Preflop equity vs those ranges comes from
  the table of each of the 169 hand classes against top-p% ranges, interpolated.
- **Preflop.**
  - Unopened pot: the open-raise decision is an EV model. It uses each player still to act and their modelled
    fold, call and 3-bet rates, our equity against their continuing range, and a realization factor for
    position. It steals a lot from players who fold too much and tightens against loose ones.
  - At 14 BB or less: shove or fold, scored with ICM. Each opponent gets a modelled calling probability and
    calling range.
  - Facing raises: all-in or near-all-in spots use ICM EV of calling vs folding (or re-shoving). Other spots
    use 3-bet, call or fold by equity vs range, with pot odds, realization and set-mining implied odds.
  - A raiser's chance of continuing vs our shove is max(observed rate, top ~7% / its range width). This
    stops bluff-shoves into narrow 3-bet ranges.
- **Postflop.**
  - eval7 Monte Carlo equity, 300 iterations heads-up and 220 multiway, against each opponent's estimated
    range. Ranges are pre-built `HandRange`s subsampled to 240 combos, since eval7's per-call range
    conversion is the main cost.
  - Earlier-street bets and calls narrow the range.
  - No bet to face: we compare EV(check) with EV(bet) at 1/3, 1/2, 3/4 and 1x pot, or all-in when that is at
    most 1.5x pot. Each bet's EV uses the modelled fold probability (which depends on bet size), equity vs the
    calling part of the range, and a raise-back risk.
  - Facing a bet: we compare EV of fold, call and raise. The bettor's range is narrowed by how often it bets,
    with bet size taken into account. Big all-in calls are scored with ICM.
- **ICM.** We compute our own Malmuth-Harville value for the top 3 places from the table's `payouts`, in about
  10 µs per call. It drives all-in decisions directly. Everywhere else it gives a loss/gain ratio λ ≥ 1 that
  scales chip losses, so we take less risk near the money.
- **Safety.**
  - Every action goes through `finalize`, which only returns offered kinds and int raise totals clamped to
    `min_amount..max_amount`. Sizes within 10% of all-in become all-in.
  - Any exception returns a legal check or fold and keeps the old memory.
  - Action kinds and statuses are normalised, whether they arrive as enums or strings.
  - When `state.time_bank_ms` falls below 60, Monte Carlo iterations drop to half, and below 20 to a quarter.
  - Tables load at import, followed by `gc.freeze()`.

## Testing

- `lab/field_kit/play.py` in several seat mixes: the upload test, legality and latency.
- `tools/sim.py` and `tools/arena.py` are my own 8-max sit-and-go engine on the fake SDK's classes. They play
  against plausible quickly-built bots from `tools/opponents.py`: TAG equity bot, LAG, calling station,
  pusher, nit and maniac, plus check_or_fold and min_raiser stand-ins. The arena can also seat older
  snapshots of this bot for A/B tests.
- `tools/losses.py` prints traced decisions from hands where we busted early. `tools/timing.py` measures CPU
  time per decision with `thread_time`, because the shared lab machine had a load average of 25 to 76 during
  testing, which made wall-clock numbers noisy.

### Iterations (arena: one bot, 7 opponents, mean points; fair share 12.5)
1. **v1 (EV framework).** 24.8 in the mixed field. Vs 7 of each type: tag 27.4, lag 28.5, station 30.9,
   pusher 39.3, nit 31.2, maniac 32.9. Leaks seen in `losses.py`: overbet all-in shoves with one pair,
   4-bet bluff-shoves with trash into nit 3-bets, a "top 3%" premium shortcut that included 99, and a 5-bet
   shove range estimated too wide.
2. **v2 (fixes for those leaks).** Beat v1 24.5 vs 20.9 at the same tables (700 tables). Vs 7 nits: 31.2 → 35.9.
3. **v3 (current).** Changes:
   - range narrowing from earlier-street aggression and calls
   - all-in raises capped unless equity is very high
   - fold-to-raise estimate scaled by how strong the bettor's range is
   - no bluff-raises below 40% equity unless the bettor folds a lot
   - lower realization when calling 3-bets and 4-bets
   - raiser continue probability = max(stat, range-based)

   Results with one bot per table (600 tables): mixed field 27.7 → **31.0**; tight field
   (3 tag, 2 nit, 2 pusher) 31.7 → **33.8**. With v1, v2 and v3 all at the same table, v2 and v3 tied
   within noise (23.8 vs 23.2, SE 0.8); v3 busted early less often.

## Final `play.py` results (v3, 200 tables each)

| seats | self mean points (SE) | places 1–8 | failed |
|---|---|---|---|
| default (4 self, 2 check_or_fold, 2 min_raiser) | **23.38** (0.60), max possible ≈ 25 | 197/191/156/90/24/71/69/2 | 0 |
| 1 self + 7 min_raiser | **39.14** (0.75) | 94/105/0/1/0/0/0/0 | 0 |
| 8 self | 12.5 (by symmetry) | | 2 timeouts in 326k decisions |
| 1 self + 7 check_or_fold (v1) | 49.98 | | 0 |

- **Upload test:** passed every time, with 0 failed decisions.
- **Latency:** CPU time per decision is p50 ≈ 35 µs, p99 ≈ 130 µs and max ≈ 275 µs. At 2.5x slower that is
  under 0.7 ms against the 1 ms limit. The slowest spots are preflop all-in decisions that run several ICM
  evaluations.
- **Wall-clock spikes.** The wall-clock p99.9 and max figures in `play.py`, and the 2 timeouts in 8-self, came
  from machine contention. The load average was 76 at the time, with other processes using the CPU. On an
  idle machine, v1's wall-clock max was 0.57 ms with no decision over 1 ms.

## Known limitations / ideas
- Multiway equity is a product of heads-up equities, which is approximate.
- Postflop ranges are preflop top-x% ranges with polar adjustments, not real range construction.
- No antes are modelled. They are handled implicitly through `pot`.
- No mixed or balanced strategy. The bot is exploit-oriented by design, with priors that assume a
  tight-aggressive field.

---

# Round 2 version (claude_iterate_r2)

## What round 1 showed
`tools/analyze*.py` analyses `../claude_iterate/round1/hand_history.jsonl.gz`.

**Result:** 10.90 points (fair share 12.5), 16th of 22. Places 33/134/154/103/100/86/94/96: we made the top 3
40% of the time but won only 4%. The leaders won 25%.

**Where the chips went (12,180 hands):**
- Losses came mainly at high blinds: −55k at 150/300 and −48k at 250/500. Early levels were slightly positive.
- Opening and then folding to a re-raise cost −78k over 250 hands. 164 of those re-raises were shoves, at a
  median of 16 BB effective. We were folding far too often to wide re-shoves after putting in 2.1 BB.
- Preflop all-in showdowns cost −43k over 176 hands. Our shoves had a median hand percentile of 0.26; the
  hands that called had a median of 0.10. Players faced with our shove called about 27% of the time, more
  than our model assumed.

**Field tendencies (from showdowns):**
- Open-shoves are wide: shown median hand percentile 0.25 at ≤12 BB, 0.30 at 12–25 BB, 0.44 deeper.
- Re-shoves at 12–25 BB: median 0.06 (p75 0.27). Above 25 BB: median 0.01.
- Facing a postflop bet, the field folds 54% of the time and raises 6%. By bet size: 37% folds to bets under
  0.4 pot, 56% to about half pot, 67% to about pot, 72% to overbets.

**Style of the winners:**
- The top teams ("ours", claude_default_b, claude_exploit) bet or raise in 53–64% of their postflop actions.
  We did so in 26%.
- With a mostly passive field that folds a lot, postflop aggression is what wins.

## Changes
1. **Ranges for open-shoves and re-shoves now come from round-1 data.**
   - Open-shove priors: 0.42, 0.32 or 0.28 of hands, depending on the shover's depth in BB.
   - Re-shove priors: 0.30, 0.14 or 0.05.
   - Before, a re-shove was treated as a 7% 3-bet range. We now call re-shoves after opening at the right
     price, and call wide open-shoves wider.
2. **Opponents are assumed to call our shoves more often.** The prior calling probability is now
   0.3·VPIP + 0.8·PFR, up from 0.25 and 0.6. This tightens our light shoves.
3. **Shove-or-fold now starts at 15 BB** (was 14).
4. **ICM risk aversion scales with how much of our stack is at risk.** The full factor λ applies only to
   all-in-sized risks. Before, every small bet or call carried the all-in penalty, which made us passive
   postflop.
5. **Postflop priors match the field:** fold-to-bet 0.58 at 2/3 pot (was 0.45), raise-back 0.06 (was 0.10),
   fold-to-raise base 0.54. As a result, the EV model bets and c-bets far more often.

## Local results (r2)
- **Head-to-head with the round-1 bot** at the same tables (600 tables; field: 2 fpush, 2 tag, lag, nit):
  r2 scored **24.89 ± 0.83**, round 1 scored 21.79 ± 0.83.
  - `fpush` is a new test opponent: push or fold with a wide range at ≤15 BB, like the round-1 field.
  - Against my older test opponents alone, the changes made no measurable difference (27.5 vs 27.6).
    Those opponents fold less and shove less than the real field did.
- **`play.py` (100 tables):**
  - Upload test passed.
  - Default mix: self 22.6 ± 0.9.
  - 0 illegal actions.
- **Timeouts:** `play.py` reported 25 timeouts (default mix) and 14 (8-self). All came from wall-clock stalls
  while the load average was 43–83 on 15 cores. CPU time per decision measured with `thread_time`:
  p50 35 µs, p99 142 µs, p99.9 193 µs, max 381 µs. At 2.5x slower the worst single decision is about
  0.95 ms, so the per-table time bank has to cover rare overruns.

---

# Round 3 version (claude_iterate_r3)

## What round 2 showed
`tools/analyze7-9.py` and the earlier scripts, run on `../claude_iterate_r2/round2/hand_history.jsonl.gz`.

**Result:** 11.16 points, up from 10.90. Win rate was still only 4.6%; top 3 was 39%. Places 37/156/120/…:
we finished 2nd 156 times.

**Heads-up was the leak.** In the sampled histories we reached heads-up 31 times and won only 4. We started
those matches with 39% of the chips on average and lost 0.25 BB per hand over 974 heads-up hands.
- In the big blind we folded to the button's raise 255 times, at −1 BB each.
- Button players in this field raise first-in 71% of the time heads-up, 54% three-handed, 37% at 4–5 players
  and 26% at 6–8. Our ranges came from stats collected mostly at a full table, so we read heads-up raises as
  a roughly 20% range and over-folded.
- For the same reason, our re-shoves with junk (85o, 32o) assumed too much fold equity.

**Postflop:** the field's fold-to-bet rate barely changes with table size (49–54%), so the postflop priors
stay.

## Changes
1. **Open-raise stats are now kept separately by table size**, in four buckets: 6+ players, 4–5, 3 and 2.
   The number of players comes from the `stack` events at the end of the previous hand. Each bucket's
   prior is half the field's first-in raise frequency for that size and half the player's full-table rate
   adjusted to the current size. In short-handed play, an opener's range is that measured rate.
2. **We assume opponents call our shoves more often in short-handed play.** The X/range rule for raisers
   uses a top-X% figure that grows as the table shrinks (by a square-root factor).
3. **Dropped a broader version of change 1.** It widened every range by table size with a fixed
   formula and tested clearly worse: 20.1 vs 25.1 against r2 in the field arena, and heads-up r2 won 467–133.
   Ranges need to be measured per opponent, not assumed.

## Local results (r3 vs r2 in the same tables)
- Field arena (fpush ×2, tag ×2, lag, nit), 600 tables: r3 **23.17 ± 0.84**, r2 21.96 ± 0.82. That is a gain
  within noise.
- **Heads-up r3 vs r2, 600 matches: r3 won 338–262 (56%).** This is the target leak and the gain is
  significant.
- `play.py`, default mix, 100 tables: self 23.05 ± 0.86, with no illegal actions. It reported 107 timeouts,
  and on that run the upload test hit 2 timeouts in 10 decisions and failed. The machine's load average was
  129 on 15 cores at the time. CPU time per decision stayed low: p50 39 µs, p99.9 218 µs, max 272 µs.
- Five reruns of the upload test straight afterwards all passed with 0 failures.
