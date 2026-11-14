# The contrarian memo (drafted Saturday 14 November; both humans read this)

Notes only: designs are described in words; nothing here is bot code. Grades as in
`strategy/EVIDENCE_TABLE.md`: **A** measured at the regional, **C** judgment, model or simulation. Numbers are
from `notes/pre/field.md` (its Appendix A) unless a source is named.

## 1. The bot 19 teams will build

Same lessons, same agents, similar prompts. The consensus bot opens about 40%, 3-bets 25-40%, re-raises a seat
again once it has folded, c-bets 75-90%, folds one pair to a raise, shoves by chart when short and folds
65-75% to 3-bets. Our own styles and shared defaults describe it too. Every line was a best response to a
field that did not answer back (A: regional openers folded no less to a seat that had already 3-bet them six
times). A field made of that bot has three holes.

## 2. Three designs that beat it

| | Design 1: **re-aggressor** | Design 2: **postflop raiser** | Design 3: **collision harvester** |
|---|---|---|---|
| In words | Opens a little tighter than the field and never raise-folds: answers a 3-bet with a 4-bet (all-in at 40bb or less) or a call in position, by the 3-bettor's measured fold to 4-bets. Re-shoves over wide opens at 15-30bb. Defends the first 3-bet at every table | Plays the consensus preflop game, then attacks automatic bets: raises c-bets and bets rivers as bluffs at the break-even mix, check-raises seats that bet whenever checked to, and pays off raises less | Folds through the early levels except premiums, calls shoves only at the ICM threshold, then turns wide and aggressive with 4 or fewer left, where each collision between others is worth most, and plays heads-up and 3-handed to win |
| What it exploits | The wide bots folded 66-86% to 4-bets while the field 4-bet 7-8% (A). 2 Curry re-raised a seat 43% after one fold and 7% after one non-fold (A) | Regional top 20, round 6: c-bet 78%, bettor folds to a flop raise 63%, only 10% of bets raised, river folds 51% (A). Sequoia's recap: nobody bluffed the river. "Fold one pair to raises" is in every team's prompt, ours included | A bystander gains 0.4 points per collision with 8 left and 5.8 with 4 (exact for 50/30/20). Seventeen teams are told to be bold. In a speedrun the do-nothing bot matched ours |
| Evidence it wins | C. No regional team played it. The nearest simulation: limp-or-shove beat a pure wide field by 2.6 | C. Untested. thepastaway's round-6 jump (13.4 to 20.3) raised 34% of flop bets, among other changes | C in simulation: tight beat limp-or-shove fields by 2.3 and calling fields by 5.4. A at the regional: the tight class fell from 14.8 in practice 1 to 10-11 in scored rounds |
| Loses to | 3-bettors who have the goods (Boston's counter-wave, tight bots): 4-bets run into value. Shove-heavy fields, where there is nothing to re-raise. Deep stacks, where a 4-bet shove risks too much | Draft bots and callers (practice 1: 27% folds to a flop raise). The 20 regional teams that fold less to seats that bet often. A twist that changes postflop information | Stealers: wide pressure beat a tight field by 5.7 (C), and a fold-first bot reaches the last five short. Any field where six or more are still alive at hand 40 |

A fourth bet cuts across all three: **start where the field will end on the twist.** Boston's average auction
bid rose from 28 chips to 66 over six rounds (Sequoia's recap, search summary only), and a 2024 MIT auction
team found 1.8 times the naive value best. Fields under-use a new decision in round 1, then escalate.

## 3. Which one this field pays, from one practice round

A 1,000-table practice cannot rank three designs by score (standard error 0.7 points; it separates bots 1.4
apart). It **can** read the field's rates, which are far tighter (pooled field ±0.2 to ±1.5 points,
`field.md` section 3). So play one design and read all three preconditions from the same file.

| Design | Pays when (practices 1 and 2 pooled, teams that raise) | Don't build it when |
|---|---|---|
| 1 Re-aggressor | 6+ of 19 teams 3-bet 25%+ with PFR 30%+, **and** those teams fold 60%+ to 4-bets (about 600 chances pooled, ±2), **and** the field's 4-bet rate is under 12% | Fold to 4-bets under 45%, or fewer than 4 wide teams |
| 2 Postflop raiser | Field c-bet 75%+, bettor folds to a flop raise 55%+ (about 2,600 chances, ±1.1), flop raise rate under 10%; river fold above the break-even for our size | Folds to a flop raise under 40% (the practice-1 state at the regional), or raises already above 15% |
| 3 Collision harvester | 1.7+ all-in collisions per table before hand 40, 5.4 or fewer players left at hand 40, and the floor bot scores 10+ (regional practice 1: 1.8, 5.2, 10; scored rounds: 1.0-1.3, 6.1-6.5, 5-7) | Wide teams above a quarter of the field, or shove/limp teams under half (C, simulation) |

Two cautions. Practice 1 will look like design 3's field whatever the Finals turn into: at the regional it had
the collisions and a fold-everything bot scoring 10 (both gone by round 1) and sticky callers (gone by round
3). Re-read the table on practice 2 and round 1. And if no precondition holds, the field is not the consensus
field: that is the finding, and D or the best response to the measured mix takes the slot.

## 4. Only the top 3 are paid: what that does to risk

**The prizes are $100,000 / $50,000 / $25,000 (official rules); 50/30/20 is the points per table.** 4th earns
what 20th earns, and 1st earns four times 3rd.

- **Theory.** When fewer than half the contestants win (here 15%), more variance and less correlation with
  rivals both raise the chance of winning (Gaba, Tsetlin and Winkler 2004); the weak should maximise
  variability, the strong minimise it (Tsetlin et al. 2004; Cabral 2003). Everyone just behind the leaders
  has the same incentive (Hvide 2002): expect late rewrites.
- **Where our variance comes from.** A round's score is a mean over 10,000 tables (standard error about
  0.15), so a bot that gambles more per hand changes its mean, not our luck. Team-level variance comes only
  from **which design we field**. Regional top 20 (A): standing still moved -0.67 with SD 0.5, a rewrite
  -0.68 with SD 1.6; 24% of rewrites improved and no unchanged bot did.
- **Low correlation means not copying the leaders.** A copy of the top three converges to their score minus
  our deficit. Outside the top 3, prefer the design whose payoff depends on the field differently.
- **A model of the rest of the day (C).** 20 teams, weights 1-6, score levels that drift as the regional top
  20's did; each window we may field a challenger seen first through one practice (edge standard error 1.0).
  Chance of a final top 3, by our rank after round 3:

  | After round 3 we are | Tweaks only | Divergent challenger (SD 1.5, mean -0.5), played at z ≥ 0.5 | Very divergent (SD 2.5, mean -1.0) | Divergent, played blind |
  |---|---|---|---|---|
  | 1st-3rd | 47% | 59% | 65% | 32% |
  | 4th-5th | 27% | 39% | 47% | 20% |
  | 6th-8th | 17% | 28% | 37% | 14% |
  | 9th-12th | 9% | 19% | 27% | 10% |

  A near-copy challenger (SD 0.75) added only 3-4 points.

  The order held with flat weights and with a stickier field. Three readings:
  1. **How different the challenger is matters more than the bar.** Bars of z ≥ 1.0, 0.5 and 0 differed by 2
     points or less; the wider-spread challenger added 6-8 despite a worse mean.
  2. **The practice filter is what makes variance pay.** Playing blind is worse than standing still until we
     are 9th or lower with two rounds left (7% against 5%).
  3. **It pays at every rank**, so in the top 3 "protect" should mean keeping the filter, not dropping the
     challenger. From 2nd, a step up is worth $50,000 and a step down costs $25,000.
- **Left out of the model:** rivals doing the same, build time, and practice fields that differ from scored
  ones. The percentages are directions, not forecasts.

## Sources

- `notes/pre/field.md` and its appendix (regional rates, practice 1 against scored rounds, noise).
- `research/finals_prep/adaptation/REPORT.md` (2 Curry's seat rule; rewrites against standing still; redteam check 4 in `redteam/REPORT.md` for the field that did not answer back).
- `research/finals_prep/metagame/REPORT.md` (style matchups, simulation only); `literature/REPORT.md` (strategy families, bystander gains by ICM).
- Official rules, prizes and weights: https://pokerbot.sequoiacap.com/rules.html ; `prep/docs/official_rules.txt`.
- Sequoia's Bay Area recap: https://x.com/sequoia/status/2119839104733200785 . Boston's bid figures were seen only in a search summary of Sequoia's Boston post.
- MIT Pokerbots 2024 auction entry (1.8 times naive value): https://github.com/gtowizard-ai/mitpoker-2024
- Gaba, Tsetlin, Winkler, "Modifying Variability and Correlations in Winner-Take-All Contests", Operations Research 52(3), 2004: https://ideas.repec.org/a/inm/oropre/v52y2004i3p384-395.html
- Tsetlin, Gaba, Winkler, "Strategic Choice of Variability in Multiround Contests and Contests with Handicaps", Journal of Risk and Uncertainty 29(2), 2004: https://ideas.repec.org/a/kap/jrisku/v29y2004i2p143-158.html
- Cabral, "R&D Competition when Firms Choose Variance", JEMS 12(1), 2003: https://ideas.repec.org/a/bla/jemstr/v12y2003i1p139-150.html
- Hvide, "Tournament Rewards and Risk Taking", Journal of Labor Economics 20(4), 2002: https://econpapers.repec.org/RePEc:ucp:jlabec:v:20:y:2002:i:4:p:877-898
- The model: a throwaway script (no poker in it), 60,000 simulated days per case, deleted after the run. Levels: SD 1.5 across teams, round-to-round persistence 0.6, from the regional top 20. Abstracts only were read for the four papers.
- Not verified: that any finalist will play design 1, 2 or 3; that fold-to-raise and fold-to-4-bet rates carry to the Finals variant.
