# claude_gto: approximately GTO sit-and-go bot

## Approach

Brief: precomputed ranges by position and stack depth, balanced value and bluffs, mixed strategies, sizing that's hard to exploit, and precomputation done up front.

**Offline tables** (built by the scripts in this folder; `agent.py` only loads the `.npz` files):
- `build_tables.py` → `pf_tables.npz`: a 169x169 heads-up all-in equity matrix (eval7 Monte Carlo, card removal handled, symmetrised) plus each class's equity against 2, 3 and 5 random hands.
- `build_pushfold.py` → `push_tables.npz`: approximate Nash push/fold strategies for an unopened pot, solved by fictitious play for 1 to 7 players left to act and stacks of 1 to 30bb. Callers best-respond per seat, with the SB and BB posts modelled. Sanity checks: SB vs BB at 10bb pushes about 58%, and UTG 8-max at 10bb pushes about 11%. Both are close to published charts.

**At import** (about 0.13s): a hand ranking (blend of heads-up and multiway equity plus a small playability bonus); equity-vs-top-x% tables on a 0.5% grid, so equity against any percentile range or band is an O(1) lookup; multiway correction factors; the ranked 1,326-combo list used for range sampling; then `gc.freeze()`.

**Preflop**
- Unopened pot: GTO-style open frequencies by players left to act (UTG 14.5% up to BTN 42% and SB 50%). Opens mix linearly across a 2.5% boundary band, and the size depends on stack depth. At 12bb or less (15bb in the SB) it switches to the Nash push/fold tables, with stack depth scaled by the actual dead money (limps, antes).
- Facing a raise: the villain's range comes from the action level (open, 3-bet, 4-bet and so on), their position, and observed PFR. The value raise region is the top 22-45% of their range. Bluff 3-bets and 4-bets use suited blocker hands (A2s-A5s, suited connectors) at mixed frequencies of 35% and 18%. Flat calls are decided by equity times a realisation factor (position, implied odds) against the pot odds.
- At shallow depth or high levels, it compares fold, call and jam in **ICM** dollars. For a jam, the villain's calling range is their best response: the hands in their range whose equity against our jam range meets their price.
- All-in calls use an exact Malmuth-Harville ICM required equity, plus a small skill premium (3% equity while 8 players remain, falling to 0 at 3) when risking at least half the stack.

**Postflop**
- Equity against each opponent's range (up to 3 opponents) uses eval7's C routines: Monte Carlo on the flop and turn, exact on the river. Each range is sampled from that player's preflop band and narrowed by their postflop actions. A bet keeps the top f of the range by made-hand strength (f scales with observed aggression) plus 1 in every 3, 4 or 6 of the rest (by street) as bluffs and draws. Calls trim the bottom. Multiway equity is the product of the per-opponent equities with a correlation correction.
- Betting uses balanced two-size play. Merged value bets are small (flop c-bet 1/3 pot, 50-55% on later streets). Polar value and bluffs share one larger size (66%, 75%, 85%). Slow-play is mixed in about 12% of the time with the nuts on early streets. Bluff frequencies are fixed by street, initiative and position, and scaled by 0.7.
- Facing bets: value raises (mixed at 85%), rare semi-bluff raises (8%), and calls on pot odds plus a margin, with ICM for large calls.

**Memory:** per-table, per-seat counts (hands, VPIP, PFR, postflop bets and passive actions, fold-to-bet, faced-raise/re-raise) as JSON, about 300 bytes.

**Safety:** every decision is wrapped in try/except with a check-or-fold fallback. Raise totals are ints clamped to `[min, max]` and only offered kinds are returned. Action kinds are read as enum or string.

## What I tested

1. **Upload test:** passes (0 failures).
2. **Spot tests** (hand-built states): open, fold and 3-bet choices by position; BB defence; 9bb CO pushes; BB calls against a 10bb jam. These caught a bug where closed all-in calls were discounted by the realisation factor; fixed.
3. **CPU time per decision** (thread time, final version, 40 tables): preflop p50/p99/max = 31/119/262µs; postflop ≈ 105/225/344µs. That's about 0.9ms worst case at 2.5x slower, with the 100ms bank as a buffer. Wall-clock latency in `play.py` was dominated by machine load: other teams' runs pushed the load average above 100, giving wall p99 around 5ms. The few timeouts below come from that, not from the bot's own compute.
4. **A/B harness** (private, in my scratchpad): seat-dispatched variants against a heterogeneous field of hand-written archetypes (station, nit, maniac, pusher, TAG, check-or-fold, min-raiser). Every comparison was run in both seatings, because seat order biased results by about 2 points. The noise floor was about ±1 point per comparison.
   - Rejected because they were neutral or negative: widening steals against over-folders; scaling bluffs by observed fold-to-bet; widening re-raise ranges by observed 3-bet frequency (-2.1, dragged us into flips against maniacs); stronger narrowing on raises. They stay in the code as flags, all off.
   - Kept: bluff multiplier 0.7 (0.5 tested +0.76, 0.25 tested -1.2); skill premium (neutral, kept because the theory supports it).
   - Neutral: thinner value thresholds, ±15% opening ranges, 1.35x bet sizes.
5. **Robustness:** 2-, 3-, 6- and 9-seat tables run with no crashes or illegal actions.

## Final `play.py` results (default seats: 4x self, 2x check_or_fold, 2x min_raiser; fair share 12.5)

| run | self mean pts | check_or_fold | min_raiser | self places 1..8 (of 800) | failed |
|---|---|---|---|---|---|
| 200 tables, seed 1 | **19.65 ± 0.74** | 10.32 | 0.38 | 197/163/49/35/135/143/77/1 | 34 timeouts / 114,752 (load) |
| 200 tables, seed 2 | **19.34 ± 0.74** | 11.07 | 0.25 | 198/155/46/39/126/146/89/1 | 20 timeouts / 110,937 (load) |

Upload test: pass. Memory used: at most 306 bytes. In the mixed archetype fields the bot averaged about 17.5 points per seat against a fair share of 12.5.
