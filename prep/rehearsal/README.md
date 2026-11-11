# Sealed rehearsal (60 minutes)

This practices the event: an unfamiliar interface, a surprise rule change, and a clock. **It is a mock.** The real kit will differ, so what you're practicing is the process.

## Setup (person who won't build, 2 minutes)

1. Edit `kit/rules_card.json` with a points table and blind schedule of your choosing.
2. Pick a variant: `holdem`, `shortdeck`, `flushfh`, `hole3` or `omaha`.
3. Tell the builders only at the start.

## Run

From `rehearsal/kit`:

```bash
# Use the project's Python. Set the variant in the shell for every run:
export POKER_VARIANT=shortdeck
# Variant tables must exist for the simulator's opponents (from lab/):
#   ../../.venv/bin/python ../../lab/build_tables.py

../../.venv/bin/python simulate.py my_bot_template.py MyAgent 500            # the baseline
../../.venv/bin/python simulate.py path/to/your_bot.py MyAgent 1000 typical  # your bot
../../.venv/bin/python simulate.py path/to/your_bot.py MyAgent 1000 holdout  # unseen opponents
```

The doc at the top of `kit/agent.py` is your only interface spec. Don't read `solution/` first.

## Pass criteria

- A legal bot in under 15 minutes.
- 0 errors and 0 illegal actions.
- Few or no over-1-ms decisions when the machine isn't busy.
- A clear win over the check/fold template on `holdout`, which scored 42 against `typical` on the placeholder table (fair share 31.9). Scores are only comparable with the same rules card and field.

## Traps built in on purpose

- `chips` excludes `street_bet`.
- Raises are expressed as chips **above the call**, not as a total.
- `max(street_bets)` isn't always the amount to call. A big blind all-in for less still sets the full amount.
- History covers only the current hand and is delivered only at your decisions, so you never see actions after your last one.
- You aren't told who raised or how many players remain to act. You have to derive both.

## Afterward

Write down what cost the most time, then fix that part of the process before tomorrow.
