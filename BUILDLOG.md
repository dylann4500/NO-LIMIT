# BUILDLOG

## Step 0 — Minute-10 bot (`bots/m10`, snapshot `releases/m10_agent.py`, `releases/m10.zip`)
What: kit template + 09_TONIGHT "Minute-10" rules.
- select: keep best 2 of 3 by (made category, draw value, eval7 value, high cards); expose the kept card not pairing the board / not in the flush draw / the lower one. Any error -> (2, 0).
- preflop: playable if some pair of the 3 is 66+, both >= T, or suited ace. Open 2.5 bb, shove <= 10 bb, call small raises, 3-bet premiums.
- postflop: top pair or better bets 2/3 pot or calls; else check/fold. Thread env vars set to 1; all ints.
Tests:
1. `poker-agent check` OK; `pack bots/m10 releases/m10.zip` OK (3,070 B).
2. Fuzz 100k states (19,794 select): illegal 0, raised 0, mem max 61 B. Laptop latency p50 5.7 us, p99 108 us, p99.9 236 us, max 2.6 ms (single outlier).
3. Heads-up vs check_or_fold, 20 hands, bank 0, seeds hu1-hu5 x 20 tables: failed 0 every seed.
4. 8 seats (m10 x4, check_or_fold x2, min_raiser x2), 200 tables, seed full1: m10 15.97/seat (17.05, 16.75, 16.20, 13.90), check_or_fold 16.18, min_raiser 1.88. Failed 0 everywhere.
Note: harness found `poker_engine` DEFAULT_VARIANT is plain hold'em; tests pin `flop_discard_reveal`.

## Step 1 — v2 (`bots/v2`, release `releases/v2.zip`, source snapshot `releases/v2_src/`)
What changed vs m10:
- Engine: build-time Monte Carlo over all 1,755 canonical 3-card classes (each side keeps best 2 on the flop): strength pct + equity vs top-w widths {.05,.10,.20,.35,.50,1}. Rebuilt at 10,000 / 3,000 samples (18 s on 12 cores); AA+x now flat at ~0.81, 222 near bottom.
- Select: eval7 MC (200 it) of each kept pair vs a "best-2-of-3-like" range (top 60% of sampled combos on this flop); expose the kept card that leaks least. Deadline-guarded; (2,0) on any error.
- Preflop: 03_STRATEGY open widths by players behind, push/fold <= 12 bb, raise-width model (per-seat PFR, shover widths widened for the field), value 3-bet / committed shove / small calls by table equity.
- Postflop: per villain, exact range {exposed card + every live hidden card}, dead = our cards + discard + all exposed; narrowed by their bets/raises/calls (03 factors incl. bet size and street); eval7 MC vs that list; product over villains. Facing bet: committed / value raise / call by odds. Not facing: 03 bet-size EV with per-seat fold-to-bet (prior 0.55).
- Platform: memory envelope v2 (per-seat stats counted at hand end, ~450 B), legality funnel, try/except, warm-up incl. select, gc.collect/freeze/set_threshold(20000,50,100), act()-anchored 0.30 ms MC deadline.
Tests (laptop):
1. check OK; pack OK (agent.py + tables_bayarea.json + build_tables.py). Import 45 ms.
2. Fuzz 100k: illegal 0, raised 0, mem max 456 B; p50 61 us, p99 160 us, p99.9 275 us. Seed 777: 0 decisions > 1 ms (max 598 us). Seed 12345 has 2 spikes (2.7, 2.6 ms) that do NOT reproduce (same states replay in 21-154 us) -> OS/timer jitter.
3. Heads-up vs check_or_fold, 20 hands, bank 0: seeds hu1-hu5 x 40 tables + hu6 x 100: failed 0.
4. Gate (same run, seed gate1, 400 tables): v2 x4 15.06/seat vs m10 x2 10.84 (check_or_fold 18.02, min_raiser 0.05). Failed 0.
   Also: mixA (v2 x2, m10 x2, examples, 400 t) v2 18.74 vs m10 15.52; mixB (v2 x4 vs m10 x4, 400 t) 14.22 vs 10.78.
   Official-rules schedule (cap 200, 25 hands/level, 300 t, pre-rebuild tables): v2 16.87 vs m10 17.03 (tie, within SE ~1.3). Kit/portal schedule is 250 / 20.

## Step 2 — v3 (`bots/v3`, release `releases/v3.zip`, source `releases/v3_src/`)
What changed vs v2 (calibrated to the practice-round field data in STEERING 18:46):
- fold_to_bet prior 0.55 -> 0.45; bets with equity < 0.45 are skipped unless the target's per-seat fold-to-bet product >= 0.50 (fewer bluffs, value bets unchanged).
- Reveal 50/50 between the kept cards (handoff §6.4); old heuristic kept behind K["reveal_random"].
- Opens tightened: by players behind {1:.40, 2:.33, 3:.27, 4:.23, 5:.21, 6:.20, 7:.20}; short-handed floor .45 -> .40.
Tests (run in parallel, own seeds):
- check OK; validate.py: replay mismatches 0, all 6 select actions valid incl. all-in seats, hostile select inputs 0 invalid.
- Fuzz 60k: illegal 0, raised 0, mem 456 B; p50 71 us, p99 223 us, p99.9 330 us, max 3.2 ms (measured while 3 match processes shared the CPU).
- No-bank upload test, seeds hu31-35 x 30 tables: failed 0.
- Head-to-head (v3 x4, v2 x2, check_or_fold, min_raiser), seeds h2hA + h2hB, 200 tables each: v3 14.76 / 14.19, v2 12.80 / 14.78 -> v3 14.48 vs v2 13.79 (+0.7, within noise). Failed 0.
- Earlier reveal-only variant (no prior/open changes) lost 13.45 vs 14.84 over 500 tables (seed gate3), so the 50/50 reveal alone doesn't win locally; local bots barely read reveals, so its value is against field bots that do.

## Step 3 — housekeeping (STEERING 18:49) + reveal A/B (STEERING item 2)
- `releases/` now holds only zips (+ LATEST.txt). Removed v2_src/, v3_src/, m10_agent.py (sources live in bots/). Table builder moved to tools/.
- Reveal A/B (v3 50/50 vs v3_lr least-leak, + v2 reveal-readers, examples), 2 seeds x 350 tables:
  revA: v3 13.23, v3_lr 15.20, v2 13.19 | revB: v3 15.14, v3_lr 14.00, v2 12.74 -> 700 tables: least-leak 14.60 vs 50/50 14.19 (+0.4, seeds disagree: within noise). Reviewer/user decide; v4 keeps 50/50.

## Step 4 — v4 (`bots/v4`, `releases/v4.zip`; alt `releases/v4n.zip` = identical with ICM off)
What changed vs v3:
- Single-file bot: tables embedded as a Python literal (agent.py 140 KB, import 60 ms); missing-table fallback heuristic.
- One value function over legal candidates (fold / check / call / 0.33,0.66,1.0 pot / jam) + softmax (temp 0.02 pot) for postflop AND preflop-facing-raise. Dials consolidated in K; see TUNING.md.
- Per-seat jam tracking (hand-start stacks from `stack` events, committed chips per hand), Beta prior 10 @ 3%; jam-call width = max(floor, 1.3 x jam rate); short-jam floor 0.40 -> 0.30.
- ICM (Malmuth-Harville via poker_agent_sdk.icm on state.config.payouts) when <= 5 players alive: unopened jams by points EV (field call prob 0.12/player, caller width 0.10), re-jams masked if points EV < fold, all-in calls masked below the ICM equity threshold.
Tests:
- check OK; validate.py: replay 0 mismatches, 6/6 select actions valid incl. all-in, hostile select 0 invalid.
- decide() probe, 24k betting states (half with most seats busted to hit ICM): 0 exceptions (no hidden fallback-to-passive).
- No-bank upload test: v4 hu51-55 x 30 tables failed 0; v4n hu61-63 x 30 failed 0.
- Clean fuzz ALONE 100k: illegal 0, raised 0, mem 668 B, p50 71 us, p99 168 us, p99.9 270 us, max 834 us.
  (Earlier clean run had a 2.5 ms max: the state replays 50x at 75-340 us and repeat sweeps peak at 449/571 us at different states -> OS jitter.)
- Gate vs v3 (v4 x4, v3 x2, examples): pre-ICM-jam build g4A/g4B 500 t: 15.87 vs 11.76. Final build g5A/g5B 500 t: 14.99 vs 14.49. Failed 0.
- ICM paired (v4 x3, v4_noicm x3, v3 x2), iA/iB 500 t: ICM 13.06 vs no-ICM 13.76 vs v3 9.77.
  Places ICM vs no-ICM: 1st 12% / 15%, 2nd 13-16% / 10-14%, 3rd 13% / 12% -> 2nd+3rd up ~3 pts, 1st down 3 pts. Local field calls jams more than the real field (7-16%), so this undercounts ICM's steal value.

## Step 5 — v4 post-mortem (STEERING 19:18: real field 9.59 pts, 97th; v3b 19.02, 7th)
New tools: `tests/stats_check.py` (hero VPIP/PFR/postflop bet+raise share in an 8-seat field: hero, v3b, station x2, maniac, tag x2, hero) and `tests/opponents/{station,maniac,tag}` field proxies.
- Calibration (150 tables, seed cal1): v3b local VPIP 27.6 / PFR 23.1 / post agg 57.8 vs real 29 / 23 / 59. v4 local 36.9 / 34.1 / 64.6 vs real 42 / 40 / 64 -> the check reproduces the real-field gap. (Postflop "raise share" = bet+raise share of all postflop actions; raise/(raise+call) would be ~80% for both.)
- **Diagnosis: v4's PFR jump is the preflop facing-raise 3-bet candidate.** v4 with only `threebet_F` 0.55 -> 0.00 (bots/v4_no3b): VPIP 36.9 -> 26.7, PFR 34.1 -> 19.4. The fixed 55% fold equity makes Q(3-bet) = 0.55*P + 0.45*(...) beat fold/call with almost any hand (e.g. P=4bb, 3-bet to 7bb: Q ~ +2 bb vs call ~ +0.3 bb), and ignores 4-bets. Postflop agg stays 62.6% without it (v4's candidate betting also over-aggresses: above the 60% cap).

## Step 6 — v5 (`bots/v5`, `releases/v5.zip`) = v3 + two flagged changes; tables embedded (single file, import 50 ms)
- (a) `river_bluff_fix` ON: on the river, a live villain whose exposed card + board already beats our hand gets fold prob min(rate, 0.08) in the bet EV -> no bluffs into visible strength.
- (b) `icm_mask` ON, ported icm_* helpers from v4 only (no softmax / candidates / jam tracking):
  - (b2) `icm_mask_calls` ON: <= 5 alive, heads-up all-in / committing calls (pre and post) must clear the Malmuth-Harville equity threshold on state.config.payouts.
  - (b1) `icm_mask_jams` OFF: masking our own jams failed the stats check (see below).
Stats check (150 tables each):
| build | VPIP | PFR | post agg | result |
|---|---|---|---|---|
| v5 with b1+b2 (seed s5a / s5b) | 21.8 / 22.1 | 17.8 / 18.2 | 58.3 / 55.4 | FAIL |
| b1+b2, icm_players 4 | 22.2 | 18.2 | 58.2 | FAIL |
| river fix only | 27.8 | 23.0 | 55.3 | PASS |
| **v5 final: river + b2 (s5a / s6b)** | **28.0 / 28.4** | **23.2 / 23.9** | **55.9 / 55.5** | **PASS** |
Gate vs v3b + field proxies (v5 x2, v3b x2, station x2, maniac, tag), f6A/f6B 250 tables each: v5 20.96 / 21.76 vs v3b 19.78 / 19.50 -> **21.36 vs 19.64 (+1.7)**; places v5 25/19-20/14-17% vs v3b 23/17-20/12-13%. Failed 0.
(The b1+b2 build lost this gate badly: 17.3 vs 22.6, 1st 11% vs 36%: jam masking over-folds.)
Other tests: validate.py 0 replay mismatches, 6/6 select valid, hostile 0; decide() probe 23.8k states (5.9k river, half near-bubble) 0 exceptions.
No-bank upload test run alone: seeds hu81-85 + hu71 x 30 tables, failed 0. (hu71 earlier showed 28 failures for v5 AND 18 for check_or_fold while 6 jobs shared the CPU = contention.)
Fuzz 100k: illegal 0, raised 0, mem 456 B, p50 61-64 us, p99 159-184 us. Max 2.49 ms / 1.27 ms in two runs while the reviewer's gate processes were at ~95% CPU each (load avg 5.6); worst state replays x30 at median 74 us, max 159 us, and lands on a different state each run -> preemption, not code. Build-box gate is the authority on latency.

## Step 7 — v6 (`bots/v6`, `releases/v6.zip`) = v5r + two flagged postflop rules (STEERING 19:35; REPORT.md section 6 rules 1-2)
Base: bots/v5 with `icm_mask_calls: False` (= v5r, live). ICM jam masking stays off. No preflop code touched; flop c-bets untouched except into a visible pair.
Changes and the real-field leak each fixes:
1. `visible_pair_rule` (REPORT section 1: calling a bet with one pair that beats their visible pair -6.27 bb, n=1,946; first-in one pair / air bets -1.45 to -3.66 / -1.61 bb vs checking +0.6 / +0.73).
   Heads-up, villain's exposed card pairs the board, our hand is one pair (incl. top pair) or air:
   never bet (any street); facing a flop/turn bet fold, except two pair+ or a flop flush draw.
2. `fold_weak_vs_hu_bet` (REPORT section 6 rule 2: air calls -1.6 to -1.8 bb, middle-pair calls -2.1 to -3.6 bb, n~9k).
   Heads-up flop/turn facing a bet, visible card not pairing the board: fold air and middle/bottom pair; keep top pair / overpair and better, and flush draws.
   Both fold rules skip calls needing < 15% equity (`rule_min_odds`), so tiny bets are still called. River behavior unchanged (river_bluff_fix stays on).
Hand classes (`hand_class`): strong = trips+/straight/flush made with hole cards, or two pair using both hole cards; top = pair of the top board card or overpair; weakpair = lower pairs; air = hole cards add nothing.
Expected frequency moves (all intended): HU flop/turn fold-to-bet UP (real field 42% -> 50-55% target); HU flop bet into a visible pair DOWN (test: <= 35%); everything else flat, preflop flat.
Tests:
- Rule unit probes, 11 hand-built spots: all as specified (v6 folds / checks where v5r called / bet; two pair, flush draws, top pair vs non-pairing card, and the river unchanged).
- validate.py: replay 0 mismatches, 6/6 select valid, hostile 0. decide() probe 18k postflop states (60% forced heads-up): 0 exceptions.
- Behavior diff, stats_check field (hero, v3b, station x2, maniac, tag x2, hero), 150 tables per run:
| metric | v5r (d1 / d2) | v6 (d1 / d2 / d4) | intended? |
|---|---|---|---|
| VPIP | 28.4 / 27.0 | 27.7 / 28.7 / 28.9 | flat, yes |
| PFR | 23.7 / 22.5 | 22.9 / 24.4 / 24.4 | flat, yes |
| postflop bet+raise share | 54.9 / 57.8 | 50.9 / 52.0 / 50.9 | down ~5 (follows from rule 1) |
| HU flop/turn fold-to-bet | 9.4 / 11.6 | 25.5 / 20.8 / 23.8 | UP, yes (proxy field folds less than real) |
| HU flop bet into visible pair | 79.7 / 81.9 | 9.4 / 10.4 / 13.3 | DOWN, yes (<= 35% test passes) |
| HU flop bet otherwise (c-bets) | 95.6 / 95.4 | 94.8 / 96.1 / 96.3 | flat, yes |
  Stats check: PASS on all three v6 seeds.
- No-bank upload test, idle CPU, seeds hu91-95 x 30 tables: failed 0.
- Failed decisions inside stats_check runs (100 ms bank): 1-3 per run spread over ALL bots incl. v3b's copy and the trivial maniac; one run during a CPU burst had 332 across all 8 bots. act() catches exceptions and the legality funnel can't emit illegal actions (fuzz: 0 illegal / 0 raised), so these are timeouts from machine load.
- Fuzz 100k, 0 illegal / 0 raised / mem 456 B in every run. Latency could NOT be measured cleanly: load avg 9.4-10.5 from other processes. Paired under the same load: v5r p50 72 / p99 293 us, max 5.9 ms; v6 p50 82 / p99 350 us, max 524 ms (a whole-process stall; worst state replays at median 68 us). v6's only extra work is hand_class (2 eval7 calls) heads-up postflop. Build-box gate is the authority on latency.

## Step 8 — v7 (`bots/v7`, `releases/v7.zip`) = v6 + flags 1, 2, 4 ON; flag 3 coded but OFF
v6's fold rules and thresholds untouched (visible_pair_rule, fold_weak_vs_hu_bet, rule_min_odds 0.15).
Flags, and the real-field leak each fixes:
1. `reveal_random: False` -> v3b's least-leak `expose_index` (never reveal the card pairing the board). Samuel r2 natural experiment: revealing top pair -0.27 +- 0.05 pts/hand. Expected move: none in betting stats.
2. `icm_mask_calls: True` -> v5's exact path. REPORT "FOR THE v7 BUILD" 1: bites only where ICM break-even >= 10 pts over pot odds (13% of calls), where calls lose (postflop -2.07 +- 0.77). Expected move: tiny drop in <=5-alive all-in calls.
3. `late_steal_widen` -> coded per spec (CO/BTN/SB first in, >= 3 alive, >= 15 bb: top 45%; 45-60% band only with >= 5 alive per the 19:58 user tweak, best-2 HU equity >= 0.535; 2.2 bb from CO or < 25 bb, else 2.5 bb). **OFF: failed the stats check in every form.**
4. `bb_fold_oop_weak: True` -> BB, >= 3 alive, single non-all-in open from a non-SB seat, no callers: a v6 "call" with pct > 0.30 becomes fold; jams / 3-bets / top-30% calls / SB-open spots unchanged. Expected move: BB fold-vs-open up, VPIP down ~1-2.
New build-time table: `tools/hu2_equity.py` -> 169-class HU equity vs random (40k MC each; AA 0.851, 22 0.501, 33 0.536, A2o 0.549, K5o 0.535, QJo 0.577, J9s 0.555, 72o 0.345) embedded as HU2. Cutoff 0.535 (spec says >= 0.54 but lists "any pair 33+", and 33 = 0.536); 0.54 tested too: no difference.
Probes: late-steal 7/7 spots (BTN/CO/SB open band hands, UTG unchanged, band off at 4 and 3 alive, on at 8 and 5); BB-fold 4/4 (fold vs CO open outside top 30%, top-30% call kept, SB open and open+caller unchanged). validate.py OK; decide() probe 24k states 0 exceptions.
Stats check, run one at a time with nothing else running, 150 tables, seed e1 unless noted:
| build | VPIP | PFR | late open 8-6 | late open 5-3 | EP open | BB fold/call/raise | result |
|---|---|---|---|---|---|---|---|
| v6 | 29.0 | 24.1 | 35.8 | 41.7 | 22.1 | 25/37/38 | PASS |
| v7 all 4 flags (e1 / e2) | 31.0 / 31.1 | **27.3 / 27.2** | 62.4 / 62.2 | 52.1 / 51.8 | 22.1 / 23.4 | 48/11/41, 52/15/34 | FAIL (PFR) |
| all 4, cutoff 0.54 | 31.1 | **27.4** | 61.8 | 52.0 | 23.4 | 42/15/43 | FAIL (PFR) |
| all 4, top-45% only (no band) | 30.5 | **26.3** | 50.7 | 49.4 | 22.9 | 45/16/39 | FAIL (PFR > 25; inside reviewer gate 17-27) |
| **v7 shipped: flags 1, 2, 4** | **27.2** | **23.4** | 37.1 | 39.9 | 21.9 | **46/14/39** | **PASS** |
v6 postflop behavior preserved in every v7 build: HU bets into a visible pair 5.0-8.6% (v6 7.3), HU flop bets otherwise 97.5-98.4% (v6 96.1), HU flop/turn fold-to-bet 22.8-29.3% (v6 26.0).
Why flag 3 overshoots: with three hole cards, almost every 45-60% hand's best two cards clear 0.54 vs random, so the band adds about its full width; locally 8-6 late opens go 36% -> 62% (target 50-55%). Top-45% alone hits 50.7% but PFR 26.3%.
No-bank upload test, alone, seeds hu101-105 x 30 tables: failed 0. Fuzz 100k alone: illegal 0, raised 0, mem 456 B, p50 62 us, p99 163 us, p99.9 272 us, max 838 us (worst state replays at median 23 us).

## Step 9 — v8 (`bots/v8`, `releases/v8.zip`) = v7 + 3 flags, all ON (v6 fold rules and v7 flags untouched)
All three only change preflop decisions where v7 FOLDS (post-filters in `decide()`), except late steal, which widens v7's first-in open range.
1. `hu_jam_widen` (STEERING 20:13). Exactly 2 alive, eff 10-20 bb: (a) first in as SB/button, or (b) BB facing a single non-all-in open. Where v7 folds and pct <= 0.75 -> jam. Requires raise to be legal (else it would become a call).
   Evidence: Samuel R1/R2 matched-hand tests, HU first-in jams at 10-20 bb +0.41 to +0.48 pts per jam vs fold; BB-vs-open jams +0.8 to +1.2. Reviewer o1: 2-3 alive unopened jams beat folding in every strength band (weakest +0.48, n=6,463).
2. `hu_open_broadway` (addendum). Exactly 2 alive, eff 10-40 bb, first in as SB/button: where v7 (after hu_jam_widen) folds a hand with two T+ cards or any ace -> open 2.2 bb (< 25 bb) / 2.5 bb. Precedence: at 10-20 bb with pct <= 0.75, hu_jam_widen's jam wins.
   Evidence: Samuel R1/R2/R3, two-broadway opens +0.26 to +0.41 pts vs fold, Ax +0.15 to +0.44.
3. `late_steal_widen` ON, top-45%-only form (`steal_band_alive: 99`, no 45-60% band) = the bots/v7_top45 build. CO/BTN/SB first in, >= 3 alive, >= 15 bb: open every pct <= 0.45 hand. Reviewer allows PFR <= 27 for this flag only.
   Evidence: our own late opens with 25-45% hands beat folding in o1 and o2 (+0.64 to +1.08 bb); top-11 median opens BTN 56% / SB 80% vs our 45% / 55%; we lose most ground to the top two at 5-8 players.
Expected behavior moves (all intended): unopened raise rate UP at 8-5 alive (late steal) and heads-up (hu_open_broadway); heads-up unopened jam rate UP (hu_jam_widen, plus BB re-jams vs larger opens). Nothing else.
Probes / sweeps (vs a build with only the flag under test removed):
- hu_jam_widen: (a) jams at 15 and 20 bb where v7 folds (10 bb: v7 already jams), unchanged at 9 bb, 21 bb, 3 alive, pct 0.753; (b) jams vs a 4 bb open at pct 0.73 where v7 folds (vs a 2.1 bb open v7 already re-jams the whole <= 0.75 range), unchanged at 9 / 21 bb, 3 alive, all-in open, pct 0.760. Sweeps: (a) 5,000 spots -> 405 changes, all fold->jam at 15-20 bb; (b) 5,000 -> 105 changes, all in scope. 0 out-of-scope.
- hu_open_broadway: A54 at 30 bb opens 2.5 bb where v8a folds; 40 bb in, 41 bb / 9 bb / 3 alive / non-broadway unchanged; 10-20 bb overlap -> jam. Sweep 6,000 vs v8-without-hu_open: 106 changes, all fold->open at 25-40 bb, 0 out-of-scope.
- late steal: BTN top-45% opens, 45-60% band hand folds (band off), UTG unchanged; 0 differences at 2 alive.
- validate.py OK; decide() probe 24k states (half heads-up-alive) 0 exceptions.
Stats check (one at a time, nothing else running, 150 tables, --pfr-max 27):
| build | VPIP | PFR | post agg | late open 8-6 | late open 5-3 | EP open | BB fold/call/raise | result |
|---|---|---|---|---|---|---|---|---|
| v7 (g1) | 26.8 | 23.4 | 53.6 | 33.0 | 39.7 | 21.6 | 50/12/38 | PASS |
| v8a = v7 + hu_jam_widen (g1 / g2) | 27.7 / 28.3 | 24.0 / 24.4 | 55.0 / 52.4 | 37.3 / 38.6 | 39.3 / 40.6 | 21.1 / 23.0 | 44/14/42, 43/15/42 | PASS |
| **v8 full (g1 / g2)** | **29.2 / 30.1** | **25.3 / 26.3** | 53.3 / 51.9 | **50.8 / 49.4** | 47.7 / 47.1 | 20.7 / 22.5 | 51/16/32, 45/15/41 | **PASS** |
v6 postflop behavior preserved: HU bets into a visible pair 7.4-14.1% (v7 6.7; n~100 per run, noisy), HU flop bets otherwise 97.7-98.4%, HU flop/turn fold-to-bet 23.4-24.4%.
No-bank upload test, alone, seeds hu111-115 x 30 tables: failed 0. Fuzz 100k alone: illegal 0, raised 0, mem 456 B, p50 60 us, p99 151 us, p99.9 205 us, max 559 us.
Fallback if the reviewer blocks the new flags: bots/v8a (v7 + hu_jam_widen only) passed every test above.

## Step 10 — v9 (`bots/v9`, `releases/v9.zip`) = v8b + `bb_jam_widen` ON (STEERING 20:28)
Base `bots/v8b` recreated = bots/v8 with `bb_fold_oop_weak: False` (one-line diff; the live round-5 build per STEERING 20:23). Nothing else touched.
Rule (post-filter in `decide()`, only folds change): we're the BB, 5-8 alive, eff < 40 bb, facing a single non-all-in open from CO/BTN/SB (opener has 1-3 non-busted seats behind it up to the BB), no limpers or callers. Where v8b folds a hand with an ace or two T+ cards -> jam. Requires raise to be legal.
Evidence: Samuel R2/R3 from our own cards, BB jam vs fold vs CO/BTN/SB opens at 5-8 alive and < 40 bb: two broadway +0.83 to +1.18 pts per jam, Ax +0.48 to +1.10; under 20 bb overall +0.65 to +1.05, 20-40 bb +0.26 to +0.69; positive in both rounds under all three matching checks.
Expected behavior move: BB re-jam (raise) rate vs late opens up, BB fold rate vs late opens down. Nothing at <= 4 alive, vs EP/MP opens, at >= 40 bb, or anywhere v8b calls / 3-bets / jams.
Probes:
- The user's listed spots with empty memory (6 alive, BTN 2.5 bb open, 25 bb): A72 and KQ5 -> jam (v8b already jams there); 953, 4 alive, 41 bb, UTG open, open + SB caller -> unchanged. v8b *calls* A72/KQ5 vs CO/SB opens at 30 bb and at 39 bb -> v9 keeps the call (calls are never altered).
- With empty memory v8b treats a lone opener as ~71% wide and almost never folds the BB, so the rule fires where v8b folds for real: tight opener stats in memory (60 hands, 9 raises) and a 5 bb open at 30 bb -> v8b folds A72 / KQ5 vs BTN, CO and SB opens and v9 jams; 953, 4 alive, 40 bb, 41 bb, UTG open, open + caller -> unchanged (fold).
- Sweep, 8,000 spots (3-8 alive, 15-60 bb, opens 2.5-7 bb, 60% with tight-opener memory, callers, all-in opens): v8b folds 5,394, v9 changes 217, all fold->jam in scope, 0 out-of-scope.
- validate.py OK; decide() probe 24k states 0 exceptions.
Stats check (one at a time, 150 tables, --pfr-max 29 --vpip-max 34):
| build | VPIP | PFR | post agg | late open 8-6 | EP open | BB vs single non-SB open fold/call/raise | result |
|---|---|---|---|---|---|---|---|
| v8b (h1) | 29.6 | 25.1 | 53.2 | 47.2 | 23.1 | 23/38/39 | PASS |
| **v9 (h1 / h2)** | **30.3 / 31.9** | **25.5 / 27.1** | 53.8 / 52.4 | 46.2 / 48.2 | 23.0 / 22.3 | 21/36/44, 24/38/38 | **PASS** |
v6 postflop behavior preserved (HU flop bets otherwise 95.9-96.3%, HU bets into a visible pair 15.7-16.7% vs v8b 12.0, n~100 noisy).
No-bank upload test, alone, seeds hu121-125 x 30 tables: failed 0.
Fuzz 100k alone: 0 illegal / 0 raised / mem 456 B both runs. Run 1 max 2.46 ms (load avg 4.4, Spotlight mds_stores ~36% CPU; that state replays x30 at median 74 / max 103 us). Run 2: p50 62 us, p99 166 us, p99.9 305 us, max 574 us.
