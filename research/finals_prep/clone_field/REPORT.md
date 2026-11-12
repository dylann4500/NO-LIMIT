## Clone-field simulator: validation result

**Verdict: it works for the questions that mattered.** A clone field fitted from one download reproduces the v4 collapse, the v6-over-v5r gain, and our absolute scores to within about 1 point. It cannot resolve differences under about 1 point. Everything below was run unless marked inferred; nothing in the repo was edited or committed.

### What the clones model
- **Coverage:** every other team in the file gets its own clone (126 in R1; the rest of the 148 entries never appear). No pooled tiers were needed: each team has about 1,100 tables in a scored file and about 56 in a first-1000 download.
- **Preflop:** fold / call / raise / all-in frequencies per situation: unopened by seats left to act, stack depth in bb and 4-or-fewer alive; facing an open; facing a 3-bet or 4-bet; facing an all-in by price.
- **Postflop:** bet-when-checked-to and fold / call / raise facing a bet, by street, heads-up vs multiway, bet size and commitment. Size distributions and lower-card exposure rate are fitted too.
- **Hand sensitivity:** frequencies become strength thresholds. Preflop uses a simulated 3-card ranking (1,755 classes) with the clone's range tracked through the hand. Postflop uses P(ahead of each opponent's exposed card plus a random unseen card), with a draw bonus.
- **Calibration:** a clone-only loop (about 10,000 tables) corrects thresholds so simulated frequencies match the fitted ones.

**Not modelled:** adaptation or memory across hands, reactions to our exposed card beyond card removal, and real discard logic. Bluffing is two global knobs (bluff share, random-strength share), not per team. I set them from showdown win rates before any candidate run, and bracketed them with an "honest" and a "bluffy" variant.

### Calibration (R1 fit, clone-only, 3,000 tables)
| Stat (pooled field) | Real | Sim | Per-team correlation |
|---|---|---|---|
| VPIP | 0.254 | 0.260 | 1.00 |
| PFR | 0.184 | 0.187 | 1.00 |
| 3-bet | 0.069 | 0.070 | 1.00 |
| Flop bet | 0.494 | 0.483 | 0.99 |
| Flop fold to bet | 0.503 | 0.517 | 0.97 |
| Turn fold to bet | 0.365 | 0.306 | 0.93 |
| River fold to bet | 0.413 | 0.417 | 0.88 |
| River bettor wins at showdown | 0.650 | 0.711 | none |

- Clones' simulated points correlate 0.79 with the teams' real points, although no outcome was fitted.
- v3b in the R1 clone field against real R1:

| | Points | VPIP | PFR | 3-bet | Fold to 3-bet | Flop fold to bet | Turn | River | 1st place | 8th place |
|---|---|---|---|---|---|---|---|---|---|---|
| Sim | 18.35 ± 0.30 | 0.295 | 0.225 | 0.149 | 0.851 | 0.390 | 0.474 | 0.685 | 27.0% | 6.4% |
| Real | 18.11 | 0.300 | 0.230 | 0.162 | 0.868 | 0.324 | 0.477 | 0.704 | 27.1% | 6.9% |

### Prediction test (same seeds for every bot; ± is one standard error)
R1 and P3 fields: 5,000 tables per bot. The other fields: 4,000.

| Clone field | v3b | v4 | v5r | v6 | v4 − v3b | v6 − v5r |
|---|---|---|---|---|---|---|
| R1 (main) | 18.35 ± 0.30 | 10.58 ± 0.27 | 17.75 ± 0.30 | 20.11 ± 0.31 | −7.77 ± 0.39 | +2.36 |
| Practice 3 (what we had before v4) | 18.64 | 10.99 | 18.80 | 21.73 | −7.65 ± 0.39 | +2.93 |
| R2 (drift check) | 17.23 | 11.59 | 17.47 | 19.09 | −5.64 ± 0.44 | +1.62 |
| R1, honest clones | 16.76 | 10.20 | 16.89 | 19.73 | −6.57 | +2.84 |
| R1, bluffy clones | 18.28 | 11.73 | 18.88 | 20.67 | −6.55 | +1.79 |
| R1 first-1000 download only | 16.82 | 9.63 | 16.07 | 18.27 | −7.19 | +2.20 |
| **Real** | 18.10 (R1), 19.02 (P3) | 9.17 (P4) | 16.73 (R2) | 19.05 (R3) | about −9 | +2.32 (across rounds) |

Paired differences against v3b carry ±0.30–0.44; v6 − v5r is a difference of two of those, so about ±0.45.

- **v4 detail:** simulated v4 has VPIP 0.44 (real 0.42), folds 86% to 4-bets (real 89%), and finishes 8th 23.5% of the time (real 23.5%).
- **Later bots, R1 field:** v7 20.99, v9s 20.99, v10 20.91, each about +2.6 over v3b.
- **Later fields:** in the R3 field v6 scores 18.75 (real R3 19.06), v7 19.46 and v10 19.14. In the R5 field v9s scores 18.20 (real R5 17.95) and v10 18.07.

### Against the three requirements
- **(i) v4 far below v3b: pass.** −5.6 to −7.8 in all six fields, including the practice-3 fit. That field would have warned us before the upload.
- **(ii) v6 above v5r by +1 to +2.5: pass.** +1.6 to +2.9 across fields; real was +2.3.
- **(iii) Realistic absolutes and style: pass, within about ±1.** Same-round comparisons (field from that round's file) miss by +0.2 (R1), +0.7 (R2), −0.3 (R3) and +0.3 (R5).

### Trust on the night
- **Trust it for:** catching a candidate that loses 2 or more points to the real field, the direction of large style changes, and sanity-checking VPIP, 3-bet and fold rates before upload. It is the opposite of the "beats our old bots" test that passed v4.
- **Do not trust it for:** differences under about 1 point. v5r − v3b came out anywhere from −0.74 to +0.60 depending on the clone settings, with ±0.3 noise on top.
- **v7, v9s and v10 against v6 is unvalidated.** The simulator puts them 0.4–0.9 above v6 in every field; the real scores fell round by round, but in different fields, so there is no ground truth.

### Failure modes seen
- **Forward predictions run high.** A field fitted from round n over-predicts our round n+1 score by 0 to 1.8 (v5r +1.0, v6 0.0, v7 +1.2, v10 +0.5, v4 +1.8). The field tightens each round and the clones are frozen: v3b drops from 18.35 against the R1 field to 15.88 against R5.
- **Clones are too honest postflop.** River bettors win 71% of showdowns in the main setting against 65% real. The bluffy setting matches (64%), and moving between settings shifts absolutes by about 1.5 points.
- **Our own flop fold-to-bet reads 39% in simulation against 32% real.** Flop overbets are also under-represented (4% of bets faced against 11%).
- **A first-1000 fit weakens the picture.** Shrinkage blurs weak teams (points correlation 0.41 against 0.79) and our score drops 1.5; the verdicts on v4 and v6 hold.
- **The Mac went to sleep mid-run and stalled about 14 minutes.** Run under `caffeinate -s`.
- **Timeouts under load are negligible.** One late run, slowed to about 27 tables/s by machine load, had 193 failed candidate decisions in 493,000.

### Timing (12-core Mac)
- **Fit:** 10–12 s for a 20,000-table file.
- **Calibration:** about 3.3 minutes at 60–70 tables/s clone-only.
- **Candidates:** 40–47 tables/s, so about 2 minutes per 5,000 tables. That gives ±0.3 on a score and ±0.35–0.4 on a paired difference.
- **Whole round:** fit, calibrate and three candidates take about 10 minutes, which fits a 20-minute window locally.
- **Clone decision time:** mean 19 µs, 99.9th percentile 113 µs, max 182 µs. As real kit processes, the clones had 0 failures in about 40,000 decisions.
- **40 cloud machines (inferred, not run):** about 500 tables/s, so 20,000 tables per candidate in under 2 minutes including start-up, for about ±0.2 on a paired difference.

### Files
Everything is under `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/clones/`:
- `lib/fit_clones.py` — the fitter: `python -I fit_clones.py HANDS.gz OUTDIR`
- `lib/clonecore.py`, `lib/agent.py`, `lib/pre3.json` — the generic clone, its wrapper and the 3-card ranking
- `lib/calibrate.sh`, `lib/calib.py` — the calibration loop and the real-vs-sim comparison
- `lib/simrun.py`, `lib/herobatch.sh`, `lib/report.py` — the paired runner (clones in-process, candidate as a real kit process) and reporting
- `lib/finalize.py` — writes standalone kit bot folders
- `fields/{r1,p3,r2,r3,r5,r1_honest,r1_bluffy,r1_first1000}/` — one folder per team with `params.json`, plus `field.json`, `acc.pkl`, `cdf.json`, `adj.json`
- `fields/r1/kit_teams/` and `fields/r1/emu_field.json` — the R1 clones as standalone folders for `cloud/kit_match.py` or `emu/tournament.py`
- `out/` — per-run pickles (`r1_v3b.pkl` and so on) and `calib_*.txt`, `batch_*.txt` logs