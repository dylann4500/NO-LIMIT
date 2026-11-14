# Pre-event note A: the regional variants, the organizers' pattern, the twist list, three timed drills

Drafted Saturday 14 November 2026, 05:10-06:00 PST, by a research session. Sunday's `theory` agent: check it and
extend it; don't redo it. Notes only: every script behind the numbers was throwaway and has been deleted.
Tags: **[C]** confirmed (our own files, or a page we fetched), **[I]** indirect (second-hand), **[J]** our judgement.

## Summary

- **Every regional was the same 8-player sit-and-go (2,000 chips, 10/20 rising every 20 hands, 250-hand cap, 50/30/20,
  1 ms) plus one new decision phase: sealed, simultaneous, free in poker chips, with its own action and a default that
  never folds.** Deck and hand ranks never changed, so `eval7` stayed valid. [C]
- **Pittsburgh's variant is found:** three hole cards and two boards; after the turn betting everyone discards one card
  face down; each board pays half the pot. Bay Area and Boston are as we knew them (§1).
- **Each variant combined two components, and the phase moved each time.** Used so far: a third hole card (twice), a
  discard (twice), a forced expose, a second currency with an auction, choosing board cards, two boards.
- **Kits leak the next variant.** Our Bay Area kit (6 November) already held Pittsburgh's `discard` action and
  multi-board code. Whoever has a Pittsburgh kit should search it on Sunday morning (§2).
- **Priors for Sunday [J]:** a card exchange or draw 25%; picking or allocating among shared cards or boards 20%; a
  bounty-style payoff 12%; a new second-currency auction 12%; a board vote 8%; anything else 23%. 85% that it is again
  one sealed free phase; 60% that it reuses a regional component.
- **Drills, announcement to first trusted table:** flop draw 15.5 minutes (fallback at 7.4), bounty 8.3 (fallback at
  4.9), flop veto 4.5. They produced 13 corrections to `TWIST_NOTES.md` and `theory.md`.
- **Not found:** eight of the 20 finalists; Pittsburgh's team count, standings, weights and official rules page; the
  Finals venue; any hint of the Finals twist.

## 1. The three regionals

| | Bay Area, 6 Nov | Boston, 9 Nov | Pittsburgh, 12 Nov |
|---|---|---|---|
| Twist | 3 hole cards; after the flop, before betting, discard 1 face down and expose 1 of the other 2; the exposed card stays public after a fold [C] | 2 hole cards; after preflop betting 5 candidates face up; everyone bids flop-chips on each card; the 3 highest totals are the flop (ties to the earlier card); you pay only bids on chosen cards; the other 2 are dead [C] | 3 hole cards, 2 boards side by side; after the turn betting discard 1 face down; the 2 kept cards play on both boards; each board pays half the pot [C: two participant repos] |
| Phase, action, default | `select`, `cards=(discard, reveal)`, 6 options, default (2, 0) [C] | `auction`, `bid` with five numbers, default all zeros; 1,000 flop-chips per table, balances public, bids secret [C] | `discard`, `cards=(index,)`; boards in `state.variant["boards"]` [C]; default not found |
| Teams; weights; tables per round | 148 ranked; 1-6; 20,000 [C] | 231 ranked (Sequoia: 270 teams) [I]; 1, 2, 3, 5, 8, 13; 10,000+ [C] | not found |
| Top five | 2 Curry 428.72, Lemonade 421.08, AZ 383.96, sandylikesfrogs 381.95, Team 72 381.25 (avalon 6th, 376.71) [C] | Du-o 727.26, Situational Awareness 715.32, BHTG 680.77, Preesh 656.03, 0_o GTO Slop 641.48 [I] | 1st: Steven Peng's team, first in four rounds and second in two [I]; rest not found |
| What winners did | 2 Curry: VPIP 38-43%, 3-bet 32-39% wide, 20+ points every round [C]. Sequoia: an exposed card pairing the board got 72% folds [C] | Leader: "aggressive play and larger auction payments"; a top-5 player: CFR failed in time, stats, heuristics and fast testing worked [I]. Average bid 28 flop-chips in round 1, 66 in round 6 [I] | not found. A top-50 bot kept the pair with the best combined chance over both boards [C] |

Also [C]: Boston tables could draw their own payout split (read `state.config.payouts`). **Finalists:** top five per
regional plus up to five wildcards [C]. Known: the ten teams above, Pittsburgh's winner and avalon. The other eight:
not found.

## 2. The pattern, and what it implies

1. **The frame never moves.** The rules page opens with one sentence ("Standard no-limit hold'em, except...") and ends
   with one starting "Improve...", which names where the organizers think the points are. Read those two first.
2. **One sealed phase with a small option set** (6 options, 3 options, five numbers under a budget). All-in players
   choose too. A choice cannot depend on the others' choices: simulate it that way.
3. **The twist changes which cards people hold and reveals something**, so the preflop ranking moves. It never changed
   who wins a showdown.
4. **Lineage.** MIT Pokerbots ran three hole cards with a discard in 2026, an auction in 2024 and three boards in 2021
   [C]. Not yet echoed: Bounty 2025, River of Blood 2023 (extra river cards), Swap 2022 (random hole-card swaps),
   Permutation 2020. The application puzzle was Colonel Blotto [I]: expect allocation, auctions or voting.
5. **Kit foreshadowing.** A Pittsburgh team's notes say the kit also lists "a bidding or pick phase and an exchange
   phase" [I]; exchange is the component still unused. **Sunday morning:** in any Pittsburgh kit, search
   `narration.py`, `local_replay.py` and `history.py` for action kinds Pittsburgh's rules don't use.

**Implication.** Fold, shove and bet rates matched within about 3 points across Bay Area and Boston (`EVIDENCE_TABLE`), and
both winners won on aggression, so the hour is not won on the twist. But a bad twist choice costs 6 to 13 points of
equity (drills), and a short rule recovers nearly all of it: build the rule first, perfect it later.

## 3. The twist list against the pattern

`TWIST_NOTES.md` fits the pattern in T9, T10, T13 and in T2 without its fee. **It misses five families:** two boards
with a split pot (Pittsburgh's own), a bounty, involuntary swaps, extra board cards, and passing a card. For any twist
compute first **what the best choice is worth over the default**, **the hand ranking with every player using the
twist**, and **what the choice reveals**. The ten most likely, with what is specific to each:

1. **Sealed draw or exchange** (drill 1). One sample = opponent hand, turn, river, then a replacement per player; score
   all three options on it. Drawing well beats keeping by 8.4 points; small pairs fall about 59 places. Mistakes: a
   replacement from dead cards; an opponent who never draws; trusting an average rule error.
2. **Two boards, split pot.** Value = the mean of the two board shares; with one river left per board, enumerate both.
   Compute the scoop rate: half-pot results move every break-even. Mistakes: one card on both boards; pot odds from
   "win probability" instead of expected share.
3. **A third hole card under a new rule.** Rank the 22,100 triples by best pair plus what the third card adds (17.2%
   hold a pair). Mistake: giving `eval7` every hole card when the rule limits how many play.
4. **Pick or draft from shared face-up cards.** Score each option with what it denies; give every opponent their own
   best pick inside every equity. A personal river needs no sampling.
5. **Bounty** (drill 2). Closed-form hit chances first; value = equity × 1.5 with the rank in hand, × 1.165 otherwise;
   hand order barely moves, call and bluff thresholds do. Mistake: equity × (1 + 0.5 × hit chance).
6. **A second-currency auction for something new.** Winning is worth my equity with the prize minus my equity when the
   strongest opponent gets it; budget = balance ÷ auctions expected to remain. Mistakes: hoarding; tuning against bad
   bidders.
7. **Board vote or veto** (drill 3). The 46 unseen cards serve all four options. Controlling the kill is worth 6.5
   points; pairs lose 1.7. Mistake: sincere voting (a pivot-aware vote gained 1.85).
8. **Pass a card to a neighbour** (rehearsed 14 November: the pass rule beat the default by 13.3 points; pairs fell to
   157th-169th). Mistake: the passed card dealt again from the deck.
9. **Extra or variable board cards.** Simulate the stopping rule; flushes and full houses inflate, one pair falls.
   `eval7` takes up to 9 cards. Mistake: fixed five-card runouts.
10. **Involuntary swaps or a hidden rule.** Equity is a mix of the current hand and a random one; for a hidden rule,
    record what each showdown reveals within the table.

## 4. Drills

Three mock rules pages in the organizers' style; clock started at "announced"; 2 worker processes each.

| Drill | Fallback table | First trusted table | Headline (heads-up, all-in, against a random hand) |
|---|---|---|---|
| 1. Sealed flop draw | 7.4 min | 15.5 min | Best option +8.43 ± 0.03 points over keeping (keep 17%, throw the lower card 60%, the higher 22%). A nine-line rule loses 0.065; Monte Carlo in the bot loses 0.10 at 200 samples (0.5 ms) |
| 2. Bounty (1.5× on pots won with your rank showing) | 4.9 min | 8.3 min | Rank not in hand: value 1.165 × equity, not 1.1765, because hitting and winning are negatively correlated (equity 47.0% when the rank comes, 51.6% when not) |
| 3. Flop veto (vote one of four cards out) | none | 4.5 min | A pivot-aware vote beats a sincere one by 1.85 ± 0.04 points |

**The recipe that worked** (step timings and what went wrong: Appendix B):
1. Write down when the choice is made, what each player sees then, which cards die, and the default.
2. Run the checks and time 50,000 deals before designing (8 seconds). Measured 2.2-4.4 µs per deal: 169 classes ×
   100,000 deals take 37 seconds on 2 workers, no Modal needed. Cost estimates made before timing were 5× too high.
3. Deal every card from one shuffle, and score plain hold'em on the same deal.
4. Every simulated player decides by one shared cheap rule, never nested Monte Carlo (1,300× slower, and noisier).
   Ship the first-guess rule's table as the fallback: it was within 1.4 points of the final one.
5. Improve the rule on 40,000 stored spots × 1,000 shared samples (55 seconds): choose on half the samples, score on
   the other half, print the loss by hand category, fix the worst, stop under 0.1 points.
6. Confirm: combo-weighted mean equity 50.0, symmetric option shares, a nested re-run of about 18 classes.
7. Payoff twists: closed forms first, then one loop counting outcomes by bonus condition (1,000,000 deals per class,
   187 seconds per worker). Measure E[share × hit]; never multiply two averages.

## Corrections for TWIST_NOTES and theory.md

**TWIST_NOTES.md**
1. **T9, wrong.** "Voting as if your vote decides the outcome is correct, because your vote only matters when it breaks
   a tie." Replace with: "Your vote matters only when it is pivotal, and the tie-break decides when. Heads-up with ties
   to the lower index, the killed card is the lower-indexed of the two votes: score vote i as the average over the
   opponent's likely votes j of your equity after killing card min(i, j). Against a sincere voter this gained 1.85 ±
   0.04 points; votes shift to low indexes (39/30/20/11%). With more voters, count the pivotal cases the same way."
2. **T3(a) and §3 bug 4, resolved.** "[unsure whether eval7 accepts 8]": `eval7.evaluate` accepts 5 to 9 cards and
   returns the best five (2,000 random 8-card hands against the best 7-card subset: 0 mismatches). Take subsets only
   when the rules limit how many hole cards play.
3. **T2 Value, missing numbers.** After "with CRN, N≈200" add: "One sample holds the opponent's hand, turn, river, my
   replacement and the opponent's; both throw options use the same replacement. Free draw, measured: the best option
   beats keeping by 8.4 points. In the bot a Monte Carlo choice loses 0.65 points at N=50, 0.28 at 100, 0.10 at 200
   (0.5 ms), so use a rule (loses 0.065): keep pocket pairs, two pair or better, two-card flush draws, pure two-card
   open-enders and two-card gutshots with both cards ten or higher; next to a pair throw the kicker (except an ace with
   top pair); with nothing always throw, keeping first a card with a gutshot, then a card with two flop cards of its
   suit, then the higher card."
4. **T2 Preflop, half wrong.** "suited connectors gain... Widen those opens slightly." Replace with: "Equities compress
   (39-80 instead of 32-85). 22-66 lose 9.5 points and about 59 places (22 is 163rd), JJ-AA lose 6.6 and stay on top,
   suited connectors lose 1.8 and 19 places, ace-rag and king-rag rise 7-9 places. Open fewer small pairs and suited
   connectors."
5. **T2 Leak, wrong for showdowns.** "you can sometimes keep with air on dry boards [unsure]": keeping with air costs
   about 17 points of equity (16% keeping, 33% after throwing the lower card).
6. **§0, add:** "To measure what the best option is worth, choose it on half the samples and score it on the other half.
   Break exact ties at random and check that option shares are symmetric." And for offline payoff tables: "1,000,000
   deals per class; count outcomes keyed by the bonus condition in one loop."
7. **§2 item 8, pessimistic.** "150–300 heads-up samples per ms": measured on the laptop 550-675 plain samples per ms
   and about 400 three-option samples per ms.
8. **§1, add two entries:** a bounty (value multiplier 1 + b × P(hit | I win); hit chance 1 − C(unseen − 4, k) /
   C(unseen, k): 35.3% preflop to river, 16.5% from the flop, 8.7% from the turn; a pot-size call needs 22.2% with the
   bounty hit; a pot-size bluff needs 40% folds) and two boards with a split pot (this note, §3 item 2). **§3, add bug 6:**
   bonus accounting (test: paid = pot + bonuses on 40,000 deals, bonuses only to winners whose rank shows).

**theory.md**
9. **Pre-event line:** add "Pittsburgh: three hole cards, two boards, discard one face down after the turn betting,
   each board pays half the pot."
10. **"a 7-card evaluation about 0.46 µs":** 0.32 µs measured; add "a full heads-up deal with the twist 2.2-4.4 µs;
    169 classes × 100,000 deals in 37 s on 2 local workers. Time 50,000 deals before designing anything."
11. **m10 `ranking.json` bullet, add:** "Every simulated player takes the twist decision by the one shared cheap rule,
    never nested Monte Carlo. Ship the first-guess rule's table as the fallback by minute 7. For a payoff twist rank by
    expected chips per chip of pot, one column per twist state, and give the simple rule that reproduces the table."
12. **"Checks before a table ships", add:** "combo-weighted mean equity 50.0 under any symmetric twist (weights 6/4/12,
    sum 1,326); against a random hand AA 85.2, 72o 34.6, 22 50.3, AKs 67.0; exact matchups with suits named: AsAh vs
    KdKc 81.26, AsAh vs KsKh 82.64, AsKs vs QdQc 46.21 (1 second each); the twist rule is unchanged by card order and
    suit relabelling."
13. **"Use the team Python", add:** "with `-I`, put the script's folder on `sys.path` yourself or sibling imports fail;
    in zsh keep the interpreter path alone in a variable."

---

## Appendix A. Sources

Our own files [C]: `starter-kit/RULES.md` and `starter-kit/sdk/` (Bay Area rules; `narration.py`, `local_replay.py`,
`history.py` and `variant.py` hold the `discard` and `board_count` code); `docs/writeup/avalon-writeup.tex` (Bay Area
standings); `docs/FINALS_PLAYBOOK.md` §1-2 (2 Curry's style, round sizes, weights); `emu/variants/flop_auction_holdem.md`
(Boston rules, rebuilt from the Format page and hand histories); `research/finals_prep/adaptation/REPORT.md` §6
(Boston field); `finals_pack/prep/SPEEDRUN_14NOV.md` (pass variant numbers); `strategy/TWIST_NOTES.md` T13 (mock auction).

Web, fetched 14 November:
- Pittsburgh rules and format: https://github.com/CapitanoZ/no-limit-2026-pokerbot (README: "After the turn betting,
  everyone discards one hole card face down"); https://github.com/noe2971/PokerBot (README and `agent.py`: phase,
  action, `state.variant["boards"]`; "top 50").
- Pittsburgh winner [I]: a LinkedIn post seen only as a search snippet via https://www.linkedin.com/in/artem-saraiev/.
- Boston rules: https://github.com/lirockyzhang/applied-math/blob/main/RULES.md ; https://github.com/AlexPha45/No-Limit-Pokerbots
  (231 teams, a 8.09-point team).
- Boston standings, the leader's style, Bay Area and Boston field statistics, "pick" and "exchange" phases, the
  Blotto application puzzle [I]: a Pittsburgh team's public notes,
  https://raw.githubusercontent.com/tranthuanhieu1610/no-limit-pittsburgh-playbook/main/references/sam/intel-earlier-regionals.md
  (it also names avalon as 6th at Bay Area and summarizes our write-up: every finalist can read it).
- Boston event: https://www.thecrimson.com/article/2026/11/12/poker-tournament-regional/
- Sequoia posts: Bay Area recap https://x.com/sequoia/status/2119839104733200785 ; Finals announcement (20 teams,
  $100K, Noam Brown talk) https://x.com/sequoia/status/2120270083830493656 ; rules https://pokerbot.sequoiacap.com/rules.html
- MIT Pokerbots engines, one per year: https://github.com/mitpokerbots (engine-2020 Permutation, 2021 Blotto, 2022
  Swap, 2023 River of Blood, 2024 Auction, 2025 Bounty, 2026 three hole cards with a face-up discard); 2019 not found.

Searched and not found: a Pittsburgh recap by the organizers; Pittsburgh team count, standings and weights; the
finalist list; the Finals venue; a public team named "2 Curry"; any organizer hint about the Finals twist; a public
copy of the Boston or Pittsburgh kit. Not opened (login needed): LinkedIn posts by Pittsburgh's and Boston's winners,
X search of Sequoia's posts. Queries tried are in the session's web log (not in git).

## Appendix B. Drill logs

All three: heads-up, all-in before the flop, against a random hand; laptop load 3-7; throwaway Python with `eval7`.
Errors common to more than one drill: "AA vs KK 81.9%" is a suit average (single layouts give 81.26-82.64);
`python -I` drops the script's folder from the import path; first-index tie-breaks bias option shares; an average
rule error hides class-specific leaks; two false alarms cost 6 minutes.

**Drill 1, sealed flop draw (a subagent with the `theory` role file; T0 05:16:55).**
- Timings: reading and design 3.7 min; library and checks 0.9; first study (40,000 spots × 1,000 samples) 0.9;
  first-guess-rule ranking 0.3 (fallback at 7.4); rule revision 1.8; ranking 0.5 (table at 10.2); second study 0.9;
  nested cross-check 1.0; second revision 0.4; final ranking 0.6 (13.6); cross-check and suit-averaged references 1.9
  (trusted at 15.5). About 12 minutes without the detours.
- Samples: 100,000 deals per class, SE 0.13-0.16 points; variant-minus-hold'em SE 0.11-0.16.
- Results: equities 39.3-79.7 (hold'em 32.3-85.1); pairs lose 8.4 on average; unpaired Broadway loses 5.5; 72o gains
  8.6; rank correlation with hold'em 0.957; 63 classes move 10 places or more. Rule shortfall: first guess 0.35,
  second 0.093, third 0.065; always throwing the lower card 5.35. Top two options within 3 points in 29% of spots.
- Went wrong: the suit-specific reference (false alarm); a cost estimate 5× too high; the first rule ignored backdoor
  flush cards and single-card gutshots; the second threw a card from two-card Broadway gutshots (AK on Q-J-x: keep
  51.3, throw 46.2); a false lead on breaking small pairs (noise at 300 nested samples).
- Checks: evaluator against an independent ranker on 3,020 spots, 0 mismatches; AA 85.26 ± 0.06, 72o 34.50, 22 50.37,
  AKs 67.01; symmetry 49.989 ± 0.013; 1,850,000 deals audited for 52 distinct cards, 0 failures; rule invariance on
  40,000 spots. The loss-by-category table and the per-class nested cross-check caught both rule leaks.
- Unverified: ranges, three or more players, betting after the draw, the organizers' hardware.

**Drill 2, bounty (a subagent; T0 05:24:24).**
- Timings: design and worker 2.2 min; pilot (50,000 per class) 0.3; checks and build scripts 2.0 (fallback at 4.9);
  main run 3.1 per worker (trusted at 8.3, would be about 6 with three workers); exact AA 6.4; second seed 3.0;
  exact Q4s 4.9.
- Results: with the rank in hand all classes but 32o and 42o return over half the pot. Not in hand: hit 35.30% by the
  river; multiplier 1.158 (32o) to 1.175 (AA); `1.18168 × equity − 0.00785` is within 0.22% of pot. Order moves at
  most 2 places. A random opponent's bounty is hit 14.9% preflop and 48.4% on a five-rank river; they call wider.
- Went wrong: tooling only (`-I` import path, a zsh variable, a format-string crash on the pilot); a split-half outlier
  (Q4s, 3.7 SE) that an exact enumeration showed to be noise.
- Checks: all passed first time, so three errors were planted: ignoring hole cards (caught, z −114), a tie counted as
  a win (caught, z 496), assuming independence (missed by a 150,000-deal cell check; caught only by an exact low
  suited class, 8.8 SE). Mock-rule assumption: the bonus is 50% of the pot share, paid in new chips.
- Unverified: flop and turn correlation, multiway, non-random opponents.

**Drill 3, flop veto (the research session itself; T0 05:20:06, rules already in mind).**
- Timings: evaluator check and two exact matchups 0.1 min; simulator 0.8; tie-break fix 0.3; 1,200,000 deals on 2
  workers 2.8 (each player votes by 40 shared samples per option; 0.28 ms per deal); analysis 0.5 (trusted at 4.5);
  strategy comparison 1.1.
- Results: SE at most 0.58 points per class; pairs −1.7 on average (22: 87th to 100th); suited +0.6, 52s-76s +2 to +3;
  both players vote the same card 26% of the time; the killed card is index 0 in 43% of deals. Voting by current made
  hand loses 1.23 ± 0.07 to voting by simulation.
- Went wrong: first-index tie-break (votes 30/25/23/21% until fixed, caught by the option-share check); `-I` import
  failure; the first "value of the vote" measure was zero by symmetry and had to be replaced.
- Unverified: three or more voters, opponents who vote strategically.
