# Immediate handoff: three-card discard/reveal poker bot

This is a compact implementation brief. The accompanying 11,000-word research memorandum contains derivations, sources, and caveats. It is a proposed strategy, not a benchmarked bot or solved equilibrium.

## Ship this first

1. Explicitly handle `state.phase == "select"`. Choose `(discard_index, reveal_index)` in ORIGINAL dealing order, distinct integers 0-2; amount zero. Default `(2,0)` on selection failure.
2. Compare all three retained pairs using made strength plus calibrated draw/nut potential. Do not compare raw eval7 integer gaps as equity gaps. Do not evaluate all three hole cards as legal retained cards.
3. Initially reveal either retained card with probability 1/2. Deterministic lowest-card reveal leaks a hidden-card rank constraint. A directional reveal bias should be a later tested adjustment.
4. Build a known-unavailable-card mask: all THREE of hero's initial cards, board, and ALL publicly exposed cards, including folded players. Unknown discards are latent, not known.
5. After selection, represent each opponent by their exposed card plus a weighted distribution over ONE hidden card. Start broad; adjust for retention, revelation, and action history with strong shrinkage.
6. Use a small distribution over legal check/fold, call, small raise, large raise, and jam. Deduplicate sizes after legal mapping. Mix chiefly between plausible near-tied choices.
7. Optimize expected points as well as chips; use actual `state.config.payouts`. ICM matters most around large late-stage commitments. Heads-up ICM is linear in chips for fixed two-place prizes.
8. Upload and verify the intended bot is ACTIVE before the snapshot. Guide says accepted uploads normally auto-activate; format text differs, so inspect status.

## Exact formulas under stated assumptions

Let P be CURRENT pot including opponent's bet, C incremental call cost, B a new bet when no bet is faced. These formulas assume a simple pot, no further betting, and the indicated opponent range.

- Terminal call chip EV: `e*(P+C)-C`; call threshold `C/(P+C)`.
- Heads-up bet EV ignoring raises: `f*P+(1-f)*(e_called*(P+2*B)-B)`.
- Pure bluff break-even fold probability: `B/(P+B)`.
- Compare betting with checking value, not merely with zero.
- In an ideal polarized heads-up river model, bluff FRACTION among bets is `B/(P+2*B)`; bluff:VALUE ratio is `B/(P+B)`. These are not universal per-hand bluff probabilities.
- Multiway all-fold probability is approximately PRODUCT of seat fold probabilities, not their mean. Do not assign fold probability to an all-in opponent.
- ICM all-in threshold ignoring ties: `(U_fold-U_lose)/(U_win-U_lose)`, with utilities evaluated on complete correct stack vectors.

Use equity against CALLING ranges for called branches. Nonterminal calls require a continuation/realization approximation. Handle side pots and unmatched refunds before applying simple formulas.

## A fast action distribution

Score a few legal candidate actions in consistent units. Use baseline-weighted softmax:

`p(a) proportional to baseline_p(a) * exp((Q(a)-max_Q)/temperature)`.

Mask illegal and clearly inferior actions first. Subtract max Q for numerical stability. An alternative is piecewise-linear probability ramps around call/raise thresholds. Random noise alone does not prevent exploitation or create a good poker strategy.

Keep only about 10-15 tunable controls: preflop participation/raise thresholds, third-card bonus, multiway adjustment, flop/turn realization, river bluff-catching, small/large sizing, bluff intensity, selection draw weight, reveal bias, ICM pressure, exploitation strength, and mixing width. Tune a subset at a time.

## Runtime: new guide contains crucial constraints

- Default allowance: 1 ms. UPLOAD TEST HAS NO TIME BANK. Local `play` always has a 100 ms bank, so a locally passing bot can still fail upload.
- The host clock includes delivery. Benchmark full feature/memory/action path, p99 and maximum, on the supplied EC2 build box. No unmeasured promise that N eval7 calls fit.
- `self` and mutable globals cannot reliably store table state. Any worker can answer any table. State travels in returned memory bytes, default maximum 64 KB; aim for a few KB.
- Load immutable models/tables and warm prediction at import. No lazy JIT in `act`; no background computation between decisions.
- Read-only non-executable upload directory; custom uploaded compiled extensions cannot run. Installed approved native packages remain available. No network/GPU.
- Set required numerical library thread limits before imports. Forked worker behavior must be tested, especially ONNX/Numba pools.
- On timeout/exception, old memory is retained and events repeat. On illegal action, returned memory is stored. Decode defensively and make updates retry-safe.
- Raise API is `Action.raise_to(total_current_street_contribution)`, NOT raise-by. Use `state.can("raise")` bounds, integer amounts, and final legality checks.
- Check and call are never simultaneously offered; folding is not offered when checking is free.
- Limits: 50 MB uploaded, 200 MB unpacked, 1,000 entries, 1 MB agent.py. Keep training tools outside the packed bot directory; even unused imports of local-only poker_engine/pokerkit in any packaged Python file cause rejection.

## Fast learning

Within a table, keep Beta counts for fold-to-bet in coarse contexts. Update only genuine opportunities, not checks or already-folded/all-in seats. Prior strength around 10 observations is a starting hypothesis, not a fact about the field. Shrink seat estimates toward population priors. Calls and raises deserve separate counters when possible.

Between uploads, stream a subset of hand logs; diagnose failures before strategy. Use eight-seat paired local tournaments, same seeds and varied opponents. The three-folder example is only three-handed, where all default places pay. Preserve a champion and test one or two parameter families at a time. Aggregate official scores do not identify an action-level gradient, and changing opponents confound comparisons across rounds.

Scored starts are at elapsed build minutes 60, 80, 100, 120, 140, 160. Results may arrive too late for the next start. Later weights matter: final three rounds carry 15/21 of total weight. Avoid missing early rounds while pursuing a large solver.

## Highest-risk mathematical bugs

- Choosing a flop discard using a sampled realized turn/river: clairvoyant teacher. Fix pair choice using flop-only expectations, then score runouts.
- Multiplying heads-up equities: generally invalid multiway; shared cards and ties matter.
- Sequential weighted sampling without replacement: order-dependent approximate joint range, not exact product-conditioned sampling.
- Tiny Monte Carlo treated as precise: 64 independent share samples have worst-case SE 6.25 percentage points, before model error.
- Ignoring selection bias: exposed card was chosen, hidden card was retained, and showdowns are a selected sample.
- Treating unknown discards as exchangeable without labeling the approximation; selection can correlate them with future-board availability.
- Treating a positive chip-EV all-in as necessarily positive tournament-points EV.

## Validation gate

Test all six selection actions; own discard removal; exposed folded-card removal; ties and board-only hands; short all-ins; closed raising; duplicate size mapping; malformed/truncated memory; replayed events; ten-player state; long event batches; cold worker calls; eight-seat long runs; no-bank upload validation. Confirm actual active version. This brief does not claim any measured strategy or latency improvement.
