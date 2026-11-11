> **Snapshot.** This folder is a copy of `samrocksnature/pokerbot` (branch `prep/adapter-field-cluster` at `17d4f61`, plus the then-uncommitted `lab/v2_next/`), imported into NO-LIMIT on 2026-11-11. It was written before the regional, so it predates the real kit and the event. Paths below are relative to `prep/`. The repo root's `AGENTS.md` takes precedence.

# No Limit pokerbot: handoff

Preparation for "No Limit: A Bot Building Tournament" (Fri Nov 6, 2026, Sequoia HQ). You are picking this up for a team of two.

**Keep this repo private.** Rule text: teams are disqualified for "colluding with other teams" or "copying another team's code". Do not commit the poker variant anywhere public before the event ends.

## Start here

1. Read `docs/event_portal.md`: the real API and format, which override anything older.
2. Read `docs/BUILD_PROMPT.md`, Parts A to E. It is the plan for the day: master prompt, tested results, timeline with prompts C0-C8, variant response and failure runbook.
3. Set up and run the checks below.
4. Do not redesign without evidence. Part B records what was tried and lost.

**The adapter exists and is tested against a stand-in platform.** `lab/adapter.py` is appended to every generated bot. It rebuilds the policy's inputs and opponent stats from `memory` on every call, so nothing per-table lives on `self`. `lab/test_adapter.py` plays it through `lab/platform_sim.py`, which implements the portal's API and failure rules. It scores 100% decision parity with the native policy under all 16 combinations of the conventions the portal leaves open, with injected timeouts and junk memory. At kickoff, check every `KIT:` line in the adapter against the real kit, then run `test_adapter.py` with the real SDK.

## Setup

Python 3.12. The bot is stdlib only; numpy is for local tuning only.

```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python numpy
# without uv: python3.12 -m venv .venv && .venv/bin/pip install numpy

cd lab && ../.venv/bin/python test_engine.py && cd ..
./make_submission.sh lab/tuned_real1.json lookup '[50,30,20,0,0,0,0,0]'
cd lab && ../.venv/bin/python test_adapter.py ../submission && cd ..
```

`make_submission.sh` needs zsh. It writes `submission/bot.py`, runs the gate, and **overwrites `reference_bot/bot.py`**. A pass is 0 illegal actions and acceptable latency. Latency numbers are only meaningful on a quiet machine on mains power.

## Layout

| Path | What it is |
|---|---|
| `docs/event_portal.md` | Real API, format, limits and build box, from the portal |
| `docs/portal_getting_started.md`, `docs/portal_format.md` | Full text of the two portal pages, recaptured the morning of the event |
| `docs/BUILD_PROMPT.md` | Main document. **Generated**: edit `docs/prompt_template.md`, then run `tools/build_doc.py` |
| `docs/official_rules.txt` | Event rules as captured. Older than the portal on format details |
| `docs/research_literature.md` | Literature notes |
| `docs/CODEX_PROMPTS.md` | Fallback prompts to rebuild from a blank repo if prepared code is ruled out |
| `docs/PLAYBOOK.md` | Superseded by `BUILD_PROMPT.md` |
| `lab/` | Engine, opponent field, policy, tuners, bot generator, tests, tables, tuned parameters |
| `lab/tuned_real1.json` | Current best parameters: `tuned_final` retuned for the real format (20-hand levels, 250 cap, 50/30/20). Beat it in all 9 fields, including 5 never-seen ones |
| `lab/tuned_final.json` | Previous best parameters |
| `lab/adapter.py` | The only code that knows the platform API. Appended to the generated bot |
| `lab/fake_sdk/`, `lab/platform_sim.py`, `lab/test_adapter.py` | Stand-in SDK and platform written from the portal text, and the adapter gate |
| `lab/field_kit/`, `lab/field_bots/` | A kit for AI-generated opponent bots (prompts in `field_kit/teams/`), and the bots. `tools/gen_codex_bots.sh` makes the OpenAI ones |
| `cluster/` | Variant x blind schedule x payout tuning matrix for a multi-core machine. See `cluster/README.md` |
| `lab/exploit_parked/` | Exploiters kept out of tuning: hardening against them lost 4-9 points |
| `lab/event_config.json` | Portal defaults the simulator uses. Add the kit's blind schedule at kickoff |
| `reference_bot/bot.py` | Current best bot: lookup equity, `tuned_final` |
| `reference_bot_mc/bot.py` | Rollout-equity bot: `tuned_mcblend`, not exploiter-hardened |
| `rehearsal/` | 60-minute mock event. Its `solution/` is a spoiler. See `rehearsal/README.md` |
| `benchmark/` | Slumbot client and logs |
| `tools/` | `extract.py` rebuilds the workspace from the document; `test_variants.sh` gates all five variants |
| `run2`-`run5`, `snap2` | Raw experiment logs and code snapshots. **Evidence only**: never edit or import from them, and ignore them when searching for source |

## What we know

All scores come from our own simulator against bots we wrote. Trust direction more than size. Most numbers below use an old placeholder points table where a fair share is 31.9.

- **Under the real format** (20-hand levels, 250-hand cap, 50/30/20, fair share 12.5, blinds after 10/20 still guessed; ±0.36): the final bot scored typical 29.84, holdout 27.06, stress 26.00, against 29.80, 25.83, 23.92 for the blend-tuned bot. It was not retuned for this format.
- **Design:** a rule-based policy with about 30 thresholds, tuned with CMA-ES against a blend of weak bots, copies of itself and exploiters. It touches the variant only through `pct(hole)` and `eq(hole, board, width)`. A single adapter holds all API-aware code.
- **Best bot versus the blend-tuned bot:** holdout 58.2 vs 54.8, stress 55.9 vs 52.1, typical 64.8 vs 64.5.
- **Exploiter score against our bot, by hardening round:** 83.5, 53.2, 64.8, 44.9.
- **Tuner:** CMA-ES 53.3 vs CEM 45.8 at 40k tables.
- **Between rounds:** refreshing against the current field scored best (52.85) and freezing the bot scored worst (51.06).

## Not verified

- **The real kit.** Variant, later blind levels and the actual SDK are unavailable until kickoff. The API is known only from the portal text, and nothing here has run against it.
- **Engine parity with the real rules.** `lab/` has not been compared against the kit's simulator, including its tie rule for simultaneous busts. Prompt C4 does this.
- **Claude and prepared material.** The portal names Claude Code for setup, but rule 3.4 names only Astra and Codex for writing the bot, plus public documentation. Confirm what is allowed at check-in. `docs/CODEX_PROMPTS.md` is the fallback, though it predates the real API.
- **Tuner and exploiter tools** were smoke-tested after their final changes, not rerun end to end. Rollout-bot retuning through `tune_event.py` has never been run.
- **Strength against strong play.** Slumbot heads-up was -84±34 and -36±28 bb/100; always folding is -75. That is one benchmark in a format that differs from the event, and the gap between those two numbers was luck.
- **Book charts.** A chart-style bot lost on holdout (53.1 vs 59.4), but it used our approximate ranges, not a book's.
- **`third_party/poker-gym`** is not in this repo and was never run. Clone it from https://github.com/mack-dot/poker-gym.git if needed.

## Before the event

- Each member adds their own SSH key on the portal (see `docs/event_portal.md`).
- Run `rehearsal/` once under the clock. Its mock API is deliberately not the real one.
- Confirm the rules question above.
- Get a GTO Wizard benchmark key only if you want that extra benchmark.
- Bring chargers. Doors 5:00 PM, check-in 5:30 PM, kickoff 6:00 PM sharp.
