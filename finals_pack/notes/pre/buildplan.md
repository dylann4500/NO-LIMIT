# The first-hour build plan (pre-event note, topic C, for `platform`)

> **Case label (14 November, evening).** Written for case R: 8 seats, 2,000 chips, no ante. The team's main case is
> now case F (6 seats, 6,000 chips, antes): `CLAUDE.md` §8 has the two side by side and `notes/pre/format_finals.md`
> what changes. Section 6 here says what to redo.

Drafted Saturday 14 November for Sunday's `platform` to check and extend. Notes only, no bot code; algorithms are in words.

**Grades** (as `strategy/EVIDENCE_TABLE.md`): **A** measured fact (a test build's time is A as a measurement, C as a forecast for Sunday); **B** a change measured on full-table results; **C** candidate; **D** withdrawn; **arith.** exact arithmetic. Hold'em-only parts are marked "(hold'em)" and listed in section 6.

## What `platform` does in its first 15 minutes because of this note

1. **Minutes 0-5: the team Python, the variant, the rules card.** Play one table with the variant named explicitly: the local engine defaulted to plain hold'em at the regional and in the speedrun (A). Announce the Python's path.
2. **Minutes 3-10: v1.** The new phase's legal default before any betting code, inside the shell, imported from an empty folder, through the no-time-bank test with check-or-fold in the same minute. Four timed builds did it in 1-3 minutes (A).
3. **Minute 6: the interface stub**, before the code behind it works. Without one, three stylists idled 6 minutes (A).
4. **Minutes 6-10: the two checks every build needed**: positions against the engine's blind events at 2, 3 and full table, and tournament equity with a seat busted this hand (section 5, rows 1 and 5).
5. **Minutes 9-15: the harness and a packer that fails loudly.**

Not in the hour: team recognition, showdown replay, tuning against sparring bots. No timed build finished them (A, 3 of 3).

## 1. Order of work, checked against the speedrun

| Minute | Work | Target (`platform.md`) | Speedrun | Reading |
|---|---|---|---|---|
| 0-5 | Team Python; variant plays; rules card | 5 | card at 2 | Two agents built their own Python |
| 3-10 | v1 released, upload-tested | 10 | 3 | Slack: spend it on the checks |
| 6 | Interface stub | 6 | none; full interface at 10 | The slot it missed |
| 6-10 | Position and bust-payout checks | minute 0 | blind swap fixed at 16, ICM zero at 14 | Other agents found both |
| 9-15 | Harness, upload test, loud packer; shared platform, full interface | 12-15 | 9-11 | On time; five silent failures came first |
| 10-20 | Theory's tables in, each behind a setting | 20 | landed 5-12, in at 14 | A missing key silently kept the old table |
| 12-17 | Styles and D legal, rebuilt after each fix | 20 | 10-17 | Rebuilds took 1-2 minutes |
| 15-25 | A review loop per release | habit | 7 releases, 3 loops by 25 | The most productive habit |
| 17-50 | Each practice pick packed fresh, tested 3 minutes before; refits and priors in; round-1 bot at 50 | each practice | not exercised | No portal, uploads or cooldown |

The speedrun ended at minute 26, without humans, at load 34-51 on 12 cores: its times are a floor (C for Sunday). At the regional the hour's last build scored 9.17 against 19.02 for the one before (A): the last 15 minutes are for practice picks, not a new design.

## 2. The safety shell and the three layers

The shell: a final step that makes any intended action legal, the new phase answered before any betting logic, a catch-all that counts, memory parsed defensively. The layers: platform, variant engine, strategy (`platform.md` has the detail). What test builds got wrong:

- **The harness must read the catch-all's count**: the kit's runner cannot show it (A).
- **Styles wrap the platform, never copy it**: a copied function missed two later fixes (A).
- **The current hand is rebuilt from the state's history every call.** Kept in memory, a cut memory made a raised pot read as unopened 16 times in 5,000 fuzzed decisions (A).
- **Randomness is seeded from table, hand, seat and history length.** Clock-seeded builds varied ±0.5 points a table on identical deals (A).

## 3. What to build at import, and the equity estimate

**At import**: card objects and indexes; theory's tables as literals in the one file; one throwaway decision of every phase; then one collection, freeze, raised thresholds. A table in a separate file got an upload rejected; embedded, the regional file was 110-150 KB of a 1 MB limit and imported in 45-90 ms (A). Collector pauses of 2.6-7 ms were the over-limit decisions; frozen, the slowest was 0.3 ms (A). Nothing is simulated at import.

**An equity estimate inside about 0.3 ms, worst case:**

| Case | Method, in words | Cost | Noise | Grade |
|---|---|---|---|---|
| Before the flop | Lookup: hand class to equity against the top-w range, simulated against opponents who use the twist | microseconds | the table's | A |
| After the flop, two hole cards, normal board (hold'em) | The evaluator library's compiled hand-against-range sampler; the range narrowed by the seat's actions | 30 µs per 300 trials per opponent | 3 points | A, one Mac |
| After the flop, anything else | A sampling loop over the evaluator; known cards in their seats, dead cards out | 110 samples in 160 µs; 35 per option when two twist options share 220 µs | 4.5 points; 8 | A, mock builds |
| Few unknowns (an exposed card) | Enumerate the opponent's holdings, about 45 | below sampling | none | C |

- **Cap by iteration count; keep the 0.15-0.2 ms deadline as a counted backstop** that never binds on an idle core. Memory and events cost a fixed 70 µs a decision in one build (A).
- **Noise exceeds margins**: 4.5 points against calling margins of 3 (A). Score twist options on the same deals, interleaved; scored in turn, the second got 4 samples to the first's 35 (A).
- **Several opponents**: samples divide by opponents. Time the full table.
- **ICM is not free**: a full-table calculation took 0.3 ms, three per all-in 0.9 ms (A). Compute our own share only, or read theory's thresholds.
- **Target**: regional bots ran p99 150-170 µs and maximum 0.56-0.84 ms on an idle laptop; the 0.83 ms one failed a decision on the organizers' slower box (A). Clean-run maximum under 0.5 ms.

## 4. Per-seat estimates with priors

- **Estimate = (times done + 4 x prior) / (chances + 4)**, counts in memory from hand 1 (456-668 bytes at the regional: A). A weight-4 prior from the other regional's variant cut per-seat error by a third in the first 1-8 chances; weight 10 on a stale prior hurt (A).
- **The prior carries the rare spots**: per table a seat gives a median of 1 chance to fold to a 3-bet, 3 to a flop bet, 1 on the turn, 0 on the river (A).
- **Priors until the first download** (A, both regionals): fold to a 3-bet 67%; open-shove 41% at 10bb or less, 22-24% at 10-15bb, 10-12.5% at 15-20bb; call a shove 20%; fold to a flop bet 53%; raise before the flop 22%.

## 5. The checks that catch the bugs that sank bots

| # | Bug | Cost | Check |
|---|---|---|---|
| 1 | A library ICM function scores a busted seat 0 though its place pays | A 45% call read as 86-88%; two rounds; about 1.4 weighted points (A; cost modelled). Design D shipped it again in the speedrun and folded every hand three-handed (A) | A busted seat gets its place's payout; shares sum to the pool. At equal stacks the bug reads 77% three-handed, 80% heads-up (arith.). Also for any candidate with its own function |
| 2 | The wrapper around a correct ICM | Pot counted twice, unmatched chips credited: calls too wide (A, two builds) | Heads-up break-even equals pot odds; 8 equal stacks 56%, 3 equal 57%, 4 equal 62-65% at 50/30/20 (arith.) |
| 3 | Flop over-calling | Folded 33% to flop bets against the leaders' 61%; 4-7 weighted points; fix +2.3 a table (B) | Equity falls clearly from check to bet to raise; count one-pair calls of raises; fold-to-bet by street beside the field's 52/45/48%, flagged high too: the fix overshot to 73/66/78% (A) |
| 4 | Silent fallbacks | Five in 20 minutes, each switching a feature off (A) | Unknown settings fail the pack; a table with wrong keys raises; the packer prints what it drops and the zip's hash; every branch reports its count |
| 5 | Position at 2-3 players | Heads-up blind swap in 444 of 444 decisions (A, three builds) | Button and blinds against the engine's blind events at 2, 3 and full table, and after a bust |
| 6 | Loaded CPU | The kit's do-nothing bot failed timing tests as often as ours (A, four builds) | A timing test counts only with load below the core count and check-or-fold in the same minute |
| 7 | The upload test: no time bank, never reaches the twist | The kit's runner has no bank switch; check-or-fold folds before the new phase (A) | Own harness: 2 players, 20 hands, bank 0, several seeds; then against a call-everything bot, counting twist phases |
| 8 | Counters and cards | Folds to our raise never counted; a passed card left in the deck (A) | A scripted sequence per statistic, also with memory cut mid-hand; the deck partition totals 52 |

## 6. If the format is not the one assumed

- **Not 8-handed**: every "8" above becomes today's table size; time sampling and ICM at the full table; keep opening counts per number of players left, or heads-up raising reads as tight (C).
- **Other payouts**: the 56 / 57 / 62-65% values are 50/30/20 only; other shapes are in `whatwins.md`, section 4.
- **Another time limit**: every deadline above is a share of 1 ms.
- **Hold'em-only**: the compiled sampler, the 169 hand classes (1,755 with three hole cards), 7-card evaluation, positions set by a button and two blinds. If one fails today, use the "anything else" row and say so in the first report.

## Sources

Team archive (paths from the repo root):
- `finals_pack/.claude/agents/platform.md`, `finals_pack/strategy/FIRST_PROMPT.md` Parts 1 and 6, `TWIST_NOTES.md` sections 2-3, `LESSONS.md`, `EVIDENCE_TABLE.md` (cross-regional priors, the shrinkage test).
- `finals_pack/prep/SPEEDRUN_14NOV.md` (every "speedrun" time, the silent fallbacks, the blind swap, design D's ICM).
- `research/finals_prep/buildtest/flop_pass_holdem.md`, `turn_draw_holdem.md`, `flop_auction_holdem_v2.md` (timed builds: milestones, sample counts, latencies under load, most bugs in section 5).
- `rebuild/01_RULES.md` (the regional kit's limits), `rebuild/02_ARCHITECTURE.md` (the compiled sampler's speed, collector pauses, the slower build box), `rebuild/05_TESTS.md`.
- `docs/BUILDLOG.md`, `docs/STEERING.md` (regional latencies, file sizes, the rejected upload, the box failure, the ICM defect); `docs/writeup/avalon-writeup.tex` (the defect's cost, the over-calling leak).

Computed for this note (scratch arithmetic outside the repo): the bust-scored-zero readings in section 5, row 1.

Not verified here: the compiled sampler was timed once, on one Mac, before the regional; whether today's kit ships that library is a minute-0 fact.
