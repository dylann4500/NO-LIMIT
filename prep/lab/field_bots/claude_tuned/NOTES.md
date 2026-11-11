# claude_tuned

The brief was to build a parameterized bot, then use simulation to search for good parameters. The bot has 60
tunable numbers covering ranges, thresholds, bet sizes and opponent-model weights. A separate simulator tuned them
against a field that is broader than `check_or_fold` / `min_raiser`.

## Files

- `agent.py`: the bot (`Agent` at module level). The tuned parameters are the `P0` dict at the top.
- `pf_tables.json`: precomputed preflop tables, read at import from the bot's own folder.
- `tools/`: offline tooling only. The bot never imports it.
  - `build_tables.py`: builds `pf_tables.json` with eval7 (about 5 s on 14 cores).
  - `sim.py`: my own 8-seat SNG engine on the fake SDK objects. It has side pots, rising blinds, bust order and
    ICM at the hand cap. I wrote it from the README rules and did not use the lab simulator.
  - `opponents.py`: opponent archetypes.
  - `tune.py`: tuning and evaluation driver (`eval`, `grad`, `agrad`, `compare`, `search`).
  - `scenarios.py`: hand-built decision checks.
  - `params_v0.json`: the untuned starting point. `tuned_g1/g2/a.json` are the tuning checkpoints.
  - `*_log.txt`: tuning logs. `play_final_default.json`: the final 1000-table `play.py` report.

## How the bot plays

**Preflop.** All 169 hand classes are ranked by a blend of heads-up and 3- and 5-way equity. The tables also hold
each class's equity against "top x%" ranges for 13 values of x, and against 1 to 7 random hands.
- **Unopened pots, deep stacks:** open by the number of players left to act (`open_ep`, `open_mp`, `open_co`,
  `open_btn`, `open_sb`). Steals widen when the blinds have been seen to over-fold (`steal_adapt`). The bot
  isolates limpers and raises from the big blind with strong hands.
- **Unopened pots at or below `shove_bb`:** shove or fold by **ICM expected points**. Each player behind calls with
  a modelled fraction of hands (`sc_base`, `sc_exp`, `bb_call_mult`), adjusted by that seat's observed
  fold-to-raise rate. Equity when called is the hand's equity against that calling range. The fold option is
  charged `fold_tax` big blinds for rising-blind pressure. Plain ICM made short-stack play too tight, and both
  tuning runs pushed toward shoving more.
- **Facing a raise:** the raiser's range comes from their observed PFR rate (`pfr_prior`, `rng_mult`), narrowed per
  re-raise (`rr_mult`) and widened for short all-ins (`sv_base`). All-in or committing calls compare ICM EV of
  calling, re-shoving and folding. At or below `reshove_bb` the bot weighs a re-shove against folding. Deeper,
  it 3-bets, 4-bet-jams, calls or folds using equity thresholds and pot odds plus a margin.

**Postflop.** eval7 Monte Carlo equity (500 iterations; exact on the river) is computed against an eval7 range
estimated from the preflop action and each seat's VPIP/PFR. Ranges are prebuilt at import. With several opponents,
equity is raised to `1 + mw*(n-1)`.
- **Facing a bet:** the bettor is assumed to hold the top `f` of their range, so equity becomes `eq^(1/f)`. `f`
  depends on the street (`bf1..3`), the bet size (`bs_exp`), the bettor's observed aggression (`af_adapt`) and
  raises on the street (`raise_f`). The bot raises above `rz*`, calls above pot odds plus `cm*`, and otherwise
  folds. Big all-in calls use ICM.
- **Checked to:** value-bet above `vb*` at `bs*` of the pot. C-bets (`cbet`) and bluffs (`bl*`) are scaled by
  opponents' observed fold-to-bet rate (`fold_adapt`). Small stack-to-pot ratios jam (`jam_spr`, `commit_frac`).

**Memory.** Compact JSON of nine counters per seat: hands, VPIP, PFR, faced and folded to a preflop raise,
postflop aggressive and passive actions, faced and folded to a bet. It also holds the parse state of the hand in
progress. It is under 300 bytes and nothing carries between tables.

**Safety.**
- Every decision runs inside try/except and falls back to check, else fold.
- Actions are built only from offered kinds. Raise totals are ints clamped to `[ceil(min), floor(max)]`, and the
  bot calls when no raise is offered.
- Action kinds are normalized by name, so the bot works whether the SDK uses enums or strings.
- A time guard switches to an 80-iteration estimate against a narrower range if more than 200 µs have already
  passed before the Monte Carlo step.
- An import-time warm-up exercises every code path, and `gc.freeze()` runs after import.
- ICM is O(n²) for 3 paid places. A cheap approximation covers more paid places, in case a round changes `payouts`.

## Tuning method

`check_or_fold` and `min_raiser` are too weak to tune against, so `tools/opponents.py` adds archetypes of what a
60-minute AI-assisted build tends to produce:
- TAG equity-threshold bot
- loose-aggressive
- calling station
- nit
- push/fold bot
- maniac
- "flaky" TAG that times out on 15–60% of its decisions and falls back to check/fold
- copies of this bot at the current base parameters (self-play)

Each table's opponent parameters get ±25% jitter. The mixed field weights are tag 3, lag 1.5, station 1, nit 1,
pusher 1.5, maniac 0.5, mirror 2.5, flaky 1.5, min-raiser 0.3, check/fold 0.4.

Testing one parameter at a time didn't work. A paired 840-table comparison had a standard error of about 0.48
points, because small decision changes cascade over a 160-hand tournament. Instead I used a **random-perturbation
regression**. Every candidate seat (4 per table, 6000 tables per iteration) gets an independent ±1-step perturbation
of all 57 searched parameters. OLS of points on the coded perturbations then estimates every parameter's effect at
once. The search used 2 pre-search iterations, then 7 pooled iterations. Data from the last 3 iterations is pooled
and recentred on the current base, which gives a standard error of about 0.07 points per step. A parameter moves
half a step when |t| > 2.2.

The main moves:
- more c-betting: `cbet` 0.55 → 0.85
- more flop and turn bluffs, and more bluffing against folders: `bl1` .12 → .18, `bl2` .10 → .16, `fold_adapt`
  1.0 → 1.6
- call flop bets wider: `bf1` .60 → .97
- give turn bets more credit: `bf2` .50 → .32
- tighter early-position opens and wider SB opens: `open_ep` .13 → .085, `open_sb` .42 → .66
- more short-stack shoving and calling: `fold_tax` 0.7, `sv_base` .28 → .315, `sc_base` .17 → .19
- tighter deep calls: `call_margin` .06 → .09

The last tuning run stopped at iteration 7. A min-raise war between two simulated `min_raiser` bots hit the
simulator's loop guard. I fixed the guard, and the bot is not involved. Iteration 6's parameters are final.

## Results

**Tuned vs untuned (`tune.py compare`, 2800 paired tables per field, 2 candidate seats):**

| field                    | untuned v0 | tuned | diff          |
|--------------------------|-----------:|------:|---------------|
| mixed tuning field       |      19.76 | 20.49 | +0.73 ± 0.29  |
| self-play (vs v0 copies) |      12.53 | 15.56 | +3.03 ± 0.30  |
| tag / flaky / pusher     |      22.13 | 22.22 | +0.08 ± 0.28  |
| loose / station / maniac |      23.00 | 23.06 | +0.06 ± 0.27  |
| weak (cof / minr / flaky)|      28.63 | 28.76 | +0.13 ± 0.23  |

The tuned version is better or equal in every field, and much better head to head against its own untuned version.

**Final `play.py` runs (fair share 12.5):**

- Default mix, `--tables 1000 --seed 1` (4 self, 2 check_or_fold, 2 min_raiser): upload test **pass** with 0
  failed decisions. self **22.10 ± 0.31**, check_or_fold 5.49, min_raiser 0.32. Places 1–8 for self:
  989 / 926 / 558 / 132 / 330 / 721 / 331 / 13. 572,806 decisions, **0 failed**, memory max 291 B.
- All self, `--tables 400 --seed 2`: 12.5 by construction, **0 failed** decisions.
- `self×2, check_or_fold×3, min_raiser×3`, `--tables 400 --seed 2`: self **31.0 ± 0.73**, 0 failed.
- Default mix, `--tables 200 --seed 9` (final file): self 22.1 ± 0.7, 0 failed, upload pass.

**Latency.** The machine was heavily loaded during these runs by processes that weren't mine (load average
50–95 on 15 cores), so `play.py`'s wall-clock maxima (2–10 ms) and `over_1ms` counts (3–91) reflect OS scheduling.
No decision failed, because the time bank absorbed them. Per-decision **CPU time** over 107k decisions is p50 about
25 µs, p99 179 µs, p99.9 242 µs, max 333 µs. On the 2.5x slower machines that is a worst case of about 0.85 ms
against the 1 ms limit. Preflop decisions take about 20–50 µs. Postflop is dominated by one eval7 call of about
60–110 µs.

## Caveats

- The tuning field is my guess at the real field. Moves that exploit specific archetypes (heavy c-betting, wide
  flop calls) carry the most risk. The compare table shows they do not hurt in any of the five fields I tried.
- `open_ep` 0.085 means the bot folds 77 under the gun at 100bb. It is tight but cheap.
- The approximation for more than 3 paid places is rough. It only matters if a round changes `payouts`.

Reproduce: `.venv/bin/python lab/field_bots/claude_tuned/tools/tune.py compare --other lab/field_bots/claude_tuned/tools/params_v0.json --tables 2800 --seed 777`
