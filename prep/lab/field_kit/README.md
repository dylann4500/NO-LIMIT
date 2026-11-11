# Starter kit (lab stand-in)

You are one team in "No Limit", a pokerbot tournament with about 150 teams. Your job is to build the strongest bot you can. This folder is everything your team has: the rules, the API and a local simulator. Everything here mirrors what the real event gives teams.

## The tournament

- **Format:** eight-bot sit-and-go tables, No-Limit Texas Hold'em. Each bot starts with 2,000 chips. Blinds start at 10/20 and rise every 20 hands. A table ends when one bot has every chip, or after 250 hands.
- **Points by finishing place:** 50 / 30 / 20 / 0 / 0 / 0 / 0 / 0. At the hand cap, the surviving bots split the remaining points by ICM on their stacks. When several bots bust in one hand, the one with more chips at the start of that hand places higher.
- **Scoring:** at least 5,000 tables per round, with random seats. A round score is the average points per table. Six rounds, weighted 1 to 6.
- **Opponents:** other teams' bots, mostly built with frontier AI coding assistants in a 60-minute build. Seats are anonymized per table.
- **Defaults can change.** A round may change the defaults. `state.config` holds each table's actual settings, including `payouts`.

## The API

```python
import poker_agent_sdk
from poker_agent_sdk import Action

class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        # Return an Action and the bytes you want back as `memory` on your next turn at this table.
        return action, memory
```

### Actions

- `Action.fold()`, `Action.check()`, `Action.call()` and `Action.raise_to(total)`. `total` is your whole bet for the current betting round.
- `state.can(kind)` returns that kind's legal action, with `min_amount` and `max_amount`, or `None`. `state.legal_actions` lists the offered actions; each has `.kind`, `.min_amount` and `.max_amount`.
- **Only offered kinds are legal.** Check and call are never offered together, and there's no fold when checking is free.
- **A `raise_to` total outside `min_amount..max_amount` is not clamped.** Floats are rounded down, so a computed size can land one chip under the minimum. Use ints.
- **Failed decisions:** a timeout, exception or illegal action plays the fallback: check if free, otherwise fold. Returning a kind that isn't offered, or an out-of-range total, is a failed decision even when the fallback has the same effect.

### State

- **The hand:** `seat` (yours), `cards`, `board`, `pot`, `to_call`, `legal_actions`, `history` (this hand only), `phase` (`"betting"`). Cards are strings like `"As"` and `"Td"`.
- **The table:** `seats`, each with `seat`, `stack`, `bet` (this street), `status` (`active`, `folded`, `all_in` or `busted`) and `shown_cards`; plus `button`. Seat numbers are anonymized per table.
- **The tournament:** `blind_level`, `blinds` (`[small, big]`), `hands_until_next_level`, `hand_number`, `players_remaining`, `bust_order`.
- **`state.config`:** `table_id`, `seat`, `variant`, `players`, `starting_stack`, `blinds` schedule, `hands_per_level`, `hand_cap`, `payouts`, `decision_ms`, `time_bank_ms`, `memory_bytes`. Also `state.time_bank_ms`, the bank remaining.
- **`state.events`:** everything public at the table since your last turn there; on your first turn, everything since the table started. Each event has `kind`, `seat` (`None` for `hand` and `board`), `amount` and `cards`. Kinds:
  - `hand` (amount: the hand number), `ante` and `blind` (chips posted), `fold`, `check`
  - `call` (chips added), `raise` (the raiser's total bet for the round)
  - `board` (only the newly dealt cards), `show` (revealed cards), `win` (chips awarded), `stack` (a seat's stack when the hand ends)
- **Showdowns:** everyone who reaches showdown reveals their hole cards, losers included. A fold reveals nothing.

### How your bot runs (production)

- **Time:** `state.config.decision_ms` per decision (1 ms). Overruns draw on a per-table bank of `time_bank_ms` (100 ms), and a timeout empties the bank. **The tournament machines are about 2.5x slower than this one**, so leave room.
- **Copies:** each team runs as a pool of identical copies, and any copy may answer any table. `self` and globals can't be relied on between calls. Per-table state travels in `memory` (bytes, `b""` at each new table), truncated at 64 KB. Up to ~16 KB costs nothing. Carrying information between tables breaks the rules.
- **Failures:** after a timeout or exception, your previous memory is kept and that turn's events are delivered again. After an illegal action, the memory you returned is stored.
- **Import:** the bot is imported once and forked, so load tables and models at import.
- **Libraries:** standard library, `numpy`, `scipy` and `eval7` are available here. The real machines also have pandas, scikit-learn, PyTorch CPU, LightGBM, XGBoost, ONNX Runtime and Numba, which aren't installed in this lab, so don't use them. There's no network.
- **Upload test:** each upload first plays a heads-up match of up to 20 hands against a check-or-fold bot, with the 1 ms limit and **no time bank**. It's rejected if it crashes or fails more than 10% of its decisions.

## Local testing

From the repo root:

```bash
.venv/bin/python lab/field_kit/play.py lab/field_bots/<your_name> --tables 200
```

This runs the upload test, then plays 8-seat tables with copies of your bot, `check_or_fold` and `min_raiser`. It reports points, finishing places, failed decisions and latency as JSON. `--seats` changes the mix, for example `--seats self,self,self,self,self,self,self,min_raiser`. `--seed` replays the same randomness.

## Deliverable

`lab/field_bots/<your_name>/agent.py`, plus any files it reads, in that folder, with `Agent` at module level. Also write `lab/field_bots/<your_name>/NOTES.md` covering your approach, what you tested, and your final local results.
