# Event portal facts (Bay Area, team avalon)

Condensed from the portal's Getting started and Tournament format pages, captured the night before the event. The full text of both pages, recaptured the morning of the event, is in `portal_getting_started.md` and `portal_format.md`. **Where these conflict with `official_rules.txt`, trust the portal, and trust the kit's own files and `state.config` over both.** The public rules page still said 25-hand levels, a 200-hand cap and 10,000 iterations on the morning of the event. Re-read both pages at kickoff; the variant, kit and uploads only appear then.

148 teams. Five teams from each regional plus five wildcards go to finals.

## What changed from our assumptions

| Topic | We built for | Portal says |
|---|---|---|
| Blinds | Up every 25 hands | Start 10/20, up every **20** hands. Later levels unknown until the kit |
| Hand cap | 200 | **250** |
| Points | Placeholder 100/60/40/25/15/10/5/0 | **50/30/20/0/0/0/0/0** by default. A round may draw payouts per table: read `state.config.payouts` |
| Iterations | 10,000 per round | **At least 5,000**; practice about 1,000 every 10 minutes |
| Uploads | One per 5 minutes | **One per 30 seconds** |
| Size | 100 MB | 50 MB upload, 200 MB unpacked, 1,000 entries, **1 MB of code in `agent.py`** |
| Libraries | Stdlib only | Also NumPy, SciPy, pandas, scikit-learn, PyTorch CPU, LightGBM, XGBoost, ONNX Runtime, Numba, eval7 |
| Time | 1 ms, then fold | 1 ms, then a **100 ms per-table bank**. A timeout empties the bank. **The upload test match has no bank** |
| Per-table state | `self` | **`self` and globals are unreliable.** Any copy may answer any table. State travels in `memory` |
| Opponent data | Live table only | Forced showdown reveals, plus **downloadable hand histories with opponents named** after each round |

## The API

```python
class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        return action, memory   # memory is bytes, b"" at the start of each table
```

**Actions:** `Action.fold()`, `Action.check()`, `Action.call()`, `Action.raise_to(total)`. `total` is the whole bet for the current betting round. A variant may add phases and action kinds.

**Legality:**
- `state.can(kind)` returns that kind's legal action with `min_amount` and `max_amount`, or None.
- Only offered kinds are legal, and a `raise_to` outside the range is not clamped.
- Check and call are never offered together. Hold'em offers no fold when checking is free.
- Returning a kind that is not offered is a failed decision, even if the fallback has the same effect.
- Floats are rounded down, so a computed size can land one chip under the minimum. Use ints.
- If neither check nor fold is offered: `first = state.legal_actions[0]; Action(first.kind, first.min_amount)`.
- Failed decisions play check if free, otherwise fold, or the automatic choice in a phase a variant adds.

**State:**
- **Hand:** `seat`, `cards`, `board`, `pot`, `to_call`, `legal_actions`, `history` (this hand only), `phase`, `variant`. Cards are strings such as `"As"`.
- **Table:** `seats` (each with `seat`, `stack`, `bet`, `status` of active/folded/all_in/busted, and `shown_cards`), `button`.
- **Tournament:** `blind_level`, `blinds`, `hands_until_next_level`, `hand_number`, `players_remaining`, `bust_order`.
- **`state.config`:** `table_id`, `seat`, `variant`, `players`, `starting_stack`, `blinds` schedule, `hands_per_level`, `hand_cap`, `payouts`, `decision_ms`, `time_bank_ms`, `memory_bytes`. Also `state.time_bank_ms`, the bank remaining.
- **`state.events`:** everything public since your last turn at this table. Each has `kind`, `seat`, `amount`, `cards`. Hold'em kinds:
  - `hand` (amount is the hand number), `ante`, `blind`, `fold`, `check`
  - `call` (chips added), `raise` (the raiser's total for the round)
  - `board` (new cards only), `show`, `win`, `stack`
  - Ignore kinds you don't handle.

**Memory:**
- Truncated at `memory_bytes` (64 KB by default), so parse defensively. Up to about 16 KB costs nothing measurable.
- After a timeout, exception or crash, the previous memory is kept and that turn's events are delivered **again**.
- After an illegal action, the memory returned with it is stored.
- Memory that makes `act` raise comes back unchanged on every later turn at that table.
- Carrying information between tables breaks the rules.

**Process model:** the microVM imports `agent.py` once and forks every copy, and each copy constructs `Agent()`. Build tables at import and run one throwaway decision there. Threads started at import don't survive the fork. If you use numeric libraries, limit them to one thread (the Getting started page lists the settings).

**Sandbox:** no network or GPU. The bot's directory is read-only and non-executable, so compiled code in an upload can't load. `/tmp` is the only writable place, and bots may not keep files between tables or compute between decisions.

## Kit commands

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ./sdk/agent-protocol -e ./sdk/engine -e ./sdk/agent-sdk
poker-agent check agent.py
poker-agent play . examples/check_or_fold examples/min_raiser --tables 200   # repeat folders to fill 8 seats
poker-agent pack DIR OUT.zip                                                 # DIR holds only the bot
```

- `poker_engine` and `pokerkit` exist only locally. A zip is rejected if **any** `.py` file in it imports them, even one the bot never loads.
- `play` always gives a 100 ms bank, so it can pass a bot that the upload test rejects. Measure `act` with `time.perf_counter_ns()` and compare p99 and max, not the mean.
- An upload plays up to 20 heads-up hands with no bank. It is rejected if it fails to start in time, crashes or stalls, or fails more than 10% of decisions.

## Activation: check it every time

The pages disagree. Getting started and the team page say a passing upload becomes active automatically. The Format page says an upload alone doesn't activate it. **Confirm "Active bot" on the team page after every upload.** No active bot at round start scores zero for that round.

Each round snapshots the active bot when it starts. A competition-wide freeze refuses uploads and active-bot changes.

## Scoring and table rules

- Rounds start 20 minutes apart after the 60-minute build, with weights 1 to 6. Final score is the weighted sum of average points per table.
- Equal totals are ordered by weighted countback: share of first places, then seconds, and so on.
- When several bots bust in one hand, the one with more chips at the start of that hand places higher.
- At the hand cap, survivors split remaining points by ICM on their stacks.
- Seats are random each iteration. Short tables use filler bots whose finishes don't score for their teams.

## Added from the full pages (event morning)

- **Upload test opponent** checks when free and otherwise folds. The startup allowance for import is unstated; a rejection names it. A crash in the test match is not restarted.
- **The clock** starts when the host sends the request: `decision_ms` plus a small delivery allowance, with memory carried inside that time.
- **Crashes are worse than exceptions.** An exception in `act` fails one decision. A copy that crashes, stalls or breaks the protocol is restarted, each copy has a limited number of starts per round, and once all copies are given up the bot plays the fallback for the rest of the round on that machine.
- `/tmp` is 64 MB, not executable, and shared by the team's copies.
- **Showdowns:** everyone who reaches showdown reveals, losers included. A fold reveals nothing, and an uncontested winner does not show. `show` events arrive on your next turn at that table.
- **The team page** shows decisions, missed decisions, restarts and tracebacks, never what the bot prints.
- **`poker-agent play`:** 2 to 10 seats, one per folder argument. Each folder runs as two processes shared by its seats. `--seed` replays; output is JSON on stdout.
- **Countback** is the weighted share of first places across rounds, then seconds, and so on.
- **Results** normally arrive within the next 20-minute window, so a round's hand histories may only reach the round after next.
- **Practice** runs about 1,000 iterations every 10 minutes during the build and never scores.
- **Short fields** use bots not already seated as fillers.
- **Regionals** are at Harvard/MIT, Stanford and CMU.

## Build box and AI tools

- **Before the event:** each member adds their own SSH public key (Account settings, SSH keys). Get the address from the team page's Build box tab; it is deliberately not stored here. Work in `~/work`. The box stays closed until its opening time.
- **Codex on the box:** `codex login --device-auth`, then run `codex` in `~/work` inside `tmux new-session -A -s no-limit-2026`.
- **Setup skill:** `https://pokerbot.sequoiacap.com/tournament/no-limit-2026-setup/SKILL.md`. It needs an API key from Settings, and the page says to use a smaller model for it. Run it again after the announcement to fetch the kit.
- **Claude:** the portal names Claude Code as a setup assistant and the kit ships a `CLAUDE.md`, but rule 3.4 names only Astra and Codex for writing the bot. Nothing we've read says whether prepared code is allowed. Ask at check-in.
- **Credits:** each competitor can claim $50 in OpenAI credits on the Getting started page.
