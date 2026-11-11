# claude_default_b: notes

## Files
- `agent.py`: the bot (`Agent` at module level). Imports only the standard library, `eval7` and `poker_agent_sdk`.
- `tables.json`: preflop tables, read once at import.
- `build_tables.py`: offline script that regenerated `tables.json` with eval7 Monte Carlo (about 6 s). The bot never runs it.

## Approach
Everything in a decision is either a table lookup or one small eval7 call. Measured CPU per decision on this machine: p50 about 40 µs, p99 about 160 µs, p99.9 about 210 µs. Postflop decisions are the slowest, with p99.9 under 300 µs (about 700 µs on a machine 2.5x slower).

**Preflop tables.** There are 169 hand classes, ordered by a blend of equity against a random hand and equity against the top 15%. For each class, `eq[class][w]` holds its heads-up all-in equity against the top `w` of hands, on a 19-point grid of `w`.

**Opponent model.** Each seat's counts are parsed incrementally from `state.events` and stored as JSON in `memory`, about 600 bytes. Re-delivered events after a failure are safe because the platform keeps the previous memory. The counts are:
- VPIP, PFR, open %, 3-bet %, calls against raises
- postflop bet frequency, fold-to-bet and raise-against-bet
- times facing an all-in and times calling one

Every estimate is shrunk toward a prior (weight of 6 observations).

**Villain ranges.**
- An opener's range is their open %, scaled by how many players were behind them (from 0.7x UTG to 2x SB).
- A 3-bettor's range is their 3-bet %.
- An all-in shove is at least a Nash-like width for that stack in big blinds, also scaled by position.
- Callers get their VPIP; a checking big blind gets every hand.

**Preflop decisions.**
- Unopened pot, deeper than 14 bb: open-raise if the hand falls inside a position-based width (14% UTG up to 50% SB). The width grows when the players behind fold often. Iso-raise limpers; the big blind raises its option with strong hands.
- 14 bb or less (18 bb when only the blinds are left to act): push or fold, chosen by an explicit EV model:
  - Each opponent who could call does so with a fraction `q` of their range. `q` comes from a precomputed table: which hands have enough equity against how wide they think my shove range is, given their pot odds. A bubble premium is added.
  - Observed all-in calls override `q` gradually.
  - Each outcome (everyone folds, or opponent i calls and I win or lose) is scored with a utility that blends ICM and chip share. ICM is Malmuth-Harville, exact for 3 paid places. ICM weight is 0.5 with 7–8 players left and 1.0 at 4 or fewer.
- Facing a raise:
  - Committed spots (at most 25 bb effective, villain all-in, or calling would cost at least 40% of my stack): shove or fold, using the same EV/ICM model. Facing an all-in, ICM-call versus fold.
  - Deep: value-raise if my equity against the raiser's range is at least about 0.57. Otherwise flat if equity × realization beats the pot odds. Realization is 0.86 in position and 0.72 out of position, minus 0.04 per player still to act, plus a bonus for pairs and suited hands when implied odds are good. A few light 3-bets go against players who fold to raises a lot.

**Postflop.**
- **Equity.** Take the main villain (the bettor if I'm facing a bet, otherwise the preflop raiser or the tightest range). Sample about 110 combos from their preflop range and rank them by made-hand strength on the current board. Keep the top fraction, set by their frequencies:
  - each bet keeps about `1.15*betfreq + 0.1`
  - each raise keeps about `1.6*raisefreq + 0.1`
  - each call keeps about `1.1 - foldfreq`

  A sixth of the rest is kept as draws and bluffs. Then run `eval7.py_hand_vs_range_monte_carlo` for 380 iterations. Multiway equity is `e^(1 + 0.75(n-1))`.

  Opponents who bet every street, such as min_raiser, don't narrow at all, so I call them down light. Nits narrow a lot.
- **Facing a bet.**
  - Raise for value when equity is at least 0.78 (0.84 on the river).
  - Call when equity × realization is at least the pot odds plus a small margin.
  - When committed, make an ICM call-versus-fold decision and shove if equity is at least 0.6.
- **Not facing a bet.** Compare checking (equity × realization × pot) with betting 33, 50, 75 or 100% of the pot:

  `EV = F*pot + (1-F)*(e_c*(pot+2B) - B)`

  - `F` is the product of each opponent's fold-to-bet estimate, scaled up for larger bets and for a flop c-bet.
  - `e_c` is my equity when called, which drops as `F` and the bet size grow.

  Value bets, thin bets, c-bets and bluffs all come out of this one formula, and it adapts per opponent. It never bluffs a station or min_raiser, and always stabs at check_or_fold.

**Safety.**
- Every action goes through `_legal()`. It returns only offered kinds, and raise totals as ints clamped to `[min, max]`; a size within 10% of max becomes all-in.
- Action, event and status kinds are normalized whether they arrive as enum members or strings.
- Any exception inside the decision falls back to check, else fold, inside `act()`, so the platform never sees an exception.
- If the decision is already slow, the postflop Monte Carlo shrinks.
- `gc.freeze()` after import keeps garbage-collection passes cheap.

## What I tested
- **Upload test** (heads-up against check_or_fold, 1 ms, no bank): passed with 0 failures on 8 seeds.
- **play.py seat mixes:**
  - the default mix
  - 8× self, and 9× self (a 9-seat table)
  - self against 7× min_raiser, and against 7× check_or_fold
  - heads-up against min_raiser
  - 3- and 6-seat tables

  No failed decisions and no errors in any of them. Memory stays under 700 bytes.
- **CPU-time harness** (thread time per decision, by street): see Approach. Wall-clock latency in play.py was inflated by other jobs running on the machine during my runs, but no decision failed because of it.
- **Probes** of push, call and open ranges by position and stack depth, against Nash-style references. These led to two fixes:
  - The caller model was too tight, which made heads-up and SB shoves too wide. I replaced the linear model with the equity-based `CALLQ` table.
  - Villain ranges ignored position, which made calls against UTG too loose and against SB too tight. I added position scaling.
- **Postflop probes** of common spots (top pair good kicker, sets, draws, air, river bluff-catchers) to check that the actions make sense.
- **Arena** (scratch harness, not shipped): every play.py "self" seat is routed to a role per table, either this bot, an older version of it, or simple archetypes (tag, nit, aggro, station). Against that field this bot averaged about 19–25 points per seat, against a fair share of 12.5. Parameter A/B tests (fold-to-bet prior, open width) were within noise. An A/A run showed about ±1 point of noise at 2,000 seats, so I kept the theory-based defaults.

## Final play.py results
`.venv/bin/python lab/field_kit/play.py lab/field_bots/claude_default_b --tables 400 --seed 1` (default mix: 4 self, 2 check_or_fold, 2 min_raiser):

| seat | mean points | SE | places 1–8 |
|---|---|---|---|
| self | **21.63** | 0.50 | 397, 360, 198, 63, 162, 284, 133, 3 |
| check_or_fold | 6.55 | 0.36 | 0, 40, 202, 331, 211, 16, 0, 0 |
| min_raiser | 0.19 | 0.11 | 3, 0, 0, 6, 27, 106, 297, 361 |

- Upload test passed, with 0 failed decisions out of 209,303. Fair share is 12.5.
- Other mixes:
  - self against 7× check_or_fold: 50.0 (wins every table)
  - self against 7× min_raiser: 43.2
  - 8× self: 12.5 (symmetric)
