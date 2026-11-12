# Recognition and masking: what the regional data says

**Do not mask our sizes.** The data backs all three of the team lead's objections. Masking buys one round of confusion, while the gap in our rare-spot rates is what makes knowing us worth anything.

**REPORT.md was not saved**: the harness refused the write (subagents may not create report files). This message is the full report; save it as `REPORT.md` if you want the file. Scripts and raw outputs are in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/strategy/identity/`. Nothing in the repo was edited and nothing was sent to an external service.

Tags: **[M]** measured from our hand histories, **[E]** estimated with a stated model, **[R]** reasoned.

## Answer to the dispute

- **(a) Sizes cost.** [M] The field's fold rate climbs steeply with the size it faces: 29% / 51% / 67% / 72% on the flop for bets of about 1/3, 1/2, 3/4 and full pot. Within a single team's bets the slope is +59 points of fold rate per pot of size on the flop and +47 on the turn and river.
- **(b) "Uses the common sizes" is its own class.** [M] No single size is used by most of the top 20: the most common flop bet, half pot, is the main size for 4 of 19. No team uses the whole set of most-common sizes. A bot that always does is found from sizes alone 98% of the time by hand 20 once opponents have one round of it; before masking that figure was 84%.
- **(c) The opponent's response ends it in one round.** [M] A size change drops recognition to under 10% for the first round in most variants (most-common, randomised, copying 2 Curry, Gavilan or TeamBallHog). From the next round, with a refreshed profile, we are found 82-95% of the time by hand 20 again, or 63-70% if we copy a team that also plays like us.

Samuel's worry is still justified on one point. We were found very early (half our seats by about hand 7), and we carried a hole an informed opponent could use. The remedy is to close the gap in the rate, which removes the value of knowing us whatever the opponent's recogniser does.

## 1. What identifies a team, and how fast

Setup: 20 candidates (the reference list, avalon included), profile from the previous round, a naive-Bayes score over public events. Figures are the share of seats labelled correctly, averaged over teams and over the five round pairs. Chance is 5%. [M]

| Features | 5 hands | 10 | 20 | 40 | 80 | whole table |
|---|---|---|---|---|---|---|
| Everything | 41 | 59 | 73 | 79 | 81 | 82 |
| Exact sizes only (opens, bets, re-raises, chip rounding) | 35 | 52 | 67 | 76 | 78 | 78 |
| Sizes + preflop action rates (the Part 4 scorer) | 40 | 57 | 72 | 79 | 80 | 81 |
| Action frequencies by situation only | 13 | 19 | 28 | 37 | 48 | 53 |
| Limp / min-raise / shove patterns only | 10 | 14 | 18 | 24 | 36 | 43 |
| Exposed-card choices only | 7 | 8 | 9 | 12 | 15 | 19 |
| Hands shown at showdown only | 5 | 6 | 6 | 7 | 9 | 10 |
| **Everything except sizes** | **14** | **21** | **31** | **41** | **55** | **61** |

- **Uncertainty:** about 1,100 test seats per team per round, so sampling error is under 0.5 points. The spread between round pairs is the real uncertainty: at 20 hands with everything, 66, 56, 72, 85, 85 for R1→2 through R5→6.
- **Without sizes:** recognition falls from 73% to 31% at 20 hands and from 79% to 41% at 40. It only becomes usable (55-61%) at the end of a table.
- **Profiles two rounds old, everything:** 37 / 53 / 66 / 72 / 74 / 74. This reproduces the earlier 54 / 67 / 73 and the ceiling of about 76 (that run had 19 candidates and excluded us).
- **Same round, held-out tables** (a bot that did not change): 51 / 73 / 90 / 96 / 98 / 98; without sizes 18 / 28 / 41 / 56 / 74 / 80.
- **Variant choices:** the discard is never public, so only the exposed card could be scored, and it adds almost nothing.
- **Boston cross-check** (different variant and field, six scored-round files in unknown order, about 370 seats per team): everything 51 / 67 / 75 at 10 / 20 / 40 hands, sizes only 45 / 62 / 73, without sizes 16 / 23 / 32. Same picture. [M]

## 2. How identifiable we were

Our sizes were identical in all six rounds: opens of 2.2, 2.1, 2.5 and 3.0 big blinds by position, bets of 0.325, 0.75 and 1.0 pot, re-raises to 3.5x. [M]

| After hands | Our seats labelled avalon (everything) | Precision at a 1-in-20 prior | Sizes only | Without sizes |
|---|---|---|---|---|
| 5 | 39% | 52% | 32% | 10% |
| 10 | 65% | 70% | 58% | 16% |
| 20 | 88% | 82% | 84% | 24% |
| 40 | 97% | 90% | 96% | 34% |
| whole table | 98.5% | 94% | 98% | 65% (±14 across round pairs) |

- **What gives us away** [M], in bits of evidence per 100 of our hands against the other 19:
  - Open sizes 47 (3.7 bits per open, 12.7 opens per 100 hands), bet sizes 25, re-raise size 5, chip rounding 4.5; all sizes together 83.
  - Action frequencies 13, limp/shove patterns 9, exposed card about 0.
  - Telling 20 teams apart needs 4.3 bits, which is two opens.
- **Confusion set** [M]:
  - With sizes, three or four other teams each take 5% or more of our labels at 5-10 hands, and none by hand 20.
  - Without sizes, four to seven other teams through hand 40 (Team 82, one in a krillion, Gavilan), and one or two at the end (Gavilan, AZ).
  - Our nearest neighbour by frequencies is Gavilan.

## 3. What masking would cost and buy

### (i) Response to the size faced [M]

Heads-up, responders are the other top-20 teams, all bettors, six rounds. Each flop cell has 6,000-118,000 responses; standard error is at most 0.5 points.

| Bet / pot | <0.28 | 0.28-0.40 | 0.40-0.55 | 0.55-0.70 | 0.70-0.90 | 0.90-1.25 | >1.25 |
|---|---|---|---|---|---|---|---|
| Flop fold % | 20 | 29 | 51 | 61 | 67 | 72 | 80 |
| Turn fold % | 16 | 27 | 48 | 56 | 58 | 64 | 80 |
| River fold % | 19 | 32 | 54 | 61 | 63 | 72 | 85 |
| Break-even fold % for a bluff | 17 | 25 | 33 | 39 | 43 | 50 | 60 |

- **Our own bets** against the same responders: 0.325 pot is folded to 27 / 24 / 28% by street, 0.75 pot 62 / 45 / 47%, full pot 71 / 62 / 69%.
- **Preflop:** each top-20 player behind an open folds 72% to a min-raise, 74% to 2.05-2.25bb, 77% to 2.45-2.75bb, 80% to 2.75-3.25bb. A button open wins the blinds outright 38 / 43 / 49 / 56% of the time across those sizes.
- **What we would give up** [E]:
  - We bet into about 5,400 chips of pot per table (5.8 flop, 2.2 turn, 0.8 river bets). Each 0.01 pot of average value per bet is 0.2-0.3 points per table.
  - Moving our full-pot bets to half pot changes a bluff's value by about -0.17 pot and a value bet's by -0.03 to -0.07. Moving our small bets up changes them the other way.
  - The net is a few tenths to about one point per table. Its sign depends on which hands we bet at each size, which I did not measure.

### (ii) Most-common sizes [M]

How many of the other 19 use the most common value for at least 20% of that action in round 6: opens 6-11 teams depending on position, flop bet 0.5 pot 8, turn 0.65 pot 5, river 0.75 pot 7, re-raise 3x 9.

| | Found by hand 10 | 20 | 40 | whole table |
|---|---|---|---|---|
| No masking | 65 | 88 | 97 | 98.5 |
| First masked round (opponents hold our old profile) | 1.5 | 0.5 | 0.1 | 0.1 |
| Later rounds, sizes only | 88 | 98 | 99.5 | 99.6 |
| Later rounds, everything | 71 | 86 | 94 | 97 |

In the first round we are labelled Golden Knight (37%), AZ (15%) or 2 Curry (10%). A recogniser that ignores sizes is unaffected throughout: 24% at 20 hands, 65% at the end.

### (iii) Randomised sizes [M]

| | Found by hand 10 | 20 | 40 |
|---|---|---|---|
| Wide band (opens 2.0-2.6bb, bets 0.45-0.75 pot), first round | 8 | 7 | 6 |
| Wide band, later rounds | 75 | 93 | 98.5 |
| Our sizes jittered one step (0.05bb, 2.5% pot), first round, exact-size recogniser | 22 | 32 | 42 |
| Same jitter, recogniser that bins sizes (0.25bb, 0.1 pot) | 54 | 76 | 91 |
| Jitter of three steps, binned recogniser, first round | 35 | 50 | 63 |
| Jitter of three steps, binned recogniser, later rounds | 61 | 85 | 96 |

A randomising bot is detected as its own class about as well as a fixed one (91% from sizes alone by hand 20), because few teams spread their sizes. Binning costs the recogniser 1.6 points on us and 5 points across the field.

### (iv) Copying one team's sizes

Recognition is [M]; the counter's effect is [E], from the model in section 4.

| Copied team | First round: labelled as that team by hand 20 | Later rounds: we are found by hand 20 / 40 | That team's own recognition at hand 20 | Its counter applied to us, points per table for the opponent |
|---|---|---|---|---|
| 2 Curry | 84% | 82 / 93 | 93 → 77 | +0.22 |
| Gavilan (plays most like us) | 83% | 63 / 75 | 90 → 71 | -0.85 |
| TeamBallHog | 95% | 70 / 80 | 99 → 79 | -0.03 |
| Lemonade | 19% (sandylikesfrogs 42%) | 94 / 99 | 91 → 89 | +0.07 |
| Correctly identified as avalon | | | | +0.47 |

- **Last column:** the opponent's gain relative to treating us as an average finalist.
- **Taken for 2 Curry:** still helps the opponent, because 2 Curry also folds too much to re-raises (73%, field 65%, us 89%).
- **Taken for Gavilan** (folds 47%): the opponent stops bluffing us, which suits a bot that over-folds.
- **So a copy pays** only when the copied team has the opposite weakness to ours, for one round, and only while that team keeps its sizes. It also costs us our own sizing.

## 4. What being recognised is worth

Model: five spots where knowing a seat's fold rate changes what to do (re-raise its open, bet into it heads-up on each street, raise into its big blind). Chances and pot sizes are measured. Chips convert to points at the measured 0.0054 points per chip with 7-8 players left (0.0046 at 5, 0.0036 at 4). [M]

- **Upper bound** [E]: every chance is used, and the gain is the gap in fold rate × (pot + amount risked).
- **Central estimate** [E]: only the hands whose decision flips gain, which gives half the gap squared × (pot + risk). It assumes bluff thresholds are spread evenly over hands.

| Seat known to be | Fold to re-raise | Upper bound, points per table per informed opponent | Central estimate |
|---|---|---|---|
| avalon, round 6 | 89% (field 65%) | 4.2 (3.2 of it from re-raises) | 0.47 (0.37) |
| avalon, round 1 | 87% (field 58%) | 5.5 | 0.76 |
| 2 Curry, round 1 → 6 | 84% → 73% | 6.9 → 1.8 | 0.83 → 0.07 |
| Lemonade | 67-72% | 0.4-0.9 | 0.02-0.08 |
| sandylikesfrogs, rounds 1 / 2 / 6 | 44% → 72% | 4.8 → 2.3 | 0.38 / 1.12 / 0.10 |
| Median of the other 19, round 6 | | 2.4 | 0.13 |

- **Against us** [E]: if all seven opponents had known us, about 3.3 points per table on the central estimate. With our fold to re-raises at the field's rate it would be about 0.7. For scale, the gap to first place was 2.5 points per table.
- **For us** [E]: perfect knowledge of all seven seats is worth about 1.9 points per table on the central estimate. Nearly all of it comes from four or five teams with large gaps (Team 123 1.08, Team 72 0.65, stanford deviants 0.64). Knowing 2 Curry and Lemonade was worth under 0.1 each after round 2.
- **Delay barely matters** [M]: knowing us only from hand 20 keeps about 90% of the value, because the pots are larger later.
- **In-table evidence cannot replace identity for the rare spots** [M]: per table we faced 2.5 re-raises, 3.1 flop bets, 0.8 turn bets and 0.4 river bets heads-up. For frequent actions (40 open chances per table) it can.
- **Nobody was using it against us at the regional** [M]: top-20 players re-raised our opens only 0.4-1.9 points more often than other top-20 openers' at the same position and size. We faced 2.5 re-raises on 11.5 opens per table.

Not counted: what a team's bets mean by size (our small and pot-sized bets may carry different hands), calling ranges against all-ins, and bluff frequencies. The true ceiling is higher than these five spots.

## 5. The levels

| Level | Move | Result |
|---|---|---|
| 0 | We do nothing | Known by about hand 7 (median), 88% by hand 20 [M]. Exposure is our rate gaps: about 0.5 points per informed opponent per table [E]. |
| 1 | We change sizes (any way) | One round at under 10% found [M]. Cost: whatever the new sizes lose, up to about a point per table [E]. |
| 2 | Opponent re-profiles each round, bins sizes, falls back on frequencies and live counts | Back to 82-95% by hand 20 from the second round. Without sizes: 24% at hand 20, 65% at the end [M]. |
| 3 | We vary frequencies too | This is changing how we play. The cost is first-order and unmeasured; what it protects is at most the 0.1-0.5 above [R]. |
| 4 | Opponent ignores identity, uses only live evidence | It cannot learn our rare-spot rates in one table, so it treats us as an average finalist [M for the counts, R for the conclusion]. |

The chain ends at level 4, and level 4 is also the best outcome masking can reach. We get the same outcome at no cost in sizing by having no large gap in the rare spots. Then a correct identification is worth about 0.1 per opponent, and a wrong one costs the opponent.

**Policy:**
- Choose sizes for value against the field's measured response.
- Keep the rare-spot rates near the field's unless the evidence says a gap pays.
- Spend the effort on recognising others, where the value is concentrated in a few teams with large gaps.

## 6. Prompt-ready text

**Replace the last bullet of Part 4 ("We are being profiled too...") with:**

```
- We are being profiled too, and changing our sizes does not hide us for more than one round. Do not move
  a size away from its best value to disguise it. Instead, every round, from the download: (1) run our
  own recogniser on our own seats and report the hand by which we are identified; (2) list our rates in
  the spots a seat reaches only 0 to 4 times a table (fold to a re-raise, fold to a bet on each street
  heads-up, big blind's fold to a late raise, fold to a raise after betting, call of an all-in) next to
  the average of the other teams, and flag any gap above 10 points; (3) for each flagged gap say what an
  opponent who knew it would do and what it costs per table. A flagged gap is a top candidate change.
```

**Add to the recogniser paragraph of Part 4:**

```
Score seats from exact sizes and preflop action rates only; exposed cards and showdown hands add about one
point of accuracy and are not worth the code. Compare sizes in bins (about a quarter of a big blind for
opens, a tenth of the pot for bets) so a one-chip change does not break a match. Sizes can be copied: before
a team's profile moves a decision far from the field's, check that the seat's live open and re-raise rates
at this table are within that team's range, and if not fall back to the field's rates. A seat that matches
no profile is an average finalist. Keep, per team, the rare-spot rates above and flag the teams whose gap
from the field exceeds 15 points: those few seats are where a profile pays.
```

**Add to the leak finder (Part 2), on sizing:**

```
Tabulate the field's fold, call and raise rates by the size faced (bins of bet over pot, by street,
heads-up and multiway separately; open size by position) and pick each of our sizes from that table for
what the bet is meant to do. At the regional the best teams folded 51% to half-pot flop bets, 67-72% to
three-quarter and full-pot bets, and under 30% to bets below 0.4 pot.
```

**In the bot from the first hour:**
- The size-response table.
- The rare-spot gap table for ourselves.
- The Part 4 recogniser with binned sizes and the live-rate check.

**Not worth building:**
- Most-common-size masking.
- Randomised sizes as disguise.
- Copying a team's sizes.
- Disguising frequencies.
- Exposed-card and showdown features in the recogniser.

One free option: when sizes are re-tuned between rounds anyway, never ship exactly the same amounts twice. It only defeats recognisers that match exact amounts (88% → 32% at hand 20, for one round).

## 7. Limits

- **Only our tables.** Our files contain only tables we sat at. Every other team's play is measured in our presence (about 1,100 seats per team per round). How the top teams play each other without us is not observed.
- **Stable bots flatter the recogniser.** We kept one set of sizes for six rounds, and several teams never changed theirs. In the Finals every bot is rewritten between rounds, so expect accuracy nearer the R2→R3 figure (56% at 20 hands) than the average.
- **Masks are simulated** by rewriting our size tokens. Opponents' reactions to different sizes within the hand are not replayed, so the cost in 3(i) comes from the response table, not from a re-run.
- **Value figures are narrow.** They cover five fold-based spots with a simple bluff model and other players assumed to fold. The upper bound is generous; the central estimate rests on one assumption about how thresholds are spread.
- **Table length.** Regional tables ran about 90 hands; the Finals run about 125, which gives a recogniser more time.
- **Boston round order is unknown**, so that check mixes lags.
- **The response table mixes bettors and situations.** The within-team slopes in the dispute answer are the controlled version.

## Files

All in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/strategy/identity/`:

| Section | Scripts | Outputs |
|---|---|---|
| Extraction (one pass per round) | `extract.py`, `lib.py` | `R1.pkl` … `R6.pkl` |
| 1 | `recog.py` | `res_recog.json` |
| 2 | `q2.py` | `q2.out` |
| 3 (i) | `resp.py` | `resp.out` |
| 3 (ii)-(iv) | `mask.py`, `jit.py` | `mask.out`, `res_mask.json`, `jit.out` |
| 4 | `ledger.py`, `q4.py`, `q4b.py` | `ledger.out`, `q4.out`, `q4b.out` |
| Boston cross-check | `boston/recog_b.py` | `boston/recog_b.out` |