## Report: clean-room build-hour test of part1_v2.md on flop_auction_holdem

The prompt held up. A legal bot existed at 1.3 minutes, and all three styles were built and checked by minute 21. Every milestone was met except twist value, which landed at 25 minutes instead of 20. The two most useful instructions were "value the twist by enumeration on shared deals" and "check what a failed decision costs". Using the auction well is worth about 8 points per table, from 11–14.5 for a bot that never bids to 19–22. The worst bug came from me, not from a check: acting on a subagent's "harmless line" comment broke the street counter for 11 minutes, and no scripted check or field run noticed.

Everything is in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/buildtest/flop_auction_holdem/`:
- `platform_core.py` is the shared platform.
- `styles/A.py`, `work_B/B.py` and `work_C/C.py` are the three style layers.
- `build.py` joins the platform and a style into `submission/{A,B,C,minimal}/agent.py`.
- `tools/harness.py`, `tools/checks.py`, `tools/fuzz.py` and `tools/sim_preflop.py` are the test tools; `sparring/` holds the practice bots.
- `NOTES.md` has the version log.

### Timeline (start 16:56:06)
| Time | Elapsed | Milestone | Target |
|---|---|---|---|
| 16:57:21 | 1.3 min | Minimal legal bot: bids zero, check or fold, safety shell. Passed the kit's check and a 20-table play with 0 failed decisions. | 10 min |
| 17:00:16 | 4 min | Auction-aware preflop ranking for all 169 hand classes, plus equity against top 5–65% ranges, embedded in the bot. Took 1 minute on 4 cores. | 20 min |
| 17:03:52 | 8 min | Platform, style A and the in-process harness. Upload-test conditions gave 0 failures. | 15 min |
| 17:04:30 | 8.5 min | Subagents for styles B and C launched; they reported back at about 17:14–17:16. | — |
| 17:17 | 21 min | v2: fixed the subagents' platform bugs. Checks for tournament equity, counters and equity-vs-action ran; the equity check caught a bug. Fuzzed 30,000 states. | — |
| 17:21 | 25 min | Twist value measured (results below). | 20 min (late) |
| 17:22 / 17:28 / 17:31 | — | Versions v3, v4 and v5 (see Build state). | — |
| ~17:37 | 41 min | Stopped building. Round robin and the 100,000-state fuzz were done by 17:36. | 60 min |

### Build state at the stop
**Platform:**
- Safety shell: one final function that makes any action legal, including bids. A catch-all counts every time it fires, stored in memory.
- Memory is JSON with defensive parsing. Per-seat counters start from a prior and are updated from complete hands only. The current hand is rebuilt from `state.history` on every call.
- Tournament equity uses my own calculation, because the kit's function gives a busted player 0.
- Equity is computed against narrowed ranges. The auction step scores all 10 possible flops on the same sampled opponent hands and turn/river cards, then bids on the best flop's cards. Bid sizes come from a budget: balance divided by the auctions expected to remain, scaled by how much the flops differ and by pot size.

**Versions after v1:**
- v3 (17:22) caps bids at 1.2 times the richest live opponent's flop-chips.
- v4 (17:28) fixed my street-counter bug (described below) and counts fold-to-re-raise once per hand.
- v5 (17:31) gives the auction 0.5 ms while the time bank is at least 60 ms, and 0.25 ms otherwise. This is safe because a failed bid only bids zero; it never folds.

**What preflop looks like under the auction:** pocket pairs lose a lot of value (22 ranks 118th of 169, 77 ranks 31st) and high cards gain (K2o ranks 84th). Controlling which flop comes is worth about 5–10 points of equity heads-up.

**The three styles:**
- **A (pressure):** wide opens and re-raises.
- **B (shove-heavy):** shove or fold up to about 25 big blinds; re-shoves sized by the raiser's fold-to-re-raise rate.
- **C (tight):** a separate parameter set for each number of players left; spends harder in the auction.

### Evaluation numbers
**Kit check and empty-folder test:** `poker-agent check` passes for A, B, C and minimal. The packed zip imports from an empty folder with `python -I`, and the bot opens no files.

**Upload test** (heads-up against check-or-fold, 20 hands, time bank 0, 3 seeds × 10 tables): 0 failed decisions for every bot.

| Bot | Max decision time | Median | check-or-fold max, same run |
|---|---|---|---|
| A, B, C | 0.07–0.11 ms | ~0.05 ms | ~0.005 ms |

This test never reaches an auction or a flop: check-or-fold folds to every open. It cannot catch a twist failure.

**100,000 fuzzed states** (from real play: 15.5k auctions, 44k heads-up, 28k three-handed, 5.5k with an all-in seat; memory was real, cut in half, garbage, or empty in rotation):
- 0 illegal actions, 0 exceptions, 0 catch-all hits.

| Bot | Median | p99.9 | Max | Decisions over 1 ms |
|---|---|---|---|---|
| A | 0.17 ms | 0.63 ms | 3.7 ms | 3 |
| B | 0.17 ms | 0.63 ms | 0.95 ms | 0 |
| C | 0.17 ms | 0.63 ms | 12.8 ms | 5 |
| check-or-fold | 0.002 ms | — | 0.12 ms | 0 |

- On the 4-worker harness (machine load about 16), about 0.5% of our decisions went over 1 ms, against about 0.01% for check-or-fold. Testing GC settings ruled out garbage collection; it is the process being paused mid-call. With the 100 ms bank this caused 0 failures in thousands of tables.

**Tournament-equity check:**
- Break-even equity to call an all-in: heads-up 0.500, equal to pot odds; 8 equal stacks 0.556; 3 equal 0.571; 4 equal 0.652.
- A busted player gets exactly their place's payout (20 for 3rd, 0 for 4th), and shares add up to 100.

**Counter checks:** a seat that folds to our bet 3 times records 3 of 3. A seat that never opens in 10 chances drops to 0.094 against a 0.25 prior. All rates lie between 0 and 1.

**Equity falls as the opponent's action strengthens** (top pair, good kicker): 0.90 against no action, 0.78 against a bet, 0.65 against a raise, after the fix described below.

**Twist value** (8-player field, 600 tables, SE about 0.85, points per table):

| Auction setting | Points |
|---|---|
| Never bid | 14.5 |
| Cheap rule: best flop by current made hand | 17.7 |
| Simulated bidding, half budget | 20.6 |
| Simulated bidding, normal budget | 22.1 |
| Simulated bidding, 1.5× budget | 20.6 |
| Simulated bidding, 3× budget | 18.8 |

- Auction thinking time (800 tables, SE about 0.75): 0.1 ms → 18.6, 0.25 ms → 19.7, 0.6 ms → 20.4.
- The three switchable adaptive settings showed nothing beyond noise: reading opponents' flop-chip payments, adjusting for bluff rates, and the bid cap.

**Round robin** (1,200 tables; 10 bots rotating through 8 seats; SE about 0.65):

| Bot | Points per table |
|---|---|
| B | 20.1 |
| A | 19.4 |
| C | 18.2 |
| Cheap-rule A | 14.7 |
| premium (sparring) | 12.7 |
| Never-bid A | 11.2 |
| randbid (sparring) | 10.1 |
| shover (sparring) | 9.4 |
| check-or-fold (kit) | 8.5 |
| min-raiser (kit) | 0.7 |

- Our bots had 0 failures. The premium sparring bot had 9, from timeouts under load.
- Suggested order: B for scored round 1, A as the challenger. A and B are within noise of each other.

### Bug hunt (every bug found)
1. **My own, and it got past every check.** At 17:17 I deleted `c.street += 1 if c.street else 1` in the current-hand rebuild because C's report called it a no-op. It was the street counter. From 17:17 to 17:28, raises and calls after the flop were counted as preflop: the list of preflop raisers, preflop callers, and "we raised preflop". Field scores showed no anomaly; I found it by reading the code cold. Fixed, and there is now a scripted rebuild test with turn events. The twist-value numbers were measured on that build; the comparisons still hold because every option ran on the same platform.
2. **Caught by the equity-vs-action check.** The pool of candidate opponent hands was only 20. Against a raise, the "top 25%" of 20 random hands held no aces, so top pair had more equity against a raise (0.86) than against no action (0.81). Fixed with a pool of 40 and narrower ranges for a bet (0.35) and a raise (0.12).
3. **Found by C.** Flop-chip payments were credited to the next hand when we had folded preflop. Fixed: a balance drop first seen in a new hand is not credited to anyone's current hand.
4. **Found by C.** The range we continue with against a re-raise always used the 4-players-behind opening range, so heads-up we folded 68% to re-raises. Fixed to use our actual opening range, including heads-up.
5. Fold-to-re-raise was counted more than once per hand. Fixed.
6. **Not fixed:**
   - The all-in call ignores extra callers in the pot beyond a flat 8-point equity cut.
   - An opponent whose stack is all-in after betting is judged by pot odds, not tournament equity.
   - Callers on earlier streets don't narrow an opponent's range.
   - The call-all-in counter and showdown replay are not built.
   - Garbage memory of the right shape but wrong inner types would hit the catch-all: counted, but loses the turn's strategy.
7. **Kit:** `icm()` gives a busted player 0 (avoided). In the auction phase the kit's legality check accepts any "bid"; only the engine validates it.

### Critique of part1_v2.md, most important first
1. **The time budgets contradict each other.** The speed section says "a deadline of 0.15-0.2 ms from the start of the call", while the twist notes say "Use about 0.6 ms of the 1 ms". For this variant the twist compute was measurably worth points, and a failed bid costs nothing in chips.
   - Replace with: "Cap betting decisions at 0.15–0.2 ms. For a twist decision whose failure default is cheap (check the rules), allow up to 0.5 ms while the time bank is healthy, and measure points against compute time."
2. **The upload-test check can't see the twist.** "heads-up against the kit's check-or-fold bot, 20 hands, no time bank" never reaches the auction or a flop, so it says nothing about the variant's phase.
   - Add: "Also run the upload conditions against a bot that calls everything, and confirm the twist phase fired (count it)."
3. **No check covers the current-hand rebuild,** and my worst bug lived there. The "never from memory" warning is good but untested.
   - Add a check 9: "Scripted rebuild test: a hand with preflop, twist, flop and turn raises; assert the preflop raiser list, street, and dead and known cards."
   - Add to HOW TO WORK: "Treat 'harmless' remarks in subagent reports as claims; rerun the checks before acting on them."
4. **"Subagents report suspected platform bugs in their first message, not their last" can't be followed.** A background subagent hands back once. Both reported at minute 10–12. That was useful, but only because they were fast.
   - Replace with: "Give each subagent a 10-minute deadline for a first report including platform bugs; then continue it with a second brief."
5. **Helped most:**
   - The enumeration-on-shared-deals paragraph: the 10 flops on the same runouts was the right design.
   - "Simulate today's ranking … by minute 20": it found the collapse of pocket pairs.
   - The warning that the kit's ICM gives busted players 0.
   - "Count the pot once … only the matched part": I got it right first time.
   - "Measure the baseline in the same run": it was the only thing that made sense of the 4–17 ms tails on a loaded machine.
   - The fold-to-re-raise ≤75% rule exposed the heads-up leak in C's report.
6. **Too long to act on in hour one; skipped or partial:**
   - The full STRATEGY regional numbers (used only as starting values).
   - Showdown replay (correctly deferred).
   - "recording each seat's exact open and bet sizes from hand 1": I recorded open sizes only.
   - The call-all-in counter.
   - "100,000 random legal states": generating legal states is not trivial. I harvested them from play (30,000 by minute 22, 100,000 at minute 40).
   - Suggest: "100,000 states harvested from local play with sparring bots, with memory rotated between real, cut, garbage and empty."
7. **Unclear:** "Round weights today: 1,2,3,4,5,6" drives nothing in the first hour. Say what it changes, or move it to the between-rounds brief.
8. **Missing for this variant:**
   - When the twist outcome is jointly decided by everyone's bids, test against opponents who also bid well (self-play arms).
   - Use public balance changes as hand information.
   - Plan a currency that is worth nothing at table end.
   - The trap list's "bid totals" and "budget over 120–140 hands" lines covered this partly and helped.
9. **Twist notes: moderately useful.** None of the 12 entries matched a flop auction. What transferred:
   - Section 0's shared-deal and noise rules (directly used).
   - Section 2 item 6, dead-card bookkeeping (the two unchosen auction cards).
   - T7's budget pacing (directly used).
   - Section 3's deck-partition test.
   - The "0.6 ms" advice conflicts with the prompt (point 1).
   - Missing: a generic "auction over board cards" entry, and "evaluate the twist's preflop effect: pairs vs high cards".

### The single change that would most improve the bot at minute 60
Make the auction scoring much cheaper per sample, so each auction gets about 100 shared samples instead of 12–20. Options are precomputed hand-class-versus-flop tables or a batched evaluator. Then retune the bid budget against a field where the other bidders also bid by simulation. The auction is the dominant lever: never bidding to bidding by simulation is +8 points per table, and points rose with thinking time (18.6 → 19.7 → 20.4). The budget has only ever been tuned against weak bidders.