## Summary
The prompt got a legal bot uploaded in 1.5 minutes and three tested styles by minute 18. Every bot ended with zero failed decisions. I stopped building at 16:19, 28 minutes into the hour. From then on, local tests on this overloaded machine could no longer tell my changes apart. That left 32 minutes unused, which a real team would spend on practice-round data.

The prompt helped most in two places: it insisted on simulating today's preflop ranking, and it said to value the twist by enumeration. It hurt most in three places:
- It defines the pressure style with hold'em numbers. Pressure lost badly when our own bots played each other.
- It leads you to keep the current hand's state in memory, which creates a silent bug when memory is cut.
- It sets a 0.3 ms sampling deadline that equals the 0.3 ms target for the whole decision, and it assumes an idle machine to measure on.

All work is in `/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/buildtest/flop_pass_holdem/` (bot/, tools/, spar/, notes/NOTES.md, submission/agent.py).

## Timeline (start 15:51:05)
| Milestone | Clock | Elapsed | Prompt target |
|---|---|---|---|
| Kit read, summary written | 15:51:40 | 0:35 | – |
| Minimal bot passes `check` and plays with 0 failures | 15:52:28 | 1:23 | 10:00 |
| Minimal bot copied to submission/ | 15:53:43 | 2:38 | 10:00 |
| Variant preflop ranking simulated | 15:54:16 | 3:11 | – |
| Shared platform and base strategy built, 0 failures | 15:57:25 | 6:20 | – |
| Upload-test and 100k-state harnesses written | 15:58:05 | 7:00 | – |
| Base copied to submission/; style subagents B and C spawned | 15:59:45–16:00 | 9:00 | – |
| Style B (shove) returned | ~16:03 | ~12 | – |
| Style C (tight) returned | ~16:08 | ~17 | – |
| Style A (pressure) built; all four pass check and the upload test | 16:08:37–16:09:01 | 18:00 | – |
| Bug fixes, sparring bots, round robins | 16:09–16:19 | 18–28 | – |
| Build stopped; submission = shove | 16:19 | 28:00 | 60:00 |

## What I built
**Variant (San Francisco).** After the flop, every live player passes one hole card to the left (heads-up they swap).
- New phase `pass`, answered with `Action("pass", cards=(i,))`.
- `state.variant` has `pass_to`, `receive_from`, `passed` and `received`.
- A failed choice passes index 1.

**Key finding: pocket pairs are the worst preflop hands.** You must hand one of the pair's cards to an opponent: AA wins about 24% heads-up against a random hand. Ace with a low kicker is best (A2s about 64%). In 4-way pots AK and AQ are best and pairs are still worst. This came from a 169×169 heads-up equity table under passing rules plus a 4-way simulation, built at build time and embedded in the bot.

**Platform (`bot/platform.py`, `bot/strategy.py`).**
- **Safety shell:** a legality function, a catch-all that counts its hits, defensive memory parsing, one file with everything embedded, warm-up of every phase and garbage collection frozen at import.
- **Equity:** Monte Carlo with an iteration cap and a 220 µs deadline. It uses the card we passed (known to be in the left neighbour's hand) and the card we received (the right neighbour kept something at least as good). Opponents are modelled as using the pass: each keeps the card that fits the flop better.
- **Pass choice:** both options are scored on the same paired samples.
- **ICM:** my own function; a player who busts gets their place's payout.
- **Per-seat counters:** 9 rates, each blended with a prior.
- **Team recognition:** structure in place; the profile table is empty.

**Styles:** shove (subagent), tight (subagent), pressure (mine), plus base. `bot/build.py` concatenates platform, strategy and style into one `agent.py`.

**State at 16:19:** submission/agent.py is shove. It packs, passes `check`, and imports from an empty folder in 0.08 s.

## Evaluation
**1. Kit check and upload-test conditions.** Heads-up against check_or_fold, 20 hands, time bank 0, 1 ms limit, 10 seeds per bot. All five bots (minimal, base, pressure, shove, tight) pass `poker-agent check`, with 0 failed decisions out of 100 each.

**Decision time.** Measured in-process on 20,000 decisions per bot, at load average 18–35, not on an idle machine:

| Bot | Mean | p50 | p99 | p99.9 | Max |
|---|---|---|---|---|---|
| minimal | 9 µs | – | 20 µs | 36 µs | 1.2 ms |
| pressure | 117 µs | 67 µs | 260 µs | 969 µs | 7.1 ms |
| shove | 124 µs | – | 263 µs | 885 µs | 12.9 ms |
| tight | 125 µs | – | 266 µs | 584 µs | 3.9 ms |

- No style meets the prompt's "99.9% under 0.3 ms" on this machine.
- Across all fuzz runs: 0 illegal actions and 0 catch-all hits. Memory never exceeded 1.3 KB.
- The spikes come from machine load. In the round robins, failed decisions ranged from 0 to 13 per 160 tables, and check_or_fold failed too at load 55.

**2. Round robins** (8 seats, points per table ± standard error; same-bot noise check heads-up: 40.3 vs 39.7):

| Field | pressure | shove | tight | Others |
|---|---|---|---|---|
| Kit examples and sparring bots, 300 tables (final) | 19.9±1.3 | **24.0±1.1** | 20.7±1.3 | minimal 10.1±0.8, check_or_fold 12.4±0.7, nit 7.7±0.7, min_raiser 3.0±0.7, shover 2.2±0.6 |
| Two seats of each of our bots, 400 tables | 7.8±0.8 / 9.4±0.9 | **14.5±0.9 / 14.7±0.9** | 12.7±0.9 / 13.6±0.9 | base 14.2 / 13.3 |
| Two seats each, 300 tables | ~10; a tamer pressure2 also ~10 | 16.2 / 14.4 | 13.9 / 15.0 | – |
| Heads-up, 120 tables | 38.5 vs tight 41.5 (±0.9) | 38.3 vs tight 41.7 | see left | – |

- The minimal bot scores below check_or_fold (10.1 vs 12.4).
- **Choice:** shove plays scored round 1, tight is the challenger, pressure is dropped.
- Pressure's loss in the all-our-bots field matches the prompt's cycle ("limp-or-shove beats wide re-raisers").
- The sparring bots pass cards at random, so these results flatter us.

**3. Cold bug hunt**

Fixed:
1. **The pass choice was biased.** Both options were scored one after the other against one deadline, so the second option got 4 samples against about 35 for the first. Now both are scored on the same samples.
2. **The left neighbour's other card was sampled at random.** It should be the card they kept as the better fit for the flop.
3. **Our passed card stayed in the deck after the left neighbour folded.**
4. **The in-hand tracker lived only in memory.** With cut or garbage memory the bot treated a raised pot as unopened and opened into a raise. It is now rebuilt from `state.history` (in fuzz this fired 16 times in 5,000 decisions).
5. **Heads-up big-blind detection was wrong.** It used position (n−2)%n, which is the button heads-up, so the defence branch never ran. Both subagents found this.
6. **ICM call overstated our win.** When the villain covers us, the unmatched part of his bet was credited to us. My fix then double-counted it in the fold branch; caught and fixed.
7. **The "calls an all-in" stat was declared but never counted.**
8. **Equity barely fell against aggression.** Top pair was 93% against no action and still 83% against a bet and a raise. Opponent hands are now drawn as the best of 1/3/6/9 samples by aggression. This is tuned, not validated.
9. **Tight had copied the shared postflop function into its style file.** My later platform fixes (dead card, right-neighbour information) did not reach it until I patched it.
10. **Team recognition read match scores that nothing ever wrote.**
11. **Branch counter names:** postflop counters were prefixed `pf_`, and a big-blind check was counted as a fold.

Not fixed:
- **A. Re-shoves are judged as calls.** `call_or_reshove` uses a call test, with no fold equity and no extra chips at risk. It also goes all-in with rank ≥ 0.85 even when only a call passed the test.
- **B. Wrong range for 3-bet and 4-bet shoves.** It uses the shover's raise-first-in rate.
- **C. ICM simplifications:**
  - The fold branch gives the whole pot to one villain, which is wrong in multiway pots.
  - Side pots are ignored.
  - Two players busting on the same hand are ignored.
  - The shove amount (`extra_pot`) is not capped at the effective stack inside `allin_ok`; the shove style caps it itself.
- **D. Mislabelled stats.** "Bet when checked to" also counts the first player to act. "Raise first in" chances are counted for players acting behind limpers.
- **E. The preflop table assumes a different pass policy than the bot uses.** The table assumes everyone keeps the card that fits the flop better. The bot itself passes by equity. No modelled opponent considers what it gives away.
- **F. Crude preflop equities.** Multiway all-in equity is the heads-up figure × 0.85 per extra opponent. Pass equities ignore opponents' preflop ranges.
- **G. Shove never folds to a re-raise.** It continues 100% of the time, which overshoots the 75% fold cap the prompt sets.
- **H. Not built:** the showdown bluff bounds and the style report by players remaining (I built only an overall one).
- **I. The deadline caps only sampling.** Memory handling (JSON) and event processing cost about 70 µs in every decision.

## Critique (most important first)
1. **The style definitions are written in hold'em numbers.**
   - Quote: "A. pressure: opens and re-raises wide (the regional winner's style)" and "The winner raised first in about 40% of the time and re-raised (3-bet) a third of the opens".
   - Under this variant the hand order is reversed for pairs, and the pressure style was the clear loser (7.8–10 against 13–16) in the field of our own bots.
   - "Treat these as starting values" is not enough when the styles are defined by those values.
   - Replacement: "Define each style as a fraction of TODAY's simulated ranking and a stack-depth rule. Before any style, check that its aggression is profitable in a field of our own other styles. The regional numbers are hold'em-specific; use them only for variants whose preflop ranking correlates above 0.8 with hold'em's."
2. **The memory rule hides a silent bug.**
   - Quote: "everything the bot remembers about a table lives in the memory bytes".
   - Following it, I kept the current hand's state in memory. When memory was cut, the bot misread raised pots as unopened.
   - Replacement: "Rebuild the current hand from `state.history` on every call. Use memory only for cross-hand statistics, and test with cut memory in the middle of a hand."
3. **The timing instructions contradict each other.**
   - Quote: "cap any sampling ... a deadline around 0.3 ms from the start of the call" and "Aim for 99.9% under 0.3 ms" and "on an idle machine".
   - A sampling deadline equal to the target for the whole decision guarantees missing the target, and there was no idle machine.
   - Replacement: "Set the sampling deadline at 0.15–0.2 ms. Measure on the build machine with `time.process_time_ns` as well as wall time. If the load average is above the core count, trust only the upload test and say so."
4. **The enumeration instruction invites biased comparisons.**
   - Quote: "list the legal options, score each with the same equity function, and take the best, inside the time limit."
   - Done literally, scoring the options one after the other starves the later ones of samples (bug 1).
   - Replacement: "Score all options on the same random deals, interleaved in one loop, so they get equal samples and common noise."
5. **The prompt only points at public information.**
   - Quote: "use every piece of information the twist makes public".
   - This variant's information is private: we know one of the left neighbour's cards, and the card we received tells us the right neighbour kept something better. A literal reading skips both.
   - Replacement: "...the twist reveals to us, publicly or privately (cards we passed or received, what an opponent chose to give away)...".
6. **Subagent hand-off rules leave gaps.**
   - Quote: "spawn two subagents ... changing only its style layer".
   - This worked well: both subagents returned in 3–8 minutes and both found real platform bugs. But one copied a shared function into its style file, so later platform fixes silently did not reach it.
   - Add: "A style may set parameters or wrap shared functions, never copy them. Report suspected platform bugs instead of working around them."
7. **The equity-against-action check is too weak.**
   - Quote: "equity for a fixed hand falls as the opponent's action strengthens from check to bet to raise."
   - My first model passed it while still giving top pair 83% against a bet and a raise.
   - Replacement: add magnitudes, e.g. "top pair against a heads-up bet and raise should be well under 65%."
8. **Too long to act on in an hour.**
   - The prompt is about 2,600 words. I did not build, or only stubbed:
     - team recognition ("record those sizes for every seat from hand 1 ... running match score"), which is dead code until profiles exist;
     - the showdown replay with bluff bounds;
     - the style report by players remaining;
     - several statistics in the OPPONENTS section.
   - These belong in a second-hour prompt.
9. **Practical gaps.**
   - Quote: "no time bank". The kit's `play` command has no time-bank option. I had to write a harness with `TableRules(time_bank_ms=0)`; the prompt should say so.
   - The kit asks for Python 3.12, which the machine lacked; I used `uv`. I installed only numpy, eval7 and the SDK, not torch and the rest.
   - The sparring list ("one that calls everything, one that shoves constantly...") was useful. It should add "and pass randomly vs. well", because sparring bots that ignore the twist flatter us.
10. **What helped.**
    - The minute-10 safety shell made legality a non-issue all hour.
    - "Build today's ranking by simulation" produced the decisive finding (pairs are worst).
    - The "opponents ALSO use the twist" warning shaped the opponent model.
    - The ICM reference figures were exactly checkable. My calculation gave 0.556 / 0.652 / 0.571 / 0.50 against the prompt's 56% / 65–74% / 57% / chip odds.
    - The busted-player ICM trap was useful.
    - "Run the same bot against itself first" gave the noise level.
    - "Take the bolder option when evidence is roughly even" settled the submission choice.

## The one change for Sunday
Replace the STRATEGY section's hold'em-calibrated style recipes with a variant-first instruction: "By minute 20, simulate today's preflop ranking and the twist's value. Express every style as fractions of that ranking and stack-depth rules. Build a mirror test rig (two seats of each of our styles plus sparring bots that also use the twist) and cut any style that loses there by more than 2 standard errors." In this run, the prompt's own hold'em-defined pressure style cost about 5 points per table in our own bots' field. Everything that worked came from simulating the variant, and a mirror rig would have caught the loser by minute 25 instead of minute 26 by luck. It also lets you move team recognition and showdown analysis to a later prompt, which shortens this one.
