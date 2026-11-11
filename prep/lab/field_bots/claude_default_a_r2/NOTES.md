# claude_default_a: notes

## Approach

A tight-aggressive, ICM-aware sit-and-go bot. Everything expensive is precomputed, and each decision makes at most one small eval7 equity call.

**Precomputed (`tables.json`, built offline with eval7):**
- A ranking of the 169 starting-hand classes (average of the heads-up and 3-way equity-vs-random ranks). Each class maps to a strength percentile (top X% of combos).
- The equity of every class against "top X%" ranges for 16 range widths (2% to 100%, 25k MC samples each). Preflop equity against any estimated range is a table lookup with interpolation.

**Built at import:** an eval7 `HandRange` for each width. Ranges wider than 360 combos are replaced by a stratified, re-weighted subsample with the same class mix. That cuts the cost of each equity call about 3x, and equity moves by less than 0.01. A warm-up pass runs, then `gc.freeze()`.

**Opponent model (kept in `memory`, about 350 bytes of JSON):** for each seat, counts of hands, VPIP, PFR, fold-to-preflop-raise, postflop bets/raises versus checks/calls (aggression), fold-to-postflop-bet, and first-in open-raise frequency split by position (early: 4+ players behind, late: 1-3 behind). All of it comes from `state.events`, with Bayesian priors. Per-hand counting context is carried in memory, so the stats stay correct across turns and after replays.

**Preflop:**
- *Unopened pot:* the open range depends on how many players are left to act (13% UTG up to 58% SB). It is scaled by those players' fold-to-raise rate (steal more against folders). Iso-raise over limpers with a tight range. Sizes are 2-2.5bb, or 3bb from the SB.
- *Effective stack ≤ 13bb (≤ 16bb with limpers):* shove or fold by ICM expected value. Each player behind calls with the hands that have enough equity against our perceived shoving range at their pot odds. That fraction is scaled by their VPIP and fold-to-raise. Outcomes are scored with ICM on the real stacks and payouts (exact Malmuth-Harville for 3 paid places, about 3 µs).
- *Facing a raise:* the raiser's range comes from their observed open frequency for that position (or PFR × 0.4 for 3-bets, × 0.2 for 4-bets; shoves are widened by stack depth). We value re-raise when our equity against that range is ≥ 0.585 (opens) or ≥ 0.56 (3-bets). Flat calls need realization-discounted equity above pot odds, with small implied-odds bonuses for pairs and suited hands. Facing an all-in, or a raise that commits us, we compare call, fold and re-shove by ICM. With ≤ 25bb, re-shove beats flatting.

**Postflop:**
- Each opponent's range width starts from their preflop role and stats. It narrows with every bet (× (0.15 + aggression)) and every raise (× (0.12 + 0.7 × aggression)). Bets from maniacs therefore narrow almost nothing, and bets from passive players narrow a lot.
- Equity comes from eval7 against the tightest opponent's range: Monte Carlo (260 iterations) on the flop and turn, exact on the river, raised to a power for multiway pots.
- *Checked to us:* value bet at ≥ 0.60 equity (0.75 pot, or 0.95 pot with nutted hands against callers). C-bet as the preflop aggressor, with frequency driven by the opponents' fold-to-bet. Bluff players who fold a lot. Occasionally semi-bluff in position.
- *Facing a bet:* raise at ≥ 0.80 equity (0.86 on the river). Call when equity ≥ pot odds + a margin (0.06 in position, 0.10 out of position, 0 on the river). If the call commits us, or the bettor is all-in, decide by ICM.

**Safety:**
- Action kinds are normalized, so enum or string kinds both work. Every raise total is an int clamped to `[min_amount, max_amount]`, and we never fold when checking is free.
- Any exception falls back to check/fold. Memory is validated and rebuilt if it is malformed.
- If `time_bank_ms` is under 30 (for example the upload test) the Monte Carlo drops to 100 iterations. If more than 0.3 ms has already passed in the decision, it drops to 50.

## What I tested

1. **`play.py`** (upload test plus the default 8-seat mix with check_or_fold and min_raiser) after every change.
2. **Engine and opponents:** play.py's opponents are trivial, so I wrote a small NLHE SNG engine in my scratch area using only the fake SDK types. It has the same blind schedule, payouts, ICM at the hand cap, side pots and bust-order rules. I also wrote proxy opponents modelled on likely field bots:
   - `tag`: chart-based, equity vs random hands postflop.
   - `aggro`: wide opens, 3-bets and c-bets, with bluffs.
   - `station`: loose-passive caller.
   - `nit`: very tight.
   - Copies of my own earlier version (`v1`), standing in for strong AI-built bots.
3. **A/B testing:** parallel runs with common random numbers per table, usually 6-8k tables per variant, in two fields:
   - **F1** = me, v1, tag×2, aggro×2, station, nit
   - **F2** = me, v1×3, tag, aggro, nit, station

   What the tuning showed:
   - **Preflop flat-calling was the biggest leak.** Scaling the call-realization factor by 0.5 raised F1 from about 18.7 to 21.2 and F2 from about 17.1 to 19.0. Results were flat between 0.5 and 0.25.
   - **Respecting postflop bets more** helped: bet-narrowing base 0.25 → 0.15, and call margins of +0.06 in position / +0.10 out of position. F2 reached about 19.8.
   - Flatting less in the 13-25bb re-shove zone (realization 0.85 → 0.6) gained about +0.8 in F1 and +0.5 in F2.
   - Estimating open ranges from position-specific open frequencies beat both PFR alone and a fixed positional multiplier. The fixed multiplier hurt against opponents that ignore position.
   - Open-size multiplier, push threshold, 3-bet threshold and shove-call modelling were all within noise.
4. **Timing:** measured as thread CPU time per decision, because the machine was heavily loaded by other jobs (load average 50-110 on 15 cores) and that inflated wall-clock times. Final bot: p50 39 µs, p99 101 µs, max 207 µs. At 2.5x slower that is about 250 µs at p99 and about 520 µs at worst, under the 1 ms limit before any time bank is used. The rare wall-clock spikes over 1 ms in `play.py` happen when the OS deschedules the process under that load. They are not compute.
5. **Robustness:** string action/event kinds, malformed memory, missing state fields, and 8 copies of itself. There were no illegal actions or exceptions in any run. The only failures ever seen were wall-clock timeouts in that one run under heavy machine load.

## Final results

`play.py --tables 400 --seed 1` (default seats: self×4, check_or_fold×2, min_raiser×2):

| seat type | mean points | se | places 1st..8th |
|---|---|---|---|
| self (4 seats) | **22.93** | 0.48 | 389 / 378 / 295 / 71 / 83 / 252 / 131 / 1 |
| check_or_fold | 3.34 | 0.28 | 0 / 20 / 104 / 321 / 289 / 66 / 0 / 0 |
| min_raiser | 0.80 | 0.22 | 11 / 3 / 0 / 9 / 27 / 84 / 325 / 341 |

- **Upload test:** passed (10 decisions, 0 failed, no crash).
- **Failed decisions across the 400 tables:** none.
- **Latency over 196k decisions:** p50 34 µs, p99 89 µs, p99.9 146 µs. 7 decisions went over 1 ms (load spikes, covered by the time bank).
- **Memory:** at most 428 bytes.
- **Benchmarks:** fair share is 12.5, and 25 is the ceiling for 4 seats. One earlier run used a near-final version (before the short-stack-call change), one `self` seat, 4× check_or_fold and 3× min_raiser, for 300 tables. It scored 30.0, and 17 decisions timed out on wall clock while the machine was at load average 85. The bot's own CPU time stays under 0.25 ms.

Own harness, final version against my first version v1 (6000 tables each, common random numbers):

| field | final bot | v1 | proxies |
|---|---|---|---|
| F1 (me, v1, tag×2, aggro×2, station, nit) | **22.63** ± 0.27 | 19.79 | tag 11.2, nit 11.9, aggro 9.3, station 4.7 |
| F2 (me, v1×3, tag, aggro, nit, station) | **19.40** ± 0.27 | 16.57 | tag 9.9, nit 9.8, aggro 8.0, station 3.2 |

## Caveats / ideas not done
- The proxy opponents are my guesses at the field. Most of the tuning gain came from tightening preflop and postflop calls, which should hold up against value-heavy bots. It may be too tight against heavy bluffers, although the aggression-aware range narrowing covers some of that.
- Not done: semi-bluff raises, check-raise bluffs, river bluff-catching from showdown data (`show` events), and per-opponent tracking of calls against all-ins.

---

# Round 2 version (`claude_default_a_r2`)

Round 1: **15.31 ± 0.68**, 4th of 22. Fair share is 12.5; the leaders scored 17.6. We finished top-3 as often as the leaders (43.6% vs 44.5%) but won far less often (17.6% vs 25.5%). We survive, but we don't build a big enough stack to win.

## What the hand histories showed

I analysed 16,994 hands from 120 tables with my own scripts.

**1. We fold far too often when someone raises.**
- Facing a single raise in the blinds with a deep stack, we folded 86% of the time (1777 of 2058 hands, -1344bb in total).
- The calls (+1.18bb each) and 3-bets (+1.77bb each) we did make were profitable.
- Other players open about 45-55% from late position, so this fold rate gets exploited.
- When our open got re-raised, we folded 88% of the time (215 deep hands, -2.5bb each).
- Our rare 4-bets and calls in that spot won 3-7bb each.
- Overall we fold to preflop raises 85% of the time, the highest in the field (others: 65-83%).

**2. We are passive after the flop.**
- Our bet/raise share after the flop is 0.38. The two leading teams are at 0.71.
- Most of the field folds about 50-60% of the time to a bet after the flop, so betting more often wins pots.

**3. We lose when calling bets from passive opponents.** When the opponent made the last bet, our showdowns netted -573bb. Most of that came from the passive `openai_*` bots, which only bet with strong hands. Against the aggressive `claude_*` bots, calling broke even or made money.

## Changes

**Preflop:**
- Raised the assumed 3-bet range from PFR × 0.4 to PFR × 0.55.
- Facing a 3-bet, we now consider a 4-bet all-in by ICM expected value up to 40 big blinds (was 25).
- Light 3-bets against wide openers who fold often: required opener range ≥ 25%, fold-to-raise ≥ 0.55, any hand in the top 6-35% (suited, or top 20%), 30% of the time.
- Big-blind defence is wider: realization factor 0.78 × 0.7 instead of × 0.5.
- Small-blind calls, cold calls and calls against 3-bets keep the tight factor.

**After the flop:**
- C-bet frequency raised (base 0.55 → 0.65).
- Stab/bluff when checked to heads-up now fires when the opponent folds to bets at least 52% of the time (was 62%).
- Bets from passive players count for more: the range-narrowing factor is `0.1 + 1.25·af^1.3` instead of `0.15 + af`.
- Calling a river bet from a passive player (aggression < 0.35) now needs +4% extra equity.

## Local results

**A/B test:** I added a `field` stand-in opponent shaped on the round-1 stats (late opens about 50%, positional ranges, wider blind defence, frequent c-bets). Then I tested 6000 tables of r2 vs r1 with seats me, r1, field×4, aggro, tag.

| r2 variant | r2 | r1 |
|---|---|---|
| All changes, full blind/SB/3-bet call widening | 18.79 | 19.69 |
| Postflop changes only | 19.73 | 19.69 |
| 3-bet + postflop changes, calls left tight | 19.57 | 19.81 |
| **Final (BB-only call widening)** | **19.56 ± 0.25** | 19.72 |

My stand-in disagreed with the real data on wider flat calls. So the final version only partly widens big-blind defence. It keeps the 3-bet/4-bet and postflop changes, which were neutral against the stand-ins and backed by the round-1 data.

**`play.py --tables 300 --seed 1`:**
- self: **23.26 ± 0.55** (r1: 22.93 at 400 tables). check_or_fold 3.15, min_raiser 0.33.
- Upload test passed, 0 failed decisions, memory at most 428 bytes.
- Wall-clock spikes in this run came from load: my A/B job was running at the same time as the other jobs on the machine. CPU time per decision was p99 128 µs and max 220 µs.
