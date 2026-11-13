# Eval results, 2026-11-13

Checklist: `hub/tests/EVAL_CHECKLIST.md`. Each test, how to run it:

| Suite | Command (from the repo root unless noted) | Result |
|---|---|---|
| Integration: two linked hubs, fake portal, agents off | `uv run --no-project --with aiohttp==3.14.5 --with claude-agent-sdk==0.2.181 --with modal==1.6.4 python hub/tests/eval/integration.py --out /tmp/eval` | **60/60** (first run 43/55) |
| Deadline guard | `… python hub/tests/eval/unit_guard.py hub` | 15/15 |
| Stall watchdog + long turns | `… python hub/tests/eval/unit_watchdog.py hub` | 6/6 |
| Note sync under races (random 0-300 ms link delays) | `… python hub/tests/eval/unit_sync_race.py hub` | 12/12 converge |
| Screens, Samuel's and Dylan's (Playwright) | integration with `--keep --ports 7821,7822,8821`, then `uv run --no-project --with playwright python hub/tests/eval/screens.py <outdir>` | 40/46. The 6 misses: 4 were wrong selectors in the test (fonts, chips), 2 were the duplicate countdown, now fixed |
| Live simulation: build hour + 3 scored rounds, Sonnet everywhere, 2 simulated teams, AI Samuel and Dylan | `hub/tests/eval/live_sim.sh` (+ `live_sim_watch.py`, which stops at 92% weekly usage) | Ran start to finish, ~65 min. 9 uploads via the Live menu, 0 rejected. Teammates rated 33 answers good, 6 partial, 0 bad. Hubs restarted 4 times mid-event to load fixes; agents resumed each time |

## Bugs found and fixed (all committed on emu/rehearsal)

**Could lose a round**
- A results fetch that failed once skipped the whole round: no hands, no card, no agents told. Now retried every poll; alert after 3 tries, give up after 15.
- Agents heard about new data only after the round card had run (90 s+); a failing fingerprint script stopped the card from reaching Data/Skeptic/Tester. Agents are now told at once; the card and fingerprint scripts run in the background, side by side.
- A note changed on both laptops within a few seconds (Samuel asks, Dylan closes) kept different versions forever. Notes now merge (read-merge-write with a verify step); every other shared value re-sends a newer copy it sees overwritten.
- A hub restart lost data-landing times (false "data hadn't landed" cut), values not yet uploaded to the other laptop, and clock steps due during the restart. All three survive now; missed steps fire late, marked LATE.
- Background loops (portal, clock, link, live-bot watcher) could die silently on one error. They restart themselves and log to `errors.log`.
- An agent whose connection hangs stayed "working" forever. 12 min with no output → interrupt, then reconnect; the task resumes.
- An impossible start time ("25:99") was accepted and moved the clock to tomorrow.

**Confusing on the day**
- Changing minute 0 was silent, so the Chat kept quoting the old times. Both Chats and both Overseers are told now, and steps already sent aren't re-sent.
- The bell filled with stale items: ten "used 80%" notes (one per agent), "Decision time" after the decision, "upload v3 now" after v4 went live. Now there's one usage note, and the rest clear themselves. Rejection alerts are never cleared automatically: an early version of this cleanup hid one, and the suite caught it.
- "vN live" notes stayed "running" after their round (the mock portal changes round ids). They now close by stage.
- Old analysis notes never closed. Now only the newest two stay open.
- After the last scored round the board showed "Round 3.5", a practice round that doesn't exist.
- The countdown strip repeated the plan's guess ("practice 3 plays style C") when another bot was chosen. It now names only the event and time.
- Build notes for agents that start later had an empty "Plan:" line.
- Agent status lines go stale. Agents are now told to update on every step, and briefs older than 10 minutes are labelled stale in what the Chat and Overseers read.
- The deadline guard's card check looked in one exact folder. Any card file, or a ledger record tagged "card", now counts.
- The "What's going on" summary called a rejected bot "the challenger". Its prompt now forbids roles the material doesn't state.
- Attachments from the other laptop didn't open in its Chat view. They're fetched from the shared store now.

**Strategy process (in DECISION_RULES.md)**
- In round 3 a change aimed at a 74.6% fold-to-3-bet rate played at 92.8%. Only "the branch fired" had been checked. A rate-targeting change must now show its rate in a local run (within ~5 points) before it ships.

## Seen working in the live run
- Clock and Overseer dispatch by minute.
- The Chat answering status questions honestly, including "I can't see that".
- Permission requests answered from the bell.
- The pre-registered T-8 decision with a written pull-back rule.
- Uploads through the Live menu download.
- The portal watcher, analysis notes, hand data and fingerprinting (lagged 95% at 20 hands on this tiny field).
- The deadline guard. It cut the round-3 change correctly: s-data's proposal came 4 s after T-8 and went to the challenger, and nobody rushed.

## Not covered yet
- Two physical laptops on a hotspot.
- The real portal.
- Opus agents for a full 6-round event.
- An 8-seat field: the emulator with 2 teams gives 3-seat tables.
- A conditional greenlight ("upload v13 once the tester passes it") still triggers the upload ask at once.
