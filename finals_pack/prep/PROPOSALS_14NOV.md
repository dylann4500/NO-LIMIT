# Decisions for Dylan and Samuel (Saturday night, 14 November)

**Status: approved and applied.** Dylan approved every recommendation as written on 14 November at about 17:10
("go ahead and just implement as written the proposals"). Items 2 to 17, 19 to 24 and 30 are in the bundle (commits
`cec5c95..e31d4de`, one per item, merged as `8f56d9a`; full tests pass), and items 25 and 27 are in `START.md`.
Still open: 18 (undecided, nothing written), 22 (Samuel confirms the figure), 26 and 28 (yours to do), and the
permission mode for Sunday's sessions (`START.md` states what was tested and leaves the choice to you). Samuel has
not yet said he agrees with sections A to C: tell the lead session if anything should change.
Evidence is in `notes/pre/` and in `prep/TABLETOP_14NOV.md` (the exact replacement wording for every item marked P).

Words used below. **Live bot**: the bot currently chosen for scored rounds. **Challenger**: the new bot tried in the
practice round before a scored round. **z**: the challenger's measured edge over the live bot divided by that edge's
standard error (SE). **T-4**: four minutes before a scored round starts. **Yardsticks**: teams that did not change
bot between the two rounds being compared. **Case F / case R**: the six-seat Finals table / the regional's
eight-seat table (`CLAUDE.md` section 8).

## What changed today (for information)

- **The Finals competition is on the portal:** 21 teams by name, weights linear 1 to 6 when read at 15:44 (Boston and
  Pittsburgh used 1, 2, 3, 5, 8, 13, and it can still change), a 30-second upload cooldown, and an upload that passes
  its test becomes the active bot by itself. No variant and no round yet.
- **Main case: six seats, 6,000 chips, antes** (Dylan, 15:55), from the Finals defaults in the portal's own code. The
  regional table is the fallback. The earlier fair-play question is closed: Dylan says the organizers treat what is
  on their site as fair to read. `notes/pre/format_finals.md` is the plan for it.
- **All 20 opponents have a card from raw hand files** (`notes/pre/finalists.md`). Team 72 is the Bay Area's (Dylan).
- **Usage and compute:** Sunday runs on a fresh Claude account (Dylan). AWS is dropped; Modal is the only compute.
- **The bundle:** about 110 instruction fixes from three timed runs, two consistency reads and a tabletop test are
  merged; the full test suite passes (228).

## A. Which bot plays (both of you)

| # | Decide | Recommended | Why |
|---|---|---|---|
| 1 | The bar for playing a challenger | **No change** | Rebuilt and tested on the regional's results: of 23 strong teams that showed a new bot in practice, the rule would have played 17 (mean gain +1.21, one loser) and refused 6 (mean -0.57). `challenger_bar.md` |
| 2 | How the edge's SE is computed | **Take it from the yardsticks' own practice-to-scored spread** (0.8 with fewer than 6 yardsticks, never below 0.7) | One practice predicts the scored round with an error of about 0.8 points; this rescales itself when the table or the payouts differ |
| 3 | A scored round's data lands late (P1) | **The challenger is still judged** if that round's result and the practice result are both in by T-6; if either is missing at T-6, the live bot plays | In the tabletop test both agents did this; the cut-off table read literally says the opposite |
| 4 | One switch deadline (P2) | **T-4.** A bot can be chosen only if at T-4 it is released, upload-tested and has a tester verdict with a heads-up run. "Fit for a scored round" means correct, fast, and heads-up no worse than the live bot by more than 2 SE | The two sessions told their humans different things four minutes before a round |
| 5 | The practice has not started when the clock says "put the live bot back" (P3) | **The challenger stays active until the practice is shown as started;** the live bot goes back then, and at T-5 at the latest | The two sessions gave Dylan opposite advice |
| 6 | "A big lead" (P4) | **z of 1.5 is needed only when our lead over 4th is more than 3 times the coming round's weight, in standings points** (before a round of weight 4: more than 12) | The words as printed gave the opposite bot from the one both agents chose |
| 7 | Standings held (P5) | **Work the standings out from each round's results and weights;** only if that is impossible, treat us as outside the top 3 | Each round's results list every team, so it can always be done |
| 8 | You two disagree, or nobody is there to click (P6, P7) | **The rule's answer stands until you agree, and Dylan makes that click even if he argued against it.** If the portal still shows the old bot at T-3, BUILDER says so once and RESEARCH asks Samuel to fetch Dylan; whatever actually played is declared afterwards | Found only after a search in the test |
| 9 | Round 1's bot (P10) | **The best scorer of practices 1 to 3 among bots that have a heads-up verdict at minute 50** | Otherwise the declared bot may not be allowed to play |
| 10 | The portal marks us out of contention (P9) | **Ask an organizer whether such teams still play and can be paid; nothing changes until the answer.** If it is final, the last-rounds bar (z of 0 or more) applies | The watcher's own message states a rule no page has |
| 11 | A table that is not 8 seats at 50/30/20 (P8) | **By minute 5 the tester writes the day's per-table spread and its ratio to 17.9; every figure given in points per table is multiplied by it.** Bars in z do not move | At six seats the ratio is 1.06; at 70/20/10 it would be 1.27 |
| 12 | Where scores come from (was 19) | **From the round's results file, never from a hand file** | The first-1,000 file's score for us missed the full round by 0.4 on average and by 2.0 once |

## B. Reading the field (both of you)

| # | Decide | Recommended | Why |
|---|---|---|---|
| 13 | When a field rate triggers a plan challenge (was 3) | **"2 points or more outside the band, in two downloads running."** Keep 2 SE for scores | A pooled field rate's SE is 0.1 to 0.5 points, while the regional field itself moved 0.5 to 2.7 between rounds: "2 SE" fires on ordinary drift |
| 14 | "Over a third of teams differ between a practice and the next scored round" (was 21) | **Reword as normal, not a warning** | It was 46% at the regional |
| 15 | Which practice judges a plan challenge (P11) | **The next practice the alternative can be released for** (released by T-15) | Otherwise a rushed build is aimed at a practice one minute away |
| 16 | The kit's do-nothing bot (P12) | **Add as a plan assumption:** our base style beats it on the real field by 1 point or more; two downloads in which it does not is a plan challenge | At six seats a folder cashes 53% of the time in simulation (11.1 of an average 16.7) |
| 17 | Tables with counters switched off, for comparison (was 22) | **In practice rounds only.** In a scored round only for a new counter nobody has validated, with the reason written down | `FINGERPRINTING.md` asks for 15% of scored-round tables; `EVIDENCE_TABLE.md` says none without a reason |
| 18 | May we upload the kit's own example bot for a practice? | **Your call:** no rule of ours or the organizers' says | It would measure the floor on the real field in one practice |

## C. Strategy defaults (both of you; stronger now that the main case is 300 big blinds deep)

| # | Decide | Recommended | Why |
|---|---|---|---|
| 19 | "No flat calls" (was 5) | **Allow flat calls where the style states the postflop plan behind them;** the check run still counts them | On the regional's real data our flats made +5.9 big blinds a table once the postflop leak was fixed, and at 100 big blinds or more in position the default is probably wrong (`format_finals.md` section 1) |
| 20 | "Call shoves wider than a chart" (was 6) | **Reword:** call at the tournament-equity threshold against that seat's measured shoving width | The evidence for "wider" is mixed |
| 21 | Round 1 between two close candidates (was 4) | **One sentence, not a rule:** prefer the more aggressive; worth at most 1 point | Early practices over-reward tight play (score against 3-bet rate: r -0.54 in practice 1, +0.25 by round 6) |
| 22 | "Our own mistakes cost about 22-25 points" in `PLAN.md` (was 7) | **Samuel:** confirm the source or correct it | The research could rebuild only 5 to 9 points for two of the mistakes |
| 23 | The smaller wordings (P13, P14, and the two script messages in P1 and P9) | **Apply as written in the tabletop report** | One-line clarifications; none changes a bar |
| 30 | The speed bar for the twist decision (was 23) | **99th percentile under 0.5 ms everywhere** | `TWIST_NOTES.md` says 0.8 ms; the tester's and the challenger's role files say 0.5. The limit is 1 ms a decision |

## D. Set-up for Sunday (Dylan)

| # | Decide | Recommended | Why |
|---|---|---|---|
| 24 | The model for the two sessions | **Fable 5.2 for both, effort high** | Two timed runs compared (`prep/SPEEDRUN_AB_14NOV.md`): no clear winner, a lean to Fable of about 60/40 with low confidence. Opus had a first bot sooner; its rig ran the wrong bot's code for 24 minutes and its bots were slower per decision |
| 25 | Desktop app or terminal tabs (was 10) | **Desktop app for the two sessions, terminal tabs only for the clock and the portal watcher** | Every mechanics check and every timed run was a desktop-app session; nothing was tested in terminal tabs. `START.md` is written for tabs and needs its steps 3 and 4 rewritten if you agree |
| 26 | The fresh account | Before Sunday: sign the desktop app in to it, confirm it offers Fable 5.2 in the Code tab, open `~/avalon-finals` once to trust it, and sign Samuel's computer in to the same account | Remote Control only shows sessions of the account the other computer is signed in to. The portal key and Modal are on the laptop, not the account |
| 27 | The Sunday repo | **Local only at `~/avalon-finals`**, built tonight from the bundle minus `prep/` | Everything runs on this laptop. Say so if you want a private GitHub copy as a backup |
| 28 | A dry run with Samuel | **Ten minutes tonight:** Samuel opens any session of this laptop from his computer and types into it while Dylan types into another | The one mechanic never tried with two people |
| 29 | First download size (was 20) | **Leave at 1,000 tables** | The practice rounds that decide the bot have about 1,000 tables anyway; the analyst can re-run on the full file's first 5,000 |

## E. Left as they are unless you say otherwise

Process choices the timed runs raised that I did not turn into rules, because each needs a script change or a
judgement that is yours:

- A second `platform` run at minute 0, and a second, narrow bug hunter for every release.
- A queue or cap for Modal jobs running at once; one shared upload-test runner; a queue in `live.py`.
- A file-watcher that wakes RESEARCH when a release lands (today it looks on every wake-up).
- A rehearsal in the build hour of the edge calculation and the round-1 recommendation.
- How withdrawn releases are named; the 300-word limit on subagent reports.
- Plan assumptions 2 and 4 to 7 have no measurable test; the fingerprinting thresholds are untested.
- Hold'em shove and call priors, push/fold keyed by players behind, the leaks lens ranking on outcomes.

Added from timed run C (six seats), also left as they are:

- Three `platform` runs at minute 0, with a clock step at minute 8 for an importable skeleton.
- A bug hunter and a tester only for releases declared to play (the bundle keeps "every release").
- A release cadence: ten releases in 20 minutes outran verdicts that take 4 to 8 minutes; nobody proposed a rule.
- A job-size limit on the shared test rig (RESEARCH proposed at most 1,000 tables a job while another tester runs).
- Script changes: a narrower loop pattern in the safety hook (it also matches prose), shorter clock lines, a file
  watcher script.
- Three open definitions in `stat_definitions.md`: which big blind sets the depth, whether a small-blind complete is
  a limp, whether a raise over limpers is an open.

Modal: the workspace is on the Starter plan with a cap of 100 containers (read in the dashboard on 14 November); the
bundle uses 80. Dylan asked Modal for 400 that evening. Unless it is granted and measured, nothing changes.

Three numbers a session chose while fixing instructions, for you to overrule: about 6 local worker processes per
session and 2 per subagent; 200 hands for the check that a candidate is alive; 30 big blinds for the scripted spot
in which AA must never fold to an all-in.

## Closed today

| Was | Outcome |
|---|---|
| 0, usage | Reset by Dylan at about 15:00; Sunday runs on a fresh account |
| 8, 9, fair play | Closed by Dylan: reading the organizers' public pages is fine. No Pittsburgh kit was sought |
| 12, connectors | A fresh account has none. Switching plugins and connectors off in the repo was measured: 12% less start-up context, not worth a settings change the night before |
| 13, AWS | Not used |
| 24, challenger release time | Not a conflict: released by T-15 (T-13 at the latest), uploaded at T-12 |
