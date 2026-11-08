# 01 · Rules, scoring, limits and the API

**The kit's `RULES.md`, `README.md` and `state.config` override everything here.**

## Format
- **Tables:** 8-player no-limit sit-and-gos, 2,000 chips each (100 big blinds). Blinds start at 10/20 and rise every 20 hands, with a 250-hand cap. The later levels come from the kit: read `state.config.blinds`.
- **Points:** 50 / 30 / 20 / 0 / 0 / 0 / 0 / 0 (fair share 12.5). At the hand cap, survivors split the remaining points by ICM on their stacks.
  - When several bots bust in one hand, the one with more chips at the start of that hand places higher.
  - A round may change payouts per table: **read `state.config.payouts`**.
- **Rounds:** six scored rounds, T1 at build end, then every 20 minutes, with weights 1-6. T4-T6 are 71% of the score and T6 alone 29%.
  - Each round plays the bot that's active when it starts.
  - At least 5,000 tables per round, so round-to-round luck is tiny (±0.3).
  - Results arrive in the next window, so round k's hand histories shape the bot for round k+2.
- **Ties** go to countback: the weighted share of 1st places, then 2nd places, and so on.

## Hard limits (a violation makes the bot ineligible or makes it lose)
- **Time:** 1 ms per decision (`decision_ms`) plus a small delivery allowance. Overruns draw on a 100 ms bank per table, and a timeout empties the bank.
- **Upload test:** heads-up, up to 20 hands, against a check-or-fold bot, with **no time bank**. It rejects bots that are too slow to start, crash, stall, or fail more than 10% of decisions.
- **Legality:** return **only offered action kinds.** A `raise_to(total)` outside `min_amount..max_amount` is **not clamped**, so it fails.
  - Floats are rounded down (one chip under the minimum fails), so always send ints.
  - Check and call are never offered together, and there's no fold when checking is free.
- **Failures:** a failed decision plays check if free, otherwise fold. **A crash is far worse than an exception:** a crashing copy gets restarted, copies get limited restarts per round, and once all copies are given up the bot plays fallback for the rest of the round.
- **Memory:** per-table state travels only in `memory` (bytes, `b""` at each new table, truncated at 64 KB; up to about 16 KB is free).
  - `self` and globals are unreliable, because any copy may answer any table.
  - After a timeout or exception the previous memory is kept and that turn's events are **delivered again**.
  - Memory that makes `act` raise comes back unchanged every time.
  - **Carrying information between tables breaks the rules.**
- **Code:** Python 3.12, stdlib, plus numpy, scipy, pandas, scikit-learn, torch CPU, lightgbm, xgboost, onnxruntime, numba and eval7.
  - No network, and the bot's folder is read-only and non-executable (no compiled extensions).
  - Upload limits: 50 MB, 1 MB of code in `agent.py`.
  - Any `.py` in the zip importing `poker_engine` or `pokerkit` gets it rejected.
- **Process model:** `agent.py` is imported once, then forked; each copy constructs `Agent()`. Load tables at import and make one throwaway decision there. Threads don't survive the fork.
- **Uploads:** one per 30 s. **Confirm "Active bot" on the team page after every upload,** because the two portal pages disagree on whether a passing upload auto-activates.

## API shape (verify every name in the kit)
- **Entry point:** `class Agent(poker_agent_sdk.Agent)` with `act(self, state, memory) -> (Action, bytes)`.
- **Actions:** `Action.fold()`, `.check()`, `.call()`, `.raise_to(total)`, where `total` is your whole bet for this betting round. `state.can(kind)` returns a legal action with `min_amount`/`max_amount`, or None. A variant may add phases and kinds; for an unknown phase, take `Action(first.kind, first.min_amount)` with `first = state.legal_actions[0]`.
- **State fields:**
  - `seat`, `cards` (strings like `"As"`), `board`, `pot`, `to_call`, `legal_actions`, `history` (this hand), `phase`, `variant`
  - `seats` (each with seat, stack, bet, status active/folded/all_in/busted, shown_cards), `button`, `blind_level`, `blinds`, `hands_until_next_level`, `hand_number`, `players_remaining`, `bust_order`
  - `config` (table_id, seat, variant, players, starting_stack, blinds, hands_per_level, hand_cap, payouts, decision_ms, time_bank_ms, memory_bytes), `time_bank_ms`
- **Events** (`state.events`, everything public since your last turn) have kind, seat, amount and cards:
  - `hand` (the hand number), `ante`/`blind` (chips posted), `fold`, `check`
  - `call` (**chips added**), `raise` (**the raiser's total for the round**)
  - `board` (only the new cards), `show`, `win`, `stack` (stack at hand end)
  - Ignore kinds you don't know. Everyone reaching showdown reveals their cards.

## The traps that silently cost points (no error, just wrong play)
The portal leaves four things open. A bot written for one guess lost **25 → 19 points per table** under another, with zero errors. **Detect them at runtime** (see `02_ARCHITECTURE.md`) and also read the kit:
1. Does `Seat.stack` include that seat's bet this street?
2. Does `state.pot` include this street's bets? This one is the worst.
3. Is your own action echoed in your next turn's events?
4. Are event kinds and statuses strings or enums?

Also:
- `max(bets)` isn't always the amount to call (a short all-in blind still sets the full amount); use `to_call`.
- Raise and raise events are totals; call events are chips added.
