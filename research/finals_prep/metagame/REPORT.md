# Metagame simulations: which styles win against which fields

Team avalon, prepared 2026-11-12 for the Finals on 2026-11-15. Everything here comes from the clone-field
simulator, which reproduces frequencies and is frozen: its clones do not adapt to us.

**Read every result below as a candidate to test on the real field, not as a conclusion.** The simulator
cannot separate differences under about 1-2 points, however many tables are run. Each headline is labelled:

- **Holds:** larger than 2 points, and in the same direction under both clone settings (standard and bluffy).
- **Weak:** 1-2 points under both settings.
- **Unresolved:** under 1 point, or it flips between settings, fits or seeds.

The ± values are sampling standard errors on paired deals, about ±0.2. They are much smaller than the
simulator's bias, and the bias is what limits these results.

## How it was run

- **Fields.** Clones fitted from scored round 6 (the latest) and from round 1 (to check drift), with avalon
  included as a clone. Each field was calibrated with the inherited calibrate.sh:
  - standard setting: eps 0.1, beta 0.06/0.08/0.12;
  - bluffy setting: eps 0.15, beta 0.10/0.15/0.20, calibrated separately on round 6.
  - Calibration matched the earlier fields: per-team correlation 0.95-0.99 on preflop rates; total-variation
    error per cell 0.031.
- **Runner.** `mrun.py` plays one hero against seven opponents. Opponents are drawn from a team list and/or
  replaced by archetypes at set shares. The draw depends only on (seed, table), so all heroes in a field
  play the same deals, and the 25/50/100% mixes share their underlying draws.
  - Tournament mode uses the kit's `seat_iteration`, with non-scoring fillers on the short table.
- **Where it ran.** 3.0 million clone tables ran on Modal (app `nolimit-strategy-sim`); our real bots ran
  locally under the kit's 1 ms limit.
  - The Modal run gave byte-identical rows to a local run on the same seeds.
  - Modal spend was **$16.91** (Modal billing report, today). All app runs are stopped (last stop at 15:38 PST).
  - No hand histories or acc.pkl left the machine; only fitted parameters and code were uploaded.
- **Table counts.** 12,000 tables per archetype cell (8,000 for the three-style sweep and the full-field
  team runs; 4,000 or 3,000 for our real bots).

**Archetypes, as built:**

| name | how it was made | measured in the top-20 field (VPIP / PFR / 3-bet / fold to 3-bet / limp / open-jam / call all-in / flop fold to bet) |
|---|---|---|
| TIGHT | the mean top-20 postflop, with preflop rewritten: narrow opens, 3-bets rare, call-offs only with strong hands, shove-or-fold under 16 bb | 15 / 12 / 5 / 75 / 0 / 6 / 19 / 49 |
| WIDE | 2 Curry's round-6 clone, unchanged | 37 / 35 / 38 / 70 / 0 / 6 / 13 / 58 |
| LIMPSHOVE | Lemonade's round-6 clone, unchanged | 27 / 11 / 12 / 76 / 22 / 8 / 16 / 74 |
| BAL | the cell-by-cell mean of the 20 top teams | 34 / 28 / 23 / 66 / 3 / 7 / 19 / 59 |
| CALLER | BAL that limps, calls and calls down; folds to bets halved | 58 / 8 / 5 / 35 / 51 / 0 / 37 / 34 |
| HYPER | thepastaway's round-6 clone, unchanged (very loose, limp/re-raise) | 56 / 40 / 60 / 35 / 30 / 8 / 24 / 60 |

Each archetype behaves as intended. Their rates barely move across fields (appendix). Two caveats:

- BAL is an average of cells, so it is not a coherent strategy. Its poor results say little about a
  well-built balanced bot.
- The clones of the strongest real teams score 2-9 points below those teams' real results. In the full
  round-6 field, 2 Curry's clone scored 16.6 against a real 18.7, Lemonade's 15.7 against 19.2, and
  thepastaway's 11.7 against 20.3.
  - Within the top 20, a clone's simulated score correlated with the team's real score at only -0.09 to
    0.33.
  - So the archetypes carry each style's frequencies, not whatever else made those teams good.

## 1. A finalist-like field

**Clone-only tournament of the top 20.** 12,000 iterations: 20 entries, three tables with fillers. Each
clone's top-20 score is compared with its score as the one test seat in the full 127-team field.

| | round-6 fit | round-1 fit |
|---|---|---|
| Change, top-20 minus full field, all 20 teams | -0.7 to -3.4 | +0.1 to -2.7 |
| Correlation of top-20 and full-field ranking | 0.83 | 0.91 |
| Held up best | thepastaway -0.7, Lemonade -0.8, Chikerbot -1.0, Gavilan -1.1, Team 123 -1.3 | Lemonade +0.1, Team 123 -0.2, avalon -0.3, Gavilan -0.9 |
| Lost most | stanford deviants -3.4, pocket rockets -3.2, Team 82 -3.2, TeamBallHog -2.9, 2 Curry -2.7 | Always Folds -2.7, Team 72 -2.7, 2 Curry -2.3 |
| Style most linked to holding up (correlation with the change) | calls all-ins +0.71, limps +0.53, folds to 3-bets -0.53, PFR -0.26 | limps +0.25, PFR -0.46, VPIP -0.36 |

The full field averages above 12.5 points for strong teams; a top-20-only field averages exactly 12.5. So
every top team loses a few points in the strong-only field; the question is who loses more.

- **Weak:** the limp-or-shove style held up best in both fits. Lemonade lost the least of all 20 teams both
  times, and its clone topped the round-6 top-20 tournament (14.9). The wide raise-first style (2 Curry)
  lost more than average in both fits (-2.7 and -2.3).
  - The gap from Lemonade to the field's average change is about 1.5-2 points: at the simulator's
    resolution, not beyond it.
  - Under the bluffy setting, the top-20 scores correlate 0.98 with standard; no team moved more than
    0.8 (2 Curry +0.8).
- **Unresolved:** any ranking of individual finalists. The spread of changes (2.5 points) is near the
  resolution, the style correlations differ between the two fits, and the clones do not track real scores
  within the top 20.

**Our real bots in the strong-only field** (paired deals; avalon removed from the opponent pool):

| field | v10 | v6 | v3b | v10 - v6 | v10 - v3b |
|---|---|---|---|---|---|
| round-6 full | 17.9 | 18.2 | 15.9 | -0.3 ±0.3 | +2.0 ±0.3 |
| round-6 top-20 | 14.1 | 14.3 | 13.2 | -0.2 ±0.3 | +0.9 ±0.3 |
| round-6 top-20, bluffy | 14.4 | 14.2 | 13.0 | +0.2 ±0.3 | +1.4 ±0.3 |
| round-1 full | 20.7 | 20.3 | 17.7 | +0.5 ±0.3 | +3.0 ±0.4 |
| round-1 top-20 | 18.9 | 18.6 | 15.5 | +0.3 ±0.3 | +3.4 ±0.3 |

- **Holds:** the order does not change. v10 and v6 are indistinguishable (|difference| ≤ 0.5 in every field
  and setting), and v3b is behind (0.9-3.4).
- **Holds:** the drop. In the round-6 field (the strongest version of the field), our best bot loses about
  4 points going from the full field to the top 20 (18 to 14); in the round-1 field it loses about 2.
  Expect Finals scores near 14-15 for a regional-quality bot, not 18-20.
- **Weak:** v3b's gap shrank from +2.0 to +0.9 in the round-6 strong-only field. It did not shrink in the
  round-1 field or under bluffy (+1.4).

## 2. Matchup table

Rows are the one differing seat; columns are the other seven seats. Points per table at 12,000 tables, with
standard errors of 0.10-0.20. The paired lead of each column's best style over the runner-up is in the appendix.

| hero \ field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | top-20 | full regional |
|---|---|---|---|---|---|---|---|---|
| TIGHT | **12.5** | 11.6 | **14.9** | 15.0 | **23.9** | **21.3** | 14.2 | 14.4 |
| WIDE | **18.2** | **12.5** | 11.9 | 14.0 | 16.2 | 14.2 | 14.0 | **17.0** |
| LIMPSHOVE | 10.8 | **15.1** | 12.6 | **15.0** | 18.5 | 19.3 | **15.0** | 15.4 |
| BAL | 12.2 | 12.1 | 10.4 | 12.5 | 17.5 | 15.7 | 12.7 | 14.7 |
| CALLER | 3.2 | 4.9 | 5.6 | 4.7 | 12.4 | 9.3 | 5.1 | 5.4 |
| HYPER | 7.2 | 14.2 | 8.5 | 10.3 | 11.0 | 12.5 | 11.0 | 11.6 |

Bluffy setting (separately calibrated round-6 field):

| hero \ field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | top-20 | full |
|---|---|---|---|---|---|---|---|---|
| TIGHT | 12.4 | 11.3 | **15.6** | 14.7 | **22.1** | **21.7** | 14.0 | 14.1 |
| WIDE | **19.0** | 12.5 | 12.7 | 14.4 | 15.8 | 14.7 | **14.5** | **17.5** |
| LIMPSHOVE | 10.8 | **14.4** | 12.6 | **14.8** | 16.2 | 19.9 | **14.5** | 15.0 |
| BAL | 12.4 | 12.0 | 10.3 | 12.4 | 16.2 | 16.1 | 12.7 | 14.5 |
| CALLER | 4.4 | 5.6 | 7.1 | 5.5 | 12.3 | 10.3 | 6.1 | 6.2 |
| HYPER | 7.2 | 13.2 | 7.9 | 9.5 | 9.1 | 12.5 | 10.4 | 11.0 |

**There is a rock-paper-scissors cycle (Holds).** Each step below beats the field's own style by more than
2 points under both settings:

| field | best response | gain over the field's own style (standard / bluffy) |
|---|---|---|
| tight | wide re-raising | +5.7 / +6.5 |
| wide re-raising | limp-or-shove | +2.6 / +1.9 |
| limp-or-shove | tight | +2.3 / +3.0 |

These are pure fields, which are extreme; the mixed fields in section 3 show the same order with smaller
margins.

**No style is best everywhere.**
- **Holds:** in the full regional field, wide re-raising is best by 1.6 (bluffy 2.5). It gives up 3.0 points
  when the weak teams are removed (17.0 to 14.0; bluffy 17.5 to 14.5). Limp-or-shove gives up only 0.4-0.5,
  and tight 0.2. This matches 2 Curry winning the regional by feeding on weak teams.
- **Unresolved:** the best style against the actual top-20 field. The standard setting has limp-or-shove
  15.0, tight 14.2, wide 14.0, all within 1 point. Bluffy has limp-or-shove 14.5 and wide 14.5 tied, with
  tight 14.0. A fresh seed agrees: 14.6 / 14.2 / 13.9.
  - With the archetypes and the field both fitted from round 1, the order changes to tight 14.0, wide 14.0,
    limp-or-shove 12.5. Lemonade's round-1 clone was the weaker one.
- **Holds:** BAL, CALLER and HYPER are never the best of the main options.
  - The calling station loses everywhere (3-7 points in other fields).
  - The very loose style scores only 7-11 except against wide raisers.
  - The averaged "balanced" profile is 2.3-6.4 behind the best response in every field.

**Best worst case: Unresolved.**
- Pure fields:

  | style | worst score (standard / bluffy) | field where it happens |
  |---|---|---|
  | wide | 11.9 / 12.5 | limp-or-shove |
  | tight | 11.6 / 11.3 | wide |
  | limp-or-shove | 10.8 / 10.8 | tight |
  | BAL | 10.4 / 10.3 | limp-or-shove |

- 26 mixed fields (top-20 based plus three-style mixes):

  | style | mean | minimum | fields won |
  |---|---|---|---|
  | limp-or-shove | 13.5 | 11.1 | 14 |
  | wide | 13.4 | 11.4 | 8 |
  | tight | 13.1 | 10.9 | 4 |
  | BAL | 11.7 | 10.4 | 0 |

The three main styles are within 0.5 on both measures. The only firm statement is that BAL, CALLER and HYPER
have the worst worst cases.

**Our real bots against the same skeletons** (3,000 tables, paired): v10 scores 13.7 in a tight field, where
the wide clone scores 18.2. In a wide field v10 scores 13.2, against 15.1 for limp-or-shove.
- v10 folds 90% to 3-bets in the wide field, against 70% for the wide clone and 77% for limp-or-shove. This
  is the regional fold-to-3-bet leak, and it costs most where the field re-raises wide.
- v10 and v6 are indistinguishable in every pure field.

## 3. The response chain

The top-20 field, with a share of its seats replaced by the style in each row. All differences are paired.

| field | TIGHT | WIDE | LIMPSHOVE | BAL | HYPER | best, lead over runner-up |
|---|---|---|---|---|---|---|
| top-20 as is | 14.2 | 14.0 | **15.0** | 12.7 | 11.0 | limp-or-shove +0.9 (bluffy: tie with wide) |
| 25% limp-or-shove | 14.3 | 13.1 | **14.5** | 12.1 | 10.1 | limp-or-shove +0.2 |
| 50% limp-or-shove | **14.5** | 12.9 | 13.9 | 11.4 | 9.7 | tight +0.6 |
| 100% limp-or-shove | **14.9** | 11.9 | 12.6 | 10.4 | 8.5 | tight +2.3 (bluffy +2.9) |
| 25% tight | 13.4 | **14.3** | 13.9 | 11.9 | 10.2 | wide +0.4 |
| 50% tight | 12.9 | **15.0** | 13.2 | 12.3 | 9.3 | wide +1.8 (bluffy +2.7) |
| 100% tight | 12.5 | **18.2** | 10.8 | 12.2 | 7.2 | wide +5.7 (bluffy +6.5) |
| 25% wide | 13.2 | 13.0 | **14.6** | 12.4 | 11.7 | limp-or-shove +1.4 |
| 50% wide | 12.6 | 13.0 | **14.6** | 12.3 | 12.7 | limp-or-shove +1.6 (bluffy +0.9; seed 2 +1.7) |
| 100% wide | 11.6 | 12.5 | **15.1** | 12.1 | 14.2 | limp-or-shove +0.9 over loose, +2.6 over wide |

Reading the chain:
- **Level 1:** against the top-20 field, limp-or-shove leads (Unresolved).
- **Level 2:** as the field copies limp-or-shove, tight takes over. It ties at 25%, leads by 0.6 at 50%
  (Unresolved) and by 2.3-2.9 at 100% (Holds).
- **Level 3:** as the field turns tight, wide re-raising takes over: +0.4 at 25%, +1.8-2.7 at 50%, +5.7-6.5
  at 100%.
- **Level 4:** as the field turns wide, limp-or-shove leads again by 0.9-1.7 at 25-50% (Weak).
- **The chain cycles; it does not converge.** At 25% adoption no style's lead exceeds 1.4. The cycle only
  becomes clear once about half the field plays one style.
- **The leader's edge shrinks as others copy it:**

  | share of the field copying it | 0% | 25% | 50% | 100% |
  |---|---|---|---|---|
  | limp-or-shove | 15.0 | 14.5 | 13.9 | 12.6 |
  | wide | 14.0 | 13.0 | 13.0 | 12.5 |
  | tight | 14.2 | 13.4 | 12.9 | 12.5 |

  Roughly half of a style's edge is gone once a quarter to a half of the field plays it.

**When most of the field plays 2 Curry's wide re-raising style:**
- What beats it: limp-or-shove, by 1.6 at 50% wide (Weak) and by 2.6 over wide itself at 100% (Holds).
  A loose re-raise-and-call style also does well at 100% (14.2).
- What does not: **the tight style is the worst main response to wide re-raisers** (12.6 at 50%, 11.6 at
  100%; bluffy 12.4 and 11.3). Holds as a direction: tight is last of the three main styles in every
  wide-heavy field.

**When the field turns tight in response:** wide re-raising wins by a lot: +1.8 at half tight, +5.7 at all
tight (Holds).

## 4. Tightness: when the reserve bot pays

"Aggressive" has to be split into two kinds, because they call for opposite responses.

**Aggression from wide raising and re-raising** (2 Curry-like): tight never overtakes. Even with the
aggressive share made half wide and half limp-or-shove, at 25%, 50%, 75% and 100% of the field,
limp-or-shove stays best (by 0.9-1.1). Tight is second, 0.9-1.1 behind.

**Aggression from shoving, limping and loose calling:** tight overtakes. Three-style sweep (8,000 tables,
seat shares in quarters):

| tight / wide / limp-or-shove share | TIGHT | WIDE | LIMPSHOVE | best |
|---|---|---|---|---|
| 0 / 25 / 75 | **13.7** | 11.5 | 13.2 | tight +0.6 |
| 25 / 0 / 75 | **14.2** | 12.5 | 11.6 | tight +1.7 |
| 0 / 50 / 50 | 12.4 | 11.4 | **13.2** | limp-or-shove +0.8 |
| 25 / 25 / 50 | 12.5 | 12.5 | 12.3 | tie |
| 0 / 75 / 25 | 11.8 | 11.8 | **14.3** | limp-or-shove +2.5 |
| 50 / 25 / 25 | 12.3 | **13.8** | 12.2 | wide +1.4 |
| 75 / 25 / 0 | 11.7 | **15.5** | 12.1 | wide +3.4 |

- Against the top-20 field with part of it replaced:

  | replaced by | 25% | 50% | 100% |
  |---|---|---|---|
  | limp-or-shove | tight ties | tight +0.6 | tight +2.3 |
  | very loose (half wide, half very loose) | | tight 0.8 behind | tight ties |
  | calling station | tight +0.8 | tight +1.5 | tight +5.4 |

- **The threshold (Weak):** tight is the best style once **about half or more of the opponents are
  shove/limp-heavy or loose callers AND wide re-raisers are a quarter of the field or less**. It is clearly
  best (by 2 or more) only at three-quarters or more. With wide re-raisers above a quarter, tight is not
  the answer at any level of shoving.

**Sensitivity of the tight style** (paired differences from the default tight; standard setting, bluffy in
brackets):

| change | top-20 | 100% wide | 100% limp-or-shove | 100% very loose | verdict |
|---|---|---|---|---|---|
| call off half as often | -0.3 | +0.1 | 0.0 | -0.1 | Unresolved (no effect) |
| call off 2x as often | -0.4 (-0.5) | -0.4 (-0.5) | -1.7 (-1.7) | -1.0 (-1.2) | Weak: wider call-offs hurt |
| call off 4x as often | -1.3 (-1.6) | -1.2 (-1.1) | -3.1 (-3.0) | -2.8 (-3.2) | Holds: much wider call-offs cost 1-3 |
| no shove-or-fold when short | -0.2 (-0.1) | -0.4 (-0.3) | +0.1 (-0.1) | +0.3 (+0.2) | Unresolved (insensitive) |
| short-stack shoves x0.5 / x2 | +0.1 / -0.3 | 0.0 / +0.2 | +0.2 / -0.5 | +0.2 / -0.4 | Unresolved |
| open 0.7x as many hands | 0.0 (0.0) | +0.2 (+0.2) | +0.8 (+0.7) | +0.9 (+1.0) | Weak: open even fewer against shovers |
| open 1.5x as many hands | -0.4 | -0.4 | -1.4 | -1.3 | Weak: do not widen |

At the default, the tight bot called 18-20% of the all-ins it faced. Wider call-offs never helped in any
field, including the shove-heavy ones. The short-stack plan made no measurable difference.

## 5. Sensitivity (bluffy setting): what survives

| conclusion | standard | bluffy | label |
|---|---|---|---|
| Rock-paper-scissors cycle: tight → wide → limp-or-shove → tight | +5.7, +2.6, +2.3 | +6.5, +1.9, +3.0 | Holds |
| Wide re-raising pays against the full field, not the strong-only field | +1.6 lead; -3.0 drop | +2.5 lead; -3.0 drop | Holds |
| Tight is the worst main response to wide re-raisers | last in all wide-heavy fields | last | Holds |
| Tight beats shove/limp/calling fields | +2.3 to +5.4 | +2.9 to +5.9 | Holds |
| Calling off much wider (4x) hurts the tight bot | -1.2 to -3.1 | -1.1 to -3.2 | Holds |
| Calling station, very loose and averaged styles never best | | | Holds |
| v10 ≈ v6 > v3b in the strong-only field | -0.2; +0.9 | +0.2; +1.4 | Holds for the order; v10 vs v6 Unresolved |
| Best style against the top-20 field as it was | limp-or-shove +0.9 | tie with wide | Unresolved |
| Limp-or-shove leads at 50% wide | +1.6 | +0.9 | Weak |
| Which individual finalists hold up | Lemonade best both fits | 0.98 correlation | Weak / Unresolved |
| Best worst case among tight, wide, limp-or-shove | within 0.5 | within 0.5 | Unresolved |
| Tight sensitivity to short-stack shoving | < 0.5 | < 0.5 | Unresolved |

## What was not run, and limits

- Clones do not adapt. Real finalists will respond within a round and between rounds, which speeds up the
  cycle above; the regional showed the field's 3-bet rate doubling.
- The archetypes are clones of regional teams or edits of averaged cells, not well-built bots. Absolute
  levels are low by 2-9 points for the strong teams' styles.
- Everything is on the regional variant (3 cards, discard and expose). The Finals variant is different;
  only preflop and stack-depth style is likely to carry over.
- Our real bots were tested in pure archetype fields only for v10 and v6, and not in the mixed chain fields.
  There is no real-bot run on the round-1 bluffy field.
- The chain's levels 2-4 used share replacement in the top-20 field, not a full re-optimisation. Archetype
  mixes other than those listed were not tried. There was no seat-position or stack-depth breakdown.
- About 20-50 of roughly 500,000 decisions timed out for v10 locally under load. This is negligible.

## Implications for the plan (instructions, no code)

1. **Build the three planned styles in the first hour.** They are the three corners of the cycle:
   balanced/pressure (B, wide re-raising), shove-heavy (C, limp-or-shove) and tight (D).
   - Against a strong field none of them has a resolved lead, so the practice rounds must decide.
   - Put C (shove-heavy) and B (wide) in the build practice rounds before A.
   - A "balanced" bot made by averaging what the field does is the worst of the lot. Build A as a coherent
     equity bot, or drop it.
2. **Expect lower scores.** A regional-quality bot scores about 14-15 against finalists, not 18-20. Don't
   read a 15 in round 1 as failure.
3. **Fix fold-to-3-bet in every bot.** Fold no more than about 75% to 3-bets. The wide clone folds 70% and
   the limp-or-shove clone 77%; v10 folded 89-93%. In a wide field v10 trails limp-or-shove by 1.9, and
   this is the most visible difference between them.
4. **Narrow the reserve bot D's trigger.** "Aggressive field" is not enough. From the latest round's
   download, classify each opponent team:
   - **wide re-raiser:** 3-bet ≥ 25% with PFR ≥ 30%;
   - **shove/limp-heavy:** limp ≥ 15%, or open-jam ≥ 8%, or VPIP ≥ 50%;
   - **tight:** VPIP ≤ 20% and 3-bet ≤ 8%.
   For reference, the regional top 20 in round 6 had about 6 wide re-raisers, 2 shove/limp-heavy teams
   (Lemonade, and thepastaway, which also counts as a wide re-raiser) and no tight ones. Then:
   - **Switch to D** only when shove/limp-heavy teams are half or more of the opponents and wide re-raisers
     are a quarter or fewer. Expect +0.5 to +2 at those mixes.
   - **If wide re-raisers are a third or more, use C (limp-or-shove, re-shove over opens), never D.**
     Tight is the worst answer to wide re-raisers.
   - **If tight teams are a third or more, use B (wide opens and re-raises).** This is the largest edge in
     the table.
5. **Settings for D:**
   - Call off all-ins only with strong hands: about the top fifth of what it faces, 18-20% of all-ins.
     Calling twice as often cost 0.4-1.7, and four times as often cost 1-3.
   - Against shovers, open even fewer hands, not more.
   - Shove-or-fold when short is optional; it made no measurable difference.
6. **Revise the "milder response" in A/B/C.** The prompt pack has them open fewer hands and call off more
   as the table's raises and shoves rise. That is right against shovers: open fewer, but keep call-offs
   narrow. Against frequent re-raisers it is wrong: answer with re-shoves and fewer folds to 3-bets, not
   by tightening.
7. **Expect the field to cycle.** If one style is clearly winning after round 1, a quarter to half of the
   finalists copying it removes about half its edge. Plan the challenger as the next style in the cycle:
   - after wide wins, limp-or-shove;
   - after limp-or-shove wins, tight;
   - after tight wins, wide.
   Switch when the round data shows the copy: the share of teams in the winner's class rising by about a
   quarter of the field.
8. **Use the cloned field for direction only.** Every number here is a candidate for the practice rounds.
   Only "Holds" items should change a decision without real-field evidence.

## Files

All under `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/strategy/metagame/`:
- `REPORT.md`: this report.
- `mrun.py`: the runner.
- `modal_app.py`, `bundle.sh`: the Modal fan-out.
- `arch.py`: builds the archetypes.
- `gen.py`: generates the job lists.
- `an1.py`-`an5.py`: the analysis scripts.
- `fields/{r6,r1,r6_bluffy}`: the calibrated fields; `arch/` inside each holds the archetype parameters.
- `out/*.pkl`: results.
- `logs/`: run logs.


# Appendix: generated tables

Generated by an1.py-an5.py from out/*.pkl. Standard clone setting unless marked bluffy.

### Matchup table: row = the one differing seat (hero), column = the other 7 seats. Points per table (se).
| hero \ field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | TOP20 | FULL | worst | mean of archetype fields |
|---|---|---|---|---|---|---|---|---|---|---|
| TIGHT | 12.5 (0.16) | 11.6 (0.14) | 14.9 (0.16) | 15.0 (0.15) | 23.9 (0.17) | 21.3 (0.16) | 14.2 (0.15) | 14.4 (0.16) | 11.6 | 16.6 |
| WIDE | 18.2 (0.20) | 12.5 (0.16) | 11.9 (0.16) | 14.0 (0.17) | 16.2 (0.17) | 14.2 (0.15) | 14.0 (0.17) | 17.0 (0.19) | 11.9 | 14.5 |
| LIMPSHOVE | 10.8 (0.16) | 15.1 (0.17) | 12.6 (0.16) | 15.0 (0.17) | 18.5 (0.18) | 19.3 (0.16) | 15.0 (0.17) | 15.4 (0.18) | 10.8 | 15.2 |
| BAL | 12.2 (0.17) | 12.1 (0.16) | 10.4 (0.16) | 12.5 (0.16) | 17.5 (0.18) | 15.7 (0.16) | 12.7 (0.17) | 14.7 (0.18) | 10.4 | 13.4 |
| CALLER | 3.2 (0.10) | 4.9 (0.12) | 5.6 (0.12) | 4.7 (0.12) | 12.4 (0.16) | 9.3 (0.16) | 5.1 (0.12) | 5.4 (0.13) | 3.2 | 6.7 |
| HYPER | 7.2 (0.15) | 14.2 (0.19) | 8.5 (0.15) | 10.3 (0.16) | 11.0 (0.16) | 12.5 (0.16) | 11.0 (0.17) | 11.6 (0.18) | 7.2 | 10.6 |

Best response per field (paired difference of the best over the runner-up, same deals):
- TIGHT: WIDE 18.2 > TIGHT 12.5 > BAL 12.2 > LIMPSHOVE 10.8 > HYPER 7.2 > CALLER 3.2; lead +5.7 ±0.2; gain from deviating from the field's own style: +5.7 ±0.2
- WIDE: LIMPSHOVE 15.1 > HYPER 14.2 > WIDE 12.5 > BAL 12.1 > TIGHT 11.6 > CALLER 4.9; lead +0.9 ±0.2; gain from deviating from the field's own style: +2.6 ±0.2
- LIMPSHOVE: TIGHT 14.9 > LIMPSHOVE 12.6 > WIDE 11.9 > BAL 10.4 > HYPER 8.5 > CALLER 5.6; lead +2.3 ±0.2; gain from deviating from the field's own style: +2.3 ±0.2
- BAL: LIMPSHOVE 15.0 > TIGHT 15.0 > WIDE 14.0 > BAL 12.5 > HYPER 10.3 > CALLER 4.7; lead +0.1 ±0.2; gain from deviating from the field's own style: +2.6 ±0.2
- CALLER: TIGHT 23.9 > LIMPSHOVE 18.5 > BAL 17.5 > WIDE 16.2 > CALLER 12.4 > HYPER 11.0; lead +5.4 ±0.2; gain from deviating from the field's own style: +11.5 ±0.2
- HYPER: TIGHT 21.3 > LIMPSHOVE 19.3 > BAL 15.7 > WIDE 14.2 > HYPER 12.5 > CALLER 9.3; lead +2.1 ±0.2; gain from deviating from the field's own style: +8.8 ±0.2
- TOP20: LIMPSHOVE 15.0 > TIGHT 14.2 > WIDE 14.0 > BAL 12.7 > HYPER 11.0 > CALLER 5.1; lead +0.9 ±0.2
- FULL: WIDE 17.0 > LIMPSHOVE 15.4 > BAL 14.7 > TIGHT 14.4 > HYPER 11.6 > CALLER 5.4; lead +1.6 ±0.2

Measured rates (%) as the hero in the TOP20 field:
| archetype | vpip | pfr | open | openjam | limp | 3bet | fold_to_3bet | 4bet | call_allin | flop_bet | flop_fold_to_bet | turn_fold_to_bet | river_fold_to_bet | wtsd | wsd | 1st/2nd/3rd | hands alive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TIGHT | 15 | 12 | 20 | 6 | 0 | 5 | 75 | 15 | 19 | 71 | 49 | 37 | 46 | 57 | 56 | 8/21/18 | 86 |
| WIDE | 37 | 35 | 43 | 6 | 0 | 38 | 70 | 11 | 13 | 75 | 58 | 43 | 40 | 41 | 53 | 14/14/13 | 78 |
| LIMPSHOVE | 27 | 11 | 9 | 8 | 22 | 12 | 76 | 10 | 16 | 64 | 74 | 42 | 43 | 35 | 54 | 15/17/14 | 75 |
| BAL | 34 | 28 | 40 | 7 | 3 | 23 | 66 | 16 | 19 | 62 | 59 | 44 | 51 | 43 | 52 | 14/12/12 | 69 |
| CALLER | 58 | 8 | 10 | 0 | 51 | 5 | 35 | 5 | 37 | 29 | 34 | 28 | 32 | 44 | 46 | 6/4/4 | 32 |
| HYPER | 56 | 40 | 25 | 8 | 30 | 60 | 35 | 40 | 24 | 60 | 60 | 59 | 78 | 39 | 45 | 15/7/7 | 52 |

Measured rates (%) as the hero in the FULL field:
| archetype | vpip | pfr | open | openjam | limp | 3bet | fold_to_3bet | 4bet | call_allin | flop_bet | flop_fold_to_bet | turn_fold_to_bet | river_fold_to_bet | wtsd | wsd | 1st/2nd/3rd | hands alive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TIGHT | 15 | 12 | 20 | 7 | 0 | 5 | 76 | 14 | 18 | 72 | 49 | 34 | 43 | 55 | 55 | 11/19/17 | 91 |
| WIDE | 39 | 36 | 45 | 6 | 0 | 39 | 70 | 10 | 14 | 77 | 60 | 43 | 40 | 42 | 52 | 23/12/11 | 82 |
| LIMPSHOVE | 27 | 11 | 10 | 9 | 22 | 13 | 78 | 10 | 16 | 64 | 74 | 44 | 45 | 35 | 53 | 18/14/12 | 79 |
| BAL | 36 | 29 | 41 | 7 | 3 | 23 | 66 | 15 | 18 | 63 | 61 | 43 | 51 | 42 | 51 | 19/10/10 | 74 |
| CALLER | 57 | 8 | 10 | 0 | 51 | 5 | 36 | 5 | 37 | 29 | 35 | 28 | 33 | 46 | 46 | 6/4/4 | 36 |
| HYPER | 58 | 41 | 28 | 9 | 30 | 61 | 36 | 38 | 24 | 60 | 61 | 57 | 76 | 39 | 45 | 18/5/6 | 51 |

Measured rates (%) as the hero in the WIDE field:
| archetype | vpip | pfr | open | openjam | limp | 3bet | fold_to_3bet | 4bet | call_allin | flop_bet | flop_fold_to_bet | turn_fold_to_bet | river_fold_to_bet | wtsd | wsd | 1st/2nd/3rd | hands alive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TIGHT | 15 | 12 | 19 | 8 | 0 | 5 | 75 | 16 | 20 | 71 | 44 | 35 | 47 | 66 | 53 | 5/18/18 | 90 |
| WIDE | 35 | 32 | 40 | 6 | 0 | 38 | 70 | 11 | 20 | 75 | 52 | 43 | 33 | 45 | 52 | 13/12/13 | 80 |
| LIMPSHOVE | 26 | 11 | 9 | 8 | 21 | 15 | 77 | 10 | 19 | 65 | 67 | 43 | 40 | 40 | 53 | 14/18/15 | 86 |
| BAL | 33 | 27 | 38 | 7 | 3 | 24 | 66 | 16 | 23 | 64 | 53 | 42 | 49 | 47 | 50 | 12/12/12 | 77 |
| CALLER | 60 | 9 | 10 | 0 | 51 | 5 | 36 | 5 | 46 | 28 | 30 | 26 | 31 | 44 | 47 | 6/4/3 | 32 |
| HYPER | 53 | 36 | 24 | 8 | 29 | 60 | 35 | 41 | 35 | 60 | 52 | 58 | 77 | 43 | 46 | 21/7/7 | 64 |

Measured rates (%) as the hero in the TIGHT field:
| archetype | vpip | pfr | open | openjam | limp | 3bet | fold_to_3bet | 4bet | call_allin | flop_bet | flop_fold_to_bet | turn_fold_to_bet | river_fold_to_bet | wtsd | wsd | 1st/2nd/3rd | hands alive |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TIGHT | 14 | 12 | 17 | 5 | 0 | 4 | 78 | 14 | 18 | 75 | 40 | 26 | 38 | 71 | 51 | 13/13/12 | 100 |
| WIDE | 37 | 35 | 44 | 5 | 0 | 38 | 71 | 10 | 16 | 76 | 58 | 33 | 34 | 54 | 49 | 27/10/10 | 98 |
| LIMPSHOVE | 26 | 8 | 7 | 5 | 23 | 13 | 86 | 6 | 21 | 72 | 72 | 36 | 40 | 28 | 50 | 13/8/9 | 81 |
| BAL | 35 | 29 | 39 | 6 | 3 | 22 | 66 | 15 | 22 | 63 | 59 | 38 | 49 | 48 | 46 | 17/7/8 | 80 |
| CALLER | 55 | 8 | 10 | 0 | 50 | 5 | 36 | 4 | 47 | 32 | 33 | 25 | 32 | 40 | 44 | 4/2/3 | 41 |
| HYPER | 52 | 33 | 23 | 8 | 30 | 60 | 35 | 39 | 29 | 62 | 56 | 55 | 71 | 32 | 41 | 10/4/5 | 54 |

### Matchup table_bluffy: row = the one differing seat (hero), column = the other 7 seats. Points per table (se).
| hero \ field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | TOP20 | FULL | worst | mean of archetype fields |
|---|---|---|---|---|---|---|---|---|---|---|
| TIGHT | 12.4 (0.16) | 11.3 (0.13) | 15.6 (0.16) | 14.7 (0.15) | 22.1 (0.16) | 21.7 (0.15) | 14.0 (0.15) | 14.1 (0.16) | 11.3 | 16.3 |
| WIDE | 19.0 (0.20) | 12.5 (0.16) | 12.7 (0.16) | 14.4 (0.17) | 15.8 (0.17) | 14.7 (0.15) | 14.5 (0.17) | 17.5 (0.19) | 12.5 | 14.8 |
| LIMPSHOVE | 10.8 (0.16) | 14.4 (0.17) | 12.6 (0.16) | 14.8 (0.17) | 16.2 (0.17) | 19.9 (0.16) | 14.5 (0.17) | 15.0 (0.18) | 10.8 | 14.8 |
| BAL | 12.4 (0.18) | 12.0 (0.16) | 10.3 (0.16) | 12.4 (0.16) | 16.2 (0.17) | 16.1 (0.16) | 12.7 (0.17) | 14.5 (0.18) | 10.3 | 13.2 |
| CALLER | 4.4 (0.12) | 5.6 (0.13) | 7.1 (0.14) | 5.5 (0.13) | 12.3 (0.16) | 10.3 (0.17) | 6.1 (0.13) | 6.2 (0.14) | 4.4 | 7.5 |
| HYPER | 7.2 (0.15) | 13.2 (0.18) | 7.9 (0.15) | 9.5 (0.16) | 9.1 (0.15) | 12.5 (0.16) | 10.4 (0.17) | 11.0 (0.17) | 7.2 | 9.9 |

Best response per field (paired difference of the best over the runner-up, same deals):
- TIGHT: WIDE 19.0 > TIGHT 12.4 > BAL 12.4 > LIMPSHOVE 10.8 > HYPER 7.2 > CALLER 4.4; lead +6.5 ±0.2; gain from deviating from the field's own style: +6.5 ±0.2
- WIDE: LIMPSHOVE 14.4 > HYPER 13.2 > WIDE 12.5 > BAL 12.0 > TIGHT 11.3 > CALLER 5.6; lead +1.1 ±0.2; gain from deviating from the field's own style: +1.9 ±0.2
- LIMPSHOVE: TIGHT 15.6 > WIDE 12.7 > LIMPSHOVE 12.6 > BAL 10.3 > HYPER 7.9 > CALLER 7.1; lead +2.9 ±0.2; gain from deviating from the field's own style: +3.0 ±0.2
- BAL: LIMPSHOVE 14.8 > TIGHT 14.7 > WIDE 14.4 > BAL 12.4 > HYPER 9.5 > CALLER 5.5; lead +0.1 ±0.2; gain from deviating from the field's own style: +2.3 ±0.2
- CALLER: TIGHT 22.1 > LIMPSHOVE 16.2 > BAL 16.2 > WIDE 15.8 > CALLER 12.3 > HYPER 9.1; lead +5.9 ±0.2; gain from deviating from the field's own style: +9.8 ±0.2
- HYPER: TIGHT 21.7 > LIMPSHOVE 19.9 > BAL 16.1 > WIDE 14.7 > HYPER 12.5 > CALLER 10.3; lead +1.8 ±0.2; gain from deviating from the field's own style: +9.2 ±0.2
- TOP20: LIMPSHOVE 14.5 > WIDE 14.5 > TIGHT 14.0 > BAL 12.7 > HYPER 10.4 > CALLER 6.1; lead +0.0 ±0.2
- FULL: WIDE 17.5 > LIMPSHOVE 15.0 > BAL 14.5 > TIGHT 14.1 > HYPER 11.0 > CALLER 6.2; lead +2.5 ±0.2

### Share of the top-20 field replaced by one style (hero points per table; se about 0.17 at 12,000 tables)
| field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | best (paired lead over runner-up) |
|---|---|---|---|---|---|---|---|
| top-20 as is | 14.2 | 14.0 | 15.0 | 12.7 | 5.1 | 11.0 | LIMPSHOVE by +0.9 ±0.2 over TIGHT |
| 25% TIGHT | 13.4 | 14.3 | 13.9 | 11.9 | 4.6 | 10.2 | WIDE by +0.4 ±0.2 over LIMPSHOVE |
| 50% TIGHT | 12.9 | 15.0 | 13.2 | 12.3 | 4.2 | 9.3 | WIDE by +1.8 ±0.2 over LIMPSHOVE |
| 100% TIGHT | 12.5 | 18.2 | 10.8 | 12.2 | 3.2 | 7.2 | WIDE by +5.7 ±0.2 over TIGHT |
| 25% WIDE | 13.2 | 13.0 | 14.6 | 12.4 | 5.1 | 11.7 | LIMPSHOVE by +1.4 ±0.2 over TIGHT |
| 50% WIDE | 12.6 | 13.0 | 14.6 | 12.3 | 5.0 | 12.7 | LIMPSHOVE by +1.6 ±0.2 over WIDE |
| 100% WIDE | 11.6 | 12.5 | 15.1 | 12.1 | 4.9 | 14.2 | LIMPSHOVE by +0.9 ±0.2 over HYPER |
| 25% LIMPSHOVE | 14.3 | 13.1 | 14.5 | 12.1 | 5.2 | 10.1 | LIMPSHOVE by +0.2 ±0.2 over TIGHT |
| 50% LIMPSHOVE | 14.5 | 12.9 | 13.9 | 11.4 | 5.3 | 9.7 | TIGHT by +0.6 ±0.2 over LIMPSHOVE |
| 100% LIMPSHOVE | 14.9 | 11.9 | 12.6 | 10.4 | 5.6 | 8.5 | TIGHT by +2.3 ±0.2 over LIMPSHOVE |
| 25% BAL | 14.4 | 13.9 | 14.9 | 13.0 | 4.9 | 10.3 | LIMPSHOVE by +0.5 ±0.2 over TIGHT |
| 50% BAL | 14.3 | 14.2 | 14.9 | 12.7 | 4.6 | 10.4 | LIMPSHOVE by +0.5 ±0.2 over TIGHT |
| 100% BAL | 15.0 | 14.0 | 15.0 | 12.5 | 4.7 | 10.3 | LIMPSHOVE by +0.1 ±0.2 over TIGHT |
| 25% CALLER | 17.2 | 15.0 | 16.4 | 14.5 | 6.8 | 11.0 | TIGHT by +0.8 ±0.2 over LIMPSHOVE |
| 50% CALLER | 19.7 | 16.4 | 18.3 | 16.2 | 8.9 | 11.1 | TIGHT by +1.5 ±0.2 over LIMPSHOVE |
| 100% CALLER | 23.9 | 16.2 | 18.5 | 17.5 | 12.4 | 11.0 | TIGHT by +5.4 ±0.2 over LIMPSHOVE |

### Aggressive share (half WIDE, half LIMPSHOVE; AGH = half WIDE, half HYPER) of the top-20 field
| field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | best (paired lead over runner-up) |
|---|---|---|---|---|---|---|---|
| 0% | 14.2 | 14.0 | 15.0 | 12.7 | 5.1 | 11.0 | LIMPSHOVE by +0.9 ±0.2 over TIGHT |
| AGG25 | 13.5 | 13.3 | 14.5 | 12.4 | 5.2 | 10.7 | LIMPSHOVE by +1.0 ±0.2 over TIGHT |
| AGG50 | 13.3 | 12.6 | 14.3 | 11.3 | 5.1 | 11.2 | LIMPSHOVE by +1.1 ±0.2 over TIGHT |
| AGG75 | 12.9 | 12.0 | 13.9 | 11.5 | 5.1 | 11.3 | LIMPSHOVE by +1.0 ±0.2 over TIGHT |
| AGG100 | 12.4 | 11.5 | 13.2 | 10.8 | 5.0 | 11.3 | LIMPSHOVE by +0.9 ±0.2 over TIGHT |
| AGH50 | 15.0 | 13.1 | 15.8 | 13.2 | 6.1 | 12.0 | LIMPSHOVE by +0.8 ±0.2 over TIGHT |
| AGH100 | 16.4 | 12.6 | 16.4 | 13.5 | 6.8 | 12.4 | LIMPSHOVE by +0.0 ±0.2 over TIGHT |

### Tight variants: points, and paired difference from the default TIGHT (same deals)
| field | TIGHT | TIGHT_c05 | TIGHT_c2 | TIGHT_c4 | TIGHT_s0 | TIGHT_s05 | TIGHT_s2 | TIGHT_o07 | TIGHT_o15 | best non-tight |
|---|---|---|---|---|---|---|---|---|---|---|
| top-20 | 14.2 | -0.3 ±0.1 | -0.4 ±0.1 | -1.3 ±0.2 | -0.2 ±0.1 | +0.1 ±0.1 | -0.3 ±0.1 | -0.0 ±0.2 | -0.4 ±0.2 | LIMPSHOVE 15.0 |
| AGG25 | 13.5 | -0.1 ±0.1 | -0.4 ±0.1 | -1.1 ±0.2 | -0.0 ±0.1 | +0.2 ±0.1 | -0.1 ±0.1 | +0.4 ±0.2 | -0.2 ±0.2 | LIMPSHOVE 14.5 |
| AGG50 | 13.3 | -0.3 ±0.1 | -0.7 ±0.1 | -1.7 ±0.2 | -0.4 ±0.1 | -0.0 ±0.1 | -0.3 ±0.1 | +0.1 ±0.2 | -0.5 ±0.2 | LIMPSHOVE 14.3 |
| AGG75 | 12.9 | -0.3 ±0.1 | -0.6 ±0.1 | -1.6 ±0.2 | -0.2 ±0.1 | +0.1 ±0.1 | -0.1 ±0.1 | +0.4 ±0.2 | -0.7 ±0.2 | LIMPSHOVE 13.9 |
| AGG100 | 12.4 | -0.2 ±0.1 | -0.9 ±0.1 | -1.8 ±0.2 | -0.1 ±0.1 | +0.2 ±0.1 | -0.3 ±0.1 | +0.4 ±0.2 | -0.7 ±0.2 | LIMPSHOVE 13.2 |
| AGH50 | 15.0 | -0.3 ±0.1 | -0.5 ±0.1 | -1.4 ±0.2 | -0.3 ±0.1 | +0.1 ±0.1 | -0.2 ±0.1 | +0.3 ±0.2 | -0.6 ±0.2 | LIMPSHOVE 15.8 |
| AGH100 | 16.4 | -0.2 ±0.1 | -0.4 ±0.1 | -1.5 ±0.2 | -0.1 ±0.1 | +0.3 ±0.1 | -0.3 ±0.1 | +0.5 ±0.2 | -0.9 ±0.2 | LIMPSHOVE 16.4 |
| 100% WIDE | 11.6 | +0.1 ±0.1 | -0.4 ±0.1 | -1.2 ±0.2 | -0.4 ±0.1 | -0.0 ±0.1 | +0.2 ±0.1 | +0.2 ±0.2 | -0.4 ±0.2 | LIMPSHOVE 15.1 |
| 100% LIMPSHOVE | 14.9 | +0.0 ±0.1 | -1.7 ±0.1 | -3.1 ±0.2 | +0.1 ±0.1 | +0.2 ±0.1 | -0.5 ±0.1 | +0.8 ±0.2 | -1.4 ±0.2 | LIMPSHOVE 12.6 |
| 100% HYPER | 21.3 | -0.1 ±0.1 | -1.0 ±0.2 | -2.8 ±0.2 | +0.3 ±0.1 | +0.2 ±0.1 | -0.4 ±0.1 | +0.9 ±0.2 | -1.3 ±0.2 | LIMPSHOVE 19.3 |

### Share of the top-20 field replaced by one style_bluffy (hero points per table; se about 0.17 at 12,000 tables)
| field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | best (paired lead over runner-up) |
|---|---|---|---|---|---|---|---|
| top-20 as is | 14.0 | 14.5 | 14.5 | 12.7 | 6.1 | 10.4 | LIMPSHOVE by +0.0 ±0.2 over WIDE |
| 50% TIGHT | 12.8 | 15.6 | 12.6 | 12.2 | 5.2 | 9.1 | WIDE by +2.7 ±0.2 over TIGHT |
| 100% TIGHT | 12.4 | 19.0 | 10.8 | 12.4 | 4.4 | 7.2 | WIDE by +6.5 ±0.2 over TIGHT |
| 50% WIDE | 12.4 | 13.5 | 14.4 | 12.1 | 5.8 | 11.8 | LIMPSHOVE by +0.9 ±0.2 over WIDE |
| 100% WIDE | 11.3 | 12.5 | 14.4 | 12.0 | 5.6 | 13.2 | LIMPSHOVE by +1.1 ±0.2 over HYPER |
| 100% LIMPSHOVE | 15.6 | 12.7 | 12.6 | 10.3 | 7.1 | 7.9 | TIGHT by +2.9 ±0.2 over WIDE |
| 100% BAL | 14.7 | 14.4 | 14.8 | 12.4 | 5.5 | 9.5 | LIMPSHOVE by +0.1 ±0.2 over TIGHT |
| 100% CALLER | 22.1 | 15.8 | 16.2 | 16.2 | 12.3 | 9.1 | TIGHT by +5.9 ±0.2 over LIMPSHOVE |

### Aggressive share (half WIDE, half LIMPSHOVE; AGH = half WIDE, half HYPER) of the top-20 field
| field | TIGHT | WIDE | LIMPSHOVE | BAL | CALLER | HYPER | best (paired lead over runner-up) |
|---|---|---|---|---|---|---|---|
| 0% | 14.0 | 14.5 | 14.5 | 12.7 | 6.1 | 10.4 | LIMPSHOVE by +0.0 ±0.2 over WIDE |
| AGG50 | 13.3 | 13.0 | 14.0 | 11.6 | 6.3 | 10.5 | LIMPSHOVE by +0.7 ±0.2 over TIGHT |
| AGG100 | 12.2 | 11.9 | 13.0 | 10.9 | 6.1 | 10.7 | LIMPSHOVE by +0.9 ±0.2 over TIGHT |

### Fields mixed from the three main styles (quarters of the 7 opponents' seats on average; 8,000 tables, se about 0.2)
| field: tight/wide/limp-shove | TIGHT | WIDE | LIMPSHOVE | BAL | best (paired lead) |
|---|---|---|---|---|---|
| 0/25/75 | 13.7 | 11.5 | 13.2 | 10.6 | TIGHT by +0.6 ±0.3 over LIMPSHOVE |
| 0/50/50 | 12.4 | 11.4 | 13.2 | 10.7 | LIMPSHOVE by +0.8 ±0.3 over TIGHT |
| 0/75/25 | 11.8 | 11.8 | 14.3 | 11.4 | LIMPSHOVE by +2.5 ±0.3 over WIDE |
| 25/0/75 | 14.2 | 12.5 | 11.6 | 10.4 | TIGHT by +1.7 ±0.3 over WIDE |
| 25/25/50 | 12.5 | 12.5 | 12.3 | 10.5 | TIGHT by +0.0 ±0.3 over WIDE |
| 25/50/25 | 12.0 | 12.7 | 13.2 | 11.0 | LIMPSHOVE by +0.5 ±0.3 over WIDE |
| 25/75/0 | 11.4 | 13.2 | 13.7 | 11.8 | LIMPSHOVE by +0.5 ±0.3 over WIDE |
| 50/0/50 | 13.5 | 13.9 | 11.1 | 10.7 | WIDE by +0.4 ±0.3 over TIGHT |
| 50/25/25 | 12.3 | 13.8 | 12.2 | 11.5 | WIDE by +1.4 ±0.3 over TIGHT |
| 50/50/0 | 10.9 | 13.9 | 13.0 | 12.0 | WIDE by +1.0 ±0.3 over LIMPSHOVE |
| 75/0/25 | 13.0 | 15.5 | 11.1 | 11.1 | WIDE by +2.5 ±0.3 over TIGHT |
| 75/25/0 | 11.7 | 15.5 | 12.1 | 11.8 | WIDE by +3.4 ±0.3 over LIMPSHOVE |

### Seed check (fresh deals, seed m2) and clone setting
| row | setting | TIGHT | WIDE | LIMPSHOVE | BAL | HYPER |
|---|---|---|---|---|---|---|
| top-20, seed m1 | standard | 14.2 | 14.0 | 15.0 | 12.7 | 11.0 |
| top-20, seed m1 | bluffy | 14.0 | 14.5 | 14.5 | 12.7 | 10.4 |
| top-20, seed m2 | standard | 14.2 | 13.9 | 14.6 | 12.8 | 10.8 |
| top-20, seed m2 | bluffy | 14.1 | 14.4 | 14.5 | 12.7 | 10.7 |
| 50% WIDE, seed m1 | standard | 12.6 | 13.0 | 14.6 | 12.3 | 12.7 |
| 50% WIDE, seed m1 | bluffy | 12.4 | 13.5 | 14.4 | 12.1 | 11.8 |
| 50% WIDE, seed m2 | standard | 12.7 | 12.7 | 14.4 | 12.3 | 12.3 |
| 50% WIDE, seed m2 | bluffy | 12.0 | 13.0 | 14.2 | 11.9 | 11.6 |

### Drift: archetypes and field both from round 1 (top-20 only)
| | TIGHT | WIDE | LIMPSHOVE | BAL | HYPER |
|---|---|---|---|---|---|
| r1 | 14.0 | 14.0 | 12.5 | 12.5 | 12.6 |
| r6 | 14.2 | 14.0 | 15.0 | 12.7 | 11.0 |

### Tight variants under the bluffy setting: paired difference from default TIGHT
| field | TIGHT | TIGHT_c2 | TIGHT_c4 | TIGHT_s0 | TIGHT_o07 |
|---|---|---|---|---|---|
| top-20 | 14.0 | -0.5 ±0.1 | -1.6 ±0.2 | -0.1 ±0.1 | +0.0 ±0.2 |
| 100% WIDE | 11.3 | -0.5 ±0.1 | -1.1 ±0.2 | -0.3 ±0.1 | +0.2 ±0.2 |
| 100% LIMPSHOVE | 15.6 | -1.7 ±0.2 | -3.0 ±0.2 | -0.1 ±0.1 | +0.7 ±0.2 |
| 100% HYPER | 21.7 | -1.2 ±0.2 | -3.2 ±0.2 | +0.2 ±0.1 | +1.0 ±0.2 |

### Our real bots (kit code) as the hero; points (se); paired differences on the same deals
| field | v10 | v6 | v3b | v10 - v6 | v10 - v3b |
|---|---|---|---|---|---|
| r6 FULL | 17.9 (0.33) | 18.2 (0.33) | 15.9 (0.32) | -0.3 ±0.3 | +2.0 ±0.3 |
| r6 TOP20 | 14.1 (0.28) | 14.3 (0.29) | 13.2 (0.28) | -0.2 ±0.3 | +0.9 ±0.3 |
| r1 FULL | 20.7 (0.34) | 20.3 (0.34) | 17.7 (0.34) | +0.5 ±0.3 | +3.0 ±0.4 |
| r1 TOP20 | 18.9 (0.32) | 18.6 (0.32) | 15.5 (0.31) | +0.3 ±0.3 | +3.4 ±0.3 |

failed decisions (timeouts under local load): v10 r6 FULL: 43, v6 r6 FULL: 0, v3b r6 FULL: 23, v10 r6 TOP20: 21, v6 r6 TOP20: 6, v3b r6 TOP20: 0, v10 r1 FULL: 0, v6 r1 FULL: 1, v3b r1 FULL: 0, v10 r1 TOP20: 48, v6 r1 TOP20: 0, v3b r1 TOP20: 0

### Real v10 and v6 against the archetype skeletons in pure fields (3,000 tables; paired difference to the best skeleton on the same deals)
| field | v10 | v6 | best skeleton | v10 - best skeleton | v10 - field's own style |
|---|---|---|---|---|---|
| TIGHT | 13.7 (0.35) | 13.6 | WIDE 18.2 | -4.7 ±0.5 | +1.0 ±0.5 |
| WIDE | 13.2 (0.33) | 13.1 | LIMPSHOVE 15.1 | -1.8 ±0.5 | +0.4 ±0.5 |
| LIMPSHOVE | 15.6 (0.31) | 15.8 | TIGHT 14.9 | +0.7 ±0.4 | +3.0 ±0.4 |
| BAL | 14.0 (0.32) | 13.8 | LIMPSHOVE 15.0 | -0.7 ±0.5 | +1.8 ±0.4 |
| CALLER | 29.5 (0.34) | 27.9 | TIGHT 23.9 | +6.0 ±0.4 | +17.0 ±0.5 |
| HYPER | 17.1 (0.28) | 17.0 | TIGHT 21.3 | -4.2 ±0.4 | +4.5 ±0.4 |
| TOP20 | 14.1 (0.28) | 14.3 | LIMPSHOVE 15.0 | -1.5 ±0.4 | +nan ±0.0 |

v10 measured rates (%): | field | vpip | pfr | 3bet | fold_to_3bet | call_allin | flop_fold_to_bet | turn_fold_to_bet | river_fold_to_bet | wtsd | wsd | 1st/2nd/3rd |
| TOP20 | 30 | 22 | 18 | 89 | 14 | 72 | 67 | 78 | 35 | 50 | 13/15/15 |
| FULL | 31 | 23 | 17 | 88 | 16 | 72 | 63 | 74 | 37 | 51 | 23/12/13 |
| WIDE | 32 | 24 | 28 | 90 | 18 | 75 | 69 | 80 | 44 | 48 | 14/12/14 |
| TIGHT | 28 | 23 | 13 | 90 | 22 | 71 | 55 | 83 | 48 | 48 | 17/9/11 |
| LIMPSHOVE | 27 | 26 | 23 | 93 | 12 | 74 | 68 | 79 | 20 | 53 | 12/19/21 |

### r6: top-20 only vs full field (clone scores; real = that round's real score at our tables, se ~0.6)
| team | real | sim full | sim top-20 | change | VPIP | PFR | 3-bet | fold to 3-bet | open-jam | limp | call all-in | flop fold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| thepastaway | 20.3 | 11.7 | 11.0 | -0.7 ±0.3 | 57 | 41 | 60 | 38 | 9 | 30 | 31 | 57 |
| Lemonade | 19.2 | 15.7 | 14.9 | -0.8 ±0.3 | 25 | 10 | 13 | 81 | 7 | 22 | 19 | 73 |
| Chikerbot | 16.6 | 15.8 | 14.7 | -1.0 ±0.3 | 32 | 31 | 21 | 59 | 3 | 0 | 25 | 43 |
| Gavilan | 16.8 | 15.1 | 14.0 | -1.1 ±0.3 | 27 | 21 | 18 | 47 | 7 | 0 | 21 | 77 |
| Team 123 | 18.3 | 11.8 | 10.5 | -1.3 ±0.3 | 43 | 35 | 41 | 33 | 2 | 1 | 27 | 39 |
| Foldemort | 14.9 | 14.1 | 12.4 | -1.7 ±0.3 | 31 | 27 | 14 | 80 | 10 | 0 | 19 | 62 |
| one in a krillion | 14.7 | 15.6 | 13.7 | -1.9 ±0.3 | 26 | 21 | 7 | 45 | 5 | 0 | 21 | 67 |
| nik airball | 15.1 | 15.1 | 13.0 | -2.0 ±0.3 | 30 | 28 | 16 | 72 | 11 | 0 | 24 | 61 |
| Golden Knight | 15.2 | 15.3 | 13.2 | -2.1 ±0.3 | 29 | 26 | 18 | 85 | 6 | 0 | 19 | 46 |
| Always Folds | 15.8 | 13.7 | 11.6 | -2.2 ±0.3 | 38 | 30 | 34 | 76 | 8 | 0 | 15 | 46 |
| Team 72 | 16.5 | 16.3 | 14.0 | -2.4 ±0.3 | 36 | 32 | 26 | 42 | 3 | 0 | 23 | 61 |
| Curious George | 16.5 | 13.9 | 11.4 | -2.5 ±0.3 | 35 | 29 | 14 | 73 | 10 | 0 | 18 | 54 |
| avalon | 17.5 | 14.0 | 11.5 | -2.5 ±0.3 | 31 | 23 | 17 | 89 | 6 | 0 | 16 | 69 |
| AZ | 15.6 | 14.2 | 11.6 | -2.6 ±0.3 | 32 | 28 | 20 | 72 | 6 | 0 | 17 | 62 |
| 2 Curry | 18.7 | 16.6 | 13.9 | -2.7 ±0.3 | 38 | 35 | 39 | 73 | 6 | 0 | 15 | 61 |
| sandylikesfrogs | 15.2 | 13.6 | 10.8 | -2.8 ±0.3 | 41 | 32 | 14 | 72 | 7 | 7 | 22 | 67 |
| TeamBallHog | 14.6 | 13.7 | 10.8 | -2.9 ±0.3 | 35 | 28 | 8 | 62 | 11 | 1 | 10 | 70 |
| Team 82 | 17.9 | 15.6 | 12.4 | -3.2 ±0.3 | 31 | 26 | 17 | 77 | 8 | 0 | 11 | 48 |
| pocket rockets | 17.3 | 16.7 | 13.4 | -3.2 ±0.3 | 36 | 34 | 28 | 74 | 2 | 1 | 19 | 53 |
| stanford deviants | 14.3 | 14.3 | 11.0 | -3.4 ±0.3 | 40 | 37 | 44 | 95 | 9 | 2 | 13 | 64 |

corr(real, sim full) = -0.09; rank order sim top20: Lemonade 14.9, Chikerbot 14.7, Team 72 14.0, Gavilan 14.0, 2 Curry 13.9, one in a krillion 13.7, pocket rockets 13.4, Golden Knight 13.2, nik airball 13.0, Foldemort 12.4, Team 82 12.4, AZ 11.6, Always Folds 11.6, avalon 11.5, Curious George 11.4, thepastaway 11.0, stanford deviants 11.0, sandylikesfrogs 10.8, TeamBallHog 10.8, Team 123 10.5
correlation of the change with style: vpip +0.04, pfr -0.26, 3bet +0.14, fold_to_3bet -0.53, fold_to_open -0.27, openjam -0.05, limp +0.53, call_allin +0.71, flop_bet +0.37, flop_fold_to_bet -0.03, turn_fold_to_bet -0.29, river_fold_to_bet +0.05, wtsd -0.09, wsd -0.30
corr(sim full, sim top20) = 0.83; sd full 1.36, sd top20 1.38

### r1: top-20 only vs full field (clone scores; real = that round's real score at our tables, se ~0.6)
| team | real | sim full | sim top-20 | change | VPIP | PFR | 3-bet | fold to 3-bet | open-jam | limp | call all-in | flop fold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lemonade | 20.0 | 13.1 | 13.2 | +0.1 ±0.3 | 28 | 16 | 22 | 67 | 11 | 24 | 22 | 68 |
| Team 123 | 9.4 | 10.4 | 10.2 | -0.2 ±0.2 | 14 | 10 | 4 | 35 | 2 | 2 | 10 | 17 |
| avalon | 18.1 | 11.7 | 11.4 | -0.3 ±0.3 | 30 | 23 | 16 | 87 | 7 | 0 | 24 | 32 |
| Gavilan | 18.0 | 13.5 | 12.7 | -0.9 ±0.3 | 32 | 22 | 13 | 43 | 8 | 0 | 34 | 80 |
| stanford deviants | 15.5 | 15.6 | 14.5 | -1.0 ±0.3 | 32 | 28 | 15 | 41 | 7 | 3 | 11 | 64 |
| Foldemort | 13.3 | 13.0 | 11.9 | -1.1 ±0.3 | 29 | 22 | 12 | 68 | 5 | 0 | 25 | 32 |
| sandylikesfrogs | 18.9 | 10.9 | 9.7 | -1.2 ±0.3 | 50 | 36 | 15 | 44 | 9 | 11 | 39 | 59 |
| Team 82 | 18.0 | 14.1 | 12.8 | -1.3 ±0.3 | 23 | 19 | 3 | 69 | 5 | 0 | 14 | 41 |
| AZ | 20.0 | 14.7 | 13.3 | -1.5 ±0.3 | 30 | 26 | 14 | 63 | 7 | 1 | 30 | 61 |
| Chikerbot | 12.6 | 12.2 | 10.7 | -1.5 ±0.2 | 22 | 18 | 4 | 63 | 4 | 0 | 16 | 26 |
| one in a krillion | 15.8 | 15.6 | 14.1 | -1.5 ±0.3 | 27 | 22 | 4 | 45 | 5 | 0 | 24 | 67 |
| thepastaway | 15.0 | 14.3 | 12.7 | -1.7 ±0.3 | 26 | 17 | 5 | 47 | 3 | 11 | 18 | 47 |
| pocket rockets | 16.8 | 14.5 | 12.7 | -1.8 ±0.3 | 40 | 23 | 10 | 61 | 2 | 25 | 24 | 55 |
| Curious George | 15.0 | 14.9 | 13.0 | -1.8 ±0.3 | 25 | 19 | 4 | 82 | 7 | 1 | 23 | 26 |
| Golden Knight | 15.1 | 16.8 | 14.9 | -1.8 ±0.3 | 25 | 23 | 8 | 82 | 10 | 0 | 15 | 67 |
| TeamBallHog | 20.4 | 14.1 | 12.2 | -1.9 ±0.3 | 39 | 31 | 8 | 58 | 12 | 1 | 16 | 68 |
| nik airball | 11.2 | 12.3 | 10.4 | -2.0 ±0.2 | 34 | 22 | 3 | 31 | 4 | 8 | 11 | 60 |
| 2 Curry | 18.1 | 16.0 | 13.7 | -2.3 ±0.3 | 43 | 41 | 34 | 84 | 7 | 0 | 17 | 62 |
| Team 72 | 19.4 | 16.1 | 13.4 | -2.7 ±0.3 | 34 | 27 | 3 | 52 | 3 | 0 | 28 | 64 |
| Always Folds | 17.1 | 14.9 | 12.2 | -2.7 ±0.3 | 33 | 26 | 5 | 58 | 8 | 0 | 8 | 41 |

corr(real, sim full) = 0.33; rank order sim top20: Golden Knight 14.9, stanford deviants 14.5, one in a krillion 14.1, 2 Curry 13.7, Team 72 13.4, AZ 13.3, Lemonade 13.2, Curious George 13.0, Team 82 12.8, pocket rockets 12.7, Gavilan 12.7, thepastaway 12.7, Always Folds 12.2, TeamBallHog 12.2, Foldemort 11.9, avalon 11.4, Chikerbot 10.7, nik airball 10.4, Team 123 10.2, sandylikesfrogs 9.7
correlation of the change with style: vpip -0.36, pfr -0.46, 3bet +0.24, fold_to_3bet -0.05, fold_to_open -0.14, openjam +0.10, limp +0.25, call_allin +0.18, flop_bet +0.15, flop_fold_to_bet -0.17, turn_fold_to_bet -0.45, river_fold_to_bet -0.32, wtsd +0.50, wsd -0.60
corr(sim full, sim top20) = 0.91; sd full 1.72, sd top20 1.39
