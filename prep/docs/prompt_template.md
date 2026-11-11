# No Limit pokerbot build document

**For:** the two of us and Claude Code, during the event. Paste Part A into Claude first. Every other part is a reference or a prompt to paste when the timeline reaches it.

**What this contains:** the plan, tested settings, prompts, and the full source code as extractable blocks. To rebuild the entire workspace:

```bash
# Save this document as BUILD_PROMPT.md, then copy the extractor from Part H into extract.py
python3 extract.py BUILD_PROMPT.md .
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python numpy   # numpy is for local tuning only, never in the bot
```

**How much to trust the numbers:** all scores come from our simulator against bots we wrote. The variant, later blind levels and real field are unknown until kickoff. Trust direction more than size. "gym" means the placeholder points table 100/60/40/25/15/10/5/0 used in Part B, where a fair share is 31.9. The real default is 50/30/20, where a fair share is 12.5. "Holdout" and "stress" fields were never seen by the tuner.

**Portal facts override this document:** `docs/event_portal.md` has the real API and format. Under the real format (20-hand levels, 250-hand cap, 50/30/20, placeholder blinds after 10/20, ±0.36), the final bot scored typical 29.84, holdout 27.06, stress 26.00, against 29.80, 25.83, 23.92 for the blend bot.

---

# Part A: paste this into Claude first

```
We are competing in a live pokerbot tournament. You are helping two teammates under a hard clock. Be fast, concrete, and honest about what you have and have not verified.

FORMAT
- 148 teams. 60 minutes to build a Python bot implementing Agent.act(state, memory). A starter kit gives an agent template, local simulator, ICM calculator, RULES.md and hand-history reader. docs/event_portal.md has the full API.
- The poker variant is revealed at the start of the build.
- Each decision has 1 ms, then a 100 ms per-table bank; a timeout empties the bank. The upload test match has no bank. Error, timeout or illegal action means check, else fold. Upload limit 50 MB, 1 MB of code in agent.py. No network.
- One upload per 30 seconds. Confirm "Active bot" on the team page after every upload. Practice rounds of about 1,000 tables run every 10 minutes during the build.
- Six scored rounds, T1 at minute 60 then every 20 minutes. Each round snapshots the active bot when it starts. Final score = 1*T1 + 2*T2 + ... + 6*T6, so T4-T6 are 71%.
- At least 5,000 eight-bot sit-and-gos per round, random tables. 2,000 chips, blinds start 10/20 and rise every 20 hands, up to 250 hands. Default points 50/30/20; ICM splits remaining points at the hand cap. A round may change these, so read state.config.
- Per-table state lives only in memory, starting at b"" each table. self and globals are unreliable, and carrying information between tables breaks the rules. Hand histories with opponents named are downloadable after each round. Collusion, copying another team's code and platform abuse mean disqualification.

DESIGN (already tested; do not redesign without evidence)
- Small rule-based policy with about 30 thresholds in one dict. It touches the variant only through pct(hole) and eq(hole, board, range_width).
- One adapter file is the only code that knows the kit's API.
- Tune with CMA-ES on a field of weak bots, copies of ourselves and exploiters. Promote only if it wins on opponents the tuner never saw.
- Do not build transformers, deep networks or CFR during the event. Do not add features because they sound good.

SAFETY (never skip)
- Never raise out of the decision function. Wrap everything; fall back to check, else fold.
- Return only offered kinds, and integer raise totals inside min_amount..max_amount: the platform does not clamp. Keep the bot stdlib only unless a measured gain justifies a package from requirements.txt.
- Build tables at import; end import with gc.collect(); gc.freeze(); gc.disable().
- Nothing gets submitted without passing the gate: 0 errors, 0 illegal actions, p99.9 well under 1 ms.

KNOWN TRAPS
1. macOS multiprocessing spawn re-executes the main module in every worker. Top-level os.environ changes in a driver script silently overwrite what you set later. Keep them inside functions or __main__.
2. Do not wait on pgrep of a script name: a monitor containing that text matches itself and stalls forever. Wait on marker files.
3. Unpaired comparisons at 3,000 tables have about ±1 standard error per difference on the 100-point table. A +1.8 once reversed to -1.8. Use 6,000+ tables or more fields before believing a small gain.
4. Compare tuned against tuned. An unequal comparison once made a lookup look equal to Monte Carlo.
5. An adapter bug can lose points without crashing. Check parity, not just the absence of errors.
6. Do not spend evidence on features: exact ICM pricing, chip-leader widening, chart overrides and mid-table parameter switching all failed tests here.
7. The generated Policy keeps per-seat stats on self. In production any copy may answer any table, so those stats must round-trip through memory. A bot that keeps them on self passes local tests and silently plays with wrong reads.
8. After a timeout or exception the previous memory is kept and events are delivered again. Update stats only from the memory you return, so nothing is double-counted.

WORKING STYLE
Do one task at a time, run it, and paste measured numbers. Say "not verified" when true. Keep the last known-good bot file. Never touch submissions in the final 3 minutes before a freeze unless asked.
```

---

# Part B: what we tested and decided

**The decision:** rule-based policy + CMA-ES + exploiter-hardened field. Final parameters are `lab/tuned_final.json`.

## Tuners (same budget, cold start, 3 seeds)

Mean gym score over holdout and stress fields.

| Tuner | 13k tables | 40k tables | Time for 40k (10 cores) |
|---|---|---|---|
| **CMA-ES** | **51.6** | **53.3** | about 55 s |
| Successive halving | 47.8 | 48.3 | about 63 s |
| SPSA | 46.9 | 47.5 | about 150 s |
| Paired (1+λ) | 45.3 | 46.9 | about 100 s |
| CEM | 44.0 | 45.8 | about 45 s |

**Use CMA-ES.** All three seeds were ahead of CEM's at 13k tables, and it was far ahead at 40k.

## Policy families (each tuned, then scored on unseen fields; gym, ±0.6)

| Family | Holdout | Stress mix | Verdict |
|---|---|---|---|
| Rule + thresholds (blend tune) | 53.9 | 51.7 | The base design |
| Thresholds by street and heads-up | 55.0 | 53.6 | Slight gain at most; not worth the parameters |
| Explicit EV + per-seat fold rates | 54.5 | 56.9 | Promising on stress, not on others; don't build first |
| Linear residual on the rule | 55.3 | 52.4 | Within noise |
| Linear from scratch (70 weights) | 39.5 | 38.2 | Weak generally, but a strong exploiter (below) |
| Tabular Q overrides, cautious | 54.1 | 52.9 | Within noise |
| Tabular Q overrides, bold | 45.7 | 49.6 | Worse |
| Switching parameter sets mid-table | 50.7-52.0 | 49.1-51.5 | Worse |
| Exact heads-up Nash chart added | about -2 | about -2 | Loses exploitation of weak bots |

## Robustness: the finding that changed the design

An exploiter trained for 3.5 minutes scored **83.5** at a table of seven blend bots (fair 31.9). It raised small with almost anything, because tuned bots over-folded. None of our hand-written opponents showed this.

Loop: train exploiter → add to field → retune defender → repeat. Exploiter score by round: 83.5, 53.2, 64.8, **44.9**, so improvement is real but not smooth. The hardened bot lost little or nothing elsewhere:

| Field (gym, ±0.5) | Blend | Final (robust3) |
|---|---|---|
| Holdout | 54.8 | **58.2** |
| Stress mix | 52.1 | **55.9** |
| 3-bet stress | 50.4 | **55.9** |
| Run-over field | 48.0 | **50.5** |
| Typical | 64.5 | 64.8 |
| Strong | 60.4 | 60.0 |
| Soft holdout | 63.5 | 62.7 |
| Table of blend copies | 32.8 | 30.4 |

## Round-to-round protocol (simulated T1-T6 with an improving field; weighted score, 2 seeds)

| Protocol | Weighted score |
|---|---|
| Refresh: tune against latest self + exploiters each round | **52.85** |
| League of all past versions | 52.69 |
| Refresh with holdout gate | 52.32 |
| Tune mostly on last round's field | 51.44 |
| Frozen | 51.06 |

Retuning is worth about 1.5-2 points; the top three are within noise. **Use refresh with a gate, because the gate guards against shipping a bad tune.** Don't over-fit to the last round's field.

## Postflop equity source (equal tuning, top3 table, ±0.4)

| Field | Lookup | MC 15 | MC 40 |
|---|---|---|---|
| Holdout | 24.09 | 25.31 | 25.05 |
| Stress mix | 23.60 | 24.65 | 25.60 |
| Typical | 29.96 | 31.02 | 30.81 |

**Start on the lookup** (about 7 µs, near-zero timeout risk). **Upgrade to MC if practice rounds show low timeouts.** In Omaha the lookup wins: 22.8 vs. 19.2 for the 8 rollouts that fit in 1 ms.

## What each piece is worth (top3, tuned-bot baseline, ±0.28, four fields)

| Change | Effect |
|---|---|
| Jam from 45 BB | -3.8 to -5.6 |
| 5 MC rollouts | -2.2 to -2.9 |
| No opponent stats | -0.4 to -2.1 |
| No close-spot margin | +0.1 to -1.9 |
| Any one threshold ±40% | About 1 point at most, near noise |

So don't hand-tweak single thresholds. Structure and running a tune matter.

## External benchmarks

- **Slumbot** (heads-up, 200 BB): -84 ± 34 bb/100 for blend; -36 ± 28 with heads-up defense. Always folding is -75. Treat it as a leak finder only: the difference isn't significant, and the gain came from small-blind hands the fix didn't touch. It exposed a real issue: 73% big-blind folds to opens. The bot was never tuned for 200 BB.
- **Nash jam-or-fold chart** (heads-up): the blend won 44.8% at 6 BB, 51.9% at 10 BB, 52.8% at 15 BB, and 74.5% at 20 BB, where the chart isn't a sensible strategy. It solves in about 30 s.
- **Chart-style bots:** a rigid chart bot from memory lost clearly to the final bot (49.2 at a table of them; `tag` 33.2). Book charts weren't tested.
- **Always all-in:** averages 6-8 points at tables of ours. Heads-up, the final bot wins about 52%, and a price-based call applies only to seats raising most hands.

## Heads-up matchups for the final bot (match win %, ±1.7)

| all-in | jam 20% | jam 8% | maniac | min-raiser | random | tag | nit | pot-sizer | short-stack |
|---|---|---|---|---|---|---|---|---|---|
| 52 | 94.6 | 100 | 67 | 79 | 80 | 88.8 | 95.6 | 83.8 | 89.4 |

Weakest spots: all-in and maniac. Worth watching if logs show those opponents reach heads-up against us often.

---

# Part C: timeline

| Minute | Person A: bot and platform | Person B: lab |
|---|---|---|
| Before kickoff | Extract workspace; run C0. | Same on the second laptop. |
| 0-5 | C1: read the kit. Find the submission path. | Copy points, blinds and variant into `lab/event_config.json`. |
| 5-15 | C2: adapter + reference bot. **Submit.** Confirm accepted. | C3: variant tables if needed; sanity-check the top hands. |
| 15-30 | Fix anything the first practice round shows. | C4: engine parity vs. the kit's simulator. |
| 30-45 | Submit the variant-aware bot if the gate passes. | C5: first real tune. |
| 45-55 | Merge. Gate. **Submit.** | C6: exploiter round if time. |
| 55-60 | Hands off. Confirm the active bot for T1. | Keep tuning for T2. |
| 60-160 | C7: review each round. Own submissions. | C8: refresh tune each round. |

**Plug in both laptops and close other apps.** Tuning and latency tests both depend on it. **One person owns submission.** Submit at least 3 minutes before each freeze and confirm it was accepted.

## C0: setup check (before kickoff)

```
Run lab/test_engine.py and report whether all checks pass. Then run:
  ./make_submission.sh lab/tuned_final.json lookup '[50,30,20,0,0,0,0,0]'
Report import time, fuzz results and latency. Confirm the submission/bot.py file exists. Do not change anything else.
```

## C1: read the kit (Person A, minute 0)

```
Read this starter kit in full. Don't write code yet. Report exactly:
1. The Agent method(s), signatures, when each is called, and whether there's a new instance per table.
2. Every observation field, its type and units. Specifically:
   - Card encoding.
   - Is a raise amount "raise to" or "raise by"? Per street or per hand?
   - Does "stack" include chips already bet this street?
   - How do folded or eliminated seats appear?
   - Is there action history? Streets, opponents' actions, actions after our fold, showdown cards?
   - Is the bot called for hands it isn't in?
3. Legal-action format, minimum raise, all-in format, and what happens on an illegal action.
4. Every rule change vs. standard no-limit hold'em: deck, hole cards, board, ranking, betting limits, antes, bounties, anything else.
5. Points table and blind schedule, verbatim. Write them to lab/event_config.json as
   {"blinds": [[10,20],...], "points": [...], "hands_per_level": 20, "max_hands": 250, "start": 2000}.
   The committed lab/event_config.json has every portal default except "blinds". Add the kit's schedule, and correct anything the kit changes.
6. How the 1 ms limit is measured, if shown. Is import or __init__ timed? Which Python and packages are available?
7. What the local simulator does, and how many hands per second it runs.
List anything ambiguous so we can ask a Gamemaster.
```

## C2: adapter and first submission (Person A, minute 5)

```
Generate the bot:
  ./make_submission.sh lab/tuned_final.json lookup '<points JSON>'
Then write lab/adapter.py containing only the kit's Agent class and the translation code. It's appended to the generated bot on every regeneration, and can use Policy, State and FOLD/CALL directly. Don't change the policy. Read docs/event_portal.md first. The API there was written before the kit shipped; if they differ, the kit wins.
Requirements for act(self, state, memory):
- Rebuild per-table Policy stats from memory on every call. Never keep per-table data on self or in globals. Use a compact format, stay well under 16 KB, and treat any parse failure as empty memory.
- Process state.events in order: Policy.observe per fold/check/call/raise, Policy.end_hand at each hand boundary. Return the updated memory with the action.
- Read blinds, payouts and hand cap from state.config at runtime. Don't trust the values baked into the file.
- Translate: (0,0) to Action.fold(), or Action.check() if fold isn't offered; (1,0) to Action.check() or Action.call(), whichever is offered; (2,to) to Action.raise_to(int(to)), clamped to min_amount..max_amount, falling back to call or check if raising isn't offered.
- Unknown phase or kind: take the automatic choice, first = state.legal_actions[0]; Action(first.kind, first.min_amount).
- The final try/except returns a legal action and the incoming memory unchanged.
- Upload as agent.py: copy submission/bot.py to a directory holding only the bot, then run poker-agent pack on it. It must not import poker_engine or pokerkit.
- Run one complete act on a synthetic state at import, then gc.freeze. Measure act with memory parsing included, on the build box, and report p99 and max.
For each decision, build a ref State with these exact meanings, deriving what the kit doesn't provide:
  seat; hole and board as ints (rank*4 + suit, 2=0 .. A=12); street (0-3); pot (all chips committed this hand);
  to_call; cur (highest street bet to match); stack (excluding this street's bet); bet (our street bet);
  sb; bb; stacks and bets lists by seat; in_hand list; n_alive (seats dealt in); n_live (not folded);
  n_behind (active seats still to act); raises (raises this street); aggressor (last raiser seat or -1);
  n_callers; min_raise_to and max_raise_to as total street amounts; can_raise.
Traps: max(bets) isn't always the amount to call, because a short big blind still sets the full amount; use state.to_call. raise_to and raise events are totals for the betting round; call events are chips added.
Feed Policy.observe(seat, street, kind) once per public action (0 fold, 1 check/call, 2 raise), and call Policy.end_hand() between hands.
rehearsal/solution/adapted_bot.py is a worked example for a different API. Use it as a pattern.
Test through the kit's simulator with 100+ tables. Report errors, illegal actions, latency, and score against the kit's baseline bots.
Print a sample of 10 decisions with all State fields so a human can compare them to the true game state.
```

## C3: variant tables (Person B, minute 5)

For a variant already supported (`holdem`, `shortdeck`, `flushfh`, `hole3`, `omaha`):

```bash
cd lab
export POKER_VARIANT=<name>
../.venv/bin/python build_tables.py                       # 1-65 s
../.venv/bin/python strength.py 150000 24 10              # 5-35 s; for omaha use 40000 12 10
../.venv/bin/python make_bot.py tuned_final.json ../submission/bot.py lookup '<points JSON>'
../.venv/bin/python test_bot.py ../submission
```

For anything else:

```
The variant is: <rules>. Update lab/pk.py to support it in the variant layer: DECK, N_HOLE, showdown(), and canon() if needed. Mirror each change in the TEMPLATE in lab/make_bot.py (showdown, made_hand, canon, feature), and update lab/strength.py's feature() if the changes affect what strong hands look like.
If the variant has a decision the policy doesn't cover (discard, auction, bounty), add one simple decision for it with a single tunable parameter, and leave all else as is.
Then build tables, print the top 20 and bottom 5 hand classes, and run test_bot.py and test_parity.py. Report anything that looks wrong for this variant. Don't start tuning yet.
```

## C4: engine parity (Person B, minute 15)

```
Compare lab/engine.py with the kit's simulator using these rules: <paste>. Check blinds, button movement after busts, heads-up order, minimum raises, side pots, same-hand elimination ordering, ICM at the cap, and points. Then run the same bot (lab reference bot, adapted) for 2,000 tables on both against a fixed mix of simple bots, and report mean points with standard errors. If they differ by more than about 3 standard errors, find out why and fix lab/engine.py to match the kit. List any rule difference that remains.
```

## C5: tune (Person B, minute 25-30)

```bash
cd lab
../.venv/bin/python tune_event.py --base tuned_final.json --out tuned_T0.json --tables 40000            # warm
../.venv/bin/python tune_event.py --base tuned_final.json --out tuned_T0.json --tables 80000 --sigma 0.2 # variant changed a lot
```

The script prints a verdict from unseen fields, and exits nonzero if the new parameters lose. Then gate it:

```bash
cd .. && ./make_submission.sh lab/tuned_T0.json lookup '<points JSON>'
```

`lab/adapter.py` is appended automatically, so your adapter survives regeneration. **Always test through the kit before submitting.**

## C6: exploiter round (Person B, once a good bot is live)

```bash
cd lab && ../.venv/bin/python exploit_loop.py --base tuned_T0.json --rounds 1 --tag ev1
```

About 5-8 minutes. It prints how exploitable the bot is, then writes hardened parameters and an exploiter that joins future tunes automatically. Promote only if the hardened bot holds up on the holdout. Exploiters from Part G are valid starting points, but on a new variant or points table they may be stale.

## C7: round review (Person A, after each round)

```
Here are the results for this round: <paste leaderboard and any logs>. Our recent submissions and settings: <paste>.
1. Any sign of technical failure on our side: timeouts, errors, illegal actions, adapter issues? Check this first.
2. Our rank and gap to the top teams, compared with last round. Estimate the noise on the 50/30/20 table from our simulator: about ±0.7 at 1,000 practice tables and ±0.3 at 5,000 scored tables. Use the real iteration count, and check the team page's decisions, missed decisions, restarts and error reports.
3. Download the smaller hand-history subset with the kit's streaming reader. Opponents are named there, so summarize by team: VPIP, raise rate, all-in rate, fold to raise, and who takes our chips. Weight by how often each opponent appears. Tell me which of our training fields most resembles it, and whether to change the field mix.
4. Propose at most ONE change. Say what evidence supports it and what would disprove it. Don't suggest untested logic within 10 minutes of a freeze.
```

## C8: between-round cycle (Person B, 20-minute rhythm)

1. **0-2 min:** read results; decide whether to change the field mix.
2. **2-12 min:** `tune_event.py --base <current>.json --out tuned_Tk.json --selfplay <current>.json --tables 60000`.
3. **12-15 min:** check the verdict. Run `make_submission.sh`. Test through the kit.
4. **15-17 min:** submit and confirm. **Latest safe time is 3 minutes before the freeze.**

If the verdict says keep the old bot, keep it. Retuning was worth only about 2 points in simulation, so a safe skipped round costs little and a broken bot costs a lot.

---

# Part D: variant response

**The safe bot ships first, whatever the variant.**

| Announced | Do | Watch for |
|---|---|---|
| Short deck | Rebuild tables, retune. | The lookup's error was highest here (10.5 points), so prefer MC if the host allows. A-6-7-8-9 straight and flush rank. Hold'em parameters transferred well in testing. |
| Re-ranked hands | Rebuild; usually minor. | Don't trust any hardcoded hand order. |
| 3 hole cards | Rebuild. Check whether a discard exists. | Lookup beat MC here (24.4 vs. 23.0). |
| Omaha | Rebuild: 65 s for `pct`, 35 s for lookup. Lookup only. | Must use exactly 2 hole cards. Generated bot caps rollouts at 6 for jam calls. Import is about 220 ms. |
| Discard or draw | Keep the hand with the best `pct`, or best equity on board. | See how the API exposes it. |
| Pot limit | Replace jams above the limit with max-legal raises. | Push-fold logic doesn't transfer. |
| Antes or straddles | Treat as a bigger pot; tune. | Whether `pot` includes them. |
| Bounties or custom points | Add bounty value to wins; tune on the real table. | Flat tables reward survival, top-heavy ones reward winning. |
| Hi-lo, multiple boards | Equity = expected pot share. | Rework lookup features. |
| Auction, blotto, mini-game | A simple separate decision with one parameter. | MIT's class uses twists like these. Don't let it eat the base bot's time. |
| Tighter time limit | Lookup only, and check import time. | Re-run the gate. |

---

# Part E: if something goes wrong

| Symptom | Check first |
|---|---|
| Very low score, no errors | Adapter: raise-by vs raise-to, stack including bets, card encoding. Print 10 decisions and compare by hand. |
| Local latency looks awful | Plug in and close other apps first. On battery, with other apps using full cores, p50 rose from about 3.5 to 12 µs and p99 to about 350 µs, purely from machine conditions. |
| Timeouts | Switch to lookup. Check for non-stdlib imports, per-table reloads and GC. Is the host slower? |
| Submission rejected | File path, entry point, size, imports. Test the kit's template first. |
| Worked yesterday, broke now | Roll back to the last known-good file immediately, then debug. |
| Tuner scores look wrong | Env variable set at module top level (trap 1). `all_mirror` self-play should score about fair share; if not, the engine or field is broken. |
| Good in lab, bad in practice | Lab field is wrong. Use logs to re-weight it and retune. Don't add features. |
| Tune loses on holdout | Keep the old bot. |
| Claude gets slow or stuck | The bot already submitted is fine. Do it by hand, or skip the round. |

---

# Part F: final parameters and tables

`lab/tuned_final.json`, the current best parameters. Thresholds are coupled, so don't read too much into any single one.

{{PARAMS_TABLE}}

**Starting-hand percentile (hold'em):** the fraction of hands at least as strong; lower is better. Suited above the diagonal, offsuit below.

{{PCT_GRID}}

**Heads-up jam-or-fold Nash, hold'em.** Use as a benchmark, not an override: bolting it on lost points against weak fields.

{{NASH_TABLE}}

---

# Part G: benchmarks and rehearsal

- `rehearsal/README.md`: a sealed 60-minute drill with an awkward mock API. Run it tonight.
- `benchmark/slumbot_client.py`: `python benchmark/slumbot_client.py <dir with bot.py> --hands 1500 --log out.jsonl`. One request at a time, heads-up 200 BB. Use it as a leak finder; ±30 bb/100 at this sample size means it can't rank similar bots. The bot directory must contain a generated bot.
- GTO Wizard's benchmark is stronger and less noisy, but needs an approved key from https://benchmark.gtowizard.com/.
- `lab/nash_hu.py`: solve jam-or-fold charts for the current variant in about 30 s.

---

# Part H: extractor and all source

Save this as `extract.py`, or paste it into a Python prompt:

```python
{{EXTRACTOR}}
```

{{FILES}}
