# claude_aggro: notes

Team brief: steal blinds, apply pressure, punish over-folding, but don't spew against strong hands.

Files: `agent.py` (the bot, `Agent` at module level) and `pf.json` (preflop tables it reads at import). Python
standard library plus `eval7` only.

## Approach

**Opponent model.** Each table's stats travel in `memory` (marshal, about 1.7 KB; corrupt or unknown memory is
reset). They are rebuilt from `state.events` with a small per-hand tracker. Stats kept per seat:

- Preflop: VPIP, PFR, open rate when first in, fold to a single raise, 3-bet rate, fold to 3-bet, open-jam rate.
- Postflop: bet rate, fold to bet, raise vs bet, fold to a re-raise.

Every frequency is a Bayesian estimate with a prior, so the bot plays sensibly from hand 1 and adapts within a
few orbits.

**Preflop** (tables precomputed offline: equity of all 169 classes against "top x%" ranges and against 1 to 7
random hands).

- Unopened pot: wide, position-based opening ranges by players left behind (SB 60%, BTN 50%, CO 36% ... UTG 15%).
  They widen automatically when the players behind fold to raises more often than the prior. Against
  check/fold-style blinds the bot opens any two.
- Short (13.5 BB or less): push/fold, with a jam range by stack depth and players behind, also widened by
  observed fold rates.
- Facing a raise: the raiser's range comes from his own observed open, 3-bet and jam frequencies. The bot
  then decides with equity against that range:
  - Value 3-bet or jam when equity against his range is at least 0.58.
  - Bluff 3-bet (suited or ace-high hands) against wide openers who fold to 3-bets at least 50% of the time.
  - Call when realised equity beats the price.
  - In commit spots (short, or the price is a large part of the stack), choose between jam and fold with an
    ICM jam-EV.
- All-in calls use ICM (Malmuth-Harville over the remaining paid places) blended with chip EV. Pot odds use
  the matched pot only; chips above my stack are excluded.

**Postflop.**

- **Villain range.** Start from the slice of preflop hands his preflop line implies. Narrow it by his
  postflop line using his own frequencies: a bet keeps about his bet rate, a raise keeps about his raise rate
  (a re-raise on the same street much less), and a call removes the bottom. The kept part is the strongest
  share by current hand value, plus a small random "draws and bluffs" share sized by his aggression.
- **Equity.** eval7 Monte Carlo against the sampled range (exact count on the river). Multiway pots multiply
  per-villain equities. A floor stops near-nut hands being treated as dead when the range gets very narrow.
- **Choosing the action.** Every option is scored with a fold-equity EV model:
  - check vs bet 33/60% pot on the flop, 50/80% on the turn, 50/85% on the river, or jam when the
    stack-to-pot ratio is low;
  - fold vs call vs raise when facing a bet.
- **How fold equity is set.** It comes from the opponent's fold-to-bet stat, decays sharply once he has
  already called this hand, and the equity "when called" is computed against the top of his range for that
  size.
- **The result.**
  - Bluffs and c-bets appear exactly where opponents over-fold.
  - Against stations it value-bets and stops bluffing.
  - Against passive players who suddenly raise, it folds medium hands.
  - Re-raises postflop are value-only, and semi-bluff raises are allowed only on the flop.

**Time safety** (1 ms per decision, real machines about 2.5x slower).

- Tables load and a warm-up decision runs at import, and `gc.freeze()` is called there too.
- Wall-clock guards skip extra multiway or "when called" Monte Carlo passes after 45% and 60% of the decision
  budget.
- A "lite" mode (small samples, 60 iterations) switches on whenever the table's time bank drops below 40%.
- Any exception falls back to check or fold. Raise totals are always clamped ints inside
  `min_amount..max_amount`.

## Testing

1. **`play.py` (lab simulator).** Upload test, plus seat mixes: default, 1 self, all self, 6-max, 10 seats,
   heads-up.
2. **Own SNG engine.** I wrote my own 8-seat sit-and-go engine (same State/Event API, side pots, rising blinds,
   ICM at the hand cap) because play.py only offers check_or_fold and min_raiser. It ran the bot against five
   archetypes of "typical AI bots":
   - TAG equity bot,
   - nit,
   - LAG with bluffs,
   - calling station,
   - push/fold jammer.

   Runs were 1,000 to 2,000 tables in parallel. The harness and the offline `pf.json` precompute script live in
   the session scratchpad and are not shipped.
3. **Big-loss hand logs.** I read every hand where the bot lost at least 40% of its stack, which drove the fixes
   below.

Leaks found and fixed (scores are archetype-mix mean points; fair share is 12.5):

| Change | Effect |
|---|---|
| Pot odds used the full pot when a jam exceeded my stack (J2o called a 2000 jam with 300 chips) | Effective pot |
| Fold equity for raising a bettor used his generic fold-to-bet rate, so it raised and re-raised nits and stations off one pair | Fold-to-re-raise stat, value-only re-raises: 28.1 to 31.0 |
| A raise kept about 40% of the villain's range | Tighter narrowing, re-raises much tighter: 31.5 to 33.4 |
| Folded a straight to a river raise getting 11:1 (range sample too small) | Bigger sample when narrow, near-nut equity floor |
| Overbet thin value with one equity number for every size | Per-size "equity when called" |
| Double-barrels and raises into players who had already called | Fold equity x0.65 per prior call, flop-only semi-bluff raises: 31.9 to 33.8 |
| Decision CPU too high (about 150 attribute calls per decision, JSON memory) | Fast paths and marshal: flop p50 158 to 124 us |

**Parameter A/B (rejected, all within noise or worse).** Each was tested on 1,500 to 2,000 tables:

- open ranges x0.8 and x1.2;
- push ranges x0.8 and x1.25;
- fold-rate priors;
- bet sizes x0.8 and x1.25;
- check realisation;
- 3-bet value threshold;
- looser preflop calling (clearly worse, 30.9);
- extra all-in call margin;
- full-ICM weight.

The defaults in `TUNE` are the submitted values. The `AGGRO_TUNE` environment override exists only for these
local tests.

**Process note.** The session scratchpad turned out to be shared with other agents. Two of my snapshot
folders (`v2`, `v3`) were overwritten by another team's bot, so a few early A/B runs were against foreign code.
I discarded those results, never read that code beyond one file header, and moved my work to a private folder.
All numbers in this file come from my own code.

## Final results

**`play.py`** (`.venv/bin/python lab/field_kit/play.py lab/field_bots/claude_aggro ...`):

| Seats | Tables | self mean points (SE) | Notes |
|---|---|---|---|
| default 4 self / 2 check_or_fold / 2 min_raiser | 500 | **22.15 (0.44)**; cof 5.55, minr 0.15 | places 1-8: 497/467/272/78/174/343/165/4 |
| same, seed 7 | 400 | **21.91 (0.50)** | 0 failed decisions of 271,069 |
| 1 self + 4 cof + 3 minr | 200 | **33.25 (1.67)** | |
| 6-max (3 self) | 100 | 26.6 (1.13) | |
| 10 seats (4 self) | 60 | 21.04 (1.31) | |
| heads-up vs min_raiser | 100 | 46.8 (0.73) | wins 84% |

- Upload test: passes every run (11 to 13 decisions, 0 failed).
- One run of 500 tables had a single timeout. It happened when the machine's load average was about 90 (other
  jobs) and the time bank had drained from wall-clock overruns, not from slow code. The lite mode was added
  afterwards; later runs had 0 failures.

**Own engine, 1 claude_aggro + 7 archetypes:**

| Field | Mean points (SE) |
|---|---|
| mixed archetypes | 32.5 to 33.8 (0.5) |
| tight field (TAG / nit) | 33.5 (0.7) |
| loose field (LAG / station / jammer) | 32.7 (0.6) |
| 7 x TAG | 33.8 |
| 7 x nit | 35.1 |
| 7 x LAG | 29.9 |
| 7 x station | 40.3 |
| 7 x jammer | 29.7 |
| 3 claude_aggro + 5 archetypes (per seat) | 21.5 (0.4) |
| emulating 2.5x slower machines (guards fire 2.5x earlier) | 32.9 (0.5) |

Finishing places against the mix: about 56% first, 7% second, 7% third, 30% out of the money. The bot plays to
win, not to min-cash.

**CPU time per decision on this machine** (under heavy background load), in microseconds:

| Street | p50 | p99 | p99.9 |
|---|---|---|---|
| preflop | 40 | 99 | 150 |
| flop | 125 | 212 | 260 |
| turn | 119 | 198 | 241 |
| river | 101 | 182 | 236 |

At 2.5x that is about 0.65 ms at flop p99.9, and the guards cap the tail. Memory stays at 1.7 KB at most.

## Known limits and ideas

- Postflop strength ordering ignores draws, apart from the random share. Multiway equity is a product
  approximation.
- No showdown-based learning: shown cards are not yet used to calibrate ranges.
- High variance by design: about 30% of tables end out of the money. Bubble-specific tightening for medium
  stacks would be the next thing to try.
