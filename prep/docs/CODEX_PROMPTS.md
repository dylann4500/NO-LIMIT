# Event-day prompts for Codex / Astra

These rebuild the design from a blank repo using only the starter kit, so the plan still works if prepared code is ruled out. Paste them in order and fill in the `<...>` values from the kickoff announcement. Review every diff: rule 7.4 makes you responsible for AI-generated code.

---

## P0: read the kit (Person A, minute 0)

```
Read this starter kit in full. Do not write code yet. Report exactly:
1. The Agent method(s) called, their signatures, when each is called, and whether a new instance is made per table.
2. Every field the observation gives, its type and units. Answer these specifically:
   - Card encoding.
   - Is a raise amount "raise to" or "raise by"? Is it per street or per hand?
   - Does "stack" include chips already bet this street?
   - How do folded or eliminated seats appear?
   - Is there an action history? Does it include streets, opponents' actions and showdown cards?
   - Does the bot get called for hands it is not in?
3. The exact legal-action format, minimum raise rule and all-in format, and what happens on an illegal action.
4. The variant's rule changes versus standard no-limit hold'em: deck, hole cards, board, ranking, betting limits, antes, bounties, and anything else.
5. The points table and blind schedule, verbatim.
6. How the 1 ms limit is measured, if the kit shows it. Is import or __init__ timed? Which Python version and packages are available?
7. What the local simulator can do and how fast it runs. Its speed decides whether we need our own engine.
```

## P1: safe bot, submitted by minute 15 (Person A)

```
Write bot.py implementing the kit's Agent. Standard library only unless the kit documents otherwise.
Requirements, in priority order:
1. It can never raise an exception to the platform. Wrap the whole decision in try/except and fall back to check, else fold.
2. All actions are clamped to legal bounds.
3. Everything is computed at import. At the end of import run gc.collect(); gc.freeze(); gc.disable(). Make one warm-up decision.
4. Policy for now, with `pct` = fraction of starting hands at least as strong as ours (0 is best):
   - Nobody has raised: open to 2.3 big blinds if pct < 0.15 + 0.55/(players_left_to_act + 0.5). Heads-up, use pct < 0.89.
   - Stack under 12 big blinds, nobody raised: all-in if pct < 0.73 * W * (1 + 0.045*(6.7 - M)), where M = effective stack/(sb+bb)
     and W by players left to act is [1, .69, .44, .34, .27, .22, .20, .18]. Heads-up, use at least pct < 0.85.
   - Facing an all-in: call only if pct < 0.05, wider heads-up (pct < 0.3).
   - Facing a raise, not all-in: 3-bet pct < 0.03, call pct < 0.10, otherwise fold.
   - Postflop: use a placeholder of made-hand category from the kit's evaluator, and call only with a pair or better.
Add test_bot.py that fuzzes the decision with 100,000 random legal and malformed states and prints illegal-action count and p50, p99, p99.9 and max latency.
```

## P2: variant tables (Person B, minute 5)

```
Using the kit's hand evaluator and the variant's deck, hole-card count and board, write build_tables.py (multiprocessing, about 30-60 seconds):
1. Group starting hands into canonical classes: sort by rank, relabel suits by first appearance.
2. For each class, Monte Carlo equity vs. 1 and vs. 2 random hands (4000 rollouts for 2-card hands, 300 or more for 4-card hands).
3. Score = 0.6*eq1 + 0.8*eq2. Output a table class -> percentile, weighted by the number of combos in each class, plus eq1.
4. Print the top 20 classes and bottom 5 so a human can sanity-check them against the variant.
Save as a Python literal or JSON loaded at import. Then build the postflop table in P3.
```

## P3: small strength model (Person B, minute 20)

```
Write strength.py. feature(hole, board) returns a small tuple:
street; made-hand category; for one pair: overpair / top pair with good or weak kicker / second / lower / board pair;
for high card: ace-high or overcard; for better hands, whether the hole cards are actually used;
flush draw flag; straight draw (0 none, 1 gutshot, 2 open-ended); board paired flag; board suitedness (0-2).
Offline: sample 150,000 random hole/board states. For each, Monte Carlo equity vs. villain drawn from the top [8%, 20%, 40%, 100%] of starting hands using the percentile table.
Average per feature cell, keeping cell counts, and save the result. table_equity(hole, board, width) interpolates between widths and backs off from rare cells.
Lookup must take under 15 microseconds. Report mean absolute error vs. 400-rollout Monte Carlo. Adapt the features if the variant changes what strong hands look like.
```

## P4: fast engine + field + tuner (Person B, minute 25, only if the kit simulator is too slow)

```
Write engine.py: an 8-seat sit-and-go with exactly the kit's rules and blind schedule, and a points function using the kit's ICM. Target over 10,000 hands/s per core in pure Python.
Validate against the kit simulator: same seed or same hands where possible, chip conservation every hand, and agreement of average finishing points on a shared bot within noise.
Write field.py with these opponents as simple classes:
fold-only; random; calling station; maniac; all-in top 20%; all-in top 8%; tight-aggressive chart; nit; loose-aggressive; Monte Carlo pot-odds; tight-then-jam-under-15BB.
Mix weights are guesses, so define four mixes: typical, strong, aggressive, passive.
Write tune.py: cross-entropy method over all policy parameters. Population 40, 8 elites, 8-12 generations.
Fitness is the mean z-score across (field mix, points table) cells over 60 tables per cell, with common seeds across candidates.
Include copies of our current bot as opponents in two of the mixes (one with mostly copies, one with all copies), because tuning only against weak bots left the policy exploitable in our tests. Refresh the copies after each promoted tune.
Also write a holdout field of five different opponents never used in tuning, and only promote parameters that win on the holdout.
A first tune of 3-8 generations is enough: most of the gain arrived by generation 3 in testing.
```

## P5: policy (Person A, minute 25)

```
Refactor the policy so it depends on the variant only through pct(hole) and eq(hole, board, range_width). All thresholds live in one PARAMS dict. Add:
- Villain range width from the action: 0.82 unraised; 0.12 vs a bet; 0.16 vs a raise. Multiply by (1 + 0.27*(8 - players_alive)/6), then by clamp(villain_vpip/0.3, 0.7, 2.2). These are starting values only; tune them.
- Multiway: eq = eq ** (1 + 0.65*(min(opponents,4) - 1)).
- Checked to us: bet 0.60 pot if eq > 0.69 (all-in if stack/pot < 2.4). Heads-up with no bet: bluff half pot 27% of the time.
- Facing a bet: raise if eq > 0.84 (all-in if stack/pot < 2), call if eq > pot_odds + 0.14, plus 0.11 more when 4 or fewer players are alive.
- Per-seat VPIP, smoothed: (vpip + 3)/(hands + 10). Derive it from the observation or history. Every update must be O(1).
- Do not add an exact ICM price on calls unless the points table is close to flat. In our tests it lost points on top-heavy tables.
```

## P6: between-rounds review (minutes 60-160)

```
Here are the leaderboard scores for our bot and others for the last round: <paste>, and any logs: <paste>.
Our recent submissions and their parameters: <paste>.
Tell me what changed, what the scores can and cannot show given noise of about <SE> points, and propose at most one change.
Do not propose anything that needs new untested code in the last 10 minutes before a freeze.
```

---

## Working with Codex under time pressure

These come from community guides and our own judgment, not official OpenAI documentation. Check `codex --help` tonight for what your version supports.

- **Parallelism:** run separate sessions or git worktrees, one task each, and say explicitly that tasks are independent. Person A and Person B should not share a working tree.
- **Project rules:** put a short `AGENTS.md` in the repo with the hard constraints: stdlib only, 1 ms, never raise, legal clamps, run `test_bot.py` before reporting done.
- **Network:** community guides report that network is off by default in the workspace-write sandbox. Test tonight whether your setup needs anything from the network.
- **Verify tool output:** make Codex run things and paste measured numbers. Don't accept a claim that something works without output.
- **Don't let a long tune block you:** run it in another terminal and keep working.

"Astra" is named in rule 3.4 without definition. Our literature pass found OpenAI's "GPT-6 Astra" and took that to be what's meant, but we couldn't open that page to confirm it directly. Ask at check-in if it matters.
