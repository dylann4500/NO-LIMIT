# Finals: start here

For Dylan and Samuel. This assumes you remember the Bay Area regional and nothing since. Read this first
(about 20 minutes). Then read `docs/SUNDAY.md` (the day itself, minute by minute) and, before any practice
run, `docs/REHEARSAL.md`. Everything else is reference. Last updated Friday 13 November, night (lean hub: four agents per laptop, progress board, decisions in the Chat).

## 1. The short version

- **The Finals:** Sunday 15 November, San Francisco. 20 teams, no house bots. The variant is announced
  at the start. We may bring prompts and notes, but no pre-written bot code. Andrew Gu (organizer)
  confirmed that general infrastructure that isn't bot code is allowed, which includes the hub below.
- **What changed since the regional:** we no longer run a pile of Claude sessions by hand. Each of you
  runs one **hub** on your laptop, a web page with four Claude agents behind it, each with one clear job
  (your **Chat**, which leads your side, plus three workers). The clock gives every worker its task at the
  right minute; the board shows plain progress tiles; you open any agent to read its work, steer it or ask
  it to research something. Decisions are asked in your Chat in plain words.
- **Your jobs on the day:**
  - **Samuel** follows analysis, testing and opponents (open the Analyst, the Tester, Opponents), and steers.
  - **Dylan** decides what plays with his Chat, and does the uploads on the organizers' website.
  - **Both** of you answer decisions in words and catch what the agents miss. Agents miss things, so we keep you in the loop.

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
  re-raise, and 62% after two. We folded to most re-raises, so it kept re-raising us. Three other top-20 teams
  had a strong rule exactly like this; ten had a strong per-seat response of some kind.
- **Almost everyone changed their bot every round (78-90% of teams).** Top-20 teams fell back about 0.65
  points per round whether they changed or not, so freezing never holds a lead.
- **The Finals field is harder.** Every finalist knows wide re-raising won. By round 5 at Boston, the top
  teams already folded only 58% to re-raises and re-raised back 23% of the time.
- **Big jumps come from rewrites.** For top-20 teams, rewrites averaged the same as standing still (−0.68 vs
  −0.67) but with three times the spread: 24% improved, by up to +3.8; no unchanged team did. With only the
  top 3 paid, that upside is worth having.
- **Bet sizes identify a team quickly:** the right team is named 73% of the time by hand 20. Hiding our
  sizes costs value and works for one round at most, so we don't hide them. Instead we avoid big
  exploitable gaps, such as folding 89% to re-raises when the field folds 65%.
- **No style wins everywhere.** In simulation (Bay Area variant, pure fields only) they formed a cycle:
  wide re-raising beats tight, limp-or-shove beats wide re-raisers, tight beats shovers. In realistic mixes
  the differences were small and the simulation couldn't rank strong teams. So the styles are starting
  points, one design is built fresh from today's rules, and the real field chooses.
- **Expect lower scores:** a field of only strong teams averages 12.5 points per table; our regional bots
  simulate at 14-19 against it, depending on the fit. Don't panic at a 15.
- **The field moves.** Boston's top 20 went from folding 75% to re-raises to 57.5% by round 5 and partly back.
  Finalists studied both regionals, so expect them to start near that point and keep moving. **The plan is a
  default, not a mandate:** an agent that sees the plan is wrong for today's field raises a *plan challenge*
  to both of you.

How sure we are of each of these: `docs/EVIDENCE_TABLE.md`.

## 3. The game plan

1. **Build hour.** At minute 0 the clock starts Dylan's Platform agent building:
   - a minimal legal bot by minute 10;
   - a test harness by minute 15;
   - today's hand ranking and the twist's value by minute 20;
   - then **one shared platform** (rules, equity, per-seat counters, memory, safety) with **three
     styles** on top: wide pressure (A), shove-heavy (B) and tight (C).

      From minute 0 the Challenger also builds **design D from scratch**: from today's rules only, without our
   regional style notes. Practice rounds at minutes 20-50 each play the most informative candidate (Dylan's
   Chat picks; one is D), every one with the newest shared tables so the comparison is fair. The best real
   score (adjusted for the field and the round size) goes live for scored round 1.
2. **Every 20 minutes after that:**
   1. a scored round lands;
   2. Samuel's side analyses it;
   3. Dylan's side builds a challenger and fixes;
   4. the challenger plays the practice round 10 minutes before the next scored round;
      5. you decide together what plays: the live bot, the live bot plus the tested changes that cleared the bar,
      or the challenger.

   Each window the Opponents agent also writes the **field trend** (what the field and the top 5 do now, and
   which plan assumptions still hold), and the Analyst's **winners lens** asks what the best teams do that we
   don't. Until about 30% of the weight is played, at least every other practice round plays a genuinely
   different design, not a tweak: one practice round can't measure small tweaks anyway.
3. **Adapt to individual seats, not to the "table mood".** Per-seat counts are blended with what we know
   about each team, and every adjustment is capped. Against seats that raise a lot, call down and re-raise
   wider; folding more is the wrong answer to aggression.
4. **Evidence before shipping, but standing still isn't safe.** An analysis that sounds convincing is a
   candidate until the real field (a practice round) has tested it; candidates go into the challenger and
   practice rounds quickly. Folding to a 3-bet of our open: no more than break-even (usually 65-75%).

## 4. The hub: how it works

### What you see

Each of you opens **http://127.0.0.1:7777** on your own laptop and clicks your name.

**On the left: Board, then your agents (your Chat first), then hub services, then your teammate's side** (behind
**Show**). That list is how you get around: click the agent whose job you want to check.

**The Board** shows progress only, as plain tiles grouped by stage (Build hour, Practice 1, ..., Round 2), newest
stage first; past stages fold away (click to open, "▾ Collapse" to close). A tile says what and where it stands,
nothing else: "Round 1 data · in progress" (the download started) → "done"; "Round 1 analysis · in progress" →
"done"; "Bot v4 · testing" → "done"; "Practice 3 · playing v4" → "finished"; "Build · Maths tables · in progress".
**Click a tile to open the agent doing it.** At the top, **Now** shows the stage, which bot the portal is running
and every agent's state. A red bar appears when a decision waits for your answer.

**Your Chat** is the lead of your side and your main conversation. Tell it when the competition starts ("the
competition starts now", or the announcement time; the hub starts the clock on both laptops itself) and any times
you learn ("round 1 is at 14:25"). Ask it anything ("what's going on?", "why v5?"); tell it what to change and it
hands the work to the right agent and reports back. **Decisions are asked here**: a red box pinned at the top
says what is being decided, the evidence and the rule, what each answer means, and the deadline. You answer in
your own words ("yes, use v13", "no, keep v8 because…"); nothing is decided until you answer clearly, and with no
answer by the deadline the pre-registered rule decides. Tabs switch between **your Chat and your teammate's**.
Drop or paste files (hand data, screenshots) into the Chat: they're staged and sent with your next message.
Type "run the check" before the start to test everything (link, portal reading and a hand download, Claude,
Codex, the repo, disk) on both laptops.

**An agent's page:** its **brief** pinned at the top (Now / Latest result / Next / Needs from you), then its
activity in plain text (tool steps folded into one line, messages to other agents as one-liners), and a message
box with quick buttons (Status?, Why?, Blocked?, Change priority). What you type there is an instruction to that
agent: it does it first or says why it can't. Use it to steer ("do the 3-bet sizing first") or to ask for research
("check whether team X adapts to us after hand 40").

**Header:** your name, the countdown to the next step (amber under 3 minutes, red under 1), **Live** (the bot the
portal is running; the menu lists every bot and downloads a bot's zip for you to upload), the **bell**
(permission requests, decisions waiting, urgent messages; the screen edges pulse red while something needs an
answer within minutes) and **☰** (show or hide the agents list).

Agent dots: green working, grey ready, dashed off, amber waiting for you, red error or usage limit.
Samuel's things are marked indigo, Dylan's rose.

### Who's who

Four agents per laptop, one job each, so you know which one to open:

| | Samuel's laptop | Dylan's laptop |
|---|---|---|
| **Chat** (the lead; you talk here) | Leads analysis, testing and opponents; sends Dylan's Chat the recommendation at T-8 | Leads the bot; asks the "which bot?" decision; tells Dylan exactly which file to upload |
| Worker | **Analyst**: build hour, the maths tables for today's variant (hand ranking, ICM, push/fold, the twist's value) and the round-card script; rounds, what the data means (leaks, the defaults check, up to three changes) | **Platform & releases**: the only one editing the main bot code; the rules card at minute 0; v1 by minute 10; every release (v1, v2, ...) |
| Worker | **Tester**: is a candidate correct and stronger (paired tests on Modal), and are the numbers decisions rest on true (re-runs, validates or disputes) | **Styles & fixes**: styles A, B, C, then opponent counters and the live bot's fixes, in its own copy of the repo |
| Worker | **Opponents**: the field trend every round (what the field and the top teams do now; plan assumptions checked), fingerprints, team profiles and counters (`docs/FINGERPRINTING.md`) | **Challenger**: the team's exploration: a design built from scratch from minute 0, then the bigger-swing bot for each window's practice round, in its own copy of the repo |
| Hub services (plain code) | **Clock**, **Portal watcher**, **Deadlines**, **Codex** | **Clock**, **Deadlines**, **Codex** |

- **The Clock** knows the schedule and gives every worker its own task at the right minute, straight from the game
  plan (no relay). It reminds you directly when a step needs your hands ("Dylan: put the live bot back as active
  now"). The **Deadlines** service enforces the cut-offs in `DECISION_RULES.md` (a late step loses its slot; the safe
  default plays; nobody is told to hurry).
- **The Portal watcher** (Samuel's laptop) reads the organizers' website every 30 s (every 6 s near the end of a
  round, every 10 s while an upload is pending). It's read-only. It saves each round's results and our hand
  histories, runs the round card and fingerprinting the moment data lands, and raises an alert if an upload is
  rejected, if there's no active bot, if the active bot isn't the one we decided on, or if the clock is off.
- **Agents talk to each other directly**, on either laptop. Samuel's Analyst hands a fix straight to Dylan's
  Styles & fixes; Dylan's Chat asks Samuel's Chat for the recommendation.
- **Nothing is left hanging.** A message you type that isn't answered is raised again with that agent; a
  contradiction the hub notices (clock vs portal, live vs active bot, two numbers for one thing) is posted to
  your Chat.
- **Parallel work.** Each agent starts its own helpers: Claude subagents, jobs on **Modal** (shared cap of 80
  containers, about $300) and on **Codex** (separate credits, up to 6 at once).

### How you steer

- **Talk to your Chat** for anything about your side; **open an agent** to steer or question that one job.
  Instructions go to the top of the agent's context and are done first.
- **Ask for research** the same way: open the agent whose job it is and say what you want and by when.
- **Decide in words**, in the Chat. Either of you can answer a live-bot decision.
- **Defaults keep things moving.** If nobody answers a live-bot decision by T-5, the pre-registered rule's answer
  plays (the challenger if it cleared the bar, else the live bot). If nobody answers a permission request in 3
  minutes, it's refused and the agent finds another way.
- **Permissions:** ordinary commands are approved automatically. Risky ones always wait for a click (deleting
  outside `/tmp`, force pushes, killing processes, Modal deletes, any write to the organizers' website, writes
  outside the repo).

## 5. Who does what

| | Dylan | Samuel |
|---|---|---|
| Owns | The bot and what plays; **every upload** on the organizers' website; confirming the active bot | Analysis, testing and opponents; the recommendation each window; the portal watcher runs on his laptop |
| Talks to | Dylan's Chat; opens Platform, Styles & fixes, Challenger to check on them | Samuel's Chat; opens Analyst, Tester, Opponents to check on them |
| Decides | Live-bot decisions (in words, in the Chat) | Live-bot decisions too |
| Hands-on moments | Upload at minute 10, before each practice round in the build hour, T-12 (challenger), T-9 (live bot back), T-3 (chosen bot) | Tell the Chat at minute 0; copy the hand-history link after practice round 1 (`SUNDAY.md` step 7) |

You decide together at T-8. If you disagree and there's no time, the rule's answer plays.

## 6. The timeline (the agents follow this too)

**Build hour** (minutes from the variant announcement):

| Minute | What happens | Who |
|---|---|---|
| 0-5 | Kit fetched; Format page read (round weights, payouts, anything unusual); the clock starts Platform on the first prompt with `TWIST_NOTES.md` | Both |
| by 10 | Minimal legal bot uploaded and active | Dylan |
| 15 | Test rig running (paired runs, sparring) | Samuel's side |
| 0 | The Challenger starts design D from scratch (today's rules only) | Dylan's side |
| 17, 27, 37, 47 | Dylan's Chat names the bot for the next practice (the most informative test); the bell reminds Dylan to upload | Dylan uploads |
| 20, 30, 40, 50 | Practice rounds | |
| after 50 | The best real-field scorer (adjusted) is active for scored round 1 | Dylan |

**Every window after that.** A practice round starts 10 minutes before each scored round and plays
whatever bot is active, so each window has two uploads.

| Time to scored round | What happens | Who |
|---|---|---|
| T-20 | Previous scored round starts. The challenger is already packed and tested | |
| T-13 | Previous round's result and hand data land; Samuel's side analyses | Samuel's side |
| T-12 | Challenger uploaded and active (skip if not ready) | Dylan |
| T-10 | Practice round plays the challenger | |
| T-9 | Live bot put back as active straight away | Dylan |
| T-9 | Samuel's Chat sends the recommendation (the threshold, then the final answer once the practice lands) | Samuel's side |
| T-8 | **Decide** by the pre-registered rule (`DECISION_RULES.md` §3): the challenger if it clears the field-adjusted bar for our standing, else the live bot with this window's tested changes. The question pinned in your Chats shows the rule's answer | Both |
| T-6 | Chosen bot tested with no time bank | Dylan's side |
| T-5 | No human answer: the hub applies the rule's answer itself | |
| T-3 | Chosen bot uploaded; active bot confirmed | Dylan |

Once the live bot is back at T-9, a missed deadline means the previous live bot plays: that is a failure to
fix, not a safe outcome (bots that stood still lost as much as bots that changed). Only tested zips are ever
uploaded.

## 7. How we decide

The full rules are in `docs/DECISION_RULES.md`; every agent has them in its instructions on every turn.

- **Goal:** a top-3 finish (only 1st-3rd pay). Standing still is not safe.
- **Live bot:** every independent tested change that clears the bar, each in a different situation and behind
  its own setting (usually one to three).
- **Challenger:** the team's exploration: the clean-room design, a new style, the best response to the field's
  measured mix, what a plan challenge points to, or a fresh rewrite. A rewrite is normal at any standing.
- **Which bot plays:** compared against yardstick teams (those that didn't change), so the challenger's
  practice and the live bot's scored round are on one scale. The challenger plays at z ≥ 0.5 outside the top 3
  (≥ 0 in the last two rounds), z ≥ 1.0 in the top 3 (1.5 with a big lead). If nobody answers in time, the
  hub applies the rule's answer.
- **Exploration:** until 30% of the weight is played, at least every other practice round plays a different
  design, at any standing unless our lead is big.
- **Plan challenges:** any agent may say the plan is wrong for today, with evidence; both of you see it, and
  by default the Challenger builds the alternative for the next practice.
- **Folding to re-raises:** near break-even (usually 65-75%) is the default, not a cap (the regional winner
  folded 81-87%); it doesn't apply to folding to 4-bets after our own light 3-bets.
- **Bolder:** behind 3rd, or outside the top 3 after 15% of the weight: the challenger slot carries a divergent
  design and the bar drops; plan the last round (often 25-40% of all points) from the round before.
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
- **The hand-history download address** isn't in the organizers' code. If the watcher can't download, Samuel
  pastes it once into his Chat as "hands link: …" after the first practice round (`SUNDAY.md` step 7).
- **The upload cooldown:** 30 s at the regionals' portal, 5 minutes in a public summary. Check the Format page.
- **The agents are good but not careful.** In simulations they:
  - used last rehearsal's data until caught;
  - asked for things nobody can see;
  - reported a "+36 points" test result that turned out to be a broken test.

  Read their findings with suspicion and ask "why?".
