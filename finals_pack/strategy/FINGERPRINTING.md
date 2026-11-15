# Fingerprinting opponents and disguising ourselves

Owner: `scout` (RESEARCH: judgment and `analysis/fp_train.py`), `platform` (BUILDER: in the bot), `tester`
(RESEARCH: checks). Subagents report to their own session; the sessions pass paths across with `SendMessage` to
BUILDER or RESEARCH (and `say.py --record`).
Everything here is written live on the day from this description; no code is brought.

## What we know (verified)

- **Downloads label every seat**: the header's `entries` list gives `entry_id` and `team_name`, and each
  table's `seats` lists the entry at each seat; `fillers` marks non-scoring seats (kit
  `hand-history/README.md`). These are our training labels.
- **The live bot sees anonymous seats** (`GameState` has no names), so recognition is inferred online.
- **No timing data** exists in downloads; don't use timing.
- **Bot limits:** memory 64 KB (keep under 16 KB, survive truncation), no cross-table globals; the bot may read
  data files shipped in its zip. Profiles ship as data; per-table state lives in memory.
- **Tables:** 21 teams make 24 seats an iteration with 3 filler seats: in case F (`CLAUDE.md` §8) four tables of 6,
  each opponent at roughly a quarter of ours; in case R three tables of 8, each opponent at roughly a third of ours. Take the table
  size from the rules card. Each team appears at most once per table (a free constraint).
- **Regional results** (`research/finals_prep/identity/REPORT.md`): recognition 59/73/79% at 10/20/40 hands
  with sizes (21/31/41% without); same-round held-out 73/90/96%; profiles two rounds old 53/66/72% (expect
  about 56% at 20 hands at the Finals, where bots change). Opponents identified **us** at 88% by hand 20,
  mostly from open sizes. Perfect knowledge of the seven seats is worth about 1.9 points/table, concentrated
  in 4-5 teams. Nobody exploited us at the regional. Changing sizes hides us for one round only.
- **Re-tested on 14 to 15 November** (all three regionals, re-implemented from scratch, and by play against the
  rehearsal's opponents). Starting points only: today's bots are new, so re-measure from today's first hand file.
  - From a 1,000-table practice profile a seat is named correctly after 20 hands 78% of the time at the Bay Area
    (61-90 across rounds), 86% at Boston, 82% at Pittsburgh; 35% without bet sizes. No trained model beat naive
    Bayes (logistic regression, trees and sequence models were 3 to 7 points worse).
  - What limits it is a bot the profile never saw, not the classifier: a team that changed its bot is named wrongly
    with confidence unless the unknown class catches it (section 1).
  - Watching a seat predicts its frequent actions (opening, betting) as well as its profile does within 6 to 20
    hands. Identity matters where the seat answers someone else's action (an open, a re-raise, a bet, an all-in):
    those are too rare to learn inside one table.
  - Acting weighted by the recogniser's confidence never lost points in play, down to chance accuracy. Every
    accuracy or confidence bar tested cost points (section 2).
  - Size: about 0.2 points a table at a table of finalists (0 to 0.45, a model estimate), near zero in the round
    after teams replace their bots and largest in the last rounds. The regional winners led by about 2 points a
    table through field-level play. Build this after the base bot is right, never instead of it.

## 1. Recognition (online, in the bot)

- **Tokens:** each public event becomes (context, outcome). Context: street, position class (button, small blind, big blind, cutoff, earlier), the situation faced (unopened, limped, facing an open, a 3-bet, a 4-bet or more; after the flop a c-bet chance, a donk or probe chance, facing a bet, facing a raise; the twist's public choice if it has one), heads-up or multiway, stack depth
  (<=15, 15-40, >40 bb). Outcome: binned size (opens 0.25 bb, bets 0.1 pot, 3-bets 0.25x the raise), an
  exact-chip token, min-raise and all-in flags; plus fold/call/raise. (No chip-rounding token: dropping it gained
  a point of accuracy on 15 November.)
- **Classifier:** multinomial naive Bayes. Classes: each opponent, as two classes where both exist (its last
  scored-round bot and its last practice bot: 5 to 6 points more accurate, in every round pair tested) and unknown. A filler seat plays another entry's own bot, so it is labelled by that entry's team: there is no filler class. The likelihood table ships as a data file; per seat, memory holds one log-score per class and a count
  (about 700 to 800 bytes a table when packed; about 4 KB if kept as JSON). The rehearsal's trained tables held 6,500 to 14,700 tokens,
  not a few hundred: keep them as plain Python lists or scaled integers (numpy was slower per event). Measured
  cost: 2.5 µs an event, about 45 µs a decision on average and 105 µs at the 99th percentile, with the scores packed as bytes (for example `array('h')` of round((score − the seat's best score) × 100), floored at −32,000 (an absolute score passes the 2-byte limit within a table and raises), after the JSON part of memory: JSON dumps and loads of a 3 KB score block alone cost 65 µs) (a prototype that kept them in JSON memory and re-read the hand added 0.1-0.15 ms at the 99th percentile and 0.2-0.8 ms at the 99.9th). Posterior per hand:
  softmax(score/T + log prior), T fitted for calibration; then 3 Sinkhorn passes so each team's mass across the
  table's seats is at most 1 (a team's two classes counted together; the unknown exempt).
- **Unknown class:** its likelihood table is the whole field's token rates from the same file, so a seat that fits
  no team better than it fits "anyone" lands there. On 15 November this took confident calls from 89% to 98% right
  and changed bots named wrongly from 47% to 5%, with fewer seats labelled (56% against 79% at 20 hands). In the play test, where changed bots stayed close to their old profiles, it cost about 0.1 points a table: its value is against a bot unlike any profile. An unknown
  seat is played on the field's rates plus its own actions (section 3). Score a seat on its last 20 hands as well as on the whole table (for example a second score decayed by 0.95 a hand, averaging the two posteriors): a seat that changes design mid-table is only found that way (the label drops in 2 to 6 hands
  and the new design is found about 15 hands later).
- **Training each round** (`fp_train.py`, under 2 minutes; practice quick mode under 60 s): P(outcome | context) per labelled seat, smoothed toward the field's rate in that context with 10 pseudo-counts; recency weights (newest scored 1.0, newest practice 0.5 as
  a separate sub-class, previous scored 0.25); each team has a "last scored bot" and a "last practice bot"
  sub-class; a team flagged as drifted is retrained from the newest round only.

## 2. Validation and invalidation

Split held-out data **by iteration** (seats at a table are correlated); hold out 20%.

**These numbers are reported, not gates** (Dylan and Samuel, 15 November). No accuracy or confidence bar decides
whether profiles are used. In play on 15 November every bar tested cost points: bars of 0.4, 0.6 and 0.8 on a
seat's confidence cost 0.3, 1.0 and 1.4 points a table, and this page's earlier rule (a 55% field-wide bar, then
0.6 for a seat) did worse than not using identity at all. The response weighted by confidence gained at every
accuracy down to chance, and a hard label only began to lose below about 26-29% accuracy. What protects is in
section 3: weighting by confidence, the blend with the seat's own actions, the unknown class, the cap and the
direction test.

| Metric (`fp_metrics.json`) | Regional reference, for scale |
|---|---|
| Same-round held-out top-1 at 10/20/40 hands | 75/91/97% |
| **Lagged** top-1 (the previous profile on this round, 20 hands) | 75% from the previous scored round, 78% from the practice before it |
| Calibration (ECE, 10 bins); accuracy of calls with confidence >= 0.8 | raw scores are overconfident (ECE 0.16; 0.8 calls 89% right, 98% with the unknown class) |
| Per-team recall at 40 hands and its confusion row | report |
| Our own recall (avalon as a class) at 10/20/40 | report |

**Drift per team** (between rounds; practice vs scored), by effect size, not p-values: (a) Jensen-Shannon
divergence of the open-size or c-bet-size histogram > 0.15 bits; (b) lagged accuracy 20+ points below
same-round accuracy; (c) a rare-spot rate (fold to 3-bet, fold to a bet by street) moved > 3 SE.
**Automatic action:** (a) or (b) → mark that team's `profile:<team>:k` line `invalidated` in `notes/LEDGER.md`,
retrain it from the newest round and keep its older bot as the team's second class. Nothing is switched off: until
the new profile exists, a seat that no longer fits falls to the unknown class and is played on the field's rates
plus its own actions. (c) alone → refresh the rates: a team can keep its sizes, so it is still recognised, and
change a rare-spot rate (at the regional 18% of confidently named seats were more than 10 points off their profile
in fold to a re-raise). `scout` confirms or overrules each invalidation in one line.

Ledger (`notes/LEDGER.md` lines): method `fp-v1` (features, alpha, T, split rule, script sha); result `fp-acc
<stage>` (lagged and same-round accuracy, ECE, n seats); method `profile:<team>:<k>` per team (each counter's line
names the profile it depends on); result `drift:<team>:<k>` (JS, Δaccuracy, n).

## 3. Exploitation

**An option, in two steps, after the base bot is right.** Step one needs no profile and can go in once a hand file from today's field exists: the expected-value comparison below at the field's rates, with each seat's own counts blended in. **Before today's first hand file, or in a spot it does not cover, leave the base bot's action alone against a seat until that seat has folded three times in the spot with no call** (twice if the folds were to our own all-ins). In a constructed test, rates brought from another field lost 2 to 3 points a table against opponents who called more, at every blend strength, with or without identity, and this simple rule lost nothing there; where the rates fit it earned about half of what the blend did. The simple rules are settings of the same method (identical play on 384 of 384 tables), so nothing is built twice. In play on 15 November step one was worth as much as identity, almost all of it from the comparison at the field's rates, which re-tunes the base bot from hand 1: judge it by a paired test like any change to the base bot (two builds from this page gave +1.3 and +1.6 points a table for step one and +2.0 and +3.3 for both, on a leaky synthetic field).
Step two adds identity once two rounds of hand files exist. BUILDER and Dylan decide whether it earns its place
against other work; the later rounds, where bots have settled, are where it pays and they carry the most weight.

- **Per team, a record** (`analysis/counters.json`): its rare-spot rates with n (fold to 3-bet, fold to c-bet by
  street heads-up, big-blind fold vs a late open, all-in calls) and up to 3 adjustments, each with `gain` and
  `loss` in points per table.
- **The predicted rate for a seat in a spot** = (the seat's own count in that spot at this table + s × prior) /
  (n + s). The prior is Σ_c post[c]·rate_c over the classes; for an unknown seat it is the field's rate.
  There is no bar on post: the weighting is the protection.
- **Strength s**, the number of the seat's own actions the prior is worth (fitted on one regional, held on the
  other two; re-fit from today's file if there is time, else start here): opening 3-4, answering a re-raise 3-7,
  first bet after the flop 4-7, blind defence 6-11, facing a bet 11-16, facing an open 12-23, facing an all-in
  24-29 (the lower figure with the field's rate as the prior, the higher with a team's; for a mix, in proportion to the belief that is on teams). These are for counting in context (next bullet), the better form, except that a seat on the field's rate in an all-in spot gets 5 or less in either form, not 24 (in play 1 to 5 beat 10 by 0.3 points a table where the rates fit and by more where they were too tight; a hypothesis to re-fit from the first hand file); with the plain formula above the fitted strengths are larger and differ between events, so otherwise use 10 there (in play, with a team's rate, anything from 3 to 50 gave the same result).
- **Count in context:** compare what the seat did with what the prior expected in those same situations (a button
  open is not an early-position open) and shift by the difference. In prediction this was worth more than
  identity in most spots.
- **Act through expected value, not a switch:** in each spot compute the action's value with the predicted rate, pricing only what can be priced (preflop, folding against going all-in over a lone open, with equity against the hands that call, the top (the opener's open rate × (1 − the predicted fold rate)) of hands, from the base bot's equity table; heads-up after the flop, checking against betting when checked to) and leaving calls and other sizes to the base bot, and change the base bot's action only where that beats it by about a quarter of a big blind. A margin of half a big blind lost about a third of the gain in play and one big blind two thirds; waiting for a confident label lost too. Start at hand 1 once the rates are today's.
- **Cap** how far identity may move a seat's predicted rate from the field's rate at 20 points; the seat's own counts are not capped (data-biased response, Johanson & Bowling 2009). A
  10-point cap cost 0.3 to 0.6 points a table in play; no cap doubles what a sign error costs.
- **Direction test, before any release with this on:** give the bot a seat that always folds in a spot and one
  that never does, and check, on the same states taken from real play, that it bluffs more into the first than the base bot does, no more into the second than the base bot does, and more into the first than the second, for every spot it adjusts (print the three counts per spot: with a reversed sign the first comparison alone still passed). A reversed sign cost 1.2 to 2.3 points a table at the regional's scale (about 0.5 at the Finals' estimated scale), and no accuracy number shows it. Then replay equivalence, timing and
  memory as in section 7.
- **Measured:** a table-hash arm in practice rounds (half the practice tables with it on). Compare the decisions
  it changed and the equity per hand where it fired: points per table cannot see 0.3 points in 5,000 tables.
  Whether a counter pays can only be measured between rounds, from the hand file, and one that lost where it fired
  is switched off for the next round; inside a table the bot can only see whether the seat still fits its label.

## 4. Opponents adapting within a table

Per team, a logistic regression on aggression against a target (3-bets an open; bets or raises after a check)
with vs-us, late-table (hand > 40), their interaction, position and size bin; errors clustered by table. The
interaction (late minus early, vs us minus vs others) is the hill-climb signal; also their 3-bet rate vs us
after we folded to a 3-bet at this table. Flag: interaction >= 5 points at z >= 3.3 (Bonferroni over teams x
spots) or Benjamini-Hochberg q = 0.1. Response (`ANTI_ADAPT_<team>`): against that seat after hand H, play the
node at its break-even frequency, removing the stationary pattern they climb. On the regional data 14 of this test's 15 flags were shared by most of the field, an artefact of our own play: read a flag as real only if most of the field does not show the same shift.

**Teams that punish a fold** (tested 15 November). "Vs us minus vs others" cannot see a team that does it to everyone, and at the regionals eight of today's opponents re-raised a seat 17 to 45 points more often after it had folded to their last re-raise. So also measure, against every opener and not only us, each team's rate of re-raising an open when that opener folded to its last re-raise at this table, minus its rate otherwise, within position and stack band. Bots with no such rule show +5 to +7 on that raw difference: flag +15 or more. Against a flagged seat, count how often it re-raises our opens at this table, all states together, and let the expected-value comparison of section 3 widen the hands we move all-in with over its re-raise (calls stay with the base bot) (+0.6 ± 0.2 points a table against six such teams in twenty on a synthetic field; -1.8 with rates from another field, so only with today's rates: a hypothesis to test today). Do not build a table of rule strengths per team, an armed-state counter, a fold on purpose to arm a seat, or a selector that picks among rules within a table: each was zero or negative on every field tested, the per-team table even where it was true, and a seat gives about 4.5 answers a table, too few for a selector to learn from.

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
| Data lands (T-13) | `scout` runs `analysis/fp_train.py` (RESEARCH briefs it as soon as the portal watcher posts the data; it runs beside the round card, never after it) | download → `analysis/<stage>/fp/` (the stage name with spaces as '-', e.g. `analysis/Round-2/fp/`: profiles, likelihood table, counters, metrics, drift, profiled_us, adapt, card) in <= 2 min; ledger lines and invalidations |
| T-12 to T-9 | `scout` | counters.json for `platform` (each team's rates with n; no accuracy gate, section 2; RESEARCH sends BUILDER the path); ledger lines for `tester`; confirm or overrule invalidations |
| T-12 to T-9 | `tester` | re-run lagged accuracy and calibration on a different split (or a Codex re-implementation); mark the lines validated or disputed (a report only; it waits until the tester's T-9 edge is sent) |
| Practice download (stage `Round k.5`, about T-8) | `tester` (the portal watcher has already run `fp_train.py` quick mode on it) | before the decision only `tester`'s field-adjusted edge matters (the watcher's drift output names the yardstick teams); `scout`'s review of it waits until after T-3 |
| T-8 to T-6 | `platform` | embed the data file behind FP_ON, CTR_<team>, ANTI_ADAPT_<team>, DISGUISE_* (outside the change count) |
| T-6 | `tester` | the direction test (section 3), replay equivalence (bot posteriors = offline within 1e-4 on 200 tables), latency, memory, truncation |
| After the T-3 upload | `scout` (+ `analyst`) | the practice download's full analysis: practice vs scored drift per team ("team X is testing a new bot"); specialist studies of the 2-3 stable teams with the largest gaps; counter A/B; profiled-us and adaptation trends; a disguise memo for BUILDER when triggered |

## 8. Tests to run before Sunday (regional data and the emulator)

Items 1, 2 and 5 were run on 14 to 15 November and their results are in "What we know" and sections 2 and 3;
item 5's gate was dropped. Items 3, 4, 6 and 7 were not run.

1. Reproduce the regional numbers with `fp_train.py` (same-round and lagged accuracy within 3 points).
2. Calibration: fit T on round k, test on k+1; ECE <= 0.05.
3. Drift: swap two teams' labels in a copy (both flagged, at most 1 false flag); in the emulator, swap two
   entries' bots between rounds and check the same on real-format downloads, filler seats included.
4. Online equivalence and cost: bot posteriors match offline within 1e-4; added p99.9 latency < 0.2 ms; memory
   < 4 KB; truncated memory raises nothing.
5. Counter gate value on regional data: >= 60% of the value with perfect labels; loss <= 25% of the gain.
6. Profiled-us: null on regional data; detects an injected +8-point effect at z >= 3 from one download.
7. Hill-climb: an emulator bot that raises its 3-bet rate after each of our folds is flagged; ANTI_ADAPT cuts
   its gain.
8. End to end on the emulator's finals field: download → fp card <= 2 min → counters to `platform` by T-9 →
   embedded and tested by T-6.

Sources: Johanson & Bowling, Data Biased Robust Counter Strategies (AISTATS 2009); Guo et al., On Calibration
of Modern Neural Networks (ICML 2017); Southey et al., Bayes' Bluff (2005).
