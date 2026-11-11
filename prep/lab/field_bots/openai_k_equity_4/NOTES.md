# openai_k_equity_4

A range-equity bot for the documented eight-seat Hold'em sit-and-go. Production loads `agent.py` and the included `equity.json`. No simulator internals were read or imported by our bot or verification scripts. All simulator matches were run through `lab/field_kit/play.py`.

## Design

- **Preflop:** 169 hand classes, 11 opening/continuing-range widths, and precomputed equity against one through seven random opponents. The asset uses 80,000 Monte Carlo samples per hand/range pair and 8,000 joint multiway deals per hand. Playability and premium blockers determine the range ordering. Multiway equity is calibrated to actual joint simulations rather than blindly multiplying heads-up equity. `build_multiway.py` adds 4,000 joint trials per hand at top-5%, top-18%, and top-50% ranges for two through seven opponents; the live bot interpolates the resulting correlation curves.
- **Ranges:** position, opening versus reraising, deep oversized opens, previous calls, current street aggression, bet size, and prior street pressure influence the range. Made strength and real hole-card flush/straight draws reweight postflop combinations. Known cards are removed. eval7 ignores its nominal range weights, so the bot implements weights by systematic resampling of combinations.
- **Learning:** per-table memory tracks VPIP, preflop raises, actions, separate preflop/postflop folding, and revealed strength of preflop raisers. Bayesian priors reduce early overreaction; extreme folders and persistent indiscriminate raisers receive specific responses.
- **Equity:** heads-up uses a vectorized 192-candidate range model, 512 live eval7 runouts, and a separate 320-runout estimate against continuing hands. Rivers use exact equity against the sampled weighted range. Multiway hands use collision-free joint simulations and smaller range samples, with exact fractional ties. Side-pot layers include folded dead money and their eligible contestants.
- **Decisions:** compare calls with pot odds and equity realization, allow small pair implied-odds calls, and compare several bet/raise sizes with checking/calling. Bet EV includes fold probability and equity against continuing hands. Short-stack opening shoves enumerate the opponents' call/fold distribution using cached equity products and effective amounts at risk. Value reraises and selective heads-up bluffs complement positional opening ranges.
- **Tournament points:** exact ICM prices large calls. Late heads-up pots and late short-stack shoves also compare expected prize utility where computation permits. This discourages unnecessary large-stack collisions while short stacks remain. Generic configured payouts are supported. Simultaneous hypothetical busts are ordered by each player's stack at the start of the hand, with equal starting stacks sharing the affected payout positions.
- **Runtime:** all card objects, range metadata, draw tables, random schedules, and equity assets load at import. Decisions have a 0.74 ms soft deadline with early stopping and smaller samples for crowded pots. At less than 30 ms of remaining bank, or when preparation has already used the allotted model budget, the agent reuses cached range combinations or fixed preflop range samples and reduces simulation work. All game-specific data lives in returned memory, never on `self` or in shared globals.
- **Legality:** actions are selected from offered Enum kinds. Every raise is an integer explicitly bounded by that action's minimum and maximum. Effective opposing stacks limit intended bet sizes, and the bot avoids bluffing into protected all-in pots.

## Iterations and testing

1. Initial 200-table default mix: **16.03 ± 0.75 points/seat**, no failures. Independent synthetic tests identified excessive work in crowded postflop pots.
2. Corrected position, improved opening-range order, reduced multiway work, and added exact ICM call prices: **16.78 ± 0.74**, no failures over 200 default tables. An additional 200-table 2.5× timing run also had no failures.
3. Added side-pot equity, separate postflop response statistics, showdown evidence, prize EV for late bets, faster shove enumeration, vectorized heads-up ranges, hole-card draw validation, and bank preservation. The side-pot stage scored **18.72 ± 0.60** with no failures over 300 tables.

`verify.py` independently exercises **3,360 randomized valid decision states plus 840 cold/warm low-bank decisions**, including board transitions. It checks legal kinds and raise endpoints, split pots, weighted side pots, ICM conservation and configured payouts, straight-draw contribution, simultaneous-bust ranking, protected all-in blinds, interchangeable copies, and memory size. It also checks the ranged multiway lookup against its calibration samples. All checks pass. It reports both CPU and wall time.

The shared build host briefly reached load averages above 85 on 15 CPUs. One intermediate 300-table run recorded 246 timeouts, including wall pauses above 100 ms; another intermediate stress run also suffered timeouts. The former is retained in `results/contended_intermediate_300.json` rather than hidden. A later 500-table run had five timeouts during another contention spike (maximum wall latency 126 ms), retained in `results/contended_rank_500.json`. A calibrated intermediate 2.5× run also recorded 14 timeouts with a 190 ms maximum wall pause (`results/contended_calibrated_slow_200.json`). The final implementation includes bank preservation and earlier deadline checks; final timing results are reported below. Timing-wrapper tests add CPU work, not multiples of scheduling pauses. No test has reported an illegal action or exception.

## Final results

Default mix: `self,self,self,self,check_or_fold,check_or_fold,min_raiser,min_raiser`.

- **500 default-mix tables, seed 20261106:** **19.45 ± 0.46 points per bot seat**, versus 12.5 fair share. Upload passed; **268,394 decisions, zero failures**. First through third places: 481 / 395 / 150 across 2,000 team seats. Maximum memory: **1,258 bytes**. Wall latency p50/p99: **63.3 / 1,046.9 μs**. Host scheduling pauses are included; the time bank covered overruns. Full report: `results/final_default_500.json`.
- **200 default-mix tables at 2.5× measured CPU cost, seed 876:** **19.20 ± 0.74 points**, upload passed, **104,773 decisions, zero failures**. Wall latency p50/p99: **162.1 / 1,025.1 μs**. Maximum wall time was 16.2 ms; the bank covered these isolated pauses. Full report: `results/final_slow_200.json`. `timing_check.py` reproduces this test without multiplying OS descheduling delays.
- **100 tables, seven copies plus one min-raiser, seed 781:** **14.21 ± 0.69 points per team seat**, **95,841 decisions, zero failures**. Full report: `results/final_mostly_self_100.json`.
- **100 tables, one copy versus seven min-raisers, seed 782:** **37.40 ± 0.97 points**, 37 firsts and 63 seconds; **2,301 decisions, zero failures**. Full report: `results/final_maniacs_100.json`.
- **50 tables, one copy versus seven check-or-fold bots, seed 783:** **50.00 points**, won every table; **6,245 decisions, zero failures**. Full report: `results/final_folders_50.json`.

Across the final **950 tables / 477,554 decisions**, every upload test passed and there were **zero timeouts, illegal actions, or exceptions**. Maximum observed returned memory was **1,581 bytes**. Earlier contention failures remain documented above. `results/manifest.json` records hashes of the exact tested agent and equity asset. The `±` values are the field kit's reported standard errors.

Reproduction (from the workspace root):

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_k_equity_4/verify.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_kit/play.py lab/field_bots/openai_k_equity_4 --tables 500 --seed 20261106
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_k_equity_4/timing_check.py --tables 200 --seed 876
```

`build_tables.py` followed by `build_multiway.py` rebuilds the offline asset if desired; rebuilding is unnecessary for upload. Keep the supplied asset for the tested version. Live heads-up Monte Carlo is stochastic, so a simulator seed alone does not make scores bit-for-bit identical.

The available opposition consists of the two kit baselines and this bot's copies. These results establish legality, runtime behavior, and strength against that field; they do not establish a win rate against unknown tournament teams. Range inference, future equity realization, multiway preflop calibration, and multiway prize utility remain approximations rather than an exhaustive game-tree solution.
