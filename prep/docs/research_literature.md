# No Limit pokerbot: literature findings (2026-11-05)

**Later test results override two inferences below.** Our evaluator runs about 0.34 µs per 7-card hand, so "live Monte Carlo is noise" and "no live Monte Carlo" don't hold on the hardware tested: 40 rollouts took about 60 µs and scored slightly better than a lookup. Also, "use ICM as a baseline" lost points on top-heavy tables as we implemented it. See PLAYBOOK.md.

**Labels:** [S] = a source states it. [I] = my inference. Most pages were read through a summarising fetch tool. I read Ganzfried-Sandholm, ICM Out and CodeClash as extracted PDF text.

**Not obtained:**
- The Husky Hold'em full paper and leaderboard (OpenReview blocked, huskybench.com did not resolve)
- The Miltersen-Sorensen PDF (404, quoted via Ganzfried-Sandholm)
- Livschitz's original article (secondary coverage only)

## 1. LLM-authored and LLM-played poker

**Husky Hold'em Bench**
- [S] Claude 4 Sonnet topped the leaderboard. Top models played "balanced or aggressive" styles, lower-ranked models more defensively. Format: 5 refinement stages, 6-player round-robin. https://neurips.cc/virtual/2025/122372
- [S] 1,000-hand games, ranked by net winnings. https://github.com/NousResearch/huskyholdem-bench
- I found no VPIP figures and no description of the bots' architecture.

**CodeClash** (same poker engine)
- [S] Claude Sonnet 4.5 was top overall but 4th in poker. A round is won outright if yours is the only valid submission. https://arxiv.org/pdf/2511.00839

**PokerBattle.ai** (LLMs played directly; they did not write bots)
- [S] o3 won (+$36,691). Llama 4 lost its whole $100k with VPIP above 60%, nearly triple its rivals. The creator warned the sample is small. https://www.pokernews.com/news/2025/11/poker-bot-battle-results-49971.htm
- [S] Reported errors: fixating on own hand rather than range, misreading hands and boards, overreacting to small samples, rarely using showdown evidence, and calling or raising when uncertain. https://www.rockingrobots.com/llms-sit-down-at-the-poker-table-and-show-their-limits/

**[I] Expected field**
- Mostly preflop tiers, pot odds and bet heuristics, with varied looseness rather than one uniform leak.
- Some bots will run live Monte Carlo and time out, which auto-folds or checks them. Those bots are stealable.
- Few will have ICM calling discipline or heads-up aggression tuned.

**Correction to the premise:** the field is not purely hour-old Codex bots.
- [S] One public repo describes a 165 KB bot built for this event, with 49 thresholds tuned by evolution strategy over full tournaments. https://github.com/EthanXu07/poker-bot-overview
- [S] A public unofficial simulator exists. https://github.com/mack-dot/poker-gym
- [S] The rules are silent on pre-written code. They ban "copying another team's code". https://pokerbot.sequoiacap.com/rules.html
- [S] The announcement says "from scratch". https://x.com/sequoia/status/2115111389501218868
- [I] Ask a Gamemaster before submitting prepared code. Preparing knowledge and rehearsing are clearly safer.

## 2. Timed and student contests

I found **no** winner write-up showing simple heuristics beating CFR under tight compute. I found no UW, CMU, Jane Street or IMC post-mortem. A Citadel-labelled repo is a plan with no results: https://github.com/johnhawver/Poker-Bot

**CFR has won with long lead times**
- [S] MIT 2017 winner used CFR with abstraction. https://github.com/Fro116/Pokerbots

**GTO Wizard's MIT 2024 entry (5 days, milliseconds per action)**
- [S] Depth-limited solving with equity-based leaf values. Its authors said an MCCFR blueprint was probably best under the time limit.
- [S] The auction used only precomputed equity tables plus a multiplier chosen by simulation (1.8x). Placement is not given. https://github.com/gtowizard-ai/mitpoker-2024

**Most directly comparable data** (the author's own simulations on placeholder points, not official results; https://github.com/EthanXu07/poker-bot-overview)
- [S] Monte Carlo refinement was dropped: gain within noise, and some decisions exceeded 1 ms.
- [S] Early version finished second often and first rarely. Heads-up it folded about 77% preflop and kept about 25% of chips. Short-handed gates and endgame training raised heads-up wins to 60-63%.
- [S] Replacing the Chen formula with equity-ranked hand order helped.
- [S] Against a jam-every-hand bot it scored 49.2, against a 31.9 average.

**Within-table adaptation: evidence is thin**
- [S] A 2011 MIT thesis agent matched new opponents to a database of player styles; a simpler version won the 2011 3-player contest. https://dspace.mit.edu/handle/1721.1/85390
- [S] The Pluribus paper says exploitation techniques need too many samples to compete with human ability. https://www.science.org/cms/asset/910714a7-ee2a-486e-9970-42fb893b08d9/pap.pdf
- [S] In a 3-player jam/fold game, a fixed ICM policy sits $9,860 per hand (of a $1M pool) below best response to a 10% jammer. That is 26 times the gap against the solver opponent. https://arxiv.org/pdf/2608.09586
- [I] That gap makes a coarse read (how often this seat jams, opens, folds to steals) potentially worth more than refining the value model. Shrink hard to priors, because the mechanism is untested in 8-max and the isolated value of the opponent tree in the EthanXu07 bot is not reported.

**[I] Recommended approach**
- Build-time precomputed tables, with thresholds tuned by simulation.
- Light Bayesian-shrunk stats.
- No live Monte Carlo and no CFR.
- T4-T6 carry 71% of the weight (T6 alone 28.6%), and rules allow resubmitting. Use the time after the build phase for tuning. Rules do not promise logs between rounds.

## 3. SNG theory: usable numbers

**Heads-up: play chips**
- [S] Jam/fold is within 0.014 of game value at 8000 total chips and 300/600 blinds. Win probability is very close to chip share. https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0313.pdf

**3-handed, equal stacks of 7.5BB** (same paper; $100 pool)

| Decision | Tournament | Single hand |
|---|---|---|
| Button jam | .376 | .355 |
| SB jam, button folded | .652 | .633 |
| SB call, button jammed | .088 | .234 |
| BB call, SB jammed | .273 | .466 |
| BB call, button jammed | .145 | .308 |
| BB overcall, both jammed | .021 | .197 |

- [S] Opening ranges barely change, but **calling ranges collapse**. The BB overcalls only with the top pairs and AKs.
- [S] Average ICM error is $0.37 on a $100 pool. The paper's largest worked error is a big blind about to lose most of its stack to the blinds, which ICM overvalues.

**ICM limits** (https://arxiv.org/pdf/2608.09586)
- [S] ICM ignores seat and elimination pressure. True value runs button > SB > BB ($341.6k / $335.5k / $323.0k at equal 7.5BB stacks in that model).
- [S] Correcting for this moves jam frequency 14% on average, 32% on the button. Gain is $214 per hand and $938 when played to a finish.
- [S] The gain turns negative against very tight opponents, crossing zero between 30% and 40% opponent jam frequency.
- [I] Use ICM as a baseline, then add a position and next-blind adjustment.

**Bubble factor**
- [S] Worked example: calling needs 45.5% equity in chip terms but 69.72% under ICM. Mid-stacks should generally tighten and big stacks can loosen. https://www.cardplayer.com/?p=1034923
- [I] Required equity = BF/(BF+1), where BF is equity lost if you lose divided by equity gained if you win. BF 2 gives 67%. BF is 1 heads-up. Compute it with the kit's ICM.

**Push/fold** (secondary chart: 9-handed, chip-EV, no antes, folded to you; ignores ICM)
https://www.pokerskill.com/charts/push-fold/

| Stack | UTG | CO | BTN | SB |
|---|---|---|---|---|
| 5BB | 24% | 45% | 54% | 83% |
| 10BB | 18% | 34% | 44% | 69% |
| 15BB (chart's own estimate) | 15% | 27% | 36% | 56% |

- [S] Heads-up thresholds: 72o jams up to 2.1BB and calls up to 3.3BB. Push/fold is usually recommended up to about 10BB. https://www.holdemresources.net/hune
- I found no reliable chart by players left and M combined.

**[I] Structure**
- 16,000 chips in play and 8 levels over 200 hands. With the *synthetic* blinds from poker-gym (ending 200/400; https://raw.githubusercontent.com/mack-dot/poker-gym/main/docs/fidelity.md), four survivors average 10BB at the last level, so late play is push/fold territory. Recheck with the real schedule.
- First place may dominate. EthanXu07 found this under placeholder points (100/60/40/25/15/10/5/0). Read the real table before setting risk aversion.

## 4. Astra and public event information

**Astra**
- [S] GPT-6 Astra is OpenAI's flagship model, available in ChatGPT Work, Codex and the API. https://openai.com/index/gpt-6-astra/
- [I] "Astra and Codex" most likely means this model and the agent. The rules do not define it.

**Event**
- **No recaps exist.** The first regional is 6 Nov.
- [S] Rules: top 5 per regional advance. Variant and exact points are revealed at build start. Empty seats are filled with non-scoring bot copies. https://pokerbot.sequoiacap.com/rules.html
- [S] Brown ties the format to MIT's 6.9630, and Maguire promises "some plot twists". https://x.com/polynoamial/status/2115125429619343609 https://x.com/shaunmmaguire/status/2115131879452295182
- [I] This raises the odds of an MIT-style custom twist.

**Rehearsal: poker-gym** (unofficial; payouts and blinds marked SYNTHETIC; https://github.com/mack-dot/poker-gym)
- [S] Pure Python, 30-34k hands/s. Sparring bots: tag, lag, shortstack, icm, adaptive.
- [S] Supports re-ranking, pot-limit, hole-card counts and street sizes. Does not support short deck, wild cards, split-pot or multiple boards.
- [S] Its fidelity document lists as an open question what bots can see of others' actions and hands. That decides whether opponent tracking works.

## 5. Fast Python and variants

**Evaluators** (I found no independent 7-card benchmark in Python)
- [S] Treys: 3.23M standard hands/s on one core. https://pokerkit.readthedocs.io/en/latest/evaluation.html
- [S] Treys evaluates 7 cards by checking all 21 five-card subsets. https://github.com/ihendley/treys
- [S] Search snippet, not page-verified: pokerfast/eval7 about 269k 7-card evals/s, self-reported. https://pypi.org/project/pokerfast/0.1.0/
- [I] Treys implies at least 6.5 µs per 7-card eval. A 300 µs budget therefore allows at most about 23 heads-up rollouts, with a standard error near 10 equity points. Live Monte Carlo is noise, so use precomputed tables. Test whether non-stdlib imports work in the sandbox.

**Latency**
- [S] Poker-gym saw 1 in 214,293 calls over 1 ms, attributed to GC; 2-6 per 350k in another run. It warns organiser hardware may be slower. It assumes only `act()` is timed, which is unconfirmed. (poker-gym links above)
- [I] Rippling's production `gc.freeze()` case has no sub-millisecond data (https://www.rippling.com/blog/the-garbage-collector-fights-back). Import and build tables at module load, `gc.collect(); gc.freeze(); gc.disable()`, avoid per-decision allocation, make one warm-up call, wrap the body in try/except returning a legal default, and test p99.9 under load.

**Variants**
- [S] MIT history: Blotto 2021, Auction 2024 (https://github.com/gtowizard-ai/mitpoker-2024), bounty 2025 (https://spei04.github.io/projects/pokerbots/), and 3-hole-card discard 2026 (https://github.com/mitpokerbots/engine-2026). Poker-gym's author treats flush-over-full-house and pot-limit as examples only, not predictions.
- [S] Short deck: 81 hand classes rather than 169. Sets flop about 17% vs 12%. Open-ender completes by the river about 45.6% vs 31.5%. Flush draws have 5 outs, not 9. Flush usually beats full house, and some rooms rank trips above straights. https://www.pokernews.com/strategy/short-deck-holdem-part-2-odds-probabilities-33304.htm
- [S] Short deck compresses equities: AA vs KK 75% (81% full deck), 88 vs AK 45% (56%), JT vs AA 38% (23%). https://cardplayer.com/cardplayer-poker-magazines/66403-2018-poker-year-in-review-32-4/articles/23606-short-deck-preflop-equities
- Unverified: search snippets put double-suited AAKK in Omaha at about 67-70% vs random, compared with hold'em AA at about 85%. I could not open a page confirming this (pokerology.com returned 403), so simulate it.
- I found no reliable numbers for pineapple or double-board.
- [I] Compressed equities mean more calling and fewer dominated folds. Pot-limit removes open-jams, so push/fold charts do not transfer. Generate equity tables at build time from the kit's evaluator, parameterised on deck, hole count, board and ranking. Do not hardcode 169 classes.
