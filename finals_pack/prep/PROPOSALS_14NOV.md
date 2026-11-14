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
| 10 | **Terminal tabs or the desktop app on Sunday** | Every mechanics check passed in desktop-app sessions under Remote Control. `START.md` is written for terminal tabs; nothing has been tested there |
| 11 | **Which Claude account** | Samuel's computer must be signed in to the same account as this laptop for Remote Control. This laptop is on a Max plan login |
| 12 | **Connectors off for the Finals sessions** | Each trivial subagent cost about 56,000 tokens of start-up context here, mostly this account's tools, connectors and skills |
| 13 | **AWS: primary, backup or unused** | The AWS chat builds the tooling with dry runs; a real comparison with Modal needs your sign-in, a yes to the quota request and a spending limit |

## D. Applied already (for information)

Factual corrections, each traced to a source in its commit message: the prizes ($100,000 / $50,000 / $25,000, not
50/30/20); paired noise for two different designs (about 21/√tables, not 13: sample sizes were 2.6 times too
small); the best-of-k discount (exact values); two practice rounds must differ by 2.0 points, not 1.4; sampling
ends at an iteration count with the deadline as a backstop; ICM is cheap only for our own share; the Modal
throughput target is marked as never measured; 13 corrections and five new entries in `TWIST_NOTES.md` and
`theory.md` from three timed drills; the portal watcher against the real portal. Details: `prep/HANDOFF.md`
section 9 and `git log`.
