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
- **A weak hint from kits.** Our Bay Area kit (6 November) shipped one variant, ours, but its shared replay and
  hand-history code already handled a separate face-down `discard` event and more than one board (`board_count`).
  Bay Area used neither; Pittsburgh's variant, six days later, used both. The kit had nothing for Boston's auction,
  which came in between: one hit, one miss (checked against the kit by the lead session, 14 November; §2).
- **Priors for Sunday [J]:** a card exchange or draw 25%; picking or allocating among shared cards or boards 20%; a
  bounty-style payoff 12%; a new second-currency auction 12%; a board vote 8%; anything else 23%. 85% that it is again
  one sealed free phase; 60% that it reuses a regional component.
- **Drills, announcement to first trusted table:** flop draw 15.5 minutes (fallback at 7.4), bounty 8.3 (fallback at
  4.9), flop veto 4.5. They produced 13 corrections to `TWIST_NOTES.md` and `theory.md`.
- **Three more drills, on one worker each (§5):** Pittsburgh's own variant 22.6 minutes (fallback at 5.1), a sealed
  split of four hole cards across two boards 16.4 (fallback at 6.9), a second-currency auction for an extra hole card
  6.0 (fallback at 4.1). They change four steps of the recipe in §4.
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
5. **Kit foreshadowing (weak).** Our kit's files `sdk/agent-sdk/src/poker_agent_sdk/local_replay.py`,
   `narration.py`, `local_history.py` and `sdk/engine/src/poker_engine/history.py` handle a `discard` event next to
   our own `select`, and `variant.py` documents `board_count`; the only variant in the kit is
   `flop_discard_reveal`. So the kit held plumbing for two of Pittsburgh's components, not its rules, and nothing
   for Boston's. A Pittsburgh team's notes say their kit also lists "a bidding or pick phase and an exchange phase"
   [I]; exchange is the component still unused. We have no Pittsburgh kit. Whether to go looking in one is for
   Dylan and Samuel to decide: the rules keep the variant confidential until it is announced.

**Implication.** Fold, shove and bet rates matched within about 3 points across Bay Area and Boston (`EVIDENCE_TABLE`), and
both winners won on aggression, so the hour is not won on the twist. But a bad twist choice costs 6 to 13 points of
equity (drills), and a short rule recovers nearly all of it: build the rule first, perfect it later.

## 3. The twist list against the pattern

`TWIST_NOTES.md` fits the pattern in T9, T10, T13 and in T2 without its fee. **It missed five families when this
was drafted; all five were added the same day:** two boards with a split pot (Pittsburgh's own, now T14), a bounty
(T15), involuntary swaps (T16), extra board cards (T17), and passing a card (T18). For any twist
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
6. Confirm: combo-weighted mean equity 50.0, symmetric option shares, a nested re-run of about 18 classes. Added after
   the 14 November timed run: score the rule at 3-4 players and against a range before calling it trusted (three
   clauses flipped), and check exhaustively that no choice breaks a made full house or better (one did, in two releases).
7. Payoff twists: closed forms first, then one loop counting outcomes by bonus condition (1,000,000 deals per class,
   187 seconds per worker). Measure E[share × hit]; never multiply two averages.

## 5. More drills, 14 November morning

Three more families from §3, each on **one** worker process (other timed tests held the laptop at load 8-10).
Same setting as §4: heads-up, all-in before the flop, against a random hand; "points" are percent of the pot.

| Drill | Fallback table | First trusted table | Headline |
|---|---|---|---|
| 4. Pittsburgh's variant (3 hole cards, 2 boards, discard after the turn) | 5.1 min | 22.6 min | The best discard beats the default by 10.82 ± 0.17 points. Scoop 23.5%, one board each 47.9%, nothing 23.5% |
| 5. Split hands (4 hole cards, 2 boards, sealed two-and-two assignment after the flops; our mock) | 6.9 min | 16.4 min | The best of six assignments beats the default by 12.95 ± 0.18 points |
| 6. Card auction (sealed first-price bids in 1,000 card-chips for an unseen extra hole card; our mock) | 4.1 min | 6.0 min | Winning the auction instead of losing it is worth 33.2 ± 0.07 points of the pot; "with minus without" is half that |

**Drill 4, Pittsburgh.**
- *Discard:* the best choice beats "keep the best pair for board 1" by 3.02 ± 0.09, "keep the two highest" by 5.96 ±
  0.13, and "best summed hand value over both boards" by 0.68 ± 0.03. In the bot, 100 shared samples (opponent's two
  cards and one river per board) lose 0.13 ± 0.01 in 0.58 ms; exact enumeration takes 0.54 s, so it is offline only.
- *Preflop:* 1,755 three-card suit classes, values 32.3 (222) to 79.6 (AA9o). Against ranking by the best two hold'em
  cards the rank correlation is 0.958 and 23% of hands move 10 or more percentiles: trips −7.8 points, pairs 22-77
  −4.1, three connected cards +3.4. The second board hardly matters preflop (correlation 0.995 with one board): the
  third card and the late discard make the difference.
- *Split pot:* the boards behave as independent once the discard is chosen (scoop ≈ p²). The variance of the share is
  0.48 of hold'em's. A call's break-even is unchanged (price = expected share), but a covered all-in busts only when
  it loses both boards: scoop-to-bust is 1.81 at a 57 share (hold'em 1.32), so an ICM call needing 1.5 to 1 needs a
  55 share, not 60. A pot-sized bluff needs 50% folds with no share, 20% with a 0.25 share, none from one third.
- *Mistakes:* a table was called trusted at 10.7 minutes with a leak: the shared rule summed raw evaluator values, so
  a small pair on both boards outvoted a big pair on one (22-55 with a high kicker off by 1.9 ± 0.24, single classes
  by 3.5). Group means hid it; per-class z-scores of a paired nested run caught it. 1.0 ± 0.11 of it remains.
- *For Sunday's theory agent:* multi-board, split pot, late discard. Time 50,000 deals first (9 µs here). Share is
  additive: score each board on its own river and count the nine board-result pairs per class in the same loop. Table
  all 1,755 three-card classes (weights sum to 22,100) at 4,000 deals: 125 s on one worker, SE 0.5. Never rank by the
  best two hold'em cards. The shared discard rule must score each board on an equity-like scale (hand percentiles
  plus a four-flush bonus lost 0.42; raw evaluator values lost 0.68 and mis-kept small pairs). Check with a paired
  nested run on 150+ classes covering every pair rank and kicker band, and read per-class z-scores before group
  means. Bot: 100 shared samples per discard. Pot odds use expected share.

**Drill 5, split hands.**
- *Assignment:* a 12-lookup table rule (12 µs) loses 0.26-0.45 to the best option; "strongest two cards to their
  board" loses 1.81 ± 0.06; "keep the pair or the suited cards together" loses 9.59 ± 0.18. A pocket pair stays
  together 90% of the time, two suited cards only 40%.
- *Is the sincere choice exploitable?* Slightly: the best response to a rule player gains 0.27 ± 0.02 and differs in
  16% of spots. Score each two-card hand against the cards an opponent **puts** on that board, not a random hand
  (ace-deuce on 8-6-5: 37% against random cards, 18% against chosen ones). Three-way, concentrating strength on one
  board loses 1.02 ± 0.04 and balancing 3.48 ± 0.10.
- *Preflop:* no 169 classes exist for four cards. 2,500 sampled hands × 500 deals and a 14-term regression gave an
  error of 0.62 points (values 33-70); "best two-card subset" errs by 3.18. Trips sit 8.0 ± 0.7 below the fit.
- *Split pot:* win both 21.2%, one each 50.0%, lose both 21.2%; the top 5% of hands still lose both 11%.
- *Mistakes:* the first rule was trained against random cards; the fallback ranking sat unread for five minutes
  because the next chain was queued on the only worker first; a 1.3-minute false alarm turned out to be a real
  board-texture effect.
- *For Sunday's theory agent:* a sealed allocation across boards. Expected share is the mean of the per-board
  equities, so score every (part, board) once and add. Build a flop-score lookup from 2-3 million deals (18-48 s),
  keyed by made hand, draws and flop texture, trained against the cards a rule-playing opponent puts on that board;
  retrain once against itself. Then 4,000 spots × 600 shared samples (60-95 s): best minus default, the rule's
  shortfall as a split-half to in-sample range, the best response to the rule, and a two-opponent column. Preflop:
  sampled hands plus a regression. Report win-both and lose-both rates. Analyse finished runs before queueing more.

**Drill 6, card auction.**
- *The prize:* I get the card 66.9, nobody 50.5, the opponent 33.7. By my hand: no pair 37, a weak pair 31, top pair
  or an overpair 25, two pair or a set 14, a straight or better 8; draws add nothing. Three players: 26.5 ± 0.07.
  Those five numbers estimate it with an error of 3.4 points, as good as 200 samples.
- *Preflop:* under a coin flip for the card, pairs lose 4.8 points (22 goes from 87th to 104th), 87s-54s gain 2.7-5.4,
  and 48 classes move 10 or more places. Getting the card is worth +2.9 to AA and +23.8 to 52o.
- *Budget (a model, with its assumptions in Appendix B):* only the winner pays, so "balance ÷ auctions left" spends
  under half: a survivor ended with 491 of 1,000 chips. The best reply to every field tried was 3-4 × balance ÷
  auctions left × pot ÷ mean remaining pot. A pot-only bid was within 0.6 share points of a hand-scaled one. Guessing
  the auction count 2× too high cost 3-8 share points of 25; 2× too low cost 1-4. A seat that busts at half-table
  wastes 550-777 chips.
- *What it reveals:* if bids scale with the bidder's own hand, the winner is the weaker hand (no pair 86% of the
  time, base rate 63%; equity 23.7% before the card, 48.2% after).
- *Mistakes:* the first budget model paced by auctions played and ran dry mid-table (seen only in the price by third
  of the table); the notes' pacing formula was coded first and underspends about 3×.
- *For Sunday's theory agent:* a sealed auction in a second currency. At once run a 5,000-deals-per-class pilot of
  three cases on the same deal (I get the prize, the opponent gets it, nobody): that is the fallback inside 4
  minutes. Then 169 × 100,000 (84 s on one worker) and 12,000 flop spots × 600 samples (25 s). Report win minus
  lose. Check that the coin-flip mean is 50.0 and that get + give = 100. Then build a budget model in numpy: about 40
  auctions, 2-4 bidders, pots rising over the table, busts; pace by table time; sweep the pacing multiplier from 1 to
  12 before comparing policies; print prices by third of the table and chips left. First build: bid 3 × balance ÷
  auctions left × pot ÷ mean remaining pot, 0.4 of that with two pair or better, never more than the richest rival's
  balance + 1. Read who pays in the rules first: at Boston every bidder paid on the chosen cards, and this multiplier
  does not apply there.

**Changes to the recipe in §4** (they apply when the twist changes how many hole cards there are or how the pot is paid):
1. *Step 1, add:* how the pot is paid and whether the value adds across parts; for an auction, the currency, who
   pays, what is public afterwards and the tie rule.
2. *Step 2:* 169 classes hold only for two hole cards. Three cards: 1,755 classes at 4,000 deals. Four cards: sampled
   hands and a regression. A deal cost 9-57 µs, not 2.2-4.4.
3. *Step 4:* state the fallback table's error per class, not on average (classes moved 3.5 points while group means
   moved 0.5). A rule that adds scores across boards needs an equity-like scale.
4. *Step 5:* 0.1 points was not reachable with a deterministic rule for a late discard or an allocation. Use two
   stops: the bot's choice under 0.15 (100 shared samples did it), the table's shared rule under 0.5 with no class off
   by more than 2 in the nested run.
5. *Step 6:* make the nested re-run paired, over 150+ classes, and read per-class z-scores first.
6. *Auctions:* the equity tables hold no decision (three cases on one deal); the decision is the bid, studied in a
   separate budget model.
7. *One worker:* analyse what is on disk before queueing the next run.

## Corrections for TWIST_NOTES and theory.md

All 13 were applied to both files on 14 November: nothing below is waiting to be done. They stay here because
`TWIST_NOTES.md` points to them by number (T2's rule is item 3).

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
   suit, then the higher card." (A flop rule, two cards to come: it did not carry over to a turn draw in the 14 November
   timed run. Label it so wherever it is quoted.)
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

**Drill 4, Pittsburgh's variant (a subagent; T0 06:30:11; one worker; rules page rebuilt from participants' READMEs,
with the default discard and the odd-chip rule assumed).**
- Timings: design and library 2.8 min; checks 0.03; discard study (6,000 spots × 600 samples) 0.9; fallback ranking
  0.5 (at 5.1); a rejected rule revision 0.8; main ranking 2.4; nested check 1.4 (table wrongly called trusted at
  10.7); exact check of 80 spots 1.4; second nested check 4.1 (leak found at 17.4); rule revision 1.2; rerun 2.5;
  third nested check 1.5 (trusted at 22.6). About 15 minutes without the detours.
- Samples: 1,755 classes × 4,000 deals, SE 0.43-0.57; two boards minus one board, paired SE 0.26.
- Results beyond §5: best discard is the lowest card 52.8%, the middle 24.9%, the highest 22.3%; the top two options
  are within 3 points in 27% of spots. Against one board: trips +1.7, JJ+ with a kicker +1.0, pairs 22-77 −1.4.
  A three-subset model (0.705 × best + 0.251 × worst two-card hold'em equity) explains 95.5% of the variance. Bands:
  a 50-55 hand scoops 25.1% and wins nothing 20.7%; 65+ scoops 52.2%; under 40 scoops 11.6%. With the default
  discard the boards are positively correlated (51.6 against 48.5).
- Went wrong: the early "trusted" call; draw bonuses that made the rule worse (1.02 against 0.68); a false alarm on
  12 exact spots (1.2 min); the one-worker limit broken twice for seconds; a format-string crash.
- Checks: evaluator on 40 spots, 0 mismatches; AsAh vs KdKc 81.255, AsKs vs QdQc 46.214; mean share 49.994; weights
  22,100; 19.4 million deals asserted (distinct cards, shares sum to 1), 0 failures; exact against sampled on 80
  spots, mean difference 0.13 ± 0.13.
- Unverified: 22-55 with a J+ kicker still understated by 1.00 ± 0.11; the shared rule loses 0.42; ranges, 8 players,
  betting; the two assumed rules.

**Drill 5, split hands (a subagent; T0 06:30:32; one worker; our mock).**
- Timings: design and library 3.5 min; score table and scripts 0.9; pilots 0.4; first study and ranking 2.0
  (fallback assignment table at 6.9); second rule 0.8; second chain 2.4; analysis and a false alarm 1.3; fallback
  ranking read at 12.0; third rule 0.4; third chain 3.7 (trusted at 16.4).
- Samples: 4,000 spots × 600 shared samples; 2,500 hands × 500 deals (per-hand SE 1.46); head-to-head 400,000 deals.
- Results beyond §5: the default scores 37.3 ± 0.2 against a rule player; rule versions lose 0.49-0.70, 0.33-0.54,
  0.26-0.45 (split-half to in-sample); "maximise the weaker board" loses 2.59 ± 0.08; SD of share 0.333; a seat
  stuck on the default is identified in two showdowns; six to eight separate "balance" from "concentrate".
- Went wrong: see §5; also a hold'em reference run reused a seed, so its repeat was not independent.
- Checks: evaluator over all 21 subsets, 0 mismatches (passing all four hole cards changes the value in 82% of
  deals); rule against itself 50.01 ± 0.12; six option shares 15.7-17.2%; 11 million samples asserted, 0 failures;
  rule unchanged by card, flop and board order on 20,000 spots.
- Unverified: ranges, betting after the assignment, four or more players, a mixed equilibrium, rare classes (trips
  n = 20), the bot interface.

**Drill 6, card auction (a subagent; T0 06:51:09; one worker; our mock).**
- Timings: reading, design and library 1.9 min; checks 0.05; flop study 0.6; idle 1.1; pilot 0.08 (fallback at 4.1);
  ranking 1.4 (trusted at 6.0); first budget model 0.3; reveal study 0.95; second budget model 0.55; sweep 0.25;
  assembly 2.0 (everything at 11.8).
- Samples: 12,000 flop spots × 600 (SE of the mean 0.07); 169 classes × 100,000 (SE 0.16); budget model 3,000 tables
  per cell (SE 0.56 share points).
- Results beyond §5: value quartiles 29.8 / 34.8 / 38.2; a 15-term rule has error 2.3; hurt most when the opponent
  gets the card: ace-high offsuit (A9o −20.5). Threshold bidding scored 16-24 against 25 at parity, hoarding 24.0,
  "just above the richest rival" 18.0; capping at the richest rival + 1 moved shares by at most 0.2.
- Budget model assumptions (all unverified): 40 auctions per table; 2, 3 or 4 bidders with chances 0.6 / 0.3 / 0.1;
  pots rising 8× over the table; one survivor, the rest busting at a uniform time; values independent across bidders;
  value linear in chips; nobody learns from prices. The 3-4 multiplier held at 20 and 80 auctions and 2× pot growth.
- Went wrong: see §5; also an integer overflow crash, and a symmetry "check" that was true by construction.
- Checks: evaluator on 6,060 comparisons and 2,020 eight-card hands, 0 mismatches; coin-flip mean 50.005; get + give
  100.008; 26.1 million deals asserted; one exact flop spot within 0.08; a second seed on 18 classes, largest z 2.03.
  All passed first time and caught nothing; no errors were planted.
- Unverified: how many auctions a seat reaches, how the field bids, opponents with ranges, betting after the card
  (only the winner knows it, so its real value is probably higher).
