# What wins sit-and-gos of AI-built bots (pre-event note, topic B, for `stylist`)

Drafted Saturday 14 November for Sunday's `stylist` to check and extend. Notes only, no bot code.

**Grades** (as `strategy/EVIDENCE_TABLE.md`): **A** measured fact, no causal claim; **B** a change measured on full-table results; **C** candidate (one regional, simulation, pre-event bots, argument); **D** withdrawn; **arith.** exact arithmetic (ICM is Malmuth-Harville, equal stacks unless said).

Sections 1-3 are behaviour rates from two hold'em-family regionals: priors, never ranges. Section 4 holds for any variant. Section 6 says what does not transfer.

## What the stylist does in its first 15 minutes because of this note

1. **Read the rules card when it lands** (speedrun: minute 2): seats, payouts, stack in big blinds, blind schedule. Pick the payout column in section 4. If the table is not 8-handed or the payouts are not 50/30/20, the report's first line says which rows here changed.
2. **Draft the style as settings**, each range a fraction of today's ranking, with placeholders until theory's ranking lands (speedrun: minute 9). Simulate nothing.
3. **For every raise, write the planned answer to the next raise and the rate that proves it**: our open facing a 3-bet (continue 25-35% or more: C), our 3-bet facing a 4-bet. No line, no raise.
4. **Give heads-up and three-handed play their own rows now.**
5. **At the interface stub** (minute 6), map the draft to its settings; add self-check counters for position, blinds and players left.
6. **First report by minute 15**: the style report by players left, the heads-up open rate, each targeted rate with its n.

## 1. Before the flop: aggression, each raise with its planned response

| Finding | Numbers | Grade | Not 8-handed / other payouts |
|---|---|---|---|
| Top teams opened more | Top 20 opened first in 39-41%; field 30-35% | A | Width goes by seats left to act: pre-event bots opened 26% at 6-8 players, 37% at 4-5, 54% three-handed, 71% heads-up (C) |
| The winner re-raised wide and learned seats | 3-bet 34-39% of opens; a fresh opener 18%, 43% after that seat folded once, 62% after two (137,937 decisions) | A; "why it won" C | Flat payouts: light 3-bets near the bubble pay section 4's premium |
| The field folded to 3-bets | 59% rising to 70% (67% pooled, both regionals); Boston's top 20 fell 75% to 57.5% and 4-bet 9% to 23% | A | None; expect finalists near Boston's end point (C) |
| Bluff 3-bet break-even | 8bb over a 2.5bb open risks 8 to win 4: 65% folds | arith. | Antes lower it; payouts don't change it |
| A raise with no plan loses | v4 3-bet 58% and folded 96% to 4-bets: 9.17 points (100th of 125) against 19.02 before | B | None |
| Over-folding to 3-bets gets found | We folded 82-87%; the share of our opens 3-bet rose 15.6% to 28.1%; open profit fell 14.9 to 9.0 bb a table | A | None |
| Flat calls are as good as the play behind them | Pre-event bots lost on them (C). Real: v3b's flats made +5.9 bb a table; big-blind calls against the button went from -0.19/-0.37 points to +0.14 ± 0.03 once the postflop leak was fixed | A | None |
| Styles cycle in simulation | Wide +5.7 in an all-tight field, limp-or-shove +2.6 in all-wide, tight +2.3 in all-shove; within 1 point against top-20 clones; wide loses 3.0 without weak teams | C | 8 seats, 50/30/20 only |

## 2. After the flop: fold against the bluff rate

| Finding | Numbers | Grade | Not 8-handed / other payouts |
|---|---|---|---|
| Break-evens | A bluff needs folds of bet/(pot+bet): 25% at a third of the pot, 33% at half, 50% at pot. A call needs equity of 20%, 25%, 33% | arith. | A call for our stack near the bubble adds section 4's premium |
| The field over-folds to big bets | Fold to a flop bet 53% (both regionals): 29% at a third pot, 51% at half, 72% at pot | A, observational | None |
| Top teams bet when checked to | Flop: field 52% rising to 66%, top 20 67-72% | A; "it pays today" C | None |
| Calling down was the commonest leak | 17 of 30 self-reviewing bots; we folded 33% to flop bets against the leaders' 61%; the fix gained 2.3 points a table | A; fix B | None |
| The fix overshot | We then folded 73/66/78% by street against the field's 52/45/48%; opponents bet 90% of our checks; cost up to 0.9 a table | A; cost C | None |
| Big late bets and raises are value | Pre-event bots: 59-100% two pair or better, 1-7% air | C | None |

## 3. Short stacks: shove or fold by depth

| Finding | Numbers | Grade | Not 8-handed / other payouts |
|---|---|---|---|
| Where it starts | About 12bb first in; equilibrium tables hold there, not above about 15bb | C | Blinds drain a stack a third faster per hand at 6 seats, a fifth slower at 10 |
| The field shoves wide, calls tight | Open-shove 41% at 10bb or less, 22-24% at 10-15bb, 10-12.5% at 15-20bb; calls 17-20%; our own jams were called 7-16% | A | Fewer seats behind, fewer callers: 1 - (1 - x)^seats |
| Our jams beat folding | 112,894 jams: +0.03 to +1.42 points each, every stratum | A, observational | Winner-take-all: no premium, chip odds |
| Call at the ICM threshold for the seat's measured width, no wider | Calls with 5 or fewer alive beat folding (15,423 calls); but leaders called 14% of jams to our 21%, and calling 2-4 times as often cost 0.4-3.1 in simulation | A and C, in tension | Thresholds move with payouts |

## 4. Tournament equity under different payouts

Break-even equity to call all-in for our whole stack against an equal stack, all stacks equal, no dead money (arith.):

| Players left | 50/30/20 | Winner takes all | 65/35 | 60/25/15 | 40/30/20/10 |
|---|---|---|---|---|---|
| 8 | 55.6% | 50% | 52.6% | 54.3% | 58.3% |
| 6 | 58.1% | 50% | 53.8% | 56.2% | 62.5% |
| 5 | 60.6% | 50% | 54.8% | 58.0% | 66.7% |
| 4 | 65.2% | 50% | 56.6% | 61.2% | 64.3% |
| 3 | 57.1% | 50% | 60.6% | 55.0% | 60.0% |
| 2 | 50% | 50% | 50% | 50% | 50% |

- **The peak is one place outside the money**: 4 left with three paid, 3 with two, 5 with four. Heads-up is always chip odds; winner-take-all is chip odds throughout, and tight play loses its reason. (arith.)
- **Table size** moves only the first rows: hand 1 needs 58.1% at 6 seats, 54.8% at 9, 54.2% at 10. (arith.)
- **Unequal stacks, 50/30/20 bubble**: a middle stack covered by the shover with a short stack alive needs 73-75%; the short stack 56-62%; a big stack calling a shorter one 54%. Dead money at 10bb takes off 2-3 points. (arith.)
- **Bystander gain** when two other equal stacks collide: +0.4 points with 8 left, +1.2 with 6, +2.3 with 5, +5.8 with 4; zero under winner-take-all. (arith.; "so tight pays" is C: it needs measured collisions and arriving with chips.)
- **The library trap**: a function that scores a busted seat 0 reads 77% three-handed and 80% heads-up at equal stacks, against 57% and 50% (arith.). It cost us two rounds (A).

## 5. Heads-up and three-handed

| Finding | Numbers | Grade | Not 8-handed / other payouts |
|---|---|---|---|
| What is at stake | 1st against 2nd 20 points, 2nd against 3rd 10, 3rd against 4th 20 | arith. | 65/35: heads-up decides 30 |
| We missed thirds and firsts, not seconds | Rounds 5-6, official: we finished 1st/2nd/3rd in 23/14/10-11% against the top five's 24-25/13/12%, and cashed 47-48% against 49-51%. We busted more with 6 and 5 left (15% and 18% of the times we got there; 2 Curry and Lemonade 11-13% and 13-14%), mostly by raising all-in. Corrected 14 November from `notes/pre/placings.md`: the earlier "27/11/10 against 22/20/18" was round 1's bot against no real team | A | The costly stage is the approach to the first paid place |
| Wide heads-up aggression paid | First-in jams at 10-20bb +0.41 to +0.48 points each; big-blind re-jams over late opens +0.8 to +1.2 | A, matched hands | Chip odds under any payouts |
| Heads-up needs its own ranges and its own test | A release with no heads-up check lost 1.9 ± 0.4 a table; in mock builds three styles came out even heads-up (40 ± 0.5) | A; C | None |

## 6. What assumes standard hold'em

- **Does not transfer**: any range, the 169 hand classes, "one pair" as the hand that folds to raises, published charts (hold'em heads-up: any ace jams to 20bb, K2o to 11.6bb; A for hold'em only). In two of three mock variants pocket pairs lost most of their value, and a pressure style set by hold'em numbers scored 7.8-10 against 13-16 (C).
- **Transfers as priors**: sections 1-3. The two regionals matched within 1-3 points on every rate compared, despite different twists (A).
- **Transfers exactly**: section 4 and the break-evens.
- **Score level**: finalists average 12.5; our regional bots simulate at 14-15 against top-20 clones (C).

## Sources

Team archive (paths from the repo root):
- `finals_pack/strategy/EVIDENCE_TABLE.md` (grades; cross-regional rates; fold rates by bet size; withdrawn figures), `FIRST_PROMPT.md` Parts 1 and 6, `DECISION_RULES.md` section 5, `finals_pack/.claude/agents/stylist.md`.
- `research/finals_prep/adaptation/REPORT.md` with `res_q2.txt`, `res_q3c.txt`, `res_boston.txt` (open, 3-bet, fold and bet rates by round; the winner's per-seat rule).
- `research/finals_prep/metagame/REPORT.md` (the style cycle, top-20-only fields, call-off sweeps); `research/finals_prep/literature/REPORT.md` (families and counters, bystander gains).
- `docs/STEERING.md` (v4's collapse, jam and call studies, flat calls, finish distribution); `docs/writeup/avalon-writeup.tex` (results by round, the over-folding audit, the ICM defect, matched-hand jam studies).
- `rebuild/04_FIELD.md` (pre-event bots: open rate by players left, value share of big bets); `research/finals_prep/buildtest/` (mock variants); `finals_pack/prep/SPEEDRUN_14NOV.md`.

Computed for this note on 14 November (Malmuth-Harville, scratch arithmetic outside the repo): every figure marked arith. in sections 4 and 5. The 50/30/20 column reproduces the pack's 56% / 65% / 57% / chip odds and the literature report's bystander gains; the unequal-stack cases reproduce the pack's "65-74% with four left".

Outside sources:
- HoldemResources heads-up push/fold chart (hold'em, no ante): https://www.holdemresources.net/hune
- Break-even fold and defence arithmetic: https://www.pokerskill.com/glossary/alpha/ and https://www.vip-grinders.com/poker-calculators/minimum-defense-frequency-mdf-calculator/
- Risk premium in sit-and-gos (a 9-seat 50/30/20 hand-1 call needs about 54% against 49% in chips): https://www.pokerstrategy.com/strategy/sit-and-go/chip-value-risk-premium-concept/
- Miltersen and Sorensen 2007 (heads-up jam/fold within 1.4 percentage points of optimal at 8,000 chips, blinds 300/600): https://www.itu.dk/~trbj/papers/poker.pdf ; Ganzfried and Sandholm 2008 (three-player jam/fold): https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf . Both known here from search summaries only; the papers were not opened.
