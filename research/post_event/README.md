# Post-event analysis (2026-11-08)

Scripts behind Sections 5-7 of the write-up (`docs/writeup/avalon-writeup.pdf`). They read the six scored-round files in `data/hands/` (see `data/README.md`). Outputs (`.pkl`, `.csv.gz`, `*_out.txt`, `out/`) are regenerable and not committed.

The scripts were recovered from the analysis sessions' logs after the original working folder was cleared. All of them parse; `spot_checks/v.py` was rerun from here and matched the original numbers. Rerun the others before relying on an exact figure.

Run from the repo root with the starter kit's Python (`PY=starter-kit/.venv/bin/python`, always with `-I`). Each pass over a 265 MB file takes 1-3 minutes with 5-6 processes.

| Folder | Question | Entry points |
|---|---|---|
| `trends_and_icm/` | Per-round profile R1-R6 (VPIP, PFR, jams, fold to bet, places, failed decisions) and the ICM call-mask defect: call rates and value per call by players alive, and its cost in weighted points | `run_all.sh` (extracts `R1..R6.pkl`), then `$PY -I trends_and_icm/aggregate.py`. `icm.py` is a Malmuth-Harville ICM that pays bust places; `check_icm.py` checks it against the platform's `equity_*` |
| `round6_attribution/` | Where round 6 points went: forward value of each decision class vs folding, with the fold-drift correction; over-folding against heads-up bets; R5 vs R6; reveal policy | `extract.py HANDS r6` (and `r5`), then `analyze.py r6 r5`, `analyze2.py r6 r5`, `q1agg.py`, `q2.py`, `q2b.py`, `q3b.py`, `q4.py` |
| `field/` | The opposing field R1-R6: style trends, head-to-head by opponent, the leaders' styles, consistency and noise of the final ranking, 3-bets against our opens, exposure choices | `extract.py HANDS out/rN.pkl` per round, then `analyze.py out`, `detail.py`, `analyze_detail.py`, `expo.py`, `maniac.py` |
| `spot_checks/` | Independent recounts of the headline numbers | `v.py` (points/table, 2-3-alive all-in call rate, flop fold-to-bet; ignore its `HU` column, which double-counts our own fold), `tb.py HANDS TEAM` (re-raise rate on our opens, our fold rate, our points at a team's tables), `f2b.py` (heads-up fold to first bet by street, by team). `hu.py` was a debugging script for a miscounted heads-up split; ignore its numbers |

## Headline results

- Our points/table R1-R6: 18.11, 16.75, 19.06, 18.26, 17.95, 17.52 (official 18.10 ... 17.53). Zero automatic (failed) decisions in every round.
- R6 vs R5: −0.43 per table (95% CI −0.83 to −0.03). Mostly the field: more 3-bets against our opens, fewer soft spots. The v10 ICM fix shows up as a gain.
- ICM defect: 2-3-alive all-in call rate 23.8% (R3) → 17.2% / 17.4% (R4, R5) → 19.7% (R6). Where the defective threshold exceeded the correct one by >0.10: 11-13% (R1-R3), 1.7-2.0% (R4-R5), 10.9% (R6); R6 calls there gained +2.20 points each. Cost ≈ 1.4 weighted points (0.9-1.7).
- Flop fold-to-bet: 33-34% in R1-R2, 66-70% from R3 (v6 fold rules).
- 3-bets: field 3-bet rate 6.9% (R1) → 12.3% (R6); share of our first-in raises re-raised 15.6% → 28.1%; we fold to 82-87% every round. thepastaway's R6 bot (3-bet 60% vs our opens): our points at its tables 3.78 below average.
- Heads-up fold to a first bet in R6, flop/turn/river: us 73/66/78%, field 52/45/48%.
- Final standing: rounds 1-2 decided it. After R2 we trailed places 3-5 by 8.5-11.1 weighted points; over R3-R6 we outscored all three.
