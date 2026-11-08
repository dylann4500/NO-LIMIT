# TUNING: the dials, and which incoming number moves each one

v4 makes every decision the same way:
1. **List the legal candidates:** fold, check, call, bet/raise at 0.33 / 0.66 / 1.0 pot, and all-in.
2. **Score each one with one chip value function.** P is the pot, C the cost to call, e our equity against the villains' ranges, and B our bet size.
   - `Q(fold) = 0`
   - `Q(check) = e · R_chk · P`
   - `Q(call) = e · R_call · (P + C) − C`
   - `Q(bet/raise B) = F_b · P + (1 − F_b) · (e_called · (P + X + Y) − X)`, where X is the chips we add and Y the chips a caller adds.
     - `F_b = F · (0.85 + size_slope · min(1, B/P))`, with `F = ∏ fold_to_bet` over live villains.
     - `e_called = e ^ (1 + called_k · (F_b + 0.5 · min(1.5, B/P)))`
3. **Apply the masks:**
   - **ICM** (≤ `icm_players` alive): all-in calls and jams must clear the points-EV threshold, using Malmuth-Harville over `state.config.payouts`.
   - **No bluffs without fold equity:** skip bets with `e < bluff_min_e` when `F < bluff_min_F`.
   - **Pot-size bets for value only:** a pot-size bet needs `e ≥ 0.55`.
4. **Pick** from `softmax((Q − Qmax) / (temp · P))` over the candidates. `temp = 0.02` means a candidate 2% of the pot worse is picked about 0.37× as often as the best. That's mixing only among near-ties.

Preflop unopened pots use percentile cut-offs instead of a Q score: open if `pct ≤ open_w[behind] · open_scale`, and at ≤ `push_bb` jam by points EV with ICM on, otherwise by the `shove_width` table. Facing a raise, preflop uses the same Q over fold / call / 3-bet / jam.

All dials live in `K` at the top of `bots/<ver>/agent.py`.

## Dials (current v4 value), the signal from each 10-minute result, and which way to turn
| # | Dial | Now | Signal from `analyze_hh.py` / STEERING | Rule |
|---|---|---|---|---|
| 1 | `open_scale` | 1.00 | our VPIP/PFR vs top teams; how often our opens get 3-bet or jammed | 3-bet/jammed > 25% → −0.1. Opens taking the blinds > 60% → +0.1 |
| 2 | `push_bb`, `push_scale` | 12, 1.6 | our jam rate (7.4% vs top 4.0%); share of our busts from our own jams | busts from our jams > 25% → `push_scale` −0.2 |
| 3 | `icm_players`, `icm_margin` | 5, 0.0 | our 1st/2nd/3rd shares vs top (22/20/18) | 4th/5th > 25% → raise `icm_margin`. 1st collapsing → lower it |
| 4 | `jam_call_q`, `jam_call_w` | 0.12, 0.10 | how often the field calls our jams (7-16%) | set `jam_call_q` to the measured call rate |
| 5 | `jam_w_short`, `jam_w_deep`, `jam_prior` | 0.30, 0.15, 0.03 | field jam rate by depth; hands shown on jams; our call-jam rate (21% vs 14%) | set from shown jam hands. Our call-jam rate above the top teams → −0.05 |
| 6 | `threebet_F`, `jam_F` | 0.55, 0.60 | field fold-to-3-bet and fold-to-jam | set to the measured rates |
| 7 | `pre_call_R` | 0.80 | our chips won/lost on preflop flats | flats losing → −0.05 |
| 8 | `fold_prior` | 0.45 | field fold rate facing postflop bets (45% now) | set to the measured rate |
| 9 | `size_slope` | 0.45 | field fold rate by bet-size bucket (small / medium / big) | fit the slope from the buckets |
| 10 | `called_k` | 1.00 | our win rate when a bet of ours gets called | won < 45% when called → +0.2 |
| 11 | `R_call`, `R_chk_*` | 0.90, 0.92/0.82 | chips lost on turn/river folds after calling (about 7 / 12 bb each in round 2) | big losses after calling → −0.05 on `R_call` |
| 12 | `bet_narrow`, `raise_narrow` | 1.15, 1.30 | what villains show after big turn/river bets and raises (share of two pair or better) | two pair+ > 70% → lower (narrower ranges) |
| 13 | `bluff_min_e`, `bluff_min_F` | 0.45, 0.50 | won-without-showdown rate of our low-equity bets | bluffs win < 50% → raise `bluff_min_F` |
| 14 | `reveal_random` | True | reveal A/B (live v3 vs v3b, local A/B) | the reviewer decides |
| 15 | `temp` | 0.02 | none directly; it's an anti-exploit width | leave it, unless opponents measurably adapt to us |

## Loop each round (about 10 minutes)
1. Check failures first: any automatic decisions, restarts or tracebacks get fixed before anything else.
2. Run `starter-kit/.venv/bin/python tests/analyze_hh.py <download> --top 15` and read the rows that feed dials 1-13.
3. Change **one or two dials**, picking the biggest measured leak, in a copy `bots/vN+1`.
4. Gate it, with the tests in parallel:
   - `tests/validate.py`
   - the no-bank upload test (`tests/match.py --bank 0 --hand-cap 20`)
   - a paired 8-seat run: new ×3, old ×3, previous ×2, 2 seeds × 250 tables
   - then `tests/fuzz.py` **alone**, with max < 1 ms
5. Pack `releases/vN+1.zip` and update `releases/LATEST.txt`. The reviewer gates it, and only zips marked SAFE get uploaded.
