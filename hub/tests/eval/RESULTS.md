# Eval results, 2026-11-13

Round 2 is at the bottom.

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

---

# Round 2 (afternoon)

| Suite | Result |
|---|---|
| Integration | **62/62**, adding clock-change notices (C9) and clock drift against the portal (C10) |
| Deadline guard | 17/17: the portal already runs the chosen bot, so no cut; an expiry never undoes a greenlight |
| Leftover processes (`unit_orphans.py`) | 4/4 |
| Second independent code review of the day's changes | 10 defects found, all fixed |
| Live simulation 2 (Sonnet, build hour + 2 scored rounds, the new prompt pack) | Stopped by hand at 91% weekly usage, during scored round 2. Answers rated 26 good, 3 partial, 0 bad. 5 uploads via the Live menu, 0 rejected, no background errors |

## Fixed in round 2

**From the review: could cost a decision or a round**
- A Greenlight could be lost when a note sync raced with it. The other laptop then expired the note and the default rule ran. Sync now merges the current value, and an expiry never undoes a human decision.
- The T-4 cut could revert a bot already active on the portal, and send Dylan "upload v6 now" and "upload nothing" at the same time. It now checks the portal first and never sends a conflicting upload ask.
- "Data landed" was counted before the hand file arrived. That caused false "card failed" cuts and no "no new data" fallback.
- An empty results list right after a round was called a forfeit and never retried.
- A clock correction re-sent steps already sent (duplicate Build notes, "LATE" labels). Sent steps now carry over.
- The default "Which bot?" note silently failed when the live bot came from `declare_live`, while the alert said it was posted.
- Long notes stopped refreshing their "What's going on" report.
- A file dropped in the Chat was announced before its upload finished. `fetch_file` now waits up to 90 s.
- A merged note could fail to reach the other laptop when the time stamps tied.
- The re-send rule could undo a newer write when the laptops' clocks differ. Re-send now needs a gap of more than 2 s.

**From the live run**
- **Leftover processes.** Stopping or crashing a hub left its agents' `claude` processes and test workers running. A restarted hub would then run a second set beside them. The hub now records its child processes every 15 s, stops leftovers on start, and stops its own on Ctrl+C or a kill signal.
- **Clock drift.** A stray "the competition starts now" moved minute 0 six minutes off the portal for the rest of the run. Every stage label and deadline was off, and one deadline-guard cut came from that. The portal watcher now compares real round starts with the clock and posts the corrected minute 0 in both Chats.
- **Stale Overseer notes** ("upload v14 for practice 3, restore v8 by …") stayed in the bell. They expire after 8 event-minutes, or 15 if urgent.
- **Stale pinned summaries** ("which bot played isn't confirmed" after it was). Summaries show "as of HH:MM, newer updates below", and Overseers are told to rewrite them.
- **Conditional greenlights** ("approve once the tester passes it") no longer declare the bot live or ask Dylan to upload before the condition holds.

**Prompt pack (FIRST_PROMPT.md), for bot strength**
- **Shared defaults for every style**, counted by the check run: no accidental limps or flat calls of opens at 10bb+, shove-or-fold at about 12bb or less, fold one pair to raises. A limp-or-jam style may limp by design. In simulation 1, bots v1-v10 limped and flat-called because nothing checked, and the leak survived into scored round 1.
- **A defaults check heads every round analysis.**
- **Rate-targeting candidates** must show their rate in a local run, within about 5 points, before they ship. This is the 74.6% → 92.8% lesson; DECISION_RULES.md says the same.

---

# Round 3 (night): the lean hub

**What changed.** Four agents per laptop, one job each:
- Samuel: Chat (the lead), Analyst, Tester, Opponents.
- Dylan: Chat (the lead), Platform & releases, Styles & fixes, Challenger.

The clock hands each worker its task directly. The board shows plain progress tiles, and a tile opens the agent
doing it. Decisions are pinned in the Chat and answered in words. There are no ideas, no prompting notes and no
narrator.

| Suite | Result |
|---|---|
| Static (pyflakes: undefined names; JS syntax) | 0 / OK |
| unit_lean (roster consistency, tiles, decisions, dispatch, worker-reply tracking, Live menu) | 25/25 |
| unit_guard, unit_decisions, unit_watchdog, unit_polling, unit_sync_race, unit_orphans | all pass |
| Integration (two linked hubs, fake portal, agents off) | **76/76** |
| Screens (tiles, Chat in the agent list, decision pinned, agent page, 390 px, no errors) | all pass |
| Redraw with a full day's data (300 tiles, 200 decisions, long Chat) | board 8 ms, Chat 7 ms (median) |
| Plan battery, 22 scenarios (6 new worker ones), tune and held-out, peer pressure, Sonnet + Haiku | base 100% on both splits; see below |
| Live simulation (Sonnet everywhere, build hour + 3 scored rounds, 2 simulated teams, AI Samuel and Dylan) | Ran to the end. 6 uploads via the Live menu, 0 rejected. Decisions answered in words and recorded with the person's words. Answers rated 63 good, 23 partial, 1 bad. errors.log empty. The clock-drift alert fired live and was corrected |

**Reinforcement experiment.** With the plan out of context and a peer pushing the wrong answer:
- **System prompt rules only** (as now): 100% on the tuning and held-out scenarios, Sonnet and Haiku.
- **A pinned rules card:** no gain.
- **A self-check:** broke the answer format twice.
- **A generic rule reminder:** caused the one held-out error.

So no rule reminders are added. The problems we saw are about state (stale briefs, missing context, silence), and
that's what the hub now handles.

**Fixed from this round's live run and review:**
- A human's message to a worker went unanswered three times; the agent kept working silently. Every message to any
  agent is now tracked until that agent replies in text. Its first sentence must be the answer or "working on it,
  ready by HH:MM". It's re-raised at 150 s, and the person's Chat is told at 6 min.
- The leads (the Chats) can't speak without a turn, so they no longer promise later messages. Dylan's Chat is now
  woken with each round result.
- Duplicate tiles appeared when an agent's label differed from the hub's (e.g. "Build · Test rig"); they now merge.
  Agents' stage spellings are normalised ("Practice-1"). Old analysis tiles close when the next round lands.
  Releases found on disk are owned by Platform.
- The Live menu always lists the live and the active bot, however many newer bots exist. Bots were built at about
  one every 3 minutes in the run.
- The contradiction check was too chatty. It now posts at most one item, drops reworded repeats, and ignores
  uploads in progress and lagging briefs.
- Hub messages never appear under a person's name. Compaction output never reaches the Chat. Pre-flight results
  show as a list. Decisions are pinned above the conversation.
- Worker processes that detached from the hub (a test rig's workers) are stopped at shutdown too.

**Not covered:**
- Two physical laptops on a hotspot.
- The real portal (its round ids and timing).
- Opus agents for a full 6-round event.
- An 8-seat field.

The emulator's 3-seat field and rounds of about 2 minutes made some simulated complaints artifacts, not hub bugs.
