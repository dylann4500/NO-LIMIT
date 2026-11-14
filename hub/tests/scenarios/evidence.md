# Evidence brief for the Finals plan docs (audit, 2026-11-13)

Scope: docs/EVIDENCE_TABLE.md, FINALS_PLAYBOOK.md, DECISION_RULES.md, START_HERE.md §2–3, FIRST_PROMPT.md Part 6 (and the Part 2 build brief it supports), research/finals_prep/* reports. Spot-checks were made against adaptation/res_q1_top.txt, res_q2.txt and res_boston.txt. No repo file was edited, and no hand data was copied here.

Grades used below:
- **M**: measured on real event data.
- **S**: simulation (the clone field, which is frozen and does not adapt).
- **J**: judgment or arithmetic.

"Single" means one variant or one event.

**Overall verdict:** most individual numbers are correctly transcribed. The problem is framing. Several measured-but-null results are written as warnings that discourage big changes. Simulation-only results (the style cycle, 14–15/table) have hardened into the build structure. Together these produce exactly the lock-in the team fears: a fixed A/B/C menu, a challenger chosen from that menu, and rewrites reserved for emergencies.

---

## 1. Claim-by-claim audit

| Claim as the docs use it | What the evidence actually is | Grade, n | Verdict |
|---|---|---|---|
| **"Standing still loses 0.65/table/round"** (DECISION_RULES §1, FIRST_PROMPT l.548) | res_q1_top: teams in the top 20 *of round n* that stayed unchanged moved −0.67 ± 0.12 (n = 18 team-gaps, 0/18 improved). Teams that jumped moved −0.65 ± 0.16 (n = 53). Rewrites moved −0.68 ± 0.39 (n = 17). Changed minus unchanged: **−0.01 ± 0.18**. These figures are *not* adjusted for regression to the mean, and the group is selected on its round-n score. Separately, the final top 20's mean score fell 19.25 → 17.43 because weak teams repaired themselves and scores are zero-sum around 12.5. | M, one event (Bay Area); Boston unchanged −0.46 ± 0.09 is a whole-field adjusted figure | **Overstated as causal.** The data says "top teams fall back about 0.65 whatever they do". Most of that is selection and a field catching up, and the catching-up mechanism is weaker in a 20-strong field. It supports "you cannot hold a lead by freezing". It does **not** show that changing helps. "18 bots" in DECISION_RULES is actually 18 team-gaps. |
| **"Top-20 rewrites lose 0.68"** (START_HERE §2; adaptation "not a routine tool") | Same table. The rewrite mean equals the unchanged mean, but the spread differs:<br>• rewrites: SD 1.61, 24% improved, best +3.8<br>• unchanged: SD 0.50, 0% improved, best −0.1<br>Top-10 rewrites (n = 5): −0.54 ± 0.69, 40% improved. Across the whole field, 81 of 92 gains of 1.5 points or more were rewrite-scale (3 by top-20 teams). | M, n = 17, single event | **Misframed. This is the most important correction.** For a top team, a rewrite cost nothing on average versus standing still and was the only route to an upside. With top-3-only payoffs, that variance is worth something whenever we are not comfortably in the top 3. Reword as "same mean, three times the spread". |
| **Fold to 3-bets ≤ ~75% (break-even 65–75%)** | The arithmetic (J) is right. Open 2.2–2.5bb, 3-bet to 3–3.5x, blinds 1.5bb: a pure-bluff 3-bet breaks even at a 65–69% fold. Field fold to 3-bet:<br>• Bay Area field: 59.2 → 69.7 → 66.8 over R1 → R6<br>• Boston field: 65–68<br>• Bay Area top 20: 63.7 → 68.4<br>• **Boston top 20: 75.0 → 57.5 (R5) → 60.4**<br>Our 82–89% leak is M. That it was exploited is M: 2 Curry 3-bet us 46% vs 35% matched. But **the regional winner itself folded 81–87% to 3-bets** (playbook §1 table; clone 73–84%). The "cost" (v10 −1.9 vs limp-or-shove in a wide field) is S and not isolated to this one rate. | J + M (rates), S (cost) | **Reasonable default, overstated as "fix in every bot"**. The winner violated it. Keep it as "recompute break-even live; folding far above it invites seat-learners", not as a cap. |
| **"Regional rates transfer across variants"** (EVIDENCE_TABLE last section, DECISION_RULES §5) | Field means match closely: fold to 3-bet 67.2 vs 67.3, open-shove at ≤10bb 41 vs 41, practice offset +0.37 vs +0.42. But field means are dominated by 100+ weak teams. The **top-20** numbers, the population the Finals actually is, diverged:<br>• Boston top-20 fold to 3-bet fell 17 points; Bay Area's rose 5<br>• Boston top-20 4-bet 8.9 → 23.4; Bay Area 7.6 → 6.9<br>• Boston top-20 open fell 37 → 32; Bay Area flat at 40 | M, two events | **Overstated for finalists.** Use regional values only as weight-4 priors, which the docs already do. Do not cite "the field is the same" as a reason to expect regional-like finalist behaviour. |
| **A/B/C style cycle** (wide > tight > shove > wide) | Metagame §2: the cycle "Holds" only in *pure* fields: +5.7, +2.6, +2.3 (bluffy +6.5, +1.9, +3.0). At 25% adoption no lead exceeds 1.4, i.e. the cycle is invisible in realistic mixes. Against the actual top 20, the three styles were within 1 point and the order flipped between round-1 and round-6 fits. The archetypes are clones of two regional teams plus one synthetic bot. **Clone scores correlated −0.09 to 0.33 with real scores within the top 20.** Frozen opponents; Bay Area variant only. | S, single variant, about 3M tables but model-limited | **Overstated in effect, even though the text hedges it.** It became the build structure (FIRST_PROMPT l.262–270: A pressure, B shove-heavy, C tight; "challenger = next in cycle" in metagame §7). Present it as one hypothesis about the field's shape, not as the menu. |
| **2 Curry per-seat 3-bet rule** | Re-raised a fresh opener 18%; after one fold 43%; after two folds 62%; after one non-fold 7% (138k decisions, 25bb+). | M for "it adapts"; C for "why it won" | Number is accurate. **START_HERE §2 overstates the spread.** "Ten of the other 19 top teams had a per-seat rule like this" is wrong: only 3 teams strongly re-raised on folds (7 flagged). 10 of 19 had a *strong response of some kind*, mostly betting into seats that fold. At Boston: 15 re-raise-on-fold learners, and 12 of the estimated top 20 with some strong response. |
| **Field drifts toward aggression** | Bay Area top-20 3-bet 9.8 → 23.7; Boston top-20 14.3 → 27.0 → 24.5. Big-blind fold fell at both. Flop bet-when-checked-to rose at both. The defence lagged at Bay Area (fold to 3-bet *rose* until R6) but came by R2–3 at Boston. | M, two events, 126/191 teams | Accurate as history. **As a forecast for Sunday it is a hypothesis.** Finalists start from the regional endpoint, and Boston's top 20 had already *peaked and reversed* by R6 (3-bet 27.0 → 24.5, 4-bet 23.4 → 18.3, open 37 → 32). |
| **Scores 14–15/table vs a strong field** | v10 in the round-6-fit top-20 clone field: 14.1 (v6 14.3). **In the round-1-fit top-20 field: 18.9 / 18.6.** The arithmetic fact is that a top-20-only field averages 12.5. The clones of strong teams ran 2–9 points below their real scores. | S, one fit | **Overstated precision.** Say "expect a compressed scale near 12.5; our regional bots simulate 14–19 depending on the fit". Use it only to stop panic at a 15. |
| **Identification by hand 20** | Using the previous round's profile against 20 candidates, the right team is named 73% of the time by hand 20 (by round pair: 56–85%). With profiles two rounds old: 67%. Without sizes: 31%. Boston: 67%. Avalon itself: half its seats by about hand 7, 88% by hand 20. The field measured was not hiding. | M, two events | Accurate. Being identified only matters through exploitable rate gaps (identity report). |
| **Rank persistence** | Field Spearman 0.84–0.91 (official, res_q1_top). Top 20: 0.41–0.79, moving 3–4.5 places per round (redteam check 10). | M | **FIRST_PROMPT Part 6 l.592 is stale**: it says "0.76–0.83 (Bay Area)". It matches neither the official 0.84–0.91 nor the at-our-tables 0.79–0.88. Boston "median 0.68" has no backing res file. Fix the line. |
| **"Big jumps come from rewrites" / Boston +18 places hail mary** | The Bay Area whole-field statistic is M (81/92). The Boston story is one friend's account (n = 1). | M + anecdote | Fine if the anecdote is labelled as one. |
| **Practice SE ~0.65; practice runs +0.37 high** | M: +0.37 ± 0.06 (156 same-bot teams); Boston +0.42. Adaptation recommends SE ±0.7, since the round-to-round wobble is ±0.3. With 20 teams one opponent's change is 5% of the field, so expect more than this. | M | DECISION_RULES uses 0.65. Update to ≥0.7 and say it is a floor for a 20-team field. |
| **Practice rounds are clean experiments** | Only 3–6% of teams ran practice-only bots. But 54% played something other than their next scored bot, and 44–64% of the eventual top 20 changed between consecutive *build* practices (redteam check 1). | M | **Understated risk.** The three build-hour styles are scored against three different fields. With styles 0.5–1 point apart and practice SE about 0.7, the pick is close to a coin flip (redteam: right "about half the time"). |
| **Cloned field as warning light** | Two large cases right in sign and size (v4 −5.6 to −7.8 vs real ≈ −9; v6 +1.6 to +2.9 vs +2.3). Below about 1–2 points it is unresolved. It cannot rank strong opponents. The pre-registered ordering test is still "running" (EVIDENCE_TABLE §4). | S validated on 2 cases | Docs are correctly hedged. Never let it prune *divergent* ideas: it is frozen, and it rates by regional styles. |

**Wrong or stale lines to fix:**
- FIRST_PROMPT l.592: rank correlation figures.
- START_HERE §2: "ten of 19 had a per-seat rule like this".
- DECISION_RULES §1: "18 bots", and the causal reading of 0.65.
- DECISION_RULES §3: practice SE 0.65 should be ≥0.7.
- START_HERE §2: "rewrites lost 0.68" without the spread.

**Single-variant items:** everything in metagame (the cycle, the tight trigger thresholds, 14–15/table), and the 2 Curry rule's payoff.

---

## 2. How the field changes during an event

**Measured (adaptation §1–2, §6–7; redteam checks 1–3, 9):**
1. **Nearly everyone changes every round.**
   - Bay Area: 78–90% of teams per gap. Boston: 75–84%.
   - Top teams change as often as the middle but by half as much: rank 1–5 RMS 4.1 points; ranks 101+ RMS 14.8.
   - Among the top 20, 20–60% have a materially different bot from one scored round to the next.
2. **The direction is one-sided aggression first, defence later.**
   - Bay Area top 20: 3-bet up every round (9.8 → 23.7), BB fold down every round (58.5 → 40.2), defence (fold to 3-bet down, 4-bets up) only in R6.
   - Boston: defence by R2–3. Top-20 fold to 3-bet 75 → 57.5 by R5; 4-bet 8.9 → 23.4.
   - Then a partial reversal at Boston R6 (3-bet 24.5, 4-bet 18.3).
   - So the counter-wave arrived about 3 rounds earlier at the second event. Finalists who studied both events should start further along: plausibly **at or past the reversal by round 1–2**.
3. **Team-level responses are real but weak**, β ≈ 0.15 per unit of experienced rate:
   - opponents folding to my flop bets → I bet more (+0.15, t = 3.6);
   - being re-raised more → I fold less (−0.14).
   Most between-round movement is convergence toward the field mean (r = −0.39 to −0.49) and bug repair.
4. **Forecasting:** "same as last round" beats the trend.
   - Field 1.29 vs 1.72; single team 5.9 vs 11.0; Boston the same.
   - The exceptions are top-20 3-bet rate and BB defence, which moved the same way every round; half the last move is the best forecast there.
   - Moves are steps, not trends: a rate that moved >3 points moved the same way next round only 35–45% of the time.
5. **What winners did between rounds:**
   - 2 Curry changed every gap but by small amounts (RMS 2–5, never rewrite-scale). Its edge was built *before round 1* and adapted *inside the table*.
   - Lemonade rewrote once (R2 → R3, +1.3), then froze and lost 0.1/0.5/0.5.
   - The R1 leaders that relied on exploiting folders (TeamBallHog 22.4 → 15.5, WAYS-ER 21.4 → 15.3, Team 72 22.2 → 17.4) collapsed as folders disappeared.
   - Team 123 added a per-seat 3-bet rule in a rewrite and went 12.8 → 17.8.
   - Last-round changes cut both ways: thepastaway 13.4 → 20.3 in R6; sandylikesfrogs 18.3 → 15.2.
6. **Boston round 5** (top 20 estimated from a single viewpoint, about 370 tables per team per round, score SE about 1.0):
   - 3-bet 27.0%, fold to 3-bet 57.5%, 4-bet 23.4%;
   - BB fold 40.5%, c-bet 84%, open-jam short 40%.
7. **Exploit decay:** in simulation, about half of a style's edge is gone once a quarter to half the field copies it (metagame §3, S). The Bay Area fallers above are the measured analogue.

**What the monitor should watch each round** (computed on the newest scored download, shrunk, compared with last round with SEs; practice downloads are tagged as partly stale):

| Watch | Why | Trigger |
|---|---|---|
| Finalist-field rates: open, 3-bet, fold to 3-bet, 4-bet, BB fold, open-jam ≤15bb, call-jam, bet-when-checked and fold-to-bet by street, variant-phase choices | Moves of 5–15 points per event on these at the top | Any rate ≥2 SE from our current prior → replace the prior, and re-ask which style is the best response |
| Style mix: share of teams per class (wide re-raiser, shove/limp, tight, other), plus an "unclassified" share | The cycle hypothesis and copying | A class gains ≥ about 5 of 19 teams; the leader's class grows |
| Per-team change class (unchanged / tweak / jump / rewrite) and the leaders' deltas | 75–90% change; leaders' moves tell us what paid | Top-5 team rewrites; ≥3 teams converge on one design |
| Responses to us: their fold to our 3-bets, their 3-bets after our folds, bets into us after our folds, residual "plays avalon" effects | Seat learning is common (half or more of finalists); named targeting becomes feasible at 20 teams | Our 3-bet fold or flop fold more than about 10 points from break-even; seat-learning slope against us |
| Score dispersion and the leader's margin | Compressed scale; noise vs signal | Spread under 2× practice SE → stop reading small differences |
| Our own-outcome leak list (the one tool tested retrospectively) | It found the real leak at z 6.6 from practice 1 | Leak persistent across two downloads → ship the fix |
| Surprise index: how far *our* pre-event priors and the plan's assumptions are from the live field | Guards against plan lock-in | Two or more key assumptions off by 2 SE or more → the lead must tell both humans "the plan's premise X is false today" |

---

## 3. Defaults vs hypotheses

**Robust enough to be defaults** (M across two events, or arithmetic):
- The hard rules (legal, fast, tested zip, rules card). Errors and timeouts auto-fold (public rules, zeniteq summary).
- Opponents change every round; "same as last round" beats trend extrapolation.
- Regional rates as **weight-4 priors**, replaced from the first Finals download. A weight above 10 hurt.
- In-table counts are thin: median 1 fold-to-3-bet chance per seat per table. So blend the count with a prior.
- Practice SE of 0.7 or more; the practice offset; the best-of-k discount; local wins don't predict the field (v4: +4.4 locally, 100th).
- Break-even arithmetic, recomputed live; ICM correctness; the leak checks (over-calling, over-folding, swallowed exceptions).
- Sizes identify us quickly; masking buys at most one round.
- Seat learners exist and react within one or two folds.

**Hypotheses only** (state as "to test on today's field"):
- the style cycle and its menu of three;
- which style wins;
- "challenger = next style in the cycle";
- the tight-mode thresholds;
- 14–15/table;
- fold ≤75% to 3-bets as a *cap*;
- aggression continuing to rise;
- the per-seat 3-bet rule as the *cause* of winning;
- "top-20 rewrites lose";
- "standing still loses" as a causal claim;
- defend-the-first-3-bet-wider;
- the cloned-field ranking of anything under 2 points.

---

## 4. External research (web)

**(a) Pittsburgh regional (12 Nov):**
- No variant, team count or results found.
- One unverified LinkedIn snippet claims a first place (Steven Peng); it could not be confirmed.
- Not to be confused with the CMU DSC AI Poker Tournament (https://cmudsc.netlify.app/pokerai-2026).
- Get it from the portal or teammates; do not assume.

**Event background:**
- Hosts are Sequoia, Citadel Securities and OpenAI. Bay Area 6 Nov (about 150 teams), Boston 9 Nov, Pittsburgh 12 Nov, Finals SF 15 Nov. Sources: https://pokerbot.sequoiacap.com/ and https://x.com/sequoia/status/2115111389501218868
- Boston: 330+ students. The organizers' framing: "shifted from 'can I build this' to 'what should I build'". A participant said the top teams researched beforehand and studied why their bots lost. https://www.thecrimson.com/article/2026/11/12/poker-tournament-regional/

**(b) Finals format:**
- Public: SF, 12–8 pm, in person, invitation only.
- Rules summary (secondary): 6 scored rounds 20 minutes apart, 1 ms per decision, offline, at most one submission per 5 minutes, state resets per table, variant secret until the build. https://www.zeniteq.com/sequoia-and-openai-open-a-100k-pokerbot-tournament-6aycef
- **Check against the docs:** the portal says a 30-second cooldown; the summary says 5 minutes. Confirm on the day.
- The Finals structure itself is not published.

**(c) Lessons from other competitions:**
- **Scoring rule decides style.**
  - In the ACPC, total-bankroll events reward exploiting weak bots; instant-runoff rewards not losing. Different bots won each: 2010 Tartanian4 (bankroll) vs Hyperborean (runoff). https://poker.cs.ualberta.ca/news_2010.html and https://spectrum.ieee.org/champions-declared-in-ai-poker-tournament
  - ICM points against 7 opponents is closer to bankroll, but a strong-only field removes the weak bots that bankroll scoring feeds on. That matches the metagame finding that wide 3-betting loses 3 points when the weak teams go (S).
- **Top rankings are mostly noise unless samples are huge.**
  - ACPC 2017 1st vs 2nd was "about 65% confident". https://groups.google.com/g/computer-poker/c/_f-c1ZJwK5w
  - 2016 needed about 15M duplicate hands, and a tiebreak was reversed. https://today.ucsd.edu/story/carnegie_mellon_baby_tartanian8_pokerbot_sweeps_annual_competition
  - Variance reduction: AIVAT (https://arxiv.org/abs/1612.06915); duplicate or fixed deals for local A/B.
  - **Implication:** one 1,000-iteration practice cannot separate candidates closer than about 1.4 points (2 SE). Use practice slots for candidates whose plausible effect is that large, which means divergent designs, not tweaks.
- **Robust exploitation.**
  - A pure best response to a model is brittle. Restricted Nash response (https://proceedings.neurips.cc/paper/2007/hash/6e7b33fdea3adc80ebd648fffb665bb8-Abstract.html) and data-biased response (https://webdocs.cs.ualberta.ca/~bowling/papers/09aistats.pdf) keep most of the gain with much less downside.
  - Safe exploitation: Ganzfried & Sandholm, https://dblp1.uni-trier.de/rec/conf/sigecom/GanzfriedS12.html
  - This supports deviations that scale with sample size, which the docs already use (C), and it argues against "best response to last round's field" as the only challenger design.
- **Populations shift and early exploits go stale.**
  - Battlecode postmortems: early exploits were nerfed or countered between sprints; one 2025 team found scrimmage margins did not predict qualifier margins; get a working bot first and iterate. https://battlecode.org/assets/files/postmortem-2025-om-nom.pdf, https://battlecode.org/assets/files/postmortem-2025-just-woke-up.pdf
  - Kaggle RPS: nothing beats Nash statistically; the gains came only from exploiting non-random bots via a meta-strategy that *switches among several predictors* according to recent results. https://github.com/0Zeta/RockPaperScissors
  - These are the external analogue of "keep several whole alternatives alive and pick by recent measured results".
- **Exploration theory.** Explore-then-commit is provably about 2× worse than continued adaptive evaluation (Garivier, Lattimore & Kaufmann, https://arxiv.org/abs/1605.08988). Do not spend all exploration in the build hour and then freeze into "live plus tweaks".

---

## 5. Recommendations for doc wording

**State as fact** (with the number and the "two regionals" or "one regional" tag):
- The field changes every round (75–90%).
- Same-as-last beats trend.
- Practice SE is 0.7 or more, and practice runs about +0.4 above the next scored round.
- Sizes identify a team within about 20 hands.
- Seat learners react within one or two folds.
- Our regional leaks.
- Break-even arithmetic.
- **Top-20 changers and non-changers fell back equally; rewrites had the same mean and three times the spread.**

**State as prior** (with "replace from the first download"):
- Every regional rate.
- The aggression drift. Wording: "at Boston the top teams' counter-wave arrived by R2–3 and partly reversed by R6; finalists likely start there".
- Fold to 3-bets near break-even.

**State as hypothesis** ("one simulation on the Bay Area variant; clones could not rank strong teams"):
- The style cycle;
- 14–15/table;
- the tight triggers;
- "challenger = next in cycle".

**Remove or reword:**
- "Standing still loses 0.65" → "Holding still did not hold a lead: top teams fell about 0.65 a round whether or not they changed."
- "Rewrites lost 0.68 for top-20" → "For top teams, rewrites cost nothing on average versus standing still and were the only source of big gains (up to +3.8); use them when the upside matters."
- "Ten of 19 had a per-seat rule like this" → "3 had a strong re-raise-after-fold rule, 10 a strong per-seat rule of some kind."
- Fix the Part 6 rank-correlation line.

**Un-lock the build menu.** Rewrite the FIRST_PROMPT Part 2 bullet:

> "Build three *deliberately different* designs. Pick them after reading today's variant and the first practice data. Regional styles (pressure, shove-heavy, tight) are one possible set, from a simulation on a different variant. At least one of the three must be a design the agents derive fresh from today's rules, without reading the regional style notes."

**Exploration budget**, as an explicit rule in DECISION_RULES §3. The justification:
- Practice can only resolve differences of about 1.4 points or more, so tweaks are unmeasurable there.
- The local clone sim cannot rank strong opponents, so only the real field can judge a divergent idea.
- Top-team rewrites cost nothing in mean.
- Explore-then-commit is suboptimal.
- Early rounds are cheap: R1 is 1/21 of the total under linear weights, 1/32 under Boston's.

The budget, by phase:
- **Build hour.**
  - 1 of the 4 practice slots goes to a from-scratch or "blank-slate" design. 2 go to the most different credible designs. 1 re-plays the leader.
  - About 25% of builder agents work outside the A/B/C frame.
- **Rounds 1–3**, or until 30% of the total weight has been played:
  - At least every other practice slot plays a *divergent* challenger. Divergent means it differs from the live bot at rewrite scale: RMS change of about 8 points or more on the standard rates, or a different style class.
  - At least 2 of the 6–10 candidate builders per window build from scratch against the newest field profile, not as edits of the live bot.
  - This holds even when we are in the top 3, unless our lead over 4th is more than one round's typical swing.
- **Later rounds:**
  - Shrink the budget in proportion to the remaining weight. At least 1 divergent builder per window stays alive as insurance against a field shift.
  - Lower the bar and raise the budget whenever the surprise index fires, or we are behind 3rd.
- **Divergent candidates are judged only by the real field** (practice, or same-round split arms if the rules allow). They are never vetoed by the clone field unless it predicts a loss of 2 points or more *and* the reason is understood.
- **Overfitting guard.**
  - Never re-tune toward a single practice round's difference under 2 SE.
  - Pool two downloads before treating a leak as persistent.
  - Discount the best of k candidates by 0.5·SE·√(2 ln k).
