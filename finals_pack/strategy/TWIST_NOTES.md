<!-- Prepared 2026-11-12 by a research agent from the three mock rules pages and general poker knowledge.
Knowledge, not code: the one-line tests describe checks for the coding agent to write. Items marked
[unsure] are judgement calls. Give this file to the coding agent at minute 0, with the kit's RULES.md. In this
setup the coding agent is `platform` (BUILDER); `theory`, `stylist` and `challenger` read it too. -->

# Finals twist notes for the coding agent

## 0. Techniques used everywhere below
- **Common random numbers (CRN).** When comparing options (which card to discard, keep, kill or bid on), score every option against the same sampled opponent hands and runouts. Comparing differences this way has far less noise than sampling each option separately. If an option changes which cards are live (for example a draw), shuffle the live deck once and give each option the next cards in that order, skipping any card that clashes with it.
- **Monte Carlo noise.** With N samples the standard error of an equity is about 0.5/√N: 0.035 at N=200 and 0.05 at N=100. Treat options closer than about 3–5% as ties. Break ties with simple rules or at random, never by over-reading the noise.
- **Measuring the best option.** To measure what the best option is worth, choose it on half the samples and score it on the other half: the maximum of several noisy estimates overstates it. Break exact ties at random, then check that option shares are symmetric (a first-index tie-break put 30% of votes on index 0 instead of 25% [drill]).
- **Offline tables for a payoff twist** (one that changes what a pot is worth, not who wins it): 1,000,000 deals per class, counting outcomes keyed by the bonus condition in one loop, so every state comes from the same deals.
- **[drill]** marks a figure measured on 14 November in a timed drill: heads-up, all-in before the flop, against a random hand. It is not general. **[drill, model]** is weaker: a small budget model with unverified assumptions. Detail: `notes/pre/variants.md`.

## 1. Nineteen plausible twists

**T1. Face-up discard from three cards (exchange + reveal).** You get 3 hole cards. After preflop betting, each player throws 1 face up before the flop. The thrown card is dead.
- Value: only 3 options, so use CRN Monte Carlo over 2-card keeps (about 150 shared runouts against weighted ranges, with every exposed discard removed). Fastest acceptable shortcut: pick the keep with the highest score in a 169-class preflop equity table built during the hour.
- Classic mistake: keeping the two highest cards. Suitedness, pairs and connectedness matter. Another mistake: treating an opponent's discard as only a dead card. They kept the two cards they liked more, so a discarded K moves their range up.
- Preflop: about 17% of 3-card hands contain a pair (vs 5.9% of 2-card hands). Rank a 3-card hand by its best 2-card subset and open tighter, about as if one extra opponent were at the table [unsure of the size; check by Monte Carlo].
- Leak: your discard reveals a floor on what you kept. Randomising isn't worth the equity it costs.

**T2. Paid flop draw (exchange + payoff).** After the flop, each player may pay a fee F to throw one hole card face up and draw a private replacement. Choices are locked at the same time.
- Value: 3 options (keep, throw 0, throw 1) with CRN: one sample holds the opponent's hand, turn, river and both replacements. Draw if Δequity × (pot + expected future bets) > F. A free draw is worth 8.4 points over always keeping [drill].
- In the bot use a rule, not sampling [drill: the rule loses 0.065 points, Monte Carlo at N=200 0.10 in 0.5 ms]. Rule: `notes/pre/variants.md`, Corrections item 3. It is a flop rule (two cards to come): for a draw on another street or at another price wait for `theory`'s rule. On a free turn draw in a 14 November run, "keep two-card open-enders" and "keep pocket pairs" were wrong, and a card with a one-card draw was kept ahead of a higher card.
- Classic mistakes: computing equity against random hands instead of the stronger range that played preflop; letting the replacement be an exposed or dead card; conditioning on other players' throws, which aren't visible when you choose.
- Preflop [drill]: 22–66 lose 9.5 points and 59 places; suited connectors lose 1.8 and 19 places. Open fewer of both.
- Leak: the thrown card tells others what you don't hold. Keeping with air costs 17 points [drill].

**T3. Public draft (ordering + reveal).** After preflop betting, k+1 cards (k = players left) are dealt face up. In a fixed order, each player takes one as a public third hole card. Showdown uses the best 5 of 8 cards.
- Value: at most 9 candidates. With CRN (about 60 runouts each), score each as (your equity if you take it) minus (equity of the strongest opponent if they take it). Denying a card counts.
- Classic mistakes: (a) `eval7.evaluate` takes 5 to 9 cards and returns the best five (checked 14 November on 2,000 random 8-card hands), so pass all 8; (b) a drafted card must be placed in that opponent's simulated hand and removed from the deck, and must not also be sampled as one of their two private cards.
- Preflop: hands become more alike and pots more multiway. Value suited and connected hands a little higher.
- Leak: your pick is public and shows what you want. Pick the denial card when the equity gap is within noise.

**T4. Show one (reveal).** After the flop, each player must expose one of their two hole cards. Choices are locked before any card is shown.
- Value: your choice does not change your equity. It only changes what opponents infer. Model a revealed opponent as that card plus one unknown card. With one unknown card per opponent, river equity is an exact enumeration of about 44 hands. On the flop or turn, use N≈200.
- Classic mistake: removing the revealed card from the deck but still sampling two unknown cards for that opponent. That double-counts it and throws away the information.
- Preflop: about unchanged. Pairs and suited connectors hide their strength better [unsure]. Keep standard ranges.
- Leak: this is the whole twist. Usually show the card that doesn't connect with the board, but randomise (about 70/30) so the hidden card isn't always the strong one [unsure; there is no clean solution].

**T5. Paid peek (information).** After the flop, a player may pay P chips into the pot to privately see one hole card of a chosen opponent. Who peeked at whom is public.
- Value: an exact value of information is too slow for 1 ms. Use a heuristic: peek only heads-up or three-way, when P is below about 5–10% of the pot and your equity is in the marginal band (0.35–0.65) [unsure thresholds]. After a peek, condition that opponent exactly as in T4.
- Classic mistake: treating the peeked card as dead but leaving it out of the target's simulated hand.
- Preflop: no change.
- Leak: peeking shows you face a close decision. If you are peeked, assume the peeker knows your stronger card.

**T6. Sealed auction for a third hole card (auction).** After the flop, one extra card is shown. Players submit sealed bids in poker chips. The winner pays into the pot and adds the card as a public third hole card.
- Value: with CRN, compute your equity with the card (Eq_me) and your equity if the strongest opponent gets it (Eq_opp). The card is worth (Eq_me − Eq_opp) × final pot. For an unseen card on the flop that is 33 points of pot, twice "with minus without" [drill].
- Classic mistakes: assuming the card stays neutral if you lose the auction (it goes to an opponent); forgetting that a bid paid into the pot partly comes back to you when you win, so the effective cost is bid × (1 − your share).
- Preflop: little change for a shown card. For an unseen one, pairs lose 4.8 points, 87s–54s gain 2.7–5.4 [drill].
- Leak: bid size reveals how well the card fits your hand. Shade first-price bids and add ±20% noise. An unseen card tends to go to the weaker hand [drill].

**T7. Position auction in a separate currency (ordering).** Using non-replenishing "position chips" (like flop-chips), players bid each hand to act last postflop.
- Value: pace the budget by table time. If every bidder pays, bid about balance ÷ (expected hands you will contest at this table) × pot-size factor. If only the winner pays, that spends under half the balance: bid about 3 × balance ÷ auctions left × pot ÷ mean remaining pot [drill, model]. Bid more with playable, position-dependent hands. What position is worth in chips is [unsure]; start at about 5–10% of the pot.
- Classic mistakes: spending everything early, or hoarding to the end of the table where the balance is worth nothing (guessing too many auctions cost more than guessing too few [drill, model]). Reading your own balance instead of the per-seat balances.
- Preflop: suited connectors and other position-dependent hands can be opened wider from early seats when you can afford to buy position.
- Leak: a big bid signals you plan to continue. Add noise.

**T8. River chosen by auction (board manipulation).** After turn betting, two river candidates A and B are shown. The highest sealed bidder (separate currency) picks the river. The other card is dead.
- Value: there are only 2 boards. For each one, the full board is known, so equity is a comparison against sampled opponent combos (about 200 shared). The value of winning is about pot × |Eq_A − Eq_B|.
- Classic mistakes: leaving the unchosen candidate in a deck that is no longer dealt from; treating the winner's choice as uninformative. The winner picked the river that helps them, so keep only opponent hands for which that river is at least as good as the other.
- Preflop: draws gain a little.
- Leak: a high bid shows your hand depends on the river. Add noise.

**T9. Kill vote on a 4-card flop (board manipulation).** Four flop cards are dealt. Each player secretly votes one card to kill; ties go to the lower index; votes are public afterwards.
- Value: 4 options. With CRN (about 60 shared samples), compute equity on each resulting 3-card flop. Your vote matters only when it is pivotal, and the tie-break decides when. Heads-up with ties to the lower index, the killed card is the lower-indexed of the two votes: score vote i as the average over the opponent's likely votes j of your equity after killing card min(i, j). Against a sincere voter this gained 1.85 ± 0.04 points [drill]. With more voters, count the pivotal cases the same way.
- Classic mistakes: leaving the killed card in the deck; ignoring the revealed votes. An opponent voting to kill a card shows it helped you or hurt them, so down-weight hands that card would have helped.
- Preflop: small changes [drill]: pairs lose 1.7 points, low suited connectors gain 2–3.
- Leak: votes are public. Randomise among options within noise.

**T10. Personal river (board manipulation).** Two river cards are shown. Before river betting, each player secretly commits to one for their own hand; choices are revealed at showdown.
- Value: picking the card that gives you the highest hand rank is a dominant strategy. You win against any fixed opponent hand exactly when your rank is higher, and opponents' choices don't depend on yours. One evaluation per card. No Monte Carlo needed.
- Classic mistake: evaluating opponents with a single river. Each opponent's strength is max(eval(hand + board + A), eval(hand + board + B)), and turn equity must model the same max for everyone.
- Preflop: draws and suited connectors gain (every player gets two river outs); pairs lose slightly.
- Leak: nothing until showdown, so don't randomise.

**T11. Hi/lo declare (payoff).** Before showdown, each player secretly declares high, low or both. Half the pot goes to the best high among high declarers, half to the best low among low declarers. "Both" must win both halves. The low rules (A-5, 8-or-better) come from the spec.
- Value: sample opponent combos (about 200) and assume each opponent declares their better side. EV(side) = ½ pot × P(win that side). Declare "both" only when P(scoop) is high.
- Classic mistake: deriving low strength by inverting the high evaluator. A-5 low ignores straights and flushes and counts the ace as low, so write a separate low evaluator and unit-test it. Also: if nobody declares low, high usually takes the whole pot [check spec].
- Preflop: aces and wheel cards (A2, A3, suited) gain a lot; middle cards (9–J) lose. Shift opens toward A-small.
- Leak: declarations are simultaneous. Randomise only when the two sides' EVs are close.

**T12. All-in cash-out (payoff).** When all-in before the river, a player may accept a guaranteed c × (equity against the actual hands) × pot instead of the runout, with c≈0.95.
- Value: in raw chips you always decline when c<1. Accept only if the ICM value of the cash-out > eq × ICM(win) + (1−eq) × ICM(lose). If the offer is quoted, your exact equity is the offer ÷ (c × pot). Malmuth-Harville ICM for 50/30/20 with 8 players needs 8×7×6 = 336 orderings: cheap for our own share only. In a timed build a full-table calculation took about 0.3 ms and three per all-in gave 0.9 ms decisions, so compute our own equity only, once per outcome, or read `theory`'s thresholds.
- Classic mistake: deciding by raw chip EV only, or accepting every offer.
- Preflop: near the bubble, all-in calls become slightly better for short stacks.
- Leak: accept/decline is public and minor.

**T13. Auction over board cards (auction, separate currency).** Tested on a mock flop auction: players bid a
separate currency on candidate flop cards, and the result picks the flop.
- Value: score every possible board outcome on the same sampled opponent hands and runouts, then bid on the
  cards of the best outcome. Size bids from the budget: balance / auctions expected to remain, scaled by how
  much the outcomes differ and by the pot. Cap bids relative to the richest live opponent's balance.
- Measured: never bidding scored 14.5 points per table; a cheap rule 17.7; simulated bidding 20.6-22.1;
  points rose with thinking time (0.1 ms 18.6, 0.6 ms 20.4). A budget 3x too large fell back to 18.8.
- Classic mistakes: tuning the budget only against bad bidders; crediting a balance drop to the wrong hand
  (when we folded preflop); leaving the unchosen cards in the deck.
- Preflop: controlling the board devalues pocket pairs (22 ranked 118th of 169) and raises high cards.
- Always simulate the twist's preflop effect: in three mock variants, pairs lost value in two of them.

**T14. Two boards, split pot (payoff; Pittsburgh's regional: three hole cards, discard after the turn).** Two boards are dealt; the same hole cards play on both, and each board pays half the pot.
- Value: your share is the mean of the two board equities, so score each board on its own river and add. The best discard beats the default by 10.8 points and "keep the two highest" by 6.0. In the bot, 100 shared samples lose 0.13 in 0.6 ms [drill].
- Split pot [drill]: scoop 23.5%, one board each 47.9%, nothing 23.5%. Pot odds use expected share, but an all-in busts only by losing both boards: an ICM call needing 1.5 to 1 needs a 55 share, not 60.
- Classic mistakes: one card dealt to both boards; pot odds from "win probability"; a keep chosen for one board only; summing raw evaluator values over the boards (mis-keeps small pairs).
- Preflop [drill]: table the 1,755 three-card classes. Ranking by the best two hold'em cards moves 23% of hands 10+ percentiles (trips −7.8 points, pairs 22–77 −4.1).
- Detail: `notes/pre/variants.md` §5.

**T15. Bounty on pots won (payoff).** Each player has a private bounty rank. A pot won with that rank in the winner's hole cards or on the board pays a bonus of b × the chips won (drill: b = 0.5).
- Value: equity × M, with M = 1 + b × P(hit | I win). Rank in hand or on the board: M = 1 + b. Otherwise the hit chance is 1 − C(unseen − 4, k)/C(unseen, k): 35.3% preflop to river, 16.5% from the flop. Call when equity ≥ price ÷ M: with the bounty hit, a pot-size call needs 22.2%.
- Classic mistakes: equity × (1 + b × hit chance), because hitting and winning are negatively correlated when the rank isn't in hand (M = 1.165, not 1.1765 [drill]); the bonus counted on a fold-out before the rank shows; opponents whose bounty is hit call wider.
- Preflop: hand order moves at most 2 places [drill].
- Leak: a bonus paid without a showdown shows the winner's rank is in their hand or on that board.

**T16. Involuntary swaps (exchange with no decision; MIT 2022).** Each hole card may be swapped at random for a deck card before the flop and before the turn.
- Value: simulate the swap chances inside every runout; equity becomes a mix of the current hand and a random one. There is no option to value.
- Classic mistakes: paying for hole-card strength (pairs, kickers) that may be swapped away; a swapped-out card left live when the rules make it dead [check spec].
- Preflop: the ranking flattens as the swap chance rises [unsure of size; simulate].
- Detail: `notes/pre/variants.md` §3.

**T17. Extra or variable board cards (board; MIT 2023: river cards keep coming until a black one).**
- Value: simulate the stopping rule in every runout. `eval7.evaluate` takes up to 9 cards; a longer board needs the best over subsets.
- Classic mistakes: fixed five-card runouts; a river equity treated as final when more cards may come.
- Preflop: flushes, straights and full houses inflate and one pair falls, so suited and connected hands gain [unsure of size; simulate].
- Detail: `notes/pre/variants.md` §3.

**T18. Pass a card (exchange + reveal; the 14 November speedrun's mock).** After the flop each player passes one hole card face down to the player on their left.
- Value: 2 options with CRN. The card you pass is live in your neighbour's hand and known to you; the card you receive is sampled from the passer's rule.
- Measured in the speedrun (heads-up): a good pass rule beat the default pass by 13.3 points of equity; pocket pairs ranked 157th–169th of 169 and ace-low hands best.
- Classic mistakes: the passed card dealt again from the deck (it happened heads-up); assuming `state.cards` keeps its order (after the pass: kept card, then received).
- Leak: what you pass tells the receiver what you didn't want, and what you receive tells you the same about the passer.

**T19. Split hands (allocation; a mock in the organizers' style).** Four hole cards and two boards; after the flops each player secretly assigns two cards to each board (six options). Each board pays half the pot.
- Value: share is the mean of the two board equities, so score the six two-card subsets on each flop and take the best sum: +12.9 points over the default [drill]. Score against the cards an opponent puts on that board, not a random hand (worth 0.27 [drill]). A 12-lookup table rule loses 0.26–0.45 [drill]. Three-way, lean to the strongest single board.
- Classic mistakes: giving eval7 all four hole cards; keeping suited cards together (right 40% of the time; pocket pairs 90%) [drill]; pot odds from win probability.
- Preflop [drill]: hold'em ranks fail (best two-card subset errs by 3.2 points). Fit a regression on sampled hands (error 0.6); trips are worth 8 less.
- Leak: assignments show at showdown; a seat stuck on the default is identified in two. Detail: `notes/pre/variants.md` §5.

## 2. First 15 minutes: checklist for the coding agent

1. Read the rules page end to end. Write down: the phase name (`state.phase`), the action kind, the meaning of `cards` (indices or card values, and in what order), whether `amount` must be 0, `max_amount`, the new `state.variant` keys, and the failure default.
2. Grep the kit for the phase string, `Action(`, `legal` and `variant[`. Check the template's fallback for unknown phases. In the mocks, empty `cards` explicitly requests the default.
3. Write the legal default first: `if state.phase == NEW: return Action(KIND, cards=DEFAULT), memory`. It must come before the betting code. Wrap the whole `act()` in try/except that returns the phase default, or check/fold when betting. Never let the new phase fall into betting logic.
4. Run the kit's local runner for a few hundred hands. Confirm zero automatic or default actions in the histories.
5. Test the edge cases:
   - All-in players still get the phase, with stack 0. Guard against dividing by zero and against requiring legal bets.
   - Heads-up (the pass mock becomes a straight swap).
   - Folded players never get the phase.
   - The phase is skipped when everyone folds. Don't assume it happens every hand.
   - Send a deliberately invalid action and confirm the server applies the default without folding.
   - Hands that are all in before the phase (runouts pause).
6. Card bookkeeping. Rebuild each decision from `state`, not from accumulated events:
   - `mine`: current `state.cards` after the phase; the order can change.
   - `board`.
   - `dead`: exposed and out of play (thrown cards, unselected cards).
   - `known[seat]`: exposed or passed cards that are still live in that seat's hand.
   - deck = 52 − mine − board − dead − all known cards.
   - Each opponent's sampled hand = known[seat] plus (2 − len(known[seat])) cards drawn from the deck.
   - Reset everything for each hand (key it by hand id).
7. Equity routine: `equity(mine, board, known_by_opp, dead, n_unknown_opps, deadline)`.
   - Build eval7 Card objects and integer lookups for all 52 cards at import time.
   - Loop to an iteration count, with a `perf_counter()` deadline as the backstop (it should not fire on an idle machine, so the same deal gives the same decision). Betting decisions: 0.15-0.2 ms. A twist decision whose failure default is cheap may use up to 0.5 ms while the time bank is healthy; measure points against compute time, and use the bank only in emergencies.
   - Weight opponents with simple rejection sampling from a preflop range (for example, a raiser holds the top 30% by the precomputed table).
8. Performance: time 1,000 evaluations at import. Measured on the team laptop on 14 November: 550–675 plain heads-up samples per ms with eval7 (about 400 when three options share each sample) and 0.32 µs per 7-card evaluation; expect about 50–100 in pure Python [unsure]. Their hardware is unknown: measure. Divide by the number of opponents. Build the preflop 169-class equity table (by number of opponents) during the hour with an offline script and paste it in as a literal; don't compute it at import.
9. Per-table memory: store only small counts (VPIP, aggression, twist-choice frequencies per seat), never hand histories.
10. Use the twist in betting decisions only after the default bot is legal and tested.

## 3. Six silent bugs, each with a one-line test

1. **Index or order confusion.** The action takes an index but the bot sends a card (or the reverse), or `state.cards` changed order after the phase (pass mock: kept card then received; draw mock: the replacement takes the thrown card's place). Test: `assert state.cards[idx] == intended_card` before returning, plus a 1,000-hand simulation asserting zero `automatic` entries.
2. **Deck partition errors**, where a dead or known card is either missing from all sets or counted twice. Test: `assert len(deck)+len(mine)+len(board)+len(dead)+sum(map(len, known.values())) == 52 and len(set().union(deck, mine, board, dead, *known.values())) == 52`.
3. **Known opponent card ignored**, meaning both of an opponent's cards are sampled even though one is known. Test: with `known[s] = {As}`, assert every sampled hand for seat s contains As and that As never appears in a runout.
4. **Evaluator misuse**: more hole cards passed than the rules let play (eval7 takes 5 to 9 cards and uses any of them), the wrong comparison direction (eval7: higher is better), or a reused high evaluator for lows. Test: `assert ev(royal) > ev(one_pair) and ev(cards8) == max(ev(c) for c in combinations(cards8, 7))`, plus `low(A2345) beats low(A2346)`.
5. **Worst-case time blow-up**: options × samples × opponents in an 8-way pot, or an all-in-only path that throws an exception. Test: time the twist decision with 7 opponents and the maximum number of options over 1,000 calls, and assert the 99th percentile is under 0.8 ms and there are zero exceptions with stacks at 0.
6. **Bonus accounting** (payoff twists). A bonus credited when its condition hasn't shown by the end of the hand, or to a loser, or on the whole pot in a split. Test: on 40,000 random deals `assert paid == pot + bonuses`, and assert every bonus goes to a winner whose condition is met.
