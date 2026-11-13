# Finals: start here

For Dylan and Samuel. This assumes you remember the Bay Area regional and nothing since. Read this first
(about 20 minutes). Then read `docs/SUNDAY.md` (the day itself, minute by minute) and, before any practice
run, `docs/REHEARSAL.md`. Everything else is reference. Last updated Thursday 12 November, night.

## 1. The short version

- **The Finals:** Sunday 15 November, San Francisco. 20 teams, no house bots. The variant is announced
  at the start. We may bring prompts and notes, but no pre-written bot code. Andrew Gu (organizer)
  confirmed that general infrastructure that isn't bot code is allowed, which includes the hub below.
- **What changed since the regional:** we no longer run a pile of Claude sessions by hand. Each of you
  runs one **hub** on your laptop, a web page with a team of Claude agents behind it. You talk to **one
  agent, your Overseer**. It runs everything else, and asks you only for what needs a person: ideas,
  greenlights, uploads.
- **Your jobs on the day:**
  - **Samuel** steers analysis and testing, and greenlights or redirects what the agents find.
  - **Dylan** decides what plays, with his Overseer, and does the uploads on the organizers' website.
  - **Both** of you post ideas and catch what the agents miss. Agents miss things, so we keep you in the loop.

## 2. What we learned since the regional

At the regional we finished 6th (376.71). 2 Curry won with 428.72, about 2.5 points per table per round
more than us.

- **Our own mistakes cost about 22-25 points; fixing them alone would have put us about 3rd.** They were:
  - over-calling flop and turn bets;
  - over-folding after v6;
  - the starter kit's ICM function scoring a busted stack as 0;
  - folding 82-89% to re-raises.

  v10 also had two counting bugs: an inverted raise-frequency stat, and folds to our own bets that were
  never counted.
- **Style mattered, and one rule in particular.** 2 Curry opened about 40% of hands, re-raised wide, and
  tracked each seat: it re-raised a fresh opener 18% of the time, 43% after that seat had folded to one
  re-raise, and 62% after two. We folded to most re-raises, so it kept re-raising us. Ten of the other
  19 top teams had a per-seat rule like this.
- **Almost everyone changed their bot every round (78-90% of teams).** For strong teams, changing only
  kept them level, so the bot at the end of the build matters a lot, and you still have to keep improving.
- **The Finals field is harder.** Every finalist knows wide re-raising won. By round 5 at Boston, the top
  teams already folded only 58% to re-raises and re-raised back 23% of the time.
- **Big jumps come from rewrites, mostly for teams far behind.** For top-20 teams, rewrites lost 0.68
  points on average.
- **Bet sizes identify a team quickly:** the right team is named 73% of the time by hand 20. Hiding our
  sizes costs value and works for one round at most, so we don't hide them. Instead we avoid big
  exploitable gaps, such as folding 89% to re-raises when the field folds 65%.
- **No style wins everywhere; they form a cycle.** In simulation:
  - wide re-raising beats a field of tight bots;
  - limp-or-shove beats a field of wide re-raisers;
  - tight beats a field of shovers.

  So we build all three and let the real field choose.
- **Expect lower scores:** about 14-15 points per table against a field of only strong teams, not 18-20.
  The average is 12.5.

How sure we are of each of these: `docs/EVIDENCE_TABLE.md`.

## 3. The game plan

1. **Build hour.** At minute 0 Dylan's Overseer starts building:
   - a minimal legal bot by minute 10;
   - a test harness by minute 15;
   - today's hand ranking and the twist's value by minute 20;
   - then **one shared platform** (rules, equity, per-seat counters, memory, safety) with **three
     styles** on top: wide pressure (A), shove-heavy (B) and tight (C).

   Practice rounds at minutes 20, 30 and 40 each play a different style, and minute 50 re-plays the
   leader. The best real score goes live for scored round 1.
2. **Every 20 minutes after that:**
   1. a scored round lands;
   2. Samuel's side analyses it;
   3. Dylan's side builds a challenger and fixes;
   4. the challenger plays the practice round 10 minutes before the next scored round;
   5. you decide together what plays: the live bot, the live bot plus **one** tested change, or the challenger.
3. **Adapt to individual seats, not to the "table mood".** Per-seat counts are blended with what we know
   about each team, and every adjustment is capped. Against seats that raise a lot, call down and re-raise
   wider; folding more is the wrong answer to aggression.
4. **Evidence before shipping, but standing still isn't safe.** An analysis that sounds convincing is a
   candidate until the real field (a practice round) has tested it; candidates go into the challenger and
   practice rounds quickly. Folding to a 3-bet of our open: no more than break-even (usually 65-75%).

## 4. The hub: how it works

### What you see

Each of you opens **http://127.0.0.1:7777** on your own laptop and clicks your name.

**The board is the whole screen by default.** Everything the agents want you to see is a sticky note
with a one-sentence, plain-English headline. The note's colour and label say what it is:

| Note | Label | What it is |
|---|---|---|
| Green | **Live bot** | which bot plays the next scored round; needs a greenlight (either of you) |
| Yellow | **Suggestion** | a proposed change to the bot; needs a greenlight |
| Lavender | **Analysis** | a finding from the latest round |
| Teal | **Research** | work an agent is running |
| Blue | **Your idea** | something you or your teammate posted |

At the top of the board, **Now** shows the stage, which bot the portal is running, decisions waiting for you,
and what every agent on both laptops is doing at this moment. Each note shows its progress (e.g. Data ✓ ·
Numbers ✓ · Angles 2/3 · Checked · Summary), its key number (e.g. 3rd of 3 · 27.75 pts/table), who is on it,
and a green pulse while it is being updated. The board has three rows: **Needs your call** (big notes with Greenlight / Reject on them),
**Being worked on** (with a **+ New idea** note to post your own) and **Recent**.
To tidy up, hover a note and click the small **x** in its corner (or **Remove** inside it), or press **Clear finished** next
to Recent. Removing a note that's still being worked on tells the agents to stop work on it; it's gone
from both laptops.

**Click a note** to open it almost full screen, like a Claude chat. At the top, **What's going on** is
written fresh when you open it (about 10 seconds), in plain language: where it stands, what we found (with
how sure we are), what's running, what's next, and what we need from you. Below are the conversation and a
folded activity log. Ask anything ("why?", "how sure are you?") or give an instruction ("try it at 30bb
instead"): it goes to the Overseer, which hands it to the right agent and answers there. If it's your call,
the Greenlight and Reject buttons are there too, and anything you type counts as "do this instead".

**Chat** (docked on the right of the board; the header button shows or hides it) is your main conversation, and
together with the board it is all you need on the day. Tell it when the competition starts ("the competition
starts now", or the announcement time) and any times you learn ("round 1 is at 14:25"): that sets the clock on
both laptops and starts the Overseer with the whole game plan. It is a readable chat that knows everything your
Overseer knows (the ledger, every agent's brief, the notes, the Overseer's recent work). Ask "what's going
on?", "what should I be doing?", "why v5?"; tell it what to change and it passes that to the Overseer and
reports back. Tabs switch between **your Chat and your teammate's**, so either of you can ask about, or
steer, the other side. You don't prompt the Overseer directly: it coordinates the agents and keeps the
context; the Chat is the window onto it.

**Header:** your name, a big countdown to the next step of the day (amber under 3 minutes, red under 1),
**Live**, **Chat** (the bot the portal is running; the menu lists every bot, built or in progress, and
downloads a bot's zip for you to upload), the **bell** and **⋯** (the agents' own pages, for emergencies only).

- **Bell:** everything that needs you: notes waiting for your call, permission requests, and messages
  from your Overseer. New ones pop up briefly in the corner; the browser tab shows the count.
- **⋯** opens the agents' side panel, which you shouldn't need: Board, Overview (every agent at a glance),
  your agents, hub services and, behind its own **Show** button, your teammate's agents. Clicking an agent
  opens its page:
  - a **brief** pinned at the top (Now / Latest result / Next / Needs from you);
  - its activity, with tool steps folded into one line and agent-to-agent messages as one-liners;
  - a message box with quick buttons (Status?, Why?, Blocked?, Change priority).
- **Before minute 0** the board shows a big **Start building** button. Press it the moment the variant
  is announced: the clock starts on both laptops and your Overseer starts the plan. (If you're late, type
  the announcement time next to it instead.)

Agent dots: green working, grey ready, dashed off, amber waiting for you, red error or usage limit.

Samuel's things are marked indigo, Dylan's rose.

### Who's who

| | Samuel's laptop | Dylan's laptop |
|---|---|---|
| **Overseer** (the one you talk to) | Runs analysis and testing. Turns each round into findings and a recommendation, sent to Dylan's Overseer at T-8 | Owns the bot and the plan. Decides what plays, with Dylan's greenlight, and tells Dylan exactly which file to upload |
| Worker | **Pipeline**: turns each round's hand data into a standard "round card" of numbers within a minute; woken automatically when data lands | **Platform**: the only one editing the main bot code; sets the rules card at minute 0; packs and checks every release (v1, v2, ...) |
| Worker | **Analyst**: what the numbers mean: our biggest leaks, opponents, the changes worth making (up to three) | **Builder**: styles A, B and C plus challengers, each in its own folder of its own copy of the repo |
| Worker | **Tester**: a verdict on every candidate, "correct?" and "stronger?" (paired tests on Modal, at the table size on the rules card) | |
| Worker | **Skeptic**: re-runs the numbers behind anything a decision rests on; marks results validated or disputed; can invalidate a wrong method, which flags everything built on it | |
| Hub services (plain code, not agents) | **Clock**, **Portal watcher**, **Codex** | **Clock**, **Codex** |

- **Overseers talk to people. Workers talk to their Overseer and to any other agent, on either laptop,
  directly.** Nobody needs you to carry messages: Samuel's Analyst can hand a fix straight to Dylan's
  Builder, and Dylan's Overseer asks Samuel's Overseer for the analysis itself.
- **The Clock** knows the schedule. It wakes the Overseers at every step and reminds you directly when a
  step needs your hands, e.g. "Dylan: put the live bot back as active now". Every Overseer turn starts
  with a brief from the hub: the exact phase, the current step, the next deadline, the live bot, and
  what's active on the portal.
- **The Portal watcher** (Samuel's laptop) reads the organizers' website every minute. It's read-only and
  never uploads. It saves each finished round's results and our hand histories, wakes the Overseer, and
  raises an alert if an upload is rejected, if there's no active bot, or if the active bot isn't the
  one we decided on.
- **Parallel work.** Each agent can start its own helpers:
  - up to 4 Claude subagents;
  - jobs on **Modal**: shared cap of 80 containers, about $300 budget;
  - jobs on **Codex** (OpenAI, separate credits), up to 3 at once.

  So more work happens at once without more screens for you.

### How you steer

- **Talk to your Chat** in plain language: "focus on the flop leak first", "why did you pick
  style B?", "round 1 is in 5 minutes". It passes instructions (and times, which update the clock on both
  laptops) to the Overseer. Your instructions go to the top of every agent's context.
- **Post ideas** on the board → + New idea. Your Overseer plans them, runs them and posts the result back
  on the note. Your ideas come before its own plans.
- **Greenlight, reject or redirect.** Agents can't act on their own analysis:
  - every **finding** goes on the board for you to see;
  - every **proposed change** and every **live-bot decision** waits for a greenlight;
  - "Suggest instead" sends your alternative back as an instruction.

  Live-bot decisions can be greenlit by either of you. Other notes say whose call they are.
- **Defaults keep things moving.** If nobody answers a live-bot decision by T-5, the pre-registered rule's
  answer plays (the challenger if it cleared the bar, else the live bot). If
  nobody answers a permission request in 3 minutes, it's refused and the agent finds another way.
- **Permissions:** ordinary commands are approved automatically. Risky ones always wait for a click.
  Risky means deleting outside `/tmp`, force pushes, killing processes, Modal deletes, any write to
  the organizers' website, and writes outside the repo.

## 5. Who does what

| | Dylan | Samuel |
|---|---|---|
| Owns | The bot and what plays; **every upload** on the organizers' website; confirming the active bot | Analysis and testing; the recommendation each window; the portal watcher runs on his laptop |
| Talks to | Dylan's Overseer | Samuel's Overseer |
| Greenlights | Live-bot decisions, changes to the bot | Findings and changes from his side; live-bot decisions too |
| Hands-on moments | Upload at minute 10, before each practice round in the build hour, T-12 (challenger), T-9 (live bot back), T-3 (chosen bot) | Set the clock at minute 0; copy the hand-history link after practice round 1 (`SUNDAY.md` step 7) |

You decide together at T-8. If you disagree and there's no time, the live bot plays.

## 6. The timeline (the agents follow this too)

**Build hour** (minutes from the variant announcement):

| Minute | What happens | Who |
|---|---|---|
| 0-5 | Kit fetched; Format page read (round weights, payouts, anything unusual); Dylan's Overseer starts Platform on the first prompt with `TWIST_NOTES.md` | Both |
| by 10 | Minimal legal bot uploaded and active | Dylan |
| 15 | Test rig running (paired runs, sparring) | Samuel's side |
| 20, 30, 40 | Each practice round plays a different style | Dylan uploads |
| 50 | Practice round re-plays the leader. Then hands off: the best real-field scorer is active for scored round 1 | Dylan |

**Every window after that.** A practice round starts 10 minutes before each scored round and plays
whatever bot is active, so each window has two uploads.

| Time to scored round | What happens | Who |
|---|---|---|
| T-20 | Previous scored round starts. The challenger is already packed and tested | |
| T-13 | Previous round's result and hand data land; Samuel's side analyses | Samuel's side |
| T-12 | Challenger uploaded and active (skip if not ready) | Dylan |
| T-10 | Practice round plays the challenger | |
| T-9 | Live bot put back as active straight away | Dylan |
| T-8 | **Decide** by the pre-registered rule (`DECISION_RULES.md` §3): the challenger if it clears the bar for our standing, else the live bot with this window's changes (up to three). The "Which bot?" note shows the rule's answer | Both |
| T-6 | Chosen bot tested with no time bank | Dylan's side |
| T-5 | No human answer means the rule's answer plays | |
| T-3 | Chosen bot uploaded; active bot confirmed | Dylan |

Once the live bot is back at T-9, a missed deadline means the previous live bot plays: that is a failure to
fix, not a safe outcome (bots that stood still lost as much as bots that changed). Only tested zips are ever
uploaded.

## 7. How we decide

The full rules are in `docs/DECISION_RULES.md`; every agent has them in its instructions on every turn.

- **Goal:** a top-3 finish (only 1st-3rd pay). Standing still is not safe.
- **Live bot:** up to three independent changes per round, each in a different situation and behind its own
  setting.
- **Challenger:** two to four changes, a new style, or a fresh rewrite. Default design: the best response to
  the field's measured mix of styles, not to the leader.
- **Which bot plays:** the challenger if it beats the live bot on the real field by 1.0 SE or more when we're
  outside the top 3 or behind 3rd (0.5 SE in the last two rounds), or by 1.5 SE when we're in the top 3. If
  nobody answers in time, the rule's answer plays.
- **Folding to re-raises:** fold to a 3-bet of our open no more than break-even (usually 65-75%); this is a
  starting value, and it doesn't apply to folding to 4-bets after our own light 3-bets.
- **Bolder:** a fresh rewrite in the challenger slot when we're outside the top 6 after 15% of the total weight;
  plan the last round (often 25-40% of all points) from the round before.
- **What counts as evidence, in order:**
  1. real-field results (practice and scored);
  2. replay testing;
  3. the cloned field, which is a warning light, not a ranking.

  Beating our own bots proves nothing.
- **Never block a change because it makes us look unusual.** The regional winner looked nothing like
  the average team.

## 8. Accounts, money and keys

| What | Where | Notes |
|---|---|---|
| Claude | Each of you on your own subscription | Agents run on it. If an agent runs out of its Opus allowance it switches to Sonnet by itself; if the whole subscription runs out, it pauses until the reset (shown in the bell) |
| Anthropic API key (optional overflow) | `~/.config/avalon-hub/anthropic-api-key` | If this file exists, an agent that hits the subscription limit switches to the key (billed per use) and carries on. Samuel chose not to add one; auto-reload is on |
| OpenAI / Codex | Samuel's laptop: Codex logged in with the API key ($1,000 credit) | Jobs try the strongest model and fall back to `gpt-5-mini` if OpenAI rate-limits. Dylan can do the same: `pbpaste \| /Applications/Codex.app/Contents/Resources/codex login --with-api-key` |
| Modal | Team workspace (Dylan's), about $300 | Rehearsal tournaments and the agents' simulations |
| Organizers' portal | Samuel's key: `~/.config/no-limit-2026/api-key` | Only the portal watcher uses it, read-only |
| $250 Codex credit (event) | Goes to whichever account opens the link first | Decide who claims it before anyone clicks |
| Tailscale | Both laptops, Samuel's Mac shared with Dylan | Only for rehearsals, so Dylan can reach the rehearsal portal on Samuel's Mac |

## 9. The documents

| Document | When |
|---|---|
| `docs/START_HERE.md` (this) | Now |
| `docs/SUNDAY.md` | The night before and on the day: exact commands and steps |
| `docs/REHEARSAL.md` | Before any practice run |
| `hub/README.md` | How the hub works inside; every option |
| `docs/TWIST_NOTES.md` | Used by the agents at minute 0: valuing the variant's twist |
| `docs/FIRST_PROMPT.md` | The prompt pack the agents follow (you don't paste these any more) |
| `docs/PORTAL_AGENT.md` | Notes on the organizers' API (the watcher already uses them) |
| `docs/EVIDENCE_TABLE.md` | How sure we are of each finding |
| `docs/FINALS_PLAYBOOK.md` | The longer reasoning behind the plan |
| `docs/Finals_Handbook.pdf` | This, `SUNDAY.md` and `REHEARSAL.md` as one printable file |

## 10. Known limits and open questions

- **Not yet tested:** two real laptops on a phone hotspot, a full 3-hour run at real speed, and the
  Anthropic API-key overflow.
- **Pittsburgh's variant** isn't known.
- **The hand-history download address** isn't in the organizers' code. Samuel copies it once after the
  first practice round (`SUNDAY.md` step 7).
- **The agents are good but not careful.** In simulations they:
  - used last rehearsal's data until caught;
  - asked for things nobody can see;
  - reported a "+36 points" test result that turned out to be a broken test.

  Read their findings with suspicion and ask "why?".
