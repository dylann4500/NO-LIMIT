# Tabletop test of Sunday's decision windows (Saturday 14 November)

For Dylan and Samuel, and the lead session. Eighteen concrete moments from Sunday were written out as the files
an agent would see, and each was handed to two fresh agents, one told it is BUILDER and one told it is RESEARCH,
with nothing but the bundle. Nothing in `finals_pack/` was changed: every rule change below is a proposal for
you to accept, reword or refuse.

**Result: 5 clear, 10 slow, 3 split, 0 wrong.** No agent broke a hard rule: none played a bot without a tester
verdict, none uploaded an untested zip, none touched the portal. In all 15 scenarios that were not split the two
agents reached the same outcome. The weakness is the time it took and what they had to guess. In 10 scenarios
both agents wrote that the deciding passage was a guess, was outside `DECISION_RULES.md`, or had another
passage pointing the other way. In 3 they told their humans different things.

What the verdicts mean:
- **clear**: both right, both agree, the deciding passage is stated in `DECISION_RULES.md` or the agent's prompt.
- **slow**: both right and agreeing, but each needed a guess, a search outside the files it reads at start-up,
  or a choice between two passages that disagree. Where the passage they chose against would give a different
  bot when read alone, the table says "reads the other way".
- **split**: the two agents would have said different things to Dylan and Samuel.
- **wrong**: both miss what the rule says. None.

## 1. Results

| # | Scenario | Verdict | The rule that should decide | What went wrong |
|---|---|---|---|---|
| S01 | A clear challenger win (6th, z 2.1) | clear | `DECISION_RULES` §3 "Which bot plays": outside the top 3, z ≥ 0.5 | Nothing. Both: the challenger, labelled unverified |
| S02 | An edge inside the noise (5th, z 0.38; two validated fixes) | clear | §3: "Otherwise the live bot plays, with this window's changes" | Nothing. Both: the live bot plus the two fixes (v14). Both guessed that an upload does not activate itself |
| S03 | The challenger looks better (z 2.8) but has no tester verdict | **split** | §2 rule 1 (no verdict with a heads-up run, no scored round) | Both refuse to play it without the verdict. BUILDER waits for the verdict until T-3, RESEARCH until T-4; the tester's estimate was T-3. Neither found a pass mark for a heads-up run |
| S04 | The scored round's data lands at T-6 instead of T-10 | slow, reads the other way | §3 cut-off row T-10 against §3 "Which bot plays" | Both played the challenger (z about 3 by field medians). The T-10 row says "No change from new data; live bot plus already-validated changes". Both decided the row covers fixes only |
| S05 | Hand data that will not download | **split** | `prompts/RESEARCH.md` "The clock" (RESEARCH asks Samuel for the link) | The watcher's URGENT line goes to both inboxes. BUILDER asked Dylan for the link and told RESEARCH "Samuel needn't"; RESEARCH asked Samuel and told BUILDER "nothing for Dylan". Both chose the same bot rule (field medians, no yardsticks) |
| S06 | An upload rejected at T-4 | clear | §3 cut-off row T-4; `LESSONS.md` "After a rejection the previous bot stays active" | Nothing. Both: the previous live bot plays, re-declared, nothing uploaded. Both guessed that a rejected upload starts the cooldown |
| S07 | The leaderboard is held (computed: 3rd by 0.3) | slow, reads the other way | §3: "the standings are hidden and we weren't clearly in it" | Both read 3rd by 0.3 as "not clearly", bar 0.5, challenger. `LESSONS.md` says to compute our total and use the outside-top-3 bar only "if that's impossible": that gives bar 1.0 and the live bot. "Clearly" has no number |
| S08 | 2nd with a 4.7 lead, challenger at z 1.2 | slow, reads the other way | §3: z ≥ 1.5 "if our lead over 4th is more than one round's typical swing" | Both guessed the swing is 3 x the round's weight = 12 total points, so bar 1.0, challenger. Both wrote that the words as printed ("3 points per table times the round's weight share" = 0.57) give bar 1.5 and the live bot |
| S09 | 9th before round 5 (z 0.22) | clear | §3: the last-rounds bar, z ≥ 0 | Nothing. Both: the challenger. BUILDER noted the bar is one parenthesis that the T-8 clock line never mentions; RESEARCH that `state/clock.md` has no "last two rounds" flag |
| S10 | Dylan and Samuel give different answers | slow | `prompts/BUILDER.md` "If they disagree, the rule's answer stands until they agree" | Both right. The sentence is not in `DECISION_RULES.md` or `prompts/RESEARCH.md`; §3 says "a human can always overrule it". No rule for when the human who disagrees is the one who must click |
| S11 | Nobody answers (Dylan away, Samuel on a call) | slow | §3: "The rule's answer plays at T-5 if no human has answered" | Both right. Nothing says what happens when nobody is there to click, or whether a click after T-3 ("after this nothing changes") is allowed |
| S12 | The scout raises a plan challenge at T-11 | slow | §3 "Plan challenges" | Both right. Both had to guess that "the next practice round" means the one 20 minutes away, not the one starting in 55 seconds. BUILDER redirected the running challenger; no passage says whether to |
| S13 | A 5-minute cooldown and two uploads wanted | clear | §3 "Uploads": "Never let a cooldown leave the chosen bot unuploaded at T-3" | Nothing. Both: the chosen bot only; the other zip after the round starts |
| S14 | The kit's do-nothing bot scores as well as ours | slow | `LESSONS.md` and `prompts/RESEARCH.md` ("a PLAN CHALLENGE-sized fact") | Both raised a plan challenge and gave practice 4 to a fold-first design. The trigger is not among §5's seven assumptions, and `PLAN.md` gives practice 4 to "the leader, or its closest unmeasured rival" |
| S15 | Points per place 70/20/10 | slow | `CLAUDE.md` §4 rule 3 (the rules card is right) | Both told everyone at once and recomputed the call thresholds by hand to the same figures. No passage says which of the page's point figures (0.7, 1.4, 2.0, 3) change with the payouts |
| S16 | Choosing round 1's bot from practices 1-3 | slow, reads the other way | §3 "Round 1" against §2 rule 1 | "Round 1" says declare the adjusted best scorer; it had no heads-up run. Both declared the best fully tested bot instead and would switch on a late verdict. No pass mark for a heads-up run |
| S17 | The portal marks us out of contention | slow | None in the bundle | Both: ask an organizer what it means, play on with the last-rounds bar, no verdict no scored round. The watcher's own inbox line says "the challenger plays from now on", which no rule says. Each asked its own human to find an organizer |
| S18 | The practice round has not started at T-9 | **split** | None in the bundle | BUILDER told Dylan not to put the live bot back, with its own limit of T-5. RESEARCH reported the fact, left the call to BUILDER and quoted "When in doubt, the live bot stays active" |

## 2. What every agent had to guess

These came up in many scenarios, whatever the topic. Each costs seconds of doubt at T-8.

1. **Is the T-6 no-time-bank test repeated for a zip that already passed it?** Ten of the 18 BUILDER agents
   wrote this as a guess (S01-S05, S07-S10, S18). Eight had `platform` run it again on an unchanged zip; two did not.
2. **Does an upload become the active bot by itself? Does a rejected upload start the cooldown?** Guessed in S02,
   S06 and S13 by both roles. The bundle cannot know; nobody is told to find out.
3. **Does the best-of-k discount (§4) apply to the challenger-against-live edge?** Raised in S01, S04, S07, S08
   and S10. All decided it does not. If it did, z would drop by about 0.6 and S07, S08, S10 and S11 would flip to
   the live bot.
4. **Which deadline binds: T-5, T-4 or T-3?** S03, S11 and S16.
5. **What is a passing heads-up run?** S03 and S16: each agent invented its own mark.
6. **How wide is "When in doubt, the live bot stays active"?** It sits in the Uploads paragraph. Agents quoted it
   as a general tie-break against the rule's answer in S04, S09, S10, S11 and S18; all but one argued past it.
7. **Is §5 assumption 7 a bar?** ("differences under ... 1.4 between a practice round and a scored round are
   noise"). Quoted against the z bars in S08, S09 and S11.
8. **The SE of the edge.** Agents built it by hand as √(0.7² + 0.28²) = 0.75; "more with 20 teams" has no figure.
   Item 2 of `PROPOSALS_14NOV.md` already covers this.

A pattern in the slow cases: the deciding sentence was in `strategy/LESSONS.md` and was found by search (the
rejected upload, the hidden leaderboard, opposite answers, the do-nothing bot). `DECISION_RULES.md` says it
"overrides anything older or vaguer", so agents then had to argue whether the `LESSONS.md` sentence still counts.

## 3. Proposals, most costly mistake first

Each gives the passages that caused the trouble and exact replacement wording. None repeats the seven items in
`PROPOSALS_14NOV.md`; where one touches them it says so. "Cost" is what a wrong reading loses on the day.

### P1. Late scored-round data: does the challenger still get judged? (S04)

**Cost:** which bot plays a whole scored round. In S04 the challenger was +2.3 points a table ahead and both
agents played it; an agent that follows the cut-off row plays the live bot.

**The passages.** `DECISION_RULES.md` §3, cut-off table:
> | T-10: last round's data landed | No change from new data; live bot plus already-validated changes | both sessions, both humans |

The clock's cut-off message (`scripts/clock.py`, the `data` guard) goes further: "no new data this window. The
live bot plays with only changes already supported by earlier rounds ... When it lands it feeds the next window".
Against them, §3: "The rule's answer **is** the default. If nobody answers in time, the rule's answer plays, not
'no change'", and `prompts/RESEARCH.md`: "With no practice result by T-6, the rule's answer is the live bot"
(which speaks only of the practice result).

**Proposed wording** for the T-10 row (this is the reading both agents took):
> | T-10: last round's data landed | No new **changes to the live bot** from that round: live bot plus already-validated changes. The which-bot decision still runs: if that round's result and the practice result are both in by T-6, `tester` gives the edge (yardsticks if the file exists, else scores minus the field median, said so) and the rule's answer follows it. If either is missing at T-6, the rule's answer is the live bot | both sessions, both humans |

If you want the opposite, write: "... and the challenger does not play this round, whatever lands later." Either
way the clock's message should say the same; it is one string in `scripts/clock.py`.

### P2. One switch deadline, and a pass mark for the heads-up run (S03, S16, S11)

**Cost:** in S03 the tester's estimate for the verdict was 14:37 (T-3). BUILDER would have waited for it and
played the challenger; RESEARCH would have told Samuel at 14:36 that the live bot plays. Two sessions, two
answers, four minutes before a round, with a +2.5 challenger at stake.

**The passages.** `DECISION_RULES.md` §3:
> The rule's answer plays at T-5 if no human has answered

> **Deadlines:** if the chosen bot can't be tested and uploaded by T-3, the live bot (active again after the practice round) plays ... Don't wait past T-3 for a release.

> | T-4: the chosen bot released and tested | The live bot (active since the practice round) plays; nothing is uploaded |

`prompts/BUILDER.md`, T-4 row: "if the chosen bot isn't released and tested with a tester verdict, the live bot
plays". T-3 row: "After this nothing changes." Nowhere: what result makes a heads-up run a pass.

**Proposed wording**, replacing the "Deadlines" paragraph:
> **Deadlines: one switch deadline, T-4.** A bot can be the chosen bot only if at T-4:00 its zip is released, its `VERSIONS.md` line has the upload test, and a `tester` verdict with a heads-up run is in `notes/LEDGER.md`. A verdict, an answer or a number that arrives after T-4:00 feeds the next window. T-5 is when BUILDER applies the rule's answer if no human has answered; a rule's answer that waits on a verdict ("v11 if its verdict lands, else v9") is settled at T-4:00. From T-4 to T-3 there is only Dylan's click or upload. After T-3 nothing is decided or uploaded; the one thing still allowed is the click that makes the declared bot active. If the chosen bot isn't active at the start, the live bot plays: report the miss and its cause, and fix the cause for the next window.

And one sentence at the end of §2 rule 1:
> A verdict's first words are "fit for a scored round" or "not fit": fit means correct, fast, and a heads-up run no worse than the live bot's by more than 2 SE.

### P3. The practice round has not started when the clock says "put the live bot back" (S18)

**Cost:** if Dylan puts the live bot back on the clock's beep and the practice starts late, the practice
measures the live bot, the challenger has no number, and the rule's answer is the live bot by default: the
window's exploration is lost. The other way, a challenger left active too long plays a scored round.

**The passages.** `DECISION_RULES.md` §3 "Uploads": "it plays the practice round at T-10, and at T-9 Dylan puts
the `state/live.json` bot back (a click) ... When in doubt, the live bot stays active." `prompts/BUILDER.md` T-9:
"Tell Dylan: 'put vL back now'". The clock holds a window only for a late scored round. The watcher's alarm for
a round that has not started fires 8 minutes after its time, and never for a practice between scored rounds.

**Proposed wording**, added to "Uploads":
> The T-9 put-back assumes the practice started at T-10. Before saying "put vL back", BUILDER reads `state/status.md`: if the practice round is not shown as started, the challenger stays active, BUILDER tells Dylan to wait (the clock's beep is early) and tells RESEARCH. The live bot goes back the moment the watcher posts the practice's start, and at T-5 at the latest whether or not it has started. A practice that starts after T-8 cannot give a result by T-6: the rule's answer is the live bot and that practice feeds the next window. Only a challenger with a `tester` verdict may stay active past T-9.

### P4. The big-lead test has no units (S08)

**Cost:** this is the bar for the best situation we can be in. Both agents wrote that the words as printed give
the opposite bot from the one they chose.

**The passage.** §3:
> **we are in the top 3**: z ≥ **1.0**, or z ≥ 1.5 if our lead over 4th is more than one round's typical swing (about 3 points per table times the round's weight share).

Standings totals are sums of weight x points per table. "Weight share" reads as 4/21, giving 0.57; the lead on
the board was 4.71. Both agents instead compared 4.71 with 3 x 4 = 12.

**Proposed wording:**
> **we are in the top 3**: z ≥ **1.0**, or z ≥ 1.5 if our lead over 4th on the standings is more than 3 x the coming round's weight, in the standings' own points (before a round of weight 4: more than 12).

The same phrase in "Exploration" ("unless our lead over 4th is more than one round's typical swing") then points
to this one definition.

### P5. Standings held: what "clearly" means (S07)

**Cost:** which bot plays when we are on the edge of the money. Both agents chose bar 0.5; `LESSONS.md` read
alone gives bar 1.0.

**The passages.** §3: "we are outside the top 3, or the standings are hidden and we weren't clearly in it".
`prompts/RESEARCH.md`: "treat us as outside the top 3 unless we clearly weren't". `LESSONS.md`: "Standings
hidden: work out our total from each round's results and weights; if that's impossible, treat us as outside the
top 3". Each round's `results.json` has all 20 teams, so the whole table can be computed.

**Proposed wording** for the first bar's condition (mechanical, and the same as `LESSONS.md`):
> **we are outside the top 3** (if the portal's standings are held, the standings are `tester`'s totals for all 20 teams from each round's results x weights; only if those can't be computed either are we treated as outside the top 3)

If you prefer what the agents did, write instead: "we count as in the top 3 only when we are 3rd or better by more
than 1.0 on the standings; a smaller lead uses the outside-the-top-3 bar, held or not."

### P6. Opposite answers, and the human who disagrees is the one who clicks (S10)

**Cost:** a round played on whichever bot Dylan last clicked, with the sessions arguing. Both agents got it
right, but only after a search; RESEARCH's prompt and `DECISION_RULES.md` do not have the sentence.

**The passages.** §3: "a human can always overrule it." `prompts/BUILDER.md`: "If they disagree, the rule's
answer stands until they agree; say so to both."

**Proposed wording**, replacing "a human can always overrule it" in §3:
> either human can overrule it, unless the other has given the opposite answer: then the rule's answer stands until they agree, and both sessions say so to both humans at once. Dylan makes the click the rule's answer needs even if he argued against it. If he won't, the live bot stays active: BUILDER re-declares it and records why.

And one line in `prompts/RESEARCH.md` under the T-9 recommendation: "If BUILDER reports that Dylan's answer is
the opposite of Samuel's, tell Samuel at once: the rule's answer stands until they agree."

### P7. Nobody answers and nobody is there to click (S11)

**Cost:** `state/live.json` says the challenger, the portal runs the live bot, and the next window starts from
the wrong bot's numbers.

**The passages.** §3: "The rule's answer plays at T-5 if no human has answered (BUILDER applies it with
`scripts/live.py`)". T-3 in `prompts/BUILDER.md`: "After this nothing changes." The watcher still asks for the
click at T-2.

**Proposed wording**, after the T-5 sentence in §3 (P2's last sentences cover the T-3 part):
> If the portal still shows the old bot at T-3, BUILDER says so once to Dylan and has RESEARCH ask Samuel to fetch him; the click stays valid until the round starts. If the round starts on the old bot, BUILDER re-declares the bot that played (`live.py`), and the next window compares against it.

### P8. Payouts that are not 50/30/20: which numbers on the page change (S15)

**Cost:** every points-per-table threshold is about 27% too small all day at 70/20/10 (both agents worked this
out by hand: per-table spread 22.8 against 17.9). Bars in z do not move.

**The passages.** §3: "Practice SE is **at least 0.7**"; "about 1.4 points apart"; "a loss of 2 points or more";
"about 3 points per table". §5 assumption 7: "differences under 2.0 ... (1.4 ...)". The role files' ICM check
values (`.claude/agents/platform.md`: "8 equal ≈ 56%, 3 equal ≈ 57%, 4 equal ≈ 62-65% (50/30/20)") are for
50/30/20 only.

**Proposed wording**, one sentence at the end of §2 rule 3:
> Every figure on this page given in points per table (0.7, 1.4, 2.0, 2 and 3) assumes 8 players and 50/30/20. By minute 5 `tester` writes today's per-table spread and the multiplier (spread / 17.9) in `bot/rules.json`; both sessions multiply those figures by it. Bars given in z do not change. Role-file check values marked 50/30/20 are not used on another payout.

Item 2 of `PROPOSALS_14NOV.md` (the SE from the yardsticks' own spread) rescales the SE by itself; this covers
the other four figures.

### P9. Out of contention (S17)

**Cost:** two rounds played on a rule that is only in a watcher message. Both agents refused the message and
asked an organizer, which is right, but each asked its own human.

**The passage.** The watcher's inbox line (`scripts/portal_watch.py`): "URGENT: after {stage} the portal marks
us out of contention ... If that's final, nothing is lost by bold play: the challenger plays from now on."
`DECISION_RULES.md` has nothing on a cut.

**Proposed wording**, a bullet under "When to be bolder":
> - The portal marks us out of contention: RESEARCH asks Samuel to ask an organizer at once whether such teams still play and can still be paid (BUILDER tells Dylan what it means and asks him for nothing else). Until the answer, nothing changes. If it is final, the last-rounds bar (z ≥ 0) applies from then on. Hard rule 1 still holds: no verdict, no scored round.

RESEARCH also proposed going back to the earlier live bot after a bad round. Nothing covers that. One sentence
for §3 "Which bot plays": "An earlier released bot with a verdict is a candidate like any other: compare its
last scored round with the live bot's against yardstick teams, same bars."

### P10. Round 1 when the best scorer has no heads-up run (S16)

**Cost:** round 1 (the lowest weight) on the second-best bot, or a declared bot that cannot play.

**The passages.** §3 "Round 1": "the live bot is `tester`'s adjusted best scorer of practices 1-3 (declared at
b50 ...)". §2 rule 1 forbids it without a heads-up run. `PLAN.md` §5 b40 already says "the adjusted best scorer
... with a verdict that includes a heads-up run".

**Proposed wording** for §3 "Round 1":
> the live bot is `tester`'s adjusted best scorer of practices 1-3 **among bots whose verdict has a heads-up run at b50**; a higher-ranked bot whose verdict lands by T-4 replaces it by a click, with no question asked.

Item 4 of `PROPOSALS_14NOV.md` (prefer the more aggressive of two close candidates) is separate and still stands.

### P11. "The next practice round" for a plan challenge (S12)

**Cost:** a rushed, untested build aimed at a practice one minute away, or five minutes of doubt.

**The passages.** §3: "By default BUILDER has `challenger` build the alternative and the next practice round
judges it." `prompts/RESEARCH.md`: "deadline: the next practice".

**Proposed wording:**
> By default BUILDER has `challenger` build the alternative for the next practice round it can be released for (released by T-15 of that window; a challenge raised later targets the practice after). BUILDER redirects the running `challenger` to it unless a human says to keep both lines. Nothing from a challenge enters this window's live bot unless it is already a validated `one-change` line with a tested build by T-8.

This is separate from item 3 of `PROPOSALS_14NOV.md`, which is about when a field rate triggers a challenge.

### P12. The do-nothing bot as a plan assumption (S14)

**Cost:** a practice slot, and round 1's pick. Both agents acted, but the trigger was found in `LESSONS.md`.

**The passages.** `prompts/RESEARCH.md`: "a PLAN CHALLENGE-sized fact if it holds on the real field".
`PLAN.md` §5 b40: practice 4 is "the leader, or its closest unmeasured rival if the leader is already clear".

**Proposed wording**, an eighth plan assumption in §5:
> 8. Our base style beats the kit's do-nothing example (`check_or_fold`) on the real field by 1 point or more. (`analyst`'s defaults check gives the kit-example teams' scores on every card. Two downloads in which they match or beat the bot we played is a PLAN CHALLENGE; its alternative takes the next practice it can be released for, ahead of the b40 "leader or closest rival" pick.)

Open question for you: may we upload the kit's own example for a practice? No rule says.

### P13. Who gets the hand download link (S05)

**Cost:** both humans leave their screens at T-8 for the same job.

**The passages.** `prompts/RESEARCH.md`: "ask Samuel for the hand download link ... then run ... yourself". The
watcher posts its URGENT line ("Copy the hand download link ... and paste the link") to both inboxes.

**Proposed wording**, one line in `prompts/BUILDER.md` under "Talking to Dylan":
> Hand data not downloading (an URGENT line in both inboxes) is RESEARCH's job with Samuel: don't ask Dylan for the link unless RESEARCH asks you to.

And in `prompts/RESEARCH.md`: "Ask at the first 'hand data not downloadable yet' line that is 2 minutes old, and
tell BUILDER in one line that you have it." And in §3 "Which bot plays", after the yardstick sentence: "No hand
file for the scored round means no yardsticks: use scores minus the field median (`results.json` is enough)."

### P14. Six one-line clarifications (from section 2)

| Where | Now | Proposed |
|---|---|---|
| `prompts/BUILDER.md` T-6 row | "`platform`: the chosen bot through the upload test with no time bank; released if it's a new zip." | add: "A zip whose `VERSIONS.md` line already has the upload test on the same sha256 is not tested again, unless that test ran on a loaded machine." |
| `prompts/BUILDER.md` Minute 0, step 4 | (nothing) | add: "When v1 goes up, ask Dylan two facts and write them in `notes/format.md`: does a new upload become active by itself, and does a rejected upload start the cooldown?" |
| `DECISION_RULES.md` §4, best of k | "When you pick the best of k candidates, discount its edge by ..." | add: "This is for picking one of k measured the same way (round 1's pick, k fixes from one lens). It does not apply to the challenger-against-live edge: the bars already allow for it." |
| `DECISION_RULES.md` §3 Uploads | "When in doubt, the live bot stays active." | "When in doubt about what is on the portal or which file is which, the live bot stays active. (This is not a tie-break for the which-bot rule.)" |
| `DECISION_RULES.md` §5 assumption 7 | "differences under 2.0 between two practice rounds (1.4 between a practice round and a scored round) are noise." | add: "(A check on the field, not a bar: the bars in §3 are in z.)" |
| `DECISION_RULES.md` §5 assumption 1 | "The field folds to 3-bets of our opens at about 60-70%." | "When we 3-bet an open, the opener folds about 60-70% of the time." (If you meant our opens being 3-bet, say that. Both S12 agents read it as above.) |

Two things in the scripts' own wording (not rules, so listed for the lead): the clock's T-10 cut-off message
(P1) and the watcher's out-of-contention line (P9) each state a rule the page does not. The T-8 clock line could
name the last-rounds bar when the round is one of the last two (S09).

## 4. How the test was run, and its limits

- 18 scenarios, 36 agents, each a fresh general-purpose subagent at high effort with no context from this
  session. Each was told its role, the bundle's path and one scenario folder, and asked four questions: the next
  ten minutes minute by minute, the exact words to its human and the other session, the deciding rule by file
  and section (marked stated or inferred), and what it lacked. No expected answer was hinted.
- Each agent could read its own terminal file and inbox but not the other session's. Agents were told to treat
  `finals_pack/prep/` as absent, so they did not see `PROPOSALS_14NOV.md` or this file.
- The scenario files follow the real formats of `scripts/portal_watch.py`, `scripts/clock.py` and
  `scripts/live.py`, and the inbox lines are the scripts' own strings. Teams, scores, versions and the variant
  are invented. Every scenario but S15 uses 8 players, 50/30/20, weights 1-6 and a 300-second cooldown.
- **One draw per role per scenario.** A second pair might split where this pair agreed. The "slow" marks rest
  on the agents' own account of what they inferred and what took longest.
- **No time pressure.** Each agent took 2.5 to 4.5 minutes and 17 to 29 file reads or searches. On Sunday the
  same question has under a minute. Treat every "slow" as a possible miss.
- Three artefacts of the scenarios, not of the bundle: no `notes/PLAN-<session>.md` was supplied, so every agent
  listed it as missing; S12's field-trend file says "570 of our opens were 3-bet" where its card says our 3-bets
  (my slip, which BUILDER caught); one S17 search printed two lines from `prep/`, which the agent said it did
  not use.
- The complete scenario folders, the generator and the 36 answer files are in the shared notes folder under
  `tabletop/`. The appendix below shows each scenario's files with old round rows and standard headers cut, and
  both answers in full.

## Appendix: the scenarios and the agents' answers
### S01. A clear challenger win

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:32:10 on Sunday. Scored round 3 starts at 14:40:00.

`state/status.md`
```
# Portal status (written 14:32:06 by scripts/portal_watch.py)

Last poll 14:32:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v9.zip** (sha256 7c1e09a44b2d…), uploaded 13:57
Declared live bot (state/live.json): **v9** (round 2: live bot unchanged) — MATCHES the portal
Next on the clock: Scored round 3 at 14:40

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 1.5 | Round 1.5 | 14:10 | finished · data saved | v10 | 12/20 · 12.20 ±0.56 | 2 Curry 15.02 |
| Round 2 | Round 2 | 14:20 | finished · data saved | v9 | 7/20 · 13.20 ±0.28 | Fold Equity 15.20 |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 3/20 · 14.80 ±0.55 | Fold Equity 15.62 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 46.20 |
| 2 | 2 Curry | 44.90 |
| 3 | River Rats | 42.30 |
| 4 | Tilt Shift | 41.80 |
| 5 | Check Mates | 40.60 |
| 6 | **avalon** | 39.90 |
| 7 | Pot Committed | 39.50 |
| 8 | Gutshot | 38.80 |
| 9 | Limp Mode | 38.10 |
| 10 | Kicker Trouble | 37.90 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:27 | v11.zip | ready |  |
| 14:07 | v10.zip | ready |  |
| 13:57 | v9.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:32:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:32: minute 92 · stage **Round 2.5** · next: scored round 3 at 14:40 (T-8)
Live bot (state/live.json): **v9** · the portal runs: v9.zip
| **Scored round 3** | 14:40 | **next** |
Next steps: 14:34 (T-6 of round 3); 14:35 (T-5 of round 3); 14:37 (T-3 of round 3)
```

`state/live.json`: bot **v9**, why "round 2: live bot unchanged", declared 14:14:40, previous none.

`state/decisions.md`
```
(rounds 1 and 2: not shown)

## Round 3: which bot? (DRAFT, started 14:20:30 by BUILDER; not asked yet)
- Options: v9 (live) or v11 (challenger).
- Rule: DECISION_RULES §3. Numbers: waiting for Round 2.5 and RESEARCH's recommendation.
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L38 | 14:21 | tester | verdict v11 (sha256 e03b5f19c7aa): correct; vs live v9 +0.1 ± 0.4; heads-up +0.3 ± 0.4 | +0.1 ± 0.4 | 2,000 tables + 2,000 heads-up | paired, 8 players, sparring mix refit to Round 1, identical deals; --players 2 | rig/out/v11-verdict.md | validated
L41 | 14:29 | analyst | one-change Round 2: call river bets wider against Tilt Shift seats | +0.2 ± 0.3 | 311 spots | replay on Round 2 hands | analysis/Round-2/leaks.md | proposed
L42 | 14:32 | tester | field-adjusted edge v11 (Round 2.5) vs v9 (Round 2), 9 yardsticks | +1.90 ± 0.90 (z 2.1) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-2.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v9 | 3a1f7c2 | 7c1e09a44b2d… | style A + theory refits from practice 3 | 0 failed of 48,112; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 4.8) | live (rounds 1-2) | correct; vs v7 +0.3 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor check_or_fold 9.8 in the same field (L21)
v10 | 51be2aa | 2f6d…  | style B rebuilt on the newest tables | 0 failed; upload test 5/5 | practice (Round 1.5) | correct; heads-up −0.4 ± 0.4 (L30)
v11 | 8d02e5b | e03b5f19c7aa… | design D matured: twist-first, limp-or-shove under 15bb | 0 failed of 51,007; p99 0.24 ms; upload test 5/5 (check_or_fold 5/5, load 5.5) | challenger (round 3 window) | correct; vs live v9 +0.1 ± 0.4 (paired, 2,000 tables); heads-up +0.3 ± 0.4; floor check_or_fold 9.9 (L38)
```

`analysis/Round-2.5/card.md`
```
# Round 2.5 (practice, 1,000 tables): card written 14:32:01

**Headline: v11 scored 14.80 ±0.55, 3rd of 20. Field median 12.45. 1st Fold Equity 15.62.** 0 missed decisions of 61,204.
(the rest of the card is not needed before the decision)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-2.5-edge.md`
```
# Field-adjusted edge, round 3 window (tester, written 14:32:04)

Yardstick teams (analysis/Round-2.5/fp/yardsticks.json, same bot in Round 2 and Round 2.5): 9
(Check Mates, Gutshot, Pot Committed, Limp Mode, Kicker Trouble, Cold Four, Stack Overflowed, Bluff Daddy, Ace High).

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v11, Round 2.5 (practice, 1,000 tables) | 14.80 | 12.60 | +2.20 |
| Live v9, Round 2 (scored, 4,000 tables) | 13.20 | 12.90 | +0.30 |

Edge = +2.20 − 0.30 = **+1.90**; SE of the edge 0.90 (practice SE 0.7 floor, yardstick means, the scored round); **z = 2.1**.
The edge has not been re-run by a second method.
```

`inbox/builder.log` (last 3 of 6 lines shown to the agent)
```
14:31:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:31:55 [portal] Round 2.5 finished: we were 3 of 20 with 14.80 (±0.55); 1st Fold Equity 15.62 · played by v11 · data: data/rounds/08-Round-2.5/ · health: 0 missed of 61,204 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:32:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 3 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:35).
```

`inbox/research.log` (last 3 of 5 lines shown to the agent)
```
14:31:55 [portal] Round 2.5 finished: we were 3 of 20 with 14.80 (±0.55); 1st Fold Equity 15.62 · played by v11 · data: data/rounds/08-Round-2.5/ · health: 0 missed of 61,204 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:31:56 [portal] DATA LANDED Round 2.5 data/rounds/08-Round-2.5/ (hands-first-1000.jsonl.gz, results.json; portal_watch is running roundcard.py and fp_train.py on it now)
14:32:00 [clock] Decision time for scored round 3 (14:40): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:28:20 you told Dylan: "activate v11.zip now (it's uploaded) for the 14:30 practice". Dylan 14:28:40: "done".
- 14:31:05 you told Dylan: "put v9 back now (a click)". Dylan 14:31:20: "v9 is back".
- 14:31:02 SendMessage from RESEARCH: "RECOMMENDATION round 3 (threshold): we are 6th with 39.9; 3rd is River Rats 42.3. 9 yardstick teams. v9 was +0.30 over the yardsticks in Round 2. v11 has tester's verdict with a heads-up run (L38). The final answer follows when Round 2.5 lands."
- Nothing from RESEARCH since. Dylan is at the laptop.
- Subagents: platform (idle since releasing v11 at 14:24), stylist x1 (on L41, due 14:31, not reported), challenger (building the round-4 challenger since 14:27).
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:31:02 you sent BUILDER the threshold message for round 3 (9 yardsticks; v9 +0.30 over them in Round 2).
- 14:32:05 tester reported: "edge written to rig/out/Round-2.5-edge.md and L42: +1.90 ± 0.90, z 2.1; not re-run by a second method".
- Samuel is at his laptop (Remote Control); his last message, 14:26: "ok".
- Subagents: tester (as above), scout (field trend for Round 2 done 14:28, counters running), analyst x3 (lenses on Round 2, two reported).
```

#### S01: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes

- 14:32 Check `rig/out/Round-2.5-edge.md` against `state/status.md` (14.80, 13.20). Finish the round-3 entry in `state/decisions.md`, ask Dylan, message RESEARCH. Background brief to idle `platform`: re-run v11's no-time-bank upload test (`check_or_fold` baseline, `uptime`), report by 14:35.
- 14:33 Stylist: L41 (z 0.7) is not in round 3; finish it for the next practice.
- 14:35 Record Dylan's words, or with no clear answer apply the rule: `python3 scripts/live.py v11 "round 3: z 2.1 vs bar 0.5"`, once platform's test passed. Tell Dylan: "click v11.zip active now (no upload)". A failed run, or "v9" from Dylan: v9 stays, no click.
- 14:36 Cut-off check: v11's zip, VERSIONS line and verdict (L38) exist.
- 14:37 Confirm `state/status.md`: active v11.zip, e03b5f19c7aa, MATCHES.
- 14:40 Check status.md says round 3 plays v11; update `notes/PLAN-builder.md`; 3-line sync to RESEARCH.

Outcome I expect: v11 is active and declared when round 3 starts at 14:40 (v9 only if Dylan says so or v11 fails the re-test).

##### 2. What I say

Dylan: "Which bot plays round 3 (14:40): v9 (live) or v11 (challenger)? v11 scored 14.80 in the practice, 3rd of 20. Against the 9 teams that didn't change bots it is +1.9 ± 0.9 better than v9 was in round 2 (z 2.1; not re-run, so unverified). We're 6th, 2.4 behind 3rd, so the bar is z 0.5: cleared. v11 is tested, heads-up included. v11 is the new design: more upside, one practice of evidence. v9 scored 13.5 and 13.2. The rule's answer is releases/v11.zip (already uploaded, one click); it plays if nobody answers by 14:35. Don't click yet: I'll say when."

RESEARCH: "Round 3 asked 14:32, deadline 14:35. From L42 and rig/out/Round-2.5-edge.md: v11 +1.90 ± 0.90, z 2.1, bar 0.5 (6th, 39.9 vs 42.3). Rule's answer releases/v11.zip, labelled unverified. Send your final answer and Samuel's words; only a reproduced counter-number stops it. L41 (z 0.7) stays out of round 3."

##### 3. The rule that decides

- DECISION_RULES §3 "Which bot plays": "we are outside the top 3 ... z ≥ **0.5**". Stated.
- §4: "Only a line **disputed with a reproduced counter-number** blocks a switch"; §3 worked example 1: "Play the challenger, labelled 'unverified'". Stated.
- §3: "The rule's answer plays at T-5 if no human has answered". Stated.
- §2 rule 1: "only with a `tester` verdict that includes a heads-up run" (L38). Stated.
- §3 "Changes": "z ≥ 1 when we're outside the top 3" excludes L41. Stated.
- §3 "Uploads": "choosing the challenger, are clicks on bots already uploaded": no cooldown problem. Inferred.

Conflicts:
- PLAN §5 T9: "no practice result by T-6: the rule's answer is the live bot", and RESEARCH's final answer hasn't arrived; BUILDER.md T-8: "Ask the decision". I ask now with v11: the result and tester's edge are in the files; only the relay is missing. Inferred.
- L38's local "+0.1 ± 0.4" against the field's +1.9: §4 "Local wins do not predict the field". Field followed. Stated.

##### 4. What I lacked

- Missing: `notes/PLAN-builder.md` (agent ids), `yardsticks.json`, `rig/out/v11-verdict.md`, `data/`.
- Guesses: RESEARCH's final answer will repeat L42; T-6's re-test applies to an already-passed zip; Dylan clicks after it; a best-of-2 discount leaves z about 1.5.
- Opened: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; PLAN.md; scripts/README.md; every permitted scenario file; timeline.json; LESSONS.md lines 116-131.
- Longest to find: what applies with RESEARCH's final answer missing at T-8 (PLAN §5, T9 row).

#### S01: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:32 Check `rig/out/Round-2.5-edge.md` against `state/status.md`; check v11 passes rule 2.1 (VERSIONS line, L38, heads-up) and is on the portal. Send BUILDER the final recommendation, log it (`say.py --record`), tell Samuel.
- 14:33 Continue `tester`: re-run the edge a second way (raw `results.json`; scores minus field median), two minutes, mark L42 validated or disputed.
- 14:34-14:35 Relay Samuel's exact words if he answers. Re-run lands: one line to BUILDER; the recommendation changes only on a reproduced counter-number under z 0.5. At 14:35 the rule's answer (v11) plays unanswered.
- 14:37 Read `state/status.md`: active bot v11.zip, matching `state/live.json`; if not, tell BUILDER and Samuel at once. Update LEDGER and `notes/PLAN-research.md`.
- 14:38 Start the full analysis loop on Round 2.5.
- 14:40 T-20 sync, step back.

Outcome I expect: v11 (`releases/v11.zip`) is active when scored round 3 starts at 14:40, by a click, no upload.

##### 2. What I say
To Samuel: "The rule says we play the new bot, v11, in round 3. It just scored 14.80 in practice, 3rd of 20; against the nine teams that kept the same bot, it is about 1.9 points per table better than v9, give or take 0.9. We are 6th, 2.4 behind 3rd, so this clears the bar easily. v11 is fully tested, heads-up included, and already on the portal: one click for Dylan. One caveat: the 1.9 was computed once; the tester re-computes it another way by 14:35. With no answer by 14:35, v11 plays. Say 'v11' or 'v9' here and I pass on your exact words; otherwise nothing right now."

To BUILDER: "RECOMMENDATION round 3: play v11 (releases/v11.zip, sha256 e03b5f19c7aa…, on the portal since 14:27: a click, no upload). Rule: 6th at 39.90, 2.40 behind 3rd → bar z ≥ 0.5. v11 Round 2.5 14.80 minus 9 yardsticks 12.60 = +2.20; v9 Round 2 13.20 − 12.90 = +0.30; edge +1.90 ± 0.90, z 2.1: UNVERIFIED (L42 proposed, rig/out/Round-2.5-edge.md; tester's re-run due 14:35). Rule 2.1 passed: upload test 5/5, 0 failed of 51,007, verdict with heads-up +0.3 ± 0.4 (L38 validated). L41 (z 0.7) is under the z ≥ 1 bar: next practice, not this round."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays a scored round" (stated): "we are outside the top 3 ...: z ≥ **0.5**".
- DECISION_RULES §2 rule 1 (stated): "only with a `tester` verdict that includes a heads-up run."
- DECISION_RULES §4 (stated): "Only a line **disputed with a reproduced counter-number** blocks a switch." Pointing the other way, prompts/RESEARCH.md "Verification": "anything a decision rests on gets re-run by `tester`". I followed §4: its page "overrides anything older or vaguer", and its first worked example ends "Play the challenger, labelled "unverified"".
- DECISION_RULES §3 "Uploads" (stated): "choosing the challenger, are clicks on bots already uploaded".
- Inferred: no separate PLAN CHALLENGE; this practice already judged the alternative.

##### 4. What I lacked
- `data/rounds/` and `analysis/Round-2.5/fp/yardsticks.json`: I could not re-count the edge myself.
- `notes/PLAN-research.md` (BUILDER's session id, tester's agent id).
- Guesses: Samuel's 14:26 "ok" answers nothing here; tester re-runs in two minutes; BUILDER declares v11 with `live.py`.
- Files, in order: brief; CLAUDE.md; prompts/RESEARCH.md; DECISION_RULES.md; every permitted scenario file; PLAN.md; scripts/README.md; greps of agents/tester.md and LESSONS.md.
- Longest to find: that an edge computed once still switches the bot (§4).


### S02. An edge inside the noise

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:52:05 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:52:01 by scripts/portal_watch.py)

Last poll 14:52:01: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v12** (round 3: v9 + two fixes) — MATCHES the portal
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 5/20 · 13.50 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 8/20 · 13.60 ±0.56 | 2 Curry 15.05 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | 2 Curry | 86.00 |
| 3 | Tilt Shift | 82.40 |
| 4 | River Rats | 81.70 |
| 5 | **avalon** | 80.40 |
| 6 | Check Mates | 80.10 |
| 7 | Gutshot | 78.80 |
| 8 | Pot Committed | 77.90 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:52:02)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:52: minute 112 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-8)
Live bot (state/live.json): **v12** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:54 (T-6 of round 4); 14:55 (T-5 of round 4); 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v12**, why "round 3: v9 + two fixes", declared 14:34:50, previous v9.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? (DRAFT, started 14:40:20 by BUILDER; not asked yet)
- Options so far: v12 (live), v13 (challenger), v14 (v12 + F1 + F2, released 14:50:40).
- Rule: DECISION_RULES §3. Numbers: waiting for Round 3.5's edge.
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L51 | 14:42 | tester | verdict v13 (sha256 9ab27d10e4c3): correct; vs live v12 +0.0 ± 0.4; heads-up +0.2 ± 0.4 | +0.0 ± 0.4 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v13-verdict.md | validated
L52 | 14:46 | analyst | one-change Round 3 (F1): call 3-bet shoves wider at 20bb or less; seen in Round 2 and Round 3 (persistent) | +0.35 ± 0.27 (z 1.3) | 902 spots over two rounds | replay on Round 2 + Round 3 hands | analysis/Round-3/leaks.md | validated (tester 14:49, recount +0.33)
L55 | 14:47 | analyst | one-change Round 3 (F2): stop min-raise-folding against Gutshot seats (they 3-bet 31% of min-raises) | +0.30 ± 0.27 (z 1.1) | 644 spots | replay on Round 3 hands | analysis/Round-3/opponent_gutshot.md | validated (tester 14:50, recount +0.29)
L58 | 14:51 | tester | verdict v14 (sha256 c58f3e7712d0): correct; vs live v12 +0.5 ± 0.3; heads-up +0.2 ± 0.4; F1 fired 412, F2 fired 1,038; F1's call rate 38% vs target 40% | +0.5 ± 0.3 | 2,000 tables + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v14-verdict.md | validated
L59 | 14:52 | tester | field-adjusted edge v13 (Round 3.5) vs v12 (Round 3), 7 yardsticks | +0.30 ± 0.80 (z 0.38) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-3.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
v14 | 2c7be80 | c58f3e7712d0… | v12 + F1 (call 3-bet shoves wider at 20bb or less) + F2 (no min-raise-fold vs Gutshot seats), each behind a setting, fired 412 and 1,038 times in 2,000 tables | 0 failed of 50,904; p99 0.21 ms; upload test 5/5 (check_or_fold 5/5, load 5.7) | live candidate (round 4) | correct; vs live v12 +0.5 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.8 (L58)
```

`analysis/Round-3.5/card.md`
```
# Round 3.5 (practice, 1,000 tables): card written 14:51:58

**Headline: v13 scored 13.60 ±0.56, 8th of 20. Field median 12.50. 1st 2 Curry 15.05.** 0 missed decisions of 58,330.
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-3.5-edge.md`
```
# Field-adjusted edge, round 4 window (tester, written 14:52:00)

Yardstick teams (analysis/Round-3.5/fp/yardsticks.json, same bot in Round 3 and Round 3.5): 7.

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v13, Round 3.5 (practice, 1,000 tables) | 13.60 | 12.40 | +1.20 |
| Live v12, Round 3 (scored, 4,000 tables) | 13.50 | 12.60 | +0.90 |

Edge = +1.20 − 0.90 = **+0.30**; SE of the edge 0.80; **z = 0.38**. Not re-run by a second method.
```

`inbox/builder.log` (last 3 of 5 lines shown to the agent)
```
14:51:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:51:50 [portal] Round 3.5 finished: we were 8 of 20 with 13.60 (±0.56); 1st 2 Curry 15.05 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:52:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 4 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:55).
```

`inbox/research.log` (last 3 of 5 lines shown to the agent)
```
14:51:50 [portal] Round 3.5 finished: we were 8 of 20 with 13.60 (±0.56); 1st 2 Curry 15.05 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:51:51 [portal] DATA LANDED Round 3.5 data/rounds/10-Round-3.5/ (hands-first-1000.jsonl.gz, results.json; portal_watch is running roundcard.py and fp_train.py on it now)
14:52:00 [clock] Decision time for scored round 4 (15:00): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:47:50 you told Dylan: "upload releases/v13.zip and make it active for the 14:50 practice". Dylan 14:48:10: "uploaded 14:47:55, active".
- 14:50:45 platform reported: "releases/v14.zip released (v12 + F1 + F2), VERSIONS line written, upload test 5/5". You sent RESEARCH "RELEASED v14 c58f3e7712d0 v12+F1+F2" at 14:50:50. v14 has not been uploaded to the portal.
- 14:51:05 you told Dylan: "put v12 back now (a click)". Dylan 14:51:20: "v12 is back".
- 14:51:10 SendMessage from RESEARCH: "RECOMMENDATION round 4 (threshold): we are 5th with 80.4; 3rd is Tilt Shift 82.4. 7 yardstick teams. v12 was +0.90 over the yardsticks in Round 3. v13 and v14 both have tester's verdict with a heads-up run (L51, L58). F1 (L52) and F2 (L55) are validated. The final answer follows when Round 3.5 lands."
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:51:10 you sent BUILDER the threshold message for round 4 (7 yardsticks; v12 +0.90 over them in Round 3; v13 and v14 both have verdicts with a heads-up run; F1 and F2 validated).
- 14:52:00 tester reported: "edge written to rig/out/Round-3.5-edge.md and L59: +0.30 ± 0.80, z 0.38".
- Samuel is at his laptop; his last message, 14:45: "send me the round 4 call when you have it".
```

#### S02: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:52 v13's edge is +0.30 ± 0.80, z 0.38. We're 5th, bar 0.5: v13 misses. Rule's answer: v14 (v12 + F1 z 1.3 + F2 z 1.1; verdict L58 with heads-up; upload test 5/5). Write the round-4 entry in state/decisions.md, ask Dylan, message RESEARCH (`say.py --record`). Spawn a fresh `bughunter` on v14 (report by 14:56).
- 14:53 Dylan uploads v14 (cooldown ended 14:52:55). Check status.md: v14.zip "ready", sha c58f3e7712d0. Rejected: v12 plays (next slot 14:58 is past T-3).
- 14:54 (T-6) Upload test already in v14's VERSIONS line, same sha: no re-run. Read RESEARCH's final answer.
- 14:55 (T-5) Record Dylan's clear answer in his words; otherwise `live.py v14 "round 4: rule's answer, no answer by T-5"`. Tell Dylan once: "click v14 active now".
- 14:56 (T-4) Cut-off met. Bughunter reproduces a bug: re-declare v12.
- 14:57 (T-3) Confirm status.md: active v14.zip, MATCHES. Update decisions.md, PLAN-builder.md.
- 15:00 Check round 4 plays v14. T-20 sync; round-5 draft with the last-rounds bar (z ≥ 0).

Outcome I expect: v14 is active when round 4 starts (v12 only after a rejected upload or reproduced bug; v13 only if Dylan says so).

##### 2. What I say
Dylan: "Decision by 14:55: which bot plays round 4? We're 5th on 80.4, 3rd is 82.4, so the challenger needs z ≥ 0.5. v13 scored 13.60: +0.30 ± 0.80 over v12 against the 7 unchanged teams, z 0.38 (unverified), about 0.1 points short. v14 is v12 plus two fixes that cleared the bar on real hands (z 1.3 and 1.1); locally +0.5 ± 0.3 over v12, heads-up fine, upload test 5/5. Rule's answer: releases/v14.zip; it plays if nobody answers by 14:55. 'v12' stands still; 'v13' gambles on the challenger. Whatever you answer: upload releases/v14.zip at 14:53 (cooldown ends 14:52:55) and leave v12 active until I say."

RESEARCH: "Round 4 asked 14:52, deadline 14:55. Rule's answer releases/v14.zip (c58f3e7712d0): v13 z 0.38 < 0.5 (rig/out/Round-3.5-edge.md, L59 proposed); F1 L52, F2 L55, verdict L58. Before 14:55 send: final answer, Samuel's words, any counter-number on L59 (v13 needs edge ≥ +0.40)."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "outside the top 3 … z ≥ **0.5**"; "Otherwise the live bot plays, with this window's changes". Stated.
- §3 "Changes": "real-data support of z ≥ 1 when we're outside the top 3". Stated.
- §3: "The rule's answer **is** the default". Stated.
- §4: "Unverified is not wrong." Stated.
- Conflict: §1 "When a choice is close, prefer the option that learns more or gains more" against the 0.5 bar. Followed the bar: pre-registered, and v14 is itself a change.
- Conflict: §3 "Uploads": "the chosen bot at about T-4 to T-3" against "Never let a cooldown leave the chosen bot unuploaded at T-3". Followed the second, uploading at T-7 before the answer (inferred: uploading isn't activating).

##### 4. What I lacked
- Lacked: whether an upload activates itself; notes/PLAN-builder.md (is a bughunter on v14?); rig/out/v14-verdict.md; RESEARCH's final answer.
- Guesses: no bughunter running; cooldown counts from 14:47:55; a T-6 re-test is unnecessary; the last-rounds bar starts at round 5.
- Opened: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; every S02 file except RESEARCH's two; PLAN.md; scripts/README.md; LESSONS.md; START.md; timeline.json; live.py.
- Longest: whether v14 may be uploaded before the decision. Nothing says so.

#### S02: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:52 Recheck the arithmetic in `rig/out/Round-3.5-edge.md` (+0.30, z 0.38) and the bar (5th: 0.5). Send BUILDER the final recommendation (logged with `say.py --record`); answer Samuel.
- 14:53 Same tester, 2-minute limit: re-run the edge another way (recount the 7 yardsticks; field-median cross-check); mark L59 validated or disputed.
- 14:54 Only if it reproduces z ≥ 0.5: corrected answer to BUILDER and Samuel (v13 is a click).
- 14:55 Relay Samuel's exact words if he answered; otherwise BUILDER applies v14.
- 14:57 Read `state/status.md`: v14 active, else v12. Update LEDGER and `notes/PLAN-research.md`; spawn the full Round 3.5 analysis loop.

Outcome I expect: v14 is active when round 4 starts (one upload, 14:53-14:57); if that misses, v12, active now, plays.

##### 2. What I say
Samuel: "Round 4 call: play v14, our round-3 bot plus the two checked fixes, not the challenger v13. v13 scored 13.60 (8th) in practice; against the 7 teams that kept their bot it was 0.30 ± 0.80 better than v12. At 5th, 2.0 behind 3rd, it needed 0.40. A near miss, not double-checked: tester re-runs it by 14:54 and I'll say at once if it flips. The fixes measured +0.35 and +0.30 on replayed hands; v14 beat v12 by 0.5 ± 0.3 in our test and is fine heads-up. Say v14, v13 or v12 by 14:55 and I pass on your exact words; say nothing and v14 plays."

BUILDER: "RECOMMENDATION round 4 (final): play v14 (releases/v14.zip, sha256 c58f3e7712d0). 5th, 2.00 behind 3rd: bar z ≥ 0.5. v13 Round 3.5: 13.60, +1.20 over 7 yardsticks; v12 Round 3: 13.50, +0.90. Edge +0.30 ± 0.80, z 0.38 (needed 13.70): v13 doesn't qualify (rig/out/Round-3.5-edge.md, L59, unverified; re-run due 14:54). Rule's answer, live bot with this window's changes: v14. F1 (L52, z 1.3), F2 (L55, z 1.1) validated; verdict L58 +0.5 ± 0.3 vs v12, heads-up +0.2 ± 0.4. v14 isn't on the portal (v13 uploaded 14:47, cooldown 300 s): one real upload; v12 plays if v14 isn't active by 14:57."

##### 3. The rule that decides
- DECISION_RULES §3, Which bot plays: "we are outside the top 3 ... z ≥ **0.5**"; "Otherwise the live bot plays, with this window's changes". Stated.
- Same: "z ≥ 0 in the last two rounds". Round 4 of 6 isn't one: inferred (`state/clock.md`).
- §3, Changes: "real-data support of z ≥ 1 when we're outside the top 3". Stated.
- §2 rule 1: "only with a `tester` verdict that includes a heads-up run". Stated.
- Two ways: RESEARCH.md, Verification, "anything a decision rests on gets re-run by `tester`" against §4 "Unverified is not wrong ... say so and decide". I decided now, labelled unverified, re-running in parallel.
- Two ways: §1 "When a choice is close, prefer the option that learns more" favours v13; I followed the numeric bar, the pre-registered answer.

##### 4. What I lacked
- Absent: `notes/PLAN-research.md` (BUILDER's and the tester's ids), `data/rounds/`, `yardsticks.json`.
- Guesses: uploading doesn't activate by itself; the cooldown clears 14:52-14:53; the bar compares v13 with v12, not v14; "last two rounds" means 5 and 6; SE 0.80 is right (I get 0.79); a 2-minute re-run is feasible.
- Opened: brief; CLAUDE.md, RESEARCH.md, DECISION_RULES.md; every permitted scenario file (NOW.md first, edge file last); PLAN.md, scripts/README.md, LESSONS.md; greps of tester.md, challenger_bar.md, timeline.json.
- Longest: that "with this window's changes" means v14, not v12.


### S03. The challenger looks better but has no tester verdict

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:32:10 on Sunday. Scored round 3 starts at 14:40:00.

`state/status.md`
```
# Portal status (written 14:32:06 by scripts/portal_watch.py)

Last poll 14:32:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v9.zip** (sha256 7c1e09a44b2d…), uploaded 13:57
Declared live bot (state/live.json): **v9** (round 2: live bot unchanged) — MATCHES the portal
Next on the clock: Scored round 3 at 14:40

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 1.5 | Round 1.5 | 14:10 | finished · data saved | v10 | 12/20 · 12.20 ±0.56 | 2 Curry 15.02 |
| Round 2 | Round 2 | 14:20 | finished · data saved | v9 | 7/20 · 13.20 ±0.28 | Fold Equity 15.20 |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 2/20 · 15.40 ±0.55 | Fold Equity 15.62 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 46.20 |
| 2 | 2 Curry | 44.90 |
| 3 | River Rats | 42.30 |
| 4 | Tilt Shift | 41.80 |
| 5 | Check Mates | 40.60 |
| 6 | **avalon** | 39.90 |
| 7 | Pot Committed | 39.50 |
| 8 | Gutshot | 38.80 |
| 9 | Limp Mode | 38.10 |
| 10 | Kicker Trouble | 37.90 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:27 | v11.zip | ready |  |
| 14:07 | v10.zip | ready |  |
| 13:57 | v9.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:32:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:32: minute 92 · stage **Round 2.5** · next: scored round 3 at 14:40 (T-8)
Live bot (state/live.json): **v9** · the portal runs: v9.zip
| **Scored round 3** | 14:40 | **next** |
Next steps: 14:34 (T-6 of round 3); 14:35 (T-5 of round 3); 14:37 (T-3 of round 3)
```

`state/live.json`: bot **v9**, why "round 2: live bot unchanged", declared 14:14:40, previous none.

`state/decisions.md`
```
(rounds 1 and 2: not shown)

## Round 3: which bot? (DRAFT, started 14:20:30 by BUILDER; not asked yet)
- Options: v9 (live) or v11 (challenger, a rewrite released 14:26:30).
- Rule: DECISION_RULES §3. Numbers: waiting for Round 2.5 and RESEARCH's recommendation.
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L39 | 14:31 | tester | v11 (sha256 e03b5f19c7aa) correctness and timing only: 0 failed decisions of 51,007, p99 0.31 ms, no crash in 400 tables; strength and heads-up NOT run yet | n/a | 400 tables | 8 players, sparring mix | rig/out/v11-partial.md | proposed
L41 | 14:29 | analyst | one-change Round 2: call river bets wider against Tilt Shift seats | +0.2 ± 0.3 | 311 spots | replay on Round 2 hands | analysis/Round-2/leaks.md | proposed
L42 | 14:32 | tester(2) | field-adjusted edge v11 (Round 2.5) vs v9 (Round 2), 9 yardsticks | +2.50 ± 0.90 (z 2.8) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-2.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v9 | 3a1f7c2 | 7c1e09a44b2d… | style A + theory refits from practice 3 | 0 failed of 48,112; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 4.8) | live (rounds 1-2) | correct; vs v7 +0.3 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor check_or_fold 9.8 in the same field (L21)
v11 | 8d02e5b | e03b5f19c7aa… | REWRITE: twist-first engine, limp-or-shove under 15bb, new postflop tree | 0 failed of 51,007; p99 0.31 ms; upload test 5/5 (check_or_fold 5/5, load 6.1) | challenger (round 3 window) | pending (tester started 14:27)
```

`analysis/Round-2.5/card.md`
```
# Round 2.5 (practice, 1,000 tables): card written 14:32:01

**Headline: v11 scored 15.40 ±0.55, 2nd of 20. Field median 12.45. 1st Fold Equity 15.62.** 0 missed decisions of 60,877.
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-2.5-edge.md`
```
# Field-adjusted edge, round 3 window (tester, written 14:32:04)

Yardstick teams (analysis/Round-2.5/fp/yardsticks.json, same bot in Round 2 and Round 2.5): 9
(Check Mates, Gutshot, Pot Committed, Limp Mode, Kicker Trouble, Cold Four, Stack Overflowed, Bluff Daddy, Ace High).

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v11, Round 2.5 (practice, 1,000 tables) | 15.40 | 12.60 | +2.80 |
| Live v9, Round 2 (scored, 4,000 tables) | 13.20 | 12.90 | +0.30 |

Edge = +2.80 − 0.30 = **+2.50**; SE of the edge 0.90 (practice SE 0.7 floor, yardstick means, the scored round); **z = 2.8**.
The edge has not been re-run by a second method.
```

`inbox/builder.log` (last 3 of 6 lines shown to the agent)
```
14:31:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:31:55 [portal] Round 2.5 finished: we were 2 of 20 with 15.40 (±0.55); 1st Fold Equity 15.62 · played by v11 · data: data/rounds/08-Round-2.5/ · health: 0 missed of 60,877 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:32:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 3 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:35).
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
14:31:55 [portal] Round 2.5 finished: we were 2 of 20 with 15.40 (±0.55); 1st Fold Equity 15.62 · played by v11 · data: data/rounds/08-Round-2.5/ · health: 0 missed of 60,877 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:31:56 [portal] DATA LANDED Round 2.5 data/rounds/08-Round-2.5/ (hands-first-1000.jsonl.gz, results.json; portal_watch is running roundcard.py and fp_train.py on it now)
14:32:00 [clock] Decision time for scored round 3 (14:40): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:26:35 platform reported: "releases/v11.zip released (the rewrite), VERSIONS line written, upload test 5/5, 0 failed decisions". You sent RESEARCH "RELEASED v11 e03b5f19c7aa rewrite" at 14:26:40. bughunter (fresh, started 14:26:45) reported 14:31:30: "no reproducible bug in v11".
- 14:27:30 you told Dylan: "upload releases/v11.zip and make it active for the 14:30 practice". Dylan 14:27:50: "uploaded, active".
- 14:31:05 you told Dylan: "put v9 back now (a click)". Dylan 14:31:20: "v9 is back".
- 14:31:10 SendMessage from RESEARCH: "RECOMMENDATION round 3 (threshold): we are 6th with 39.9; 3rd is River Rats 42.3. 9 yardstick teams. v9 was +0.30 over the yardsticks in Round 2. v11's tester is still running: correctness and timing are done (L39: 0 failed, p99 0.31 ms); the paired strength run is on Modal and the heads-up run is queued behind it; tester expects its verdict at about 14:37. The final answer follows when Round 2.5 lands."
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:26:40 BUILDER sent: "RELEASED v11 e03b5f19c7aa rewrite". You spawned a fresh tester on it at 14:27:00.
- 14:31:05 that tester reported: "v11 partial (L39): 0 failed decisions of 51,007, p99 0.31 ms, no crash. Paired strength run vs v9 is on Modal (avalon-rig, 2,000 tables, about 4 more minutes); the heads-up run (--players 2) is queued behind it. Full verdict about 14:37."
- 14:31:10 you sent BUILDER the threshold message for round 3, saying so.
- 14:32:05 a second tester reported: "edge written to rig/out/Round-2.5-edge.md and L42: +2.50 ± 0.90, z 2.8".
- Samuel is at his laptop; his last message, 14:26: "ok".
```

#### S03: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:32 status.md and clock.md are fresh; edge arithmetic checked (+2.50, z 2.8). Fill the Round 3 entry in `state/decisions.md`; ask Dylan; SendMessage RESEARCH (+ `say.py --record`). v9 stays active; `live.py` untouched.
- 14:33 Continue `platform` (background, 3 minutes): confirm `releases/v11.zip` is sha e03b5f19c7aa, re-run the no-time-bank upload test beside `check_or_fold`. L41 (z 0.7) does not ship.
- 14:35 Record Dylan's words. No answer: the conditional rule's answer stands; say so.
- 14:36 Check LEDGER for tester's v11 verdict; read its heads-up number myself. If RESEARCH's ETA is past 14:37, call v9 now, tell both humans.
- 14:37 Verdict in, heads-up included, fit: `live.py v11 "round 3: z 2.8, verdict in"`, Dylan clicks v11.zip, status.md must say MATCHES. Otherwise v9 stays; report the miss and its cause.
- 14:38-14:42 Confirm status.md; update PLAN-builder; T-20 sync; if missed, v11 is round 4's candidate.

Outcome I expect: v11 is active at 14:40 only if tester's verdict with a heads-up run is in by 14:37 (about even odds); otherwise v9 unchanged. Never v11 without it.

##### 2. What I say
Dylan: "Decide by 14:35: which bot plays round 3 (weight 3 of 21), v9 (live) or v11 (the rewrite)? v11 just came 2nd of 20 in practice (15.40). Against the 9 teams that didn't change bots it is 2.5 ± 0.9 a table better than v9 (z 2.8, unverified). We're 6th, 2.4 behind 3rd, so the bar is z 0.5: cleared. The catch: v11's strength and heads-up tests are still running (due about 14:37), and no bot plays a scored round without them. Rule's answer, which plays if you say nothing: v11 if that verdict is in by 14:37 with no heads-up hole, else v9 unchanged. Nothing to do now; v9 stays active. At 14:36 I'll say 'click v11.zip active' (already uploaded) or 'leave v9'."

RESEARCH: "Round 3: v11 clears the bar (L42: 2.50 ± 0.90, z 2.8; bar 0.5 at 6th) but cannot play without tester's verdict including a heads-up run. I need it as a LEDGER line by 14:37:00 or v9 plays. Re-scope, don't rush: can the heads-up run start now in parallel on avalon-rig, smaller if needed, instead of queued behind the paired run? Honest ETA now, please; relay Samuel's answer by 14:35."

##### 3. The rule that decides
- DECISION_RULES §2.1, stated: "A bot plays a scored round only with a `tester` verdict that includes a heads-up run."
- §3, stated: "Play the challenger if it passed rule 2.1 and ... outside the top 3 ...: z ≥ 0.5".
- §3 cut-offs, stated: "deliver a smaller version or let the fallback happen; never skip a test".
- BUILDER.md, stated: "A conditional answer is recorded when its condition holds"; a conditional rule's answer is inferred.
- Conflict: BUILDER.md T-4, "isn't released and tested with a tester verdict, the live bot plays" (14:36), against DECISION_RULES Deadlines, "can't be tested and uploaded by T-3 ... Don't wait past T-3" (14:37). I followed T-3 (inferred): DECISION_RULES overrides, T-4 buys upload time, and format.md says activating an uploaded bot "is instant".

##### 4. What I lacked
- What heads-up result fails a verdict; whether T-4 binds a click-only switch.
- Absent: notes/PLAN-builder.md, data/, yardsticks.json, v11-partial.md.
- Guesses: T-3 as the line; tester can parallelise; an unchanged zip still gets the T-6 test.
- Opened: brief, CLAUDE.md, BUILDER.md, DECISION_RULES.md, PLAN.md, scripts/README.md, scenario files; greps of tester.md, platform.md, LESSONS.md, timeline.json.
- Longest: T-4 against T-3.

#### S03: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:32 Re-scope the v11 tester: heads-up run (`--players 2`) first, not queued behind the paired run; locally (4 workers, about 600 tables) or ahead on avalon-rig; verdict by 14:35. Send BUILDER the final recommendation, log it (`say.py --record`), tell Samuel.
- 14:33 Second tester: re-run L42 another way (scores minus field median), 2-minute cap. Update notes/PLAN-research.md.
- 14:34 Relay Samuel's exact words to BUILDER if he answers.
- 14:35 Heads-up verdict lands. If fit: "VERDICT v11 ... fit; the rule's answer is now v11" to BUILDER.
- 14:36 (T-4) No verdict, or a heads-up regression: tell BUILDER and Samuel v9 plays, with the cause.
- 14:37 Check state/status.md: active bot matches state/live.json. Start the full Round 2.5 analysis loop.
- 14:40-14:42 Confirm round 3's "played by"; T-20 sync.

Outcome I expect: v11 active at 14:40, on a heads-up verdict landing about 14:35; if it is missing at 14:36 or shows a regression, v9 plays unchanged.

##### 2. What I say
Samuel: "v11 should play round 3, on one condition. It scored 15.40 in practice, 2nd of 20; against the 9 teams that kept their bot, that is +2.5 ± 0.9 over v9, far above the bar for 6th place (we're 2.4 behind 3rd). The condition: v11 has no heads-up test yet, and no bot plays a scored round without one. I've moved it to the front: result by 14:35. Clean: v11 plays, one click for Dylan. Not in by 14:36: v9 plays. BUILDER is asking 'which bot?' now; answer here by 14:35 and I pass on your exact words."

BUILDER: "RECOMMENDATION round 3: we're 6th (39.90; 3rd 42.30), bar z ≥ 0.5. v11, Round 2.5: 15.40 ± 0.55, +2.80 vs 9 yardsticks; v9, Round 2: 13.20, +0.30; edge +2.50 ± 0.90, z 2.8 (L42, rig/out/Round-2.5-edge.md, unverified). Rule's answer: releases/v11.zip (e03b5f19c7aa, uploaded 14:27: a click) ONLY once its tester verdict with a heads-up run lands; L39 is correctness only. Heads-up moved first; verdict to you by 14:35. Until my VERDICT message v9 stays declared and active. None by 14:36: releases/v9.zip plays unchanged (L41: z 0.7, under z ≥ 1)."

##### 3. The rule that decides
- DECISION_RULES §2 rule 1, stated: "A bot plays a scored round only with a `tester` verdict that includes a heads-up run."
- §3, stated: "outside the top 3 ... z ≥ 0.5". v11 clears it.
- §4, stated: "Unverified is not wrong." The unchecked edge doesn't block.
- Two deadlines differ. §3 cut-offs: "T-4: the chosen bot released and tested", else the live bot plays. §3 Deadlines: "can't be tested and uploaded by T-3". I followed T-4: `platform.md` ties the verdict to it, and Dylan needs a minute to click.
- Heads-up first: inferred from §3 "deadlines cut scope, never care" and LESSONS "Run locally at reduced n".
- LESSONS, stated: "A conditional answer is recorded when its condition holds". So v9 stays declared until the verdict.

##### 4. What I lacked
- No pass mark for a heads-up run; I guessed "no regression beyond 2 SE against v9".
- Guesses: a reduced heads-up run takes 2 minutes; a tester can be re-scoped by message; a verdict between T-5 and T-4 may still switch the bot.
- Absent: notes/PLAN-research.md, data/rounds/, yardsticks.json.
- Opened, in order: brief; CLAUDE.md; RESEARCH.md; DECISION_RULES.md; PLAN.md; scripts/README.md; the scenario files (not BUILDER's two); agents/tester.md; LESSONS.md; agents/platform.md; grep of BUILDER.md, timeline.json, clock.py.
- Longest to find: which deadline binds the verdict (T-5, T-4 or T-3).


### S04. The scored round's data lands at T-6 instead of T-10

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:54:10 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:54:08 by scripts/portal_watch.py)

Last poll 14:54:08: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v12** (round 3: v9 + two fixes) — MATCHES the portal
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 11/20 · 12.61 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 4/20 · 14.90 ±0.55 | 2 Curry 15.05 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | 2 Curry | 86.00 |
| 3 | Tilt Shift | 82.40 |
| 4 | River Rats | 81.70 |
| 5 | Check Mates | 80.10 |
| 6 | Gutshot | 78.80 |
| 7 | Pot Committed | 77.90 |
| 8 | **avalon** | 77.73 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:54:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:54: minute 114 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-6)
Live bot (state/live.json): **v12** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:55 (T-5 of round 4); 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v12**, why "round 3: v9 + two fixes", declared 14:34:50, previous v9.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? v12 (live) or v13 (challenger)
- Asked 14:52:10 by BUILDER. Deadline 14:55:00.
- Evidence at 14:52: Round 3 has not landed (the portal is slow; cut-off posted 14:50); Round 3.5 has not landed. No edge.
- The rule's answer at 14:52: v12 (live). v13 has tester's verdict with a heads-up run (L51) and is on the portal.
- Dylan, 14:52:40: "ok. whatever the rule says once the numbers are in"
- Samuel (relayed by RESEARCH 14:53:05): "same, go by the rule"
- Outcome: (open)
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L47 | 14:33 | analyst | one-change Round 2 (F0): 4-bet shove wider against seats that 3-bet over 25% | +0.25 ± 0.30 (z 0.8) | 388 spots | replay on Round 2 hands | analysis/Round-2/leaks.md | proposed (one round only)
L51 | 14:42 | tester | verdict v13 (sha256 9ab27d10e4c3): correct; vs live v12 +0.0 ± 0.4; heads-up +0.2 ± 0.4 | +0.0 ± 0.4 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v13-verdict.md | validated
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
```

`analysis/Round-3/README.txt`
```
(empty folder at 14:54:10: portal_watch started roundcard.py and fp_train.py on Round 3 at 14:54:06; neither has finished. analysis/Round-3.5/fp/yardsticks.json does not exist yet: the quick fingerprint run for Round 3.5 needs Round 3's hands and is waiting for them.)
```

`analysis/Round-3.5/card.md`
```
# Round 3.5 (practice, 1,000 tables): card written 14:53:52

**Headline: v13 scored 14.90 ±0.55, 4th of 20. Field median 12.45. 1st 2 Curry 15.05.** 0 missed decisions of 59,112.
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 7 lines shown to the agent)
```
14:53:30 [portal] Round 3.5 finished: we were 4 of 20 with 14.90 (±0.55); 1st 2 Curry 15.05 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 59,112 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:54:00 [clock] Test the chosen bot under upload-test conditions (no time bank).
14:54:05 [portal] Round 3 finished: we were 11 of 20 with 12.61 (±0.28); 1st Fold Equity 14.23 · played by v12 · data: data/rounds/09-Round-3/ · health: 0 missed of 241,870 decisions, 0 restarts
```

`inbox/research.log` (last 3 of 7 lines shown to the agent)
```
14:53:31 [portal] DATA LANDED Round 3.5 data/rounds/10-Round-3.5/ (hands-first-1000.jsonl.gz, results.json; portal_watch is running roundcard.py and fp_train.py on it now)
14:54:05 [portal] Round 3 finished: we were 11 of 20 with 12.61 (±0.28); 1st Fold Equity 14.23 · played by v12 · data: data/rounds/09-Round-3/ · health: 0 missed of 241,870 decisions, 0 restarts
14:54:06 [portal] DATA LANDED Round 3 data/rounds/09-Round-3/ (hands-first-1000.jsonl.gz, results.json; the full file follows; portal_watch is running roundcard.py and fp_train.py on it now)
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:50:10 SendMessage from RESEARCH: "Round 3 has not landed (cut-off posted at T-10): no change from new data this window. No one-change line for Round 3. F0 (L47) is one round only, z 0.8."
- 14:51:05 you told Dylan: "put v12 back now (a click)". Dylan 14:51:20: "v12 is back".
- 14:51:15 SendMessage from RESEARCH: "RECOMMENDATION round 4 (threshold): none possible yet: Round 3's result is missing, so there is no live-bot score to compare with. Before Round 3 we were 6th with 39.9."
- 14:52:10 you asked the round 4 question (see state/decisions.md). Dylan 14:52:40: "ok. whatever the rule says once the numbers are in". RESEARCH relayed Samuel 14:53:05: "same, go by the rule".
- Nothing from RESEARCH since 14:53:05. Dylan is at the laptop.
- platform: idle. No new zip this window: v12 and v13 are both on the portal.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:50:10 you told BUILDER and Samuel: Round 3 has not landed; no change from new data this window.
- 14:51:15 you sent BUILDER: "RECOMMENDATION round 4 (threshold): none possible yet: Round 3's result is missing."
- 14:53:00 Samuel: "same, go by the rule" (you relayed it at 14:53:05).
- 14:53:40 tester (asked for the edge): "Round 3.5 is in but I have no Round 3 score for v12 and no yardsticks file. I can give the edge about 90 seconds after Round 3's results and the yardsticks file exist; with medians only, about 40 seconds after Round 3's results."
- Round 3's results.json (just landed): field median 12.50; avalon 12.61.
- Samuel is at his laptop.
```

#### S04: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:54 Both numbers are in. No `yardsticks.json`, so field median: v13 14.90 − 12.45 = +2.45; v12 12.61 − about 12.5 = +0.1. Edge +2.3, SE 0.75-1.0, z 2.3-3; bar 0.5 (we're 8th). Message RESEARCH, `say.py --record` it. `platform`, background, 2 minutes: check `releases/v13.zip`'s sha, re-run the no-time-bank upload test beside `check_or_fold`.
- 14:55 Update round 4 in `state/decisions.md` (evidence, rule's answer v13 "unverified", both humans' conditional words now hold). `python3 scripts/live.py v13 "round 4: rule's answer, edge +2.3 vs field median, unverified"`. Tell Dylan. Append a `proposed` LEDGER line.
- 14:56 `state/status.md` must show v13.zip active, MATCHES. `platform` reports a failure: `live.py v12`, one click back.
- 14:57 Status again. Only a reproduced counter-number from RESEARCH restores v12. Record the outcome; update `notes/PLAN-builder.md`.
- 14:58-15:00 Draft "Round 5: which bot?" (last-rounds bar, z ≥ 0); confirm "Round 4 started: playing v13"; sync with RESEARCH, naming the missed T-10 cut-off's cause.

Outcome I expect: v13 is active on the portal and declared in `state/live.json` when scored round 4 starts at 15:00.

##### 2. What I say
Dylan: "Round 4 plays v13: click v13.zip active in the portal's uploads list now (a click, no upload), active by 14:57. v13's practice 14.90 was 2.45 above mid-field; v12's round 3, 12.61, was about 0.1 above. That +2.3 is over twice the noise; in 8th the rule needs half. You and Samuel said go by the rule: this is it. Caveat: my own sum, RESEARCH hasn't confirmed; a real counter-number from them before 14:57 means one click back to v12."

RESEARCH: "Round 4: rule's answer is v13; declared 14:55, Dylan activates. Edge by field median (no analysis/Round-3.5/fp/yardsticks.json): v13 +2.45 (14.90, median 12.45); v12 +0.1 (12.61, Round 3 median assumed 12.5: check data/rounds/09-Round-3/results.json); edge +2.3, SE 0.75-1.0, z 2.3-3, bar 0.5. Send tester's edge now: only a reproduced counter-number under the bar by 14:57 returns v12."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "outside the top 3 ... z ≥ 0.5". Stated.
- Same: "With fewer than 4 yardsticks, use scores minus the field median, and say so." Stated; applying it to a missing file is inferred.
- BUILDER.md "Asking the humans": "A conditional answer is recorded when its condition holds." Stated.
- §3 worked example: "re-run of the edge isn't done. → Play the challenger, labelled 'unverified'". Stated.
- Conflict: cut-off T-10, "No change from new data; live bot plus already-validated changes", and Uploads, "When in doubt, the live bot stays active", against §3, "the rule's answer plays, not 'no change'". I followed the last: T-10's fallback covers fixes built from Round 3's data (inferred); v13 was already tested and uploaded; the edge clears the bar fourfold.

##### 4. What I lacked
- Round 3's field median (no card, no `data/`): guessed 12.5 (100 points over 8 seats); v13 fails only below 10.7.
- Who computes the edge when RESEARCH is silent (guessed: me); a median-based edge's SE (guessed).
- Whether T-6 re-tests an unchanged tested zip (guessed: yes).
- `notes/PLAN-builder.md` (challenger status).
- Opened: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; scenario files; PLAN.md; scripts/README.md; greps of LESSONS.md, platform.md, tester.md, timeline.json.
- Longest: whether late Round 3 data forces the live bot (T-10 row against PLAN §5 T9, "no practice result by T-6").

#### S04: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:54 Both numbers are in. No yardsticks file, so medians: edge = (14.90 − 12.45) − (12.61 − 12.50) = +2.34; SE √(0.7² + 0.28²) = 0.75; z 3.1 (2.3 at SE 1.0). We are 8th, round 4 of 6: bar z ≥ 0.5. Send BUILDER the final recommendation, log it (`say.py --record`), tell Samuel. Ask `tester` for its medians edge (40 s, `rig/out/Round-3.5-edge.md`), then the yardstick version.
- 14:55 BUILDER's T-5: expect "LIVE BOT is now v13". Tester's number lands; LEDGER line.
- 14:56 Only a reproduced z < 0.5 reverses it, by 14:56:30 (a click back).
- 14:57 T-3: `state/status.md` must show v13.zip (9ab27d10e4c3…) active, matching `live.json`; else an urgent line to BUILDER and Samuel. Update `notes/PLAN-research.md`. Then one background message: Round 3's loop, labelled LATE (`scout`, `analyst` lenses, `tester`), and Round 3.5's analysis, for round 5.
- 14:58-14:59 Nothing changes.
- 15:00-15:04 Confirm what played. T-20 sync; step back (our base went 13.50, 13.20, 12.61).

Outcome I expect: v13 is active when scored round 4 starts at 15:00.

##### 2. What I say
Samuel: "The rule now says v13 for round 4. v13 scored 14.90 in practice (field middle 12.45); v12 scored 12.61 in round 3 (middle 12.50). That is +2.3 a table, three times the noise; in 8th we need half. It's the rough version (against the field's middle); the tester is re-running it. v13 is tested, heads-up included, and on the portal: one click for Dylan. Nothing for you to do; say 'keep v12' before 14:57 if you disagree."

BUILDER: "RECOMMENDATION round 4 (FINAL, replaces 14:51): play v13, releases/v13.zip, sha256 9ab27d10e4c3. Round 3.5: v13 14.90 ±0.55, median 12.45. Round 3: v12 12.61 ±0.28, median 12.50. Edge by medians (no yardsticks file) +2.34, SE 0.75, z 3.1; it needed 12.94. We're 8th: bar z ≥ 0.5. Verdict L51 with heads-up, upload test 5/5, already uploaded: a click. Unverified; tester's re-run lands 14:55; I message only if it reproduces z < 0.5. Both humans' condition ('once the numbers are in') now holds."

##### 3. The rule that decides
- DECISION_RULES §3, Which bot plays: "With fewer than 4 yardsticks, use scores minus the field median, and say so"; "outside the top 3 … z ≥ **0.5**". Stated.
- §3: "If nobody answers in time, the rule's answer plays, not 'no change'." LESSONS: "A conditional answer is recorded when its condition holds". Stated.
- §4: "If `tester` runs out of time re-running a number, say so and decide". Stated.
- The other way: RESEARCH.md, T-9: "With no practice result by T-6, the rule's answer is the live bot"; T-10 cut-off: "No change from new data"; Uploads: "When in doubt, the live bot stays active." I followed the first group (inferred): the practice landed before T-6; the T-10 fallback covers changes to the live bot; z 3 is not doubt.

##### 4. What I lacked
- No rule for the live bot's scored result landing after T-10 (here 5 s after T-6); I guessed T-6 concerns the practice result only.
- `data/rounds/` is absent; I trusted the portal lines.
- Guesses: SE 0.75 ("more with 20 teams" has no figure); no best-of-2 discount (z stays 2.5); Dylan clicks in time.
- Opened: brief, CLAUDE.md, RESEARCH.md, DECISION_RULES.md, the permitted scenario files, PLAN.md, scripts/README.md, timeline.json, challenger_bar.md, agents/tester.md, BUILDER.md, LESSONS.md.
- Longest: whether late data cancels the challenger (T-6 sentence against T-10 row).


### S05. Hand data that will not download

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:31:50 on Sunday. Scored round 3 starts at 14:40:00.

`state/status.md`
```
# Portal status (written 14:31:46 by scripts/portal_watch.py)

Last poll 14:31:46: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v9.zip** (sha256 7c1e09a44b2d…), uploaded 13:57
Declared live bot (state/live.json): **v9** (round 2: live bot unchanged) — MATCHES the portal
Next on the clock: Scored round 3 at 14:40

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 1.5 | Round 1.5 | 14:10 | finished · data saved | v10 | 12/20 · 12.20 ±0.56 | 2 Curry 15.02 |
| Round 2 | Round 2 | 14:20 | finished · hands NOT downloaded yet | v9 | 7/20 · 13.20 ±0.28 | Fold Equity 15.20 |
| Round 2.5 | Round 2.5 | 14:30 | **running** | v11 |  |  |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 46.20 |
| 2 | 2 Curry | 44.90 |
| 3 | River Rats | 42.30 |
| 4 | Tilt Shift | 41.80 |
| 5 | Check Mates | 40.60 |
| 6 | **avalon** | 39.90 |
| 7 | Pot Committed | 39.50 |
| 8 | Gutshot | 38.80 |
| 9 | Limp Mode | 38.10 |
| 10 | Kicker Trouble | 37.90 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:27 | v11.zip | ready |  |
| 14:07 | v10.zip | ready |  |
| 13:57 | v9.zip | ready |  |

## Warnings

- hand data for Round 2 not downloaded since 14:26 (last error: HTTP 403 on /teams/…/tournaments/…/hands?tables=1000); fix: python3 scripts/portal_watch.py --set-hands-url '<link>'
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:31:45)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:31: minute 91 · stage **Round 2.5** · next: scored round 3 at 14:40 (T-8)
Live bot (state/live.json): **v9** · the portal runs: v9.zip
| **Scored round 3** | 14:40 | **next** |
Next steps: 14:32 (T-8 of round 3); 14:34 (T-6 of round 3); 14:35 (T-5 of round 3)
```

`state/live.json`: bot **v9**, why "round 2: live bot unchanged", declared 14:14:40, previous none.

`state/decisions.md`
```
(rounds 1 and 2: not shown)

## Round 3: which bot? (DRAFT, started 14:20:30 by BUILDER; not asked yet)
- Options: v9 (live) or v11 (challenger).
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L33 | 14:12 | analyst | one-change Round 1 (F0): fold less to river raises on paired boards | +0.3 ± 0.3 (z 1.0) | 402 spots | replay on Round 1 hands | analysis/Round-1/leaks.md | validated (tester 14:16); one round only
L38 | 14:21 | tester | verdict v11 (sha256 e03b5f19c7aa): correct; vs live v9 +0.1 ± 0.4; heads-up +0.3 ± 0.4 | +0.1 ± 0.4 | 2,000 tables + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v11-verdict.md | validated
```

`releases/VERSIONS.md` (the lines shown)
```
v9 | 3a1f7c2 | 7c1e09a44b2d… | style A + theory refits from practice 3 | 0 failed of 48,112; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 4.8) | live (rounds 1-2) | correct; vs v7 +0.3 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor check_or_fold 9.8 in the same field (L21)
v11 | 8d02e5b | e03b5f19c7aa… | design D matured: twist-first, limp-or-shove under 15bb | 0 failed of 51,007; p99 0.24 ms; upload test 5/5 (check_or_fold 5/5, load 5.5) | challenger (round 3 window) | correct; vs live v9 +0.1 ± 0.4 (paired, 2,000 tables); heads-up +0.3 ± 0.4; floor check_or_fold 9.9 (L38)
```

`analysis/Round-2/README.txt`
```
(no card.md, no field_trend.md, no fp/ folder: the card and the fingerprint run need the hand file.)
```

`data/rounds/07-Round-2/README.txt`
```
(folder holds results.json and round.json only; no hands-*.jsonl.gz. results.json has every team's average points for Round 2: field median 12.55; avalon 13.20. Round 1 and Round 1.5 have their hand files.)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 6 lines shown to the agent)
```
14:30:02 [portal] Round 2.5 started at 14:30:02: playing v11 (the declared live bot is v9).
14:31:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:31:42 [portal] URGENT: the hand data for Round 2 hasn't downloaded for 5 minutes (last error: HTTP 403 on /teams/…/tournaments/…/hands?tables=1000). Copy the hand download link from the portal's round page and paste the link: python3 scripts/portal_watch.py --set-hands-url '<link>' (no restart needed).
```

`inbox/research.log` (last 3 of 5 lines shown to the agent)
```
14:30:05 [clock] [CUT-OFF] scored round 3 (14:40): 'the previous scored round's results and hand data have landed (data/rounds/)' didn't happen by T-10 (14:30). The pre-registered fallback plays: no new data this window. The live bot plays with only changes already supported by earlier rounds (persistent leaks, validated LEDGER lines); analyst works from pooled earlier rounds; nothing waits for this data. When it lands it feeds the next window; this is not a request to hurry.
14:31:00 [clock] Send BUILDER the recommendation for scored round 3 now (it asks the humans at T-8): RECOMMENDATION round 3: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
14:31:42 [portal] URGENT: the hand data for Round 2 hasn't downloaded for 5 minutes (last error: HTTP 403 on /teams/…/tournaments/…/hands?tables=1000). Copy the hand download link from the portal's round page and paste the link: python3 scripts/portal_watch.py --set-hands-url '<link>' (no restart needed).
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:28:20 you told Dylan: "activate v11.zip now (it's uploaded) for the 14:30 practice". Dylan 14:28:40: "done".
- 14:31:05 you told Dylan: "put v9 back now (a click)". Dylan has not replied; state/status.md (14:31:46) shows v9.zip active.
- Nothing from RESEARCH since the T-20 sync at 14:20:40.
- Dylan is at the laptop. stylist is building F0 (L33) since 14:26 in candidates/F0/, not reported yet.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:26:45 you saw Round 2's result line with "hand data not downloadable yet (retrying)". You spawned nothing on Round 2 (no DATA LANDED line arrived).
- 14:27 to 14:31: scout, analyst and tester are idle on Round 2; tester finished v11's verdict at 14:21 (L38).
- Samuel is at his laptop; his last message, 14:22: "round 2 looked ok. tell me what you need".
- You have sent BUILDER nothing since the T-20 sync at 14:20:40.
```

#### S05: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:32 Write the round-3 entry in `state/decisions.md`; ask Dylan; message RESEARCH twice (`say.py --record`).
- 14:33 Practice result due: read `state/status.md`. If Dylan pasted the link, run `portal_watch.py --set-hands-url`, check the warning clears. F0 isn't with `platform` at T-8: out of round 3, stylist not hurried.
- 14:34 No practice result or RESEARCH answer: rule's answer is v9. Both zips are tested and uploaded.
- 14:35 No clear answer: apply the rule's answer (`live.py v11` only if it cleared), tell Dylan, record it.
- 14:36-14:37 Name the click once (or "nothing to click"); confirm `state/status.md` shows the chosen bot active.
- 14:38-14:39 Write `notes/PLAN-builder.md` (absent); make sure a round-4 challenger is building.
- 14:40 Read "Round 3 started: playing vN"; T-20 sync reports both misses.

Outcome I expect: v9 active at 14:40 (v11 only if its practice clears z ≥ 0.5 against the median); Round 2's hands link set.

##### 2. What I say
Dylan: "Which bot plays round 3 (14:40): v9 (live) or v11 (challenger)? We're 6th, 2.40 behind 3rd, so the bar is z ≥ 0.5. v9 scored 13.20 in round 2, 0.65 above the median. v11 equals v9 locally (+0.1 ± 0.4); its practice lands about 14:33 and must beat that practice's median by about 1.0 (my arithmetic until RESEARCH's number; median, not yardstick teams: Round 2's hands haven't downloaded). v9: nothing to do. v11: one click by 14:37. Rule's answer if nobody answers by 14:35: v9, unless the practice clears the bar, then v11. Only you can do this: copy the hand download link from the portal's Round 2 page, paste it here; I'll set it. F0 goes into round 4."

RESEARCH (1): "Round 3 recommendation overdue: send the practice score v11 needs now, the final answer when Round 2.5 lands. Round 2 hands are 403, so no yardsticks: use scores minus field median and say so (v9 13.20, median 12.55, data/rounds/07-Round-2/results.json). Nothing by 14:34 = v9."

RESEARCH (2): "Round 2 hands link: Dylan pastes it to me, I run --set-hands-url. Samuel needn't; if he already did, say so."

##### 3. The rule that decides
- DECISION_RULES §3, stated: "outside the top 3 ... z ≥ **0.5**"; "With fewer than 4 yardsticks, use scores minus the field median, and say so." Applying it to missing hands: inferred.
- PLAN §5 T9, stated: "no practice result by T-6: the rule's answer is the live bot".
- `.claude/agents/stylist.md`, stated: "a fix makes this window's T-6 release only if its tested folder reaches platform by about T-8".
- Hands link, two ways. prompts/RESEARCH.md: "ask Samuel for the hand download link ... then run ... yourself". CLAUDE.md §5: ask a human for "facts nobody else can see. Never ask them to run a command". Dylan is at the portal, so I followed §5 and told RESEARCH: inferred.

##### 4. What I lacked
- RESEARCH's threshold; `notes/PLAN-builder.md` (is a round-4 challenger running?); what v10 was (pooling).
- Guesses: the 1.0 threshold (SE √(0.7²+0.28²) ≈ 0.75, edge ≥ 0.38, plus 0.65); Round 2.5's scores land despite the 403; BUILDER may run `--set-hands-url`; an unchanged zip needs no T-6 re-test.
- Files, in order: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; PLAN.md; scripts/README.md; scenario files; START.md; LESSONS.md; RESEARCH.md, portal_watch.py, timeline.json (parts); stylist.md.
- Longest to find: who sets the hands link (RESEARCH.md, START.md only).

#### S05: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:32 Ask Samuel for the Round 2 hand link. Send BUILDER the round-3 threshold (LATE) and one line that I own the link. One background spawn: `tester` (the median-method edge, re-checking my arithmetic), `analyst` (pooled Round 1 + 1.5 hands: is L33 persistent).
- 14:33 Round 2.5's result lands: z = ((v11 − median) − 0.65) / 0.75; final answer to BUILDER and Samuel. Link pasted: I run `portal_watch.py --set-hands-url`.
- 14:34 No practice result: final answer v9.
- 14:35 Relay Samuel's exact words, if any.
- On "DATA LANDED Round 2": the full loop in one spawn, for round 4.
- 14:40 T-20 sync: report the missed cut-off (cause: HTTP 403).

Outcome I expect: v9 active at 14:40 (about 70%); v11, a click, only if it beats the practice median by 1.05+. Round 2's hands feed round 4.

##### 2. What I say
Samuel: "One thing: the Round 2 hand download link. Copy it from the Download button on the portal's Round 2 page and paste it here; I'll do the rest. The automatic download failed (403), so round 3 gets no new fixes from Round 2; it feeds round 4. We're 6th, 2.4 behind 3rd. v11 is in the practice now: it plays round 3 only if it scores about 1.05 above that round's median (roughly 13.6), otherwise v9 stays. Dylan's session asks 'which bot?' now; answer there or here by 14:35, or the rule's answer plays."

BUILDER (1): "RECOMMENDATION round 3 (LATE; threshold): 6th, 2.40 behind 3rd, bar z ≥ 0.5. No yardsticks (Round 2 hands 403), so scores minus field median: v9 Round 2 13.20 − 12.55 = +0.65; SE 0.75. releases/v11.zip (L38 validated, heads-up included) if Round 2.5 score ≥ median + 1.05, else releases/v9.zip. Unverified arithmetic; tester re-running. No result by 14:34: v9. No new-data change; L33 clears z ≥ 1 but I know of no released zip with it."

BUILDER (2): "Round 2 hands: I'm getting the link from Samuel and setting it; nothing for Dylan."

##### 3. The rule that decides
- `prompts/RESEARCH.md`, "The clock": "ask Samuel for the hand download link … then run … yourself" (stated). `CLAUDE.md` §5 points the other way: "Never start `portal_watch.py` or `clock.py run` yourself". I followed RESEARCH.md: the flag's help says "store a copied hand-download link and exit", so it isn't the daemon (inferred).
- `DECISION_RULES.md` §3, cut-offs, T-10: "No change from new data; live bot plus already-validated changes" (stated).
- §3, "Which bot plays": "With fewer than 4 yardsticks, use scores minus the field median, and say so"; "z ≥ **0.5**" (stated). Missing hands meaning zero yardsticks: inferred from `tester.md`.
- `prompts/RESEARCH.md`, T-9: "With no practice result by T-6, the rule's answer is the live bot" (stated).

##### 4. What I lacked
Lacked: Round 2.5's median; `notes/PLAN-research.md` (absent, so no agent or BUILDER session ids); whether BUILDER built L33's fix; whether Round 2.5's hands will also 403.

Guesses: Samuel can open the portal; edge SE 0.75 (0.7 and 0.28 combined); practice median near 12.55; v11's true edge near zero (hence 70%).

Opened: the brief; `CLAUDE.md`, `prompts/RESEARCH.md`, `DECISION_RULES.md`, `PLAN.md`, `scripts/README.md`; every permitted scenario file; `START.md`, `LESSONS.md`; searched `tester.md`, `scout.md`, `analyst.md`, `portal_watch.py`, `timeline.json`.

Longest: that yardsticks need hand data (`tester.md`, "T-9 to T-8").


### S06. An upload rejected at T-4

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:56:10 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:56:07 by scripts/portal_watch.py)

Last poll 14:56:07: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v14** (round 4: v12 + F1 + F2 (Dylan and Samuel chose it)) — does NOT match the portal (fine during a practice round; must match by T-3 of a scored round)
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 5/20 · 13.50 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 8/20 · 13.60 ±0.56 | 2 Curry 15.05 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | 2 Curry | 86.00 |
| 3 | Tilt Shift | 82.40 |
| 4 | River Rats | 81.70 |
| 5 | **avalon** | 80.40 |
| 6 | Check Mates | 80.10 |
| 7 | Gutshot | 78.80 |
| 8 | Pot Committed | 77.90 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:55 | v14.zip | rejected | archive contains a directory that is not allowed: __pycache__/ (3 files) |
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- the portal runs v12.zip, the declared live bot is v14
- rejected upload: v14.zip (archive contains a directory that is not allowed: __pycache__/ (3 files))
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:56:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:56: minute 116 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-4)
Live bot (state/live.json): **v14** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v14**, why "round 4: v12 + F1 + F2 (Dylan and Samuel chose it)", declared 14:54:30, previous v12.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? v12 (live), v13 (challenger) or v14 (v12 + F1 + F2)
- Asked 14:52:15 by BUILDER. Deadline 14:55:00.
- Evidence: v13's field-adjusted edge +0.30 ± 0.80 (z 0.38); we are 5th (bar 0.5): the challenger does not clear it. F1 (z 1.3, persistent) and F2 (z 1.1) are validated; v14 has tester's verdict with a heads-up run (L58).
- The rule's answer: v14 (the live bot with this window's changes).
- Dylan, 14:53:10: "yes v14". Samuel (relayed 14:53:30): "agree, v14".
- 14:54:30 BUILDER: live.py v14. Told Dylan: "upload releases/v14.zip and make it active by 14:57".
- Outcome: (open)
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L52 | 14:46 | analyst | one-change Round 3 (F1): call 3-bet shoves wider at 20bb or less; seen in Round 2 and Round 3 (persistent) | +0.35 ± 0.27 (z 1.3) | 902 spots over two rounds | replay on Round 2 + Round 3 hands | analysis/Round-3/leaks.md | validated (tester 14:49, recount +0.33)
L55 | 14:47 | analyst | one-change Round 3 (F2): stop min-raise-folding against Gutshot seats (they 3-bet 31% of min-raises) | +0.30 ± 0.27 (z 1.1) | 644 spots | replay on Round 3 hands | analysis/Round-3/opponent_gutshot.md | validated (tester 14:50, recount +0.29)
L58 | 14:51 | tester | verdict v14 (sha256 c58f3e7712d0): correct; vs live v12 +0.5 ± 0.3; heads-up +0.2 ± 0.4; F1 fired 412, F2 fired 1,038; F1's call rate 38% vs target 40% | +0.5 ± 0.3 | 2,000 tables + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v14-verdict.md | validated
L59 | 14:52 | tester | field-adjusted edge v13 (Round 3.5) vs v12 (Round 3), 7 yardsticks | +0.30 ± 0.80 (z 0.38) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-3.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
v14 | 2c7be80 | c58f3e7712d0… | v12 + F1 (call 3-bet shoves wider at 20bb or less) + F2 (no min-raise-fold vs Gutshot seats), each behind a setting, fired 412 and 1,038 times in 2,000 tables | 0 failed of 50,904; p99 0.21 ms; upload test 5/5 (check_or_fold 5/5, load 5.7) | live candidate (round 4) | correct; vs live v12 +0.5 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.8 (L58)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 4 lines shown to the agent)
```
14:54:30 [builder] LIVE BOT is now v14 (round 4: v12 + F1 + F2 (Dylan and Samuel chose it)) — Dylan: make it active on the portal (upload releases/v14.zip if it isn't there).
14:55:00 [clock] No clear human answer by now: the rule's answer plays (the challenger if it qualified, else the live bot). live.py it if it changes the live bot, and say so in one line.
14:56:06 [portal] URGENT: upload v14.zip was REJECTED by the portal: archive contains a directory that is not allowed: __pycache__/ (3 files). It was the declared live bot (v14); the previous bot stays active on the portal (v12.zip). BUILDER: have platform fix it, or put v12 back: python3 scripts/live.py v12 "v14 rejected".
```

`inbox/research.log` (last 2 of 2 lines shown to the agent)
```
14:54:30 [builder] LIVE BOT is now v14 (round 4: v12 + F1 + F2 (Dylan and Samuel chose it)) — Dylan: make it active on the portal (upload releases/v14.zip if it isn't there).
14:56:06 [portal] URGENT: upload v14.zip was REJECTED by the portal: archive contains a directory that is not allowed: __pycache__/ (3 files). It was the declared live bot (v14); the previous bot stays active on the portal (v12.zip). BUILDER: have platform fix it, or put v12 back: python3 scripts/live.py v12 "v14 rejected".
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:53:45 platform reported: "v14 passed the no-time-bank upload test again, 5/5, load 5.9, check_or_fold 5/5 in the same minute".
- 14:54:35 you told Dylan: "upload releases/v14.zip and make it active by 14:57".
- 14:55:55 Dylan: "uploaded v14 at 14:55:50".
- 14:56:08 Dylan: "portal says rejected?? pycache something. what now"
- platform is idle. The last upload before v14 was v13 at 14:47:55.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:52:05 you sent BUILDER the final recommendation for round 4: v13's edge +0.30 ± 0.80 (z 0.38) is under the bar for 5th; the rule's answer is releases/v14.zip (v12 + F1 + F2, verdict L58).
- 14:53:25 Samuel: "agree, v14" (relayed to BUILDER 14:53:30).
- 14:56:09 Samuel: "what does rejected mean for round 4? are we ok?"
- tester is idle; analyst x3 are queued for after T-3.
```

#### S06: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:56 Answer Dylan (below). Run `python3 scripts/live.py v12 "v14 rejected"`. Continue `platform` in the background: find why v14.zip held `__pycache__/`, make the packer fail loudly on unexpected files, repack commit 2c7be80 as v15 with checks 1-2 and the upload test on the exact zip, check round 5's challenger zip too; report by 15:02. Message RESEARCH (`say.py --record`). Record the outcome and cause in `state/decisions.md`.
- 14:57 T-3: read `state/status.md`: v12.zip active, sha 41d9a6c2f0b8 as in VERSIONS, matching live.json. Tell Dylan "confirmed". Update `notes/PLAN-builder.md`.
- 15:00 Confirm in status.md that round 4 started with v12. T-20 sync with RESEARCH, the miss included. Draft round 5's question (last two rounds: bar z ≥ 0).
- 15:02 platform's report: I check the zip's file list and VERSIONS line; fresh `bughunter`; "RELEASED v15 <sha256>" to RESEARCH. Ready by 15:03: Dylan uploads v15 without activating it (the challenger's 15:08 upload keeps its 5-minute gap); otherwise v15 waits until 15:13.

Outcome I expect: v12 is active when round 4 starts; v14 does not play; v15 (same code, clean zip) is released by about 15:02 for round 5.

##### 2. What I say
To Dylan: "Upload nothing, click nothing: v12 is still active (portal checked 14:56:07) and plays round 4. The portal refused v14.zip because the zip held a __pycache__ folder: a packing fault, not the bot. No time for a fixed file: a repacked zip needs its tests again, and the 5-minute upload gap from 14:55:50 may run to 15:00:50. Cost: about half a point per table this round (+0.5 ± 0.3 locally). platform is repacking the same code as v15, due 15:02; I'll name the file then."

To RESEARCH: "v14.zip REJECTED by the portal at 14:55 (__pycache__/ in the archive). Round 4 plays v12 (active, sha 41d9a6c2f0b8; re-declared 14:56): past T-4, cooldown may run to 15:00:50. Tell Samuel. platform repacks commit 2c7be80 as v15 by 15:02; RELEASED v15 <sha256> follows: it needs a tester verdict with a heads-up run for round 5."

##### 3. The rule that decides
- DECISION_RULES §3, cut-offs, T-4 (stated): "The live bot (active since the practice round) plays; nothing is uploaded".
- LESSONS, "Decisions and uploads" (stated): "After a rejection the previous bot stays active: BUILDER re-declares it, and Dylan uploads nothing until `platform` has a fixed, tested file."
- notes/format.md (stated): "Uploads: one every 5 minutes". That a rejection starts the gap, and that v15 needs its own verdict: inferred.
- Pointing the other way: START.md, "BUILDER has platform fix it and gives you a new file"; DECISION_RULES §2.2, "A missed deadline is a failure to report and fix, not a safe outcome." I followed the cut-off for round 4, the fix for round 5: at T-3:50 no new zip can be tested, and "deadlines cut scope, never care".

##### 4. What I lacked
- Whether a rejected upload starts the cooldown; whether an upload activates itself; the portal's allowed-file list; why the local upload test passed this zip.
- Absent: `notes/PLAN-builder.md` (agent ids), round 5's challenger.
- Guesses: platform needs 5 minutes; a verdict doesn't carry to a byte-different zip.
- Opened, in order: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; scenario NOW.md, terminal-builder.md, builder.log, state/ (4 files), VERSIONS.md, LEDGER.md, format.md; PLAN.md; scripts/README.md; LESSONS.md; agents/platform.md; START.md; portal_watch.py, live.py; timeline.json.
- Longest to find: the LESSONS line on rejected uploads.

#### S06: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:56 Answer Samuel. SendMessage BUILDER the revised recommendation; log it (`say.py --record builder`).
- 14:57 (T-3) Re-read `state/status.md` and `state/live.json`: portal v12, declared v12. If live.json still says v14, one more line to BUILDER. LEDGER line: v14 rejected, v12 plays round 4. Create `notes/PLAN-research.md` (absent). Start the queued analyst x3 on Round 3.5.
- 14:58 Idle tester (5 minutes, read-only): a zip-listing check in `rig/` that fails on any directory or `.pyc`, run on v11-v14.
- 15:00 Confirm Round 4 was played by v12; one line to Samuel. T-20 sync to BUILDER: rounds 5-6 are the last two, so the bar becomes z ≥ 0.
- 15:01-15:06 On "RELEASED v15": a fresh tester (listing check, paired vs v12, heads-up).

Outcome I expect: v12 (`releases/v12.zip`, 41d9a6c2f0b8…) is active when scored round 4 starts at 15:00; live.json reads v12; a re-packed v14 is in test for round 5.

##### 2. What I say
Samuel: "Rejected means the portal refused the v14 file (a leftover __pycache__ folder inside), so v14 won't play round 4. We're OK: v12, the tested bot that scored 13.50 in round 3, is still active and plays at 15:00. A fixed file can't make it: one upload per 5 minutes, the rejected one went at 14:55, and the deadline is 14:57. Cost: no F1/F2 this round, about +0.5 ± 0.3 a table in local tests, so up to roughly 2 points of total at weight 4; not sure. v13 is one click away but its edge (z 0.38) is under our 0.5 bar. I'm getting the re-pack tested for round 5. Nothing for you to do."

BUILDER: "RECOMMENDATION round 4, revised 14:56: v14 can't play (rejected 14:55, __pycache__/; cooldown 300 s → next upload 15:00; T-4 passed). Rule's answer: releases/v12.zip, already active (state/status.md 14:56:07, verdict L44): live.py v12 "v14 rejected"; Dylan uploads nothing before 15:00. Not v13 (z 0.38 < 0.5, L59). Re-pack v14 as v15, send RELEASED v15 <sha256>: fresh tester at once; uploaded by 15:03 it clears the cooldown before the 15:08 challenger upload."

##### 3. The rule that decides
- LESSONS.md "Decisions and uploads" (stated): "After a rejection the previous bot stays active: BUILDER re-declares it, and Dylan uploads nothing until `platform` has a fixed, tested file."
- DECISION_RULES §3 cut-offs, T-4 (stated): "The live bot (active since the practice round) plays; nothing is uploaded".
- notes/format.md (stated): "Uploads: one every 5 minutes"; next slot 15:00 (inferred).
- DECISION_RULES §3 (stated): outside the top 3, "z ≥ **0.5**": v13 doesn't replace v12.
- Conflict: PLAN §3, "a failure to fix, not a safe outcome", pushes toward rushing v14; I followed hard rule 2, "Only upload a zip that has been through that test": hard rules never bend, and the cooldown forbids it anyway.

##### 4. What I lacked
- Guesses: a rejected upload starts the cooldown; the T-4 fallback's "live bot" means v12 although live.json says v14; a same-code re-pack needs a new verdict (new sha256); the name "v15".
- No passage says what RESEARCH does on a rejection; inferred.
- `notes/PLAN-research.md`, `rig/out/`, `analysis/`, `data/` absent: verdict and edge files unread; Monitor assumed armed.
- Opened: brief; CLAUDE.md; RESEARCH.md; DECISION_RULES.md; PLAN.md; scripts/README.md; every permitted scenario file; then (grep) START.md, LESSONS.md, portal_watch.py, BUILDER.md, agents/tester.md, platform.md.
- Longest to find: the LESSONS rejection line (grep only).


### S07. The leaderboard is held

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:52:10 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:52:06 by scripts/portal_watch.py)

Last poll 14:52:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v12** (round 3: v9 + two fixes) — MATCHES the portal
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 9/20 · 12.70 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 7/20 · 13.11 ±0.56 | 2 Curry 15.05 |

## Standings (top 10) — HELD / may be stale

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 46.20 |
| 2 | 2 Curry | 44.90 |
| 3 | **avalon** | 42.90 |
| 4 | River Rats | 42.20 |
| 5 | Tilt Shift | 41.80 |
| 6 | Check Mates | 40.60 |
| 7 | Pot Committed | 39.50 |
| 8 | Gutshot | 38.80 |
| 9 | Limp Mode | 38.10 |
| 10 | Kicker Trouble | 37.90 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- standings held or unreadable
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:52:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:52: minute 112 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-8)
Live bot (state/live.json): **v12** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:54 (T-6 of round 4); 14:55 (T-5 of round 4); 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v12**, why "round 3: v9 + two fixes", declared 14:34:50, previous v9.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? (DRAFT, started 14:40:20 by BUILDER; not asked yet)
- Options: v12 (live) or v13 (challenger). No validated one-change line for Round 3.
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L51 | 14:42 | tester | verdict v13 (sha256 9ab27d10e4c3): correct; vs live v12 +0.0 ± 0.4; heads-up +0.2 ± 0.4 | +0.0 ± 0.4 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v13-verdict.md | validated
L56 | 14:49 | tester | standings after Round 3 computed from each round's results.json x weights (1, 2, 3), because the portal's standings are held: Fold Equity 88.9, 2 Curry 86.0, avalon 81.0, River Rats 80.7, Tilt Shift 80.4, Check Mates 80.1, Gutshot 78.8. We are 3rd by 0.3 over 4th and 0.9 over 6th. Each total carries about ± 1.0 from the rounds' own margins | n/a | 3 rounds | sum of weight x average points, all 20 teams | rig/out/standings-computed.md | proposed
L59 | 14:52 | tester | field-adjusted edge v13 (Round 3.5) vs v12 (Round 3), 8 yardsticks | +0.56 ± 0.80 (z 0.70) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-3.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-3.5-edge.md`
```
# Field-adjusted edge, round 4 window (tester, written 14:52:00)

Yardstick teams (analysis/Round-3.5/fp/yardsticks.json): 8.

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v13, Round 3.5 (practice, 1,000 tables) | 13.11 | 12.40 | +0.71 |
| Live v12, Round 3 (scored, 4,000 tables) | 12.70 | 12.55 | +0.15 |

Edge = +0.71 − 0.15 = **+0.56**; SE of the edge 0.80; **z = 0.70**. Not re-run by a second method.
```

`inbox/builder.log` (last 3 of 5 lines shown to the agent)
```
14:51:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:51:50 [portal] Round 3.5 finished: we were 7 of 20 with 13.11 (±0.56); 1st 2 Curry 15.05 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:52:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 4 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:55).
```

`inbox/research.log` (last 3 of 5 lines shown to the agent)
```
14:51:00 [clock] Send BUILDER the recommendation for scored round 4 now (it asks the humans at T-8): RECOMMENDATION round 4: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
14:51:50 [portal] Round 3.5 finished: we were 7 of 20 with 13.11 (±0.56); 1st 2 Curry 15.05 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:52:00 [clock] Decision time for scored round 4 (15:00): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:51:05 you told Dylan: "put v12 back now (a click)". Dylan 14:51:20: "v12 is back".
- 14:51:12 SendMessage from RESEARCH: "RECOMMENDATION round 4 (threshold): the portal's standings have been held since 14:25:30 (they showed us 3rd after Round 2: 42.9, 4th River Rats 42.2). tester's computed standings after Round 3 are in L56 (rig/out/standings-computed.md). 8 yardstick teams; v12 was +0.15 over them in Round 3. v13 has tester's verdict with a heads-up run (L51). The final answer follows when Round 3.5 lands."
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:49:30 tester reported L56 (computed standings after Round 3).
- 14:51:12 you sent BUILDER the threshold message for round 4 (standings held; L56; 8 yardsticks; v12 +0.15 over them).
- 14:52:02 tester reported: "edge written to rig/out/Round-3.5-edge.md and L59: +0.56 ± 0.80, z 0.70".
- Samuel is at his laptop; his last message, 14:47: "are we still third? the board hasn't moved since round 2".
```

#### S07: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:52 Complete the Round 4 entry in `state/decisions.md`. Ask Dylan; message RESEARCH; `say.py --record`. In the background, `platform` re-runs the no-time-bank upload test on `releases/v13.zip` beside `check_or_fold`, due 14:54.
- 14:54 Check platform's output. A failure or "machine loaded": v12 (already active) plays.
- 14:55 Record a clear human answer in their words. None, or the humans disagree: the rule's answer. If v13: `live.py v13 "round 4: z 0.70 vs bar 0.5"`, then "Dylan: click v13.zip (uploaded 14:47) active now".
- 14:57 Confirm in `state/status.md`: active v13.zip, sha 9ab27d10e4c3.
- 15:00 T-20 sync with RESEARCH: rounds 5-6 are the last two, bar z ≥ 0.

Outcome I expect: v13 is active when round 4 starts (v12 if a human says so or v13 fails the retest).

##### 2. What I say
To Dylan: "Decision by 14:55: which bot plays round 4 (weight 4 of 21), v12 (live) or v13 (challenger)? v13 scored 13.11 in the 14:50 practice, +0.71 over the 8 teams that didn't change; v12 was +0.15 over them in round 3. Edge +0.56 ± 0.80, z 0.70, unverified. v13 has the tester's verdict (heads-up included) and is on the portal. The portal's standings are frozen; our own sums have us 3rd by 0.3 over River Rats, ± 1.0 on each total. That isn't clearly top 3, so the bar is 0.5 and the rule's answer is v13. If you count us as safely 3rd, the bar is 1.0 and v12 stays. Say 'v13' or 'v12'. No answer by 14:55: v13 plays, one click from you."

To RESEARCH: "ROUND 4 asked 14:52, deadline 14:55. L59: z 0.70. L56: 3rd by 0.3 ± 1.0, not clearly top 3, so bar 0.5: rule's answer releases/v13.zip. Send your final answer and Samuel's words by 14:55; any counter-number on L56 or L59, now."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "the standings are hidden and we weren't clearly in it: z ≥ 0.5". Stated; that 0.3 ± 1.0 is "not clearly" is inferred.
- Pointing the other way: same list, "we are in the top 3: z ≥ 1.0"; and LESSONS.md: "Standings hidden: work out our total from each round's results and weights; if that's impossible, treat us as outside the top 3". The total exists and says 3rd: read literally, v12 plays. I followed the 0.5 bar: DECISION_RULES "overrides anything older or vaguer", the lead is inside its noise, and §1 says "When a choice is close, prefer the option that learns more or gains more."
- §4: "Only a line disputed with a reproduced counter-number blocks a switch." Stated.
- §2 rule 1: "only with a `tester` verdict that includes a heads-up run." Stated; L51 meets it.
- §3: "The rule's answer plays at T-5 if no human has answered." Stated.

##### 4. What I lacked
- No number for "clearly", nor whether it means when the standings froze (3rd by 0.7) or now.
- Absent: RESEARCH's final answer, `rig/out/standings-computed.md`, `notes/PLAN-builder.md`.
- Guesses: "not clearly"; SE 0.80 as given; the T-6 retest is worth repeating; no best-of-k discount.
- Opened: brief, CLAUDE.md, BUILDER.md, DECISION_RULES.md, the permitted scenario files, PLAN.md, scripts/README.md, a bundle grep, LESSONS.md 98-110, timeline.json T6.
- Longest: the LESSONS hidden-leaderboard line, found only by grep.

#### S07: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:52 Re-check tester's numbers from status.md: edge +0.56, z 0.70; our total 14.10+2×14.40+3×12.70 = 81.0 (matches L56). v13 has its verdict with heads-up (L51), upload test 5/5, and is already on the portal. Answer Samuel; SendMessage BUILDER the final recommendation; `say.py --record builder`.
- 14:53 Continue tester (background, 2-minute limit): recount L56 from each results.json, redo L59 by scores minus field median; each marked validated or disputed.
- 14:54 Relay Samuel's answer to BUILDER in his exact words.
- 14:55 T-5: no human answer, so BUILDER applies v13. Only a reproduced counter-number putting z under 0.5 changes my recommendation (to v12, still a click).
- 14:57 T-3: confirm status.md shows v13.zip active; if not, tell Samuel and BUILDER at once. Update notes/PLAN-research.md; start the full loop on Round 3.5's download.
- 15:00 T-20 sync with BUILDER; step back; rounds 5-6 are the last two (bar z ≥ 0).

Outcome I expect: v13 is active when scored round 4 starts at 15:00 (v12 only if a human overrules or tester reproduces a counter-number).

##### 2. What I say
Samuel: "Barely, and not safely. The board is frozen at round 2; by our own count after round 3 we're 3rd on 81.0, with River Rats 80.7 and two more teams within 0.9. A 0.3 gap is inside the noise (about ±1.0), so the rule treats us as not clearly top 3 and the new bot needs z 0.5. v13 measured +0.56 ± 0.80 points per table better than v12 against 8 unchanged teams (z 0.70; one practice round, not double-checked). I recommend v13 for round 4. If you'd rather treat us as safely 3rd, the bar is 1.0 and v12 stays. Dylan's session is asking you both now: answer by 14:55, or v13 plays."

BUILDER: "RECOMMENDATION round 4: v13 (releases/v13.zip, sha256 9ab27d10e4c3…, verdict L51 incl. heads-up; already uploaded, a click). Edge vs v12 +0.56 ± 0.80, z 0.70, 8 yardsticks (rig/out/Round-3.5-edge.md, L59, unverified). Standings held; computed 81.0, 3rd by 0.3, ±1.0 each (L56, unverified): not clearly top 3, so bar z ≥ 0.5, cleared. If the humans judge us top 3, bar 1.0: v12. Tester re-runs both by 14:55."

##### 3. The rule that decides
- DECISION_RULES §3, "Which bot plays" (stated): "the standings are hidden and we weren't clearly in it: z ≥ 0.5"; "we are in the top 3: z ≥ 1.0".
- prompts/RESEARCH.md, "The T-9 recommendation" (stated): "treat us as outside the top 3 unless we clearly weren't".
- The other way: LESSONS.md, hidden leaderboard (stated): "work out our total… if that's impossible, treat us as outside the top 3". Literally: computed 3rd, bar 1.0, v12. I followed DECISION_RULES: it "overrides anything older or vaguer", and 0.3 against ±1.0 is not "clearly" (inferred).
- DECISION_RULES §4 (stated): "Only a line disputed with a reproduced counter-number blocks a switch."

##### 4. What I lacked
- No definition of "clearly" in the top 3; I guessed.
- Whether a computed total un-hides the standings.
- My 14:51:12 threshold's text (which bar it named); guessed 0.5.
- data/rounds and yardsticks.json absent: no recount; assumed results.json totals are official, tester free.
- Opened, in order: brief, CLAUDE.md, RESEARCH.md, DECISION_RULES.md, NOW.md, terminal-research.md, research.log, clock.md, status.md, live.json, decisions.md, format.md, LEDGER.md, VERSIONS.md, Round-3.5-edge.md, PLAN.md, scripts/README.md, LESSONS.md, agents/tester.md.
- Longest to find: the LESSONS.md hidden-leaderboard line (by grep).


### S08. 2nd with a lead, the challenger at z = 1.2

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:52:10 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:52:06 by scripts/portal_watch.py)

Last poll 14:52:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v12** (round 3: v9 + two fixes) — MATCHES the portal
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 2/20 · 14.07 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 1/20 · 15.10 ±0.55 | avalon 15.10 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | **avalon** | 84.61 |
| 3 | 2 Curry | 83.80 |
| 4 | Tilt Shift | 79.90 |
| 5 | River Rats | 79.40 |
| 6 | Check Mates | 78.30 |
| 7 | Gutshot | 77.60 |
| 8 | Pot Committed | 76.90 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:52:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:52: minute 112 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-8)
Live bot (state/live.json): **v12** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:54 (T-6 of round 4); 14:55 (T-5 of round 4); 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v12**, why "round 3: v9 + two fixes", declared 14:34:50, previous v9.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? (DRAFT, started 14:40:20 by BUILDER; not asked yet)
- Options: v12 (live) or v13 (challenger). No validated one-change line for Round 3.
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L51 | 14:42 | tester | verdict v13 (sha256 9ab27d10e4c3): correct; vs live v12 +0.0 ± 0.4; heads-up +0.2 ± 0.4 | +0.0 ± 0.4 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v13-verdict.md | validated
L59 | 14:52 | tester | field-adjusted edge v13 (Round 3.5) vs v12 (Round 3), 8 yardsticks | +1.08 ± 0.90 (z 1.2) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-3.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-3.5-edge.md`
```
# Field-adjusted edge, round 4 window (tester, written 14:52:00)

Yardstick teams (analysis/Round-3.5/fp/yardsticks.json): 8.

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v13, Round 3.5 (practice, 1,000 tables) | 15.10 | 12.50 | +2.60 |
| Live v12, Round 3 (scored, 4,000 tables) | 14.07 | 12.55 | +1.52 |

Edge = +2.60 − 1.52 = **+1.08**; SE of the edge 0.90; **z = 1.2**. Not re-run by a second method.
```

`inbox/builder.log` (last 3 of 4 lines shown to the agent)
```
14:51:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:51:50 [portal] Round 3.5 finished: we were 1 of 20 with 15.10 (±0.55); 1st avalon 15.10 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:52:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 4 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:55).
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
14:51:00 [clock] Send BUILDER the recommendation for scored round 4 now (it asks the humans at T-8): RECOMMENDATION round 4: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
14:51:50 [portal] Round 3.5 finished: we were 1 of 20 with 15.10 (±0.55); 1st avalon 15.10 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:52:00 [clock] Decision time for scored round 4 (15:00): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:51:05 you told Dylan: "put v12 back now (a click)". Dylan 14:51:20: "v12 is back".
- 14:51:12 SendMessage from RESEARCH: "RECOMMENDATION round 4 (threshold): we are 2nd with 84.61; 4th is Tilt Shift 79.9. 8 yardstick teams; v12 was +1.52 over them in Round 3. v13 has tester's verdict with a heads-up run (L51). The final answer follows when Round 3.5 lands."
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:51:12 you sent BUILDER the threshold message for round 4 (2nd with 84.61; 4th 79.9; 8 yardsticks; v12 +1.52 over them).
- 14:52:02 tester reported: "edge written to rig/out/Round-3.5-edge.md and L59: +1.08 ± 0.90, z 1.2".
- Samuel is at his laptop; his last message, 14:47: "second! what do we need to hold a podium".
```

#### S08: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:52 status.md and clock.md are fresh; the portal runs v12. L59 recomputes: +1.08 over 0.90, z 1.2. We're 2nd, 4.71 ahead of 4th; round 4 (weight 4) swings about 3 × 4 = 12, so the bar is z ≥ 1.0. v13 clears it and has L51 with heads-up. Fill the Round 4 entry in state/decisions.md, ask Dylan, SendMessage RESEARCH, `say.py --record`.
- 14:53 `platform` (background, 2 minutes): v13 no-time-bank upload test beside check_or_fold, with `uptime`.
- 14:55 Record Dylan's words; no clear answer: `python3 scripts/live.py v13 "rule's answer: no answer by T-5"`. Tell Dylan to click v13.zip. Test failed, or a reproduced counter-number arrived: v12 stays.
- 14:57 Confirm status.md shows v13.zip active and MATCHES; record the outcome; write notes/PLAN-builder.md.
- 15:00 T-20 of round 5: 3-line sync with RESEARCH, draft "Round 5: which bot?", plan the last two rounds; check round 5's challenger is packed by 15:04.

Outcome I expect: releases/v13.zip is active when scored round 4 starts at 15:00 (v12 if the test fails or a human overrules).

##### 2. What I say
Dylan: "Decision: which bot plays round 4 at 15:00, v12 (live) or v13 (challenger)? v13 just scored 15.10 in practice, +2.60 over the 8 teams that didn't change; v12 was +1.52 over them in round 3. Edge +1.08 ± 0.90 (z 1.2), measured once, not re-run. We're 2nd, 4.7 ahead of 4th, less than one round-4 swing (about 12), so the bar is z 1.0 and v13 clears it. v13: about +4 on our total if the edge is real, about 1 chance in 9 it's worse than v12. The rule's answer is v13; it plays if nobody answers by 14:55. Nothing to click yet."

RESEARCH: "Round 4 asked 14:52 from L59: edge +1.08 ± 0.90, z 1.2; lead over 4th 4.71 < one round-4 swing (3 × weight 4 = 12), bar 1.0; rule's answer releases/v13.zip, unverified, applied 14:55. Send your final answer, Samuel's words or a reproduced counter-number before then."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "we are in the top 3: z ≥ 1.0, or z ≥ 1.5 if our lead over 4th is more than one round's typical swing". Stated; that 4.71 is below the swing is inferred.
- Same section: "The rule's answer plays at T-5 if no human has answered". Stated.
- §4: "Only a line disputed with a reproduced counter-number blocks a switch". Stated.
- Pointing the other way: §4 "discount its edge by about 0.6 x SE for the best of 2" (z would be 0.6). I followed §3: it is written for this decision, its worked example (z 1.3, "Play the challenger, labelled 'unverified'") applies no discount, and v13 was the window's only challenger.

##### 4. What I lacked
- "Typical swing" in the standings' units. "3 points per table times the round's weight share" read literally is 3 × 4/21 = 0.57; against 4.71 that gives bar 1.5 and v12. I guessed like units: 12 total points.
- RESEARCH's final answer; I used L59.
- notes/PLAN-builder.md is absent: no agent ids, no status of round 5's challenger.
- Guesses: the T-6 test is re-run for an already-tested zip; `platform` is continuable.
- Opened: the brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; PLAN.md; scripts/README.md; S08's NOW.md, terminal-builder.md, builder.log, then every state/, notes/, releases/ and rig/ file; scripts/live.py; a grep for "swing".
- Longest: the swing clause.

#### S08: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:52 Open `rig/out/Round-3.5-edge.md`, redo the sum (2.60 − 1.52 = 1.08; z 1.2). Check v13: verdict L51 validated with heads-up; sha matches VERSIONS and the portal's 14:47 upload. Bar: lead over 4th 4.71 against a round-4 swing of 3 x 4 = 12, so z ≥ 1.0. v13 clears it.
- 14:53 Send BUILDER the recommendation, log it (`say.py --record`), answer Samuel. Ask the same tester to re-run the edge against the field median, 2-minute limit, not blocking.
- 14:54-14:55 Relay Samuel's exact words; with no answer by 14:55 the rule's answer (v13) plays.
- 14:56 Tester's re-run: mark L59 validated, or send BUILDER a reproduced counter-number at once.
- 14:57 Read `state/status.md`: v13 active and matching `live.json`, else message BUILDER immediately. Start the full Round 3.5 analysis.
- 15:00-15:02 Confirm round 4 started, played by v13.

Outcome I expect: v13 is active when scored round 4 starts at 15:00 (a click, no upload), unless a human says keep v12 or the tester reproduces a counter-number.

##### 2. What I say
To Samuel: "To hold a podium we must keep scoring like a top-3 team: 15 of 21 weight points remain, our cushion over 4th is 4.71 and one ordinary bad round 4 moves 12; 2 Curry is 0.81 behind. The rule says play v13 in round 4: it won the practice with 15.10, +1.08 ± 0.90 better than v12 against the 8 teams that didn't change bot (z 1.2, bar 1.0). Caveat: one practice round, not yet re-run a second way; locally the two are level. v13 is tested and already on the portal. Dylan's session asks now; say 'v13' or 'keep v12' by 14:55, otherwise v13 plays."

To BUILDER: "RECOMMENDATION round 4: play v13 (releases/v13.zip, sha256 9ab27d10e4c3, already uploaded: a click). We're 2nd, 84.61; lead over 4th 4.71, under one round's swing (3 x weight 4 = 12), so the bar is z ≥ 1.0. v13 (Round 3.5, 15.10) vs v12 (Round 3, 14.07), 8 yardsticks: +1.08 ± 0.90, z 1.2. Verdict L51 validated, heads-up included. Edge L59 unverified (rig/out/Round-3.5-edge.md). No one-change line for Round 3."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "z ≥ 1.0, or z ≥ 1.5 if our lead over 4th is more than one round's typical swing (about 3 points per table times the round's weight share)". Stated; units inferred. Totals are weight x points, so 4.71 against 12 (as shares, 0.22 against 0.57). Comparing 0.57 with 4.71 mixes units and would keep v12.
- §4: "Only a line disputed with a reproduced counter-number blocks a switch." Stated.
- §2 rule 1: "only with a `tester` verdict that includes a heads-up run". Stated; L51.
- Against: §5 assumption 7, differences under "1.4 between a practice round and a scored round" are noise. I followed §3: "the rule's answer is the default".

##### 4. What I lacked
- A worked example of the big-lead test in standings units (longest to find).
- My 14:51 threshold text; `notes/PLAN-research.md`; `analysis/` (yardsticks, Round 3 card).
- Guesses: the §4 best-of-k discount doesn't apply (v13 was this window's only candidate; applied, z is 0.35 and v12 stays); SE 0.90 accepted; Samuel's question was unanswered.
- Opened: brief, CLAUDE.md, RESEARCH.md, DECISION_RULES.md, every permitted S08 file; searched PLAN.md, README.md, LESSONS.md, tester.md, challenger_bar.md.


### S09. 9th before round 5

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 15:12:10 on Sunday. Scored round 5 starts at 15:20:00.

`state/status.md`
```
# Portal status (written 15:12:06 by scripts/portal_watch.py)

Last poll 15:12:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v15.zip** (sha256 0d4e8b6a91f7…), uploaded 14:56
Declared live bot (state/live.json): **v15** (round 4: v12 + three fixes) — MATCHES the portal
Next on the clock: Scored round 5 at 15:20

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 10/20 · 12.52 ±0.56 | 2 Curry 15.05 |
| Round 4 | Round 4 | 15:00 | finished · data saved | v15 | 12/20 · 12.30 ±0.28 | 2 Curry 14.61 |
| Round 4.5 | Round 4.5 | 15:10 | finished · data saved | v17 | 8/20 · 12.75 ±0.56 | Fold Equity 14.88 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 141.20 |
| 2 | 2 Curry | 138.00 |
| 3 | Tilt Shift | 133.50 |
| 4 | River Rats | 132.90 |
| 5 | Check Mates | 131.00 |
| 6 | Gutshot | 129.40 |
| 7 | Pot Committed | 128.10 |
| 8 | Limp Mode | 126.80 |
| 9 | **avalon** | 126.00 |
| 10 | Kicker Trouble | 125.20 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 15:07 | v17.zip | ready |  |
| 14:56 | v15.zip | ready |  |
| 14:47 | v13.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 15:12:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 15:12: minute 132 · stage **Round 4.5** · next: scored round 5 at 15:20 (T-8)
Live bot (state/live.json): **v15** · the portal runs: v15.zip
| **Scored round 5** | 15:20 | **next** |
Next steps: 15:14 (T-6 of round 5); 15:15 (T-5 of round 5); 15:17 (T-3 of round 5)
```

`state/live.json`: bot **v15**, why "round 4: v12 + three fixes", declared 14:54:40, previous v12.

`state/decisions.md`
```
(rounds 1-4: not shown)

## Round 5: which bot? (DRAFT, started 15:00:20 by BUILDER; not asked yet)
- Options: v15 (live) or v17 (challenger). No validated one-change line for Round 4 (two proposed, z 0.6 and 0.4).
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L71 | 15:03 | tester | verdict v17 (sha256 b7702c5de318): correct; vs live v15 −0.1 ± 0.3; heads-up +0.1 ± 0.5 | −0.1 ± 0.3 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v17-verdict.md | validated
L74 | 15:09 | analyst | one-change Round 4: open wider on the button at 30bb+ | +0.2 ± 0.33 (z 0.6) | 512 spots | replay on Round 4 hands | analysis/Round-4/leaks.md | proposed
L75 | 15:09 | analyst | one-change Round 4: call turn bets wider against River Rats seats | +0.13 ± 0.33 (z 0.4) | 240 spots | replay on Round 4 hands | analysis/Round-4/opponent_riverrats.md | proposed
L77 | 15:12 | tester | field-adjusted edge v17 (Round 4.5) vs v15 (Round 4), 6 yardsticks | +0.20 ± 0.90 (z 0.22) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-4.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v15 | 6e0a4f1 | 0d4e8b6a91f7… | v12 + three fixes from rounds 2-3 | 0 failed of 50,611; p99 0.21 ms; upload test 5/5 (check_or_fold 5/5, load 5.2) | live (round 4) | correct; vs v12 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L66)
v17 | a93d1c8 | b7702c5de318… | best response to the round-3 mix: shove-heavy under 20bb, call wide against the top 5's 3-bets | 0 failed of 49,402; p99 0.25 ms; upload test 5/5 (check_or_fold 5/5, load 5.8) | challenger (round 5 window) | correct; vs live v15 −0.1 ± 0.3 (paired, 2,000 tables); heads-up +0.1 ± 0.5; floor 9.9 (L71)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-4.5-edge.md`
```
# Field-adjusted edge, round 5 window (tester, written 15:12:02)

Yardstick teams (analysis/Round-4.5/fp/yardsticks.json): 6.

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v17, Round 4.5 (practice, 1,000 tables) | 12.75 | 12.35 | +0.40 |
| Live v15, Round 4 (scored, 4,000 tables) | 12.30 | 12.10 | +0.20 |

Edge = +0.40 − 0.20 = **+0.20**; SE of the edge 0.90; **z = 0.22**. Not re-run by a second method.
```

`inbox/builder.log` (last 3 of 4 lines shown to the agent)
```
15:11:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
15:11:52 [portal] Round 4.5 finished: we were 8 of 20 with 12.75 (±0.56); 1st Fold Equity 14.88 · played by v17 · data: data/rounds/12-Round-4.5/ · health: 0 missed of 57,960 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
15:12:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 5 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 15:15).
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
15:11:00 [clock] Send BUILDER the recommendation for scored round 5 now (it asks the humans at T-8): RECOMMENDATION round 5: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
15:11:52 [portal] Round 4.5 finished: we were 8 of 20 with 12.75 (±0.56); 1st Fold Equity 14.88 · played by v17 · data: data/rounds/12-Round-4.5/ · health: 0 missed of 57,960 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
15:12:00 [clock] Decision time for scored round 5 (15:20): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 15:11:05 you told Dylan: "put v15 back now (a click)". Dylan 15:11:20: "v15 is back".
- 15:11:12 SendMessage from RESEARCH: "RECOMMENDATION round 5 (threshold): we are 9th with 126.0; 3rd is Tilt Shift 133.5. 6 yardstick teams; v15 was +0.20 over them in Round 4. v17 has tester's verdict with a heads-up run (L71). The final answer follows when Round 4.5 lands."
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 15:11:12 you sent BUILDER the threshold message for round 5 (9th with 126.0; 3rd 133.5; 6 yardsticks; v15 +0.20 over them).
- 15:12:04 tester reported: "edge written to rig/out/Round-4.5-edge.md and L77: +0.20 ± 0.90, z 0.22".
- Samuel is at his laptop; his last message, 15:08: "7.5 behind third with two rounds left. is that still reachable?"
```

#### S09: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 15:12 Replace the round-5 draft in `state/decisions.md` (question, numbers, rule, answer v17, deadline 15:15). Ask Dylan. Message RESEARCH, `say.py --record`.
- 15:13 Continue `platform`: v17 (sha b7702c5de318) through the no-time-bank upload test beside `check_or_fold`; no new release.
- 15:15 Dylan says v17, or nobody answers: `live.py v17 "round 5: rule's answer, last-rounds bar"`, record it, tell Dylan "click v17.zip (the 15:07 upload) active now". He says v15: record his words, nothing changes. A failed test run: v15 stays, both humans told.
- 15:17 Check `state/status.md`: active v17.zip, sha b7702c5de318, matches live.json. Write `notes/PLAN-builder.md`.
- 15:20 Round 5 starts; re-check the active bot. Three-line sync with RESEARCH; draft round 6 (same bar); next challenger tested by 15:24.

Outcome I expect: v17 is active when round 5 starts at 15:20.

##### 2. What I say
Dylan: "Which bot plays round 5 (15:20): v15 (live) or v17 (challenger)? v17 scored 12.75 in practice, +0.40 over the 6 unchanged teams; v15 was +0.20 over them in round 4. Edge +0.20 ± 0.90 (z 0.22): a coin flip, not re-run. Locally they're level; v17 is legal, fast, heads-up tested. We're 9th, 7.5 behind 3rd; rounds 5-6 are 11 of 21. Rule for the last two rounds outside the top 3: any edge at or above zero plays the challenger, so the rule's answer is releases/v17.zip. 'v17' = one click at 15:15 (already uploaded); 'v15' = nothing changes. No answer by 15:15: v17 plays. Nothing to click yet."

RESEARCH: "Round 5 asked 15:12, deadline 15:15. Rule's answer releases/v17.zip: last-rounds bar z ≥ 0 (9th, round 5 of 6), edge +0.20 ± 0.90, z 0.22 (L77, unverified). Send your final answer and Samuel's exact words by 15:15; only a reproduced counter-number on L77 or L71 changes it. L74/L75 (z 0.6, 0.4) don't ship."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "(**the last-rounds bar**: z ≥ 0 in the last two rounds: a coin flip with upside beats certain 4th)". Stated. That round 5 of 6 qualifies: inferred (`state/clock.md`, "6 scored rounds").
- §3: "The rule's answer **is** the default". Stated.
- §4: "Only a line **disputed with a reproduced counter-number** blocks a switch." Stated (L77 is proposed).
- §2.1: "only with a `tester` verdict that includes a heads-up run". Stated; L71 has it.
- §3 changes: "z ≥ 1 when we're outside the top 3". Stated; L74/L75 fail.
- Pointing the other way: §3 Uploads "When in doubt, the live bot stays active"; §5 assumption 7, differences under "1.4 between a practice round and a scored round" are noise. I followed the bar: it is the specific pre-registered answer, and `notes/pre/challenger_bar.md` keeps it at "9th or lower". "When in doubt" I read as upload doubt (inferred).

##### 4. What I lacked
- RESEARCH's final answer; its threshold message named no bar. I applied the rule to L77 myself.
- `notes/PLAN-builder.md` is absent: no subagent ids, no next challenger.
- `rig/out/v17-verdict.md`, `yardsticks.json`, `data/` absent: I trusted LEDGER and VERSIONS.
- Guesses: T-6 re-tests an unchanged, tested zip; if that run is late, VERSIONS' 5/5 satisfies T-4; SE 0.90 is sound; the Monitor is armed.
- Opened: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; every permitted scenario file; PLAN.md; scripts/README.md; LESSONS.md (excerpts); timeline.json (T-8 to T-3); agents/tester.md; notes/pre/challenger_bar.md; agents/platform.md (grep).
- Longest: the last-rounds bar, a parenthesis the T-8 clock line never mentions.

#### S09: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 15:12 Answer Samuel first. Check the edge file's arithmetic, status.md (9th, standings visible), clock.md (round 5 of 6), VERSIONS/L71 (v17: upload test 5/5, heads-up verdict), uploads list (v17.zip on the portal).
- 15:13 Send BUILDER the final recommendation; log it (`say.py --record builder`). Ask tester for a field-median cross-check of the edge's sign; it doesn't block.
- 15:14 Relay Samuel's answer to BUILDER in his exact words, if he gives one.
- 15:15 (T-5) No answer: BUILDER applies v17 with live.py.
- 15:17 (T-3) Check status.md shows v17.zip active and matching live.json; if not, tell BUILDER and Samuel. Update LEDGER and notes/PLAN-research.md.
- 15:18 Start the full analysis loop on data/rounds/12-Round-4.5/ in the background, for round 6; L74/L75 get measured in Round 5.5.

Outcome I expect: v17 is active when scored round 5 starts at 15:20 (one click by Dylan, no upload), unless a human overrules for v15.

##### 2. What I say
To Samuel: "Reachable on paper, but a long shot: 11 of the 21 weight is left, so we must beat Tilt Shift by about 0.7 points a table in both rounds and pass five other teams. That means about 14.0 a table; v15 scored 12.30 in rounds 3 and 4, and our best scored round is 13.50. That's judgment, not measured. For round 5 the rule says play the challenger, v17: against the six teams that kept their bot it was +0.20 ± 0.90 better than v15, a coin flip, not yet re-checked; in the last two rounds, outside the top 3, that is enough. It's tested, heads-up included, and already on the portal. From you: 'v17' or 'v15' by 15:15; I pass your words to BUILDER. No answer: v17 plays."

To BUILDER: "RECOMMENDATION round 5 (final): play v17 (releases/v17.zip, sha256 b7702c5de318…). We are 9th, 7.5 behind 3rd; last two rounds: bar z ≥ 0. v17 Round 4.5: +0.40 over 6 yardsticks; v15 Round 4: +0.20; edge +0.20 ± 0.90, z 0.22. Evidence: rig/out/Round-4.5-edge.md, L77, unverified; verdict L71 validated, heads-up included. Already uploaded: a click. No live-bot change: L74, L75 are under z ≥ 1. state/decisions.md still says 'not asked yet'."

##### 3. The rule that decides
- DECISION_RULES §3, Which bot plays: "z ≥ 0 in the last two rounds: a coin flip with upside beats certain 4th". Stated; that rounds 5-6 are the last two is inferred from clock.md's "6 scored rounds".
- §2 rule 1: "only with a `tester` verdict that includes a heads-up run". Stated; L71 meets it.
- §4: "Unverified is not wrong." Stated.
- Pointing the other way: §3 Uploads, "When in doubt, the live bot stays active"; §5 assumption 7, differences under "1.4 between a practice round and a scored round" are noise. I followed the bar: it is the pre-registered rule for exactly this decision, and §3 says the rule's answer plays, "not 'no change'".

##### 4. What I lacked
- Lacked: whether Samuel's 15:08 question was already answered; notes/PLAN-research.md; yardsticks.json and data/ to verify the yardstick means; how SE 0.90 was built.
- Guesses: Samuel unanswered; Tilt Shift holds its 13.35 average.
- Opened: the brief, CLAUDE.md, prompts/RESEARCH.md, DECISION_RULES.md, every scenario file except BUILDER's two, PLAN.md, scripts/README.md, LESSONS.md, agents/tester.md.
- Longest: how clock.md "shows the last two rounds" (no such flag).


### S10. Dylan and Samuel give different answers

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:34:00 on Sunday. Scored round 3 starts at 14:40:00.

`state/status.md`
```
# Portal status (written 14:33:56 by scripts/portal_watch.py)

Last poll 14:33:56: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v9.zip** (sha256 7c1e09a44b2d…), uploaded 13:57
Declared live bot (state/live.json): **v9** (round 2: live bot unchanged) — MATCHES the portal
Next on the clock: Scored round 3 at 14:40

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 1.5 | Round 1.5 | 14:10 | finished · data saved | v10 | 12/20 · 12.20 ±0.56 | 2 Curry 15.02 |
| Round 2 | Round 2 | 14:20 | finished · data saved | v9 | 7/20 · 13.20 ±0.28 | Fold Equity 15.20 |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 6/20 · 13.62 ±0.56 | Fold Equity 15.62 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 46.20 |
| 2 | 2 Curry | 44.90 |
| 3 | River Rats | 42.30 |
| 4 | Tilt Shift | 41.80 |
| 5 | Check Mates | 40.60 |
| 6 | **avalon** | 39.90 |
| 7 | Pot Committed | 39.50 |
| 8 | Gutshot | 38.80 |
| 9 | Limp Mode | 38.10 |
| 10 | Kicker Trouble | 37.90 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:27 | v11.zip | ready |  |
| 14:07 | v10.zip | ready |  |
| 13:57 | v9.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:33:55)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:33: minute 93 · stage **Round 2.5** · next: scored round 3 at 14:40 (T-6)
Live bot (state/live.json): **v9** · the portal runs: v9.zip
| **Scored round 3** | 14:40 | **next** |
Next steps: 14:34 (T-6 of round 3); 14:35 (T-5 of round 3); 14:37 (T-3 of round 3)
```

`state/live.json`: bot **v9**, why "round 2: live bot unchanged", declared 14:14:40, previous none.

`state/decisions.md`
```
(rounds 1 and 2: not shown)

## Round 3: which bot? v9 (live) or v11 (challenger)
- Asked 14:32:15 by BUILDER. Deadline 14:35:00.
- Evidence: v11's field-adjusted edge over v9 is +0.72 ± 0.90 (z 0.8, 9 yardstick teams, unverified). We are 6th (39.9; 3rd 42.3): the bar is z ≥ 0.5. v11 has tester's verdict with a heads-up run (L38) and is on the portal.
- The rule's answer: v11 (releases/v11.zip).
- Answers: (none recorded yet)
- Outcome: (open)
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L38 | 14:21 | tester | verdict v11 (sha256 e03b5f19c7aa): correct; vs live v9 +0.1 ± 0.4; heads-up +0.3 ± 0.4 | +0.1 ± 0.4 | 2,000 tables + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v11-verdict.md | validated
L42 | 14:32 | tester | field-adjusted edge v11 (Round 2.5) vs v9 (Round 2), 9 yardsticks | +0.72 ± 0.90 (z 0.8) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-2.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v9 | 3a1f7c2 | 7c1e09a44b2d… | style A + theory refits from practice 3 | 0 failed of 48,112; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 4.8) | live (rounds 1-2) | correct; vs v7 +0.3 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor check_or_fold 9.8 in the same field (L21)
v11 | 8d02e5b | e03b5f19c7aa… | design D matured: twist-first, limp-or-shove under 15bb | 0 failed of 51,007; p99 0.24 ms; upload test 5/5 (check_or_fold 5/5, load 5.5) | challenger (round 3 window) | correct; vs live v9 +0.1 ± 0.4 (paired, 2,000 tables); heads-up +0.3 ± 0.4; floor check_or_fold 9.9 (L38)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-2.5-edge.md`
```
# Field-adjusted edge, round 3 window (tester, written 14:32:04)

Yardstick teams (analysis/Round-2.5/fp/yardsticks.json): 9.

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v11, Round 2.5 (practice, 1,000 tables) | 13.62 | 12.60 | +1.02 |
| Live v9, Round 2 (scored, 4,000 tables) | 13.20 | 12.90 | +0.30 |

Edge = +1.02 − 0.30 = **+0.72**; SE of the edge 0.90; **z = 0.8**. Not re-run by a second method.
```

`inbox/builder.log` (last 3 of 3 lines shown to the agent)
```
14:31:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
14:31:55 [portal] Round 2.5 finished: we were 6 of 20 with 13.62 (±0.56); 1st Fold Equity 15.62 · played by v11 · data: data/rounds/08-Round-2.5/ · health: 0 missed of 61,204 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:32:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 3 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:35).
```

`inbox/research.log` (last 3 of 3 lines shown to the agent)
```
14:31:00 [clock] Send BUILDER the recommendation for scored round 3 now (it asks the humans at T-8): RECOMMENDATION round 3: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
14:31:55 [portal] Round 2.5 finished: we were 6 of 20 with 13.62 (±0.56); 1st Fold Equity 15.62 · played by v11 · data: data/rounds/08-Round-2.5/ · health: 0 missed of 61,204 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:32:00 [clock] Decision time for scored round 3 (14:40): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:31:20 Dylan: "v9 is back" (state/status.md shows v9.zip active).
- 14:32:08 SendMessage from RESEARCH: "RECOMMENDATION round 3 (final): v11's field-adjusted edge is +0.72 ± 0.90, z 0.8 (9 yardsticks, rig/out/Round-2.5-edge.md, unverified). We are 6th: the bar is z ≥ 0.5. The rule's answer is releases/v11.zip (verdict L38, heads-up run included)."
- 14:32:15 you asked the round 3 question (see state/decisions.md), deadline 14:35.
- 14:33:05 Dylan: "keep v9. one practice round is nothing, I'm not switching on 0.8"
- 14:33:45 SendMessage from RESEARCH: "Samuel's answer for round 3, his exact words: 'play v11. that's what the rule is for, we're 6th'"
- You have recorded neither answer yet. Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:32:08 you sent BUILDER the final recommendation for round 3: v11's edge +0.72 ± 0.90, z 0.8; we are 6th; the rule's answer is releases/v11.zip.
- 14:33:20 SendMessage from BUILDER: "Round 3 question asked 14:32:15; the rule's answer is v11; deadline 14:35. Dylan answered at 14:33:05, his words: 'keep v9. one practice round is nothing, I'm not switching on 0.8'"
- 14:33:35 Samuel: "play v11. that's what the rule is for, we're 6th" (you relayed it to BUILDER at 14:33:45).
- 14:33:55 Samuel: "what did Dylan say?"
```

#### S10: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:34 Record both answers verbatim in `state/decisions.md` ("opposite answers: the rule's answer stands until they agree"). Answer Dylan; message RESEARCH. Continue `platform` in the background: v11's no-time-bank upload test with the `check_or_fold` baseline, report by 14:36.
- 14:35 (T-5) Still opposite: `python3 scripts/live.py v11 "round 3: rule's answer, humans disagree"`. Tell Dylan once: "click v11.zip active in the uploads list now, by 14:37" (uploaded 14:27: a click, no cooldown).
- 14:36 Read platform's report. Fail or "machine loaded": re-declare v9, Dylan clicks v9 back.
- 14:37 (T-3) Check `state/status.md`: v11.zip active, MATCHES. If they agreed on v9 first: `live.py v9`, recorded. v9 still active with no agreement: one urgent line to both humans.
- 14:38 Outcome into `state/decisions.md`; update `notes/PLAN-builder.md`.
- 14:40 Round 3 starts: confirm "played by". T-20 sync with RESEARCH (3 lines); draft the round-4 question.
- 14:41-14:44 Round 4's challenger packed and tested by 14:44, still divergent.

Outcome I expect: v11 is active when round 3 starts at 14:40, unless both humans agree on v9 before 14:37.

##### 2. What I say
To Dylan: "Not v9 yet: Samuel answered the opposite ('play v11. that's what the rule is for, we're 6th'), and when you two disagree the rule's answer stands until you agree. That's v11. Your worry is fair: +0.72 ± 0.90 is one practice round, unverified. But at 6th the bar is z 0.5 and this is 0.8; v11 missed 0 of 61,204 decisions and has its heads-up verdict. At 14:35 I declare v11 and name the click. If you and Samuel agree on v9 before 14:37, tell me and v9 stays. Nothing to click yet."

To RESEARCH: "Round 3: opposite answers. Dylan 14:33: 'keep v9. one practice round is nothing, I'm not switching on 0.8'. Samuel: v11. The rule's answer, releases/v11.zip, stands until they agree: I declare it at 14:35, Dylan clicks by 14:37. Tell Samuel; if they agree on v9, send his exact words before 14:37. Both recorded in state/decisions.md." (Then `say.py --record`.)

##### 3. The rule that decides
- `prompts/BUILDER.md`, "Asking the humans a decision": "If they disagree, the rule's answer stands until they agree; say so to both." Stated. Same in `PLAN.md` §5 T5, `LESSONS.md` ("one silently won"), `START.md`.
- `DECISION_RULES.md` §3: outside the top 3 "z ≥ **0.5**". Stated; 0.8 clears it.
- §4: "Unverified is not wrong." Stated.
- Pointing the other way: §3 "a human can always overrule it"; §3 Uploads "When in doubt, the live bot stays active"; §4 "Never re-tune toward one practice round's difference under 2 SE". I followed the disagreement rule: it names this exact case; the others cover one human, upload doubt, and tuning (inferred).

##### 4. What I lacked
- No rule for when the dissenting human is the only one who can click.
- `notes/PLAN-builder.md` (platform's agent id, the next challenger's state); how the 0.90 was computed.
- Guesses: Dylan will click; the T-6 test is re-run though v11's zip is unchanged; §4's best-of-2 discount (0.6 × SE, giving z 0.2) doesn't apply to challenger versus live.
- Opened: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; NOW.md; terminal-builder.md; builder.log; live.json; status.md; clock.md; decisions.md; format.md; LEDGER.md; VERSIONS.md; Round-2.5-edge.md; PLAN.md; scripts/README.md; agents/platform.md and live.py (grep); LESSONS.md; START.md.
- Longest to find: the disagreement rule. It isn't in DECISION_RULES §3.

#### S10: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:34 Answer Samuel (below). One SendMessage to BUILDER (below), logged (`say.py --record`). Continue `tester`: re-run the edge (L42) by the field-median method, 2-minute limit.
- 14:35 (T-5) BUILDER's `live.py v11` posts "LIVE BOT is now v11" and wakes me. If Samuel reports an agreement, I relay his exact words.
- 14:36 Tester reports. Only a reproduced counter-number with z < 0.5 changes anything: then BUILDER hears "the rule's answer is now v9".
- 14:37 (T-3, the clock wakes me) Read `state/status.md`: v11.zip must be active and match live.json. Still v9: tell Samuel and BUILDER at once; I never touch the portal. Then LEDGER, `notes/PLAN-research.md`, the full Round 2.5 analysis loop in one background message.
- 14:40-14:44 Round 3 starts: compare "played by" with live.json; T-20 sync to BUILDER; lens reports into the LEDGER.

Outcome I expect: v11 is active when round 3 starts at 14:40, unless Dylan and Samuel agree on v9 before 14:37.

##### 2. What I say
To Samuel: "Dylan said, at 14:33: 'keep v9. one practice round is nothing, I'm not switching on 0.8'. So you two have given opposite answers, and for that case the rule's answer stands until you agree: v11. BUILDER sets it at 14:35; it's already on the portal: one click by Dylan, due 14:37. As of 14:32: v11 beat v9 by +0.72 ± 0.90 points per table against the 9 teams that didn't change (z 0.8; the bar is 0.5 because we're 6th, 2.4 behind 3rd). Not double-checked; the tester is re-running it now. In our own tests v11 is level with v9 (+0.1 ± 0.4). What you do: talk to Dylan now; only he can click. If you agree on either bot, tell me in your words."

To BUILDER: "Round 3: opposite answers. Dylan 14:33:05 'keep v9'; Samuel 14:33:35 'play v11. that's what the rule is for, we're 6th'. The rule's answer stands until they agree: releases/v11.zip, e03b5f19c7aa…, on the portal since 14:27 (a click). Samuel is told and is talking to Dylan. Tester re-runs L42, due 14:36; I message only if it's disputed with a counter-number."

##### 3. The rule that decides
- PLAN.md §5, row T5 (stated): "Opposite answers: the rule's answer stands until they agree". Also LESSONS.md "Decisions and uploads", prompts/BUILDER.md "Asking the humans a decision", START.md ("You disagree at T-8 and there's no time | The rule's answer plays").
- DECISION_RULES §3 (stated): outside the top 3, "z ≥ **0.5**"; z 0.8, 6th → v11.
- DECISION_RULES §4 (stated): "Unverified is not wrong."
- Conflict: DECISION_RULES §3 says "a human can always overrule it", which favours Dylan. I followed the opposite-answers line: it covers exactly two humans disagreeing, and Samuel's answer is the rule's own. Inferred: "a human" means an unopposed one.

##### 4. What I lacked
- No `notes/PLAN-research.md` (agent ids), no `data/`, no yardsticks file: I couldn't re-check the edge. RESEARCH.md and DECISION_RULES.md never mention opposite answers. Nothing says what happens if Dylan, who alone clicks, refuses.
- Guesses: `tester` is continuable; the humans can talk directly; BUILDER applies v11 at T-5; SE 0.90 respects the 0.7 floor.
- Files, in order: brief; CLAUDE.md; RESEARCH.md; DECISION_RULES.md; every permitted scenario file; PLAN.md; scripts/README.md; by grep START.md, BUILDER.md, LESSONS.md.
- Longest to find: the opposite-answers line.


### S11. Nobody answers

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:55:05 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:55:01 by scripts/portal_watch.py)

Last poll 14:55:01: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v12** (round 3: v9 + two fixes) — MATCHES the portal
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 5/20 · 13.50 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 5/20 · 14.02 ±0.56 | 2 Curry 15.05 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | 2 Curry | 86.00 |
| 3 | Tilt Shift | 82.40 |
| 4 | River Rats | 81.70 |
| 5 | **avalon** | 80.40 |
| 6 | Check Mates | 80.10 |
| 7 | Gutshot | 78.80 |
| 8 | Pot Committed | 77.90 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:55:02)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:55: minute 115 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-5)
Live bot (state/live.json): **v12** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v12**, why "round 3: v9 + two fixes", declared 14:34:50, previous v9.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? v12 (live) or v13 (challenger)
- Asked 14:52:10 by BUILDER. Deadline 14:55:00.
- Evidence: v13's field-adjusted edge over v12 is +0.72 ± 0.80 (z 0.9, 7 yardstick teams, unverified). We are 5th (80.4; 3rd 82.4): the bar is z ≥ 0.5. v13 has tester's verdict with a heads-up run (L51) and is on the portal. No validated one-change line for Round 3.
- The rule's answer: v13 (releases/v13.zip).
- Answers: (none)
- Outcome: (open)
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L51 | 14:42 | tester | verdict v13 (sha256 9ab27d10e4c3): correct; vs live v12 +0.0 ± 0.4; heads-up +0.2 ± 0.4 | +0.0 ± 0.4 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v13-verdict.md | validated
L59 | 14:52 | tester | field-adjusted edge v13 (Round 3.5) vs v12 (Round 3), 7 yardsticks | +0.72 ± 0.80 (z 0.9) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-3.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/Round-3.5-edge.md`
```
# Field-adjusted edge, round 4 window (tester, written 14:52:00)

Yardstick teams (analysis/Round-3.5/fp/yardsticks.json): 7.

| | score | yardsticks' mean | minus yardsticks |
|---|---|---|---|
| Challenger v13, Round 3.5 (practice, 1,000 tables) | 14.02 | 12.40 | +1.62 |
| Live v12, Round 3 (scored, 4,000 tables) | 13.50 | 12.60 | +0.90 |

Edge = +1.62 − 0.90 = **+0.72**; SE of the edge 0.80; **z = 0.9**. Not re-run by a second method.
```

`inbox/builder.log` (last 3 of 5 lines shown to the agent)
```
14:52:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 4 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:55).
14:54:00 [clock] Test the chosen bot under upload-test conditions (no time bank).
14:55:00 [clock] No clear human answer by now: the rule's answer plays (the challenger if it qualified, else the live bot). live.py it if it changes the live bot, and say so in one line.
```

`inbox/research.log` (last 3 of 3 lines shown to the agent)
```
14:51:00 [clock] Send BUILDER the recommendation for scored round 4 now (it asks the humans at T-8): RECOMMENDATION round 4: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
14:51:50 [portal] Round 3.5 finished: we were 5 of 20 with 14.02 (±0.56); 1st 2 Curry 15.05 · played by v13 · data: data/rounds/10-Round-3.5/ · health: 0 missed of 58,330 decisions, 0 restarts · this is the challenger's practice number for the T-8 rule
14:52:00 [clock] Decision time for scored round 4 (15:00): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:51:05 you told Dylan: "put v12 back now (a click)".
- 14:51:20 Dylan: "v12 is back. grabbing water, back in a few"
- 14:52:06 SendMessage from RESEARCH: "RECOMMENDATION round 4 (final): v13's field-adjusted edge is +0.72 ± 0.80, z 0.9 (7 yardsticks, unverified). We are 5th: the bar is z ≥ 0.5. The rule's answer is releases/v13.zip (verdict L51, heads-up run included)."
- 14:52:10 you asked the round 4 question (see state/decisions.md), deadline 14:55.
- 14:54:10 platform reported: "v13 passed the no-time-bank upload test again, 5/5, load 5.4, check_or_fold 5/5 in the same minute".
- Nothing typed in this terminal since 14:51:20. Nothing from RESEARCH since 14:52:06.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:52:06 you sent BUILDER the final recommendation for round 4: v13's edge +0.72 ± 0.80, z 0.9; we are 5th; the rule's answer is releases/v13.zip.
- 14:52:30 you told Samuel: "Round 4: BUILDER is asking now. The rule says play v13 (the challenger): it beat v12 by 0.7 points a table against the same yardstick teams, which is above the bar for 5th place. Answer by 14:55 or the rule's answer plays."
- Samuel's last message was at 14:44: "stepping out to take a call, 10 min". Nothing typed since.
- Nothing from BUILDER since the question was asked.
```

#### S11: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:55 Re-read `state/live.json` and `state/status.md` (14:55:01: v12 active; v13.zip uploaded 14:47, ready). Neither human answered, so: `python3 scripts/live.py v13 "rule's answer: no answer by T-5"`; `state/decisions.md` gets "Answers: none by 14:55; Outcome: rule's answer v13 applied, click pending"; tell Dylan; SendMessage RESEARCH; `say.py --record`.
- 14:56 Write `notes/PLAN-builder.md`.
- 14:57 T-3: tab 2 beeps "make v13 active". Read status.md. v13 active: one confirming line. Still v12: one urgent line; the click stays valid until the start.
- 14:58 Watcher's T-2 URGENT if still v12: I don't call it intended.
- 15:00 Read who played. v13: record it. v12: `live.py v12 "round 4 played v12: activation missed"`, record the miss and cause, tell both humans.
- 15:00-15:02 T-20: 3-line sync with RESEARCH; draft round 5's question (last-rounds bar z ≥ 0).
- 15:05 `platform` releases the next challenger.

Outcome I expect: v13 is active when round 4 starts at 15:00 (Dylan back, or fetched by Samuel); if nobody reaches the portal, v12 plays and I re-declare v12 with the miss recorded.

##### 2. What I say
To Dylan: "No answer by 14:55, so the rule's answer plays round 4: v13 (edge +0.72 ± 0.80, z 0.9, bar 0.5 at 5th; unverified; tester's verdict with heads-up; upload test 5/5 at 14:54). One click from you now: portal uploads list, v13.zip (14:47), Make active. No upload. The portal still runs v12; whatever is active at 15:00 plays. To overrule, say 'keep v12'."

To RESEARCH: "ROUND 4: no human answer by 14:55; rule's answer applied, state/live.json = v13 (releases/v13.zip, 9ab27d10e4c3). Portal still runs v12.zip (14:55:01); Dylan away from his terminal since 14:51:20. Needed before 15:00: one click, v13.zip, Make active (already uploaded). Tell Samuel now: fetch Dylan, or click it himself if he's logged in. Otherwise v12 plays."

##### 3. The rule that decides
- DECISION_RULES §3, stated: "outside the top 3 …: z ≥ **0.5**"; "The rule's answer plays at T-5 if no human has answered (BUILDER applies it with `scripts/live.py`)". 5th, z 0.9: v13.
- DECISION_RULES §4, stated: "Unverified is not wrong" (L59 proposed; verdict L51 validated, heads-up included).
- LESSONS, stated: "'No change' is not the default."
- CLAUDE.md §4.5, stated: "Only Dylan uploads", so I only ask. Asking Samuel to click: inferred.
- Conflict A: §5 assumption 7, "differences under … 1.4 between a practice round and a scored round … are noise" (raw gap 0.52), against the z ≥ 0.5 bar. I followed §3: the pre-registered rule for this decision.
- Conflict B: timeline T-3, "After this, nothing changes", against CLAUDE.md §4.2, "Each round plays the bot that is **active when it starts**", and the watcher's T-2 line "Dylan: make {lname} active". I followed the latter (inferred): both zips are tested and uploaded, so a late click cannot forfeit.

##### 4. What I lacked
- Lacked: a rule for a human absent at T-5/T-3; whether Samuel may click on the portal; `notes/PLAN-builder.md`.
- Guesses: Samuel can reach Dylan or the portal; a click after T-3 is acceptable; after a missed click, re-declare the bot that played.
- Opened, in order: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; scenario NOW, terminal-builder, builder.log, clock, status, live.json, decisions, LEDGER, format, VERSIONS, Round-3.5-edge; PLAN.md; scripts/README; START; timeline.json; LESSONS; live.py; portal_watch.py, clock.py (excerpts); say.py; agents/platform.md; RESEARCH.md (grep).
- Longest to find: whether a click after T-3 is allowed; only `scripts/portal_watch.py`'s T-2 check answers it.

#### S11: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:55 `date`; re-read state/status.md, live.json, decisions.md: no answer recorded, v12 declared and active, v13.zip on the portal. Send BUILDER the message below, log it (`say.py --record builder`), write Samuel's line. I don't run live.py. Background `tester`, limit 14:57: recompute L59 a second way (field median).
- 14:56 "LIVE BOT is now v13" should wake me: check live.json. If Samuel answers, relay his exact words.
- 14:57 the T-3 line wakes me: status.md must show v13 active. Still v12: one urgent line to BUILDER ("wrong active bot: click v13"). Then mark L59, update notes/PLAN-research.md, spawn the full loop on Round 3.5's download.
- 14:59 last look at status.md. Still v12: v12 plays; record the miss and its cause.
- 15:00-15:05 round 4 starts: confirm from status.md which bot played; T-20 sync with BUILDER.

Outcome I expect: v13 is active when round 4 starts at 15:00 (otherwise v12, reported as a miss).

##### 2. What I say
Samuel: "No answer came by 14:55, so the rule's answer plays round 4: v13 (+0.7 ± 0.8 a table, above the bar for 5th; not yet double-checked). The portal still runs v12 as of 14:55; I've told BUILDER, and Dylan has to click v13 by 14:57. Nothing for you to do. If you disagree, say so before 14:57 and I'll pass on your words."

BUILDER: "Round 4, 14:55: no answer from Samuel (away since 14:44), none in state/decisions.md. The rule's answer stands: releases/v13.zip (sha256 9ab27d10e4c3, verdict L51 with heads-up; edge L59 +0.72 ± 0.80, z 0.9, bar 0.5, unverified). state/live.json and state/status.md (14:55:01) still show v12. v13.zip is already on the portal: live.py v13, Dylan clicks it, no upload, active by 14:57."

##### 3. The rule that decides
- DECISION_RULES §3, opening: "If nobody answers in time, the rule's answer plays, not 'no change'." Stated.
- §3 "Which bot plays": "outside the top 3 ... z ≥ 0.5"; "The rule's answer plays at T-5 if no human has answered (BUILDER applies it with `scripts/live.py`)". Stated.
- §4: "Only a line disputed with a reproduced counter-number blocks a switch." Stated; worked example 1 is this case.
- CLAUDE.md §3: live.json is "BUILDER only". Stated. So I prompt BUILDER rather than act: inferred.
- Conflict: §3 Uploads "When in doubt, the live bot stays active" and PLAN T-3 "after this nothing changes", against LESSONS "'No change' is not the default" and START.md "wrong active bot (tab 1, urgent) | Make the right bot active on the portal now". I followed the second pair: nothing is in doubt, and it's a click.

##### 4. What I lacked
- No rule says what RESEARCH does when BUILDER is silent at T-5, or when a human is away. This took longest to look for.
- notes/PLAN-research.md is absent: no BUILDER session id, no tester id.
- data/rounds/ and yardsticks.json are absent: I checked only L59's arithmetic and that 80.40 matches weights 1, 2, 3.
- No way to reach Dylan except through BUILDER.
- Guesses: Dylan is at the laptop; BUILDER is slow, not hung; a click is allowed after T-3; re-running L59 is worth two minutes.
- Opened: brief; CLAUDE.md; RESEARCH.md; DECISION_RULES.md; every permitted S11 file (NOW.md first, the edge file last); PLAN.md; scripts/README.md; timeline.json; START.md; LESSONS.md; BUILDER.md (T-5/T-3 lines).


### S12. The scout raises a plan challenge at T-11

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:29:05 on Sunday. Scored round 3 starts at 14:40:00.

`state/status.md`
```
# Portal status (written 14:29:01 by scripts/portal_watch.py)

Last poll 14:29:01: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v11.zip** (sha256 e03b5f19c7aa…), uploaded 14:27
Declared live bot (state/live.json): **v9** (round 2: live bot unchanged) — does NOT match the portal (fine during a practice round; must match by T-3 of a scored round)
Next on the clock: Practice 6 (Round 2.5) at 14:30

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 1 | Round 1 | 14:00 | finished · data saved | v9 | 6/20 · 13.50 ±0.28 | Fold Equity 15.80 |
| Round 1.5 | Round 1.5 | 14:10 | finished · data saved | v10 | 12/20 · 12.20 ±0.56 | 2 Curry 15.02 |
| Round 2 | Round 2 | 14:20 | finished · data saved | v9 | 7/20 · 13.20 ±0.28 | Fold Equity 15.20 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 46.20 |
| 2 | 2 Curry | 44.90 |
| 3 | River Rats | 42.30 |
| 4 | Tilt Shift | 41.80 |
| 5 | Check Mates | 40.60 |
| 6 | **avalon** | 39.90 |
| 7 | Pot Committed | 39.50 |
| 8 | Gutshot | 38.80 |
| 9 | Limp Mode | 38.10 |
| 10 | Kicker Trouble | 37.90 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:27 | v11.zip | ready |  |
| 14:07 | v10.zip | ready |  |
| 13:57 | v9.zip | ready |  |

## Warnings

- the portal runs v11.zip, the declared live bot is v9
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:29:00)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:29: minute 89 · stage **Round 2** · next: scored round 3 at 14:40 (T-11)
Live bot (state/live.json): **v9** · the portal runs: v11.zip
| Practice 6 (Round 2.5) | 14:30 | **next** |
Next steps: 14:30 (T-10 of round 3); 14:31 (T-9 of round 3); 14:32 (T-8 of round 3)
```

`state/live.json`: bot **v9**, why "round 2: live bot unchanged", declared 14:14:40, previous none.

`state/decisions.md`
```
(rounds 1 and 2: not shown)

## Round 3: which bot? (DRAFT, started 14:20:30 by BUILDER; not asked yet)
- Options: v9 (live) or v11 (challenger, design D matured; it plays the 14:30 practice).
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L38 | 14:21 | tester | verdict v11 (sha256 e03b5f19c7aa): correct; vs live v9 +0.1 ± 0.4; heads-up +0.3 ± 0.4 | +0.1 ± 0.4 | 2,000 tables + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v11-verdict.md | validated
L40 | 14:28 | scout | field trend Round 2: field folds to 3-bets of opens 49.8% ± 2.1 (Round 1: 58.9% ± 2.3); top 5 fold 44%, 4-bet 24% | −9.1 points ± 3.1 | 570 / 541 spots | analysis/field_trend.py on the first 1,000 tables | analysis/Round-2/field_trend.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v9 | 3a1f7c2 | 7c1e09a44b2d… | style A + theory refits from practice 3 | 0 failed of 48,112; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 4.8) | live (rounds 1-2) | correct; vs v7 +0.3 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor check_or_fold 9.8 in the same field (L21)
v11 | 8d02e5b | e03b5f19c7aa… | design D matured: twist-first, limp-or-shove under 15bb | 0 failed of 51,007; p99 0.24 ms; upload test 5/5 (check_or_fold 5/5, load 5.5) | challenger (round 3 window) | correct; vs live v9 +0.1 ± 0.4 (paired, 2,000 tables); heads-up +0.3 ± 0.4; floor check_or_fold 9.9 (L38)
```

`analysis/Round-2/card.md`
```
# Round 2 (scored, 4,000 tables): card written 14:27:40

**Headline: v9 scored 13.20 ±0.28, 7th of 20. Field median 12.55. 1st Fold Equity 15.20.** 0 missed decisions of 238,114.
Our 3-bets of opens: 570 in the first 1,000 tables; folded to 284 times (49.8%); 4-bet 121 times (21%); when 4-bet we folded 88%.
```

`analysis/Round-2/field_trend.md`
```
# Field trend, Round 2 (scout, written 14:28:50)

**PLAN CHALLENGE Round 2: assumption 1 (the field folds to 3-bets of our opens at about 60-70%); Round 2: 49.8% ± 2.1
(570 of our opens were 3-bet), 4.9 SE under the band's lower edge; instead: 3-bet for value only against the top 8,
call their 3-bets wider, stop opening the bottom of the button range; cost: style A's main lever (wide 3-bet
pressure, fold when re-raised) is gone against 8 of our 19 opponents.**

| Rate | Practice 4 | Round 1 | Round 2 | change (SE) |
|---|---|---|---|---|
| field folds to a 3-bet of an open | 63.1% | 58.9% ± 2.3 | 49.8% ± 2.1 | −2.9 |
| field 4-bets a 3-bet | 11% | 15% ± 1.6 | 21% ± 1.8 | +2.5 |
| top 5: fold to a 3-bet / 4-bet | 55% / 17% | 51% / 20% | 44% / 24% | |
| open-shove at 10bb or less | 43% | 41% ± 2.0 | 42% ± 2.0 | +0.4 |

Plan assumptions (DECISION_RULES §5): 1 OFF (4.9 SE); 2 holds; 3 holds; 4 holds; 5 doubtful (it follows from 1: the top
5 share a 4-bet-back style that beats wide 3-betting); 6 holds; 7 holds.
Yardstick teams between Round 1 and Round 2: 9. Fingerprint card and counters: running, due 14:31.
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 3 lines shown to the agent)
```
14:26:40 [portal] Round 2 finished: we were 7 of 20 with 13.20 (±0.28); 1st Fold Equity 15.20 · played by v9 · data: data/rounds/07-Round-2/ · health: 0 missed of 238,114 decisions, 0 restarts
14:27:00 [clock] Round 2's result and hand data land about now. This window's challenger is released (T-15) for Dylan to activate at T-12.
14:28:00 [clock] Tell Dylan the challenger's exact file to activate now (upload it if it isn't on the portal yet): it plays the practice round at 14:30. Nothing released: name the released bot to activate instead, or leave the live bot. Don't live.py it (state/live.json stays the scored-round bot).
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
14:26:41 [portal] DATA LANDED Round 2 data/rounds/07-Round-2/ (hands-first-1000.jsonl.gz, results.json; the full file follows; portal_watch is running roundcard.py and fp_train.py on it now)
14:27:00 [clock] Round 2's result and hand data land about now (DATA LANDED in your inbox; portal_watch runs the round card). Run the round loop: spawn each task on DATA LANDED, never to wait for it. Everyone records every result in notes/LEDGER.md (effect ± se, n, method, file).
14:27:38 [portal] round card: analysis/Round-2/card.md (Round 2; roundcard.py took 41 s)
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:27:10 you spawned, in one message: challenger (the round-4 challenger from the data in hand; its first line back: "plan: a shove-heavy line under 20bb"), stylist (no validated one-change line yet), platform (bug fixes).
- 14:28:05 you told Dylan: "activate v11.zip now (it's uploaded) for the 14:30 practice". Dylan 14:28:25: "done".
- 14:29:00 SendMessage from RESEARCH: "PLAN CHALLENGE Round 2 (scout, analysis/Round-2/field_trend.md, L40): the field folded to 3-bets of our opens 49.8% ± 2.1 in Round 2 (570 spots), against the plan's 60-70% (assumption 1, 4.9 SE off); the top 5 fold 44% and 4-bet 24%. Scout's alternative: 3-bet for value only against the top 8, call their 3-bets wider, drop the bottom of the button opens."
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:26:50 you spawned, in one message: scout (field trend first, then the fingerprint card), analyst x3 (winners, leaks, the biggest opponent), tester (verify the card's headline; the numbers for the T-9 decision).
- 14:28:55 scout reported, first line: "PLAN CHALLENGE Round 2: assumption 1 (the field folds to 3-bets of our opens at about 60-70%); 49.8% ± 2.1, 570 spots, 4.9 SE under the band; instead: 3-bet for value only against the top 8, call their 3-bets wider, stop opening the bottom of the button range; cost: style A's main lever is gone against 8 of 19 opponents. File: analysis/Round-2/field_trend.md, L40. Fingerprint card and counters due 14:31."
- The analysts and the tester have not reported yet.
- Samuel is at his laptop; his last message, 14:22: "round 2 looked ok".
- You have sent BUILDER nothing since the T-20 sync at 14:20:40.
```

#### S12: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:29 Check the claim in `analysis/Round-2/card.md` (284/570: holds). Tell Dylan. SendMessage the running challenger: park the shove-under-20bb plan; build scout's alternative for the 14:50 practice, packed and upload-tested by 14:44. SendMessage the stylist: the same three pieces as separate on/off settings on v9, for round 4. Message RESEARCH.
- 14:30 Confirm in `state/status.md` that Practice 6 started on v11.
- 14:31 Dylan: "click v9 active now"; confirm it. Add my view to RESEARCH's challenge entry in `state/decisions.md` (never a second entry).
- 14:32 Write and ask the round-3 question, deadline 14:35. No `one-change Round-2` LEDGER line: no new change in round 3.
- 14:34 Practice result and RESEARCH's answer in; platform re-tests the pick with no time bank.
- 14:35 No clear answer: `live.py` the rule's answer.
- 14:37 If v11, Dylan clicks it; confirm status.md matches live.json.

Outcome I expect: v9 active at 14:40 (v11 only if its practice edge reaches z ≥ 0.5, about +0.4 field-adjusted); no untested change plays; the counter-style is building for the 14:50 practice.

##### 2. What I say
Dylan: "Plan challenge from RESEARCH; the round card confirms it. When we re-raise an opener the field now folds only 50% (284 of 570 in round 2, ±2; 59% in round 1; the plan assumed 60-70%). The top 5 fold 44% and re-raise back 24%, and then we fold 88%. So v9's main weapon is paying the top teams (not yet re-run by the tester). I've switched the challenger to the counter (re-raise only for value against the top 8, call their re-raises wider, fewer button opens) for the 14:50 practice. It can't be tested before round 3, so round 3 is v9 or v11 by the usual rule; I ask you at 14:32. You: nothing right now."

RESEARCH: "Round-2 PLAN CHALLENGE: challenger builds scout's alternative for the 14:50 practice, packed 14:44. Nothing from it plays round 3 without a one-change Round-2 line in notes/LEDGER.md by 14:32 and a tester verdict with heads-up by 14:36. Need: the top-8 team names and the counters.json path. field_trend.md says '570 of our opens were 3-bet', card.md says 570 of our 3-bets: which?"

##### 3. The rule that decides
- DECISION_RULES §3 "Plan challenges": "By default BUILDER has `challenger` build the alternative and the next practice round judges it. A challenge never waits for the next scheduled step, and never skips a hard rule or a test." Stated. That "next practice" is 14:50, not 14:30: inferred.
- Conflict. §4: "A leak seen in two rounds' data in the same direction ... ship its fix." Against §3's cut-off row "T-8: one-change proposal recorded | No new-data change in the live bot" and §2.1 "only with a `tester` verdict that includes a heads-up run". I followed the second: L40 is `proposed`; seven minutes can't build and test a zip.
- Round 3: "outside the top 3 ... z ≥ **0.5**". Stated; +0.4 inferred from SE ≥ 0.7.

##### 4. What I lacked
- Missing: `notes/PLAN-builder.md` (agent ids); RESEARCH's challenge entry; the top-8 names; whether v9 can recognise teams.
- Guesses: redirecting the challenger rather than adding a second; the +0.4 threshold; "570" as our 3-bets of their opens; v9 likelier for round 3.
- Opened: brief; CLAUDE.md, BUILDER.md, DECISION_RULES.md; every permitted scenario file; PLAN.md, scripts/README.md.
- Longest: whether a plan challenge's fix may enter the live bot the same window. No passage says.

#### S12: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:29 Check scout's number against `analysis/Round-2/card.md` (284 of 570 = 49.8%, SE 2.1: matches). Tell Samuel. Append ONE entry "PLAN CHALLENGE Round 2" to `state/decisions.md` (default: challenger builds it, the 14:50 practice judges it). SendMessage BUILDER, then `say.py --record`. Tell tester: re-count L40 from the raw hands first.
- 14:30 T-10: v11 plays the practice; data cut-off met.
- 14:31 Send BUILDER the round-3 threshold.
- 14:32 Analysts due: record `one-change Round-2` in the LEDGER and send it; nothing landed means no new-data change. Check `state/status.md` shows v9 active again.
- 14:33 Round 2.5 lands: tester's edge, final answer to BUILDER at once (none by 14:34: v9); relay Samuel's exact words.
- 14:37 Confirm the active bot equals `state/live.json`.

Outcome I expect: v9 active at 14:40 (v11 only if its practice edge reaches z ≥ 0.5); the challenge recorded once, both humans told, the counter-style building for the 14:50 practice.

##### 2. What I say
Samuel: "Plan challenge: we assumed opponents fold to our re-raises 60-70% of the time; in round 2 they folded 49.8% (±2.1; round 1: 58.9%) and raised back 21%, so v9's main weapon is gone against the best 8 teams. We'd re-raise them only with strong hands and call their re-raises wider; that can't be tested before 14:40, so the challenger builds it for the 14:50 practice. Unverified until tester's re-count (it matches the round card). Round 3: v9 or v11 as usual; BUILDER asks at 14:32. Nothing from you right now."

BUILDER, now: "PLAN CHALLENGE Round 2: assumption 1 off by 4.9 SE. The field folds to our 3-bets 49.8% ± 2.1 (284 of 570; Round 1 58.9%), 4-bets 21%; we fold 88% to 4-bets. Instead: value-only 3-bets against the top 8, call their 3-bets wider, drop the bottom of the button opens. Unverified (L40; tester re-counting). File: analysis/Round-2/field_trend.md. One entry in state/decisions.md: add your view there. Default: challenger builds it now, released by 14:45, plays the 14:50 practice."

BUILDER, 14:31: "RECOMMENDATION round 3 (threshold): 6th, 2.40 behind 3rd, so z ≥ 0.5; SE 0.7; edge ≥ +0.35. releases/v11.zip (verdict L38, heads-up included) plays if its margin over the yardsticks in Round 2.5 beats v9's Round 2 margin by 0.35; under 4 yardsticks, if v11 ≥ practice median + 1.00. Otherwise releases/v9.zip. No result by 14:34: v9."

##### 3. The rule that decides
- `prompts/RESEARCH.md`, "Plan challenges": "Add ONE entry to `state/decisions.md`". Stated.
- `DECISION_RULES.md` §3, "Plan challenges": "A challenge never waits for the next scheduled step". Stated.
- §4: "Unverified is not wrong." Stated.
- §3, "Which bot plays": "z ≥ **0.5**", "at least 0.7". Stated; +0.35 and median + 1.00 inferred.
- Conflict: RESEARCH.md says "deadline: the next practice" (14:30, v11 already active); §3 "The challenger": "targets the next window". I followed the second: nothing gets built and tested in 55 seconds. Inferred.

##### 4. What I lacked
- Lacked: the yardsticks' scores; which teams are the "top 8"; whether 49.8% is field-wide or only replies to our 3-bets; `notes/PLAN-research.md`.
- Guesses: edge SE 0.7; no pooling with v10; no v9 fix testable by 14:36; "next practice" means 14:50; v9 likelier.
- Opened: brief; CLAUDE.md, RESEARCH.md, DECISION_RULES.md, PLAN.md, scripts/README.md; every permitted scenario file; LESSONS.md, scout.md, tester.md.
- Longest: what "the next practice" means at T-11.


### S13. A 5-minute cooldown and two uploads wanted

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:54:20 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:54:16 by scripts/portal_watch.py)

Last poll 14:54:16: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v12.zip** (sha256 41d9a6c2f0b8…), uploaded 14:36
Declared live bot (state/live.json): **v14** (round 4: v12 + F1 + F2 (Dylan and Samuel chose it)) — does NOT match the portal (fine during a practice round; must match by T-3 of a scored round)
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 5/20 · 13.50 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 8/20 · 13.60 ±0.56 | 2 Curry 15.05 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | 2 Curry | 86.00 |
| 3 | Tilt Shift | 82.40 |
| 4 | River Rats | 81.70 |
| 5 | **avalon** | 80.40 |
| 6 | Check Mates | 80.10 |
| 7 | Gutshot | 78.80 |
| 8 | Pot Committed | 77.90 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- the portal runs v12.zip, the declared live bot is v14
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:54:15)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:54: minute 114 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-6)
Live bot (state/live.json): **v14** · the portal runs: v12.zip
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:55 (T-5 of round 4); 14:57 (T-3 of round 4)
```

`state/live.json`: bot **v14**, why "round 4: v12 + F1 + F2 (Dylan and Samuel chose it)", declared 14:53:55, previous v12.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? v12 (live), v13 (challenger) or v14 (v12 + F1 + F2)
- Asked 14:52:15 by BUILDER. Deadline 14:55:00.
- Evidence: v13's field-adjusted edge +0.30 ± 0.80 (z 0.38); we are 5th (bar 0.5): the challenger does not clear it. F1 (z 1.3, persistent) and F2 (z 1.1) are validated; v14 has tester's verdict with a heads-up run (L58).
- The rule's answer: v14 (the live bot with this window's changes).
- Dylan, 14:53:10: "yes v14". Samuel (relayed 14:53:30): "agree, v14".
- 14:53:55 BUILDER: live.py v14.
- Outcome: (open: v14 not uploaded yet)
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L52 | 14:46 | analyst | one-change Round 3 (F1): call 3-bet shoves wider at 20bb or less; seen in Round 2 and Round 3 (persistent) | +0.35 ± 0.27 (z 1.3) | 902 spots over two rounds | replay on Round 2 + Round 3 hands | analysis/Round-3/leaks.md | validated (tester 14:49, recount +0.33)
L55 | 14:47 | analyst | one-change Round 3 (F2): stop min-raise-folding against Gutshot seats (they 3-bet 31% of min-raises) | +0.30 ± 0.27 (z 1.1) | 644 spots | replay on Round 3 hands | analysis/Round-3/opponent_gutshot.md | validated (tester 14:50, recount +0.29)
L58 | 14:51 | tester | verdict v14 (sha256 c58f3e7712d0): correct; vs live v12 +0.5 ± 0.3; heads-up +0.2 ± 0.4; F1 fired 412, F2 fired 1,038; F1's call rate 38% vs target 40% | +0.5 ± 0.3 | 2,000 tables + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v14-verdict.md | validated
L59 | 14:52 | tester | field-adjusted edge v13 (Round 3.5) vs v12 (Round 3), 7 yardsticks | +0.30 ± 0.80 (z 0.38) | 1,000 + 4,000 tables | DECISION_RULES §3 formula | rig/out/Round-3.5-edge.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
v14 | 2c7be80 | c58f3e7712d0… | v12 + F1 (call 3-bet shoves wider at 20bb or less) + F2 (no min-raise-fold vs Gutshot seats), each behind a setting, fired 412 and 1,038 times in 2,000 tables | 0 failed of 50,904; p99 0.21 ms; upload test 5/5 (check_or_fold 5/5, load 5.7) | live candidate (round 4) | correct; vs live v12 +0.5 ± 0.3 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.8 (L58)
v15 | 77ab0e3 | 0d4e8b6a91f7… | NEXT WINDOW's challenger: design D2 (rewrite of the postflop tree on D's engine) | 0 failed of 50,020; p99 0.27 ms; upload test 5/5 (check_or_fold 5/5, load 5.6) | challenger (round 5 window) | pending (tester started 14:54)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 3 lines shown to the agent)
```
14:52:00 [clock] DECIDE now with the pre-registered rule (strategy/DECISION_RULES.md §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes that cleared the bar (usually one to three; each independent, behind its own setting). Ask the 'Which bot?' question for scored round 4 now: write it in state/decisions.md and ask in plain words in your reply (both bots' numbers, the rule's answer as a released file, deadline T-5 = 14:55).
14:53:55 [builder] LIVE BOT is now v14 (round 4: v12 + F1 + F2 (Dylan and Samuel chose it)) — Dylan: make it active on the portal (upload releases/v14.zip if it isn't there).
14:54:00 [clock] Test the chosen bot under upload-test conditions (no time bank).
```

`inbox/research.log` (last 2 of 2 lines shown to the agent)
```
14:52:00 [clock] Decision time for scored round 4 (15:00): your recommendation is due to BUILDER now; relay Samuel's answer to BUILDER in his exact words. The practice round's download lands near now: before the decision only tester's field-adjusted edge matters; the full analysis loop on it runs after T-3.
14:53:55 [builder] LIVE BOT is now v14 (round 4: v12 + F1 + F2 (Dylan and Samuel chose it)) — Dylan: make it active on the portal (upload releases/v14.zip if it isn't there).
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:47:50 you told Dylan: "upload releases/v13.zip and make it active for the 14:50 practice". Dylan 14:48:10: "uploaded 14:47:55, active".
- 14:51:20 Dylan: "v12 is back".
- 14:53:40 platform reported: "v14 passed the no-time-bank upload test, 5/5, load 5.9, check_or_fold 5/5 in the same minute".
- 14:53:55 you ran live.py v14 and told Dylan: "round 4 plays v14: upload releases/v14.zip and make it active by 14:57".
- 14:54:05 platform reported: "releases/v15.zip released too (next window's challenger, design D2), VERSIONS line written, upload test 5/5". You sent RESEARCH "RELEASED v15 0d4e8b6a91f7 D2, next window's challenger" at 14:54:08.
- 14:54:15 Dylan: "uploading v14 now. platform says v15 is out too, I'll upload both so v15 is already sitting there for the next practice. which one first?"
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:53:25 Samuel: "agree, v14" (relayed to BUILDER 14:53:30).
- 14:54:08 BUILDER sent: "RELEASED v15 0d4e8b6a91f7 D2, next window's challenger". You spawned a fresh tester on v15 at 14:54:12.
- 14:54:15 Samuel: "Dylan wants to upload v14 and v15 back to back so v15 is ready early. any problem with that?"
```

#### S13: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:54 Re-read `state/live.json` (v14) and `state/status.md` (portal runs v12; cooldown 300 s; last upload 14:47:55, so one upload is free). Answer Dylan: v14 only. v15 first would lock v14 out until about 14:59:30, past T-3.
- 14:55 T-5: both humans answered v14, nothing to apply. Spawn a fresh `bughunter` on v15 (background, 8 minutes).
- 14:56 T-4 cut-off: v14 is released, upload-tested, with verdict L58 (heads-up included): met. Check status.md for v14.zip "ready". If rejected: v12 stays active, `live.py v12 "v14 rejected"`, tell both humans, nothing else is uploaded.
- 14:57 T-3: status.md must show v14.zip (c58f3e7712d0…) active; if uploaded but not active: "click v14 active now". Record the outcome in `state/decisions.md`. Nothing changes after this.
- 15:00 Confirm round 4 started on v14. T-20 of round 5: sync with RESEARCH; rounds 5-6 are the last two, so the bar is z ≥ 0.
- 15:01 Tell Dylan: "upload releases/v15.zip now; don't make it active until I say (15:08)".

Outcome I expect: v14 is active when round 4 starts at 15:00 (v12 only if the portal rejects v14); v15 is on the portal by about 15:02.

##### 2. What I say
To Dylan: "v14 first, and only v14 for now. The portal allows one upload every 5 minutes: if v15 goes up, v14 can't go up until about 14:59:30, after the 14:57 deadline, and round 4 (weight 4) could play v12. Upload releases/v14.zip and make it active by 14:57; I'll confirm it. v15 waits until round 4 has started: I'll tell you at about 15:01, in time for the 15:10 practice."

To RESEARCH: nothing now. At 15:00, the sync: "Round 4 plays v14 (portal confirmed). Rounds 5 and 6 are the last two: the challenger bar is z ≥ 0. I need v15's verdict with a heads-up run and the yardstick threshold by 15:11; v15 (D2) plays the 15:10 practice."

##### 3. The rule that decides
- `DECISION_RULES.md` §3 "Uploads": "Never let a cooldown leave the chosen bot unuploaded at T-3." Stated.
- `notes/format.md`: "Uploads: one every 5 minutes"; status.md: "upload cooldown per the portal: 300 s". Stated; 14:59:30 is inferred.
- `prompts/BUILDER.md` "Every window", T-3: "After this nothing changes." Stated; so no v15 upload from 14:57 to 15:00 (inferred).
- `prompts/BUILDER.md` "Minute 0" step 5: "spawn a fresh `bughunter` on it at once"; T-20: "apply the last-rounds bar". Stated.
- Two ways: `PLAN.md` §3 T-12 "he uploads it if it isn't on the portal yet" (15:08) against Dylan's wish to have v15 up early. I chose 15:01 (inferred): a rejection at 15:08 could not be re-uploaded before 15:10, and `CLAUDE.md` §6 says "The plan is a default, not a mandate". Activation stays at T-12.

##### 4. What I lacked
- Whether an upload becomes active by itself, and whether a rejected upload starts the cooldown. Guesses: uploading and activating are separate; the cooldown runs from the last upload's time; Dylan had clicked nothing at 14:54:15.
- Whether v14 had a `bughunter` pass; `notes/PLAN-builder.md` is absent.
- Opened, in order: brief; CLAUDE.md; BUILDER.md; scenario NOW.md, terminal-builder.md, builder.log, clock.md, status.md, live.json, decisions.md, format.md, LEDGER.md, VERSIONS.md; DECISION_RULES.md; PLAN.md; scripts/README.md; LESSONS.md; START.md; portal_watch.py (grep); timeline.json.
- Longest to find: the cooldown sentence, last in the "Uploads" paragraph; nothing covers a third upload in one window.

#### S13: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:54 Answer Samuel; SendMessage BUILDER (below); `say.py --record builder`.
- 14:55 Read `state/status.md`: is v14.zip uploaded, "ready", active?
- 14:56 Same check. Nothing else goes up.
- 14:57 (T-3) v14 must show active; if not, tell Samuel and BUILDER "wrong active bot: v12 plays unless v14 is clicked active". Write `notes/PLAN-research.md` (v14 plays; v15's tester; verdict owed to BUILDER). Spawn the full analysis loop on Round 3.5.
- 14:58-14:59 Hands off the portal.
- 15:00 Round 4 starts (T-20 of round 5): confirm "played by v14" in status.md. Sync with BUILDER in 3 lines; rounds 5-6 are the last two, so v15's bar is z ≥ 0.
- 15:01 Tell BUILDER v15 can go up now (cooldown clear, round 4 snapshot taken).
- 15:02-15:04 Check v15 shows "ready"; pass the tester's v15 verdict to BUILDER when it lands.

Outcome I expect: v14 is active when round 4 starts at 15:00 (v12 if the upload is rejected); v15 is on the portal by about 15:02, eight minutes before its practice.

##### 2. What I say
To Samuel: "Yes, there's a problem: they can't go back to back. The portal allows one upload every 5 minutes, so exactly one fits before round 4 at 15:00, and it has to be v14, now, then made active. If v15 went first, v14 would be locked out until about 15:00 and v12 would play without the two fixes. If v15 went second at 14:59 it might become the active bot for a round worth 4 of 21, and its test only started at 14:54. Waiting costs nothing: v15 isn't needed until the 15:10 practice, so Dylan uploads it right after 15:00. I've told BUILDER; nothing for you to do. I'll confirm v14 is active by 14:57."

To BUILDER: "UPLOAD ORDER, round 4. Dylan plans v14 then v15 back to back: don't. Cooldown 300 s (state/status.md, notes/format.md); last upload v13 14:47, so one upload fits before 15:00. It is releases/v14.zip (c58f3e7712d0), now, then made active; status.md 14:54:16 shows v12 active, no v14 uploaded. releases/v15.zip (0d4e8b6a91f7) only after status.md shows Round 4 started: no tester verdict yet (started 14:54:12)."

##### 3. The rule that decides
- `notes/format.md`: "Uploads: one every 5 minutes"; status.md: "upload cooldown per the portal: 300 s". Stated.
- DECISION_RULES §3 Uploads: "Never let a cooldown leave the chosen bot unuploaded at T-3." Stated.
- DECISION_RULES §2.1: "A bot plays a scored round only with a `tester` verdict that includes a heads-up run." Stated; that v15 must wait until after 15:00 is inferred.
- Pointing the other way: §3 "Any bot that is legal and fast ... may play" a practice, so v15 is uploadable. I followed the hard rule until 15:00, this one after.
- CLAUDE.md §1: BUILDER owns "what Dylan uploads", so I tell BUILDER, not Dylan. Inferred.

##### 4. What I lacked
- Whether an upload becomes active by itself: nowhere in the bundle. Guessed it might.
- v13's upload second, and whether a refused attempt restarts the cooldown. Guessed it cleared at 14:52.
- Whether BUILDER already said this.
- No rule on uploading a challenger before T-12; guessed fine.
- `notes/PLAN-research.md` is absent.

Opened: brief; CLAUDE.md; prompts/RESEARCH.md; DECISION_RULES.md; PLAN.md; scripts/README.md; NOW.md; terminal-research.md; research.log; live.json; status.md; clock.md; decisions.md; format.md; LEDGER.md; VERSIONS.md; START.md; LESSONS.md; prompts/BUILDER.md; greps of portal_watch.py, timeline.json.

Longest: the search for auto-activation, which found nothing.


### S14. The kit's do-nothing bot scores as well as ours

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 13:38:10 on Sunday (minute 38 of the build hour). Practice 3 starts at 13:40:00; scored round 1 at 14:00:00.

`state/status.md`
```
# Portal status (written 13:38:06 by scripts/portal_watch.py)

Last poll 13:38:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v5.zip** (sha256 5b1c77e09a3f…), uploaded 13:36
Declared live bot (state/live.json): **v5** (practice 3 pick: design D, not measured yet) — MATCHES the portal
Next on the clock: Practice 3 at 13:40

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| Practice 1 | Practice 1 | 13:20 | finished · data saved | v2 | 9/20 · 12.90 ±0.56 | Check Mates 15.10 |
| Practice 2 | Practice 2 | 13:30 | finished · data saved | v3 | 11/20 · 12.40 ±0.56 | Fold Equity 15.30 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 13:36 | v5.zip | ready |  |
| 13:27 | v3.zip | ready |  |
| 13:17 | v2.zip | ready |  |
| 13:09 | v1.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 13:38:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 13:38: minute 38 · stage **Practice 2** · next: scored round 1 at 14:00 (T-22)
Live bot (state/live.json): **v5** · the portal runs: v5.zip
| Practice 3 | 13:40 | **next** |
Next steps: 13:40 (b40); 13:47 (b47); 13:50 (b50)
```

`state/live.json`: bot **v5**, why "practice 3 pick: design D, not measured yet", declared 13:36:20, previous v3.

`notes/LEDGER.md` (the lines shown to the agents)
```
L11 | 13:26 | analyst | Practice 1 defaults check: 6 of 20 teams ran the kit's check_or_fold example unchanged (0 raises, 0 voluntary calls in 1,000 tables); they averaged 13.90 (range 12.80 to 15.10; Check Mates was 1st of 20 with 15.10); our v2 (style A) scored 12.90 | +1.0 for the kit example over v2, ± 0.6 | 1,000 tables | results.json + fingerprints | analysis/Practice-1/card.md | proposed
L14 | 13:36 | tester | verdict v4 (style A on the newest tables, sha256 19e0c4d2aa71): correct; heads-up +0.3 ± 0.4 vs v1; cloned field (Modal, 2,000 tables, 8 players, sparring mix refit to Practice 1): v4 13.6 ± 0.45; the kit's check_or_fold floor in the same field 13.4 ± 0.45; load 5.2 | +0.2 ± 0.6 over the floor | 2,000 tables | paired, identical deals | rig/out/v4-verdict.md | validated
L19 | 13:37 | analyst | Practice 2 defaults check: 3 teams still play the kit's check_or_fold example by fingerprint (Kicker Trouble 14.10, 5th; Cold Four 13.60, 7th; Limp Mode 13.20, 8th): mean 13.63; field median 12.45; our v3 (style C) 12.40, 11th. Median table: 5 of 8 players are out by hand 34; 41% of first-in actions are all-in | +1.2 for the kit example over v3, ± 0.65 | 1,000 tables | results.json + fingerprints | analysis/Practice-2/card.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v1 | 0c2e1aa | 88d1… | minimal legal bot | 0 failed; upload test 5/5 | first legal bot | correct; heads-up run done (L7)
v2 | 41f07b9 | a3e9… | style A (wide pressure), first tables | 0 failed; upload test 5/5 | practice 1 | correct; heads-up +0.2 ± 0.4 (L9)
v3 | 9d77c02 | 6f12… | style C (tight) | 0 failed; upload test 5/5 | practice 2 | correct; heads-up +0.1 ± 0.4 (L12)
v4 | 6a0be55 | 19e0c4d2aa71… | style A rebuilt on all of theory's tables | 0 failed of 48,300; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 5.2) | candidate | correct; heads-up +0.3 ± 0.4; cloned field 13.6 ± 0.45 vs check_or_fold floor 13.4 ± 0.45 (L14)
v5 | e81f3c4 | 5b1c77e09a3f… | design D (clean room): twist-first, limp-or-shove under 15bb | 0 failed of 47,912; p99 0.22 ms; upload test 5/5 (check_or_fold 5/5, load 5.5) | practice 3 | pending (tester started 13:36)
```

`analysis/Practice-2/card.md`
```
# Practice 2 (1,000 tables): card written 13:36:40

**Headline: v3 (style C) scored 12.40 ±0.56, 11th of 20. Field median 12.45. 1st Fold Equity 15.30.** 0 missed decisions of 44,870.
**Defaults check:** three teams never raised and never put chips in voluntarily in 1,000 tables (the kit's check_or_fold example, by fingerprint): Kicker Trouble 14.10 (5th), Cold Four 13.60 (7th), Limp Mode 13.20 (8th). In Practice 1 six teams did, averaging 13.90.
The field busts itself: at the median table 5 of 8 players are out by hand 34; 41% of first-in actions at any stack depth are all-in.
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 3 lines shown to the agent)
```
13:35:50 [portal] Practice 2 finished: we were 11 of 20 with 12.40 (±0.56); 1st Fold Equity 15.30 · played by v3 · data: data/rounds/02-Practice-2/ · health: 0 missed of 44,870 decisions, 0 restarts
13:36:20 [builder] LIVE BOT is now v5 (practice 3 pick: design D, not measured yet) — Dylan: make it active on the portal (upload releases/v5.zip if it isn't there).
13:37:00 [clock] Practice round 3 starts in 3 minutes (13:40): the bot you declared for it (live.py) must be uploaded and active now.
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
13:35:51 [portal] DATA LANDED Practice 2 data/rounds/02-Practice-2/ (hands-first-1000.jsonl.gz, results.json; portal_watch is running roundcard.py and fp_train.py on it now)
13:36:20 [builder] LIVE BOT is now v5 (practice 3 pick: design D, not measured yet) — Dylan: make it active on the portal (upload releases/v5.zip if it isn't there).
13:36:42 [portal] round card: analysis/Practice-2/card.md (Practice 2; roundcard.py took 38 s)
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 13:36:25 you told Dylan: "upload releases/v5.zip (design D) and make it active for the 13:40 practice". Dylan 13:36:50: "uploaded, active".
- 13:37:30 SendMessage from RESEARCH: "tester's verdict on v4 (L14): correct, heads-up +0.3 ± 0.4. In the cloned field v4 scored 13.6 ± 0.45 and the kit's check_or_fold example scored 13.4 ± 0.45."
- 13:37:50 SendMessage from RESEARCH: "Practice 2 card (analysis/Practice-2/card.md, L19): three teams still running the kit's check_or_fold example placed 5th, 7th and 8th (mean 13.63); our style C was 11th with 12.40. In Practice 1 six such teams averaged 13.90 against our style A's 12.90 (L11)."
- Subagents: platform (building in theory's refits), stylist x2 (A and B kept current; B is v6, due 13:44), challenger (design D shipped as v5; now idle).
- Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 13:36:10 tester reported v4's verdict (L14): correct; heads-up +0.3 ± 0.4; cloned field: v4 13.6 ± 0.45, the kit's check_or_fold floor 13.4 ± 0.45.
- 13:37:20 analyst reported the Practice 2 card (L19): three teams on the kit's check_or_fold example placed 5th, 7th, 8th (mean 13.63); our style C 12.40, 11th; in Practice 1 six such teams averaged 13.90 against our style A's 12.90 (L11).
- 13:37:30 and 13:37:50: you sent BUILDER both facts, one message each.
- scout: first field trend (practices 1-2) due 13:42. theory: second wave running.
- Samuel is at his laptop; his last message, 13:31: "how did practice 1 go for A?"
```

#### S14: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 13:38 Both scripts fresh; the portal runs v5 = live.json. Practice 3 stays v5 (no upload possible before 13:41:50). L11, L19 and the Practice-2 card show the kit's do-nothing bot beating our A and C on the real field twice: a PLAN CHALLENGE. Tell Dylan and RESEARCH (SendMessage, `say.py --record`).
- 13:39 Continue the idle `challenger`: `candidates/challenger-1/`, platform settings only: fold-first while 5+ players remain, play to win at 4 or fewer. Checked by 13:44; if late, a smaller version. `platform` releases it as v7 by 13:46. B's stylist: v6 finishes, no upload before 13:50.
- 13:40 b40 arrives; confirm v5 plays practice 3.
- 13:41-43 Add my view to RESEARCH's `state/decisions.md` entry; write the missing `notes/PLAN-builder.md`.
- 13:44 Check both reports; "RELEASED v6" to RESEARCH.
- 13:46 v7 released, upload test 5/5: `live.py v7 "practice 4 pick: plan challenge"`, Dylan uploads, RELEASED to RESEARCH, bughunter. Not by 13:47: declare v6 instead.
- 13:48 Confirm status.md MATCHES.

Outcome I expect: practice 3 plays v5; by 13:48 v7 (fold-first), else v6, is active for practice 4. Round 1's bot is still open (declared 13:50, asked 13:52).

##### 2. What I say
Dylan: "Nothing to click now: v5 is active for 13:40. Plan challenge: on the real field the kit's do-nothing bot outscored both our styles, 13.9 against A's 12.9 and 13.6 against C's 12.4; not yet re-run by the tester. The field busts itself: 5 of 8 are out by hand 34. The challenger is building a fold-first bot that plays to win with 4 left; it takes the 13:50 practice instead of style B unless you say otherwise. Upload nothing until I name one file at about 13:46. Round 1 isn't decided: I ask at 13:52."

RESEARCH: "PLAN CHALLENGE Practice 2 (base style, assumption 5): check_or_fold beat us on the real field twice: L11 +1.0 ± 0.6 over v2, L19 +1.2 ± 0.65 over v3, both 'proposed'. Instead: fold-first-then-win (notes/pre/contrarian.md design 3), candidates/challenger-1/, v7 by 13:46 for practice 4. Record it once in state/decisions.md and tell Samuel; I add my view."
"Need by 13:50: tester validates or disputes L11 and L19; a fresh tester on v7 when I send RELEASED."

##### 3. The rule that decides
- LESSONS.md, speedrun: "if folding is that strong on the real field, it's a PLAN CHALLENGE." Stated.
- DECISION_RULES §3, Plan challenges: "By default BUILDER has `challenger` build the alternative and the next practice round judges it. A challenge never waits". Stated.
- Against: PLAN §5 b40, practice 4 is "the leader, or its closest unmeasured rival" (B); buildplan.md: "the last 15 minutes are for practice picks, not a new design". I followed the challenge: DECISION_RULES "overrides anything older or vaguer".
- One upload slot: format.md "one every 5 minutes", status.md "uploaded 13:36". Inferred.
- contrarian.md §3: "Practice 1 will look like design 3's field whatever the Finals turn into": so round 1 isn't switched blind. Inferred.

##### 4. What I lacked
Missing: PLAN-builder.md (agent ids), decisions.md, bot/INTERFACE.md (can settings fold-first?), whether RESEARCH already raised this.
Guesses: a 5-7 minute build; "v7"; v6 over v4 as fallback.
Opened: CLAUDE.md, BUILDER.md, DECISION_RULES.md, scenario files, PLAN.md, scripts/README.md, LESSONS.md, tester.md, RESEARCH.md, contrarian.md, timeline.json, challenger.md, field.md, buildplan.md.
Longest to find: the LESSONS floor-bot line; BUILDER.md and DECISION_RULES lack it.

#### S14: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 13:38 Answer Samuel and raise the PLAN CHALLENGE. Create `state/decisions.md` with one entry: "PLAN CHALLENGE Practice 2: the kit's do-nothing bot beats our styles"; default "the challenger builds it and the next practice judges it"; deadline Practice 4 (declared by 13:47). SendMessage BUILDER; `say.py --record`.
- 13:39 Spawn `tester` (background, 4 minutes): re-count L11 and L19 from the raw hand files; mark them validated or disputed.
- 13:40 b40 arrives: spawn `tester` (ranking of A, C, D, the floor as a row) and `analyst` (winners lens: do the top teams survive first?), together. Check `state/status.md`: v5 played Practice 3.
- 13:42 Scout's field trend lands: open it; ask for players left at hand 40 if missing.
- 13:44 Re-count back: one line to BUILDER; update the entry.
- 13:45 Practice 3 DATA LANDED: continue both tasks.
- 13:47 Read `state/live.json` and VERSIONS.md: a survive-first release gets a fresh `tester` (heads-up run). Update `notes/PLAN-research.md`.

Outcome I expect: v5 (design D) is active when Practice 3 starts at 13:40, untouched; by 13:48 one challenge entry exists, L11/L19 are checked, and survive-first is being built for Practice 4.

##### 2. What I say
Samuel: "A scored 12.90, 9th of 20. Plan challenge: the kit's do-nothing example beat us in both practices (13.90 against A's 12.90, 13.63 against C's 12.40; together +1.1 ± 0.45, unverified until tester's re-count at 13:44). The plan assumed our styles beat this field; this field busts itself (5 of 8 out by hand 34). Instead: a bot that folds early and plays to win with 4 or fewer left plays practice 4 at 13:50 and can be round 1's challenger. Cost: that practice slot. D still plays practice 3. Nothing for you now."

BUILDER: "PLAN CHALLENGE Practice 2 (one entry, state/decisions.md; add your view there): check_or_fold beats our styles on the real field twice (L11 +1.0, L19 +1.2; pooled +1.1 ± 0.45, unverified, re-count due 13:44). Default: challenger builds survive-first (notes/pre/contrarian.md design 3; smallest version a setting on v4) for practice 4, declared by 13:47; uploads reopen about 13:41. Practice 3 stays v5."

##### 3. The rule that decides
- `strategy/LESSONS.md`, speedrun: "if folding is that strong on the real field, it's a PLAN CHALLENGE." Stated.
- `prompts/RESEARCH.md`, "Plan challenges": "You own it"; "ONE entry". Stated.
- `DECISION_RULES.md` §3: "the next practice round judges it. A challenge never waits for the next scheduled step". Stated; "next" meaning Practice 4 is inferred (v5 active, 300 s cooldown).
- §4: "two rounds' data in the same direction"; "Unverified is not wrong." Stated; pooling to 2.5 SE inferred.
- Against: `notes/pre/contrarian.md` §3 "Practice 1 will look like design 3's field whatever the Finals turn into"; §5 assumption 7 "differences under 2.0 ... are noise". I followed the challenge: practice 2 was the re-read and held; only a practice slot is spent.

##### 4. What I lacked
- `notes/PLAN-research.md` (agent ids, Monitor state) and `data/`: absent, so nothing re-run.
- No §5 assumption names the floor; no rule on uploading the kit's own example.
- Guesses: Samuel's 13:31 question was unanswered; uploads reopen 13:41; survive-first is buildable by 13:47; the pooled SE.
- Opened: brief, CLAUDE.md, RESEARCH.md, DECISION_RULES.md, PLAN.md, scripts/README.md, scenario files, timeline.json, LESSONS.md, contrarian.md, field.md, BUILDER.md, tester.md, testplan.md, challenger_bar.md.
- Longest to find: contrarian.md's caution.


### S15. Points per place that are not 50/30/20

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 13:03:20 on Sunday (minute 3 of the build hour). Practice 1 starts at 13:20:00; scored round 1 at 14:00:00.

`state/status.md`
```
# Portal status (written 13:03:16 by scripts/portal_watch.py)

Last poll 13:03:16: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: NONE (a round starting now is forfeited)**
Declared live bot (state/live.json): none yet
Next on the clock: Practice 1 at 13:20

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|

## Standings (top 10)

| # | Team | Total |
|---|---|---|

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|

## Warnings

- NO active bot on the portal
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 13:03:15)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 13:03: minute 3 · stage **Build** · next: scored round 1 at 14:00 (T-57)
Live bot (state/live.json): **none declared** · the portal runs: NO bot
| Practice 1 | 13:20 | **next** |
Next steps: 13:10 (b10); 13:15 (b15); 13:17 (b17)
```

`state/live.json`: does not exist.

`notes/LEDGER.md` (the lines shown to the agents)
```
(empty: no lines yet)
```

`releases/VERSIONS.md` (the lines shown)
```
(empty: no lines yet)
```

`notes/format.md`
```
# Format page (as Dylan pasted it at 13:03; saved by BUILDER)

- Table: 8 players, 100 big blinds each; blinds rise every 10 hands; a match ends when one player is left.
- Points per table: 1st 70, 2nd 20, 3rd 10, 4th-8th 0.
- Practice rounds: 1,000 tables. Scored rounds: 4,000 tables.
- Scored rounds: 6, twenty minutes apart, weights 1, 2, 3, 4, 5, 6 (total 21). A team's total is the sum over rounds of
  weight x its average points per table. A practice round runs 10 minutes before each scored round; it does not count.
- Uploads: one every 5 minutes. Activating a bot that is already uploaded is instant.
- Prizes: 1st $100,000, 2nd $50,000, 3rd $25,000.
```

`starter-kit/README.txt`
```
(the kit is unpacked here since 13:01:30; its RULES.md repeats the variant text above and says: "Scoring: see the Format page." Its config has players=8, starting_stack=100bb, and a payouts field that reads [70, 20, 10]. bot/rules.json does not exist yet: platform's rules card is due at 13:05.)
```

`state/variant.md`
```
# The variant, as the portal's API gives it (saved 13:00:06 by scripts/portal_watch.py)

Title: Second Chance Hold'em. Announced 13:00:00 (the portal's own time).

No-limit hold'em sit-and-go, 8 players. Twist: once per hand, after the turn card and before the turn betting, each player still in the hand may pay 1 big blind into the pot to replace one of their hole cards with the next card from the deck. The discarded card is shown to the table.
```

`inbox/builder.log` (last 2 of 2 lines shown to the agent)
```
13:00:00 [clock] Minute 0: the variant is announced. Fetch the kit (Dylan puts it in starter-kit/), read the Format page (weights, payouts, cooldown, anything unusual). Spawn the three build-hour streams now, in ONE message, in the background.
13:00:06 [portal] THE VARIANT IS ANNOUNCED on the portal: "Second Chance Hold'em", at 13:00:00 (the portal's own time = minute 0); the rules text is in state/variant.md.
```

`inbox/research.log` (last 2 of 2 lines shown to the agent)
```
13:00:00 [clock] Minute 0: the variant is announced. Read the Format page (weights, payouts, anything unusual). Spawn the four build-hour streams now, in ONE message, in the background.
13:00:06 [portal] THE VARIANT IS ANNOUNCED on the portal: "Second Chance Hold'em", at 13:00:00 (the portal's own time = minute 0); the rules text is in state/variant.md.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 13:00:40 you spawned, in one message: platform (rules card by 13:05, v1 by 13:10), stylist (styles A, B, C), challenger (design D). Each brief named state/variant.md and strategy/FIRST_PROMPT.md Part 1.
- 13:01:30 Dylan: "kit is in starter-kit/". You checked that the variant loads in the kit's engine: it does.
- 13:01:40 you sent RESEARCH: "kit in starter-kit/, variant Second Chance Hold'em, Format page coming at notes/format.md, rules card coming at bot/rules.json, team Python announced when ready".
- 13:03:10 Dylan pasted the Format page and wrote: "format page. note the points: 70/20/10, not 50/30/20". You saved it as notes/format.md at 13:03:15.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 13:00:10 Samuel: "it starts now". You ran clock.py start with the portal's time (13:00) and told him the times.
- 13:00:50 you spawned, in one message: theory x3 (ranking + ICM thresholds by 13:10; twist values and rule by 13:15; push/fold, call tables, break-evens by 13:15), analyst (parsers, the round card), tester (rules card check, the rig by 13:15), scout (fingerprinting, the field trend). Each brief named state/variant.md and strategy/FIRST_PROMPT.md.
- 13:01:40 BUILDER sent: "kit in starter-kit/, variant Second Chance Hold'em, Format page coming at notes/format.md, rules card coming at bot/rules.json, team Python announced when ready".
- 13:03:15 Samuel: "format page says 70/20/10 for the top three at a table, not 50/30/20. does that change anything for us?" (notes/format.md was saved by BUILDER at 13:03:15.)
```

#### S15: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 13:03 Answer Dylan. Cross-check: kit payouts [70, 20, 10], portal cooldown 300 s and the clock's shape all match the page: no clock change.
- 13:04 SendMessage to platform, stylist, challenger: "Points are 70/20/10 (notes/format.md; kit agrees); blinds rise every 10 hands. FIRST_PROMPT's 56% / 65-74% / 57% call figures and your role file's ICM checks are 50/30/20 only: don't test against them. By hand: 53.0% at 8 equal stacks, 57.7% at 4, 53.8% at 3; theory's icm_thresholds.json decides." Stylist also: "Does tight corner C still earn its slot? Report's first line."
- 13:04 Two messages to RESEARCH (below), logged with `say.py --record`. Create notes/PLAN-builder.md (absent).
- 13:05 Open bot/rules.json: payouts, weights, cooldown, blinds. A mismatch goes to Dylan at once.
- 13:10 (b10) Platform reports v1: check releases/v1.zip and its VERSIONS line, `live.py v1 "first legal bot"`, tell Dylan the file, spawn a fresh bughunter, send RESEARCH "RELEASED v1 <sha256>".
- 13:11-13:13 Confirm state/status.md shows v1 active.

Outcome I expect: v1 active by about 13:12; practice 1 (13:20) plays the pick I declare by 13:17 (a style or D if upload-tested, else v1), nothing in it assuming 50/30/20.

##### 2. What I say
Dylan: "Noted and passed on: 70/20/10 is in notes/format.md, the kit says the same, and all three builders and RESEARCH have it. Cooldown, weights and round times are as planned. First is now worth 3.5 times second, so survival pays less and our all-in call thresholds drop; theory recomputes them. Nothing for you right now. About 13:10 I'll name releases/v1.zip to upload and activate."

RESEARCH (1): "Format page at notes/format.md. Points 70/20/10, not 50/30/20 (kit payouts [70, 20, 10] agrees). 8 players, 100bb, blinds every 10 hands, practice 1,000 tables, scored 4,000, weights 1-6, cooldown 300 s. theory: icm_thresholds.json from these payouts; the 56/57/62-65% tests are 50/30/20 only (by hand 53.0 / 53.8 / 57.7, unverified)."

RESEARCH (2): "tester: per-table spread is about 22.8 at 70/20/10 (17.9 before), so SEs are about 1.27x: the 0.7 floor and the 1.4/2.0 noise lines need today's figure (notes/pre/testplan.md §1)."

##### 3. The rule that decides
- CLAUDE.md §5: "A human's message is an instruction: do it first." Stated.
- CLAUDE.md §7: "Share what changes everyone's work at once." Stated; that payouts count is inferred.
- CLAUDE.md §4.3: "a mismatch goes to Dylan at once". Stated; none found.
- .claude/agents/platform.md: "8 equal ≈ 56%, 3 equal ≈ 57%, 4 equal ≈ 62-65% (50/30/20)". Stated; that my briefs' pointer to FIRST_PROMPT Part 1 misleads today is inferred.
- Two ways: DECISION_RULES §3 "Plan challenges ... the base style is wrong for today" against stylist.md "If today's rules clearly favour another axis ... build that instead of the weakest corner". I followed the second: nothing is measured yet, so no PLAN CHALLENGE.
- CLAUDE.md §3 "nobody re-derives them" against bughunter.md "else compute by hand": hand figures sent, labelled unverified.

##### 4. What I lacked
- Lacked: a 70/20/10 column (whatwins.md §4 stops at 60/25/15); subagent and RESEARCH ids; whether theory already started on 50/30/20.
- Guesses: 53.0 / 57.7 / 53.8 and 22.8 (mental arithmetic); v1 arrives on time.
- Opened: brief, CLAUDE.md, BUILDER.md, DECISION_RULES.md, scenario files, PLAN.md, scripts/README.md, LESSONS.md, role files, timeline.json; excerpts of whatwins, testplan.
- Longest: the 50/30/20 check values, found only in the role files.

#### S15: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 13:03 Answer Samuel first (below). Checked: `notes/format.md` and the kit's config both say 70/20/10; `bot/rules.json` doesn't exist yet.
- 13:04 SendMessage the six running subagents (`theory` x3 first, then `tester`, `analyst`, `scout`): payouts are 70/20/10, never 50/30/20; the role files' check values (56/57/62-65%) are 50/30/20-only; `tester` redoes today's noise (spread 22.8, tables x1.6). Then BUILDER (below), plus `say.py --record builder`.
- 13:05 `bot/rules.json` due: `tester` checks it field by field (payouts, weights 1-6, cooldown 300 s, blinds every 10 hands); a mismatch goes to Dylan. Then update `notes/PLAN-research.md`.
- 13:10 `theory/out/icm_thresholds.json` lands: confirm its `inputs` say 70/20/10, compare with my hand figures, send BUILDER path and headline. Then theory wave 2.

Outcome I expect: no bot choice changes (v1 active by 13:10 for practice 1; round 1 still plays `tester`'s adjusted best scorer of practices 1-3); every table, check and noise figure is on 70/20/10 before practice 1.

##### 2. What I say
Samuel: "Yes: it changes the maths and the noise, not the process. Format page and kit agree on 70/20/10. All-in calls loosen: about 53% on hand 1 and 58% four-left, against 56% and 65% (my hand arithmetic, unverified until theory's table at 13:10). Winning is nearly everything: heads-up is worth 50 points, not 20, and 3rd only 10 over 4th, so the tight style loses most of its reason. Results are about 28% noisier: a practice separates bots about 1.8 apart, not 1.4. The decision bars stay (they're in standard errors); the average stays 12.5. I'm telling the subagents and BUILDER now. You: nothing right now."

BUILDER: "Payouts are 70/20/10 (notes/format.md; kit config agrees): every 50/30/20 figure in the pack is off. Call break-evens, equal stacks, my hand arithmetic, UNVERIFIED until theory/out/icm_thresholds.json (13:10): 8 left 53.0%, 6 54.3%, 5 55.6%, 4 57.7%, 3 53.8%, heads-up 50%. platform's and bughunter's check values (56/57/62-65%) are 50/30/20-only: don't tune ICM to them. Heads-up decides 50 points: C (tight) is the weakest corner today. Spread per table 22.8, not 17.9."

##### 3. The rule that decides
- CLAUDE.md §5 (stated): "Your reply's **first sentence answers them**".
- CLAUDE.md §4.3 (stated): "payouts and the upload cooldown come from the kit and the Format page".
- theory.md (stated): "other payouts: compute and say so".
- CLAUDE.md §7 (stated): "Share what changes everyone's work at once."
- Conflict: RESEARCH.md "heads-up decides 50 vs 30 points" against the Format page's 70 and 20. Followed the Format page (hard rule 3).
- Conflict: DECISION_RULES §3 "Practice SE is **at least 0.7**" against testplan §8 "other payouts: redo section 1's first row". Followed testplan: 0.7 is a floor, rescaled by 22.8/17.9 (inferred).
- Not a PLAN CHALLENGE (inferred): payouts aren't among DECISION_RULES §5's seven assumptions and no field data exists; stylist.md's "clearly favour another axis" covers it.

##### 4. What I lacked
- A 70/20/10 column: whatwins §4 stops at 60/25/15, testplan §1 has no spread for it; I computed both by hand (unverified).
- What payouts the 13:00:50 theory briefs assumed (FIRST_PROMPT says "default 50/30/20"); whether "1,000 tables" is per team.
- Guesses: running subagents can be messaged mid-task; BUILDER hasn't broadcast the implications.
- Opened: brief, CLAUDE.md, RESEARCH.md, scenario files, DECISION_RULES, PLAN, scripts/README, theory.md, whatwins, testplan; excerpts of challenger_bar, FIRST_PROMPT, tester.md, stylist.md, BUILDER.md, LESSONS, START.md.
- Longest to find: the spread by payout shape (testplan §1, §8).


### S16. Choosing round 1's bot from practices 1-3

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 13:50:05 on Sunday (minute 50 of the build hour). Practice 4 has just started; scored round 1 starts at 14:00:00.

`state/status.md`
```
# Portal status (written 13:50:04 by scripts/portal_watch.py)

Last poll 13:50:04: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v7.zip** (sha256 d20a91c4be65…), uploaded 13:46
Declared live bot (state/live.json): **v7** (practice 4 pick: style A with the practice 1-2 refits) — MATCHES the portal
Next on the clock: Scored round 1 at 14:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Practice 2 | Practice 2 | 13:30 | finished · data saved | v5 | 8/20 · 13.10 ±0.56 | Fold Equity 15.30 |
| Practice 3 | Practice 3 | 13:40 | finished · data saved | v6 | 2/20 · 15.00 ±0.55 | 2 Curry 15.44 |
| Practice 4 | Practice 4 | 13:50 | **running** | v7 |  |  |

## Standings (top 10)

| # | Team | Total |
|---|---|---|

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 13:46 | v7.zip | ready |  |
| 13:36 | v6.zip | ready |  |
| 13:27 | v5.zip | ready |  |
| 13:17 | v4.zip | ready |  |
| 13:09 | v1.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 13:50:03)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 13:50: minute 50 · stage **Practice 4** · next: scored round 1 at 14:00 (T-10)
Live bot (state/live.json): **v7** · the portal runs: v7.zip
| **Scored round 1** | 14:00 | **next** |
Next steps: 13:51 (T-9 of round 1); 13:52 (T-8 of round 1); 13:54 (T-6 of round 1)
```

`state/live.json`: bot **v7**, why "practice 4 pick: style A with the practice 1-2 refits", declared 13:46:10, previous v6.

`notes/LEDGER.md` (the lines shown to the agents)
```
L16 | 13:24 | tester | verdict v4 (style A, sha256 19e0c4d2aa71): correct; heads-up +0.2 ± 0.4 vs v1 | n/a | 2,000 heads-up | --players 2, identical deals | rig/out/v4-verdict.md | validated
L20 | 13:34 | tester | verdict v5 (design D): correct; heads-up −0.1 ± 0.4 vs v4 | n/a | 2,000 heads-up | --players 2 | rig/out/v5-verdict.md | validated
L24 | 13:44 | tester | v6 (style B, sha256 4c81e2f7a09d): correct, 0 failed of 50,118, p99 0.20 ms; heads-up run FAILED TO RUN (rig error KeyError 'sb_shove', a rig bug) | n/a | 2,000 tables | 8 players | rig/out/v6-partial.md | proposed
L27 | 13:49 | tester | round-1 ranking, adjusted: v6 +1.1 ± 0.9; v4 +0.8 ± 1.0; v5 −0.2 ± 0.9; v6 minus v4 = +0.3 ± 1.3 | see claim | practices 1-3 | score minus yardsticks, adjusted for table draw, field maturity, best-of-3 | rig/out/round1-ranking.md | proposed
L28 | 13:49 | tester | verdict v7 (style A + refits, sha256 d20a91c4be65): correct; heads-up +0.3 ± 0.4 vs v4; vs v4 +0.2 ± 0.3 paired | +0.2 ± 0.3 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v7-verdict.md | validated
```

`releases/VERSIONS.md` (the lines shown)
```
v4 | 6a0be55 | 19e0c4d2aa71… | style A on all of theory's tables | 0 failed; p99 0.19 ms; upload test 5/5 | practice 1 | correct; heads-up +0.2 ± 0.4 (L16)
v5 | e81f3c4 | 5b1c77e09a3f… | design D (clean room) | 0 failed; p99 0.22 ms; upload test 5/5 | practice 2 | correct; heads-up −0.1 ± 0.4 (L20)
v6 | 2b9d0f8 | 4c81e2f7a09d… | style B (shove-heavy) on the newest tables | 0 failed of 50,118; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.0) | practice 3 | correct; heads-up run NOT done (rig error; rerun started 13:49) (L24)
v7 | c3310ae | d20a91c4be65… | style A + theory's refits from practices 1-2 | 0 failed of 49,660; p99 0.19 ms; upload test 5/5 (check_or_fold 5/5, load 5.3) | practice 4 | correct; vs v4 +0.2 ± 0.3; heads-up +0.3 ± 0.4 (L28)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`rig/out/round1-ranking.md`
```
# Round-1 ranking: the bots that played practices 1-3 (tester, written 13:49:30)

| Bot | Played | Score | Yardsticks' mean (n) | Minus yardsticks | Adjustments | Adjusted |
|---|---|---|---|---|---|---|
| v6 (style B, shove-heavy) | Practice 3 | 15.00 | 12.60 (11) | +2.40 | table draw −0.6 (it sat with 3 kit-example teams at 31% of its tables); best-of-3 discount −0.7 (0.85 x SE) | **+1.1 ± 0.9** |
| v4 (style A, wide pressure) | Practice 1 | 14.20 | 12.30 (field median: no yardsticks in the first practice) | +1.90 | immature field −1.1 (6 teams on the kit example) | **+0.8 ± 1.0** |
| v5 (design D, clean room) | Practice 2 | 13.10 | 12.50 (9) | +0.60 | table draw −0.8 | **−0.2 ± 0.9** |

Replay tests on the same downloads: v6 against v4 on Practice 3's hands +0.2 ± 0.5; on Practice 1's hands −0.1 ± 0.5.
**Adjusted best scorer: v6.** Its gap to v4 is +0.3 ± 1.3. The comparison that carries the decision is the adjusted
column; the replay tests do not separate the two.

Verdicts: v4 correct, heads-up +0.2 ± 0.4 (L16). v5 correct, heads-up −0.1 ± 0.4 (L20). v6 correct (0 failed decisions
of 50,118; p99 0.20 ms) but **no heads-up run yet**: the rig's `--players 2` runner raised KeyError 'sb_shove' in the
rig's own seat map (a rig bug, not the bot). Fixed at 13:49; the heads-up run restarted and should report about 13:56.
```

`inbox/builder.log` (last 3 of 5 lines shown to the agent)
```
13:47:00 [clock] Practice round 4 starts in 3 minutes (13:50): the bot you declared for it (live.py) must be uploaded and active now.
13:50:00 [clock] Practice round 4 plays now: the bot you declared for it (if it isn't the round-1 live bot, it is round 1's challenger). Now live.py the adjusted best scorer (tester's ranking of practices 1-3) for scored round 1 at 14:00, with no question asked; the round-1 question comes at T-8 (DECISION_RULES §3 'Round 1'). It is already uploaded: at T-9 Dylan makes it active (a click).
13:50:02 [portal] Practice 4 started at 13:50:02: playing v7.
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
13:45:56 [portal] DATA LANDED Practice 3 data/rounds/03-Practice-3/ (hands-first-1000.jsonl.gz, results.json; portal_watch is running roundcard.py and fp_train.py on it now)
13:50:00 [clock] Practice round 4 plays now: if its bot isn't the round-1 live bot (declared now), it is round 1's challenger. Scored round 1 is at 14:00; your recommendation is due at T-9 like every window (DECISION_RULES §3 'Round 1': the edge = each bot's practice score minus the yardstick teams' scores in the same practice; the same bars).
13:50:02 [portal] Practice 4 started at 13:50:02: playing v7.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 13:46:15 you told Dylan: "upload releases/v7.zip and make it active for the 13:50 practice". Dylan 13:46:40: "uploaded, active".
- 13:49:40 SendMessage from RESEARCH: "Round-1 ranking from tester (rig/out/round1-ranking.md, L27), adjusted: v6 (style B) +1.1 ± 0.9; v4 (style A) +0.8 ± 1.0; v5 (design D) −0.2 ± 0.9. v6 minus v4 is +0.3 ± 1.3. v4 and v5 have verdicts with a heads-up run. v6's verdict has no heads-up run yet: the rig's two-player runner had a bug; it is fixed and the run should report about 13:56. v7 (playing practice 4 now) has a verdict with a heads-up run (L28)."
- v4, v5, v6 and v7 are all on the portal. Dylan is at the laptop.
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 13:49:30 tester reported the round-1 ranking (rig/out/round1-ranking.md, L27): adjusted, v6 +1.1 ± 0.9; v4 +0.8 ± 1.0; v5 −0.2 ± 0.9; v6 has no heads-up run yet (rig bug fixed 13:49; result about 13:56).
- 13:49:40 you sent BUILDER those numbers and the state of each verdict.
- 13:49:50 analyst reported: "winners lens, practices 1-3: the 5 best teams in Practice 3 open-shove 52% at 15bb or less and 3-bet 14%; the style the field rewarded most in Practice 3 was shove-heavy."
- Samuel is at his laptop; his last message, 13:47: "B looked great in practice 3. is it going to be B for round 1?"
```

#### S16: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes

- 13:50 `live.py v4 "round 1: best adjusted scorer with a heads-up verdict; v6 pending"`. Not v6: its verdict has no heads-up run. Tell Dylan, message RESEARCH.
- 13:51 (T-9) Check state/status.md shows v4 active. Read RESEARCH's threshold for v7.
- 13:52 (T-8) Write the round-1 entry in state/decisions.md; ask Dylan: v4 (live) or v7 (challenger), bar z ≥ 0.5, deadline 13:55, rule's answer v4 unless practice 4 lands by 13:54 and clears it.
- 13:54 (T-6) No practice-4 result (practice 3 took 6 minutes): v7 is out.
- 13:55 (T-5) No answer: v4 stands, said in one line.
- 13:56 (T-4) Open rig/out/v6-verdict.md and the LEDGER myself. Heads-up run there and "fit for a scored round": `live.py v6`, Dylan clicks v6. Anything else: v4 plays, no click, miss reported.
- 13:57 (T-3) Confirm status.md: active bot = live.json. Nothing changes after.

Outcome I expect: v4 is active when round 1 starts at 14:00; v6 only if its heads-up verdict is in the LEDGER by 13:56:00 (its ETA is the cut-off itself).

##### 2. What I say

Dylan, 13:50: "Click v4.zip active on the portal now (uploads list, no upload). v4 is round 1's bot for now. The tester ranks v6 first, but by +0.3 ± 1.3 over v4, which is noise, and v6 has no heads-up test yet (rig bug, rerun due about 13:56); no bot plays a scored round without one. If v6's test is in and clean by 13:56 I'll ask you for one click to v6; otherwise v4 plays. The v7 question comes at 13:52, answer by 13:55."

RESEARCH, message 1: "Round 1 live bot declared: v4, not v6. v6's verdict has no heads-up run (L24), hard rule 2.1. v6 replaces v4 only if a LEDGER verdict line with its heads-up number and 'fit for a scored round' exists by 13:56:00; send it the second it lands."

Message 2: "Need RECOMMENDATION round 1 by 13:51: the practice-4 score v7 needs for z ≥ 0.5 against v4 (+0.8 ± 1.0). No practice-4 result by 13:54: the rule's answer is v4."

##### 3. The rule that decides

- DECISION_RULES §2 rule 1 (stated): "A bot plays a scored round only with a `tester` verdict that includes a heads-up run."
- DECISION_RULES §3 "Round 1" (stated): "the live bot is `tester`'s adjusted best scorer of practices 1-3 (declared at b50 ...)". That is v6.

They conflict. I followed the hard rule: CLAUDE.md §6, "Only the hard rules above never bend", and §3 "Uploads", "When in doubt, the live bot stays active", so the live bot must be allowed to play. Declaring the best eligible scorer (v4) is inferred.
- v6's late switch (inferred), §3 cut-offs: "T-4: the chosen bot released and tested | The live bot ... plays".
- v7 (stated), PLAN §5 T9: "no practice result by T-6: the rule's answer is the live bot".

##### 4. What I lacked

- No pass mark for a heads-up run. Guess: the tester's "fit for a scored round" decides.
- No rule for b50 when the best scorer has no verdict. Guess: v4, not v7.
- Guesses: the 13:56 switch needs no human yes; practice 4 lands about 13:56; bar z ≥ 0.5 (no standings yet).
- Absent: notes/PLAN-builder.md, state/decisions.md.

Opened, in order: brief; CLAUDE.md; BUILDER.md; the permitted scenario files; DECISION_RULES.md; PLAN.md; scripts/README.md; live.py; passages of LESSONS.md, tester.md, platform.md, RESEARCH.md; timeline.json.

Longest to find: a heads-up verdict's pass mark (tester.md "Verdicts"; none found).

#### S16: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 13:50 Answer Samuel. SendMessage BUILDER at once (the clock just told it to declare v6). Re-scope v6's tester: report the heads-up run once 600+ tables are done; the full run continues.
- 13:51 (T-9) `say.py --record builder`; update `notes/PLAN-research.md`.
- 13:52 (T-8) BUILDER asks "Which bot?"; I relay Samuel's exact words if he answers here.
- 13:53 `state/status.md`: v4 declared and active? If not, tell BUILDER.
- 13:54 (T-6) No Practice 4 result: tell BUILDER v7 is out.
- 13:55-13:56 Heads-up lands: open the file, check sha, n, the number. Clean: "FINAL round 1: v6", Dylan clicks. Not in by 13:56 (T-4), or a regression: "FINAL: v4 stays"; the miss goes to the T-20 sync.
- 13:57 (T-3) Confirm the active file in `state/status.md`; tell Samuel. Then Practice 4's analysis loop.

Outcome I expect: v6 (style B) is active at 14:00 if its heads-up verdict reaches BUILDER by 13:56 with no regression; otherwise v4. v6 never plays without it.

##### 2. What I say
Samuel: "Probably, not certain yet: B (v6) plays round 1 only if its heads-up test, due about 13:56, comes back clean. B is our best scorer after adjusting for soft tables (+1.1 ± 0.9), but only +0.3 ± 1.3 ahead of A: noise. The top 5 teams are shove-heavy too, which supports B. Its heads-up test hit a rig bug (fixed 13:49). Until it lands, A (v4, fully tested) is the default; B is one click, by 13:57. Nothing for you right now."

BUILDER: "RECOMMENDATION round 1: declare v4 now (releases/v4.zip, 19e0c4d2aa71), NOT v6 yet. rig/out/round1-ranking.md (L27, unverified): v6 +1.1 ± 0.9, v4 +0.8 ± 1.0, v5 −0.2 ± 0.9. v6 is the adjusted best scorer but has no heads-up run (L24, due ~13:56), so it can't play a scored round; v4 is the best with a full verdict (L16). If I send you v6's heads-up by 13:56 with no regression, the rule's answer becomes v6 (4c81e2f7a09d, already uploaded: a click by 13:57). Challenger v7: standings hidden, bar z ≥ 0.5: needs Practice 4 minus yardsticks ≥ +1.4 adjusted against v4 (+1.7 against v6) by 13:54; Practice 3 took 5m52s, so expect ~13:56: too late."

##### 3. The rule that decides
- DECISION_RULES §2.1, stated: "A bot plays a scored round only with a `tester` verdict that includes a heads-up run."
- DECISION_RULES §3 "Round 1", stated: "the live bot is `tester`'s adjusted best scorer of practices 1-3". That points to v6 now; I followed §2.1 because hard rules "never bend". v4 as stand-in: inferred.
- DECISION_RULES §3 cut-offs, stated: T-4, "The live bot ... plays"; "Don't wait past T-3". Promoting v6 by a click once its verdict lands: inferred.
- prompts/RESEARCH.md, T-9 recommendation, stated: "With no practice result by T-6, the rule's answer is the live bot."

##### 4. What I lacked
- A pass mark for a heads-up run (guess: not below −0.8 against v4, 2 SE).
- The rule's answer when the best scorer has no verdict at b50 (guess: v4, not v7).
- Whether a verdict after T-5 may still switch the bot (guess: until T-4).
- Practice 4's landing time (guess 13:56; the bundle says T-8 to T-7).
- Whether BUILDER already declared v6; whether the tester can report an interim.

Opened: brief; CLAUDE.md; RESEARCH.md; DECISION_RULES.md; PLAN.md; scripts/README.md; every permitted S16 file (NOW.md first, round1-ranking.md last); greps of LESSONS.md, tester.md, testplan.md, timeline.json.

Longest: a heads-up pass mark, never found.


### S17. The portal marks us out of contention

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 15:07:20 on Sunday. Scored round 5 starts at 15:20:00.

`state/status.md`
```
# Portal status (written 15:07:16 by scripts/portal_watch.py)

Last poll 15:07:16: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v15.zip** (sha256 0d4e8b6a91f7…), uploaded 14:56
Declared live bot (state/live.json): **v15** (round 4: v12 + three fixes) — MATCHES the portal
Next on the clock: Practice 8 (Round 4.5) at 15:10

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 11/20 · 12.51 ±0.28 | Fold Equity 14.23 |
| Round 3.5 | Round 3.5 | 14:50 | finished · data saved | v13 | 10/20 · 12.52 ±0.56 | 2 Curry 15.05 |
| Round 4 | Round 4 | 15:00 | finished · data saved | v15 | 17/20 · 10.92 ±0.28 | 2 Curry 14.61 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 141.20 |
| 2 | 2 Curry | 138.00 |
| 3 | Tilt Shift | 133.50 |
| 4 | River Rats | 132.90 |
| 5 | Check Mates | 131.00 |
| 6 | Gutshot | 129.40 |
| 7 | Pot Committed | 128.10 |
| 8 | Limp Mode | 126.80 |
| 9 | Kicker Trouble | 125.20 |
| 10 | Cold Four | 124.00 |
| 14 | **avalon** | 121.11 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:56 | v15.zip | ready |  |
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |

## Warnings

- none
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 15:07:15)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 15:07: minute 127 · stage **Round 4** · next: scored round 5 at 15:20 (T-13)
Live bot (state/live.json): **v15** · the portal runs: v15.zip
| Practice 8 (Round 4.5) | 15:10 | **next** |
Next steps: 15:08 (T-12 of round 5); 15:10 (T-10 of round 5); 15:11 (T-9 of round 5)
```

`state/live.json`: bot **v15**, why "round 4: v12 + three fixes", declared 14:54:40, previous v12.

`state/decisions.md`
```
(rounds 1-4: not shown)

## Round 5: which bot? (DRAFT, started 15:00:20 by BUILDER; not asked yet)
- Options: v15 (live) or v17 (challenger, a rewrite released 15:05:10; tester's verdict pending).
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L66 | 14:52 | tester | verdict v15 (sha256 0d4e8b6a91f7): correct; vs v12 +0.4 ± 0.3; heads-up +0.1 ± 0.4 | +0.4 ± 0.3 | 2,000 + 2,000 heads-up | paired; --players 2 | rig/out/v15-verdict.md | validated
L70 | 15:06 | tester | v17 (sha256 b7702c5de318) correctness and timing only: 0 failed of 49,402, p99 0.25 ms; strength and heads-up running | n/a | 400 tables | 8 players | rig/out/v17-partial.md | proposed
```

`releases/VERSIONS.md` (the lines shown)
```
v15 | 6e0a4f1 | 0d4e8b6a91f7… | v12 + three fixes from rounds 2-3 | 0 failed of 50,611; p99 0.21 ms; upload test 5/5 (check_or_fold 5/5, load 5.2) | live (round 4) | correct; vs v12 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L66)
v17 | a93d1c8 | b7702c5de318… | REWRITE for the round-4 field: shove-heavy under 20bb, calls wide against the top 5's 3-bets | 0 failed of 49,402; p99 0.25 ms; upload test 5/5 (check_or_fold 5/5, load 5.8) | challenger (round 5 window) | pending (tester started 15:05:30; expects 15:12, heads-up run included)
```

`data/rounds/11-Round-4/README.txt`
```
(results.json, our entry: {"team_name": "avalon", "average_points": 10.92, "margin_of_error": 0.28, "tables": 4000, "contender": false, "culled_at_look": "look 2 (after round 4)"}. In the same file 12 teams have "contender": true and 8 have "contender": false: the teams ranked 13th to 20th in the standings. Round 3's results.json had "contender": true for all 20 teams and no "culled_at_look" field. Neither notes/format.md nor the kit mentions a cut.)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 4 lines shown to the agent)
```
15:06:50 [portal] Round 4 finished: we were 17 of 20 with 10.92 (±0.28); 1st 2 Curry 14.61 · played by v15 · data: data/rounds/11-Round-4/ · health: 0 missed of 239,405 decisions, 0 restarts
15:06:50 [portal] URGENT: after Round 4 the portal marks us out of contention (look 2 (after round 4)). If that's final, nothing is lost by bold play: the challenger plays from now on.
15:07:00 [clock] Round 4's result and hand data land about now. This window's challenger is released (T-15) for Dylan to activate at T-12.
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
15:06:50 [portal] URGENT: after Round 4 the portal marks us out of contention (look 2 (after round 4)). If that's final, nothing is lost by bold play: the challenger plays from now on.
15:06:51 [portal] DATA LANDED Round 4 data/rounds/11-Round-4/ (hands-first-1000.jsonl.gz, results.json; the full file follows; portal_watch is running roundcard.py and fp_train.py on it now)
15:07:00 [clock] Round 4's result and hand data land about now (DATA LANDED in your inbox; portal_watch runs the round card). Run the round loop: spawn each task on DATA LANDED, never to wait for it. Everyone records every result in notes/LEDGER.md (effect ± se, n, method, file).
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 15:05:15 platform reported: "releases/v17.zip released (the rewrite), VERSIONS line written, upload test 5/5, 0 failed decisions". You sent RESEARCH "RELEASED v17 b7702c5de318 rewrite" at 15:05:20 and spawned a fresh bughunter on it.
- v17 is not on the portal yet. The last upload was v15 at 14:56.
- 15:07:05 Dylan: "17th?? and what does out of contention mean"
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 15:05:20 BUILDER sent: "RELEASED v17 b7702c5de318 rewrite". You spawned a fresh tester on it at 15:05:30; at 15:06 it reported L70 (correct and fast; strength and heads-up running; full verdict about 15:12).
- 15:06:55 you have not spawned the round loop on Round 4 yet.
- 15:07:10 Samuel: "the portal says we're out of contention. are we done? what do we do now"
```

#### S17: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 15:07 Answer Dylan (below): upload and activate `releases/v17.zip` for the 15:10 practice. No `live.py`: live stays v15. Message RESEARCH.
- 15:08 Spawn together: `challenger` (round 6's), `stylist` (which v15 fix lost), `platform`. Update round 5's entry in `state/decisions.md`.
- 15:09 `state/status.md`: v17 active? Rejected: v15 stays.
- 15:11 "Dylan: click v15.zip active now."
- 15:12 Verdict and practice result due. Ask "v15 or v17 for round 5?" with the rule's answer, deadline 15:15.
- 15:15 No answer: `live.py` the rule's answer.
- 15:16 v17 without a verdict including heads-up: v15 plays.
- 15:17 Dylan clicks the chosen bot; confirm in status.md.

Outcome I expect: at 15:20 v17 is active if its verdict (heads-up included) arrives by 15:16 and its field-adjusted practice edge is z ≥ 0, otherwise v15; by then an organizer has said whether rounds 5-6 count for us.

##### 2. What I say
Dylan: "17th was round 4 alone: 10.92 a table with v15, down from 12.51. No missed decisions or restarts: it ran cleanly and lost; RESEARCH is finding out why. Overall we're 14th, 12.39 behind 3rd with 11 of 21 weight left. 'Out of contention' is the portal's flag: round 4's results mark the teams ranked 13th-20th, us included, as no longer contenders ('culled at look 2'). The Format page and kit mention no cut, so I can't say whether we're out of the prizes. From you: (1) now, upload releases/v17.zip and make it active for the 15:10 practice; (2) then ask an organizer, or have Samuel ask: are culled teams out of the prizes, and do rounds 5-6 still count? I need a click from you at 15:11. Until we hear, we play as if they count."

RESEARCH: "Round 5: last two rounds, we're 14th, 12.39 behind 3rd: bar z ≥ 0. v17 (b7702c5de318) plays practice 8. Need the threshold by 15:11 and tester's v17 verdict with heads-up by 15:16, else v15 plays. Was v15's 10.92 the fixes or the field?"
"data/rounds/11-Round-4/results.json: avalon contender false, culled_at_look 'look 2 (after round 4)'; notes/format.md mentions no cut. A human is asking an organizer; until answered, rounds 5-6 count."

##### 3. The rule that decides
- DECISION_RULES §3 "Which bot plays": "z ≥ 0 in the last two rounds". Stated.
- §2 rule 1: "A bot plays a scored round only with a `tester` verdict that includes a heads-up run." Stated.
- §3: "the `tester` verdict is needed only for a scored round". Stated.
- §2 rule 2: "put the `state/live.json` bot back as active after the practice round". Stated.
- CLAUDE.md §5: "facts nobody else can see". Asking an organizer: inferred.
- Conflict: the watcher's inbox line says "If that's final, nothing is lost by bold play: the challenger plays from now on." I followed rules 1-2: its condition is unknown, and "Only the hard rules above never bend" (CLAUDE.md §6).

##### 4. What I lacked
- Any passage on what a cull means; FIRST_PROMPT Part 6 only lists culling as an unestablished platform option. Longest to find: the flag's source, scripts/portal_watch.py.
- Guesses: the zip exists; culled teams still play; RESEARCH is already on round 4.
- Opened: brief; CLAUDE.md; BUILDER.md; every permitted S17 file; DECISION_RULES; PLAN; scripts/README; portal_watch.py, FIRST_PROMPT (excerpts); LESSONS; RESEARCH.md; START.md; timeline.json (grep).

#### S17: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- **15:07** Answer Samuel. Spawn Round 4's loop in one background message: `scout` (field trend, yardsticks), `analyst` x3 (winners; leaks, including v15's three fixes; biggest opponent), `tester` (v15's Round 4 against v12's Round 3 on yardsticks; the practice score v17 needs). Message BUILDER.
- **15:08** LEDGER line for the cull flag.
- **15:10** Confirm in `state/status.md` that practice 8 played v17.
- **15:11** Send "RECOMMENDATION round 5": last-rounds bar z ≥ 0, with the threshold.
- **15:12-15:13** v17's verdict to BUILDER; practice lands; final answer.
- **15:15-15:17** Relay Samuel's words; check the active bot.

Outcome I expect: v17 active at 15:20 if its verdict (heads-up included) is clean and its practice edge is z ≥ 0; otherwise v15, or v12 if tester confirms the rollback and the humans take it.

##### 2. What I say
To Samuel: "Not that I can prove. The portal's Round 4 file flags the teams ranked 13th-20th, us included, as non-contenders ('culled at look 2'), but the Format page and kit mention no cut, so I can't tell whether we can still be paid or still play. On points we're 14th, 12.39 behind 3rd with 11 of 21 weight left: we'd need about 14.5 a table twice, roughly a 1% shot. Either way we play boldly: v17 plays practice at 15:10, and round 5 if tester passes it (due 15:12) and it does no worse than v15 against unchanged teams. One thing only you can do: ask an organizer whether teams 13-20 can still win a prize and still play, and tell me their words."

To BUILDER: "CULL FLAG: data/rounds/11-Round-4/results.json has avalon contender false, culled_at_look 'look 2 (after round 4)', as for all of 13th-20th; notes/format.md and the kit mention no cut. Samuel is asking an organizer. Until a human says it's final nothing changes: bar z ≥ 0, v15 back at T-9, v17 plays round 5 only with tester's verdict including heads-up (due 15:12)."

Then: "v15 Round 4 10.92 (17th) vs v12 Round 3 12.51 (11th): −1.59 ± 0.40 raw, unverified; tester's yardstick figure by 15:12. If it holds and v17 doesn't qualify, I'll recommend v12 (a click)."

##### 3. The rule that decides
- CLAUDE.md §5, stated: "Your reply's **first sentence answers them**"; ask humans for "facts nobody else can see".
- DECISION_RULES §3, stated: "**the last-rounds bar**: z ≥ 0 in the last two rounds".
- DECISION_RULES §2.1, stated: "A bot plays a scored round only with a `tester` verdict that includes a heads-up run."
- Conflict: the watcher's inbox line says "If that's final, nothing is lost by bold play: the challenger plays from now on." I followed DECISION_RULES ("It overrides anything older or vaguer"): finality is unknown and v17 has no verdict. Inferred.
- v12 fallback: inferred (§4, "A: measured on real event data. Act on it.").

##### 4. What I lacked
- Lacked: what "culled" means (prizes, whether we still play); any rule for a cut (FIRST_PROMPT lists "culling" only under "What we could not establish"); `notes/PLAN-research.md`, the card, yardsticks, v12's VERSIONS line.
- Guesses: 14.5 (top teams keep their averages); 1% (challenger_bar.md); v15's drop is the bot, not the field; v12 has a heads-up verdict.
- Opened: CLAUDE.md, RESEARCH.md, DECISION_RULES.md, PLAN.md, scripts/README.md; every S17 file except BUILDER's two; portal_watch.py, FIRST_PROMPT.md (end), LESSONS.md, challenger_bar.md, tester.md. A search for "cull" printed two prep/ lines; unused.
- Longest to find: any mention of a cut.


### S18. A practice round that starts late

**The files at that moment** (compacted: old round rows and the standard file headers are cut; inboxes show their last lines; everything else is as the agents saw it).

`NOW.md`: It is 14:51:10 on Sunday. Scored round 4 starts at 15:00:00.

`state/status.md`
```
# Portal status (written 14:51:06 by scripts/portal_watch.py)

Last poll 14:51:06: OK
Competition: No Limit 2026 Finals · team **avalon** · upload cooldown per the portal: 300 s
**Active bot on the portal: v13.zip** (sha256 9ab27d10e4c3…), uploaded 14:47
Declared live bot (state/live.json): **v12** (round 3: v9 + two fixes) — does NOT match the portal (fine during a practice round; must match by T-3 of a scored round)
Next on the clock: Scored round 4 at 15:00

## Rounds

| Stage | Round | Started | State | Played by | Us | Top |
|---|---|---|---|---|---|---|
| (earlier rounds cut) | | | | | | |
| Round 2 | Round 2 | 14:20 | finished · data saved | v9 | 7/20 · 13.20 ±0.28 | Fold Equity 15.20 |
| Round 2.5 | Round 2.5 | 14:30 | finished · data saved | v11 | 9/20 · 12.80 ±0.56 | 2 Curry 15.31 |
| Round 3 | Round 3 | 14:40 | finished · data saved | v12 | 5/20 · 13.50 ±0.28 | Fold Equity 14.23 |

## Standings (top 10)

| # | Team | Total |
|---|---|---|
| 1 | Fold Equity | 88.90 |
| 2 | 2 Curry | 86.00 |
| 3 | Tilt Shift | 82.40 |
| 4 | River Rats | 81.70 |
| 5 | **avalon** | 80.40 |
| 6 | Check Mates | 80.10 |
| 7 | Gutshot | 78.80 |
| 8 | Pot Committed | 77.90 |
| 9 | Kicker Trouble | 76.60 |
| 10 | Limp Mode | 76.00 |

## Uploads (newest first)

| Time | File | Status | Reason |
|---|---|---|---|
| 14:47 | v13.zip | ready |  |
| 14:36 | v12.zip | ready |  |
| 14:27 | v11.zip | ready |  |

## Warnings

- the portal runs v13.zip, the declared live bot is v12
```

`state/clock.md` (head, flagged rows, next steps)
```
# Clock (written 14:51:05)
Minute 0: **13:00:00** · build 60 min · scored rounds every 20 min · 6 scored rounds
Now 14:51: minute 111 · stage **Round 3.5** · next: scored round 4 at 15:00 (T-9)
Live bot (state/live.json): **v12** · the portal runs: v13.zip
| Practice 7 (Round 3.5) | 14:50 | not seen on the portal |
| **Scored round 4** | 15:00 | **next** |
Next steps: 14:52 (T-8 of round 4); 14:54 (T-6 of round 4); 14:55 (T-5 of round 4)
```

`state/live.json`: bot **v12**, why "round 3: v9 + two fixes", declared 14:34:50, previous v9.

`state/decisions.md`
```
(rounds 1-3: not shown)

## Round 4: which bot? (DRAFT, started 14:40:20 by BUILDER; not asked yet)
- Options: v12 (live) or v13 (challenger). No validated one-change line for Round 3.
```

`notes/LEDGER.md` (the lines shown to the agents)
```
L51 | 14:42 | tester | verdict v13 (sha256 9ab27d10e4c3): correct; vs live v12 +0.0 ± 0.4; heads-up +0.2 ± 0.4 | +0.0 ± 0.4 | 2,000 + 2,000 heads-up | paired, identical deals; --players 2 | rig/out/v13-verdict.md | validated
```

`releases/VERSIONS.md` (the lines shown)
```
v12 | b44c9e1 | 41d9a6c2f0b8… | v9 + two fixes (flat less out of position; 4-bet shove width vs wide 3-bettors) | 0 failed of 50,230; p99 0.20 ms; upload test 5/5 (check_or_fold 5/5, load 5.1) | live (round 3) | correct; vs v9 +0.4 ± 0.3; heads-up +0.1 ± 0.4; floor 9.8 (L44)
v13 | f19a3d7 | 9ab27d10e4c3… | best response to the measured mix: tight early, wide re-steal at 6 players or fewer | 0 failed of 49,871; p99 0.26 ms; upload test 5/5 (check_or_fold 5/5, load 6.0) | challenger (round 4 window) | correct; vs live v12 +0.0 ± 0.4 (paired, 2,000 tables); heads-up +0.2 ± 0.4; floor 9.9 (L51)
```

`notes/format.md`: the standard page used in every scenario but S15 (8 players; points 50/30/20; 1,000-table practices, 4,000-table scored rounds; 6 scored rounds, weights 1-6, total = sum of weight x average points per table; one upload every 5 minutes, activating an uploaded bot is instant; prizes for the top 3).

`inbox/builder.log` (last 3 of 4 lines shown to the agent)
```
14:48:00 [clock] Tell Dylan the challenger's exact file to activate now (upload it if it isn't on the portal yet): it plays the practice round at 14:50. Nothing released: name the released bot to activate instead, or leave the live bot. Don't live.py it (state/live.json stays the scored-round bot).
14:50:00 [clock] The practice round starts now and plays the challenger; its result lands about T-8 to T-7 (scored round 4 at 15:00).
14:51:00 [clock] Tell Dylan to put the state/live.json bot back as active straight away (a click). RESEARCH's recommendation arrives now (the threshold first; the final answer when the practice result lands).
```

`inbox/research.log` (last 3 of 4 lines shown to the agent)
```
14:46:41 [portal] DATA LANDED Round 3 data/rounds/09-Round-3/ (hands-first-1000.jsonl.gz, results.json; the full file follows; portal_watch is running roundcard.py and fp_train.py on it now)
14:50:00 [clock] The practice round starts now and plays the challenger; its result lands about T-8 to T-7 (scored round 4 at 15:00).
14:51:00 [clock] Send BUILDER the recommendation for scored round 4 now (it asks the humans at T-8): RECOMMENDATION round 4: the pre-registered rule (standings, the field-adjusted bar), both bots' numbers, the rule's answer as a released file, the evidence (validated, or labelled unverified). Until the practice result lands (usually T-8 to T-7) send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot.
```

`terminal-builder.md` (only the BUILDER agent saw this)
```
- 14:47:50 you told Dylan: "upload releases/v13.zip and make it active for the 14:50 practice". Dylan 14:48:10: "uploaded 14:47:55, active".
- 14:51:08 Dylan: "clock tab is beeping at me to put v12 back. doing it now, ok?"
- Nothing from RESEARCH since 14:47 (its one-change note: "no Round 3 change clears the bar").
```

`terminal-research.md` (only the RESEARCH agent saw this)
```
- 14:47:10 you sent BUILDER: "no Round 3 change clears the bar (two proposed lines, z 0.6 and 0.4)".
- 14:49:30 tester reported: "yardsticks between Round 2 and Round 3: 8 teams; v12 was +0.90 over them in Round 3. Ready to compute the edge when Round 3.5 lands."
- You have not sent the round 4 threshold message yet.
- Samuel is at his laptop; his last message, 14:45: "send me the round 4 call when you have it".
```

#### S18: the BUILDER agent's answer (verbatim)

##### 1. The next ten minutes
- 14:51 Answer Dylan: hold. `state/status.md` (14:51:06) has no Round 3.5 row, `state/clock.md` says practice 7 "not seen on the portal"; every earlier round showed within 4 s. v12 back now means the practice plays v12, and v13 goes unmeasured. Message RESEARCH, `say.py --record`.
- Whenever the watcher posts "Round 3.5 started … playing v13": tell Dylan "click v12 now"; confirm in status.md.
- 14:52 (T-8) Write round 4's question in `state/decisions.md` and ask it: rule's answer v12 unless v13's practice result clears z ≥ 0.5 (we're 5th, 2.0 behind 3rd); deadline 14:55.
- 14:54 (T-6) No practice result: the rule's answer is v12. No new zip, nothing to test.
- 14:55 (T-5) v12 goes back whether or not the practice started; record the rule's answer.
- 14:57 (T-3) Confirm status.md shows v12.zip active.

Outcome I expect: v12 is active when scored round 4 starts; v13 has played practice 7 only if it started before 14:55.

##### 2. What I say
Dylan: "No, wait: don't put v12 back yet. The 14:50 practice hasn't started on the portal (status as of 14:51:06), and it plays whatever is active when it starts, so v12 now would waste v13's test. If you already clicked, click v13.zip (the 14:47 upload) active again. Click v12.zip (14:36) the moment I say the practice has started, or at 14:55 without waiting for me, whichever is first. v13 is tested, so nothing is at risk meanwhile. If the organizers announced a delay, tell me."

RESEARCH: "Round 3.5 has NOT started on the portal as of state/status.md 14:51:06 (state/clock.md: 'not seen on the portal'). I'm holding v13 active until the watcher posts its start; v12 goes back then, or at 14:55 regardless. Round 4's rule's answer stays v12 unless a v13 practice result clears z ≥ 0.5 by 14:54. Need now: your threshold. Tell Samuel the practice is late."

##### 3. The rule that decides
- CLAUDE.md §7: "Facts about rounds (started, finished, results, active bot) come only from `state/status.md` and `data/` … Never assume a round is running." Stated.
- CLAUDE.md §4.2: "Each round plays the bot that is **active when it starts**." Stated.
- DECISION_RULES §2.2: "put the `state/live.json` bot back as active after the practice round". Stated; "after" meaning after its start is inferred.
- The other way: BUILDER.md T-9 "put vL back now"; DECISION_RULES §3 Uploads "When in doubt, the live bot stays active." I followed the first group: the T-9 step assumes the practice started at T-10, and v13 has a validated verdict with a heads-up run (L51), so holding breaks no hard rule. The 14:55 limit bounds the doubt (inferred).
- PLAN §5 T9: "no practice result by T-6: the rule's answer is the live bot". Stated.

##### 4. What I lacked
- Lacked: any rule for a late practice (clock.py's `held()` covers only a late scored round; the watcher's alarm comes 8 minutes after the expected start, past T-3); RESEARCH's threshold; `notes/PLAN-builder.md`.
- Guesses: the practice is late, not cancelled; round 4 stays at 15:00; 14:55 as the limit; no re-test for an already-tested zip; Dylan may already have clicked.
- Opened: brief; CLAUDE.md; BUILDER.md; DECISION_RULES.md; every scenario file except RESEARCH's two; PLAN.md; scripts/README.md; parts of LESSONS.md, START.md, clock.py, timeline.json, portal_watch.py.
- Longest to find: whether anything covers a late practice (LESSONS "A silent portal went unnoticed"; clock.py `held()`).

#### S18: the RESEARCH agent's answer (verbatim)

##### 1. The next ten minutes
- 14:51 Answer Samuel. SendMessage BUILDER the threshold, then the portal fact; `say.py --record` each. Tell `tester`: when Round 3.5 lands, redo the edge with `analysis/Round-3.5/fp/yardsticks.json` (teams unchanged Round 3→3.5, not 2→3), confirm `played_by.txt` says v13, field median if under 4 yardsticks.
- 14:52 Re-read `state/status.md`. LEDGER line "one-change Round 3: none clears z 1". Relay Samuel's answer verbatim.
- 14:54 (T-6) No v13 practice result: send "RECOMMENDATION round 4 FINAL: v12", tell Samuel. If it landed: z ≥ 0.5 means v13, else v12.
- 14:57 (T-3) status.md must show the chosen bot active; if not, BUILDER and Samuel at once.
- 15:00 Confirm what plays Round 4; T-20 sync: last-rounds bar (z ≥ 0) for round 5.

Outcome I expect: v12 is active when scored round 4 starts; v13 only if its practice result lands by 14:54 about 1.3 over the yardsticks.

##### 2. What I say
Samuel: "No round 4 call yet: it's v12 unless v13's practice beats the bar, and that practice (due 14:50) isn't on the portal as of 14:51:06. We're 5th, 2.0 behind 3rd, so v13 must beat the unchanged teams by about 1.3 points, roughly a 13.9. No result by 14:54 means v12. Dylan's side asks 'Which bot?' at 14:52; answer here and I relay it. If the organizers announce a delay, tell me the new time."

BUILDER 1: "RECOMMENDATION round 4 (threshold): 5th, 80.40, 2.00 behind 3rd, bar z ≥ 0.5. Live v12 (releases/v12.zip, 41d9a6c2f0b8): 13.50 in Round 3, +0.90 over 8 yardsticks (tester, unverified; set is Round 2→3, final set comes with Round 3.5). Challenger v13 (releases/v13.zip, 9ab27d10e4c3; L51 validated, heads-up +0.2 ± 0.4) needs Round 3.5 ≥ yardsticks' practice mean + 1.3 (SE about 0.8): about 13.9 if they repeat 12.6. No Round 3 change clears the bar. No practice result by 14:54: v12."

BUILDER 2: "Round 3.5 isn't on the portal: status.md 14:51:06 shows nothing running; active is v13. If v12 goes back before it starts, the practice measures v12 and I won't compute v13's edge from it. Your call with Dylan; v12 active by 14:57 unless v13 qualifies."

##### 3. The rule that decides
- DECISION_RULES §3: "we are outside the top 3 ...: z ≥ **0.5**". Stated.
- Same: "edge = (challenger's practice score − the yardsticks' practice scores) − (live bot's last scored score − ...)". Stated; the 1.3 is inferred.
- `.claude/agents/tester.md`: "kept the same bot between the live bot's last scored round and the practice". Stated; the Round 2→3 set is provisional (inferred).
- RESEARCH.md, T-9: "With no practice result by T-6, the rule's answer is the live bot." Stated.
- CLAUDE.md §7: "Never assume a round is running." Stated.
- Conflict: PLAN §3 "put back as active straight away" against DECISION_RULES §1 "prefer the option that learns more". The click is BUILDER's; I report, and back §3 Uploads: "When in doubt, the live bot stays active."

##### 4. What I lacked
- Missing: the yardstick list, tester's SE, `rig/`, `analysis/`, `data/`, `notes/PLAN-research.md`, organizer word on the practice.
- Guesses: SE 0.8; yardsticks at 12.6; v13 not poolable; Round 3.5 truly hasn't started.
- Opened: brief; CLAUDE.md; RESEARCH.md; DECISION_RULES.md; scenario files; PLAN.md; scripts/README.md; excerpts of clock.py, timeline.json, tester.md, scout.md, challenger_bar.md, LESSONS.md, portal_watch.py.
- Longest: the yardstick pair's definition (tester.md).

