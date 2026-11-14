# Decisions for Dylan and Samuel (Saturday 14 November, from the overnight research)

One page. Each item: what to decide, the evidence, and my recommendation. Nothing in section A or B has been
applied: they change how the team decides or touch the event's rules, so they are yours. Section C lists what
was applied, for information. Evidence files are in `notes/pre/`.

## A. Decision rules and defaults (strategy: both of you)

| # | Decide | Evidence | Recommendation |
|---|---|---|---|
| 1 | **The bar for playing a challenger** (`DECISION_RULES.md` §3). The contrarian memo said the bar inside the top 3 is too cautious | An independent check (`challenger_bar.md`) rebuilt the model and tested the rule on the regional's results: of 23 strong teams that showed a new bot in practice, the current rule would have played 17 (mean gain +1.21, one loser) and refused 6 (mean −0.57). Any bar from 0 to 1.0 points lands within 1 percentage point of the best. The "too cautious" claim did not survive | **No change to any bar** |
| 2 | **How the edge's standard error is computed** (§3, "Practice SE is at least 0.7") | One practice predicts the scored-round edge with an error of about 0.8 points (1.0 for top-20 teams), and the points per place may differ on Sunday | **Adopt the one edit** in `challenger_bar.md` §5: take the SE from the yardstick teams' own practice-to-scored spread (0.8 with fewer than 6 yardsticks, never below 0.7). It rescales itself |
| 3 | **When a field rate triggers a PLAN CHALLENGE** (§5: "off by 2 SE or more") | A pooled field rate's SE is 0.1-0.5 points in a 1,000-table file, while the regional field itself moved 0.5-2.7 points between rounds: "2 SE" fires on ordinary drift. Found by the field forecast, confirmed by the independent check | **Change for field rates only:** "2 points or more outside the band, in two downloads running". Keep 2 SE for scores |
| 4 | **Choosing round 1's bot from practices 1-3** | Early practices over-reward tight play (score against 3-bet rate: r −0.54 in practice 1, +0.25 by round 6); for a single unchanged bot the evidence is mixed | **Add one sentence, not a rule:** between two close candidates for round 1, prefer the more aggressive; worth at most 1 point |
| 5 | **"No flat calls" default** (`FIRST_PROMPT.md` Part 1; plan assumption 2) | It rests on pre-event simulated bots. On the regional's real data our flats made +5.9 bb a table once the postflop leak was fixed (`whatwins.md` §1) | **Soften it:** flat calls are allowed where the style states the postflop plan behind them; the check run still counts them |
| 6 | **"Call shoves wider than a chart"** (`FIRST_PROMPT.md` Part 1) | Mixed evidence (`whatwins.md`) | **Reword:** call at the ICM threshold against that seat's measured shoving width |
| 7 | **"Our own mistakes cost about 22-25 points"** (`PLAN.md` §1) | The research could not rebuild the figure; the write-up gives 5-9 points for two of the mistakes | **Samuel:** confirm the source or correct the number |

## B. Fair play (both of you)

| # | Decide | What happened | Recommendation |
|---|---|---|---|
| 8 | **Tell the organizers?** | While finding the hand-download address I fetched the portal's public login-page scripts. One contains default table settings for presets named "finals" and "finals_community". The rules say the variant "will remain confidential until that announcement", so I stopped reading there. The values are in no note, brief or file of ours, and no research session was told | **Don't use it, and tell the organizers** their public page exposes it. It protects the team and costs nothing |
| 9 | **Look in a Pittsburgh kit for unused actions?** | Our Bay Area kit's replay code already handled a separate `discard` event and several boards, which Pittsburgh's variant later used (it had nothing for Boston's auction). A Pittsburgh team's public notes say their kit lists more phases | We have no Pittsburgh kit. **Don't go looking for one**; reading the kit we are given on Sunday is normal work |

One caveat on item 8: after seeing it I wrote the research briefs to hold for "a table that is not 8-handed and
payouts that differ". The bundle's own lessons already demand that (a rehearsal ran every test at the wrong table
size; the rules say points per place vary), but you should know the order of events.

## C. Set-up choices (Dylan, at noon)

| # | Choose | What I found |
|---|---|---|
| 0 | **Usage for Sunday: the most urgent item on this page** | At 06:15 on Saturday the desktop app's account (plan shown as Ultra) had used **71% of its weekly all-models limit** (Fable alone: 25%), and the week does not reset until **Wednesday 18 November**, after the Finals. Extra usage is switched off. Sunday is two sessions with up to 40 subagents each for four hours. The terminal `claude` on this laptop is signed in to a different login (it reports a Max plan), with its own limits. Decide before the rehearsal: which account runs Sunday, whether to switch on extra usage as insurance, and keep Saturday's remaining spending on the Sunday account small (the rehearsal itself will cost a lot) |
| 10 | **Terminal tabs or the desktop app on Sunday** | Every mechanics check passed in desktop-app sessions under Remote Control. `START.md` is written for terminal tabs; nothing has been tested there |
| 11 | **Which Claude account** | Samuel's computer must be signed in to the same account as this laptop for Remote Control. This laptop is on a Max plan login |
| 12 | **Connectors off for the Finals sessions** | Each trivial subagent cost about 56,000 tokens of start-up context here, mostly this account's tools, connectors and skills |
| 13 | ~~AWS~~ **decided (Dylan, 14 Nov, about 06:05): not used.** | The credits cannot be obtained before the Finals. Modal stays the only compute, as the bundle says. The tooling built overnight is kept, shelved, in `cloud/aws/`; it never ran on AWS |

## E. Rule wordings found unclear by the tabletop test (both of you; evidence in `prep/TABLETOP_14NOV.md`)

Eighteen Sunday moments were given to 36 fresh agents who had only the bundle: 5 came out clear, 10 slow (right,
but after a guess or a search), 3 split (the two sessions told their humans different things), none wrong. The
report's section 3 has exact replacement wording for each. The five that would cost most:

| # | The gap | What happened in the test |
|---|---|---|
| 14 | **Late data** (its P1): if a scored round's data lands at T-6, is the challenger still judged? | Both agents played the challenger; the cut-off table read literally says "no change from new data" |
| 15 | **One switch deadline and a pass mark for the heads-up run** (P2) | A challenger with no tester verdict: BUILDER waited until T-3, RESEARCH until T-4; neither found what "passing" a heads-up run means |
| 16 | **A practice round that has not started when the clock says "put the live bot back"** (P3) | The two sessions gave Dylan opposite advice |
| 17 | **"A big lead" has no units** (P4) | 2nd with a 4.7-point lead and a challenger at z 1.2: agents guessed the bar is 1.0 (challenger plays); the words as printed give 1.5 (live bot plays) |
| 18 | **Standings held: what "clearly in the top 3" means** (P5) | Third by 0.3: both agents chose the lower bar; `LESSONS.md` read literally gives the higher one |

P6-P14 are smaller: what happens when you two disagree and the one who disagrees must click; nobody there to
click; which figures change when points per place are not 50/30/20; "out of contention" (the watcher's own line
says the challenger plays from then on, which no rule says); round 1's bot when the best scorer has no heads-up
run; and six one-line clarifications.

## F. From the consistency read and the sample check (smaller; both of you)

| # | Decide | Evidence |
|---|---|---|
| 19 | **Where scores come from**: add to `DECISION_RULES.md` that scores are taken from `results.json`, never from a hand file | `notes/pre/first1000.md`: the first-1,000 file is a fair sample of the round, but its score for us missed the full round by +0.4 on average and by 2.0 once; it shows other teams only at our tables. The analyst's role file already says this now |
| 20 | **Fetch 5,000 tables first instead of 1,000?** | The same note recommends it (score error 0.30 instead of 0.66). I left the watcher at 1,000: the practice rounds that decide the bot have only about 1,000 tables anyway, and the full file starts with the same tables, so the analyst can re-run on its first 5,000. One line changes it if you want it |
| 21 | **Is "over a third of teams differ between a practice and the next scored round" a broken assumption or normal?** | `field.md` treats it as a warning sign; `challenger_bar.md` counted about 46% doing so at the regional |
| 22 | **A control arm in scored rounds** | `FINGERPRINTING.md` wants 15% of scored-round tables with counters off; `EVIDENCE_TABLE.md` says no control arm in scored rounds without a stated reason |
| 23 | **Speed bar for the twist decision** | `TWIST_NOTES.md` says p99 under 0.8 ms; `tester.md` and `challenger.md` say under 0.5 ms |
| 24 | **Latest release time for the challenger** | The timeline says T-15, T-13 at the latest; the cut-off in `DECISION_RULES.md` is T-12 |

Three places the consistency read expects an agent to go wrong even though nothing is inconsistent: Dylan
clicking "make it active" the moment BUILDER declares the round-1 bot (minute 50, when practice 4 starts) instead
of at the clock's reminder; the practice download at T-8 being treated like a scored round's and loading the CPU
during the upload test; and the T-9 to T-5 arithmetic when there are too few yardstick teams.

## D. Applied already (for information)

Factual corrections, each traced to a source in its commit message: the prizes ($100,000 / $50,000 / $25,000, not
50/30/20); paired noise for two different designs (about 21/√tables, not 13: sample sizes were 2.6 times too
small); the best-of-k discount (exact values); two practice rounds must differ by 2.0 points, not 1.4; sampling
ends at an iteration count with the deadline as a backstop; ICM is cheap only for our own share; the Modal
throughput target is marked as never measured; 13 corrections and five new entries in `TWIST_NOTES.md` and
`theory.md` from three timed drills; the portal watcher against the real portal. Details: `prep/HANDOFF.md`
section 9 and `git log`.
