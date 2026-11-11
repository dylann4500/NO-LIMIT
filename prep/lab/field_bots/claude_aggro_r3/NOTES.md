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

## Round 2 changes (claude_aggro_r2)

Round 1: **12.71 ± 0.66 points** (9th of 22, fair share 12.5). Places 1-8: 115/98/74/90/84/102/114/123, so 8th
was our most common finish. Win 14.4%, top 3 35.9%, 0 failed decisions. I analysed the 17,192 hands in
`claude_aggro/round1/hand_history.jsonl.gz` with my own scripts, and replayed every table through the bot's
own stat tracker to measure the field.

What cost points:

1. **Busting preflop with weak hands.** 97 of our 104 busts were preflop all-ins at about 7 to 14 big blinds.
   Many were re-jams over an open with bottom-of-range hands (42o, 74o, T2o, 52o, 92o, 65o). The field called
   our re-jams 30-39% of the time, while the model assumed about 23%. Re-jams with the bottom 40% of hands
   lost 0.55 BB per hand; re-jams with better hands won 1.0-1.8 BB.
2. **Wide preflop defence, then over-folding postflop.** We folded only 63% to a single raise (the field folds
   74.5%). After that we folded to 62% of flop bets, 80% of turn bets and 87% of river bets.
   - Flop calls that later folded lost 4.1 BB each.
   - The field bets about 40% when checked to, and the top two bots bet about 77%. Our model read each bet
     as too strong a range.
3. Steals were fine: the field folds to a raise 74.5% of the time, matching the prior. Opens with top-15%
   hands made +1.17 BB per hand and wider opens broke even, so open ranges are unchanged.

Changes (no new computation; CPU per decision is unchanged at flop p99.9 about 0.29 ms):

| Change | Before → after | Reason |
|---|---|---|
| Preflop call realisation (OOP / IP) | 0.76/0.92 → 0.70/0.86 | Defend about as tightly as the field |
| Fold equity of a re-jam | callers continue with top 7% → top 11% (absolute) | Matches the observed ~35% call rate |
| Re-jam hand filter | none → only top 55% of hands, unless 8 BB or less | Removes the trash re-jams behind most busts |
| Aggression prior | 0.30 → 0.40 | Field average |
| Range kept after a villain's bet | af×1.05+0.06 (min 0.15) → af×1.2+0.12 (min 0.25) | Stop over-folding to bets |
| Range kept after a villain's call | 1−0.8·fold rate (min 0.3) → 1−0.6·fold rate (min 0.4) | Same |

Local results for r2:
- `play.py` default mix, 300 tables: self **21.72 ± 0.58** (round 1 bot: 21.9-22.2).
- Upload test passes; 0 illegal actions.
- That run logged timeouts, but the machine's load average was 40-80 at the time. The unchanged round-1 bot
  also timed out in the same conditions (wall-clock stalls up to 167 ms), while r2's CPU time per decision is
  unchanged.

Own engine:

| Setup | r2 | r1 |
|---|---|---|
| 4 r2 vs 4 r1, 3,200 seats each | **13.14 ± 0.32** | 11.86 ± 0.31 |
| 2 r2 + 2 r1 + 4 archetypes | **19.53 ± 0.51** | 17.77 ± 0.50 |
| 1 bot vs archetype mix | 31.8 ± 0.7 | 32-33 |

## Round 3 changes (claude_aggro_r3)

Round 2: **13.61 ± 0.66 points** (9th of 22, up from 12.71).

- Places 1-8: 118/105/92/73/91/105/117/99. Top 3 rose to 39.4% from 35.9%, and 8th place fell to 99 from 123.
- Net chips over the 17,658 recorded hands went from −45 BB (round 1) to +1,385 BB.
- Trash re-jams disappeared (3, against 54 in round 1).
- Postflop folds to bets dropped to 55/70/68% on flop/turn/river (from 63/81/87%).

So the round-2 fixes worked. The remaining leaks, found with the same scripts on
`claude_aggro_r2/round2/hand_history.jsonl.gz`:

1. **Opening too wide for this field.**
   - After our open, someone re-raises 40-50% of the time and everyone folds only about 20%.
   - Opens with hands ranked 25-45% lost about 0.35 BB each, consistently across both rounds (about 450-500
     opens per round).
   - Top-10% opens made +1.8 BB and 10-25% opens +0.17 BB.
   - Open-then-fold-to-a-3-bet cost −873 BB over 385 hands.
2. **Calling 3-bets after opening.** The open, call the 3-bet, play postflop line lost 4.8 BB per hand
   (68 hands).
3. **Open-jams outside the top 35%** were slightly negative in round 2 (about −56 BB over 156 jams).

Changes (constants only; CPU per decision unchanged):

| Change | Before → after |
|---|---|
| Open-range scale | 1.0 → 0.8 (BTN 50%→40%, CO 36%→29%, SB 60%→48%; still widened by observed fold rates) |
| Push-range scale | 1.0 → 0.9 |
| Realisation when calling a 3-bet or bigger after opening | ×0.85 |

Local results for r3:
- `play.py` default mix, 300 tables: self **22.04 ± 0.57** (r2 21.72).
- Upload test passes; 0 illegal actions.
- That run logged 1 timeout while the machine's load average was about 46 (wall-clock stalls up to 71 ms).
  This is machine load, not the bot.

Own engine:

| Setup | r3 | r2 |
|---|---|---|
| 4 r3 vs 4 r2, 3,200 seats each | 12.72 ± 0.31 | 12.28 ± 0.32 |
| 2 r3 + 2 r2 + 4 archetypes | 18.48 ± 0.50 | 19.13 ± 0.51 |
| 1 bot vs archetype mix | 32.9 ± 0.7 | 31.8 ± 0.7 |

Even within noise: my archetypes rarely 3-bet, so they cannot show the benefit. The case for r3 rests on the
round-2 field data above.
