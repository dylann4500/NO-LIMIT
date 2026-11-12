# Strategy families, counters and counter-counters: literature map for the Finals

**Not saved as REPORT.md.** The harness refused the write ("subagents should return findings as text"), and I did not work around it. The full report is below for you to save. The only files in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/strategy/literature/` are `icm.py` (the ICM arithmetic used below) and `dl/` (the downloaded papers and their extracted text). Nothing in the repo was changed.

Labels on every claim: **[S]** from a source I opened this session (link in Sources); **[M]** a standard result cited from memory, link not opened; **[R]** my own reasoning or arithmetic; **[U]** uncertain.

## 1. The short version

1. **The plan stops at level 1 in three places.** These are wide 3-betting (a best response to last week's field), team recognition by bet sizes (assumes nobody masks or impersonates), and practice rounds as "the only fully trustworthy judge" (assumes other teams play their real bot in practice, which we ourselves do not). Details in section 4.
2. **The literature's answer to "which level are they on" is not to guess the level.** Keep a sound baseline, deviate by an amount tied to the sample size behind each deviation, run a small number of whole alternative responses, and pick among them by measured recent results. Section 3.
3. **Deep reasoning is rarely needed.** Measured populations sit at 0-2 steps of reasoning, and going past level 2 adds little. Build for level 0 and 1 opponents and be safe against level 2. [S, M]
4. **Every chain below either cycles (tight → steal → resteal → tight) or stops at a break-even frequency we can compute.** The stopping points are the baseline; the cycle is where measured, bounded deviation belongs. [R]
5. **Public write-ups of this event do not exist yet.** Searches found only announcements. Past-competition evidence on winning styles is thin and mostly from heads-up formats. [S]

## 2. Strategy families and their chains

Break-even figures are plain pot arithmetic, or ICM for 50/30/20 computed in `icm.py` [R]. "Stops" means the chain reaches a frequency no opponent can profit from; "cycles" means it returns to an earlier family.

| # | Family (level 0) | What it exploits | What beats it (level 1) | What beats that (level 2) | Where it stops or cycles |
|---|---|---|---|---|---|
| 1 | **Wide open-raise and wide 3-bet, fold to 4-bet** (2 Curry) | Openers who fold 70-85% to 3-bets. A 3-bet to 8bb over a 2.5bb open risks 8 to win about 4, so it profits on folds alone above about 65% folds | 4-bet all-in with more than premiums (it folds 81-87% to 4-bets), and call 3-bets in position with hands that play well. Opening tighter also removes its targets | 3-bet only strong hands against seats that have 4-bet or called; keep bluff 3-bets only for seats still folding; call the 4-bet jam wider | **Stops** per seat when measured fold-to-3-bet falls to about 60-65%: below that only value 3-bets pay. **Cycles** otherwise: value-only 3-bettors get folded to, which invites wide 3-bets again |
| 2 | **Shove-or-fold and limp-or-jam** (Lemonade) | Callers who need 56-74% equity under ICM and so fold too much; no postflop play to get wrong | Call at the ICM threshold against the *measured* shove range (a 40-60% shover is called far wider than a chart says). At 100bb an open jam risks 100 to win 1.5 and is called only by hands that crush it | Shover narrows to the equilibrium range for that stack depth | **Stops** at 12bb or less: jam/fold equilibrium is computable and near-optimal there (Miltersen-Sorensen 2007 [M]; Ganzfried-Sandholm three-player [S]). Above about 15bb it does not stop: it loses to family 1 and to trapping |
| 3 | **Tight survivor** (our bot D) | Other teams colliding. Each all-in between two other equal stacks pays every bystander: +0.42 points with 8 left, +1.17 with 6, +2.33 with 5, +5.83 with 4 | Steal its blinds every orbit: it folds. It reaches the last five short: 1,500 chips against four stacks of 3,625 is worth 10.7 points, below the 12.5 average. It needs about its starting stack at four left (15.2 points) to be above average | Re-raise all-in over frequent openers at 15-25bb (the resteal) | **Cycles** into family 2 (resteal), then family 1. Pays only if the field actually collides: measure all-ins per table before hand 40 |
| 4 | **Call down with one pair** | Bots that bluff too much | Bet thicker for value, drop bluffs | Fold more (our v6) | Leads to family 5 |
| 5 | **Fold to bets** (us after v6: 73/66/78%) | Bots whose bets are mostly value | Bet every time it checks | Check-raise and check-call that seat with a trapping range | **Stops** at folding about bet/(pot+bet) of the time against an unknown bettor, shifted by that seat's measured bluff share. The prompt pack already says this |
| 6 | **In-table opponent model** (live counts per seat) | Seats with fixed leaks | Noise: a seat gives 0-4 chances per table on the rare rates. Switching: play one way for 30 hands at cheap blinds, then the other when blinds are large. Recency windows chase the switch | Deviate in proportion to the count behind each estimate; treat a sudden change as less reliable, not more | **Stops** at the baseline when counts are small. Hoehn et al.: even in Kuhn poker, converging on the best exploit within a few hundred hands is impractical, though beating equilibrium is possible [S] |
| 7 | **Team recognition by bet sizes, team priors** (ours) | Teams that keep their sizes and their bot | Mask: use the field's commonest sizes. Impersonate: copy the sizes of a team whose profile says "never folds to 3-bets" and get left alone, or one that "folds too much" and get bluffed into calls. Swap bots between rounds. Play a decoy in practice rounds | Identify from behaviour that costs chips to fake (frequencies, responses), cap the prior's pull, drop to the field prior on any mismatch | **Stops** at "field prior plus live counts". The rare rates are where the prompt pack gives the profile the most weight, so that is where impersonation pays most [R] |
| 8 | **Tailored counter to a team ahead** (opponent specialists) | A leader's fixed leak | The leader sees the same histories and patches; we misidentify; a given team is at our table only about 33% of the time (8+8+4 split) | Target leaks that need a redesign to fix, not a parameter | Mostly **stops at small**: gain is (points when present) x 0.33 x recognition accuracy x chance the leak survives. Johanson et al.: best responses to one opponent are brittle against others [S] |
| 9 | **Anticipate the field's next move** (level 2 at the team level) | Teams that best-respond to last round's data | A field that does not move. Regional rank correlation of 0.76-0.83 suggests most bots change little | Decide by measured trend, not by assumption | **Stops** at an ensemble: score "same as last round", "last round plus its trend" and "everyone copies the leader" on each new download and use the one that predicted best |
| 10 | **Variant-twist specialist** | Teams that misvalue the new decision | Copying: twist decisions show in the histories, so this edge decays fastest. A fixed rule (always expose the low card, bid a fixed fraction) leaks our hand | Randomise the twist choice where options are close in value; read each team's twist rule | **Stops** when twist choices are near-indifferent mixes. One public 2024 auction bot's README concedes its bids do not yet account for the information they reveal [S] |
| 11 | **Exploit the filler bots** (4 non-scoring seats on the 4-team table) | Static bots that never adapt | Nothing: fillers do not rewrite | - | **Stops at level 1.** The one place full exploitation is safe. We are on that table about 20% of the time. Check on the day what the fillers are and whether they can be recognised [R, U] |

Three points the table makes that the plan does not:

- **Family 1's direct counter is not bot D.** The counter to wide 3-betting is re-aggression (4-bet jam wider, call in position), not folding more. D counters *collisions*, which is a different thing. No bot in our build set has the style "trap and re-raise the raisers". [R]
- **Family 3's arithmetic is conditional.** Bystander gains are small early (0.42 points per collision at 8 players) and large late (5.83 at 4). A tight bot profits only if it arrives late with chips. [R]
- **Family 7 is two-sided.** Whatever we do to recognise others, 19 teams can do to us, and the cheapest attack on our own design is to copy another team's sizes. [R]

## 3. Robust principles, with source and prompt wording

**P1. Deviate from a baseline in proportion to the data behind each deviation.**
- Source: Johanson, Zinkevich, Bowling 2007 [S]. Best responses computed against one opponent lost to other opponents; one weak bot beat every counter-strategy except the one trained on it.
- Source: Johanson and Bowling 2009 [S]. With few observed games, pushing the response further toward the model made it both more exploitable and *less* profitable against the real opponent. Setting confidence per situation by observation count fixed this.
- Prompt: "Every opponent-specific adjustment moves a decision from the default by an amount that grows with the number of observations behind it and is capped. State the cap for each adjustment. With fewer than about five observations the default plays." (The "five" is my placeholder, not from a source.)

**P2. Risk on exploitation only what the opponent has already given away.**
- Source: Ganzfried and Sandholm 2015 [S]. Safe deviation from equilibrium is possible only by spending "gifts" from opponents' earlier mistakes; safe exploiters beat a plain best response against strong, changing opponents.
- Limit: proven for two-player zero-sum only. Transfer to 8-player ICM is my extrapolation [R, U].
- Prompt: "Keep a running estimate, per seat, of chips won from that seat by adjustments. Widen adjustments against a seat while that total is positive; return to the default when it turns negative."

**P3. Choose among a few whole responses by measured results; do not estimate many parameters.**
- Source: Bard et al. 2013 [S]. A portfolio of four prepared responses, chosen online by Exp4, did at least as well as a much larger one and would have won the 2011 ACPC total-bankroll event; more arms meant more exploration cost.
- Translation [R]: between rounds this is our live bot plus challenger, which the plan already does. Inside a 125-hand table, result-based selection is too noisy, so switch modes on a measured table statistic (raises, re-raises and all-ins per orbit). Group the 19 teams into three or four behaviour types with one response each, in place of 19 tailored counters.
- Prompt: "Build at most four table modes (default, against a raising table, against a folding table, against a calling table). Pick the mode from counts at this table, with a blend, not a hard switch."

**P4. Apply each prediction at shifted levels, keep whichever has predicted best recently, and fall back to the baseline when none does.**
- Source: Iocaine Powder (Egnor, 1999 RoShamBo winner), as described in [S]. One predictor yields six strategies (three levels of "I counter you", three of "you counter me"); selection is by recent score; it plays randomly when being out-predicted.
- Prompt for the test rig: "Build three versions of the cloned field: as measured; shifted one more step along each team's last change; and with every team moved toward the current leader's rates. When a new download lands, report which version predicted it best. Ship nothing that loses 2 points or more to any of the three."

**P5. Do not design for deep recursion.**
- Source: de Weerd, Verbrugge, Verheij 2013 [S]. First- and second-order reasoners clearly beat shallower ones; third order adds little.
- Source: Camerer, Ho, Chong 2004 [M]. People average about 1.5 steps.
- Source: Wunder et al. 2012 [S]. A model of the population's reasoning depth explained the 2011 Lemonade Stand winner.
- Source: Zinkevich et al. 2011 [S]. A constant strategy beat sophisticated learners in pre-tests.
- Prompt: "For each plan, write one line on what a team that expects it would do, and one line on our reply. Stop there."

**P6. Fix plain mistakes before playing the cycle.**
- Source: Czarnecki et al. 2020 [S, abstract and summaries only]. Games have a skill axis plus cycles, and cycles shrink relative to skill as play improves. Our own rank correlation of 0.76-0.83 fits.
- Prompt: already in the plan (bugs and leaks first). Supported.

**P7. In multi-player play there is no safety theorem; evidence supports both a fixed strong baseline and modelling.**
- Pluribus beat professionals who could study it. That it did not model them is from memory, not confirmed by the summary I opened [S for the result, M for the rest].
- Ganzfried, Wang, Chiswick 2022 [S, abstract]: opponent modelling beat exact equilibrium in three-player Kuhn poker.
- No source covers ICM sit-and-gos with adapting bots [U].

**P8. A reputation can be worth more than a mask.**
- Source: Fudenberg and Levine 1989; Kreps and Wilson 1982 [M]. A player seen repeatedly gains by being known as a type that does not back down.
- Source: Aumann and Maschler [S, summary only]. The informed side's best policy is usually partial revelation, because using information reveals it.
- Translation [R]: sizes are free to change, so mask them. Frequencies cost chips to fake, so don't. If opponents use profiles, being *known* to call 3-bet jams wide stops them 3-betting us, which is a reason to keep one honest, visible trait.

**P9. Explore where it is cheap.**
- Source: Hoehn et al. 2005 [S]. Among equally good baseline strategies, some reveal the opponent's tendencies faster.
- Prompt [R]: "In the first 20 hands (blinds 10/20), prefer lines that test each seat's response: one small 3-bet, one bet when checked to. Chips are cheapest then, and the rare rates never get measured otherwise."

## 4. Where the current plan is contradicted or unsupported

1. **Practice rounds as the trustworthy judge** (FIRST_PROMPT Part 3; playbook "the real field is the judge"). We put our challenger in the practice round and the live bot in the scored round. If other teams do the same, the practice field is not the scored field, and practice downloads feed wrong profiles. No source; this is the plan's own logic applied to the other 19 teams [R]. It can be checked on regional data we already hold: does a team's practice-round profile match its next scored-round profile?
2. **"Use the blend from the first hand", with heavy profile priors on rare rates** (Part 1, Part 4). The recognition figures (54% / 67% / 73%) were measured on a field that was not trying to hide. P1's sources say acting hard on a thin model is the classic failure. The cap in Part 4 is right but unspecified, and nothing detects a seat with team X's sizes and different behaviour. [S for P1; R for the application]
3. **"Vary our sizes within a small band"** (Part 4). A band is itself a signature. Using the field's commonest sizes hides us better at the same cost. The plan also never asks whether we want to be hidden (P8). [R]
4. **One opponent specialist per team ahead** (Part 5). Contradicted by Johanson 2007 (brittle) and Bard 2013 (small portfolio no worse than large). Expected gain is diluted by the 33% table share and recognition error. [S, R]
5. **"Recent or against-us rate departs from the long-run rate: move toward it"** (Part 4). This is the behaviour a switching bot exploits (family 6). Bound the move by the count behind the recent window. [S: Hoehn, Ganzfried-Sandholm; R]
6. **Wide 3-betting as item 3 of "what it takes to win"** (playbook section 1). The evidence is one softer field. All 20 finalists have studied the regionals, and our own data shows the field's 3-bet rate doubling within one event. Part 6 admits this could not be established, but no bot in the build set is the direct counter (re-aggression). [R]
7. **"Shove much wider than we call"** (Part 1). True only against callers who respect ICM. It needs the seat's measured call-an-all-in rate, which the prompt tracks but does not tie to shove width. [R; standard ICM texts agree, S secondary]
8. **"When a choice trades a small chance of a worse result for a real chance of a much better one, take it"** (Part 1 opening). Our score is a mean over thousands of tables, so in-table gambling adds no useful variance; it only lowers the mean. Risk-seeking belongs in the choice of bot and style, not in chip decisions. A coding agent may read the sentence the other way. [R]
9. **The cloned field as a veto** (Part 3). It is a level-0 predictor of the next round. The prompt notes clones do not adapt; P4 gives the fix. [S]
10. **Supported as written**: A, B and C counting raises at the table and tightening (measured behaviour, not identity); the challenger slot (P3); bugs and leaks first (P6); folding near break-even adjusted by shown bluffs (family 5).

## 5. What I could not find

- **This event:** no public write-up of the No Limit regionals or of Pittsburgh (today). Searches returned announcements only. [S]
- **MIT Pokerbots:** no year-by-year winner write-ups beyond 2017.
  - Variants, from a third-party catalogue [S]: 2020 Permutation, 2022 Swap, 2023 Red River, 2024 Auction, 2025 Bounty, 2026 Toss (three hole cards, discard face up, close to the Bay Area regional).
  - The 2017 prize-winner's notes [S]: tables built against opponents who do not discard overstated equity; solver-trained bots folded to very large raises; it tightened against all-in bots.
- **ACPC:** results I found are heads-up and three-player limit. The claim that the total-bankroll event (closest to our scoring) rewarded exploiting weak entrants while the elimination event rewarded not losing is partly sourced (Johanson and Bowling 2009 on total bankroll; a search snippet on defending chips in the runoff). [S, partial]
- **Rock-paper-scissors on Kaggle:** I could not find the winning write-up, so nothing here relies on it.
- **Theory:** none on exploitation, masking or impersonation for multi-player ICM games. Everything on those in sections 2-4 is reasoning from two-player results. [U]

## Sources

Opened this session:
- Johanson, Zinkevich, Bowling, "Computing Robust Counter-Strategies", NIPS 2007: https://poker.cs.ualberta.ca/publications/NIPS07-rnash.pdf
- Johanson, Bowling, "Data Biased Robust Counter Strategies", AISTATS 2009: https://proceedings.mlr.press/v5/johanson09a.html
- Bard, Johanson, Burch, Bowling, "Online Implicit Agent Modelling", AAMAS 2013: https://poker.cs.ualberta.ca/publications/AAMAS13-modelling.pdf
- Ganzfried, Sandholm, "Safe Opponent Exploitation", ACM TEAC 2015: https://www.cs.cmu.edu/~sandholm/safeExploitation.teac15.pdf
- Ganzfried, Sandholm, "Computing Equilibria in Multiplayer Stochastic Games of Imperfect Information", IJCAI 2009: https://www.cs.cmu.edu/~sandholm/stochgames.ijcai09.pdf
- Ganzfried, Wang, Chiswick, "Opponent Modeling in Multiplayer Imperfect-Information Games" (abstract): https://arxiv.org/abs/2212.06027
- Hoehn, Southey, Holte, Bulitko, "Effective Short-Term Opponent Exploitation in Simplified Poker", AAAI 2005: https://cdn.aaai.org/AAAI/2005/AAAI05-123.pdf
- Zinkevich, Bowling, Wunder, "The Lemonade Stand Game Competition", SIGecom Exchanges 2011: https://sigecom.hosting.acm.org/exchanges/volume_10/1/ZINKEVICH.pdf
- Wunder, Kaisers, Yaros, Littman, "A Framework for Modeling Population Strategies by Depth of Reasoning", AAMAS 2012: https://ifaamas.csc.liv.ac.uk/Proceedings/aamas2012/papers/5E_3.pdf
- de Weerd, Verbrugge, Verheij, "How much does it help to know what she knows you know?", Artificial Intelligence 2013: https://www.ai.rug.nl/~verheij/publications/pdf/ai2013.pdf
- Iocaine Powder explained: https://inchpin.substack.com/p/rock-paper-scissors-is-not-solved
- Czarnecki et al., "Real World Games Look Like Spinning Tops" (abstract): https://arxiv.org/abs/2004.09468
- Pluribus (press summary): https://www.cmu.edu/news/stories/archives/2019/july/cmu-facebook-ai-beats-poker-pros.html
- Future game simulation and its limits: https://icmizer.com/en/blog/how-fgs-future-game-simulation-calculator-works
- MIT 2017 prize-winner notes: https://github.com/sebLopezCot/SPAM_pokerbot_2017
- MIT 2024 auction bot: https://github.com/abh-win/auction-poker-bot
- Third-party mock of this event, with the variant catalogue: https://github.com/aniketxdey/pokerbots
- A tight, survival-first bot for a similar format: https://github.com/Markus112105/pokerbot
- Event page: https://pokerbot.sequoiacap.com/

Cited from memory, not opened: Camerer, Ho, Chong 2004 (cognitive hierarchy); Fudenberg and Levine 1989 and Kreps and Wilson 1982 (reputation); Miltersen and Sorensen 2007 (heads-up jam/fold); Aumann and Maschler (repeated games with incomplete information; I saw only a search summary).

Researched but not used above: the Southampton 2004 prisoner's dilemma handshake (https://www.southampton.ac.uk/news/2004/10/team-wins-competition.page). It needs several entries per team, which this format does not allow.