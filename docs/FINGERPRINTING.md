# Fingerprinting opponents and disguising ourselves

Owner: s-scout (Opponents: judgment and `analysis/fp_train.py`), d-platform (in the bot), s-tester (checks).
Everything here is written live on the day from this description; no code is brought.

## What we know (verified)

- **Downloads label every seat**: the header's `entries` list gives `entry_id` and `team_name`, and each
  table's `seats` lists the entry at each seat; `fillers` marks non-scoring seats (kit
  `hand-history/README.md`). These are our training labels.
- **The live bot sees anonymous seats** (`GameState` has no names), so recognition is inferred online.
- **No timing data** exists in downloads; don't use timing.
- **Bot limits:** memory 64 KB (keep under 16 KB, survive truncation), no cross-table globals; the bot may read
  data files shipped in its zip. Profiles ship as data; per-table state lives in memory.
- **Tables:** 8 + 8 + 4 teams with 4 fillers at the short table; each team is at about 7 of our 19 tables;
  each team appears at most once per table (a free constraint).
- **Regional results** (`research/finals_prep/identity/REPORT.md`): recognition 59/73/79% at 10/20/40 hands
  with sizes (21/31/41% without); same-round held-out 73/90/96%; profiles two rounds old 53/66/72% (expect
  about 56% at 20 hands at the Finals, where bots change). Opponents identified **us** at 88% by hand 20,
  mostly from open sizes. Perfect knowledge of the seven seats is worth about 1.9 points/table, concentrated
  in 4-5 teams. Nobody exploited us at the regional. Changing sizes hides us for one round only.

## 1. Recognition (online, in the bot)

- **Tokens:** each public event becomes (context, outcome). Context: street, position class, spot (open,
  limp, iso, 3-bet, 4-bet, c-bet, donk, probe, raise vs bet, twist), heads-up or multiway, stack depth
  (<=15, 15-40, >40 bb). Outcome: binned size (opens 0.25 bb, bets 0.1 pot, 3-bets 0.25x the raise), an
  exact-chip token, a rounding token (amount mod 5/10/25), min-raise and all-in flags; plus fold/call/raise.
- **Classifier:** multinomial naive Bayes over 21 classes (19 opponents, filler, unknown/new bot). The
  likelihood table (about 600 tokens x 21, float32, about 50 KB) ships as a data file; per seat, memory holds
  21 log-scores and a count (about 90 B; under 2 KB for 7 seats). Each new event adds a row (under 60 µs per
  turn). Posterior per hand: softmax(score/T + log prior), T fitted for calibration; then 3 Sinkhorn passes so
  each team's mass across the table's seats is at most 1 (fillers exempt).
- **Unknown gate:** if the best class's mean log-likelihood per event is below that team's 5th percentile on
  held-out tables, move half the mass to "unknown" (catches a team that changed its bot mid-day).
- **Training each round** (`fp_train.py`, under 2 minutes; practice quick mode under 60 s): token counts per
  labelled seat with Dirichlet smoothing (alpha 10); recency weights (newest scored 1.0, newest practice 0.5 as
  a separate sub-class, previous scored 0.25); each team has a "last scored bot" and a "last practice bot"
  sub-class; a team flagged as drifted is retrained from the newest round only.

## 2. Validation and invalidation

Split held-out data **by iteration** (seats at a table are correlated); hold out 20%.

| Metric (`fp_metrics.json`) | Bar to use profiles |
|---|---|
| Same-round held-out top-1 at 10/20/40 hands | >= 50/65/75% field mean |
| **Lagged** top-1 (round k-1 profiles on round k, 20 hands): the decision number | >= 55% field mean |
| Calibration (ECE, 10 bins); accuracy of calls with confidence >= 0.8 | ECE <= 0.05; >= 75% right (n >= 200) |
| Per-team recall at 40 hands and its confusion row | >= 50% to enable that team's counters |
| Our own recall (avalon as a class) at 10/20/40 | report |

**Drift per team** (between rounds; practice vs scored), by effect size, not p-values: (a) Jensen-Shannon
divergence of the open-size or c-bet-size histogram > 0.15 bits; (b) lagged accuracy 20+ points below
same-round accuracy; (c) a rare-spot rate (fold to 3-bet, fold to a bet by street) moved > 3 SE.
**Automatic action:** (a) or (b) → `invalidate` that team's `profile:<team>:k` (its counters, which depend on
it, are flagged), retrain from the newest round, counters off (rates fall back to the field-prior blend);
counters come back when the next download shows lagged accuracy >= 55% for that team. (c) alone → refresh
the rates, keep the counters. s-scout confirms or overrules each invalidation in one line.

Ledger: method `fp-v1` (features, alpha, T, split rule, script sha); result `fp-acc <stage>` (lagged and
same-round accuracy, ECE, n seats); method `profile:<team>:<k>` per team (counters `depends_on` it); result
`drift:<team>:<k>` (JS, Δaccuracy, n).

## 3. Exploitation

- Per team, a counter record: rare-spot rates (fold to 3-bet, fold to c-bet by street heads-up, big-blind fold
  vs a late open, all-in calls) and up to 3 discrete adjustments, each with `gain` (pts/table when right) and
  `loss` (pts/table when applied to a seat that is really another team, averaged over the confusion row).
- **Rates:** prior = Σ_c post[c]·rate_c blended with the field rate, weight ramping over 10 hands, then live
  counts take over (the prior-blend from FIRST_PROMPT Part 1).
- **Discrete counters:** apply when post·gain − (1−post)·loss > 0 **and** post >= 0.6, the seat isn't
  "unknown", and the seat's open and 3-bet rates at this table are inside the team's 90% range.
- **Bounded loss** (data-biased response, Johanson & Bowling 2009): each counter moves a decision parameter by
  at most δ_max × min(1, n_spot / n_full); δ_max starts at a 10-point frequency shift.
- **Measured:** a table-hash arm: 50% of practice tables with counters on, a 15% off arm in scored rounds;
  compare the change in equity per hand where a counter would fire (far less noisy than points per table).

## 4. Opponents adapting within a table

Per team, a logistic regression on aggression against a target (3-bets an open; bets or raises after a check)
with vs-us, late-table (hand > 40), their interaction, position and size bin; errors clustered by table. The
interaction (late minus early, vs us minus vs others) is the hill-climb signal; also their 3-bet rate vs us
after we folded to a 3-bet at this table. Flag: interaction >= 5 points at z >= 3.3 (Bonferroni over teams x
spots) or Benjamini-Hochberg q = 0.1. Response (`ANTI_ADAPT_<team>`): against that seat after hand H, play the
node at its break-even frequency, removing the stationary pattern they climb.

## 5. Have they profiled us?

Per team and spot (3-bets vs our opens, folds to our 3-bets, folds to our c-bets by street, raises of our
c-bets, calls of our shoves): their rate vs us minus their rate vs others, stratified by position x size bin x
stack, on **hands 1-20 only** (exploitation that early can only come from identity). Keep a table across
rounds with a trend. **Trigger a disguise review** when one team shows >= 5 points at z >= 3 in a spot worth
>= 0.1 pts/table to them, or 3+ teams are significant in the same direction, or the trend rises for 2 rounds.
Expect a null (the regional showed 0.4-1.9 points).

## 6. Disguise (weighed by expected return)

Our exposure = Σ_teams P(team identifies us by hand h) × its measured effect (§5) × value per spot.

| Option | Buys | EV cost | When |
|---|---|---|---|
| D0 close rare-spot gaps (e.g. fold to 3-bets near break-even) | being recognised becomes worth little | usually positive | always a candidate: the real defence |
| D1 never ship identical exact sizes twice (shift 1-2 chips / 0.05 bb) | defeats exact-amount recognisers for a round | about 0 | every re-tune |
| D2 one-round size mask inside the EV-flat band | under 10% recognition for one round | up to ~1 pt/table if the band is wrong | §5 trigger fired and it's the heaviest remaining round |
| D3 per-table style rotation | little (a mixture model recovers it) | small | no |
| D4 mixing near-indifferent actions | unmeasured | unmeasured | no |

Don't disguise when nobody acts on knowing us, when the "tell" is a deliberate exploit that pays, or when the
band's EV cost isn't measured flat on this event's data. Masks work once: save them for the round that
matters most.

## 7. Who does what each window

| When | Who | What |
|---|---|---|
| Data lands (T-13) | hub runs `analysis/fp_train.py` (s-scout owns it) | download → `analysis/<stage>/fp/` (profiles, likelihood table, counters, metrics, drift, profiled_us, adapt, card) in <= 2 min; automatic records and invalidations |
| T-12 to T-9 | s-scout | counters on/off by the gate; counters.json → d-platform; items → s-tester; confirm or overrule invalidations |
| T-12 to T-9 | s-tester | re-run lagged accuracy and calibration on a different split (or a Codex re-implementation); verify |
| Practice download (about T-8) | script, quick mode | practice vs scored drift per team ("team X is testing a new bot") |
| T-8 to T-6 | d-platform | embed the data file behind FP_ON, CTR_<team>, ANTI_ADAPT_<team>, DISGUISE_* (outside the three-change count) |
| T-6 | s-tester | replay equivalence (bot posteriors = offline within 1e-4 on 200 tables), latency, memory, truncation |
| After the T-3 upload | s-scout (+ s-data) | specialist studies of the 2-3 stable teams with the largest gaps; counter A/B; profiled-us and adaptation trends; a disguise memo when triggered |

## 8. Tests to run before Sunday (regional data and the emulator)

1. Reproduce the regional numbers with `fp_train.py` (same-round and lagged accuracy within 3 points).
2. Calibration: fit T on round k, test on k+1; ECE <= 0.05.
3. Drift: swap two teams' labels in a copy (both flagged, at most 1 false flag); in the emulator, swap two
   entries' bots between rounds and check the same on real-format downloads, filler class included.
4. Online equivalence and cost: bot posteriors match offline within 1e-4; added p99.9 latency < 0.2 ms; memory
   < 4 KB; truncated memory raises nothing.
5. Counter gate value on regional data: >= 60% of the value with perfect labels; loss <= 25% of the gain.
6. Profiled-us: null on regional data; detects an injected +8-point effect at z >= 3 from one download.
7. Hill-climb: an emulator bot that raises its 3-bet rate after each of our folds is flagged; ANTI_ADAPT cuts
   its gain.
8. End to end on the emulator's finals field: download → fp card <= 2 min → counters to d-platform by T-9 →
   embedded and tested by T-6.

Sources: Johanson & Bowling, Data Biased Robust Counter Strategies (AISTATS 2009); Guo et al., On Calibration
of Modern Neural Networks (ICML 2017); Southey et al., Bayes' Bluff (2005).
