# 07: GTO Wizard benchmark: how avalon could use it, and what it would tell them

Five-line summary
1. The benchmark is heads-up no-limit hold'em for chips, 50/100 blinds, 200 big blinds reset every hand, against GTO Wizard AI (version 2 on the leaderboard), scored in luck-adjusted bb/100 (AIVAT). It is free, by approved key, capped at 10,000 hands a day, 25,000 a week, 50,000 a month. Every hand is public and permanent under the key's name.
2. The key goes in `~/.config/gtow.env` as one line `GTOW_API_KEY=<key>` (mode 600), or the environment variable `GTOW_API_KEY`. The team's adapter sends it as the `X-API-Key` header. Neither exists on this Mac now (presence checked, nothing read).
3. The adapter `emu/benchmark/gtow.py` exists (written by Samuel, 11 Nov). I found no evidence it was ever run against the live API: no output files, no leaderboard entry named Avalon, no key file. It has one probable seat-numbering bug and cannot see a bot's own swallowed errors.
4. No bot of the team's is a plain hold'em bot. Last night's bots run mechanically but carry pre-flop values and an opponent model built for the card-pass twist. A result measures deep heads-up hold'em fundamentals only; it says nothing about the twist, tournament play, six seats, or 1 ms.
5. Recommendation: place the key if you like, run nothing before the event. After it, strip the twist from v17, smoke-test 20 hands attended, then 5,000 hands (about ±7 to ±9 bb/100). Nothing here was run and no key was used, read or requested.

How the web facts were read: through a page-fetching tool that summarizes. Numbers below are as it reported them at about 01:10 PST on 15 Nov 2026; recheck any figure you intend to quote.

---

## 1. What the benchmark is

| Item | Fact | Source |
|---|---|---|
| Game | Heads-up no-limit Texas hold'em. Game name in the API: `HUNL 200BB` (the only one accepted for new hands) | https://gtowizard.com/benchmark ; https://researcher.gtowizard.com/openapi.json |
| Blinds, stacks | 50 and 100 chips; 200 big blinds (20,000 chips); stacks reset before every hand; positions alternate every hand | https://gtowizard.com/benchmark ; https://arxiv.org/html/2603.23660v1 |
| Cash or tournament | Each hand is independent with reset stacks, so it is chip play, the old Computer Poker Competition rules. The words "cash game" are not used | https://arxiv.org/html/2603.23660v1 |
| Rake, antes | Not stated on their pages for the benchmark (the paper says the agent in general can play with rake) | https://arxiv.org/html/2603.23660v1 |
| Other formats | Heads-up pot-limit Omaha "coming soon". No six-handed game, no tournament game | https://gtowizard.com/benchmark |
| Opponent | GTO Wizard AI, their proprietary agent (the engine behind their custom solutions, from Ruse AI). Beat Slumbot by 19.4 ± 4.1 bb/100 over 150,000 hands | https://gtowizard.com/benchmark ; https://arxiv.org/abs/2603.23660 ; https://blog.gtowizard.com/introducing-gto-wizard-ai/ |
| Opponent version | No version named on the page. Leaderboard rows carry `gto_wizard_version`: 2 on almost all current rows, 1 on a few old ones | https://researcher.gtowizard.com/leaderboard?game_name=HUNL%20200BB&limit=100&min_hands=1 |
| How a bot connects | Plain HTTPS, JSON. `POST /hands` with `{"game_name": "HUNL 200BB"}` starts a hand and returns the state; `POST /hands/{hand_id}/act` with `{"action": "f"|"k"|"c"|"b", "amount": int}` acts and returns the state after GTO Wizard has answered. `GET /hands/in-progress` lists unfinished hands; `GET /results` returns your statistics (optional date range and version); `GET /leaderboard` and `GET /winnings` need no key | https://researcher.gtowizard.com/openapi.json (interactive docs: https://researcher.gtowizard.com/docs) |
| State format | `action_history` tokens: `_` end of round, `f`, `c`, `k`, `bX` where X is the "cumulative bet on round"; `legal_actions`; `raise_range` min and max; `total_pot`; `players` with `position` and `hole_cards`; at the end `winnings` and `aivat_score` in chips | https://raw.githubusercontent.com/gtowizard-ai/researcher-api-client/main/src/models.py |
| Undocumented | The values of `position`, the order of `players`, the card string format, whether `raise_range` is a raise-to total | not stated on their pages |
| Decision time limit for your bot | Not stated on their pages. Their client uses a 180 s request timeout | https://raw.githubusercontent.com/gtowizard-ai/researcher-api-client/main/src/main.py |
| Speed of their side | Not stated on their pages. "Solves any spot in seconds" is the only claim. Their client retries HTTP 502, 503, 504 ("engine busy") with back-off from 2 s to 32 s, up to 32 attempts | https://blog.gtowizard.com/introducing-gto-wizard-ai/ ; https://raw.githubusercontent.com/gtowizard-ai/researcher-api-client/main/src/main.py ; .../src/utils.py |
| Hands at once | At most 20 concurrent hands "as of 2026-04-09"; their client defaults to 5 and recommends a small number | https://raw.githubusercontent.com/gtowizard-ai/researcher-api-client/main/src/main.py |
| Length of a run | No fixed length. One hand is enough to appear on the leaderboard. Their own model runs were 5,000 hands each | https://gtowizard.com/benchmark ; https://arxiv.org/html/2603.23660v1 |
| What it reports | Per hand: `winnings` and `aivat_score`. Per entry: hands, raw bb/100, AIVAT bb/100, its standard error (`aivat_std_bb_per_100`, "standard error; name kept for backward compatibility"), all-hands chips, chance correction, action correction | https://researcher.gtowizard.com/openapi.json |
| Variance reduction | AIVAT: about 3 times lower standard deviation, "ten times fewer hands" for the same significance | https://arxiv.org/html/2603.23660v1 ; https://gtowizard.com/benchmark |
| Ranking | By the lower bound of the 95% confidence interval of the AIVAT win rate | https://gtowizard.com/benchmark |
| Limits | Per user and game: 10,000 hands a day, 25,000 a week, 50,000 a month; resets at midnight UTC (16:00 PST), Monday, and the 1st. "May change at any time." (An April news article said 100,000 a month and a 2,500-hand minimum; the page now says otherwise.) | https://gtowizard.com/benchmark ; https://www.pokernews.com/news/2026/04/gto-wizard-ai-outperforms-gpt-5-and-grok-4-in-new-benchmark-51020.htm |
| Cost | No price anywhere. Access is by a request form; an approved key arrives by email | https://gtowizard.com/benchmark ; https://github.com/gtowizard-ai/researcher-api-client |
| Publicity | Results are public; "no expectation of privacy". You grant a perpetual, irrevocable licence to publish the agent's name, rank, data and full hand histories. Removal or reset of an entry: not stated on their pages | https://gtowizard.com/benchmark/terms |
| Terms on automated play | The agent "must operate autonomously"; human help during live hands is a material breach. No extracting their strategy, no training other solvers on the data, no rate-limit evasion. They may use your play to improve their AI. Access can end at any time for any reason. Keep the key out of public repos; you are liable for all use of it | https://gtowizard.com/benchmark/terms |
| Several bots on one key | Not stated on their pages. The request form takes one `bot_name` and `organization` per user, and `/results` returns one statistics row, so all hands on a key appear to pool into one public entry. `/results` takes a date range, so separate runs can be read apart privately | https://researcher.gtowizard.com/openapi.json |
| Starter code | Python 3.13 + uv; `cd src && uv run python -m main --key YOUR_API_KEY --agent-type allin --num-hands 10`; baselines allin, check_call, random, fold | https://github.com/gtowizard-ai/researcher-api-client |

### Scores other entries have

Published baselines and language models, 5,000 hands each, AIVAT bb/100 (https://arxiv.org/html/2603.23660v1):

| Agent | AIVAT bb/100 | standard error |
|---|---|---|
| GPT-5.3 extra high (best model in the paper) | -16.0 | 3.0 |
| Claude Opus 4.6 | -20.4 | 4.4 |
| Gemini 3.1 Pro | -30.8 | 2.3 |
| Always fold | -64.6 | 1.7 |
| Grok 4 high | -60.0 | 7.7 |
| Check or call | -241 | 13.4 |
| Uniform random | -285 | 15.1 |
| Always all-in | -381 | 2.2 |

A human professional is quoted at about 5 bb/100 against typical opposition (same source). Nobody on the leaderboard is above zero with a real sample.

Live leaderboard, top 100 by rank, any sample size (https://researcher.gtowizard.com/leaderboard?game_name=HUNL%20200BB&limit=100&min_hands=1 ; the endpoint returns at most 100 rows, so weaker entries are not visible there):

- Best real entries: "Competitor" -2.7 ± 0.43 standard error over 225,002 hands; "MikkaMakka" -2.7 ± 0.50 over 204,028; "Trainer" -4.7 ± 0.39 over 321,892.
- Ranks 10 to 40: about -4 to -12. Ranks 40 to 100: about -10 to -25.
- Language models now listed: GPT-6 low reasoning -5.4 ± 2.4 (10,000 hands), GPT-6 extra high -8.8 ± 2.0, GPT-5.5 extra high -9.2 ± 2.8, Claude Opus 4.6 -19.7 ± 2.6 (10,073 hands), Claude Opus 4.5 -19.4 ± 3.3.
- University entries for scale: Marvel (MIT) -4.6 over 124,029 hands; Shakuni (Stanford University) -11.4 ± 3.4 over 3,347; Oski (UC Berkeley) -16.0 over 15,736.
- No row named Avalon, in that list or in the 42 entries with hands since 8 Nov (https://researcher.gtowizard.com/leaderboard?game_name=HUNL%20200BB&limit=100&min_hands=1&start_date=2026-11-08T00:00:00Z). The weakest entries active this week: -31, -34, -37, -63, -102.

---

## 2. Authentication: where the key goes

- **On the wire:** HTTP header `X-API-Key: <key>` on `POST /hands`, `POST /hands/{id}/act`, `GET /hands/in-progress`, `GET /results` (https://researcher.gtowizard.com/openapi.json).
- **In the team's adapter** (`/Users/dylan/Documents/GitHub/nolimit-hub/emu/benchmark/gtow.py`, function `api_key()`, lines 41-47): first the environment variable `GTOW_API_KEY`; otherwise the file `~/.config/gtow.env`, i.e. `/Users/dylan/.config/gtow.env`, a line starting `GTOW_API_KEY=` (quotes around the value are stripped). The docstring asks for mode 600 and "never in the repo".
- **State on this Mac at 01:15:** that file does not exist and the variable is not set in this shell (existence only was checked).
- **To place it without it appearing on screen or in shell history** (key in the clipboard, in your own terminal):

  ```
  umask 077; mkdir -p ~/.config; { printf 'GTOW_API_KEY='; pbpaste; echo; } > ~/.config/gtow.env; chmod 600 ~/.config/gtow.env
  ```

- **The official client** takes the key only as a command-line flag `--key` (https://github.com/gtowizard-ai/researcher-api-client). That puts it in shell history and the process list; prefer the adapter's file.
- **Which entry the hands land on:** the adapter's docstring says the team key's public entry is "Avalon / Stanford University". The name and organization were fixed when the key was requested (form fields `bot_name`, `organization`: https://researcher.gtowizard.com/openapi.json). If the key Dylan holds is a different one, its hands go to whatever name it was requested under.

---

## 3. What already exists in the team's code

**The adapter.** `/Users/dylan/Documents/GitHub/nolimit-hub/emu/benchmark/gtow.py` (305 lines), byte-identical in `/Users/dylan/Documents/GitHub/nolimit-emu2/emu/benchmark/gtow.py`. Committed once, `3e4dee5`, by samrocksnature (Samuel) on 2026-11-11 18:27 PST, inside the commit that added the Finals rehearsal emulator. Copies also sit in eight untracked worktrees under `/Users/dylan/Documents/GitHub/nolimit-live/.claude/worktrees/`. `nolimit-live` itself has no adapter in its tree.

What it does:
- Loads `agent.py` from a bot folder and takes its `Agent` class (the starter-kit interface `Agent.act(state, memory)`).
- For each hand: `POST /hands`, then for every decision rebuilds a kit `GameState` from the API's action history (blinds, events, pot, bets, stacks, legal actions with the raise range), asks the bot, maps the answer to `f`/`k`/`c`/`b` (raise amounts clamped into the range), and posts it. A new `Agent` and empty memory every hand.
- The table it describes to the bot: 2 players, variant `no_limit_holdem`, 20,000 chips, one blind level 50/100, no ante, payouts `(100,)`, phase always `betting`, `state.variant` empty, time bank 1,000 ms.
- Writes one JSON line per hand (hand id, winnings, AIVAT score, actions, history, board) and prints AIVAT and raw bb/100 with 95% intervals every 50 hands.
- Guards: refuses to play without `--yes-public`; stops the run if the pot it rebuilt differs from the API's `total_pot` by more than 1 chip; retries 502/503/504 with back-off; sets a custom User-Agent because "the API's firewall rejects Python's default agent".
- `selftest <bot>`: 2,000 random states through the translation and the bot, offline, no API calls.
- Usage, from the hub root: `starter-kit/.venv/bin/python emu/benchmark/gtow.py play bots/<bot> --hands 500 --out emu/runs/gtow/<name>.jsonl --yes-public` (default 5 hands at once, capped at 20).

Which bots it was written for: "any hold'em bot written for the kit"; the docstring says bots for non-hold'em variants (three hole cards, auctions) cannot play, and records a team decision of 2026-11-11 to benchmark "only avalon's own serious bots with this key". `emu/README.md` line 64 repeats it. No specific bot is named, and on 11 Nov the team had no two-card kit bot: the `bots/` folders in the hub and in `nolimit-live` are all the regional's three-card bots.

Was it ever run, and with what result: **not found.** I looked for `emu/runs/gtow/` and any `*gtow*` file or folder in all four repos (none besides the adapter), for the key file (absent), for a leaderboard row named Avalon (none), and for session transcripts on this Mac that mention running it (none besides this review). The User-Agent comment shows someone made at least one request to the service; the adapter's guess list for the button's `position` string (`SB`, `BTN`, `BU`, `BUTTON`, `SB/BTN`) suggests the author had not seen a real hand state. It may have been run on Samuel's machine; ask him.

Two defects found by reading it (not by running it):
1. **Seat numbering mixes two frames** (lines 120-156). `hero` and `button` are indexes into the API's `players` list, and the events, bets and stacks are keyed by those indexes, but the state handed to the bot hard-codes `seat=0` for us. If the API ever lists GTO Wizard first, the bot sees the opponent's stack and bets as its own and its own actions as the opponent's. The pot guard would not trip (the pot is the same either way) and `selftest` always puts the hero first. Whether the API lists the user first is not stated on their pages; the first live hand answers it.
2. **A bot's own swallowed errors are invisible.** The adapter counts only exceptions that escape `act()`. Last night's bots catch everything inside and play check/fold, counting it in their memory (`x` in v17), which the adapter throws away each hand. A bot that crashes internally on every post-flop decision would show "bot errors 0" and a very bad score.

Smaller points: v17 routes every table through one module-level `_BOT` object, and the adapter plays hands on threads, so concurrency above 1 is untested for it; a stopped run leaves up to 5 hands unfinished on the server.

**Other mentions** (search for gtow, GTO Wizard, gtowizard):
- `prep/docs/BUILD_PROMPT.md:438` and `prep/docs/prompt_template.md:362` (hub, emu2, live): "GTO Wizard's benchmark is stronger and less noisy, but needs an approved key from https://benchmark.gtowizard.com/." `prep/README.md:86`: get a key "only if you want that extra benchmark".
- `finals_pack/notes/pre/testplan.md:112`: AIVAT noted as something nobody can build in the hour.
- `docs/FIRST_PROMPT.md:629`, `finals_pack/strategy/FIRST_PROMPT.md:663`: the benchmark paper in a reading list.
- The rest are GTO Wizard blog articles cited for strategy, and their MIT 2024 entry.
- **The only earlier outside benchmark with results:** Slumbot, 6 Nov, in `/Users/dylan/Documents/GitHub/nolimit-live/prep/benchmark/` (`blend.out`, `blend_def.out`): two pre-regional generated bots, -84.4 ± 34.2 and -36.4 ± 28.1 bb/100 raw over 1,500 and 1,487 hands, same game shape (heads-up, 50/100, 200 big blinds). `prep/README.md:77` already draws the right conclusion: always folding is -75 there, and the gap between the two numbers was luck.

---

## 4. The fit problem

The Finals: a twist on hold'em, six seats, 6,000 chips starting at 10/20 with antes (300 big blinds deep, shrinking to push/fold), scored by finishing place (50/30/20), 1 ms a decision, against a field of AI-built bots. The benchmark: plain hold'em, two players, always 200 big blinds, no antes, scored in chips, no time limit that matters, against one near-equilibrium opponent that does not adapt.

Which bots could play it as they are:

| Bots | Where | Can it play? |
|---|---|---|
| Regional bots v2 to v10, m10 (26 folders) | `/Users/dylan/Documents/GitHub/nolimit-live/bots/` (same in the hub) | No. Built for `flop_discard_reveal`: three hole cards, a `select` phase, pre-flop tables over three-card hands |
| Kit examples `check_or_fold`, `min_raiser` | `starter-kit/examples/` | Yes, but they are not the team's work and the paper already publishes such baselines |
| Pre-regional generated bots `blend`, `blend_def` | `nolimit-live/prep/benchmark/bots/` | Not through this adapter (they are `bot.py` for the Slumbot client, not kit agents) |
| Last night's releases v1 to v17 | `/Users/dylan/Documents/GitHub/avalon-nolimit/releases/` | Mechanically yes, probably: two hole cards, kit interface, and the adapter never sends the `pass` phase. Not verified (nothing was run). But they are not plain hold'em bots: see below |

Last night's bots under the adapter (read from `releases/v17.zip`, the bot that won round 6, and `v15.zip`, the single-file D line):
- **Pre-flop values are for the pass twist.** `avcore/preflop.py`: "pairs are NOT premium in this variant"; `tables/ranking.json` was computed "with the pass modelled". Played as plain hold'em it would undervalue pairs and misorder hands.
- **Post-flop reads assume a pass happened.** With `state.variant` empty the passed and received cards are `None`; the opponent-hand model in `avcore/postpass.py` is built around them. Whether that path degrades cleanly or throws into the catch-all is unknown without a run.
- **Tuned for another depth and payout.** Push/fold tables solved for six players with antes; raise sizes and call limits tuned for a six-seat ante game. With payouts `(100,)` heads-up, its ICM is linear in chips, which is correct here.

What an adapter has to translate (the existing one does all of this, subject to the defects in section 3): the action-token history into kit events; cumulative-per-round bet sizes into raise-to amounts; stacks and bets per seat; who has the button (heads-up the button posts the small blind and acts first before the flop); legal actions and the raise range; a fixed table description; the bot's `Action` back into `f`/`k`/`c`/`b`. What it cannot translate: the twist (there is none to send), a tournament (stacks reset), a field.

What a result would measure: how many chips a bot built in an hour loses per hand to a near-perfect opponent in deep heads-up hold'em. That is a test of post-flop fundamentals: bet sizing, calling too much or too little, bluff-catching, not stacking off 200 big blinds with one pair. It overlaps the Finals in one place: the opening 100 or so hands are 300 down to 40 big blinds deep.

What it would not measure: the twist (the team's main edge last night); six-handed play; antes; short-stack push/fold and ICM, where finishing places are decided; exploiting weak AI-built bots (an equilibrium opponent punishes exactly the wide, bullying play that wins against that field, so a better field bot can score worse here); adapting between rounds; the 1 ms limit and reliability; and the workflow's speed, coordination and release discipline. The regional's lesson stands (`nolimit-live/AGENTS.md`): v4 beat the team's own bots by +4.4 locally and scored 9.17 in the real field. A benchmark number is one more proxy.

---

## 5. Options for "benchmarking the workflow"

### How many hands, how long

Per-hand spread, worked out from leaderboard rows as standard error × √hands (https://researcher.gtowizard.com/leaderboard?game_name=HUNL%20200BB&limit=100&min_hands=1): 200 to 330 bb/100 per hand for real bots (Competitor 204, Trainer 220, Claude Opus 4.6 262, harvey 286, Opus 4.5 327); always-fold 121; check-call and random about 1,000. Using 250 (typical) and 330 (loose bot):

| Hands | 95% interval, typical | 95% interval, loose | What it separates |
|---|---|---|---|
| 500 | ±22 | ±29 | "plays poker" from check-call or random (-240, -285) |
| 1,000 | ±15 | ±20 | a bot at -40 from zero |
| 2,500 | ±10 | ±13 | better or worse than always folding (-64.6), unless within 15 of it |
| 5,000 | ±7 | ±9 | which band: serious bots (-3 to -12), zero-shot language models (-16 to -20), weak (-30 and below) |
| 10,000 (a full day's quota) | ±5 | ±6.5 | two bots 10 apart |
| 20,000 each (most of a week's quota) | ±3.5 | ±4.6 | two bots 5 to 7 apart |

So: distinguishable from zero takes about 1,000 hands, because the bot will be far below zero. Placing it among other entries takes 5,000. Comparing two of the team's own builds takes 10,000 each, which is two days of quota, and small improvements cannot be compared at all inside the weekly cap. For scale, the team's Slumbot runs gave ±28 to ±34 at 1,500 hands; here 1,500 hands would give about ±13.

Wall-clock: **seconds per hand are not stated on their pages.** Time = hands × seconds per hand ÷ hands at once. One weak clue: the paper's cheapest model run took 3.32 hours for 5,000 hands, about 2.4 s a hand including the model's own thinking (https://arxiv.org/html/2603.23660v1; whether that was one hand at a time is not stated). At 5 hands at once: 5,000 hands is about 35 minutes if a hand takes 2 s, 1.4 hours at 5 s, 2.8 hours at 10 s; 10,000 hands is double. The first 100 hands of any run give the real figure; the adapter prints a summary every 50 hands but not the rate, so time it with `time` or the file's line count.

Quota clock: the day resets at 16:00 PST and so does the week (Monday 00:00 UTC is Sunday 16:00 PST). Hands played before 16:00 today count against the week that is ending.

### (a) An existing bot through the existing adapter

- What it takes: the key in place; unzip a release (v17, or v15 as a single file) into a scratch folder; `selftest`; a short attended first run to check the seat order and the bot's own error counter; then the long run. About 15 minutes of attention, then 1 to 3 hours unattended for 5,000 hands.
- What the number means: little. It mixes hold'em fundamentals with an unknown penalty for playing pass-twist pre-flop values in a game with no pass, and possibly with silent check/folds. If it came back at -70 you could not say whether the engine is weak or the mismatch did it.
- Use: as a smoke test of the adapter, and as the "before" figure for option (c).

### (b) The workflow builds a plain hold'em bot from scratch in an hour, then benchmark it

- What it takes: a full timed run of the workflow (both humans steering, three sessions plus subagents, a kit with the twist removed; the emulator's `emu/variants/make_kit.py` is the place to look) then 5,000 hands. Two to four hours end to end, and the session cost of a rehearsal.
- What the number means: the most honest reading of "benchmark the workflow", with one choice to make first. If the build target is the Finals table without a twist, the benchmark tests it in a regime (heads-up, 200 deep, no ante) it only partly built for. If the build target is the benchmark's own game, the number is directly comparable with the leaderboard, including the zero-shot models at -16 to -20 and the always-fold line at -64.6, but it measures a product the team will never ship.
- One run is one sample of the workflow. Run-to-run spread of the workflow is unknown and would need several builds, at 5,000 hands each: the weekly cap allows five.

### (c) Strip the twist from last night's best bot and benchmark that

- What it takes: for v17, regenerate the pre-flop ranking for plain hold'em with the team's own table tool, switch the pass model off so post-flop equity runs against plain ranges, confirm zero catch-alls offline. One implementation agent, 30 to 60 minutes, plus review. Then 5,000 hands.
- What the number means: the hold'em fundamentals of the betting engine the workflow actually produced under event conditions. Better than (a) because the mismatch is removed, cheaper than (b) because nothing is rebuilt. Still heads-up, deep, chips.

### (d) Better uses found

1. **Use the published baselines instead of running any.** Always fold -64.6, check-call -241, all-in -381, random -285, zero-shot models -16 to -31 are already measured (https://arxiv.org/html/2603.23660v1). Spending public hands on baselines under the team's name buys nothing.
2. **Read it as a leak finder, not a score.** Every hand comes back with its own AIVAT score and the adapter saves the action line. Grouping 5,000 hands by situation (folds before the flop, calls of flop bets, river calls, stack-offs) shows where the chips go. That transfers to the event; the total does not. The regional was decided by a flop over-calling leak that the data could have shown after the first practice round (`nolimit-live/AGENTS.md`).
3. **A build-minute ladder, which is the real "benchmark of the workflow".** Strip the twist from three of last night's releases (for example v2 at minute 12, v8 mid-build, v17 at the end) and play 5,000 hands each: 15,000 hands, two days of quota. It answers whether an hour of iteration improved the poker or only the fit to the twist and the field. Differences under about 10 bb/100 will not show.
4. **For the question that matters today, the benchmark is the wrong instrument.** Absolute strength in the Finals format can only come from the Finals field: the first practice round's hand histories, read at once.

---

## 6. Timing reality (01:15, sleep, set-up 08:30, event 11:00)

- **Nothing can produce a meaningful number before 08:30 without human attention.** Options (b) and (c) need building. Option (a) is the only one that can run tonight, and it cannot responsibly start unattended: the adapter has no recorded live run, has a probable seat-frame bug that would silently corrupt play, cannot see the bot's swallowed errors, and every hand it plays is public and permanent under the team's name. It needs about 15 attended minutes first, and its number means little.
- **If Dylan wants a figure by morning anyway:** option (a) with v17, attended for the first 20 hands at one hand at a time, then 3,000 to 5,000 hands under `caffeinate` while asleep. Expect something between the language models (-20) and worse than always folding (-65); either way it changes nothing that can be acted on by 11:00, because the day's bot is built for a twist nobody knows yet.
- **Machine and attention cost today:** a run is network-bound and light on CPU, but it should not share the build machine during the event, and the quota day ends at 16:00 PST in any case.
- **Wait until after the event:** (c), then (d)3 if the first number is interesting, then (b) only if the team wants a publishable "built in an hour" result.

### Paste-ready prompt for the implementation agent (after the event; Opus, effort set explicitly)

```
Read /Users/dylan/avalon-rehearsal-log/analysis/07_gto_wizard_benchmark.md sections 3 to 5 first.
Work in a new folder /Users/dylan/Documents/GitHub/nolimit-hub/emu/runs/gtow/ and a copy of the adapter; do not
touch avalon-nolimit. Never print, read aloud or commit the key in ~/.config/gtow.env. Make NO call to
researcher.gtowizard.com: everything below is offline. Stop and report when done.
1. Adapter (emu/benchmark/gtow.py): remap seats so the state handed to the bot is in one frame (0 = us,
   1 = GTO Wizard) whatever order the API lists players in; add a selftest case with the hero listed second.
   Add --concurrency 1 as the default. After each hand, record in the output line whether the bot's returned
   memory shows a catch-all (v17: key "x"), and print the count in the summary. Log seconds per hand.
2. Bot: unzip avalon-nolimit/releases/v17.zip to emu/runs/gtow/v17_asis/. Make emu/runs/gtow/v17_plain/: the
   same bot with the pre-flop ranking regenerated for plain hold'em (no pass) and the pass model off, so
   post-flop equity uses plain ranges. Change nothing else.
3. Evidence: selftest on both, 0 errors and 0 catch-alls over 2,000 states; 200 local heads-up hands of each
   against the kit's min_raiser at 200 big blinds with 0 catch-alls. Report the numbers and the exact
   command for a 20-hand live run. Do not start it.
```

---

## Could not determine

- Seconds per hand on their side, and whether 5 or 20 hands at once is faster in practice.
- The order of `players` and the `position` strings in a live state (decides whether defect 1 bites).
- Whether one key can hold more than one public entry, and whether an entry can be removed.
- Whether Samuel ran the adapter on his own machine.
- Whether last night's bots run cleanly under the adapter (nothing was executed, by instruction).
- Leaderboard rows below rank 100 (the public endpoint returns at most 100).
