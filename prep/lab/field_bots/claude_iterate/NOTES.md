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
