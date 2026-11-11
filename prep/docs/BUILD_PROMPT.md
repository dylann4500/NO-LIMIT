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

| Parameter | Value |
|---|---|
| `bet_frac` | 0.969 |
| `bluff_freq` | 0.1555 |
| `call_jam` | 0.09058 |
| `call_jam_short` | 0.04694 |
| `call_margin` | 0.1329 |
| `call_odds` | 0.01856 |
| `call_open` | 0.1075 |
| `commit_spr` | 1.947 |
| `eqcall` | 1 |
| `eqcall_margin` | 0.2 |
| `fourbet` | 0.01963 |
| `hu_defend` | 0.7281 |
| `hu_eqcall` | 1 |
| `hu_gate` | 0.45 |
| `hu_jam` | 0.4758 |
| `hu_margin` | 0 |
| `hu_open` | 0.941 |
| `hu_vwidth` | 1.5 |
| `icm_margin` | 0.1135 |
| `jam_m` | 7.571 |
| `jam_scale` | 1.281 |
| `jam_slope` | 0.1245 |
| `open_a` | 0.1523 |
| `open_b` | 0.7612 |
| `open_size` | 2.088 |
| `raise_eq` | 0.7805 |
| `range_bet` | 0.1114 |
| `range_raise` | 0.2561 |
| `range_unraised` | 0.5366 |
| `sh_range` | 0.9815 |
| `sh_widen` | 0.3079 |
| `steal_fold_bonus` | 0.7743 |
| `threebet` | 0.02297 |
| `threebet_mult` | 3.404 |
| `value_eq` | 0.685 |
| `vwidth_mult` | 0.4826 |
| `width_cap` | 6.746 |

**Starting-hand percentile (hold'em):** the fraction of hands at least as strong; lower is better. Suited above the diagonal, offsuit below.

| |A|K|Q|J|T|9|8|7|6|5|4|3|2|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|**A**|0.00|0.03|0.04|0.05|0.05|0.09|0.11|0.13|0.15|0.15|0.16|0.22|0.24|
|**K**|0.06|0.01|0.06|0.11|0.09|0.12|0.24|0.24|0.22|0.35|0.38|0.33|0.37|
|**Q**|0.05|0.10|0.01|0.12|0.13|0.21|0.26|0.34|0.35|0.45|0.43|0.41|0.47|
|**J**|0.08|0.14|0.19|0.02|0.18|0.24|0.33|0.37|0.46|0.51|0.54|0.56|0.52|
|**T**|0.09|0.17|0.21|0.28|0.02|0.29|0.37|0.43|0.47|0.59|0.64|0.64|0.70|
|**9**|0.13|0.20|0.30|0.35|0.36|0.03|0.39|0.46|0.54|0.62|0.67|0.73|0.68|
|**8**|0.17|0.27|0.39|0.40|0.48|0.53|0.03|0.46|0.54|0.62|0.73|0.79|0.80|
|**7**|0.22|0.31|0.44|0.49|0.54|0.59|0.61|0.07|0.57|0.65|0.67|0.79|0.86|
|**6**|0.25|0.41|0.42|0.60|0.65|0.69|0.76|0.71|0.11|0.63|0.72|0.84|0.88|
|**5**|0.23|0.43|0.55|0.63|0.70|0.79|0.77|0.75|0.78|0.15|0.73|0.77|0.83|
|**4**|0.29|0.46|0.57|0.66|0.72|0.89|0.86|0.85|0.83|0.89|0.26|0.82|0.93|
|**3**|0.32|0.51|0.62|0.68|0.81|0.84|0.92|0.96|0.94|0.91|0.92|0.37|0.90|
|**2**|0.33|0.50|0.58|0.74|0.82|0.87|0.95|0.97|0.98|0.95|1.00|0.99|0.50|

**Heads-up jam-or-fold Nash, hold'em.** Use as a benchmark, not an override: bolting it on lost points against weak fields.

| Stack (BB) | SB jams | BB calls |
|---|---|---|
| 1 | 100.0% | 100.0% |
| 1.5 | 98.2% | 100.0% |
| 2 | 89.6% | 100.0% |
| 2.5 | 82.1% | 100.0% |
| 3 | 78.6% | 91.9% |
| 3.5 | 75.6% | 82.5% |
| 4 | 74.0% | 74.1% |
| 5 | 71.8% | 62.1% |
| 6 | 68.5% | 54.9% |
| 7 | 66.4% | 49.0% |
| 8 | 63.0% | 45.0% |
| 9 | 60.8% | 40.6% |
| 10 | 59.0% | 37.5% |
| 12 | 53.0% | 33.3% |
| 14 | 48.6% | 29.6% |
| 16 | 44.7% | 26.8% |
| 18 | 42.7% | 24.1% |
| 20 | 40.0% | 21.7% |
| 25 | 35.4% | 17.4% |
| 30 | 31.8% | 14.5% |
| 40 | 24.9% | 11.0% |

Per-hand maximum depths are in `lab/nash_hu_holdem.json`.

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
#!/usr/bin/env python3
"""Rebuild the workspace from the prompt document. usage: python3 extract.py BUILD_PROMPT.md <target_dir>"""
import os, re, sys
doc, out = sys.argv[1], sys.argv[2]
text = open(doc, encoding="utf-8").read()
n = 0
for m in re.finditer(r"<!-- FILE: (\S+) -->\n````[a-z]*\n(.*?)\n````", text, flags=re.S):
    path = os.path.join(out, m.group(1))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(m.group(2) + "\n")
    if path.endswith(".sh"):
        os.chmod(path, 0o755)
    n += 1
print(f"wrote {n} files under {out}")
```

<!-- FILE: lab/event_config.json -->
````json
{"points": [50, 30, 20, 0, 0, 0, 0, 0], "hands_per_level": 20, "max_hands": 250, "start": 2000}
````

<!-- FILE: lab/pk.py -->
````python
"""Cards, fast pure-Python evaluator, Monte Carlo equity, preflop tables.

Cards are ints 0..51: rank = c >> 2 (0=2 .. 12=A), suit = c & 3.
Higher evaluator value = better hand.
"""
import json, os, random
from itertools import combinations

# Each card maps to: base-5 rank-count key (high bits) + 4-bit suit counters (low 16 bits).
_POW5 = [5 ** r for r in range(13)]
CARD_KEY = [(_POW5[c >> 2] << 16) + (1 << (4 * (c & 3))) for c in range(52)]
RANKBIT = [1 << (c >> 2) for c in range(52)]
_STRAIGHTS = [0b1111100000000 >> i for i in range(9)] + [0b1000000001111]  # A-high .. wheel


def _straight_high(mask):
    for i, s in enumerate(_STRAIGHTS):
        if mask & s == s:
            return 12 - i if i < 9 else 3
    return -1


_MASK_STRAIGHT = [_straight_high(m) for m in range(8192)]


def _top_bits(mask, n):
    out = 0
    for r in range(12, -1, -1):
        if mask >> r & 1:
            out = out * 13 + r
            n -= 1
            if n == 0:
                break
    while n > 0:
        out *= 13
        n -= 1
    return out


_FLUSH_VAL = [0] * 8192
for _m in range(8192):
    if bin(_m).count("1") >= 5:
        _s = _MASK_STRAIGHT[_m]
        _FLUSH_VAL[_m] = (8 << 20) + _s if _s >= 0 else (5 << 20) + _top_bits(_m, 5)


def _rank_value(key):
    """Value of a non-flush rank multiset encoded in base 5."""
    counts = [(key // _POW5[r]) % 5 for r in range(13)]
    mask = 0
    quads, trips, pairs = [], [], []
    for r in range(12, -1, -1):
        c = counts[r]
        if c:
            mask |= 1 << r
        if c == 4:
            quads.append(r)
        elif c == 3:
            trips.append(r)
        elif c == 2:
            pairs.append(r)
    if quads:
        k = _top_bits(mask & ~(1 << quads[0]), 1)
        return (7 << 20) + quads[0] * 13 + k
    if trips and (len(trips) > 1 or pairs):
        t = trips[0]
        p = max(trips[1:] + pairs)
        return (6 << 20) + t * 13 + p
    s = _MASK_STRAIGHT[mask]
    if s >= 0:
        return (4 << 20) + s
    if trips:
        return (3 << 20) + trips[0] * 169 + _top_bits(mask & ~(1 << trips[0]), 2)
    if len(pairs) >= 2:
        return (2 << 20) + pairs[0] * 169 + pairs[1] * 13 + _top_bits(mask & ~(1 << pairs[0]) & ~(1 << pairs[1]), 1)
    if pairs:
        return (1 << 20) + pairs[0] * 2197 + _top_bits(mask & ~(1 << pairs[0]), 3)
    return _top_bits(mask, 5)


_RANK_CACHE = {}


def evaluate(cards):
    """Evaluate 5-7 cards. About 1 microsecond on a modern laptop."""
    k = 0
    for c in cards:
        k += CARD_KEY[c]
    if (k + 0x3333) & 0x8888:
        low = k & 0xFFFF
        for s in range(4):
            if (low >> (4 * s)) & 15 >= 5:
                m = 0
                for c in cards:
                    if c & 3 == s:
                        m |= RANKBIT[c]
                return _FLUSH_VAL[m]
    rk = k >> 16
    v = _RANK_CACHE.get(rk)
    if v is None:
        v = _RANK_CACHE[rk] = _rank_value(rk)
    return v


def evaluate_omaha(hole, board):
    best = 0
    for h in combinations(hole, 2):
        for b in combinations(board, 3):
            v = evaluate(h + b)
            if v > best:
                best = v
    return best


def hand_class(a, b):
    """0..168 canonical index: pairs on diagonal, suited above, offsuit below."""
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return ra * 13 + rb
    return ra * 13 + rb if (a & 3) == (b & 3) else rb * 13 + ra


def class_name(idx):
    n = "23456789TJQKA"
    x, y = idx // 13, idx % 13
    if x == y:
        return n[x] * 2
    return n[x] + n[y] + "s" if x > y else n[y] + n[x] + "o"


# ---- variant layer (set POKER_VARIANT before import; subprocesses inherit it) --------------------
VARIANT = os.environ.get("POKER_VARIANT", "holdem")
TABLE_VARIANT = os.environ.get("POKER_TABLE_FROM", VARIANT)  # lets us test a stale table
N_HOLE = {"omaha": 4, "hole3": 3}.get(VARIANT, 2)
DECK = [c for c in range(52) if VARIANT != "shortdeck" or c >> 2 >= 4]
_SD_WHEEL = (1 << 12) | 0b11110000  # A + 6,7,8,9 with rank index 2=0


def _rerank(cards, wheel):
    """Flush beats full house; optionally the short-deck A-6-7-8-9 straight. Values are doubled."""
    v = evaluate(cards)
    c = v >> 20
    if c == 5:
        return v * 2 + (3 << 20)
    if wheel and c < 4:
        m = 0
        for x in cards:
            m |= RANKBIT[x]
        if m & _SD_WHEEL == _SD_WHEEL:
            return ((4 << 20) + 3) * 2
    return v * 2


if VARIANT == "shortdeck":
    def showdown(h, b):
        return _rerank(h + b, True)
elif VARIANT == "flushfh":
    def showdown(h, b):
        return _rerank(h + b, False)
elif VARIANT == "omaha":
    def showdown(h, b):
        return evaluate_omaha(h, b)
else:
    def showdown(h, b):
        return evaluate(h + b)


def canon(hole):
    """Canonical strategy class: ranks with suits relabelled in order of appearance."""
    cs = sorted(hole, key=lambda c: (-(c >> 2), c & 3))
    m, out = {}, []
    for c in cs:
        s = m.setdefault(c & 3, len(m))
        out.append((c >> 2) * 4 + s)
    return tuple(out)


_TABLE_PATH = os.path.join(os.path.dirname(__file__), f"table_{TABLE_VARIANT}.json")


def _mc_class(args):
    rep, rollouts, seed = args
    rng = random.Random(seed)
    rep = list(rep)
    rest = [c for c in DECK if c not in rep]
    w1 = w2 = 0.0
    for _ in range(rollouts):
        s = rng.sample(rest, 5 + 2 * N_HOLE)
        b = s[:5]
        me = showdown(rep, b)
        v1 = showdown(s[5 : 5 + N_HOLE], b)
        v2 = showdown(s[5 + N_HOLE : 5 + 2 * N_HOLE], b)
        if me > v1:
            w1 += 1
        elif me == v1:
            w1 += 0.5
        if me > v1 and me > v2:
            w2 += 1
        elif me >= v1 and me >= v2:
            w2 += 0.5
    return w1 / rollouts, w2 / rollouts


def build_table(rollouts=None, procs=10):
    """Full strategy table for the current variant. Returns seconds taken."""
    import time
    from multiprocessing import Pool
    t0 = time.time()
    if rollouts is None:
        rollouts = {2: 4000, 3: 1200, 4: 300}[N_HOLE]
    counts, rep = {}, {}
    for h in combinations(DECK, N_HOLE):
        k = canon(h)
        counts[k] = counts.get(k, 0) + 1
        rep.setdefault(k, h)
    keys = list(rep)
    with Pool(procs) as p:
        res = p.map(_mc_class, [(rep[k], rollouts, i) for i, k in enumerate(keys)], chunksize=32)
    score = {k: 0.6 * r[0] + 0.8 * r[1] for k, r in zip(keys, res)}
    order = sorted(keys, key=lambda k: -score[k])
    tot, cum, out = sum(counts.values()), 0, {}
    for k in order:
        cum += counts[k]
        i = keys.index(k) if False else None
        out[",".join(map(str, k))] = [round(cum / tot, 5)]
    eq = {k: r[0] for k, r in zip(keys, res)}
    for k in keys:
        out[",".join(map(str, k))].append(round(eq[k], 4))
    json.dump(out, open(_TABLE_PATH, "w"))
    return time.time() - t0, len(keys)


_T = None
_C = None
if os.path.exists(_TABLE_PATH):
    _T = {tuple(map(int, k.split(","))): v for k, v in json.load(open(_TABLE_PATH)).items()}


def _load_order():
    global COMBOS_SORTED
    def key(h):
        v = _T.get(canon(h))
        return v[0] if v else 1.0
    COMBOS_SORTED = sorted(combinations(DECK, N_HOLE), key=key)


COMBOS_SORTED = None
if _T is not None:
    _load_order()
_CACHE2 = {}


def pct(hole):
    """Fraction of starting hands at least this strong (0 best, 1 worst)."""
    if N_HOLE == 2:
        a, b = hole[0], hole[1]
        k = (a, b)
        v = _CACHE2.get(k)
        if v is None:
            e = _T.get(canon(hole))
            v = _CACHE2[k] = e[0] if e else 1.0
        return v
    e = _T.get(canon(hole))
    return e[0] if e else 1.0


def hu_eq(hole):
    e = _T.get(canon(hole))
    return e[1] if e else 0.5


def equity_vs_range(hole, board, width, rollouts, rng=random.random):
    """Heads-up equity vs. a villain drawn uniformly from the top `width` of starting hands."""
    combos = COMBOS_SORTED
    size = len(combos)
    k_limit = max(8, int(width * size))
    known = set(hole)
    known.update(board)
    nb = 5 - len(board)
    nd = len(DECK)
    deck = DECK
    wins = 0.0
    n = 0
    bl = list(board)
    sd = showdown
    for _ in range(rollouts):
        v = combos[int(rng() * k_limit)]
        bad = False
        for c in v:
            if c in known:
                bad = True
                break
        if bad:
            continue
        runout = bl
        if nb:
            runout = bl[:]
            while len(runout) < 5:
                c = deck[int(rng() * nd)]
                if c not in known and c not in v and c not in runout:
                    runout.append(c)
        n += 1
        v1 = sd(hole, runout)
        v2 = sd(list(v), runout)
        if v1 > v2:
            wins += 1
        elif v1 == v2:
            wins += 0.5
    return wins / n if n else 0.5


def icm(stacks, payouts):
    """Malmuth-Harville ICM. stacks: list of chips, payouts: list best-first. Returns expected points."""
    n = len(stacks)
    total = float(sum(stacks))
    if total <= 0:
        return [0.0] * n
    pay = list(payouts[:n]) + [0.0] * max(0, n - len(payouts))
    memo = {}

    def rec(mask, place, remain):
        # Returns expected payout vector for players in mask, given places `place..` remain.
        key = mask
        if key in memo:
            return memo[key]
        res = [0.0] * n
        if place >= n or remain <= 0:
            memo[key] = res
            return res
        for i in range(n):
            if mask >> i & 1 and stacks[i] > 0:
                p = stacks[i] / remain
                res[i] += p * pay[place]
                sub = rec(mask & ~(1 << i), place + 1, remain - stacks[i])
                for j in range(n):
                    res[j] += p * sub[j]
        memo[key] = res
        return res

    return rec((1 << n) - 1, 0, total)
````

<!-- FILE: lab/engine.py -->
````python
"""Eight-seat SNG engine following rules section 4: 2000 chips, 10/20, level every 25 hands,
200-hand cap, finishing-position points, ICM at the cap.

Bot API: bot.act(o) -> (0,0) fold | (1,0) check/call | (2,to) raise to `to` total this street.
Optional bot.observe(seat, street, kind, amount) for table events (kind: 0 fold, 1 call/check, 2 raise).
"""
import json, os, random
import pk
from pk import icm

FOLD, CALL, RAISE = 0, 1, 2

# Assumed: the real schedule ships with the starter kit. Swap at kickoff.
SCHEDULE_DEFAULT = [(10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500)]
HANDS_PER_LEVEL = 25
MAX_HANDS = 200
START = 2000
# event_config.json holds the real announced rules: {"blinds": [[10,20],...], "points": [...], "hands_per_level": 25, "max_hands": 200, "start": 2000}
_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "event_config.json")
EVENT = json.load(open(_CFG)) if os.path.exists(_CFG) else {}
if EVENT.get("blinds"):
    SCHEDULE_DEFAULT = [tuple(x) for x in EVENT["blinds"]]
HANDS_PER_LEVEL = EVENT.get("hands_per_level", HANDS_PER_LEVEL)
MAX_HANDS = EVENT.get("max_hands", MAX_HANDS)
START = EVENT.get("start", START)


class Obs:
    __slots__ = (
        "seat", "hole", "board", "street", "pot", "to_call", "min_raise_to", "max_raise_to", "can_raise",
        "stack", "bet", "cur", "sb", "bb", "hand_no", "button", "stacks", "bets", "in_hand", "allin",
        "n_alive", "n_live", "n_behind", "raises", "total_chips", "aggressor", "first_in", "n_callers",
    )


def play_table(bots, schedule=SCHEDULE_DEFAULT, rng=random):
    """Plays one table. Returns (finish_groups, hands, survivors) where finish_groups lists
    (list of seats, place index) as eliminated and survivors is the dict of live stacks at the end."""
    n = len(bots)
    stacks = [START] * n
    button = rng.randrange(n)
    eliminated = []  # list of lists of seats, in elimination order
    total = START * n
    deck = pk.DECK
    NH = pk.N_HOLE
    showdown = pk.showdown
    wants = [hasattr(b, "observe") for b in bots]
    o = Obs()
    o.total_chips = total
    hand_no = 0
    while hand_no < MAX_HANDS:
        alive = [i for i in range(n) if stacks[i] > 0]
        if len(alive) <= 1:
            break
        lvl = min(hand_no // HANDS_PER_LEVEL, len(schedule) - 1)
        sb, bb = schedule[lvl]
        # move button to next live seat
        button = (button + 1) % n
        while stacks[button] <= 0:
            button = (button + 1) % n
        bi = alive.index(button)
        rot = alive[bi:] + alive[:bi]  # button first
        m = len(rot)
        if m == 2:
            sb_seat, bb_seat = rot[0], rot[1]
            pre_order = [rot[0], rot[1]]
            post_order = [rot[1], rot[0]]
        else:
            sb_seat, bb_seat = rot[1], rot[2]
            pre_order = rot[3:] + rot[:3]
            post_order = rot[1:] + rot[:1]
        start_stack = stacks[:]
        cards = rng.sample(deck, 5 + NH * m)
        full_board = cards[:5]
        holes = {s: cards[5 + NH * j : 5 + NH * (j + 1)] for j, s in enumerate(rot)}
        in_hand = [stacks[i] > 0 for i in range(n)]
        bets = [0] * n
        contrib = [0] * n

        def post(s, a):
            a = min(a, stacks[s])
            stacks[s] -= a
            bets[s] += a
            contrib[s] += a

        post(sb_seat, sb)
        post(bb_seat, bb)
        live = m
        for street, nb in ((0, 0), (1, 3), (2, 4), (3, 5)):
            if live <= 1:
                break
            board = full_board[:nb]
            order = pre_order if street == 0 else post_order
            if street == 0:
                cur = bb
                last_raise = bb
            else:
                cur = 0
                last_raise = bb
                for i in range(n):
                    bets[i] = 0
                can_bet = sum(1 for s in order if in_hand[s] and stacks[s] > 0)
                if can_bet < 2:
                    continue
            raises = 0
            aggressor = -1
            to_act = len(order)
            idx = 0
            callers = 0
            first_in = True
            while to_act > 0 and live > 1:
                s = order[idx % len(order)]
                idx += 1
                to_act -= 1
                if not in_hand[s] or stacks[s] <= 0:
                    continue
                to_call = min(cur - bets[s], stacks[s])
                others = sum(1 for x in order if x != s and in_hand[x] and stacks[x] > 0)
                if to_call == 0 and others == 0:
                    continue
                o.seat = s
                o.hole = holes[s]
                o.board = board
                o.street = street
                o.pot = sum(contrib)
                o.to_call = to_call
                o.cur = cur
                o.stack = stacks[s]
                o.bet = bets[s]
                o.max_raise_to = bets[s] + stacks[s]
                o.min_raise_to = min(cur + last_raise, o.max_raise_to)
                o.can_raise = others > 0 and stacks[s] > to_call
                o.sb, o.bb = sb, bb
                o.hand_no = hand_no
                o.button = button
                o.stacks = stacks
                o.bets = bets
                o.in_hand = in_hand
                o.n_alive = m
                o.n_live = live
                o.raises = raises
                o.aggressor = aggressor
                o.first_in = first_in
                o.n_callers = callers
                # Number of active seats still to act after this one (includes re-acting aggressors).
                nbh = 0
                L = len(order)
                for j in range(idx, idx + to_act):
                    x = order[j % L]
                    if in_hand[x] and stacks[x] > 0:
                        nbh += 1
                o.n_behind = nbh
                try:
                    kind, amt = bots[s].act(o)
                except Exception:
                    kind, amt = (CALL, 0) if to_call == 0 else (FOLD, 0)
                if kind == FOLD and to_call == 0:
                    kind = CALL
                if kind == RAISE and not o.can_raise:
                    kind = CALL
                if kind == FOLD:
                    in_hand[s] = False
                    live -= 1
                    ev = (s, street, 0, 0)
                elif kind == CALL:
                    stacks[s] -= to_call
                    bets[s] += to_call
                    contrib[s] += to_call
                    if to_call > 0:
                        callers += 1
                    ev = (s, street, 1, to_call)
                else:
                    to = int(amt)
                    if to < o.min_raise_to:
                        to = o.min_raise_to
                    if to > o.max_raise_to:
                        to = o.max_raise_to
                    add = to - bets[s]
                    stacks[s] -= add
                    bets[s] = to
                    contrib[s] += add
                    if to - cur >= last_raise:
                        last_raise = to - cur
                    cur = max(cur, to)
                    raises += 1
                    aggressor = s
                    first_in = False
                    to_act = len(order) - 1
                    idx = idx  # continue ring from next seat
                    ev = (s, street, 2, to)
                for j in range(n):
                    if wants[j]:
                        bots[j].observe(*ev)
        # settle
        settle_contrib = contrib
        if live == 1:
            w = next(i for i in rot if in_hand[i])
            stacks[w] += sum(settle_contrib)
        else:
            vals = {}
            for s in rot:
                if in_hand[s]:
                    vals[s] = showdown(holes[s], full_board)
            remaining = settle_contrib[:]
            while True:
                pos = [c for c in remaining if c > 0]
                if not pos:
                    break
                lv = min(pos)
                pot = 0
                elig = []
                for i in range(n):
                    if remaining[i] > 0:
                        pot += lv
                        remaining[i] -= lv
                        if i in vals:
                            elig.append(i)
                if not elig:
                    # Dead money whose contributors all folded goes to the best live hand.
                    elig = list(vals)
                best = max(vals[i] for i in elig)
                winners = [i for i in elig if vals[i] == best]
                share = pot // len(winners)
                for w in winners:
                    stacks[w] += share
                for w in winners[: pot - share * len(winners)]:
                    stacks[w] += 1
        for b in bots:
            if hasattr(b, "hand_result"):
                b.hand_result(stacks, start_stack)
            if hasattr(b, "end_hand"):
                b.end_hand(hand_no)
        hand_no += 1
        busted = [i for i in alive if stacks[i] <= 0]
        if busted:
            # Bust order inside one hand: larger starting stack finishes higher.
            busted.sort(key=lambda i: start_stack[i])
            groups = {}
            for i in busted:
                groups.setdefault(start_stack[i], []).append(i)
            for k in sorted(groups):
                eliminated.append(groups[k])
    survivors = {i: stacks[i] for i in range(n) if stacks[i] > 0}
    return eliminated, hand_no, survivors


def points_for(eliminated, survivors, payouts, n=8):
    """Convert a table result to per-seat points. Ties split place points; survivors get ICM."""
    pts = [0.0] * n
    pay = list(payouts) + [0.0] * (n - len(payouts))
    place = n  # next place from the bottom (1-indexed count)
    for grp in eliminated:
        k = len(grp)
        slice_ = pay[place - k : place]
        val = sum(slice_) / k
        for s in grp:
            pts[s] = val
        place -= k
    seats = list(survivors)
    if len(seats) == 1:
        pts[seats[0]] = pay[0]
    elif seats:
        vals = icm([survivors[s] for s in seats], pay[: len(seats)])
        for s, v in zip(seats, vals):
            pts[s] = v
    return pts
````

<!-- FILE: lab/field.py -->
````python
"""Opponent archetypes: a guess at what a field of one-hour, AI-assisted bots looks like.
Nothing here is measured from the real field. Treat it as a stress test.
"""
import random
import pk
from pk import equity_vs_range

FOLD, CALL, RAISE = (0, 0), (1, 0), None
R = random.random


def pct(o):
    return pk.pct(o.hole)


def raise_to(o, x):
    return (2, int(x))


class FoldBot:
    """A crashing or timing-out bot: the platform auto-checks or folds for it."""
    def act(self, o):
        return CALL if o.to_call == 0 else FOLD


class RandomBot:
    def act(self, o):
        r = R()
        if r < 0.25 and o.to_call:
            return FOLD
        if r < 0.75 or not o.can_raise:
            return CALL
        return raise_to(o, o.min_raise_to + R() * (o.max_raise_to - o.min_raise_to) * 0.3)


class Station:
    """Rarely folds, rarely raises."""
    def __init__(self, width=0.6):
        self.width = width

    def act(self, o):
        if o.street == 0:
            if pct(o) < self.width or o.to_call == 0:
                return CALL
            return FOLD
        if o.to_call == 0:
            return CALL
        if o.to_call > o.pot * 1.2 and equity_vs_range(o.hole, o.board, 1.0, 12) < 0.55:
            return FOLD
        return CALL


class Maniac:
    """Huge raises and frequent all-ins."""
    def __init__(self, width=0.5, jam=0.2):
        self.width, self.jam = width, jam

    def act(self, o):
        if o.street == 0 and pct(o) > self.width:
            return CALL if o.to_call == 0 else FOLD
        if o.can_raise:
            if R() < self.jam:
                return raise_to(o, o.max_raise_to)
            if R() < 0.6:
                return raise_to(o, o.cur + o.pot)
        return CALL


class Jammer:
    """All-in with the top `width`, otherwise fold. A common cheap 1 ms design."""
    def __init__(self, width=0.2):
        self.width = width

    def act(self, o):
        if o.street == 0:
            if pct(o) < self.width:
                return raise_to(o, o.max_raise_to) if o.can_raise else CALL
            return CALL if o.to_call == 0 else FOLD
        return CALL if o.to_call == 0 else (raise_to(o, o.max_raise_to) if o.can_raise else CALL)


class TAG:
    """Chart preflop, then continuation bets plus pot odds. A typical assistant 'solid' bot."""
    def __init__(self, open_w=0.2, call_w=0.08, cbet=0.6, value=0.72):
        self.open_w, self.call_w, self.cbet, self.value = open_w, call_w, cbet, value

    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if o.raises == 0:
                if p < self.open_w and o.can_raise:
                    return raise_to(o, 3 * o.bb + o.n_callers * o.bb)
                return CALL if o.to_call == 0 else FOLD
            if p < self.call_w * 0.5 and o.can_raise:
                return raise_to(o, o.cur * 3)
            if p < self.call_w or (o.to_call <= 0.1 * o.stack and p < self.open_w * 0.6):
                return CALL
            return FOLD
        eq = equity_vs_range(o.hole, o.board, 0.35, 24)
        if o.to_call == 0:
            if eq > self.value - 0.1 and o.can_raise and R() < self.cbet + 0.3:
                return raise_to(o, o.pot * 0.66)
            return CALL
        if eq > self.value + 0.1 and o.can_raise:
            return raise_to(o, o.cur + o.pot * 0.75)
        if eq > o.to_call / (o.pot + o.to_call) + 0.08:
            return CALL
        return FOLD


class MCPotOdds:
    """The most likely assistant-written bot: MC equity vs. a random hand, raised to the number
    of live opponents, compared with pot odds."""
    def __init__(self, rollouts=20, raise_at=0.7):
        self.rollouts, self.raise_at = rollouts, raise_at

    def act(self, o):
        opp = max(1, o.n_live - 1)
        if o.street == 0:
            eq = pk.hu_eq(o.hole)
        else:
            eq = equity_vs_range(o.hole, o.board, 1.0, self.rollouts)
        eq = eq ** min(opp, 3)
        odds = o.to_call / (o.pot + o.to_call) if o.to_call else 0
        if eq > self.raise_at and o.can_raise:
            return raise_to(o, o.cur + o.pot * 0.75)
        if o.to_call == 0:
            return CALL
        return CALL if eq >= odds else FOLD


class ShortFolder:
    """TAG deep, then jam-or-fold under 15 big blinds."""
    def __init__(self):
        self.t = TAG(0.18, 0.06)

    def act(self, o):
        if o.street == 0 and o.stack + o.bet < 15 * o.bb:
            w = 0.1 + 0.02 * (15 - (o.stack + o.bet) / o.bb)
            if pct(o) < w:
                return raise_to(o, o.max_raise_to) if o.can_raise else CALL
            return CALL if o.to_call == 0 else FOLD
        return self.t.act(o)


ARCHETYPES = {
    "fold": FoldBot,
    "random": RandomBot,
    "station": Station,
    "maniac": Maniac,
    "jam20": lambda: Jammer(0.2),
    "jam08": lambda: Jammer(0.08),
    "tag": TAG,
    "nit": lambda: TAG(0.10, 0.04, 0.5, 0.78),
    "lag": lambda: TAG(0.40, 0.15, 0.8, 0.62),
    "mc": MCPotOdds,
    "shortfold": ShortFolder,
}

# Field mixes as weights. All guesses: compare across them rather than trusting any single one.
FIELDS = {
    "early_buggy": {"fold": 3, "random": 2, "station": 2, "maniac": 2, "jam20": 1, "jam08": 1, "tag": 3, "nit": 1, "lag": 1, "mc": 5, "shortfold": 1},
    "typical": {"fold": 1, "random": 1, "station": 2, "maniac": 2, "jam20": 1, "jam08": 1, "tag": 4, "nit": 2, "lag": 2, "mc": 5, "shortfold": 3},
    "strong": {"maniac": 1, "jam08": 1, "tag": 5, "nit": 3, "lag": 3, "mc": 3, "shortfold": 6},
    "aggro": {"maniac": 5, "jam20": 4, "jam08": 2, "lag": 4, "tag": 2, "mc": 2},
    "passive": {"station": 6, "mc": 5, "nit": 4, "tag": 2, "fold": 1},
}


# Copies of the candidate, used to test against a field as well prepared as we are.
def _tuned(path):
    import json, os
    from hero import Hero
    d = {}
    if os.path.exists(path):
        d = json.load(open(path))["mu"]
    if _os.environ.get("CAND_TABLE"):
        from strength import HeroTable
        return lambda: HeroTable(**d)
    return lambda: Hero(**d)

import os as _os
_here = _os.path.dirname(__file__)
ARCHETYPES["cand"] = _tuned(_os.environ.get("CAND_PATH") or _os.path.join(_here, "tuned_final.json"))
FIELDS["mirror"] = {"cand": 5, "tag": 2, "shortfold": 2, "nit": 1, "lag": 1, "mc": 1}
FIELDS["all_mirror"] = {"cand": 1}


# ---- Holdout opponents. The tuner never sees these; they exist only to detect overfitting. ----
class AllIn:
    """Moves all-in every hand."""
    def act(self, o):
        return raise_to(o, o.max_raise_to) if o.can_raise else CALL


class MinRaiser:
    """Min-raises any playable hand and calls down too much."""
    def act(self, o):
        if o.street == 0 and pct(o) > 0.55:
            return CALL if o.to_call == 0 else FOLD
        if o.can_raise and R() < 0.5:
            return raise_to(o, o.min_raise_to)
        return CALL if o.to_call <= o.pot else FOLD


class PotSizer:
    """Tier chart; pot-sized bets by made-hand strength, folds to pressure without a strong hand."""
    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if p < 0.15 and o.can_raise:
                return raise_to(o, o.cur + o.pot)
            if p < 0.35 and o.to_call <= 3 * o.bb:
                return CALL
            return CALL if o.to_call == 0 else FOLD
        eq = equity_vs_range(o.hole, o.board, 0.5, 16)
        if eq > 0.68 and o.can_raise:
            return raise_to(o, o.cur + o.pot)
        if o.to_call == 0:
            return CALL
        return CALL if eq > 0.6 else FOLD


class ChipLeaderBully:
    """Loose and aggressive when above average stack, tight when below."""
    def __init__(self):
        self.big, self.small = TAG(0.45, 0.2, 0.9, 0.6), TAG(0.12, 0.05, 0.5, 0.75)

    def act(self, o):
        avg = sum(o.stacks) / max(1, o.n_alive)
        return (self.big if o.stack > avg else self.small).act(o)


class SizedPusher:
    """Jam width grows as the stack shrinks; flat-calls small raises when deep."""
    def act(self, o):
        bbs = (o.stack + o.bet) / o.bb
        p = pct(o)
        if o.street == 0:
            w = 0.5 if bbs < 6 else 0.3 if bbs < 12 else 0.12 if bbs < 25 else 0.05
            if p < w and o.can_raise:
                return raise_to(o, o.max_raise_to)
            if bbs >= 25 and p < 0.25 and o.to_call <= 3 * o.bb:
                return CALL
            return CALL if o.to_call == 0 else FOLD
        if o.to_call == 0:
            return CALL
        eq = equity_vs_range(o.hole, o.board, 0.25, 16)
        return CALL if eq > o.to_call / (o.pot + o.to_call) else FOLD


ARCHETYPES.update({"allin": AllIn, "minraise": MinRaiser, "potsize": PotSizer, "bully": ChipLeaderBully, "pusher": SizedPusher})
FIELDS["holdout"] = {"allin": 1, "minraise": 3, "potsize": 4, "bully": 4, "pusher": 4}
FIELDS["holdout_soft"] = {"minraise": 5, "potsize": 3, "bully": 1, "fold": 1}


# ---- Stress opponents, written to punish wide, small opens. Not used in tuning. ----
class Squeezer:
    """Re-jams a wide range over any open, and opens fairly wide itself."""
    def __init__(self, w=0.22):
        self.w = w

    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if o.raises >= 1:
                if p < self.w and o.can_raise:
                    return raise_to(o, o.max_raise_to)
                return CALL if p < 0.05 else FOLD
            if p < 0.25 and o.can_raise:
                return raise_to(o, 2.5 * o.bb)
            return CALL if o.to_call == 0 else FOLD
        eq = equity_vs_range(o.hole, o.board, 0.35, 16)
        if o.to_call == 0:
            return raise_to(o, o.pot * 0.7) if eq > 0.6 and o.can_raise else CALL
        return CALL if eq > o.to_call / (o.pot + o.to_call) + 0.05 else FOLD


class Trapper:
    """Flats strong hands preflop, checks, then check-raises big when it connects."""
    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if p < 0.25 and o.to_call <= 0.08 * (o.stack + o.bet):
                return CALL
            return CALL if o.to_call == 0 else FOLD
        eq = equity_vs_range(o.hole, o.board, 0.3, 16)
        if o.to_call == 0:
            return CALL
        if eq > 0.72 and o.can_raise:
            return raise_to(o, o.max_raise_to if o.stack < 2 * o.pot else o.cur + 1.5 * o.pot)
        return CALL if eq > o.to_call / (o.pot + o.to_call) else FOLD


class Sticky:
    """Defends wide against small opens and seldom folds postflop, so stealing and small bets fail."""
    def act(self, o):
        p = pct(o)
        if o.street == 0:
            if o.to_call <= 3 * o.bb and p < 0.6:
                return CALL
            if p < 0.08 and o.can_raise:
                return raise_to(o, o.cur * 3)
            if p < 0.12:
                return CALL
            return CALL if o.to_call == 0 else FOLD
        eq = equity_vs_range(o.hole, o.board, 0.7, 14)
        if eq > 0.8 and o.can_raise:
            return raise_to(o, o.cur + o.pot * 0.7)
        if o.to_call == 0:
            return CALL
        return CALL if eq > 0.3 else FOLD


ARCHETYPES.update({"squeezer": Squeezer, "squeezer35": lambda: Squeezer(0.35), "trapper": Trapper, "sticky": Sticky})
FIELDS["stress_3bet"] = {"squeezer": 3, "squeezer35": 2, "tag": 1}
FIELDS["stress_trap"] = {"trapper": 3, "sticky": 3, "tag": 1}
FIELDS["stress_mix"] = {"squeezer": 2, "squeezer35": 1, "trapper": 2, "sticky": 2, "tag": 1, "shortfold": 1}


# League: each seat is a random past version of our bot. CAND_LEAGUE is a comma-separated list of json paths.
def _league():
    import json
    paths = [p for p in _os.environ.get("CAND_LEAGUE", "").split(",") if p]
    if not paths:
        return lambda: ARCHETYPES["cand"]()
    from strength import HeroTable
    ds = [json.load(open(p))["mu"] for p in paths]
    return lambda: HeroTable(**random.choice(ds))


ARCHETYPES["league"] = _league()
FIELDS["league_mix"] = {"league": 5, "tag": 2, "shortfold": 2, "nit": 1, "lag": 1, "mc": 1}
FIELDS["all_league"] = {"league": 1}

FIELDS["hidden"] = {"cand": 5, "squeezer": 1, "trapper": 1, "sticky": 1, "shortfold": 1, "tag": 1}


# Exploiters: bots trained specifically to beat our bot. EXPLOIT_PATHS is a comma-separated list of json files.
def _exploit():
    import json
    paths = [p for p in _os.environ.get("EXPLOIT_PATHS", "").split(",") if p]
    if not paths:
        return lambda: AllIn()
    import methods
    ds = [json.load(open(p))["mu"] for p in paths]
    return lambda: methods.HeroLinearScratch(**random.choice(ds))


ARCHETYPES["exploit"] = _exploit()
FIELDS["exploit_mix"] = {"exploit": 3, "cand": 4}
FIELDS["exploit_soft"] = {"exploit": 1, "tag": 2, "shortfold": 2, "cand": 2}
FIELDS["runover"] = {"minraise": 4, "cand": 3}


# A rigid solver-chart-style bot: fixed ranges and no adaptation. Stand-in for teams playing from published charts.
def _chart():
    from strength import HeroTable
    d = {"open_a": 0.11, "open_b": 0.38, "hu_open": 0.85, "hu_jam": 0.65, "open_size": 2.3, "threebet": 0.07, "fourbet": 0.03, "call_open": 0.14, "call_odds": 0.1,
         "jam_m": 6.7, "jam_scale": 1.0, "jam_slope": 0.07, "call_jam": 0.12, "call_jam_short": 0.03, "steal_fold_bonus": 0.0, "sh_widen": 1.5,
         "call_margin": 0.0, "icm_margin": 0.0, "adapt": 0.0, "bluff_freq": 0.33}
    return lambda: HeroTable(**d)


ARCHETYPES["chartbot"] = _chart()
FIELDS["chart_mix"] = {"chartbot": 3, "tag": 1, "shortfold": 1, "cand": 2}
FIELDS["all_chart"] = {"chartbot": 1}
````

<!-- FILE: lab/hero.py -->
````python
"""Parametric candidate policy. Small enough to retune quickly and fast enough for 1 ms."""
import os
import random
from pk import pct, equity_vs_range

R = random.random
FOLD, CALL = (0, 0), (1, 0)
# Chip-EV jam width at about 10 big blinds, by number of players left to act (secondary 9-handed chart).
JAM_CHART = [1.0, 0.69, 0.44, 0.34, 0.27, 0.22, 0.20, 0.18]

DEFAULT = {
    # preflop, deep
    "open_a": 0.08, "open_b": 0.32, "hu_open": 0.70, "hu_jam": 0.65,
    "sh_widen": 2.0, "sh_range": 0.8, "jam_scale": 0.85,
    "call_open": 0.10, "threebet": 0.05, "fourbet": 0.025,
    "open_size": 2.5, "open_limp_add": 1.0, "threebet_mult": 3.0,
    "call_odds": 0.1, "hu_defend": 0.0,
    # How far a seat's looseness can widen the range we assume for it. Low values get run over by constant raisers.
    "width_cap": 2.2,
    "hu_eqcall": 0.0, "hu_margin": 0.0, "hu_vwidth": 1.5, "hu_gate": 0.45,
    "steal_fold_bonus": 0.25,
    # short-stack jam-or-fold
    "jam_m": 12.0, "jam_slope": 0.07, "call_jam": 0.09, "call_jam_short": 0.02,
    # postflop
    "range_unraised": 0.45, "range_bet": 0.28, "range_raise": 0.10,
    "value_eq": 0.70, "bluff_freq": 0.18, "bet_frac": 0.66, "call_margin": 0.04, "raise_eq": 0.82,
    "commit_spr": 1.3,
    # ICM: discount for close spots once few players remain
    "icm_margin": 0.05, "rollouts": 40,
    # within-table adaptation
    "adapt": 1.0,
    # optional v3 features; zero means off
    "bully": 0.0, "cbet_pfr": 0.0, "cap_tight": 0.0,
    # Facing a preflop all-in: equity vs. this seat's observed raising range.
    "eqcall": float(os.environ.get("HERO_EQCALL", 0)), "eqcall_margin": 0.04, "vwidth_mult": 1.2,
}


class Hero:
    def __init__(self, **kw):
        self.p = dict(DEFAULT)
        self.p.update(kw)
        self.vpip = {}
        self.hands = {}
        self.raises = {}
        self.seen_vp = set()
        self.seen_h = set()
        self.last_hand = -1
        self.saw_aggro = 0
        self.aggro_seat = -1
        self.pfr = False
        self.pf_raise = {}
        self.seen_pf = set()

    # ---- opponent tracking; each event is O(1)
    def observe(self, seat, street, kind, amount):
        if street == 0:
            if seat not in self.seen_h:
                self.seen_h.add(seat)
                self.hands[seat] = self.hands.get(seat, 0) + 1
            if kind and seat not in self.seen_vp:
                self.seen_vp.add(seat)
                self.vpip[seat] = self.vpip.get(seat, 0) + 1
        if kind == 2:
            if street == 0 and seat not in self.seen_pf:
                self.seen_pf.add(seat)
                self.pf_raise[seat] = self.pf_raise.get(seat, 0) + 1
            self.saw_aggro += 1
            self.aggro_seat = seat
            self.raises[seat] = self.raises.get(seat, 0) + 1

    def end_hand(self, n):
        self.seen_vp = set()
        self.seen_h = set()
        self.saw_aggro = 0
        self.aggro_seat = -1
        self.pfr = False
        self.seen_pf = set()

    def _vpip(self, s):
        # Bayesian shrink toward 30%
        return (self.vpip.get(s, 0) + 3.0) / (self.hands.get(s, 0) + 10.0)

    def _fold_rate_behind(self, o):
        p = self.p
        if not p["adapt"]:
            return 0.0
        v = []
        for s in range(len(o.stacks)):
            if s != o.seat and o.in_hand[s]:
                v.append(self._vpip(s))
        return 1.0 - (sum(v) / len(v)) if v else 0.0

    def act(self, o):
        if o.street == 0:
            r = self.preflop(o)
            if r[0] == 2:
                self.pfr = True
            return r
        return self.postflop(o)

    def preflop(self, o):
        p = self.p
        hp = pct(o.hole)
        m = (o.stack + o.bet) / float(o.sb + o.bb)
        eff = self._eff_stack(o)
        eff_m = eff / float(o.sb + o.bb)
        few = o.n_alive
        margin = p["icm_margin"] * (1.0 if few <= 4 else 0.0)

        hu = o.n_alive == 2
        sh = 1.0 + p["sh_widen"] * (8 - o.n_alive) / 6.0
        if o.raises == 0:
            behind = o.n_behind
            # short: jam or fold
            if eff_m < p["jam_m"]:
                w = p["jam_scale"] * JAM_CHART[min(behind, 7)] * max(0.25, 1.0 + p["jam_slope"] * (6.67 - eff_m))
                if hu:
                    w = max(w, p["hu_jam"])
                w *= 1.0 + p["steal_fold_bonus"] * (self._fold_rate_behind(o) - 0.6)
                if hp < w:
                    return (2, o.max_raise_to) if o.can_raise else CALL
                return CALL if o.to_call == 0 else FOLD
            w = p["hu_open"] if hu else p["open_a"] + p["open_b"] / (behind + 0.5)
            w *= 1.0 + p["steal_fold_bonus"] * (self._fold_rate_behind(o) - 0.6)
            if p["bully"]:
                avg = o.total_chips / float(o.n_alive)
                w *= 1.0 + p["bully"] * max(-0.5, min(1.5, (o.stack + o.bet) / avg - 1.0))
            if hp < w and o.can_raise:
                return (2, o.bb * (p["open_size"] + p["open_limp_add"] * o.n_callers))
            if o.to_call == 0:
                return CALL
            # complete the small blind cheaply with reasonable hands
            if o.to_call <= o.sb and hp < w * 1.6:
                return CALL
            return FOLD
        # facing a raise
        cost = o.to_call
        all_in_ish = o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur
        odds = cost / float(o.pot + cost)
        if all_in_ish and p["hu_eqcall"] and o.n_alive == 2 and o.aggressor >= 0 and (self.pf_raise.get(o.aggressor, 0) + 1.2) / (self.hands.get(o.aggressor, 0) + 10.0) >= p["hu_gate"]:
            # Heads-up there is no ICM to protect. Against a seat raising most hands, call on price against
            # its observed range. Against tight jammers keep folding, since marginal flips waste a skill edge.
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            width = max(0.03, min(1.0, rate * p["hu_vwidth"]))
            eq = equity_vs_range(o.hole, [], width, int(p["rollouts"]))
            return CALL if eq > odds + p["hu_margin"] else FOLD
        if all_in_ish and p["eqcall"] and o.aggressor >= 0:
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            width = max(0.03, min(1.0, rate * p["vwidth_mult"]))
            eq = equity_vs_range(o.hole, [], width, int(p["rollouts"]))
            opp = max(1, o.n_live - 1)
            if opp > 1:
                eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
            return CALL if eq > odds + p["eqcall_margin"] + margin else FOLD
        if all_in_ish:
            aggro = self._raiser_width(o)
            w = p["call_jam"] * aggro * sh - margin * 0.5
            w += p["call_jam_short"] * max(0.0, 8.0 - eff_m)
            w += max(0.0, odds - 0.33) * 0.5
            return CALL if hp < max(0.01, w) else FOLD
        if o.raises >= 2:
            if hp < p["fourbet"] and o.can_raise:
                return (2, o.max_raise_to)
            return CALL if hp < p["fourbet"] * 2 else FOLD
        aggro = self._raiser_width(o) * sh
        if hp < p["threebet"] * aggro and o.can_raise:
            if eff_m < 25:
                return (2, o.max_raise_to)
            return (2, o.cur * p["threebet_mult"])
        # Price matters: a min-raise offers 3-to-1, so defend wider when it is cheap, especially short-handed.
        wd = p["call_open"] * aggro + odds * p["call_odds"]
        if hu:
            wd = max(wd, p["hu_defend"] * (odds / 0.25) if odds >= 0.1 else 0.0)
        if hp < wd and cost < 0.2 * o.stack:
            return CALL
        return FOLD

    def _raiser_width(self, o):
        p = self.p
        if not p["adapt"] or o.aggressor < 0:
            return 1.0
        return max(0.7, min(p["width_cap"], self._vpip(o.aggressor) / 0.3))

    def eq(self, hole, board, width):
        return equity_vs_range(hole, board, width, int(self.p["rollouts"]))

    def _eff_stack(self, o):
        best = 0
        for s in range(len(o.stacks)):
            if s != o.seat and o.in_hand[s]:
                v = o.stacks[s] + o.bets[s]
                if v > best:
                    best = v
        return min(best, o.stack + o.bet)

    def postflop(self, o):
        p = self.p
        # Estimate villain range from the action.
        if o.aggressor >= 0 and o.to_call > 0:
            base = p["range_raise"] if o.raises >= 2 else p["range_bet"]
            if p["adapt"]:
                base *= max(0.7, min(p["width_cap"], self._vpip(o.aggressor) / 0.3))
        else:
            base = p["range_unraised"]
        base = min(1.0, base * (1.0 + p["sh_range"] * (8 - o.n_alive) / 6.0))
        eq = self.eq(o.hole, o.board, base)
        opp = max(1, o.n_live - 1)
        if opp > 1:
            eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
        spr = o.stack / float(max(1, o.pot))
        margin = p["call_margin"] + (p["icm_margin"] if o.n_alive <= 4 else 0.0)
        # Near the cap, survival is what ICM pays for: require more to call off.
        if p["cap_tight"] and o.hand_no >= 180:
            margin += p["cap_tight"]
        if o.to_call == 0:
            if not o.can_raise:
                return CALL
            if eq > p["value_eq"]:
                size = o.pot * p["bet_frac"]
                if spr < p["commit_spr"]:
                    return (2, o.max_raise_to)
                return (2, size)
            bf = p["bluff_freq"] + (p["cbet_pfr"] if self.pfr and o.street == 1 else 0.0)
            if o.n_live == 2 and R() < bf:
                return (2, o.pot * 0.5)
            return CALL
        odds = o.to_call / float(o.pot + o.to_call)
        if eq > p["raise_eq"] and o.can_raise:
            if spr < 2.0:
                return (2, o.max_raise_to)
            return (2, o.cur + o.pot * 0.8)
        return CALL if eq > odds + margin else FOLD
````

<!-- FILE: lab/strength.py -->
````python
"""Small model: postflop equity from a hand-feature lookup table built offline. No live Monte Carlo.
Features are cheap and variant-portable: rebuild the table with the variant's evaluator."""
import json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk
from pk import evaluate, equity_vs_range
from hero import Hero

WIDTHS = [0.08, 0.2, 0.4, 1.0]
_TP = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"strength_{pk.VARIANT}.json")


def feature(hole, board):
    all_ = hole + board
    # Features stay in the base ranking; each variant's table learns what they are worth under its own rules.
    v = pk.evaluate_omaha(hole, board) if pk.VARIANT == "omaha" else evaluate(all_)
    cat = v >> 20
    bv = evaluate(board)
    bcat = bv >> 20
    ranks = sorted((c >> 2 for c in board), reverse=True)
    top = ranks[0]
    sub = 0
    if cat == 1:
        pr = (v - (1 << 20)) // 2197
        hi = max(c >> 2 for c in hole)
        if bcat == 1:
            sub = 5 if hi >= 11 else 6 if hi >= 8 else 7  # board pair, kicker strength
        elif pr > top:
            sub = 0 if pr >= 8 else 1  # overpair
        elif pr == top:
            sub = 2 if hi >= 10 and hi != pr or pr >= 11 else 3  # top pair, kicker
        elif len(ranks) > 1 and pr >= ranks[1]:
            sub = 4
        else:
            sub = 8
    elif cat == 0:
        hi = max(c >> 2 for c in hole)
        sub = 0 if hi > top and hi == 12 else 1 if hi > top else 2
    else:
        sub = 1 if cat > bcat else 0  # does our hand actually use the hole cards
    fd = sd = 0
    if len(board) < 5:
        if pk.VARIANT == "omaha":
            # Must use exactly two hole cards, so a draw needs two of the suit in hand and two on board.
            hc, bc = [0, 0, 0, 0], [0, 0, 0, 0]
            for c in hole:
                hc[c & 3] += 1
            for c in board:
                bc[c & 3] += 1
            for i in range(4):
                if hc[i] >= 2 and bc[i] == 2:
                    fd = 1
        else:
            cnt = [0, 0, 0, 0]
            for c in all_:
                cnt[c & 3] += 1
            ms = cnt[0]
            s = 0
            for i in range(1, 4):
                if cnt[i] > ms:
                    ms, s = cnt[i], i
            if ms == 4 and any((c & 3) == s for c in hole):
                fd = 1
        m = 0
        for c in all_:
            m |= 1 << (c >> 2)
        m = (m << 1) | (m >> 12 & 1)
        for i in range(0, 10):
            b = (m >> i) & 31
            if b in (0b11110, 0b01111):
                sd = 2
                break
            if b in (0b11101, 0b11011, 0b10111):
                sd = max(sd, 1)
    bpair = 1 if bcat >= 1 else 0
    cnt2 = [0, 0, 0, 0]
    for c in board:
        cnt2[c & 3] += 1
    wet = max(cnt2)
    wet = 2 if wet >= 3 else 1 if wet == 2 else 0
    return (len(board), cat, sub, fd, sd, bpair, wet)


def _sample(args):
    n, rollouts, seed = args
    random.seed(seed)
    out = {}
    deck = pk.DECK
    for _ in range(n):
        st = random.choice((3, 4, 5))
        s = random.sample(deck, pk.N_HOLE + st)
        hole, board = s[:pk.N_HOLE], s[pk.N_HOLE:]
        k = feature(hole, board)
        row = out.setdefault(k, [0] + [0.0] * len(WIDTHS))
        row[0] += 1
        for i, w in enumerate(WIDTHS):
            row[i + 1] += equity_vs_range(hole, board, w, rollouts)
    return out


def build(n=150000, rollouts=24, procs=10):
    from multiprocessing import Pool
    t = time.time()
    with Pool(procs) as p:
        parts = p.map(_sample, [(n // procs, rollouts, 1000 + i) for i in range(procs)])
    tot = {}
    for part in parts:
        for k, r in part.items():
            row = tot.setdefault(k, [0] + [0.0] * len(WIDTHS))
            for i in range(len(row)):
                row[i] += r[i]
    tab = {",".join(map(str, k)): [round(x / r[0], 4) for x in r[1:]] + [r[0]] for k, r in tot.items()}
    json.dump(tab, open(_TP, "w"))
    return time.time() - t, len(tab)


_TAB = None


def _load():
    global _TAB
    d = json.load(open(_TP))
    _TAB = {tuple(map(int, k.split(","))): v for k, v in d.items()}


def table_equity(hole, board, width):
    if _TAB is None:
        _load()
    r = _TAB.get(feature(hole, board))
    if r is None or r[-1] < 5:
        k = feature(hole, board)
        # Back off: ignore texture when the exact cell is rare.
        for cand, v in _TAB.items():
            if cand[:5] == k[:5] and v[-1] >= 5:
                r = v
                break
        if r is None:
            return 0.5
    if width <= WIDTHS[0]:
        return r[0]
    for i in range(1, len(WIDTHS)):
        if width <= WIDTHS[i]:
            f = (width - WIDTHS[i - 1]) / (WIDTHS[i] - WIDTHS[i - 1])
            return r[i - 1] * (1 - f) + r[i] * f
    return r[3]


class HeroTable(Hero):
    """Same policy as the candidate; only the postflop equity source differs."""
    def eq(self, hole, board, width):
        return table_equity(hole, board, width)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150000
    ro = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    secs, cells = build(n, ro, procs)
    print(f"{pk.VARIANT}: {cells} feature cells in {secs:.1f}s -> {os.path.getsize(_TP)} bytes")
    _load()
    import time as T
    a = [random.sample(pk.DECK, pk.N_HOLE + 5) for _ in range(5000)]
    t = T.perf_counter()
    for s in a:
        table_equity(s[:pk.N_HOLE], s[pk.N_HOLE:pk.N_HOLE + random.choice((3, 4, 5))], 0.3)
    print(f"lookup {(T.perf_counter()-t)/5000*1e6:.1f} us")
    err = []
    for _ in range(600):
        st = random.choice((3, 4, 5))
        s = random.sample(pk.DECK, pk.N_HOLE + st)
        w = random.choice([0.15, 0.3, 0.6])
        h, b = s[:pk.N_HOLE], s[pk.N_HOLE:]
        err.append(abs(table_equity(h, b, w) - equity_vs_range(h, b, w, 200)))
    err.sort()
    print(f"abs equity error vs 200-rollout MC: mean {sum(err)/len(err):.3f}, p90 {err[int(.9*len(err))]:.3f}")
````

<!-- FILE: lab/methods.py -->
````python
"""Alternative policy families, all built on the same preflop table, lookup equity and engine."""
import json, math, os, random
from hero import Hero, DEFAULT, FOLD, CALL
from pk import pct
from strength import HeroTable

R = random.random


# ---- 1. Contextual thresholds: postflop thresholds vary by street and heads-up vs. multiway. ----
CTX_NAMES = ["value_eq", "call_margin", "raise_eq", "bet_frac"]


class HeroCtx(HeroTable):
    def __init__(self, **kw):
        super().__init__(**kw)
        base = self.p
        self.ctx = {}
        for st in (1, 2, 3):
            for hu in (0, 1):
                d = dict(base)
                for n in CTX_NAMES:
                    d[n] = base[n] + base.get(f"d_{n}_{st}{hu}", 0.0)
                self.ctx[(st, hu)] = d

    def postflop(self, o):
        keep = self.p
        self.p = self.ctx[(o.street, 1 if o.n_live == 2 else 0)]
        r = super().postflop(o)
        self.p = keep
        return r


def ctx_search():
    s = {}
    for st in (1, 2, 3):
        for hu in (0, 1):
            s[f"d_value_eq_{st}{hu}"] = (-0.15, 0.15)
            s[f"d_call_margin_{st}{hu}"] = (-0.12, 0.12)
            s[f"d_raise_eq_{st}{hu}"] = (-0.12, 0.1)
            s[f"d_bet_frac_{st}{hu}"] = (-0.4, 0.6)
    return s


# ---- 2. Explicit EV: choose the postflop action with the best risk-adjusted value, per-seat fold rates. ----
EV_DEFAULT = {"f0": 0.45, "fk": 0.35, "calldown": 0.6, "lam": 0.2, "lam4": 0.25, "real": 0.85, "ev_margin": 0.0}


class HeroEV(HeroTable):
    def __init__(self, **kw):
        d = dict(EV_DEFAULT)
        d.update(kw)
        super().__init__(**d)
        self.faced, self.folds, self.pending = {}, {}, set()

    def observe(self, seat, street, kind, amount):
        super().observe(seat, street, kind, amount)
        if street > 0:
            if seat in self.pending and kind != 2:
                self.pending.discard(seat)
                self.faced[seat] = self.faced.get(seat, 0) + 1
                if kind == 0:
                    self.folds[seat] = self.folds.get(seat, 0) + 1
            if kind == 2:
                self.pending = set(range(8)) - {seat}

    def end_hand(self, n):
        super().end_hand(n)
        self.pending = set()

    def _f(self, s, ratio):
        p = self.p
        base = (self.folds.get(s, 0) + p["f0"] * 8.0) / (self.faced.get(s, 0) + 8.0)
        return min(0.95, base * ratio ** p["fk"])

    def postflop(self, o):
        p = self.p
        if o.aggressor >= 0 and o.to_call > 0:
            base = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * max(0.7, min(2.2, self._vpip(o.aggressor) / 0.3))
        else:
            base = p["range_unraised"]
        base = min(1.0, base * (1.0 + p["sh_range"] * (8 - o.n_alive) / 6.0))
        opp = max(1, o.n_live - 1)
        ex = 1 + 0.65 * (min(opp, 4) - 1)
        eq = self.eq(o.hole, o.board, base) ** ex
        eqc = self.eq(o.hole, o.board, max(0.03, base * p["calldown"])) ** ex
        lam = p["lam"] + (p["lam4"] if o.n_alive <= 4 else 0.0)
        pot = float(max(1, o.pot))
        best, act = (eq * pot * p["real"] if o.to_call == 0 else -1e-9 + 0.0), (CALL if o.to_call == 0 else FOLD)
        if o.to_call > 0:
            ev = eq * pot - (1 + lam) * (1 - eq) * o.to_call - p["ev_margin"] * o.to_call
            if ev > best:
                best, act = ev, CALL
        if o.can_raise:
            others = [s for s in range(len(o.stacks)) if s != o.seat and o.in_hand[s] and o.stacks[s] > 0]
            for to in (o.cur + 0.5 * pot, o.cur + pot, o.max_raise_to):
                to = max(o.min_raise_to, min(to, o.max_raise_to))
                add = to - o.bet
                f = 1.0
                for s in others:
                    f *= self._f(s, (to - o.cur) / pot)
                called = add - o.to_call
                ev = f * pot + (1 - f) * (eqc * (pot + called) - (1 + lam) * (1 - eqc) * add) - p["ev_margin"] * add
                if ev > best:
                    best, act = ev, (2, to)
        return act


EV_SEARCH = {"f0": (0.1, 0.8), "fk": (0.0, 1.0), "calldown": (0.2, 1.0), "lam": (0.0, 1.0), "lam4": (0.0, 1.0), "real": (0.4, 1.1), "ev_margin": (0.0, 0.3)}


# ---- 3. Small linear policy over features; optionally a residual on top of the rule. ----
N_FEAT = 14


def features(self, o):
    hp = pct(o.hole)
    if o.street == 0:
        s = 1.0 - hp
    else:
        s = self.eq(o.hole, o.board, 0.4) ** (1 + 0.65 * (min(max(1, o.n_live - 1), 4) - 1))
    pot = float(max(1, o.pot))
    odds = o.to_call / (pot + o.to_call) if o.to_call else 0.0
    stack = float(max(1, o.stack))
    m = math.log(max(1.0, (o.stack + o.bet) / float(o.sb + o.bb))) / 4.0
    ag = self._vpip(o.aggressor) if o.aggressor >= 0 else 0.3
    return [1.0, s, odds, min(2.0, o.to_call / stack), m, min(5.0, stack / pot) / 5.0, o.n_live / 8.0, o.n_alive / 8.0, o.n_behind / 8.0,
            1.0 if o.street == 1 else 0.0, 1.0 if o.street == 2 else 0.0, 1.0 if o.street == 3 else 0.0, ag, min(o.raises, 3) / 3.0]


def _action(o, i):
    pot = float(max(1, o.pot))
    if i == 0:
        return CALL if o.to_call == 0 else FOLD
    if i == 1 or not o.can_raise:
        return CALL
    if i == 2:
        return (2, o.cur + max(0.5 * pot, 1))
    if i == 3:
        return (2, o.cur + pot)
    return (2, o.max_raise_to)


def _index(o, a):
    if a[0] == 0:
        return 0
    if a[0] == 1:
        return 1
    if a[1] >= o.max_raise_to:
        return 4
    return 2 if a[1] - o.cur <= 0.75 * max(1, o.pot) else 3


class HeroLinear(HeroTable):
    """rule_bonus > 0: the rule's action gets a bonus, so all-zero weights reproduce the rule exactly."""
    rule_bonus = 1.0

    def __init__(self, **kw):
        w = kw.pop("W", None)
        extra = {k: kw.pop(k) for k in list(kw) if k.startswith("w_")}
        super().__init__(**kw)
        self.W = [[extra.get(f"w_{i}_{j}", 0.0) for j in range(N_FEAT)] for i in range(5)]

    def act(self, o):
        x = features(self, o)
        rule = super().act(o) if self.rule_bonus else None
        ri = _index(o, rule) if rule else -1
        best, bi = -1e18, 1
        for i in range(5):
            if i >= 2 and not o.can_raise:
                continue
            if i == 0 and o.to_call == 0:
                continue
            v = sum(a * b for a, b in zip(self.W[i], x)) + (self.rule_bonus if i == ri else 0.0)
            if v > best:
                best, bi = v, i
        if bi == ri:
            return rule
        return _action(o, bi)


class HeroLinearScratch(HeroLinear):
    rule_bonus = 0.0


def linear_search(limit):
    return {f"w_{i}_{j}": (-limit, limit) for i in range(5) for j in range(N_FEAT)}


# ---- 4. Tabular Q overrides learned from self-play hand results, falling back to the rule. ----
def q_key(self, o):
    if o.street == 0:
        s = min(9, int(pct(o.hole) * 10))
    else:
        e = self.eq(o.hole, o.board, 0.4) ** (1 + 0.65 * (min(max(1, o.n_live - 1), 4) - 1))
        s = min(9, int(e * 10))
    pot = float(max(1, o.pot))
    if o.to_call == 0:
        fc = 0
    elif o.to_call >= 0.5 * max(1, o.stack):
        fc = 4
    else:
        r = o.to_call / pot
        fc = 1 if r < 0.33 else 2 if r < 0.8 else 3
    m = (o.stack + o.bet) / float(o.sb + o.bb)
    mb = 0 if m < 4 else 1 if m < 8 else 2 if m < 15 else 3 if m < 30 else 4
    nl = 0 if o.n_live == 2 else 1 if o.n_live == 3 else 2
    bh = 0 if o.n_behind == 0 else 1 if o.n_behind <= 2 else 2
    return f"{o.street}{s}{fc}{mb}{nl}{bh}"


_QCACHE = {}


def _loadq(path):
    q = _QCACHE.get(path)
    if q is None:
        q = _QCACHE[path] = json.load(open(path))
    return q


class HeroQ(HeroTable):
    """Q[key] = list of 5 [mean_reward, count]. Overrides the rule only with enough evidence."""
    def __init__(self, qfile=None, eps=0.0, nmin=200, delta=0.05, collect=False, **kw):
        super().__init__(**kw)
        self.Q = _loadq(qfile) if qfile else {}
        self.eps, self.nmin, self.delta, self.collect = eps, nmin, delta, collect
        self.rec, self.seat = [], -1
        self.out = {}

    def act(self, o):
        rule = super().act(o)
        k = q_key(self, o)
        ri = _index(o, rule)
        i = ri
        q = self.Q.get(k)
        if q and q[ri][1] >= self.nmin:
            best = q[ri][0] + self.delta
            for j in range(5):
                if j >= 2 and not o.can_raise:
                    continue
                if j == 0 and o.to_call == 0:
                    continue
                if q[j][1] >= self.nmin and q[j][0] > best:
                    best, i = q[j][0], j
        if self.eps and R() < self.eps:
            i = random.randrange(5)
            if i == 0 and o.to_call == 0:
                i = 1
            if i >= 2 and not o.can_raise:
                i = 1
        if self.collect:
            self.seat = o.seat
            self.rec.append((k, i))
        return rule if i == ri else _action(o, i)

    def hand_result(self, stacks, start):
        if not self.rec:
            return
        u = lambda s: 100.0 * (s / 16000.0) ** 0.7
        r = u(stacks[self.seat]) - u(start[self.seat])
        for k, i in self.rec:
            row = self.out.setdefault(k, [[0.0, 0] for _ in range(5)])
            row[i][0] += r
            row[i][1] += 1
        self.rec = []


# ---- 5. Portfolio: switch between two tuned parameter sets from how tough the table looks. ----
class HeroSwitch(HeroTable):
    def __init__(self, weak=None, tough=None, band=(0.18, 0.5), frac=0.6, after=15, **kw):
        super().__init__(**(weak or {}))
        self.pw, self.pt = self.p, dict(self.p)
        self.pt.update(tough or {})
        self.band, self.frac, self.after = band, frac, after

    def act(self, o):
        seats = [s for s in range(len(o.stacks)) if s != o.seat and o.stacks[s] + o.bets[s] > 0 and self.hands.get(s, 0) >= self.after]
        tough = False
        if len(seats) >= 2:
            lo, hi = self.band
            n = sum(1 for s in seats if lo <= self.vpip.get(s, 0) / max(1, self.hands.get(s, 1)) <= hi)
            tough = n >= self.frac * len(seats)
        self.p = self.pt if tough else self.pw
        return super().act(o)


CLASSES = {"ctx": HeroCtx, "ev": HeroEV, "linear": HeroLinear, "linear0": HeroLinearScratch, "q": HeroQ, "switch": HeroSwitch}


# ---- 6. Exact heads-up jam-or-fold Nash chart for short stacks, falling back to the tuned rule. ----
_NASH = {}
_RK = "23456789TJQKA"


def _hclass(h):
    ra, rb = h[0] >> 2, h[1] >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return _RK[ra] * 2
    return _RK[ra] + _RK[rb] + ("s" if (h[0] & 3) == (h[1] & 3) else "o")


def nash_table():
    import pk
    t = _NASH.get(pk.VARIANT)
    if t is None:
        t = _NASH[pk.VARIANT] = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"nash_hu_{pk.VARIANT}.json")))
    return t


class HeroNash(HeroTable):
    """Heads-up at or below nash_max big blinds: jam or fold from the chart. Otherwise the tuned rule."""
    def __init__(self, nash_max=15.0, **kw):
        super().__init__(**kw)
        self.nmax = nash_max
        self.nt = nash_table()

    def act(self, o):
        if o.n_alive == 2 and o.street == 0:
            s = self._eff_stack(o) / float(o.bb)
            if s <= self.nmax:
                c = _hclass(o.hole)
                if o.raises == 0 and o.to_call <= o.sb:  # small blind, first to act
                    if self.nt["jam"].get(c, 0) >= s:
                        return (2, o.max_raise_to) if o.can_raise else CALL
                    return FOLD
                if o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur:  # facing a jam
                    return CALL if self.nt["call"].get(c, 0) >= s else FOLD
        return super().act(o)


class PureNash(HeroNash):
    """Benchmark opponent: the jam-or-fold chart at every heads-up depth up to 40 big blinds."""
    def __init__(self, **kw):
        super().__init__(nash_max=40.0, **kw)


CLASSES.update({"nash": HeroNash, "purenash": PureNash})
````

<!-- FILE: lab/run.py -->
````python
"""Parallel tournament runner. Each table: `hero_spec` at one seat, seven field bots."""
import math, random, sys, time, json
from multiprocessing import Pool
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import play_table, points_for, SCHEDULE_DEFAULT
from field import ARCHETYPES, FIELDS
from hero import Hero

# Guesses at the point table. The real one is announced at kickoff, so test across all of these.
PAYOUTS = {
    "top3": [50, 30, 20, 0, 0, 0, 0, 0],
    "top4": [45, 25, 18, 12, 0, 0, 0, 0],
    "steep": [100, 50, 30, 20, 10, 5, 2, 0],
    "linear": [7, 6, 5, 4, 3, 2, 1, 0],
    "wta": [100, 0, 0, 0, 0, 0, 0, 0],
    "gym": [100, 60, 40, 25, 15, 10, 5, 0],
}


# The announced table, when event_config.json exists.
from engine import EVENT
if EVENT.get("points"):
    PAYOUTS["real"] = list(EVENT["points"])


def make(spec):
    if isinstance(spec, dict):
        c = spec.get("cls")
        if c == "table":
            from strength import HeroTable
            return HeroTable(**{k: v for k, v in spec.items() if k != "cls"})
        if c:
            import methods
            return methods.CLASSES[c](**{k: v for k, v in spec.items() if k != "cls"})
        return Hero(**spec)
    return ARCHETYPES[spec]()


def _work(a):
    heroes, field, payout_names, tables, seed, schedule = a
    random.seed(seed)
    names = list(FIELDS[field])
    weights = [FIELDS[field][k] for k in names]
    out = {h: {p: [0.0, 0.0] for p in payout_names} for h in heroes}
    hands = 0
    for t in range(tables):
        for h, spec in heroes.items():
            seats = random.choices(names, weights, k=7)
            bots = [make(s) for s in seats]
            pos = random.randrange(8)
            bots.insert(pos, make(spec))
            elim, nh, surv = play_table(bots, schedule)
            hands += nh
            for pn in payout_names:
                v = points_for(elim, surv, PAYOUTS[pn])[pos]
                c = out[h][pn]
                c[0] += v
                c[1] += v * v
    return out, hands


def evaluate(heroes, field="typical", payouts=("top3", "linear", "steep"), tables=2000, procs=10, seed=7, schedule=SCHEDULE_DEFAULT):
    """Returns {hero: {payout: (mean, stderr)}}."""
    per = max(1, tables // procs)
    jobs = [(heroes, field, list(payouts), per, seed * 1000 + i, schedule) for i in range(procs)]
    with Pool(procs) as pool:
        res = pool.map(_work, jobs)
    tot = per * procs
    final = {}
    for h in heroes:
        final[h] = {}
        for p in payouts:
            s = sum(r[0][h][p][0] for r in res)
            s2 = sum(r[0][h][p][1] for r in res)
            mean = s / tot
            var = max(0.0, s2 / tot - mean * mean)
            final[h][p] = (mean, math.sqrt(var / tot))
    return final, sum(r[1] for r in res)


if __name__ == "__main__":
    t0 = time.time()
    heroes = {k: k for k in ARCHETYPES}
    heroes["HERO"] = {}
    res, hands = evaluate(heroes, tables=int(sys.argv[1]) if len(sys.argv) > 1 else 300)
    dt = time.time() - t0
    print(f"{hands} hands in {dt:.1f}s = {hands/dt:.0f} hands/s")
    fair = {p: sum(v) / 8 for p, v in PAYOUTS.items()}
    for h, r in sorted(res.items(), key=lambda x: -x[1]["top3"][0]):
        print(h.ljust(10), "  ".join(f"{p}:{m:6.2f}±{s:4.2f} (fair {fair[p]:.1f})" for p, (m, s) in r.items()))
````

<!-- FILE: lab/mtune.py -->
````python
"""General tuner testbed. Same fitness for all algorithms: mean over (field, points table) of score / fair share."""
import json, math, os, random, sys, time
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS
from run import PAYOUTS, make

BLEND_FIELDS = ["typical", "strong", "aggro", "all_mirror", "mirror"]
# The recommended tuning field: weak bots, copies of ourselves, and bots trained to beat us.
ROBUST_FIELDS = ["typical", "strong", "aggro", "all_mirror", "mirror", "exploit_soft", "runover"]
ALLP = ["top3", "steep", "linear", "wta"]
BASE_SEARCH = {
    "open_a": (0.02, 0.2), "open_b": (0.1, 0.8), "hu_open": (0.3, 1.0), "hu_jam": (0.3, 1.0), "sh_widen": (0.0, 5.0), "sh_range": (0.0, 2.0), "jam_scale": (0.4, 1.3),
    "call_open": (0.03, 0.25), "threebet": (0.015, 0.12), "fourbet": (0.01, 0.06), "open_size": (2.0, 4.0), "threebet_mult": (2.5, 4.0), "steal_fold_bonus": (0.0, 0.8),
    "jam_m": (5.0, 25.0), "jam_slope": (0.0, 0.2), "call_jam": (0.03, 0.25), "call_jam_short": (0.0, 0.05), "range_unraised": (0.3, 1.0), "range_bet": (0.1, 0.6),
    "range_raise": (0.03, 0.3), "value_eq": (0.55, 0.85), "bluff_freq": (0.0, 0.5), "bet_frac": (0.33, 1.2), "call_margin": (-0.03, 0.15), "raise_eq": (0.7, 0.95),
    "commit_spr": (0.5, 3.0), "icm_margin": (0.0, 0.15), "call_odds": (0.0, 1.5), "hu_defend": (0.0, 0.9), "width_cap": (1.5, 8.0),
}


FULL_SEARCH = {**BASE_SEARCH, "eqcall_margin": (-0.05, 0.25), "vwidth_mult": (0.3, 2.5)}


def _eval(a):
    """Returns mean normalised score of one candidate. Same seed means the same tables and seats for all candidates."""
    spec, fields, payouts, tables, seed = a
    rng = random.Random(seed)
    random.seed(seed)
    tot = 0.0
    for f in fields:
        names = list(FIELDS[f]); w = [FIELDS[f][k] for k in names]
        for _ in range(tables):
            seats = rng.choices(names, w, k=7)
            bots = [ARCHETYPES[s]() for s in seats]
            pos = rng.randrange(8)
            bots.insert(pos, make(spec))
            e, nh, s = play_table(bots)
            for p in payouts:
                tot += points_for(e, s, PAYOUTS[p])[pos] / (sum(PAYOUTS[p]) / 8.0)
    return tot / (tables * len(fields) * len(payouts))


class Box:
    """Maps [0,1]^d to parameter dicts."""
    def __init__(self, search, fixed):
        self.keys = list(search); self.lo = np.array([search[k][0] for k in self.keys]); self.hi = np.array([search[k][1] for k in self.keys]); self.fixed = fixed

    def enc(self, d):
        return np.clip((np.array([d.get(k, 0.0) for k in self.keys]) - self.lo) / (self.hi - self.lo), 0, 1)

    def dec(self, x):
        d = dict(self.fixed)
        v = self.lo + np.clip(x, 0, 1) * (self.hi - self.lo)
        d.update({k: float(a) for k, a in zip(self.keys, v)})
        return d


class Ctx:
    def __init__(self, box, fields, payouts, procs, seed):
        self.box, self.fields, self.payouts, self.rng = box, fields, payouts, np.random.default_rng(seed)
        self.pool = Pool(procs); self.used = 0; self.t0 = time.time(); self.log = []

    def batch(self, xs, tables):
        s = int(self.rng.integers(1 << 30))
        r = self.pool.map(_eval, [(self.box.dec(x), self.fields, self.payouts, tables, s) for x in xs], chunksize=1)
        self.used += len(xs) * tables * len(self.fields)
        return np.array(r)

    def mark(self, x):
        self.log.append((self.used, round(time.time() - self.t0, 1), self.box.dec(x)))


def t_cem(c, x0, budget, sig0=0.25, pop=30, elite=6, tables=30):
    mu, sig = x0.copy(), np.full_like(x0, sig0)
    while c.used < budget:
        xs = [mu.copy()] + [np.clip(mu + c.rng.normal(size=mu.size) * sig, 0, 1) for _ in range(pop - 1)]
        r = c.batch(xs, tables)
        e = np.array([xs[i] for i in np.argsort(-r)[:elite]])
        mu = 0.7 * e.mean(0) + 0.3 * mu
        sig = np.maximum(0.03, 0.8 * e.std(0) + 0.2 * sig)
        c.mark(mu)
    return mu


def t_cma(c, x0, budget, sig0=0.2, tables=30):
    n = x0.size; lam = 4 + int(3 * math.log(n)); lam = max(lam, 14); mu_n = lam // 2
    w = np.log(mu_n + 0.5) - np.log(np.arange(1, mu_n + 1)); w /= w.sum(); me = 1 / (w ** 2).sum()
    cc, cs = (4 + me / n) / (n + 4 + 2 * me / n), (me + 2) / (n + me + 5)
    c1 = 2 / ((n + 1.3) ** 2 + me); cm = min(1 - c1, 2 * (me - 2 + 1 / me) / ((n + 2) ** 2 + me))
    ds = 1 + 2 * max(0, math.sqrt((me - 1) / (n + 1)) - 1) + cs; chi = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
    m, s, C, pc, ps = x0.copy(), sig0, np.eye(n), np.zeros(n), np.zeros(n)
    while c.used < budget:
        D, B = np.linalg.eigh(C); D = np.sqrt(np.maximum(D, 1e-12))
        zs = c.rng.normal(size=(lam, n)); ys = zs * D @ B.T
        xs = [np.clip(m + s * y, 0, 1) for y in ys]
        r = c.batch(xs, tables)
        o = np.argsort(-r)[:mu_n]
        yw = (ys[o] * w[:, None]).sum(0); m = np.clip(m + s * yw, 0, 1)
        ps = (1 - cs) * ps + math.sqrt(cs * (2 - cs) * me) * (B @ ((B.T @ yw) / D))
        hs = np.linalg.norm(ps) / math.sqrt(1 - (1 - cs) ** (2 * (c.used + 1))) < (1.4 + 2 / (n + 1)) * chi
        pc = (1 - cc) * pc + hs * math.sqrt(cc * (2 - cc) * me) * yw
        C = (1 - c1 - cm) * C + c1 * np.outer(pc, pc) + cm * (ys[o].T * w) @ ys[o]
        s *= math.exp((cs / ds) * (np.linalg.norm(ps) / chi - 1)); s = min(s, 0.4)
        c.mark(m)
    return m


def t_paired(c, x0, budget, sigma=0.1, lam=10, tables=30):
    """(1+lambda) with a two-stage acceptance on fresh tables, like the public repo's method."""
    x = x0.copy()
    while c.used < budget:
        xs = [x.copy()] + [np.clip(x + c.rng.normal(size=x.size) * sigma, 0, 1) for _ in range(lam)]
        r = c.batch(xs, tables)
        i = int(np.argmax(r))
        if i != 0:
            r2 = c.batch([x, xs[i]], tables * 3)
            if r2[1] > r2[0]:
                x = xs[i]; sigma = min(0.2, sigma * 1.1)
            else:
                sigma = max(0.03, sigma * 0.9)
        c.mark(x)
    return x


def t_spsa(c, x0, budget, a=0.05, ch=0.12, tables=60):
    x, k = x0.copy(), 1
    while c.used < budget:
        d = c.rng.choice([-1.0, 1.0], size=x.size)
        ck = ch / k ** 0.101
        r = c.batch([np.clip(x + ck * d, 0, 1), np.clip(x - ck * d, 0, 1)], tables)
        g = (r[0] - r[1]) / (2 * ck) * d
        x = np.clip(x + (a / (k + 5) ** 0.3) * g * 8, 0, 1)
        k += 1
        if k % 5 == 0:
            c.mark(x)
    return x


def t_halving(c, x0, budget, sigma=0.2, n=27, tables=8):
    """Successive halving: many candidates on few tables, the survivors on many; restart around the winner."""
    x = x0.copy()
    while c.used < budget:
        xs = [x.copy()] + [np.clip(x + c.rng.normal(size=x.size) * sigma, 0, 1) for _ in range(n - 1)]
        t = tables
        while len(xs) > 1:
            r = c.batch(xs, t)
            xs = [xs[i] for i in np.argsort(-r)[: max(1, len(xs) // 3)]]
            t *= 3
        x = xs[0]; sigma = max(0.04, sigma * 0.85)
        c.mark(x)
    return x


TUNERS = {"cem": t_cem, "cma": t_cma, "paired": t_paired, "spsa": t_spsa, "halving": t_halving}


def tune(name, spec_cls, search, start, budget, seed=1, fields=BLEND_FIELDS, payouts=ALLP, procs=10, **kw):
    fixed = dict(start)
    if spec_cls:
        fixed["cls"] = spec_cls
    box = Box(search, fixed)
    c = Ctx(box, fields, payouts, procs, seed)
    x = TUNERS[name](c, box.enc(start), budget, **kw)
    c.pool.close()
    return box.dec(x), c.log, c.used, time.time() - c.t0
````

<!-- FILE: lab/tune_event.py -->
````python
"""One-command event tune. Warm-starts from a params file on the blended field, with the real points table
weighted double if event_config.json exists, then reports old vs. new on fields the tuner never saw.

usage: tune_event.py --base tuned_final.json --out tuned_T2.json [--tuner cma] [--tables 40000] [--sigma 0.06] [--fields a,b] [--selfplay tuned_T1.json]
A cold retune for a new variant: --sigma 0.2. Exploiter files (exploit_*.json) next to this script join the field automatically.
Exit code 0 means new beat or matched old on holdout+stress, so it may be submitted after the gate.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tuner", default="cma"); ap.add_argument("--tables", type=int, default=40000); ap.add_argument("--sigma", type=float, default=0.06)
    ap.add_argument("--procs", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    ap.add_argument("--selfplay", default=None)
    ap.add_argument("--fields", default=None); ap.add_argument("--cls", default="table")
    a = ap.parse_args()
    # Workers import field.py fresh, so these must be set before any pool starts.
    os.environ["CAND_PATH"] = a.selfplay or a.base
    os.environ["CAND_TABLE"] = "1"
    here = os.path.dirname(os.path.abspath(__file__))
    ex = sorted(f for f in os.listdir(here) if f.startswith("exploit_") and f.endswith(".json"))
    os.environ["EXPLOIT_PATHS"] = ",".join(os.path.join(here, f) for f in ex)
    import mtune
    from run import evaluate, PAYOUTS
    base = json.load(open(a.base))["mu"]
    pays = ["real", "real", "top3", "steep"] if "real" in PAYOUTS else mtune.ALLP
    flds = a.fields.split(",") if a.fields else (mtune.ROBUST_FIELDS if ex else mtune.BLEND_FIELDS)
    start = dict(base)
    x, log, used, sec = mtune.tune(a.tuner, a.cls, mtune.FULL_SEARCH, start, a.tables, fields=flds, payouts=pays, procs=a.procs, sig0=a.sigma)
    x.pop("cls", None)
    json.dump({"mu": x}, open(a.out, "w"), indent=0)
    print(f"tuned {used} tables in {sec:.0f}s -> {a.out}")
    p = "real" if "real" in PAYOUTS else "steep"
    d = 0.0
    for f in ["holdout", "stress_mix"]:
        r, _ = evaluate({"old": dict(base, cls=a.cls), "new": dict(x, cls=a.cls)}, field=f, payouts=[p], tables=3000, procs=a.procs, seed=int(time.time()) % 100000)
        o, n = r["old"][p], r["new"][p]
        d += n[0] - o[0]
        print(f"{f:12} old {o[0]:7.2f}±{o[1]:.2f}  new {n[0]:7.2f}±{n[1]:.2f}  on {p}")
    print("VERDICT:", "promote (still run the gate)" if d >= 0 else "KEEP OLD: new lost on opponents the tuner never saw")
    sys.exit(0 if d >= 0 else 1)
````

<!-- FILE: lab/exploit_loop.py -->
````python
"""Find how exploitable a bot is, then harden it: train an exploiter, retune with it in the field, repeat.
usage: exploit_loop.py --base tuned_final.json --rounds 1 [--ex-tables 100000] [--def-tables 120000]
Writes exploit_<tag>_<k>.json and tuned_<tag>_<k>.json. Prints exploiter score at a table of 7 copies; fair share is points/8.
"""
import argparse, glob, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def L(n):
    return json.load(open(n))["mu"]


def save(n, mu):
    json.dump({"mu": {k: v for k, v in mu.items() if k != "cls"}}, open(n, "w"), indent=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--rounds", type=int, default=1); ap.add_argument("--tag", default=str(int(time.time()) % 100000))
    ap.add_argument("--ex-tables", type=int, default=100000); ap.add_argument("--def-tables", type=int, default=120000)
    ap.add_argument("--procs", type=int, default=max(2, (os.cpu_count() or 4) - 2))
    a = ap.parse_args()
    os.environ["CAND_TABLE"] = "1"
    import mtune, methods
    from run import evaluate, PAYOUTS
    p = "real" if "real" in PAYOUTS else "gym"
    fair = sum(PAYOUTS[p]) / 8.0
    pool = sorted(glob.glob("exploit_*.json"))
    cur = a.base
    for k in range(a.rounds + 1):
        os.environ["CAND_PATH"] = cur
        os.environ["EXPLOIT_PATHS"] = ""
        z = {f"w_{i}_{j}": 0.0 for i in range(5) for j in range(methods.N_FEAT)}
        x, _, _, sec = mtune.tune("cma", "linear0", methods.linear_search(3.0), {**L(a.base), **z}, a.ex_tables, seed=k + 1, fields=["all_mirror", "mirror"], payouts=[p, "top3"], procs=a.procs, sig0=0.2)
        ep = f"exploit_{a.tag}_{k}.json"
        save(ep, x)
        pool.append(ep)
        r, _ = evaluate({"exploiter": dict(x, cls="linear0"), "ours": dict(L(cur), cls="table")}, field="all_mirror", payouts=[p], tables=3000, procs=a.procs, seed=k + 9)
        print(f"round {k}: {cur}: exploiter scores {r['exploiter'][p][0]:.2f}, our bot {r['ours'][p][0]:.2f}, fair {fair:.2f} ({sec:.0f}s)", flush=True)
        if k == a.rounds:
            break
        os.environ["EXPLOIT_PATHS"] = ",".join(pool)
        d, _, _, sec = mtune.tune("cma", "table", mtune.FULL_SEARCH, L(cur), a.def_tables, seed=k + 50, fields=mtune.ROBUST_FIELDS, payouts=["gym", "top3", "linear", "wta"] if p == "gym" else [p, p, "top3", "steep"], procs=a.procs, sig0=0.1)
        cur = f"tuned_{a.tag}_{k + 1}.json"
        save(cur, d)
        print(f"retuned -> {cur} ({sec:.0f}s). Check it with the holdout before promoting.", flush=True)


if __name__ == "__main__":
    main()
````

<!-- FILE: lab/make_bot.py -->
````python
"""Generate one self-contained bot file with params and a preflop table inlined. Pure stdlib, no numpy.

usage: make_bot.py <tuned_json or -> <out.py>
"""
import json, os, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import pk
from hero import DEFAULT


TEMPLATE = r'''"""Reference poker policy: postflop equity vs. an estimated range, from a small lookup table or from
deadline-guarded rollouts with the lookup as fallback (see POSTFLOP_MC). Position-based preflop ranges,
and jam-or-fold when short. Exact ICM pricing and observed-range jam calls exist but are off.

Hard safety properties, in order of importance:
  1. Never raises an exception to the platform (a crash becomes check/fold).
  2. Every Monte Carlo loop stops at a deadline (BUDGET_S) well under the 1 ms limit.
  3. Tables are built at import, except a small rank cache whose misses cost microseconds.
"""
import gc
import random
import time
from itertools import combinations

BUDGET_S = 0.00035  # stop rollouts here; leaves margin for slower sandboxes
MAX_ROLLOUTS = 40  # tested: 40 about matches 100 on score, and costs about 60 us. Omaha evaluates 60x more combos.
PAYOUTS = __PAYOUTS__  # REPLACE with the announced points table, best place first
POSTFLOP_MC = __MC__  # True: deadline-guarded rollouts, falling back to the lookup. False: lookup only.
MIN_ROLLOUTS = 12  # with fewer finished rollouts than this, the Monte Carlo estimate is too noisy to use
USE_ICM_PRICE = False  # Tested: small gain on flat tables, large loss on top-heavy ones. Off unless the table is flat.
PARAMS = __PARAMS__
VARIANT = __VARIANT__
N_HOLE = __NHOLE__
if N_HOLE >= 4:
    MAX_ROLLOUTS = 6
DECK = __DECK__
PCT = __PCT__

_pc = time.perf_counter
_R = random.random

# ---- evaluator -------------------------------------------------------------------------------
_POW5 = [5 ** r for r in range(13)]
_KEY = [(_POW5[c >> 2] << 16) + (1 << (4 * (c & 3))) for c in range(52)]
_BIT = [1 << (c >> 2) for c in range(52)]
_STR = [0b1111100000000 >> i for i in range(9)] + [0b1000000001111]

def _sh(m):
    for i, s in enumerate(_STR):
        if m & s == s:
            return 12 - i if i < 9 else 3
    return -1

_MS = [_sh(m) for m in range(8192)]

def _top(m, n):
    o = 0
    for r in range(12, -1, -1):
        if m >> r & 1:
            o = o * 13 + r
            n -= 1
            if not n:
                break
    return o * 13 ** n

_FL = [0] * 8192
for _m in range(8192):
    if bin(_m).count("1") >= 5:
        _s = _MS[_m]
        _FL[_m] = (8 << 20) + _s if _s >= 0 else (5 << 20) + _top(_m, 5)

def _rv(key):
    cnt = [(key // _POW5[r]) % 5 for r in range(13)]
    m, q, t, p = 0, [], [], []
    for r in range(12, -1, -1):
        c = cnt[r]
        if c:
            m |= 1 << r
        if c == 4:
            q.append(r)
        elif c == 3:
            t.append(r)
        elif c == 2:
            p.append(r)
    if q:
        return (7 << 20) + q[0] * 13 + _top(m & ~(1 << q[0]), 1)
    if t and (len(t) > 1 or p):
        return (6 << 20) + t[0] * 13 + max(t[1:] + p)
    s = _MS[m]
    if s >= 0:
        return (4 << 20) + s
    if t:
        return (3 << 20) + t[0] * 169 + _top(m & ~(1 << t[0]), 2)
    if len(p) >= 2:
        return (2 << 20) + p[0] * 169 + p[1] * 13 + _top(m & ~(1 << p[0]) & ~(1 << p[1]), 1)
    if p:
        return (1 << 20) + p[0] * 2197 + _top(m & ~(1 << p[0]), 3)
    return _top(m, 5)

# Filled on demand: a miss costs a few microseconds, while prebuilding added about 300 ms to import.
_RC = {}

def evaluate(cards):
    k = 0
    for c in cards:
        k += _KEY[c]
    if (k + 0x3333) & 0x8888:
        low = k & 0xFFFF
        for s in range(4):
            if (low >> (4 * s)) & 15 >= 5:
                m = 0
                for c in cards:
                    if c & 3 == s:
                        m |= _BIT[c]
                return _FL[m]
    r = k >> 16
    v = _RC.get(r)
    if v is None:
        v = _RC[r] = _rv(r)
    return v

_SD_WHEEL = (1 << 12) | 0b11110000  # short deck A-6-7-8-9

def _rerank(cards, wheel):
    v = evaluate(cards)
    c = v >> 20
    if c == 5:
        return v * 2 + (3 << 20)
    if wheel and c < 4:
        m = 0
        for x in cards:
            m |= _BIT[x]
        if m & _SD_WHEEL == _SD_WHEEL:
            return ((4 << 20) + 3) * 2
    return v * 2

def made_hand(hole, board):
    """Base-ranking value of the best hand; features use this in every variant."""
    if VARIANT != "omaha":
        return evaluate(hole + board)
    best = 0
    for h in combinations(hole, 2):
        for b in combinations(board, 3):
            v = evaluate(list(h) + list(b))
            if v > best:
                best = v
    return best

if VARIANT == "shortdeck":
    def showdown(h, b):
        return _rerank(h + b, True)
elif VARIANT == "flushfh":
    def showdown(h, b):
        return _rerank(h + b, False)
else:
    showdown = made_hand

def canon(hole):
    cs = sorted(hole, key=lambda c: (-(c >> 2), c & 3))
    m, out = {}, []
    for c in cs:
        s = m.setdefault(c & 3, len(m))
        out.append((c >> 2) * 4 + s)
    return tuple(out)

def pct(hole):
    return PCT.get(canon(hole), 1.0)

_ALL = list(combinations(DECK, N_HOLE))
if len(_ALL) > 30000:  # Omaha-sized hand spaces: a fixed sample keeps import fast
    _ALL = random.Random(7).sample(_ALL, 20000)
_COMBOS = sorted(_ALL, key=pct)
del _ALL

def equity_vs_range(hole, board, width, max_rollouts, deadline, min_n=1):
    lim = max(8, int(width * len(_COMBOS)))
    known = set(hole)
    known.update(board)
    nb = 5 - len(board)
    wins, n, bl, combos = 0.0, 0, list(board), _COMBOS
    nd = len(DECK)
    for i in range(max_rollouts):
        if not i & 7 and _pc() > deadline:
            break
        v = combos[int(_R() * lim)]
        bad = False
        for c in v:
            if c in known:
                bad = True
                break
        if bad:
            continue
        run = bl
        if nb:
            run = bl[:]
            while len(run) < 5:
                c = DECK[int(_R() * nd)]
                if c not in known and c not in v and c not in run:
                    run.append(c)
        n += 1
        v1, v2 = showdown(hole, run), showdown(list(v), run)
        if v1 > v2:
            wins += 1
        elif v1 == v2:
            wins += 0.5
    if n < min_n:
        return None
    return wins / n

def icm_me(stacks, me, pay):
    n, total, memo = len(stacks), float(sum(stacks)), {}
    def rec(mask, place, remain):
        if not mask >> me & 1:
            return 0.0
        if mask in memo:
            return memo[mask]
        if remain <= 0:
            return 0.0
        res, pp = 0.0, pay[place] if place < len(pay) else 0.0
        for i in range(n):
            if mask >> i & 1 and stacks[i] > 0:
                p = stacks[i] / remain
                res += p * pp if i == me else p * rec(mask & ~(1 << i), place + 1, remain - stacks[i])
        memo[mask] = res
        return res
    return rec((1 << n) - 1, 0, total)

# ---- small strength model: feature cell -> equity at each villain range width --------------------
_WIDTHS = [0.08, 0.2, 0.4, 1.0]
_RAW = __STRENGTH__
_TAB = {tuple(int(x) for x in k.split(",")): v for k, v in _RAW.items()}
_BACK = {}  # rare cells back off to the first well-sampled cell with the same hand features
for _k, _v in _TAB.items():
    if _v[-1] >= 5:
        _BACK.setdefault(_k[:5], _v)

def feature(hole, board):
    a = hole + board
    v = made_hand(hole, board)
    cat = v >> 20
    bcat = evaluate(board) >> 20
    ranks = sorted((c >> 2 for c in board), reverse=True)
    top = ranks[0]
    hi = max(c >> 2 for c in hole)
    sub = 0
    if cat == 1:
        pr = (v - (1 << 20)) // 2197
        if bcat == 1:
            sub = 5 if hi >= 11 else 6 if hi >= 8 else 7
        elif pr > top:
            sub = 0 if pr >= 8 else 1
        elif pr == top:
            sub = 2 if hi >= 10 and hi != pr or pr >= 11 else 3
        elif len(ranks) > 1 and pr >= ranks[1]:
            sub = 4
        else:
            sub = 8
    elif cat == 0:
        sub = 0 if hi > top and hi == 12 else 1 if hi > top else 2
    else:
        sub = 1 if cat > bcat else 0
    fd = sd = 0
    if len(board) < 5:
        if VARIANT == "omaha":
            hc, bc = [0, 0, 0, 0], [0, 0, 0, 0]
            for c in hole:
                hc[c & 3] += 1
            for c in board:
                bc[c & 3] += 1
            for i in range(4):
                if hc[i] >= 2 and bc[i] == 2:
                    fd = 1
        else:
            cnt = [0, 0, 0, 0]
            for c in a:
                cnt[c & 3] += 1
            ms, s = cnt[0], 0
            for i in range(1, 4):
                if cnt[i] > ms:
                    ms, s = cnt[i], i
            if ms == 4 and any((c & 3) == s for c in hole):
                fd = 1
        m = 0
        for c in a:
            m |= 1 << (c >> 2)
        m = (m << 1) | (m >> 12 & 1)
        for i in range(10):
            b = (m >> i) & 31
            if b in (0b11110, 0b01111):
                sd = 2
                break
            if b in (0b11101, 0b11011, 0b10111):
                sd = max(sd, 1)
    c2 = [0, 0, 0, 0]
    for c in board:
        c2[c & 3] += 1
    w = max(c2)
    return (len(board), cat, sub, fd, sd, 1 if bcat >= 1 else 0, 2 if w >= 3 else 1 if w == 2 else 0)

def table_equity(hole, board, width):
    k = feature(hole, board)
    r = _TAB.get(k)
    if r is None or r[-1] < 5:
        r = _BACK.get(k[:5], r)
        if r is None:
            return 0.5
    if width <= _WIDTHS[0]:
        return r[0]
    for i in range(1, 4):
        if width <= _WIDTHS[i]:
            f = (width - _WIDTHS[i - 1]) / (_WIDTHS[i] - _WIDTHS[i - 1])
            return r[i - 1] * (1 - f) + r[i] * f
    return r[3]

# ---- policy ----------------------------------------------------------------------------------
FOLD, CALL = (0, 0), (1, 0)
JAM_CHART = [1.0, 0.69, 0.44, 0.34, 0.27, 0.22, 0.20, 0.18]

class State:
    """Normalised view of one decision; `adapt_observation` is the only place that knows the API."""
    __slots__ = ("seat", "hole", "board", "street", "pot", "to_call", "min_raise_to", "max_raise_to",
                 "can_raise", "stack", "bet", "cur", "sb", "bb", "stacks", "bets", "in_hand", "n_alive",
                 "n_live", "n_behind", "raises", "aggressor", "n_callers")

class Policy:
    def __init__(self):
        self.p = PARAMS
        self.vpip, self.hands, self.seen_vp, self.seen_h = {}, {}, set(), set()
        self.pf_raise, self.seen_pf = {}, set()

    def observe(self, seat, street, kind):
        """Call once per public action. kind: 0 fold, 1 check/call, 2 raise."""
        if street == 0:
            if seat not in self.seen_h:
                self.seen_h.add(seat)
                self.hands[seat] = self.hands.get(seat, 0) + 1
            if kind and seat not in self.seen_vp:
                self.seen_vp.add(seat)
                self.vpip[seat] = self.vpip.get(seat, 0) + 1
            if kind == 2 and seat not in self.seen_pf:
                self.seen_pf.add(seat)
                self.pf_raise[seat] = self.pf_raise.get(seat, 0) + 1

    def end_hand(self):
        self.seen_vp, self.seen_h, self.seen_pf = set(), set(), set()

    def _v(self, s):
        return (self.vpip.get(s, 0) + 3.0) / (self.hands.get(s, 0) + 10.0)

    def _foldrate(self, o):
        v = [self._v(s) for s in range(len(o.stacks)) if s != o.seat and o.in_hand[s]]
        return 1.0 - sum(v) / len(v) if v else 0.0

    def _rw(self, o):
        return 1.0 if o.aggressor < 0 else max(0.7, min(self.p["width_cap"], self._v(o.aggressor) / 0.3))

    def _eff(self, o):
        b = 0
        for s in range(len(o.stacks)):
            if s != o.seat and o.in_hand[s]:
                v = o.stacks[s] + o.bets[s]
                if v > b:
                    b = v
        return min(b, o.stack + o.bet)

    def _req(self, o):
        v = o.aggressor
        if v < 0 or not PAYOUTS:
            return None
        seats = [s for s in range(len(o.stacks)) if s == o.seat or o.stacks[s] + o.bets[s] > 0]
        if len(seats) > 6 or v not in seats:
            return None
        pay, me, vi = PAYOUTS[:len(seats)], seats.index(o.seat), seats.index(v)
        base = [o.stacks[s] for s in seats]
        pot = o.pot
        f = base[:]
        f[vi] += pot
        m = min(base[vi], max(0, base[me] - o.to_call))
        w = base[:]
        w[me] = base[me] + pot + m
        w[vi] = base[vi] - m
        l = base[:]
        l[me] = base[me] - o.to_call - m
        l[vi] = base[vi] + pot + o.to_call + m
        F, W = icm_me(f, me, pay), icm_me(w, me, pay)
        L = icm_me(l, me, pay) if l[me] > 0 else (pay[len(seats) - 1] if len(seats) - 1 < len(pay) else 0.0)
        return None if W - L <= 1e-9 else (F - L) / (W - L)

    def decide(self, o, deadline):
        p = self.p
        if USE_ICM_PRICE and PAYOUTS and o.to_call > 0.25 * o.stack and o.to_call > 0:
            req = self._req(o)
            if req is not None:
                if o.street == 0:
                    w = max(0.03, min(0.6, 0.12 * self._rw(o) * (1.6 if o.raises <= 1 else 1.0)))
                else:
                    w = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._rw(o)
                eq = equity_vs_range(o.hole, o.board, w, MAX_ROLLOUTS, deadline)
                if eq is not None:
                    opp = max(1, o.n_live - 1)
                    if opp > 1:
                        eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
                    if eq < req:
                        return FOLD
                    if eq > 0.72 and o.can_raise:
                        return (2, o.max_raise_to)
                    return CALL
        return self._pre(o, deadline) if o.street == 0 else self._post(o, deadline)

    def _pre(self, o, deadline):
        p = self.p
        hp = pct(o.hole)
        eff_m = self._eff(o) / float(o.sb + o.bb)
        margin = p["icm_margin"] if o.n_alive <= 4 else 0.0
        hu = o.n_alive == 2
        sh = 1.0 + p["sh_widen"] * (8 - o.n_alive) / 6.0
        if o.raises == 0:
            behind = o.n_behind
            fr = 1.0 + p["steal_fold_bonus"] * (self._foldrate(o) - 0.6)
            if eff_m < p["jam_m"]:
                w = p["jam_scale"] * JAM_CHART[min(behind, 7)] * max(0.25, 1.0 + p["jam_slope"] * (6.67 - eff_m))
                if hu:
                    w = max(w, p["hu_jam"])
                w *= fr
                if hp < w:
                    return (2, o.max_raise_to) if o.can_raise else CALL
                return CALL if o.to_call == 0 else FOLD
            w = (p["hu_open"] if hu else p["open_a"] + p["open_b"] / (behind + 0.5)) * fr
            if hp < w and o.can_raise:
                return (2, o.bb * (p["open_size"] + p["open_limp_add"] * o.n_callers))
            if o.to_call == 0:
                return CALL
            return CALL if o.to_call <= o.sb and hp < w * 1.6 else FOLD
        cost = o.to_call
        odds = cost / float(o.pot + cost)
        if p.get("hu_eqcall") and hu and o.aggressor >= 0 and (o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur) and (self.pf_raise.get(o.aggressor, 0) + 1.2) / (self.hands.get(o.aggressor, 0) + 10.0) >= p["hu_gate"]:
            # Heads-up there is no ICM to protect. Against a seat raising most hands, call on price.
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            eq = equity_vs_range(o.hole, [], max(0.03, min(1.0, rate * p["hu_vwidth"])), MAX_ROLLOUTS, deadline)
            if eq is not None:
                return CALL if eq > odds + p["hu_margin"] else FOLD
        if p.get("eqcall") and o.aggressor >= 0 and (o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur):
            # Equity vs. this seat's observed raising range, not a fixed tight assumption.
            v = o.aggressor
            rate = (self.pf_raise.get(v, 0) + 1.2) / (self.hands.get(v, 0) + 10.0)
            eq = equity_vs_range(o.hole, [], max(0.03, min(1.0, rate * p["vwidth_mult"])), MAX_ROLLOUTS, deadline)
            if eq is not None:
                opp = max(1, o.n_live - 1)
                if opp > 1:
                    eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
                return CALL if eq > odds + p["eqcall_margin"] + margin else FOLD
        if o.cur >= 0.5 * (o.stack + o.bet) or o.max_raise_to <= o.cur:
            w = p["call_jam"] * self._rw(o) * sh - margin * 0.5
            w += p["call_jam_short"] * max(0.0, 8.0 - eff_m) + max(0.0, odds - 0.33) * 0.5
            return CALL if hp < max(0.01, w) else FOLD
        if o.raises >= 2:
            if hp < p["fourbet"] and o.can_raise:
                return (2, o.max_raise_to)
            return CALL if hp < p["fourbet"] * 2 else FOLD
        a = self._rw(o) * sh
        if hp < p["threebet"] * a and o.can_raise:
            return (2, o.max_raise_to) if eff_m < 25 else (2, o.cur * p["threebet_mult"])
        wd = p["call_open"] * a + odds * p["call_odds"]
        if hu:
            wd = max(wd, p["hu_defend"] * (odds / 0.25) if odds >= 0.1 else 0.0)
        return CALL if hp < wd and cost < 0.2 * o.stack else FOLD

    def _post(self, o, deadline):
        p = self.p
        if o.aggressor >= 0 and o.to_call > 0:
            base = (p["range_raise"] if o.raises >= 2 else p["range_bet"]) * self._rw(o)
        else:
            base = p["range_unraised"]
        base = min(1.0, base * (1.0 + p["sh_range"] * (8 - o.n_alive) / 6.0))
        eq = None
        if POSTFLOP_MC:
            eq = equity_vs_range(o.hole, o.board, base, MAX_ROLLOUTS, deadline, MIN_ROLLOUTS)
        if eq is None:
            eq = table_equity(o.hole, o.board, base)
        opp = max(1, o.n_live - 1)
        if opp > 1:
            eq = eq ** (1 + 0.65 * (min(opp, 4) - 1))
        spr = o.stack / float(max(1, o.pot))
        margin = p["call_margin"] + (p["icm_margin"] if o.n_alive <= 4 else 0.0)
        if o.to_call == 0:
            if not o.can_raise:
                return CALL
            if eq > p["value_eq"]:
                return (2, o.max_raise_to) if spr < p["commit_spr"] else (2, o.pot * p["bet_frac"])
            if o.n_live == 2 and _R() < p["bluff_freq"]:
                return (2, o.pot * 0.5)
            return CALL
        odds = o.to_call / float(o.pot + o.to_call)
        if eq > p["raise_eq"] and o.can_raise:
            return (2, o.max_raise_to) if spr < 2.0 else (2, o.cur + o.pot * 0.8)
        return CALL if eq > odds + margin else FOLD

    def safe_decide(self, o):
        """Never raises; always returns a legal (kind, amount)."""
        t0 = _pc()
        try:
            kind, amt = self.decide(o, t0 + BUDGET_S)
            if kind == 2:
                if not o.can_raise:
                    return CALL
                return (2, int(min(o.max_raise_to, max(o.min_raise_to, amt))))
            if kind == 0 and o.to_call == 0:
                return CALL
            return (kind, 0)
        except Exception:
            return CALL if getattr(o, "to_call", 1) == 0 else FOLD

# Touch the tables so the first real decision doesn't pay for anything lazy.
_warm = [DECK[i] for i in range(N_HOLE)]
pct(_warm)
del _warm

# ---- platform adapter: rewrite these for the real Agent interface at kickoff ------------------
# The real API is unknown until the starter kit ships. Map its fields to State here and nowhere else.
def adapt_observation(obs):
    raise NotImplementedError("Map starter-kit fields to State, card ints: rank*4+suit, 2=0 .. A=12")

def to_platform_action(kind, amount, obs):
    raise NotImplementedError("Map (0,0) fold, (1,0) check/call, (2,to) raise-to onto the kit's action format")

gc.collect()
gc.freeze()
gc.disable()  # Cycle collection caused the one observed 1 ms breach. The policy creates no cycles.
'''


def build(params, payouts, out, mc=False):
    p = dict(DEFAULT)
    p.update(params)
    src = TEMPLATE.replace("__MC__", repr(mc)).replace("__PAYOUTS__", repr(payouts)).replace("__PARAMS__", repr({k: (round(v, 4) if isinstance(v, float) else v) for k, v in p.items()}))
    src = src.replace("__STRENGTH__", repr(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"strength_{pk.VARIANT}.json")))))
    src = src.replace("__PCT__", repr({k: v[0] for k, v in pk._T.items()}))
    src = src.replace("__VARIANT__", repr(pk.VARIANT)).replace("__NHOLE__", repr(pk.N_HOLE)).replace("__DECK__", repr(pk.DECK))
    # lab/adapter.py, if present, is appended, so the kit-specific code survives every regeneration.
    ad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adapter.py")
    if os.path.exists(ad):
        src += "\n# ---- lab/adapter.py ----\n" + open(ad).read()
    open(out, "w").write(src)


if __name__ == "__main__":
    # usage: make_bot.py <tuned_json or -> <out.py> [lookup|mc] [points as JSON]
    params = {} if sys.argv[1] == "-" else json.load(open(sys.argv[1]))["mu"]
    mode = sys.argv[3] if len(sys.argv) > 3 else "lookup"
    pts = json.loads(sys.argv[4]) if len(sys.argv) > 4 else [100, 60, 40, 25, 15, 10, 5, 0]
    build(params, pts, sys.argv[2], mc=mode == "mc")
    print("wrote", sys.argv[2], mode)
````

<!-- FILE: lab/build_tables.py -->
````python
"""Regenerate a variant's starting-hand table. usage: POKER_VARIANT=x python build_tables.py"""
import pk
if __name__ == "__main__":
    secs, n = pk.build_table()
    print(f"{pk.VARIANT}: {n} hand classes in {secs:.1f}s, wrote {pk._TABLE_PATH}")
````

<!-- FILE: lab/nash_hu.py -->
````python
"""Heads-up jam-or-fold Nash charts by fictitious play. Output: for each of 169 hand classes, the largest stack
in big blinds at which the small blind jams, and at which the big blind calls a jam. Variant-aware via pk."""
import json, os, random, sys, time
from itertools import combinations
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk

RK = "23456789TJQKA"


def _class(a, b):
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return RK[ra] * 2
    return RK[ra] + RK[rb] + ("s" if (a & 3) == (b & 3) else "o")


CLS = {}
for ab in combinations(pk.DECK, 2):
    CLS.setdefault(_class(*ab), []).append(list(ab))
NAMES = sorted(CLS, key=lambda c: pk.pct(CLS[c][0]))


def _pair(a):
    i, j, n, seed = a
    rng = random.Random(seed)
    A, B = CLS[NAMES[i]], CLS[NAMES[j]]
    valid = [(x, y) for x in A for y in B if not set(x) & set(y)]
    if not valid:
        return i, j, 0.5, 0
    w = 0.0
    for _ in range(n):
        x, y = rng.choice(valid)
        rest = [c for c in pk.DECK if c not in x and c not in y]
        b = rng.sample(rest, 5)
        v1, v2 = pk.showdown(x, b), pk.showdown(y, b)
        w += 1.0 if v1 > v2 else 0.5 if v1 == v2 else 0.0
    return i, j, w / n, len(valid)


def matrix(n=800, procs=8):
    m = len(NAMES)
    jobs = [(i, j, n, i * 1000 + j) for i in range(m) for j in range(i, m)]
    E, W = np.full((m, m), 0.5), np.zeros((m, m))
    with Pool(procs) as p:
        for i, j, e, c in p.imap_unordered(_pair, jobs, chunksize=64):
            E[i, j], E[j, i] = e, 1 - e
            W[i, j] = W[j, i] = c
    return E, W


def solve(E, W, S, iters=3000):
    """Fictitious play at stack S big blinds. Blinds 0.5 and 1. Returns jam and call frequencies."""
    m = len(NAMES)
    combos = np.array([len(CLS[n]) for n in NAMES], float)
    x, y = np.ones(m) * 0.5, np.ones(m) * 0.5
    for t in range(1, iters + 1):
        # SB best response to y: value of jamming with i, weighted by non-conflicting villain combos.
        wy = W * y
        tot = W.sum(1)
        pcall = wy.sum(1) / np.maximum(tot, 1)
        eqc = ((E * wy).sum(1)) / np.maximum(wy.sum(1), 1e-9)
        evj = (1 - pcall) * 1.0 + pcall * (eqc * 2 * S - S)
        bx = (evj > -0.5).astype(float)
        # BB best response to x.
        wx = W * x
        eqv = ((E * wx).sum(1)) / np.maximum(wx.sum(1), 1e-9)
        by = (eqv * 2 * S - S > -1.0).astype(float)
        a = 1.0 / (t + 1)
        x += a * (bx - x)
        y += a * (by - y)
    return x, y, combos


if __name__ == "__main__":
    t0 = time.time()
    E, W = matrix()
    print(f"equity matrix {time.time()-t0:.0f}s; AA vs 72o {E[NAMES.index('AA'), NAMES.index('72o')]:.3f}; AKs vs QQ {E[NAMES.index('AKs'), NAMES.index('QQ')]:.3f}")
    depths = [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30, 40]
    jam, call = {n: 0.0 for n in NAMES}, {n: 0.0 for n in NAMES}
    summary = []
    for S in depths:
        x, y, c = solve(E, W, S)
        summary.append((S, float((x * c).sum() / c.sum()), float((y * c).sum() / c.sum())))
        for i, n in enumerate(NAMES):
            if x[i] > 0.5:
                jam[n] = S
            if y[i] > 0.5:
                call[n] = S
    json.dump({"depths": depths, "jam": jam, "call": call, "summary": summary, "variant": pk.VARIANT}, open(f"nash_hu_{pk.VARIANT}.json", "w"), indent=0)
    print("S  jam%  call%")
    for S, a, b in summary:
        print(f"{S:4} {a:6.1%} {b:6.1%}")
    print("72o jam up to", jam["72o"], " call up to", call["72o"])
    print("A2o jam", jam["A2o"], "call", call["A2o"], "| K7s jam", jam["K7s"], "call", call["K7s"], "| 22 jam", jam["22"], "call", call["22"])
    print(f"total {time.time()-t0:.0f}s")
````

<!-- FILE: lab/test_bot.py -->
````python
"""Pre-submit gate: import time, first-call latency, fuzz legality, latency tail, and score parity.
usage: test_bot.py path/to/bot_dir"""
import importlib, random, sys, time, math
sys.path.insert(0, __file__.rsplit("/", 1)[0])
pc = time.perf_counter
t = pc()
sys.path.insert(0, sys.argv[1])
bot = importlib.import_module("bot")
print(f"import: {(pc()-t)*1e3:.1f} ms; variant {bot.VARIANT}")
import os
os.environ["POKER_VARIANT"] = bot.VARIANT  # the engine and opponents must play the same game as the bot
from engine import Obs, play_table, points_for
from field import ARCHETYPES, FIELDS
from run import PAYOUTS

class G:
    lat = []
    def __init__(self):
        self.p = bot.Policy()
    def act(self, o):
        t = pc()
        r = self.p.safe_decide(o)
        G.lat.append(pc() - t)
        return r
    def observe(self, seat, street, kind, amount):
        self.p.observe(seat, street, kind)
    def end_hand(self, n):
        self.p.end_hand()

# First decision after import, in a fresh policy.
o = Obs()
o.seat, o.hole, o.board, o.street, o.pot, o.to_call = 0, bot.DECK[-bot.N_HOLE:], [], 0, 30, 20
o.min_raise_to, o.max_raise_to, o.can_raise, o.stack, o.bet, o.cur, o.sb, o.bb = 40, 2000, True, 2000, 0, 20, 10, 20
o.stacks, o.bets, o.in_hand, o.n_alive, o.n_live, o.n_behind, o.raises, o.aggressor, o.n_callers = [2000]*8, [0]*8, [True]*8, 8, 8, 7, 0, -1, 0
t = pc(); r = bot.Policy().safe_decide(o); print(f"first decision: {(pc()-t)*1e6:.0f} us -> {r}")

# Fuzz: random and hostile states, including impossible ones. Must be legal and must not raise.
bad = 0
N = 200000
for i in range(N):
    n = random.randint(2, 8)
    st = [random.choice([0, 1, 5, 20, random.randint(0, 16000)]) for _ in range(8)]
    o.seat = random.randrange(8)
    st[o.seat] = random.choice([1, 5, 40, random.randint(1, 16000)])
    deck = random.sample(bot.DECK, 5 + bot.N_HOLE)
    o.hole = deck[:bot.N_HOLE]
    o.street = random.randrange(4)
    o.board = deck[bot.N_HOLE : bot.N_HOLE + [0, 3, 4, 5][o.street]]
    o.stack = st[o.seat]
    o.stacks = st
    o.bets = [random.choice([0, 0, 20, random.randint(0, 4000)]) for _ in range(8)]
    o.bet = o.bets[o.seat]
    o.in_hand = [random.random() < 0.6 for _ in range(8)]
    o.in_hand[o.seat] = True
    o.pot = random.choice([0, 1, 30, random.randint(0, 16000)])
    o.to_call = random.choice([0, 0, 1, random.randint(0, o.stack)])
    o.cur = o.bet + o.to_call
    o.max_raise_to = o.bet + o.stack
    o.min_raise_to = min(o.cur + random.choice([20, 40, 500]), o.max_raise_to)
    o.can_raise = o.stack > o.to_call and random.random() < 0.8
    o.sb, o.bb = random.choice([(10, 20), (250, 500), (1280, 2560)])
    o.n_alive, o.n_live, o.n_behind = n, random.randint(2, n), random.randint(0, n - 1)
    o.raises, o.n_callers = random.randint(0, 4), random.randint(0, 5)
    o.aggressor = random.choice([-1, random.randrange(8)])
    p = bot.Policy()
    # Force the crash path sometimes by sending garbage in a field.
    if i % 1000 == 0:
        o.hole = None
    k, a = p.safe_decide(o)
    ok = k in (0, 1, 2) and (k != 2 or (o.can_raise and o.min_raise_to <= a <= o.max_raise_to)) and not (k == 0 and o.to_call == 0 and o.hole is not None)
    bad += not ok
print(f"fuzz: {N} states, {bad} illegal or malformed")

# Real game parity and latency.
G.lat = []
pay = list(bot.PAYOUTS)
names = list(FIELDS["typical"]); w = [FIELDS["typical"][k] for k in names]
s = s2 = 0.0
T = 1500
for _ in range(T):
    pos = random.randrange(8)
    bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
    bots.insert(pos, G())
    e, nh, surv = play_table(bots)
    v = points_for(e, surv, pay)[pos]
    s += v; s2 += v * v
m = s / T
print(f"score vs typical on bot's points table: {m:.2f} ± {math.sqrt((s2/T-m*m)/T):.2f} (fair {sum(pay)/8:.2f})")
L = sorted(G.lat); n = len(L)
q = lambda p: L[min(n - 1, int(p * n))] * 1e6
print(f"latency n={n} p50={q(.5):.1f} p99={q(.99):.1f} p99.9={q(.999):.1f} p99.99={q(.9999):.1f} max={L[-1]*1e6:.1f} us, over 1 ms: {sum(1 for x in L if x > 1e-3)}, over 500 us: {sum(1 for x in L if x > 5e-4)}")
````

<!-- FILE: lab/test_engine.py -->
````python
"""Validates what the experiments rest on, using checks independent of the code under test."""
import random, sys
from itertools import combinations
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import pk, engine
from pk import evaluate, icm
from engine import play_table, points_for
from field import ARCHETYPES
from hero import Hero

fails = 0
def check(name, ok, detail=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name, detail)
    fails += not ok

# 1. Independent naive five-card evaluator, written differently: tuple of category then tiebreak ranks.
def naive5(cs):
    r = sorted((c >> 2 for c in cs), reverse=True)
    fl = len({c & 3 for c in cs}) == 1
    cnt = {x: r.count(x) for x in set(r)}
    by = sorted(cnt, key=lambda x: (-cnt[x], -x))
    shape = sorted(cnt.values(), reverse=True)
    st = -1
    if len(cnt) == 5:
        if r[0] - r[4] == 4:
            st = r[0]
        elif r == [12, 3, 2, 1, 0]:
            st = 3
    if st >= 0 and fl: return (8, st)
    if shape == [4, 1]: return (7, *by)
    if shape == [3, 2]: return (6, *by)
    if fl: return (5, *r)
    if st >= 0: return (4, st)
    if shape == [3, 1, 1]: return (3, *by)
    if shape == [2, 2, 1]: return (2, *by)
    if shape == [2, 1, 1, 1]: return (1, *by)
    return (0, *r)

def naive7(cs):
    return max(naive5(c) for c in combinations(cs, 5))

random.seed(3)
bad = 0
N = 60000
for _ in range(N):
    s = random.sample(range(52), 14)
    a, b = s[:7], s[7:]
    fa, fb = evaluate(a), evaluate(b)
    na, nb = naive7(a), naive7(b)
    if (fa > fb) != (na > nb) or (fa == fb) != (na == nb):
        bad += 1
check(f"7-card ordering agrees with naive evaluator on {N} random pairs", bad == 0, f"mismatches={bad}")
# Boards that force ties and shared hands.
bad = 0
for _ in range(20000):
    s = random.sample(range(52), 9)
    board = s[:5]
    a, b = s[5:7] + board, s[7:9] + board
    if (evaluate(a) > evaluate(b)) != (naive7(a) > naive7(b)) or (evaluate(a) == evaluate(b)) != (naive7(a) == naive7(b)):
        bad += 1
check("same-board comparisons, including chops, agree", bad == 0, f"mismatches={bad}")

# 2. Category frequency for 7 cards against published exact counts of 133,784,560 hands.
EXACT = {8: 41584, 7: 224848, 6: 3473184, 5: 4047644, 4: 6180020, 3: 6461620, 2: 31433400, 1: 58627800, 0: 23294460}
T = 400000
c = {k: 0 for k in EXACT}
for _ in range(T):
    c[evaluate(random.sample(range(52), 7)) >> 20] += 1
ok = True
for k, v in EXACT.items():
    p = v / 133784560
    se = (p * (1 - p) / T) ** 0.5
    if abs(c[k] / T - p) > 4.5 * se:
        ok = False
        print("   category", k, c[k] / T, p)
check("7-card category frequencies match exact counts", ok)

# 3. Known preflop equities.
aa = pk.hu_eq([48, 49])
check("AA vs random about 85.2%", abs(aa - 0.852) < 0.02, f"{aa:.3f}")
# 4. ICM against brute force over finishing orders.
from itertools import permutations
def brute(st, pay):
    n = len(st); out = [0.0] * n
    for perm in permutations(range(n)):
        p = 1.0; rem = float(sum(st))
        for i in perm:
            p *= st[i] / rem; rem -= st[i]
        for place, i in enumerate(perm):
            out[i] += p * (pay[place] if place < len(pay) else 0)
    return out
ok = True
for _ in range(50):
    n = random.randint(2, 5)
    st = [random.randint(1, 5000) for _ in range(n)]
    pay = sorted((random.randint(0, 100) for _ in range(n)), reverse=True)
    a, b = icm(st, pay), brute(st, pay)
    ok &= all(abs(x - y) < 1e-6 for x, y in zip(a, b))
check("ICM matches brute force", ok)

# 5. Hand-worked side pot. A 100, B 300, C 300 all-in; A has the best hand, B beats C.
class Script:
    def __init__(self, a): self.a = a
    def act(self, o): return self.a(o)
def jam(o): return (2, o.max_raise_to) if o.can_raise else (1, 0)
orig = engine.START
# Run the same settlement rule through the engine with rigged cards.
class RigRng:
    def __init__(self, cards, btn=0): self.cards, self.btn = cards, btn
    def randrange(self, n): return n - 1  # button moves to seat 0 first
    def sample(self, deck, k): return self.cards[:k]
sp = lambda s: ['23456789TJQKA'.index(s[i]) * 4 + 'shdc'.index(s[i + 1]) for i in range(0, len(s), 2)]

def one_hand(stacks, cards, sb=10, bb=20):
    """Single rigged hand using the engine's table loop with chosen starting stacks."""
    n = len(stacks)
    res = {}
    class B:
        def __init__(s, i): s.i = i
        def act(s, o): return jam(o)
        def end_hand(s, h): raise StopIteration
    # Patch stacks through a temporary copy of the module constant.
    start = engine.START
    return None

# Chip conservation and rule invariants over many real tables, with deep instrumentation through wrappers.
class Audit:
    def __init__(self, inner):
        self.b = inner
        if hasattr(inner, "observe"): self.observe = inner.observe
        if hasattr(inner, "end_hand"): self.end_hand = inner.end_hand
    def act(self, o):
        Audit.calls += 1
        total = sum(o.stacks) + o.pot
        if total > engine.START * 8 or total < 0: Audit.bad.append(("chips above total", total))
        if min(o.stacks) < 0: Audit.bad.append(("negative stack", list(o.stacks)))
        if o.to_call < 0 or o.to_call > o.stack: Audit.bad.append(("to_call", o.to_call, o.stack))
        if o.can_raise and not (o.min_raise_to <= o.max_raise_to): Audit.bad.append(("raise bounds", o.min_raise_to, o.max_raise_to))
        if o.max_raise_to != o.bet + o.stack: Audit.bad.append(("max raise", o.max_raise_to))
        if o.hole is None or len(set(o.hole + o.board)) != len(o.hole) + len(o.board): Audit.bad.append(("dup cards",))
        if len(o.board) != [0, 3, 4, 5][o.street]: Audit.bad.append(("board size", o.street, len(o.board)))
        return self.b.act(o)
Audit.calls = 0; Audit.bad = []
names = ["fold", "random", "station", "maniac", "jam20", "jam08", "tag", "nit", "lag", "mc", "shortfold", "allin", "minraise", "potsize", "bully", "pusher"]
PAYS = [[50, 30, 20, 0, 0, 0, 0, 0], [100, 50, 30, 20, 10, 5, 2, 0], [7, 6, 5, 4, 3, 2, 1, 0]]
pt_bad = chip_bad = capped = 0
TAB = 4000
for t in range(TAB):
    bots = [Audit(ARCHETYPES[random.choice(names)]()) for _ in range(7)] + [Audit(Hero())]
    random.shuffle(bots)
    e, nh, s = play_table(bots)
    capped += nh >= engine.MAX_HANDS
    # Every seat is accounted for exactly once.
    seen = [x for g in e for x in g] + list(s)
    if sorted(seen) != list(range(8)): chip_bad += 1
    # Final chips are conserved when anyone survives.
    if sum(s.values()) != engine.START * 8: chip_bad += 1
    for pay in PAYS:
        pts = points_for(e, s, pay)
        if abs(sum(pts) - sum(pay)) > 1e-6 or min(pts) < -1e-9: pt_bad += 1
check(f"invariants across {Audit.calls} decisions", not Audit.bad, str(Audit.bad[:3]))
check(f"chips conserved and all seats placed on {TAB} tables", chip_bad == 0, f"bad={chip_bad}; reached 200-hand cap: {capped/TAB:.0%}")
check("points conserved on every table", pt_bad == 0, f"bad={pt_bad}")

# 6. Hand-worked side pot through the settle rule: rig seats and cards so the result is known.
class Stacked:
    """Plays one table where everyone jams, with known cards; verifies main and side pot payout."""
import types
src = open(engine.__file__).read().replace("stacks = [START] * n", "stacks = list(STACKS)")
m = types.ModuleType("rigged"); m.__dict__["STACKS"] = None; m.__dict__["__file__"] = engine.__file__
sys.modules["rigged"] = m
exec(compile(src, "rigged", "exec"), m.__dict__)
def rig(stacks, board, holes, max_hands=1):
    # Button lands on seat 0 because randrange returns n-1.
    m.STACKS = stacks; m.MAX_HANDS = max_hands
    n = len(stacks)
    live = [i for i in range(n) if stacks[i] > 0]
    cards = sp(board) + [c for seat in live for c in sp(holes[seat])]
    bots = [types.SimpleNamespace(act=jam) for _ in range(n)]
    e, nh, surv = m.play_table(bots, [(10, 20)], RigRng(cards))
    return {i: surv.get(i, 0) for i in range(n)}
# Three-way: seat 0 has 100, seats 1, 2 have 300. Board is rainbow low, 0: AA, 1: KK, 2: QQ.
r = rig([100, 300, 300], "2s7h9dJc3s", {0: "AsAh", 1: "KsKh", 2: "QsQh"})
check("side pot: short AA wins main 300, KK wins side 400", r == {0: 300, 1: 400, 2: 0}, str(r))
# Short stack loses to the side-pot winner, and the excess bet is returned to the big stack.
r = rig([100, 300, 900], "2s7h9dJc3s", {0: "4s4h", 1: "QsQh", 2: "KsKh"})
check("uncalled excess returned", r == {0: 0, 1: 0, 2: 1300}, str(r))
# Chop between two equal stacks with a board straight.
r = rig([200, 200], "TsJhQdKcAs", {0: "2s2h", 1: "3s3h"})
check("board-plays chop", r == {0: 200, 1: 200}, str(r))
print("\nALL PASS" if not fails else f"\n{fails} FAILED")
````

<!-- FILE: lab/test_parity.py -->
````python
"""Generated bot vs. lab lookup policy: same decisions on the same states, and the same score."""
import json, math, random, sys, os
sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), sys.argv[1]]
import bot
os.environ["POKER_VARIANT"] = bot.VARIANT
import pk
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS
from strength import HeroTable, table_equity, feature
params = dict(bot.PARAMS)
# 1. Feature and equity agreement on random states.
bad = 0
for _ in range(100000):
    st = random.choice((3, 4, 5))
    s = random.sample(bot.DECK, bot.N_HOLE + st)
    h, b = s[:bot.N_HOLE], s[bot.N_HOLE:]
    w = random.choice([0.05, 0.1, 0.3, 0.7, 1.0])
    if abs(bot.table_equity(h, b, w) - table_equity(h, b, w)) > 1e-9 or bot.feature(h, b) != feature(h, b):
        bad += 1
print("feature/equity mismatches:", bad)
# 2. Decision agreement in real play, with one shadowing the other on the same event stream.
class Shadow:
    n = same = 0
    diffs = {}
    ex = []
    def __init__(self):
        self.g, self.l = bot.Policy(), HeroTable(**params)
    def act(self, o):
        rs = random.getstate()
        a = self.g.safe_decide(o)
        random.setstate(rs)  # both policies must see the same random draw
        b = self.l.act(o)
        kb, ab = b
        if kb == 2:
            if not o.can_raise:
                kb, ab = 1, 0
            else:
                ab = int(min(o.max_raise_to, max(o.min_raise_to, ab)))
        else:
            ab = 0
            if kb == 0 and o.to_call == 0:
                kb = 1
        Shadow.n += 1
        if a == (kb, ab):
            Shadow.same += 1
        else:
            key = ("pre" if o.street == 0 else "post", a[0], kb)
            if len(Shadow.ex) < 3:
                Shadow.ex.append((a, (kb, ab), o.street, o.raises, o.n_alive, o.n_behind, o.to_call, o.stack, list(o.hole)))
            Shadow.diffs[key] = Shadow.diffs.get(key, 0) + 1
        return a
    def observe(self, s, st, k, am):
        self.g.observe(s, st, k)
        self.l.observe(s, st, k, am)
    def end_hand(self, n):
        self.g.end_hand()
        self.l.end_hand(n)
names = list(FIELDS["typical"]); w = [FIELDS["typical"][k] for k in names]
for _ in range(int(sys.argv[2])):
    bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
    bots.insert(random.randrange(8), Shadow())
    play_table(bots)
print(f"decisions {Shadow.n}, identical {Shadow.same} ({100*Shadow.same/max(1,Shadow.n):.2f}%)", Shadow.diffs)
print(Shadow.ex)
````

<!-- FILE: make_submission.sh -->
````bash
#!/bin/zsh
# usage: ./make_submission.sh <params.json> <lookup|mc> '<points JSON>'  ->  submission/bot.py, gated.
# lab/adapter.py is appended automatically when it exists. Set POKER_VARIANT for non-hold'em.
set -e
ROOT=${0:A:h}; PY=${PY:-$ROOT/.venv/bin/python}; PARAMS=${1:A}
mkdir -p $ROOT/submission $ROOT/reference_bot
cd $ROOT/lab
$PY make_bot.py $PARAMS $ROOT/submission/bot.py ${2:-lookup} ${3:-'[50,30,20,0,0,0,0,0]'}
$PY test_bot.py $ROOT/submission
cp $ROOT/submission/bot.py $ROOT/reference_bot/bot.py
rm -rf $ROOT/submission/__pycache__
echo "PASSES only if: 0 illegal, and latency looks fine above. Then test through the kit before submitting."
````

<!-- FILE: benchmark/slumbot_client.py -->
````python
"""Plays a generated reference bot against Slumbot's public API, one request at a time. stdlib only.
usage: slumbot_client.py <bot_dir> --hands N [--log hands.jsonl] [--delay 0.1]

Format differs from the tournament: heads-up cash, 50/100, 200 BB, stacks reset every hand.
Use this to find postflop and heads-up leaks, not to predict tournament score.
"""
import argparse, itertools, json, math, os, sys, time, urllib.request

URL = "https://slumbot.com/slumbot/api/"
SB, BB, STACK = 50, 100, 20000
RK, SU = "23456789TJQKA", "shdc"
CARD = {r + s: i * 4 + j for i, r in enumerate(RK) for j, s in enumerate(SU)}


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "poker-benchmark-client"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def parse(action):
    """Returns one dict of current-street state plus an event list, from an action string like b200c/kb400."""
    streets = action.split("/")
    total = [0, 0]  # by order: 0 = small blind / first preflop, 1 = big blind
    events = []
    cur_st = {}
    for si, s in enumerate(streets):
        bets = [SB, BB] if si == 0 else [0, 0]
        cur, last = (BB, BB) if si == 0 else (0, BB)
        actor = 0 if si == 0 else 1
        raises, aggressor = 0, -1
        i = 0
        while i < len(s):
            ch = s[i]
            i += 1
            if ch == "b":
                j = i
                while j < len(s) and s[j].isdigit():
                    j += 1
                to = int(s[i:j]); i = j
                if to - cur > last:
                    last = to - cur
                cur = to; bets[actor] = to; raises += 1; aggressor = actor
                events.append((si, actor, 2))
            elif ch == "c":
                bets[actor] = cur; events.append((si, actor, 1))
            elif ch == "k":
                events.append((si, actor, 1))
            elif ch == "f":
                events.append((si, actor, 0))
            actor = 1 - actor
        cur_st = dict(street=si, bets=bets, cur=cur, last=last, actor=actor, raises=raises, aggressor=aggressor, prior=list(total))
        if si < len(streets) - 1:
            total = [total[0] + bets[0], total[1] + bets[1]]
    cur_st["total"] = total
    return cur_st, events


def seen_acts(action):
    return action.split("/")[-1]


def decide(ref, policy, r, n_seen):
    """Maps a Slumbot response to the policy's normalised State. In the policy's view we are seat 0, Slumbot seat 1."""
    action, pos = r["action"], r["client_pos"]
    me = 1 if pos == 0 else 0  # client_pos 0 means big blind; preflop index 1
    st, events = parse(action)
    for si, who, kind in events[n_seen:]:
        policy.observe(0 if who == me else 1, si, kind)
    n_seen = len(events)
    o = ref.State()
    bets = st["bets"]
    prior = st["total"]
    my_bet, op_bet = bets[me], bets[1 - me]
    my_stack = STACK - prior[me] - my_bet
    op_stack = STACK - prior[1 - me] - op_bet
    o.seat = 0
    o.hole = [CARD[c] for c in r["hole_cards"]]
    o.board = [CARD[c] for c in r["board"]]
    o.street = st["street"]
    o.pot = sum(prior) + sum(bets)
    o.to_call = min(st["cur"] - my_bet, my_stack)
    o.cur = st["cur"]
    o.stack, o.bet = my_stack, my_bet
    o.sb, o.bb = SB, BB
    o.stacks, o.bets = [my_stack, op_stack], [my_bet, op_bet]
    o.in_hand = [True, True]
    o.n_alive, o.n_live = 2, 2
    # On a new street, or facing no bet when first to act, the opponent acts behind us.
    o.n_behind = 1 if (o.to_call == 0 and st["raises"] == 0 and (st["actor"] == (0 if st["street"] == 0 else 1))) or (st["street"] == 0 and st["raises"] == 0 and me == 0) else 0
    o.raises = st["raises"]
    o.aggressor = -1 if st["aggressor"] < 0 else (0 if st["aggressor"] == me else 1)
    o.n_callers = 0
    o.max_raise_to = my_bet + my_stack
    o.min_raise_to = min(st["cur"] + st["last"], o.max_raise_to)
    o.can_raise = op_stack > 0 and my_stack > o.to_call
    k, a = policy.safe_decide(o)
    if k == 2:
        return f"b{int(a)}", n_seen
    if k == 1:
        return ("k" if o.to_call == 0 else "c"), n_seen
    return "f", n_seen


def allin_adjusted(ref, r, winnings):
    """If both players were all-in before the river and cards were shown, replace the result with expected chips."""
    bot = r.get("bot_hole_cards")
    act = r.get("action", "")
    if not bot or not act.endswith("/") or "f" in act.split("/")[-1]:
        return winnings
    hole = [CARD[c] for c in r["hole_cards"]]
    opp = [CARD[c] for c in bot]
    streets = act.split("/")
    known = {0: 0, 1: 3, 2: 4, 3: 5}
    idx = 0
    for i, s in enumerate(streets):
        if s:
            idx = i
    nb = known.get(idx, 5)
    board = [CARD[c] for c in r["board"]][:nb]
    if len(board) >= 5:
        return winnings
    deck = [c for c in range(52) if c not in hole and c not in opp and c not in board]
    w = t = 0.0
    for extra in itertools.combinations(deck, 5 - len(board)):
        b = board + list(extra)
        a, v = ref.evaluate(hole + b), ref.evaluate(opp + b)
        w += 1.0 if a > v else 0.5 if a == v else 0.0
        t += 1
    return (2 * w / t - 1) * abs(winnings) if winnings else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("bot_dir"); ap.add_argument("--hands", type=int, default=20)
    ap.add_argument("--log", default=None); ap.add_argument("--delay", type=float, default=0.1)
    a = ap.parse_args()
    sys.path.insert(0, a.bot_dir)
    import bot as ref
    token = None
    results = []
    logf = open(a.log, "a", buffering=1) if a.log else None
    err = 0
    for h in range(a.hands):
        try:
            body = {"token": token} if token else {}
            r = post("new_hand", body)
            token = r.get("token", token)
            policy = ref.Policy()
            n_seen = 0
            while "winnings" not in r:
                inc, n_seen = decide(ref, policy, r, n_seen)
                time.sleep(a.delay)
                body = {"token": token, "incr": inc}
                r2 = post("act", body)
                if "error_msg" in r2:
                    err += 1
                    print("API error:", r2["error_msg"], "after", r["action"], "sent", inc, file=sys.stderr, flush=True)
                    r2 = post("act", {"token": token, "incr": "k" if inc in ("k",) else "c"})
                    if "error_msg" in r2:
                        r2 = post("act", {"token": token, "incr": "f"})
                r = r2
                token = r.get("token", token)
            w = r["winnings"]
            adj = allin_adjusted(ref, r, w)
            results.append((w, adj))
            if logf:
                logf.write(json.dumps({"w": w, "adj": adj, "action": r["action"], "pos": r["client_pos"], "hole": r["hole_cards"], "board": r["board"], "bot": r.get("bot_hole_cards")}) + "\n")
        except Exception as e:
            err += 1
            print("error:", repr(e), file=sys.stderr, flush=True)
            time.sleep(5)
            token = None
        if (h + 1) % 100 == 0 or h + 1 == a.hands:
            n = len(results)
            for lab, i in (("raw", 0), ("allin-adj", 1)):
                m = sum(x[i] for x in results) / n
                sd = math.sqrt(sum((x[i] - m) ** 2 for x in results) / max(1, n - 1))
                print(f"{n} hands {lab}: {m/BB*100:+.1f} ± {sd/math.sqrt(n)/BB*100:.1f} bb/100", flush=True)
            print(f"errors so far: {err}", flush=True)
            time.sleep(0)
````

<!-- FILE: rehearsal/README.md -->
````markdown
# Sealed rehearsal (60 minutes)

This practices the event: an unfamiliar interface, a surprise rule change, and a clock. **It is a mock.** The real kit will differ, so what you're practicing is the process.

## Setup (person who won't build, 2 minutes)

1. Edit `kit/rules_card.json` with a points table and blind schedule of your choosing.
2. Pick a variant: `holdem`, `shortdeck`, `flushfh`, `hole3` or `omaha`.
3. Tell the builders only at the start.

## Run

From `rehearsal/kit`:

```bash
# Use the project's Python. Set the variant in the shell for every run:
export POKER_VARIANT=shortdeck
# Variant tables must exist for the simulator's opponents (from lab/):
#   ../../.venv/bin/python ../../lab/build_tables.py

../../.venv/bin/python simulate.py my_bot_template.py MyAgent 500            # the baseline
../../.venv/bin/python simulate.py path/to/your_bot.py MyAgent 1000 typical  # your bot
../../.venv/bin/python simulate.py path/to/your_bot.py MyAgent 1000 holdout  # unseen opponents
```

The doc at the top of `kit/agent.py` is your only interface spec. Don't read `solution/` first.

## Pass criteria

- A legal bot in under 15 minutes.
- 0 errors and 0 illegal actions.
- Few or no over-1-ms decisions when the machine isn't busy.
- A clear win over the check/fold template on `holdout`, which scored 42 against `typical` on the placeholder table (fair share 31.9). Scores are only comparable with the same rules card and field.

## Traps built in on purpose

- `chips` excludes `street_bet`.
- Raises are expressed as chips **above the call**, not as a total.
- `max(street_bets)` isn't always the amount to call. A big blind all-in for less still sets the full amount.
- History covers only the current hand and is delivered only at your decisions, so you never see actions after your last one.
- You aren't told who raised or how many players remain to act. You have to derive both.

## Afterward

Write down what cost the most time, then fix that part of the process before tomorrow.
````

<!-- FILE: rehearsal/kit/agent.py -->
````python
"""Mock starter kit for rehearsal. NOT the official interface, which is unknown until kickoff.
It is deliberately awkward so wiring practice is realistic.

Implement:
    class MyAgent(Agent):
        def reset(self, seat, n_players): ...       # called at the start of each table
        def get_action(self, state): ...            # must return within 1 ms

state is a dict:
    hand_id, street ("preflop" | "flop" | "turn" | "river"), my_seat, dealer_seat, small_blind, big_blind
    hole:       card strings, e.g. ["As", "Td"]
    community:  card strings
    players:    list by seat: {"seat", "chips", "street_bet", "status"}
                chips EXCLUDES street_bet; status: "active", "allin", "folded", "out"
    pot:        all chips committed this hand, including street bets
    legal:      {"can_check": bool, "call_cost": int, "raise_by_min": int or None, "raise_by_max": int or None}
    history:    this hand only, oldest first: {"street", "seat", "action", "amount"}
                action: "sb", "bb", "fold", "check", "call", "raise"

Return a dict:
    {"action": "fold"} | {"action": "check"} | {"action": "call"}
    {"action": "raise", "by": N}  # chips ABOVE the call, on top of matching the current bet
Anything illegal, any exception, or any overrun counts as check-else-fold.
"""


class Agent:
    def reset(self, seat, n_players):
        pass

    def get_action(self, state):
        raise NotImplementedError
````

<!-- FILE: rehearsal/kit/simulate.py -->
````python
"""Rehearsal simulator. usage: python simulate.py path/to/my_bot.py MyAgent [tables] [field]
Set POKER_VARIANT (holdem, shortdeck, flushfh, hole3, omaha) before running to change the rules."""
import importlib.util, json, os, random, sys, time, math
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "..", "lab"))
sys.path.insert(0, ROOT)
from engine import play_table, points_for
from field import ARCHETYPES, FIELDS

RULES = json.load(open(os.path.join(ROOT, "rules_card.json")))
RK, SU = "23456789TJQKA", "shdc"
S = lambda c: RK[c >> 2] + SU[c & 3]
ST = ["preflop", "flop", "turn", "river"]
pc = time.perf_counter


class Bridge:
    """Presents the engine to a kit-style agent, and enforces rule 3.7 on it."""
    def __init__(self, agent):
        self.a, self.hist, self.hand, self.seat_known = agent, [], -1, False
        self.lat, self.err, self.illegal, self.over = [], 0, 0, 0
        self.cur_hand = 0

    def observe(self, seat, street, kind, amount):
        name = ("fold", "call", "raise")[kind]
        if kind == 1 and amount == 0:
            name = "check"
        self.hist.append({"street": ST[street], "seat": seat, "action": name, "amount": amount})

    def end_hand(self, n):
        # Normal: history is only ever delivered at decisions, so actions after our last decision are never seen.
        # KIT_FULL_HISTORY delivers them, by replaying the finished hand to an optional agent hook.
        if os.environ.get("KIT_FULL_HISTORY") and hasattr(self.a, "hand_over"):
            self.a.hand_over(self.hist)
        self.hist = []

    def act(self, o):
        if not self.seat_known:
            self.a.reset(o.seat, len(o.stacks))
            self.seat_known = True
        st = []
        for i in range(len(o.stacks)):
            s = "out" if o.stacks[i] + o.bets[i] <= 0 and not o.in_hand[i] else "folded" if not o.in_hand[i] else "allin" if o.stacks[i] == 0 else "active"
            st.append({"seat": i, "chips": o.stacks[i], "street_bet": o.bets[i], "status": s})
        rb = o.min_raise_to - o.cur if o.can_raise else None
        state = {
            "hand_id": o.hand_no, "street": ST[o.street], "my_seat": o.seat, "dealer_seat": o.button,
            "small_blind": o.sb, "big_blind": o.bb, "hole": [S(c) for c in o.hole], "community": [S(c) for c in o.board],
            "players": st, "pot": o.pot,
            "legal": {"can_check": o.to_call == 0, "call_cost": o.to_call, "raise_by_min": rb,
                      "raise_by_max": (o.max_raise_to - o.cur) if o.can_raise else None},
            "history": list(self.hist),
        }
        t = pc()
        try:
            r = self.a.get_action(state)
        except Exception as e:
            self.err += 1
            return (1, 0) if o.to_call == 0 else (0, 0)
        d = pc() - t
        self.lat.append(d)
        if d > 1e-3:
            self.over += 1
            if not os.environ.get("KIT_NO_DEADLINE"):
                return (1, 0) if o.to_call == 0 else (0, 0)
        try:
            k = r["action"]
            if k == "fold":
                return (0, 0)
            if k == "check" and o.to_call == 0:
                return (1, 0)
            if k == "call" and o.to_call > 0:
                return (1, 0)
            if k == "raise" and o.can_raise and rb <= r["by"] <= o.max_raise_to - o.cur:
                return (2, o.cur + int(r["by"]))
        except Exception:
            pass
        self.illegal += 1
        if os.environ.get("KIT_DEBUG") and self.illegal <= 3:
            print("ILLEGAL", r, "to_call", o.to_call, "cur", o.cur, "min", o.min_raise_to, "max", o.max_raise_to, "can_raise", o.can_raise, "stack", o.stack, "bet", o.bet, file=sys.stderr)
        return (1, 0) if o.to_call == 0 else (0, 0)


def main():
    path, cname = sys.argv[1], sys.argv[2]
    T = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    fld = sys.argv[4] if len(sys.argv) > 4 else "typical"
    spec = importlib.util.spec_from_file_location("my_bot", path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    t = pc()
    spec.loader.exec_module(m)
    print(f"import {1e3*(pc()-t):.0f} ms")
    cls = getattr(m, cname)
    names = list(FIELDS[fld]); w = [FIELDS[fld][k] for k in names]
    pay = RULES["points"]
    sch = [tuple(x) for x in RULES["blinds"]]
    s = s2 = 0.0; lat = []; err = ill = over = 0
    for _ in range(T):
        pos = random.randrange(8)
        b = Bridge(cls())
        bots = [ARCHETYPES[x]() for x in random.choices(names, w, k=7)]
        bots.insert(pos, b)
        e, nh, surv = play_table(bots, sch)
        v = points_for(e, surv, pay)[pos]
        s += v; s2 += v * v
        lat += b.lat; err += b.err; ill += b.illegal; over += b.over
    mean = s / T
    print(f"score {mean:.2f} ± {math.sqrt(max(0, s2/T-mean*mean)/T):.2f} (fair {sum(pay)/8:.2f}) on field {fld}")
    print(f"errors {err}, illegal {ill}, over 1 ms {over}")
    lat.sort()
    if lat:
        n = len(lat)
        print(f"latency us p50 {lat[n//2]*1e6:.1f} p99 {lat[int(.99*n)]*1e6:.1f} p99.9 {lat[int(.999*n)]*1e6:.1f} max {lat[-1]*1e6:.1f}")


if __name__ == "__main__":
    main()
````

<!-- FILE: rehearsal/kit/rules_card.json -->
````json
{"points": [100, 60, 40, 25, 15, 10, 5, 0],
 "blinds": [[10,20],[15,30],[25,50],[40,80],[60,120],[100,200],[150,300],[250,500]],
 "note": "Placeholder values. Change these for each rehearsal so the bot can't assume them."}
````

<!-- FILE: rehearsal/kit/my_bot_template.py -->
````python
from agent import Agent


class MyAgent(Agent):
    def get_action(self, state):
        return {"action": "check"} if state["legal"]["can_check"] else {"action": "fold"}
````

<!-- FILE: rehearsal/solution/adapted_bot.py -->
````python
"""Worked adapter: rebuilds the reference policy's inputs from the mock kit's minimal state.
Rewrite this one file for the real kit. The policy itself should not change."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reference_bot"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
from agent import Agent
import bot as ref

RK, SU = "23456789TJQKA", "shdc"
CARD = {r + s: i * 4 + j for i, r in enumerate(RK) for j, s in enumerate(SU)}
STREET = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}
KIND = {"fold": 0, "check": 1, "call": 1, "raise": 2}


class MyAgent(Agent):
    def __init__(self):
        self.p = ref.Policy()
        self.last_hand, self.seen = -1, 0

    def hand_over(self, hist):
        # Only used if the kit reveals the actions that followed our last decision.
        for ev in hist[self.seen:]:
            if ev["action"] in KIND:
                self.p.observe(ev["seat"], STREET[ev["street"]], KIND[ev["action"]])
        self.seen = len(hist)

    def get_action(self, s):
        p = self.p
        leg = s["legal"]
        try:
            if s["hand_id"] != self.last_hand:
                p.end_hand()
                self.last_hand, self.seen = s["hand_id"], 0
            h = s["history"]
            for ev in h[self.seen:]:
                if ev["action"] in KIND:
                    p.observe(ev["seat"], STREET[ev["street"]], KIND[ev["action"]])
            self.seen = len(h)
            o = ref.State()
            pl = s["players"]
            me = s["my_seat"]
            street = s["street"]
            o.seat = me
            o.hole = [CARD[c] for c in s["hole"]]
            o.board = [CARD[c] for c in s["community"]]
            o.street = STREET[street]
            o.pot = s["pot"]
            o.to_call = leg["call_cost"]
            o.stack = pl[me]["chips"]
            o.bet = pl[me]["street_bet"]
            o.sb, o.bb = s["small_blind"], s["big_blind"]
            o.stacks = [x["chips"] for x in pl]
            o.bets = [x["street_bet"] for x in pl]
            o.in_hand = [x["status"] in ("active", "allin") for x in pl]
            # Not max(bets): a big blind all-in for less still sets the full amount to call.
            o.cur = max(max(o.bets), o.bet + o.to_call)
            o.can_raise = leg["raise_by_min"] is not None
            o.max_raise_to = o.bet + o.stack
            o.min_raise_to = o.cur + (leg["raise_by_min"] or 0)
            o.n_alive = sum(1 for x in pl if x["status"] != "out")
            o.n_live = sum(o.in_hand)
            this = [e for e in h if e["street"] == street]
            acted = {e["seat"] for e in this if e["action"] in KIND}
            o.n_behind = sum(1 for x in pl if x["seat"] != me and x["status"] == "active" and (x["seat"] not in acted or x["street_bet"] < o.cur))
            raises = [e for e in this if e["action"] == "raise"]
            o.raises = len(raises)
            o.aggressor = raises[-1]["seat"] if raises else -1
            last = this.index(raises[-1]) if raises else -1
            o.n_callers = sum(1 for e in this[last + 1:] if e["action"] == "call")
            k, a = p.safe_decide(o)
            if k == 2:
                return {"action": "raise", "by": int(a) - o.cur}
            if k == 1:
                return {"action": "check"} if leg["can_check"] else {"action": "call"}
            return {"action": "fold"}
        except Exception:
            return {"action": "check"} if leg["can_check"] else {"action": "fold"}
````

<!-- FILE: lab/tuned_final.json -->
````json
{
"mu": {
"open_a": 0.15229995340694283,
"open_b": 0.761203465043292,
"hu_open": 0.9410073258848779,
"hu_jam": 0.47581277045130577,
"sh_widen": 0.30794231894939195,
"sh_range": 0.981540226738397,
"jam_scale": 1.2813677758257014,
"call_open": 0.10745630561949975,
"threebet": 0.022973335877218108,
"fourbet": 0.019629801122473277,
"open_size": 2.0882579682643394,
"threebet_mult": 3.404240466692629,
"steal_fold_bonus": 0.7742859290370907,
"jam_m": 7.570703950064964,
"jam_slope": 0.12454978722317274,
"call_jam": 0.09057551104425829,
"call_jam_short": 0.04694335356211145,
"range_unraised": 0.5365608533774165,
"range_bet": 0.11138944208692902,
"range_raise": 0.2561345287620911,
"value_eq": 0.6849991852599197,
"bluff_freq": 0.1555457759853949,
"bet_frac": 0.9690359839721008,
"call_margin": 0.1328562129099615,
"raise_eq": 0.7805221225051396,
"commit_spr": 1.9472353303958316,
"icm_margin": 0.1135080737485917,
"eqcall": 1.0,
"width_cap": 6.74559268663644,
"call_odds": 0.018564707772350406,
"hu_defend": 0.7281426209297055,
"eqcall_margin": 0.2,
"vwidth_mult": 0.48256583545663656,
"hu_eqcall": 1.0,
"hu_margin": 0.0,
"hu_vwidth": 1.5,
"hu_gate": 0.45
}
}
````

<!-- FILE: lab/tuned_blend.json -->
````json
{
 "mu": {
  "open_a": 0.1724677678705957,
  "open_b": 0.7252266805663437,
  "hu_open": 0.9555095206665043,
  "hu_jam": 0.9811960646289772,
  "sh_widen": 0.7729148299249884,
  "sh_range": 0.2722798703329023,
  "jam_scale": 1.1440501944883787,
  "call_open": 0.07960357846733165,
  "threebet": 0.04088514867980683,
  "fourbet": 0.011685095320543789,
  "open_size": 2.113637005555376,
  "threebet_mult": 3.081431803793298,
  "steal_fold_bonus": 0.21591319263037995,
  "jam_m": 6.040212220031699,
  "jam_slope": 0.050641346274622065,
  "call_jam": 0.03426656835013188,
  "call_jam_short": 0.02608623099912937,
  "range_unraised": 0.8170063624758167,
  "range_bet": 0.12496025628189264,
  "range_raise": 0.1557066277049791,
  "value_eq": 0.6933851603603727,
  "bluff_freq": 0.26518442698856026,
  "bet_frac": 0.6032481369767818,
  "call_margin": 0.1366461623204806,
  "raise_eq": 0.8412842333627305,
  "commit_spr": 2.42508975360683,
  "icm_margin": 0.10671678467689988
 },
 "hist": [
  {
   "open_a": 0.1579442317457359,
   "open_b": 0.7449561920958537,
   "hu_open": 0.9209971744518122,
   "hu_jam": 0.9252254269615379,
   "sh_widen": 1.3111211160978162,
   "sh_range": 0.30198265381290307,
   "jam_scale": 0.9703644072783839,
   "call_open": 0.09287796729974955,
   "threebet": 0.048474695321311816,
   "fourbet": 0.011517226426645226,
   "open_size": 2.178194510834337,
   "threebet_mult": 3.0178906744915746,
   "steal_fold_bonus": 0.17392773358164695,
   "jam_m": 7.014129690086556,
   "jam_slope": 0.0670928523535042,
   "call_jam": 0.040833151709630776,
   "call_jam_short": 0.027710865593821847,
   "range_unraised": 0.7052207562323729,
   "range_bet": 0.13446609016806854,
   "range_raise": 0.16149449901684446,
   "value_eq": 0.6735513980855139,
   "bluff_freq": 0.28464020622593067,
   "bet_frac": 0.6099169098180535,
   "call_margin": 0.12360745357207253,
   "raise_eq": 0.8199642330269465,
   "commit_spr": 2.263343022208112,
   "icm_margin": 0.09632102136614248
  },
  {
   "open_a": 0.160516385702671,
   "open_b": 0.745657696392341,
   "hu_open": 0.8999734990531674,
   "hu_jam": 0.9466590126001413,
   "sh_widen": 0.9345123145760641,
   "sh_range": 0.4109067174838087,
   "jam_scale": 1.0512523483349905,
   "call_open": 0.0941706071409204,
   "threebet": 0.05481853794636029,
   "fourbet": 0.011261813151104909,
   "open_size": 2.1416879347476314,
   "threebet_mult": 3.05534857092636,
   "steal_fold_bonus": 0.1534779779158626,
   "jam_m": 6.535385906194144,
   "jam_slope": 0.057819457031359184,
   "call_jam": 0.0361647330220225,
   "call_jam_short": 0.028514427303382536,
   "range_unraised": 0.7541826897313889,
   "range_bet": 0.12246264354100408,
   "range_raise": 0.17147020097375554,
   "value_eq": 0.6603965248421046,
   "bluff_freq": 0.27878081382049685,
   "bet_frac": 0.5703505486116596,
   "call_margin": 0.12848641496687568,
   "raise_eq": 0.8177462817552832,
   "commit_spr": 2.2775652017955412,
   "icm_margin": 0.09778180267963991
  },
  {
   "open_a": 0.158132543826914,
   "open_b": 0.7394286078319662,
   "hu_open": 0.9155627716593253,
   "hu_jam": 0.9551120519451997,
   "sh_widen": 0.8327022944871224,
   "sh_range": 0.6648608679095028,
   "jam_scale": 1.0605131609586342,
   "call_open": 0.08656370168690641,
   "threebet": 0.05462485994096343,
   "fourbet": 0.011537499827632613,
   "open_size": 2.22319681166025,
   "threebet_mult": 3.099097476716353,
   "steal_fold_bonus": 0.1677395914363776,
   "jam_m": 6.432599911876361,
   "jam_slope": 0.05264944298576976,
   "call_jam": 0.036715351670476994,
   "call_jam_short": 0.027751651868023183,
   "range_unraised": 0.7987642835602665,
   "range_bet": 0.11786113693913111,
   "range_raise": 0.16916147314853533,
   "value_eq": 0.6669649422156496,
   "bluff_freq": 0.28716933655302807,
   "bet_frac": 0.5563451719125234,
   "call_margin": 0.13141489940481654,
   "raise_eq": 0.8175042007136079,
   "commit_spr": 2.3354626515134553,
   "icm_margin": 0.10210553470701338
  },
  {
   "open_a": 0.16029862092221017,
   "open_b": 0.740077553122122,
   "hu_open": 0.8845342395139406,
   "hu_jam": 0.9588864233520635,
   "sh_widen": 0.7875942159669318,
   "sh_range": 0.7393454937664448,
   "jam_scale": 1.0638426939081316,
   "call_open": 0.09688605703760339,
   "threebet": 0.04752614683397899,
   "fourbet": 0.01186020316615052,
   "open_size": 2.2015674886078793,
   "threebet_mult": 3.1097390423035325,
   "steal_fold_bonus": 0.19673933292331125,
   "jam_m": 6.543689023853589,
   "jam_slope": 0.05426779338117935,
   "call_jam": 0.036941703494290205,
   "call_jam_short": 0.02680635273922835,
   "range_unraised": 0.7699678412424886,
   "range_bet": 0.11909721962885422,
   "range_raise": 0.15972049668476745,
   "value_eq": 0.6565079818382972,
   "bluff_freq": 0.28555461776194,
   "bet_frac": 0.5796467405913488,
   "call_margin": 0.13157612766014168,
   "raise_eq": 0.8294125227874465,
   "commit_spr": 2.297704793039855,
   "icm_margin": 0.09840755094928444
  },
  {
   "open_a": 0.1552661097246671,
   "open_b": 0.7328482167483665,
   "hu_open": 0.9340681762743597,
   "hu_jam": 0.953576686543437,
   "sh_widen": 1.0627663810553272,
   "sh_range": 0.6836795030138603,
   "jam_scale": 1.112653260681251,
   "call_open": 0.08653281918395526,
   "threebet": 0.038888655176199695,
   "fourbet": 0.012077864666415026,
   "open_size": 2.180202404217183,
   "threebet_mult": 3.0984572538905484,
   "steal_fold_bonus": 0.206597571887027,
   "jam_m": 6.5888431634501154,
   "jam_slope": 0.05360687801754209,
   "call_jam": 0.03725172463138859,
   "call_jam_short": 0.02762024072765564,
   "range_unraised": 0.8157466694419506,
   "range_bet": 0.11710862556358646,
   "range_raise": 0.15585637156543192,
   "value_eq": 0.6584517397330323,
   "bluff_freq": 0.27185989759679907,
   "bet_frac": 0.6055537547654594,
   "call_margin": 0.1341848587777026,
   "raise_eq": 0.8381505835392177,
   "commit_spr": 2.395410354375344,
   "icm_margin": 0.10476623648579429
  },
  {
   "open_a": 0.16454250322973882,
   "open_b": 0.7314983318431023,
   "hu_open": 0.9284760192331681,
   "hu_jam": 0.9595685769254769,
   "sh_widen": 0.8262365313841282,
   "sh_range": 0.41147632067233353,
   "jam_scale": 1.1072405356858488,
   "call_open": 0.08059314420364967,
   "threebet": 0.03401968479946943,
   "fourbet": 0.012102880861907398,
   "open_size": 2.150309539962584,
   "threebet_mult": 3.09323419828739,
   "steal_fold_bonus": 0.21970150343661898,
   "jam_m": 6.378947512162972,
   "jam_slope": 0.051268876573162064,
   "call_jam": 0.03721921192120353,
   "call_jam_short": 0.02861873014485119,
   "range_unraised": 0.7869952815838429,
   "range_bet": 0.1113824381955402,
   "range_raise": 0.1531750304432012,
   "value_eq": 0.6838386377206142,
   "bluff_freq": 0.26959605190038705,
   "bet_frac": 0.6047689945397103,
   "call_margin": 0.1351616383166726,
   "raise_eq": 0.8302949528227521,
   "commit_spr": 2.3589908756294373,
   "icm_margin": 0.1099949202939891
  },
  {
   "open_a": 0.1685904803788059,
   "open_b": 0.7331400757431183,
   "hu_open": 0.9276046073794997,
   "hu_jam": 0.9699415791005537,
   "sh_widen": 0.9294818511976577,
   "sh_range": 0.3522081360421798,
   "jam_scale": 1.1176040642244989,
   "call_open": 0.08184765536837639,
   "threebet": 0.03515635179970118,
   "fourbet": 0.01141855256368376,
   "open_size": 2.131777486646377,
   "threebet_mult": 3.092338662518011,
   "steal_fold_bonus": 0.19903984767127478,
   "jam_m": 6.233077833391487,
   "jam_slope": 0.052542661829772866,
   "call_jam": 0.03459347502631005,
   "call_jam_short": 0.02802293079453851,
   "range_unraised": 0.7734530380718683,
   "range_bet": 0.11157463686572026,
   "range_raise": 0.16271922710627634,
   "value_eq": 0.6660298284770971,
   "bluff_freq": 0.27045523147430345,
   "bet_frac": 0.5999523436380039,
   "call_margin": 0.13017097360233415,
   "raise_eq": 0.8354402742330844,
   "commit_spr": 2.411426967251444,
   "icm_margin": 0.11331204464369948
  },
  {
   "open_a": 0.1707047259835086,
   "open_b": 0.7331418954740846,
   "hu_open": 0.955668250278342,
   "hu_jam": 0.9670224226422064,
   "sh_widen": 1.0007513699205246,
   "sh_range": 0.3552031894480019,
   "jam_scale": 1.137910360808414,
   "call_open": 0.0818199238909314,
   "threebet": 0.0355984929016345,
   "fourbet": 0.011642885810970522,
   "open_size": 2.124498252945505,
   "threebet_mult": 3.0944889530681743,
   "steal_fold_bonus": 0.1956784416450627,
   "jam_m": 6.07177166180217,
   "jam_slope": 0.05377889449024958,
   "call_jam": 0.032424013584311746,
   "call_jam_short": 0.027485850175374915,
   "range_unraised": 0.8512856364420213,
   "range_bet": 0.11247141792632634,
   "range_raise": 0.16639841014602588,
   "value_eq": 0.6949514666713096,
   "bluff_freq": 0.26799638059630637,
   "bet_frac": 0.5854834870064127,
   "call_margin": 0.13161585788016228,
   "raise_eq": 0.8406622667996846,
   "commit_spr": 2.438219119586865,
   "icm_margin": 0.1102270618136913
  },
  {
   "open_a": 0.17394549582483776,
   "open_b": 0.7301362562973427,
   "hu_open": 0.9665383598733297,
   "hu_jam": 0.9630881000175838,
   "sh_widen": 0.9009669940958429,
   "sh_range": 0.33377786027917133,
   "jam_scale": 1.1445113002582672,
   "call_open": 0.08457331562476562,
   "threebet": 0.03699819489765046,
   "fourbet": 0.011656226507848474,
   "open_size": 2.122733767936307,
   "threebet_mult": 3.091561987970911,
   "steal_fold_bonus": 0.19892817073565713,
   "jam_m": 6.0899580029452185,
   "jam_slope": 0.051469004510923975,
   "call_jam": 0.03173833664344231,
   "call_jam_short": 0.026085139763242195,
   "range_unraised": 0.839942642345739,
   "range_bet": 0.11298758677554975,
   "range_raise": 0.1671763779359753,
   "value_eq": 0.6962595543005294,
   "bluff_freq": 0.27003956276403374,
   "bet_frac": 0.5819859942680532,
   "call_margin": 0.13341710460147782,
   "raise_eq": 0.8302797106021025,
   "commit_spr": 2.4217612338760457,
   "icm_margin": 0.10153708529150388
  },
  {
   "open_a": 0.16940233137256244,
   "open_b": 0.7240879623995388,
   "hu_open": 0.9566277733219708,
   "hu_jam": 0.96895390501722,
   "sh_widen": 0.8456208692672906,
   "sh_range": 0.286752548490346,
   "jam_scale": 1.1505849939136565,
   "call_open": 0.08375616427371066,
   "threebet": 0.040005361606373246,
   "fourbet": 0.011663255025054987,
   "open_size": 2.137909815377098,
   "threebet_mult": 3.086471994536253,
   "steal_fold_bonus": 0.19526700612473308,
   "jam_m": 6.202048240625802,
   "jam_slope": 0.05208528986958719,
   "call_jam": 0.03326634285615099,
   "call_jam_short": 0.02581469992274825,
   "range_unraised": 0.8323528876143816,
   "range_bet": 0.1132707595330755,
   "range_raise": 0.16324402308712158,
   "value_eq": 0.6942916342212808,
   "bluff_freq": 0.2713171750488723,
   "bet_frac": 0.5809400197041946,
   "call_margin": 0.13343071116867655,
   "raise_eq": 0.8323993406607647,
   "commit_spr": 2.4069126817921394,
   "icm_margin": 0.09825248049836594
  },
  {
   "open_a": 0.1686934040252541,
   "open_b": 0.7248634520097106,
   "hu_open": 0.9595511098957331,
   "hu_jam": 0.9759635275472514,
   "sh_widen": 0.767706577192804,
   "sh_range": 0.282175130423787,
   "jam_scale": 1.1575683510539259,
   "call_open": 0.08287458073660431,
   "threebet": 0.0413258624483392,
   "fourbet": 0.011562625946448735,
   "open_size": 2.1315246481604415,
   "threebet_mult": 3.0781879275067645,
   "steal_fold_bonus": 0.19245711358894924,
   "jam_m": 6.101110529954373,
   "jam_slope": 0.05015444680734475,
   "call_jam": 0.0346366981557632,
   "call_jam_short": 0.02542841439298931,
   "range_unraised": 0.8392919207342531,
   "range_bet": 0.12202595995183033,
   "range_raise": 0.16011058020273494,
   "value_eq": 0.6907436946277324,
   "bluff_freq": 0.26827384451171327,
   "bet_frac": 0.602783268987783,
   "call_margin": 0.13360060747340383,
   "raise_eq": 0.8389803223309233,
   "commit_spr": 2.3924682587665735,
   "icm_margin": 0.10454088402148998
  },
  {
   "open_a": 0.1724677678705957,
   "open_b": 0.7252266805663437,
   "hu_open": 0.9555095206665043,
   "hu_jam": 0.9811960646289772,
   "sh_widen": 0.7729148299249884,
   "sh_range": 0.2722798703329023,
   "jam_scale": 1.1440501944883787,
   "call_open": 0.07960357846733165,
   "threebet": 0.04088514867980683,
   "fourbet": 0.011685095320543789,
   "open_size": 2.113637005555376,
   "threebet_mult": 3.081431803793298,
   "steal_fold_bonus": 0.21591319263037995,
   "jam_m": 6.040212220031699,
   "jam_slope": 0.050641346274622065,
   "call_jam": 0.03426656835013188,
   "call_jam_short": 0.02608623099912937,
   "range_unraised": 0.8170063624758167,
   "range_bet": 0.12496025628189264,
   "range_raise": 0.1557066277049791,
   "value_eq": 0.6933851603603727,
   "bluff_freq": 0.26518442698856026,
   "bet_frac": 0.6032481369767818,
   "call_margin": 0.1366461623204806,
   "raise_eq": 0.8412842333627305,
   "commit_spr": 2.42508975360683,
   "icm_margin": 0.10671678467689988
  }
 ]
}
````

<!-- FILE: lab/tuned_lookup.json -->
````json
{
 "mu": {
  "open_a": 0.14238773068973787,
  "open_b": 0.7199322248780492,
  "hu_open": 0.9153471753428459,
  "hu_jam": 0.937870050126824,
  "sh_widen": 0.3654280097596124,
  "sh_range": 0.20001373429618746,
  "jam_scale": 0.8542306895767785,
  "call_open": 0.08925365492473075,
  "threebet": 0.02103540602000383,
  "fourbet": 0.011064768530941436,
  "open_size": 2.3900580382930983,
  "threebet_mult": 2.9627669425852217,
  "steal_fold_bonus": 0.19004682233068032,
  "jam_m": 5.635624705183206,
  "jam_slope": 0.04484267081049468,
  "call_jam": 0.03841165475127828,
  "call_jam_short": 0.02173450898411933,
  "range_unraised": 0.45772833267278346,
  "range_bet": 0.1559626758456601,
  "range_raise": 0.1376620103339142,
  "value_eq": 0.6835337613000688,
  "bluff_freq": 0.17982979724407955,
  "bet_frac": 0.6161758982409045,
  "call_margin": 0.14614516239652442,
  "raise_eq": 0.8509587362916482,
  "commit_spr": 2.1603319848445923,
  "icm_margin": 0.12065536124273069
 },
 "hist": [
  {
   "open_a": 0.14190535246112612,
   "open_b": 0.6134738727591206,
   "hu_open": 0.9188027158220863,
   "hu_jam": 0.867106840472389,
   "sh_widen": 0.5531898061245883,
   "sh_range": 0.6132333511077078,
   "jam_scale": 0.778331243980033,
   "call_open": 0.11344964962076118,
   "threebet": 0.026318018285532478,
   "fourbet": 0.014497466872988564,
   "open_size": 2.212329339037881,
   "threebet_mult": 2.972470884067836,
   "steal_fold_bonus": 0.16215702709602192,
   "jam_m": 6.883743145712643,
   "jam_slope": 0.040748668308094725,
   "call_jam": 0.039127723765709416,
   "call_jam_short": 0.020479913256431958,
   "range_unraised": 0.4793757698681108,
   "range_bet": 0.1939333654812528,
   "range_raise": 0.0899462303381793,
   "value_eq": 0.6781327883622921,
   "bluff_freq": 0.21568284170196694,
   "bet_frac": 0.5802370493570693,
   "call_margin": 0.11891746530399669,
   "raise_eq": 0.8513801125131775,
   "commit_spr": 1.6004554700289988,
   "icm_margin": 0.1069495404197765
  },
  {
   "open_a": 0.1583172684657114,
   "open_b": 0.6656938977241114,
   "hu_open": 0.9275146264650505,
   "hu_jam": 0.9052901072941608,
   "sh_widen": 0.3658114725139049,
   "sh_range": 0.7558864179481819,
   "jam_scale": 0.6955359733690496,
   "call_open": 0.08077077243849207,
   "threebet": 0.026280380692776703,
   "fourbet": 0.013785648464757733,
   "open_size": 2.2843664813414355,
   "threebet_mult": 2.957182205249337,
   "steal_fold_bonus": 0.1314421962547948,
   "jam_m": 6.798883255657774,
   "jam_slope": 0.042789323073838675,
   "call_jam": 0.03676926549398821,
   "call_jam_short": 0.02183921578546558,
   "range_unraised": 0.48019421901246423,
   "range_bet": 0.19383365395781796,
   "range_raise": 0.08415386921820533,
   "value_eq": 0.6856170329017203,
   "bluff_freq": 0.1966115868403046,
   "bet_frac": 0.5491119242973457,
   "call_margin": 0.12671262506523465,
   "raise_eq": 0.8505796173051106,
   "commit_spr": 1.755941593606971,
   "icm_margin": 0.10938508852050512
  },
  {
   "open_a": 0.13592993641487272,
   "open_b": 0.7230328295394859,
   "hu_open": 0.9445681416775265,
   "hu_jam": 0.917938311561304,
   "sh_widen": 0.5617877472567478,
   "sh_range": 0.6945322914317411,
   "jam_scale": 0.659622693543336,
   "call_open": 0.08015355125812583,
   "threebet": 0.022433575299769366,
   "fourbet": 0.014174433642240455,
   "open_size": 2.38447830289958,
   "threebet_mult": 2.8958754400794477,
   "steal_fold_bonus": 0.16036741014596126,
   "jam_m": 6.51123564109624,
   "jam_slope": 0.04113856956111762,
   "call_jam": 0.03895568623932378,
   "call_jam_short": 0.023766903943824517,
   "range_unraised": 0.49628230519621547,
   "range_bet": 0.17831570572632843,
   "range_raise": 0.10447882804754775,
   "value_eq": 0.6892865553767855,
   "bluff_freq": 0.1983757925374901,
   "bet_frac": 0.530855497086524,
   "call_margin": 0.1380943179246812,
   "raise_eq": 0.828821992534437,
   "commit_spr": 1.8298989041832536,
   "icm_margin": 0.11738006100187268
  },
  {
   "open_a": 0.13319128221479665,
   "open_b": 0.7189514575916298,
   "hu_open": 0.9167527351119509,
   "hu_jam": 0.9232518580985072,
   "sh_widen": 0.5015532262961959,
   "sh_range": 0.7590331755437723,
   "jam_scale": 0.7009493851077124,
   "call_open": 0.0893305709029015,
   "threebet": 0.020041327442984973,
   "fourbet": 0.012971708230711976,
   "open_size": 2.407390798089351,
   "threebet_mult": 2.894547159503202,
   "steal_fold_bonus": 0.18914135567104232,
   "jam_m": 6.736718385261258,
   "jam_slope": 0.044290111190748355,
   "call_jam": 0.04006780643699496,
   "call_jam_short": 0.020321615846167027,
   "range_unraised": 0.5253483187215964,
   "range_bet": 0.17217659727575307,
   "range_raise": 0.11497545701457776,
   "value_eq": 0.66607562268997,
   "bluff_freq": 0.19127339332501916,
   "bet_frac": 0.5437162677030085,
   "call_margin": 0.13857293949060517,
   "raise_eq": 0.8338829570271753,
   "commit_spr": 1.801202791655298,
   "icm_margin": 0.1190125589056098
  },
  {
   "open_a": 0.12899201660465343,
   "open_b": 0.7191371805827155,
   "hu_open": 0.9386288316302549,
   "hu_jam": 0.922337311272726,
   "sh_widen": 0.4722330490774632,
   "sh_range": 0.40864315477923785,
   "jam_scale": 0.8176295114984148,
   "call_open": 0.096678795421043,
   "threebet": 0.01972547687513293,
   "fourbet": 0.012565530661702604,
   "open_size": 2.419606766780491,
   "threebet_mult": 2.9379702149757465,
   "steal_fold_bonus": 0.19851903393865805,
   "jam_m": 6.171484567685043,
   "jam_slope": 0.03936891047696588,
   "call_jam": 0.04270959684125332,
   "call_jam_short": 0.016426091672584218,
   "range_unraised": 0.5103429181172403,
   "range_bet": 0.1618941549147669,
   "range_raise": 0.12620767372677388,
   "value_eq": 0.6728653235776574,
   "bluff_freq": 0.17587350933416804,
   "bet_frac": 0.568731089341191,
   "call_margin": 0.14183136253039336,
   "raise_eq": 0.8458712928680541,
   "commit_spr": 1.842690768421096,
   "icm_margin": 0.11698358015874316
  },
  {
   "open_a": 0.13169505100974446,
   "open_b": 0.7261465642921456,
   "hu_open": 0.9277981556984431,
   "hu_jam": 0.9261044299125154,
   "sh_widen": 0.47005703019759193,
   "sh_range": 0.344294698676838,
   "jam_scale": 0.7959576428937148,
   "call_open": 0.0932039974841833,
   "threebet": 0.018300522014216326,
   "fourbet": 0.012677161685561931,
   "open_size": 2.403710884631737,
   "threebet_mult": 2.9294964051058408,
   "steal_fold_bonus": 0.21613983470959056,
   "jam_m": 6.066785468541209,
   "jam_slope": 0.03757443193726864,
   "call_jam": 0.04196170212679737,
   "call_jam_short": 0.01681914985351393,
   "range_unraised": 0.4703830074338527,
   "range_bet": 0.15900960858546365,
   "range_raise": 0.13084593786432488,
   "value_eq": 0.6864188851610219,
   "bluff_freq": 0.17644122345148114,
   "bet_frac": 0.5888982203491049,
   "call_margin": 0.14305021361081238,
   "raise_eq": 0.8519011087713406,
   "commit_spr": 1.9568932634241871,
   "icm_margin": 0.11812829125082919
  },
  {
   "open_a": 0.13675479827221146,
   "open_b": 0.729128540195636,
   "hu_open": 0.9070230250884441,
   "hu_jam": 0.9349066522879992,
   "sh_widen": 0.5439225388036959,
   "sh_range": 0.3210937005770374,
   "jam_scale": 0.8018923625024952,
   "call_open": 0.09437999122416854,
   "threebet": 0.019351652615770286,
   "fourbet": 0.011971247273379558,
   "open_size": 2.3978891545099605,
   "threebet_mult": 2.9832875861470574,
   "steal_fold_bonus": 0.1994344737580084,
   "jam_m": 5.947251546459796,
   "jam_slope": 0.04249790125423294,
   "call_jam": 0.04206308448747548,
   "call_jam_short": 0.018182137852068708,
   "range_unraised": 0.4723706431483917,
   "range_bet": 0.15701831178497094,
   "range_raise": 0.139965288627415,
   "value_eq": 0.6796133419638487,
   "bluff_freq": 0.170311073699204,
   "bet_frac": 0.5989269181668283,
   "call_margin": 0.14075311042677802,
   "raise_eq": 0.8481098438939602,
   "commit_spr": 2.0818141785524134,
   "icm_margin": 0.11652532728068123
  },
  {
   "open_a": 0.14006581585290886,
   "open_b": 0.7328611081879907,
   "hu_open": 0.9123391747556261,
   "hu_jam": 0.9409567151315352,
   "sh_widen": 0.6146309749203401,
   "sh_range": 0.23745819850975852,
   "jam_scale": 0.8074443557123054,
   "call_open": 0.09969705559266936,
   "threebet": 0.020822155392635003,
   "fourbet": 0.012496861147878888,
   "open_size": 2.415486275054846,
   "threebet_mult": 2.9864126345264976,
   "steal_fold_bonus": 0.18955636484633281,
   "jam_m": 5.858651160294001,
   "jam_slope": 0.05098974132076422,
   "call_jam": 0.04090354193658811,
   "call_jam_short": 0.019022784018832607,
   "range_unraised": 0.4895526840459175,
   "range_bet": 0.15487450434518582,
   "range_raise": 0.13829372833163922,
   "value_eq": 0.6822287325119306,
   "bluff_freq": 0.16036613305184674,
   "bet_frac": 0.6011709295587812,
   "call_margin": 0.14193311532060138,
   "raise_eq": 0.8497413029883755,
   "commit_spr": 1.9984509239547519,
   "icm_margin": 0.11965269893542914
  },
  {
   "open_a": 0.14076147104900358,
   "open_b": 0.7218437645598796,
   "hu_open": 0.920941151829406,
   "hu_jam": 0.9390343742662817,
   "sh_widen": 0.48340526071545764,
   "sh_range": 0.24552184953528655,
   "jam_scale": 0.8440783399450846,
   "call_open": 0.09501319076264206,
   "threebet": 0.02100824186586287,
   "fourbet": 0.012392817670310741,
   "open_size": 2.4463898799352872,
   "threebet_mult": 2.9758366217534515,
   "steal_fold_bonus": 0.18293151745325548,
   "jam_m": 5.856363776740325,
   "jam_slope": 0.04848741608829965,
   "call_jam": 0.03999824505413199,
   "call_jam_short": 0.018523422638135008,
   "range_unraised": 0.4378949167075783,
   "range_bet": 0.1542421764268698,
   "range_raise": 0.13698764698443017,
   "value_eq": 0.6862202505515042,
   "bluff_freq": 0.16628777155718902,
   "bet_frac": 0.6043097298223198,
   "call_margin": 0.14388305671025228,
   "raise_eq": 0.8437611398050946,
   "commit_spr": 2.034588968507971,
   "icm_margin": 0.12084010812566581
  },
  {
   "open_a": 0.14168623720273413,
   "open_b": 0.7247581180738603,
   "hu_open": 0.9188531462292546,
   "hu_jam": 0.9445847509629499,
   "sh_widen": 0.46326932031862905,
   "sh_range": 0.24742116982907536,
   "jam_scale": 0.8530810892211974,
   "call_open": 0.09244677604067239,
   "threebet": 0.02110490361463378,
   "fourbet": 0.011935431682218613,
   "open_size": 2.4327000591184937,
   "threebet_mult": 2.9772793804350353,
   "steal_fold_bonus": 0.18166626610079611,
   "jam_m": 6.246137687303305,
   "jam_slope": 0.048226216132642385,
   "call_jam": 0.0397655520911135,
   "call_jam_short": 0.02097872473323683,
   "range_unraised": 0.45461743770579954,
   "range_bet": 0.14959589002389825,
   "range_raise": 0.1374110266899037,
   "value_eq": 0.6806526748584687,
   "bluff_freq": 0.17742169423030363,
   "bet_frac": 0.6060034916361768,
   "call_margin": 0.14521047754979455,
   "raise_eq": 0.8421094497795063,
   "commit_spr": 2.022294369807795,
   "icm_margin": 0.12198324188131666
  },
  {
   "open_a": 0.14184864544471854,
   "open_b": 0.7211216603965384,
   "hu_open": 0.9199794442241847,
   "hu_jam": 0.943664747404855,
   "sh_widen": 0.43186919908357774,
   "sh_range": 0.2384618060689936,
   "jam_scale": 0.857831458788011,
   "call_open": 0.09071607581989438,
   "threebet": 0.019901723702291717,
   "fourbet": 0.011486271762700057,
   "open_size": 2.433620240026025,
   "threebet_mult": 2.957191652074809,
   "steal_fold_bonus": 0.18905901806418135,
   "jam_m": 5.991921327759762,
   "jam_slope": 0.046341293000351,
   "call_jam": 0.03866669402933393,
   "call_jam_short": 0.021658354276339838,
   "range_unraised": 0.4699929865801261,
   "range_bet": 0.15242422917631732,
   "range_raise": 0.14018275180714354,
   "value_eq": 0.6861604729793043,
   "bluff_freq": 0.1752872272304307,
   "bet_frac": 0.6082163879489795,
   "call_margin": 0.1464889739488322,
   "raise_eq": 0.8453354578992667,
   "commit_spr": 2.107212445268454,
   "icm_margin": 0.12236780203569611
  },
  {
   "open_a": 0.14238773068973787,
   "open_b": 0.7199322248780492,
   "hu_open": 0.9153471753428459,
   "hu_jam": 0.937870050126824,
   "sh_widen": 0.3654280097596124,
   "sh_range": 0.20001373429618746,
   "jam_scale": 0.8542306895767785,
   "call_open": 0.08925365492473075,
   "threebet": 0.02103540602000383,
   "fourbet": 0.011064768530941436,
   "open_size": 2.3900580382930983,
   "threebet_mult": 2.9627669425852217,
   "steal_fold_bonus": 0.19004682233068032,
   "jam_m": 5.635624705183206,
   "jam_slope": 0.04484267081049468,
   "call_jam": 0.03841165475127828,
   "call_jam_short": 0.02173450898411933,
   "range_unraised": 0.45772833267278346,
   "range_bet": 0.1559626758456601,
   "range_raise": 0.1376620103339142,
   "value_eq": 0.6835337613000688,
   "bluff_freq": 0.17982979724407955,
   "bet_frac": 0.6161758982409045,
   "call_margin": 0.14614516239652442,
   "raise_eq": 0.8509587362916482,
   "commit_spr": 2.1603319848445923,
   "icm_margin": 0.12065536124273069
  }
 ]
}
````

<!-- FILE: lab/tuned_meta1.json -->
````json
{
 "mu": {
  "open_a": 0.16501899466731962,
  "open_b": 0.7704463982241294,
  "hu_open": 0.9581360803996549,
  "hu_jam": 0.943762404597442,
  "sh_widen": 1.3946463115434564,
  "sh_range": 0.276259514393175,
  "jam_scale": 1.0313836900495867,
  "call_open": 0.11157063389825024,
  "threebet": 0.03677049427945413,
  "fourbet": 0.011665734808247731,
  "open_size": 2.285680773507962,
  "threebet_mult": 3.118415291688631,
  "steal_fold_bonus": 0.1633585949290114,
  "jam_m": 6.186121332106644,
  "jam_slope": 0.07148146222442467,
  "call_jam": 0.03695411158288231,
  "call_jam_short": 0.02935592288614601,
  "range_unraised": 0.6938580063945627,
  "range_bet": 0.1479839469457178,
  "range_raise": 0.1725484235394094,
  "value_eq": 0.6600392046400818,
  "bluff_freq": 0.2768052600184484,
  "bet_frac": 0.5804256867510461,
  "call_margin": 0.14219337554740136,
  "raise_eq": 0.8333578319550974,
  "commit_spr": 2.0907044082928534,
  "icm_margin": 0.09137202905159092
 },
 "hist": [
  {
   "open_a": 0.14660747425035114,
   "open_b": 0.7442847873711227,
   "hu_open": 0.9380257234570565,
   "hu_jam": 0.9425453826614298,
   "sh_widen": 0.6878387253909828,
   "sh_range": 0.31394425443197416,
   "jam_scale": 0.8649512063439022,
   "call_open": 0.10359774739698169,
   "threebet": 0.024348298186021414,
   "fourbet": 0.011787127548441035,
   "open_size": 2.4029043460380453,
   "threebet_mult": 2.9436179018549016,
   "steal_fold_bonus": 0.15926351787899112,
   "jam_m": 5.81089199495759,
   "jam_slope": 0.038148656113988204,
   "call_jam": 0.03941800579332319,
   "call_jam_short": 0.02554747267631288,
   "range_unraised": 0.48195663332568267,
   "range_bet": 0.22150654463700037,
   "range_raise": 0.14259828667113567,
   "value_eq": 0.65937951265773,
   "bluff_freq": 0.24193663920768982,
   "bet_frac": 0.6147252461526833,
   "call_margin": 0.1335169396155315,
   "raise_eq": 0.8444827677951087,
   "commit_spr": 2.067333058694044,
   "icm_margin": 0.11889061581942592
  },
  {
   "open_a": 0.15150885748637546,
   "open_b": 0.7421728913641257,
   "hu_open": 0.9267718241299547,
   "hu_jam": 0.9489319147386654,
   "sh_widen": 0.9890560175935003,
   "sh_range": 0.28249546573165385,
   "jam_scale": 0.9203318681377282,
   "call_open": 0.09188489136107206,
   "threebet": 0.0306693190987378,
   "fourbet": 0.012159747283955996,
   "open_size": 2.2844378502753147,
   "threebet_mult": 3.0016037351117206,
   "steal_fold_bonus": 0.18450333550640163,
   "jam_m": 6.162235088903018,
   "jam_slope": 0.038113573481490096,
   "call_jam": 0.035493234384257936,
   "call_jam_short": 0.031708614130592935,
   "range_unraised": 0.5614631864077895,
   "range_bet": 0.20464682648983745,
   "range_raise": 0.14307240022977735,
   "value_eq": 0.6646382159937805,
   "bluff_freq": 0.23366298973142086,
   "bet_frac": 0.6046946874819454,
   "call_margin": 0.13435475165531144,
   "raise_eq": 0.8257698430540295,
   "commit_spr": 2.04800141417493,
   "icm_margin": 0.11831841570066937
  },
  {
   "open_a": 0.1487711917158526,
   "open_b": 0.7536873194007441,
   "hu_open": 0.9278617695295921,
   "hu_jam": 0.9545937971047797,
   "sh_widen": 0.9033052801942878,
   "sh_range": 0.3052647708132681,
   "jam_scale": 0.9283756887219128,
   "call_open": 0.10733135581457617,
   "threebet": 0.03195785640252053,
   "fourbet": 0.012715305427094923,
   "open_size": 2.2523103482292024,
   "threebet_mult": 3.0089067912668908,
   "steal_fold_bonus": 0.17455183064990612,
   "jam_m": 5.997557793001218,
   "jam_slope": 0.05782581799098077,
   "call_jam": 0.035381637628162106,
   "call_jam_short": 0.029535070976119213,
   "range_unraised": 0.6254386424385716,
   "range_bet": 0.1929213826271327,
   "range_raise": 0.1373864414835374,
   "value_eq": 0.6509716216719716,
   "bluff_freq": 0.2730499871201152,
   "bet_frac": 0.6037276588668024,
   "call_margin": 0.13524028006843974,
   "raise_eq": 0.8447885107918486,
   "commit_spr": 1.9316273030283069,
   "icm_margin": 0.10907086959707404
  },
  {
   "open_a": 0.15552143214359437,
   "open_b": 0.7662439698241904,
   "hu_open": 0.9412740698503482,
   "hu_jam": 0.9500983119842619,
   "sh_widen": 0.9988519063650259,
   "sh_range": 0.3416328979307764,
   "jam_scale": 0.9273124298667588,
   "call_open": 0.11367769720965504,
   "threebet": 0.03177296755155654,
   "fourbet": 0.012284285914156924,
   "open_size": 2.2272197334991657,
   "threebet_mult": 3.037440648387017,
   "steal_fold_bonus": 0.1746279805112673,
   "jam_m": 6.176370888404433,
   "jam_slope": 0.06836792501995553,
   "call_jam": 0.03611256572713856,
   "call_jam_short": 0.027902758297086397,
   "range_unraised": 0.650498397780994,
   "range_bet": 0.17886685697371277,
   "range_raise": 0.1420015304459309,
   "value_eq": 0.6560487044530491,
   "bluff_freq": 0.28464295828878333,
   "bet_frac": 0.6144261945318519,
   "call_margin": 0.13709371712942375,
   "raise_eq": 0.8193956382020843,
   "commit_spr": 1.8335187606760428,
   "icm_margin": 0.10922986820897262
  },
  {
   "open_a": 0.158083871081131,
   "open_b": 0.7668995016516366,
   "hu_open": 0.9528794040011181,
   "hu_jam": 0.9509446148080052,
   "sh_widen": 1.2667543055107258,
   "sh_range": 0.2882464994793611,
   "jam_scale": 1.0357121578840274,
   "call_open": 0.11325327542193073,
   "threebet": 0.03449813454990645,
   "fourbet": 0.012225253824969175,
   "open_size": 2.205464923141921,
   "threebet_mult": 3.064653926898902,
   "steal_fold_bonus": 0.1699049183958931,
   "jam_m": 6.262773463545073,
   "jam_slope": 0.0665258199396847,
   "call_jam": 0.037563376946574065,
   "call_jam_short": 0.026038128652390795,
   "range_unraised": 0.6467349722390218,
   "range_bet": 0.15683546582142588,
   "range_raise": 0.14193962657911605,
   "value_eq": 0.6517188372864698,
   "bluff_freq": 0.25153756929932547,
   "bet_frac": 0.5835161902443355,
   "call_margin": 0.1397796675460628,
   "raise_eq": 0.8487760121693282,
   "commit_spr": 1.88742733891243,
   "icm_margin": 0.10357281536084371
  },
  {
   "open_a": 0.1559280469701809,
   "open_b": 0.7665215262601568,
   "hu_open": 0.948972315704774,
   "hu_jam": 0.9526628447921478,
   "sh_widen": 1.2468638059959516,
   "sh_range": 0.2960924026652454,
   "jam_scale": 1.0577899145073508,
   "call_open": 0.10884904298473336,
   "threebet": 0.030222016820582565,
   "fourbet": 0.012077640592487471,
   "open_size": 2.2318866833185704,
   "threebet_mult": 3.089657810119129,
   "steal_fold_bonus": 0.1671302395252896,
   "jam_m": 6.335995807554479,
   "jam_slope": 0.06955421769145992,
   "call_jam": 0.03755283911851545,
   "call_jam_short": 0.028464803131566872,
   "range_unraised": 0.6713852080910139,
   "range_bet": 0.15640259956048322,
   "range_raise": 0.15454055531365912,
   "value_eq": 0.6513598627793012,
   "bluff_freq": 0.25129238017708644,
   "bet_frac": 0.5648474567827136,
   "call_margin": 0.1383985699273855,
   "raise_eq": 0.8304094246287904,
   "commit_spr": 1.9129289453623635,
   "icm_margin": 0.09970937961543636
  },
  {
   "open_a": 0.16525241982837938,
   "open_b": 0.7639448429406124,
   "hu_open": 0.9423400817637063,
   "hu_jam": 0.947337130585164,
   "sh_widen": 1.405921545651686,
   "sh_range": 0.29463292524920803,
   "jam_scale": 1.047762870700886,
   "call_open": 0.11040403059885574,
   "threebet": 0.032116424907997355,
   "fourbet": 0.01194620137907842,
   "open_size": 2.2601314379719084,
   "threebet_mult": 3.113866538502068,
   "steal_fold_bonus": 0.16343399136952452,
   "jam_m": 6.158686997601475,
   "jam_slope": 0.06973960633210319,
   "call_jam": 0.03795899522527009,
   "call_jam_short": 0.0286786916170534,
   "range_unraised": 0.704829208238992,
   "range_bet": 0.15429511999890652,
   "range_raise": 0.16474140223701755,
   "value_eq": 0.6586116723699322,
   "bluff_freq": 0.2645107663793722,
   "bet_frac": 0.5724649688836319,
   "call_margin": 0.13938264991733101,
   "raise_eq": 0.843322887074533,
   "commit_spr": 2.068583876349664,
   "icm_margin": 0.09592089099949005
  },
  {
   "open_a": 0.16501899466731962,
   "open_b": 0.7704463982241294,
   "hu_open": 0.9581360803996549,
   "hu_jam": 0.943762404597442,
   "sh_widen": 1.3946463115434564,
   "sh_range": 0.276259514393175,
   "jam_scale": 1.0313836900495867,
   "call_open": 0.11157063389825024,
   "threebet": 0.03677049427945413,
   "fourbet": 0.011665734808247731,
   "open_size": 2.285680773507962,
   "threebet_mult": 3.118415291688631,
   "steal_fold_bonus": 0.1633585949290114,
   "jam_m": 6.186121332106644,
   "jam_slope": 0.07148146222442467,
   "call_jam": 0.03695411158288231,
   "call_jam_short": 0.02935592288614601,
   "range_unraised": 0.6938580063945627,
   "range_bet": 0.1479839469457178,
   "range_raise": 0.1725484235394094,
   "value_eq": 0.6600392046400818,
   "bluff_freq": 0.2768052600184484,
   "bet_frac": 0.5804256867510461,
   "call_margin": 0.14219337554740136,
   "raise_eq": 0.8333578319550974,
   "commit_spr": 2.0907044082928534,
   "icm_margin": 0.09137202905159092
  }
 ]
}
````

<!-- FILE: lab/tuned_meta3.json -->
````json
{
 "mu": {
  "open_a": 0.14980582117550295,
  "open_b": 0.7816760629454169,
  "hu_open": 0.9064364313693898,
  "hu_jam": 0.9488380767331128,
  "sh_widen": 1.958540983188292,
  "sh_range": 0.569323348984466,
  "jam_scale": 1.0280430064844004,
  "call_open": 0.06555212693689358,
  "threebet": 0.04603748209293411,
  "fourbet": 0.011104732669727701,
  "open_size": 2.235294703720818,
  "threebet_mult": 2.8499306199217287,
  "steal_fold_bonus": 0.19905076034579838,
  "jam_m": 7.585057352876081,
  "jam_slope": 0.09629056212076002,
  "call_jam": 0.038485528649742466,
  "call_jam_short": 0.03294117306929486,
  "range_unraised": 0.8330583601518659,
  "range_bet": 0.1362239021343844,
  "range_raise": 0.13934719114166091,
  "value_eq": 0.6161899999395467,
  "bluff_freq": 0.3861907490672531,
  "bet_frac": 0.6167930995093291,
  "call_margin": 0.1262193516681536,
  "raise_eq": 0.9170332617918531,
  "commit_spr": 1.8873887148775825,
  "icm_margin": 0.09393964666521182
 },
 "hist": [
  {
   "open_a": 0.14745657201846737,
   "open_b": 0.7742485344038768,
   "hu_open": 0.8981913077484558,
   "hu_jam": 0.9269959548237896,
   "sh_widen": 2.826837232310545,
   "sh_range": 0.41291973081886085,
   "jam_scale": 0.9923598999861885,
   "call_open": 0.06486018082155598,
   "threebet": 0.04938846984834941,
   "fourbet": 0.011389429313150777,
   "open_size": 2.1548327391429902,
   "threebet_mult": 2.9429283287867465,
   "steal_fold_bonus": 0.21838178629499416,
   "jam_m": 8.656683789892693,
   "jam_slope": 0.06506085298922909,
   "call_jam": 0.03651728379147559,
   "call_jam_short": 0.036699314035570835,
   "range_unraised": 0.821322356936256,
   "range_bet": 0.12155995979376871,
   "range_raise": 0.126829308792683,
   "value_eq": 0.696398202967264,
   "bluff_freq": 0.3247021040966488,
   "bet_frac": 0.6109727118903483,
   "call_margin": 0.12373837302353574,
   "raise_eq": 0.8948489820248522,
   "commit_spr": 2.3888341940680062,
   "icm_margin": 0.09535239571607365
  },
  {
   "open_a": 0.1419537447954203,
   "open_b": 0.7569122287219012,
   "hu_open": 0.8247433254332246,
   "hu_jam": 0.9394504706654103,
   "sh_widen": 2.4160109435426897,
   "sh_range": 0.44074314909371803,
   "jam_scale": 1.0411237339482684,
   "call_open": 0.060350065846933504,
   "threebet": 0.04968994895593694,
   "fourbet": 0.011628222339227657,
   "open_size": 2.2018003511300535,
   "threebet_mult": 2.8890358999858097,
   "steal_fold_bonus": 0.17100528041965785,
   "jam_m": 6.997167242817026,
   "jam_slope": 0.049553854781205456,
   "call_jam": 0.03630341954399774,
   "call_jam_short": 0.03743081818758375,
   "range_unraised": 0.8427658981319878,
   "range_bet": 0.1289718264891343,
   "range_raise": 0.11770878904007567,
   "value_eq": 0.6823094794384408,
   "bluff_freq": 0.3347888567435819,
   "bet_frac": 0.563597711808541,
   "call_margin": 0.1256269319275772,
   "raise_eq": 0.8842194103148848,
   "commit_spr": 2.5185897605715937,
   "icm_margin": 0.09922128965874351
  },
  {
   "open_a": 0.14528532597183624,
   "open_b": 0.7577635229160271,
   "hu_open": 0.8516198722174281,
   "hu_jam": 0.9370502056878318,
   "sh_widen": 2.1588713758948597,
   "sh_range": 0.4802657647695339,
   "jam_scale": 1.0660024463197533,
   "call_open": 0.06318342323153898,
   "threebet": 0.04589607017878593,
   "fourbet": 0.011651954247912417,
   "open_size": 2.1548521374018814,
   "threebet_mult": 2.8701998236497936,
   "steal_fold_bonus": 0.16509344647825194,
   "jam_m": 7.428061722580396,
   "jam_slope": 0.06807941126076611,
   "call_jam": 0.03602607289246775,
   "call_jam_short": 0.037239780398067496,
   "range_unraised": 0.860684286143209,
   "range_bet": 0.1258647282525889,
   "range_raise": 0.11405616808830098,
   "value_eq": 0.680595018132896,
   "bluff_freq": 0.36923314268662677,
   "bet_frac": 0.5719394938388019,
   "call_margin": 0.12716079977958558,
   "raise_eq": 0.8941995912357269,
   "commit_spr": 2.329255930847573,
   "icm_margin": 0.09341571846786814
  },
  {
   "open_a": 0.1500272302968785,
   "open_b": 0.7617737522484069,
   "hu_open": 0.8327066023682224,
   "hu_jam": 0.9362696284482281,
   "sh_widen": 1.8919562121220523,
   "sh_range": 0.5308250820911512,
   "jam_scale": 1.0602691079471203,
   "call_open": 0.06758643825986237,
   "threebet": 0.04210646283679895,
   "fourbet": 0.011628270530650507,
   "open_size": 2.237173459383963,
   "threebet_mult": 2.8774999792898304,
   "steal_fold_bonus": 0.21042001623787612,
   "jam_m": 8.04901561915324,
   "jam_slope": 0.08083504655387078,
   "call_jam": 0.03464113675714247,
   "call_jam_short": 0.035104412891444475,
   "range_unraised": 0.8627309395554108,
   "range_bet": 0.1259646844965573,
   "range_raise": 0.12009634693915089,
   "value_eq": 0.6781995563399982,
   "bluff_freq": 0.36426606590042193,
   "bet_frac": 0.5475999238987619,
   "call_margin": 0.12504998533762549,
   "raise_eq": 0.8958731746645894,
   "commit_spr": 2.11288270313696,
   "icm_margin": 0.09222933593066843
  },
  {
   "open_a": 0.14817877837088475,
   "open_b": 0.7520398497920524,
   "hu_open": 0.8770565688617012,
   "hu_jam": 0.9295046233200004,
   "sh_widen": 1.9428507044144305,
   "sh_range": 0.4925142017837375,
   "jam_scale": 1.0521198943852341,
   "call_open": 0.06458322205531275,
   "threebet": 0.037395485241374204,
   "fourbet": 0.011649326866861685,
   "open_size": 2.2194141027046674,
   "threebet_mult": 2.9004171732058595,
   "steal_fold_bonus": 0.20798277595605943,
   "jam_m": 7.668043536934027,
   "jam_slope": 0.0800719931839447,
   "call_jam": 0.03412126829016119,
   "call_jam_short": 0.03600662853775386,
   "range_unraised": 0.8493962562120607,
   "range_bet": 0.12794644157405222,
   "range_raise": 0.12160078917224586,
   "value_eq": 0.6526811681840673,
   "bluff_freq": 0.3578724080607173,
   "bet_frac": 0.5700233315465728,
   "call_margin": 0.12573847960354684,
   "raise_eq": 0.9082955449223002,
   "commit_spr": 1.9317770791826196,
   "icm_margin": 0.09101535314767675
  },
  {
   "open_a": 0.152789057530717,
   "open_b": 0.7564281744580184,
   "hu_open": 0.9212667509043432,
   "hu_jam": 0.9376026190750633,
   "sh_widen": 1.8473051519083374,
   "sh_range": 0.5219066240007996,
   "jam_scale": 1.0342140446924684,
   "call_open": 0.06257197626663233,
   "threebet": 0.039248343334714615,
   "fourbet": 0.011540613457003763,
   "open_size": 2.208614346851937,
   "threebet_mult": 2.8536409408237233,
   "steal_fold_bonus": 0.20279054490060716,
   "jam_m": 7.4633925523558045,
   "jam_slope": 0.08219983796663069,
   "call_jam": 0.0348280476041031,
   "call_jam_short": 0.03442267855324549,
   "range_unraised": 0.820717445754358,
   "range_bet": 0.12677596605279445,
   "range_raise": 0.12243748418965783,
   "value_eq": 0.6128845217668345,
   "bluff_freq": 0.38697746317790366,
   "bet_frac": 0.5756941646371974,
   "call_margin": 0.12739652382519545,
   "raise_eq": 0.9149298156702375,
   "commit_spr": 1.8734782199492728,
   "icm_margin": 0.095412134024921
  },
  {
   "open_a": 0.14700530466996453,
   "open_b": 0.7699182945660399,
   "hu_open": 0.8952219335850711,
   "hu_jam": 0.9480316587521356,
   "sh_widen": 2.013967543688542,
   "sh_range": 0.5392205963113003,
   "jam_scale": 1.0327370999153271,
   "call_open": 0.06366627979921376,
   "threebet": 0.042820057774998185,
   "fourbet": 0.01192148124049006,
   "open_size": 2.2289404367507517,
   "threebet_mult": 2.8481006536062203,
   "steal_fold_bonus": 0.20629317696932345,
   "jam_m": 7.446101547726111,
   "jam_slope": 0.08803714496195875,
   "call_jam": 0.038457139205040305,
   "call_jam_short": 0.03505958569706551,
   "range_unraised": 0.8367449846192444,
   "range_bet": 0.13685485783103296,
   "range_raise": 0.12571427176461886,
   "value_eq": 0.6311897336666922,
   "bluff_freq": 0.3746818673520068,
   "bet_frac": 0.5871583477125658,
   "call_margin": 0.12774874725020605,
   "raise_eq": 0.9124240015640075,
   "commit_spr": 1.9368830537926778,
   "icm_margin": 0.0916978189181813
  },
  {
   "open_a": 0.14980582117550295,
   "open_b": 0.7816760629454169,
   "hu_open": 0.9064364313693898,
   "hu_jam": 0.9488380767331128,
   "sh_widen": 1.958540983188292,
   "sh_range": 0.569323348984466,
   "jam_scale": 1.0280430064844004,
   "call_open": 0.06555212693689358,
   "threebet": 0.04603748209293411,
   "fourbet": 0.011104732669727701,
   "open_size": 2.235294703720818,
   "threebet_mult": 2.8499306199217287,
   "steal_fold_bonus": 0.19905076034579838,
   "jam_m": 7.585057352876081,
   "jam_slope": 0.09629056212076002,
   "call_jam": 0.038485528649742466,
   "call_jam_short": 0.03294117306929486,
   "range_unraised": 0.8330583601518659,
   "range_bet": 0.1362239021343844,
   "range_raise": 0.13934719114166091,
   "value_eq": 0.6161899999395467,
   "bluff_freq": 0.3861907490672531,
   "bet_frac": 0.6167930995093291,
   "call_margin": 0.1262193516681536,
   "raise_eq": 0.9170332617918531,
   "commit_spr": 1.8873887148775825,
   "icm_margin": 0.09393964666521182
  }
 ]
}
````

<!-- FILE: lab/tuned_mcblend.json -->
````json
{
 "mu": {
  "open_a": 0.1757818625183531,
  "open_b": 0.7654950443077992,
  "hu_open": 0.974194853826461,
  "hu_jam": 0.874551058197748,
  "sh_widen": 0.4552109058033953,
  "sh_range": 0.7324084059007265,
  "jam_scale": 0.9003533308998516,
  "call_open": 0.09106339361079707,
  "threebet": 0.03728986456162825,
  "fourbet": 0.012542054298942736,
  "open_size": 2.084503517164194,
  "threebet_mult": 3.046062469264748,
  "steal_fold_bonus": 0.24923497874622375,
  "jam_m": 5.447133656697666,
  "jam_slope": 0.02793868562818342,
  "call_jam": 0.04145789714775966,
  "call_jam_short": 0.016682706452042353,
  "range_unraised": 0.37266850070471286,
  "range_bet": 0.11701893084290542,
  "range_raise": 0.13077239035766486,
  "value_eq": 0.6719107306994851,
  "bluff_freq": 0.14400572496546785,
  "bet_frac": 0.6855968117022267,
  "call_margin": 0.13884668598106914,
  "raise_eq": 0.895339104625666,
  "commit_spr": 2.0569469988943543,
  "icm_margin": 0.10336666870094852
 },
 "hist": [
  {
   "open_a": 0.16543974620173135,
   "open_b": 0.7150890152605227,
   "hu_open": 0.954219441435074,
   "hu_jam": 0.8408577621809941,
   "sh_widen": 0.28460830932355186,
   "sh_range": 0.9382281524404589,
   "jam_scale": 0.8008779302979434,
   "call_open": 0.09938101481548275,
   "threebet": 0.024900129043866792,
   "fourbet": 0.014424641600326587,
   "open_size": 2.1079924335259497,
   "threebet_mult": 2.8868720995520976,
   "steal_fold_bonus": 0.3003430329276239,
   "jam_m": 5.469489869239725,
   "jam_slope": 0.035657769181608165,
   "call_jam": 0.04541503220863012,
   "call_jam_short": 0.020567666543610225,
   "range_unraised": 0.43046585248700653,
   "range_bet": 0.12514097037604532,
   "range_raise": 0.10506738159105464,
   "value_eq": 0.699192759762002,
   "bluff_freq": 0.12481735560334867,
   "bet_frac": 0.7365074475793245,
   "call_margin": 0.12879289528205945,
   "raise_eq": 0.8663684664632005,
   "commit_spr": 1.9947161859491598,
   "icm_margin": 0.11356356344402671
  },
  {
   "open_a": 0.17703035873715178,
   "open_b": 0.7298457171550883,
   "hu_open": 0.9535419232781647,
   "hu_jam": 0.8530740680481335,
   "sh_widen": 0.21875351890796596,
   "sh_range": 0.9585395463749398,
   "jam_scale": 0.810757224075977,
   "call_open": 0.09046198538457369,
   "threebet": 0.03335291113965051,
   "fourbet": 0.013655644941717148,
   "open_size": 2.1359406531039533,
   "threebet_mult": 2.9273495786538803,
   "steal_fold_bonus": 0.2638079569913188,
   "jam_m": 5.473761332753948,
   "jam_slope": 0.02940918488809497,
   "call_jam": 0.043291923197167535,
   "call_jam_short": 0.023466640852725665,
   "range_unraised": 0.4241645742459761,
   "range_bet": 0.11784591526497036,
   "range_raise": 0.10776729138350175,
   "value_eq": 0.7137201779249855,
   "bluff_freq": 0.11800085785254466,
   "bet_frac": 0.6961191994108669,
   "call_margin": 0.13658698926601479,
   "raise_eq": 0.8573427781322358,
   "commit_spr": 1.9973781765064829,
   "icm_margin": 0.11575333830472193
  },
  {
   "open_a": 0.1695327584481186,
   "open_b": 0.7706698881883913,
   "hu_open": 0.9552891394802623,
   "hu_jam": 0.854722783091258,
   "sh_widen": 0.24570064289027127,
   "sh_range": 0.9875980794663777,
   "jam_scale": 0.7558797746226229,
   "call_open": 0.09637366181365047,
   "threebet": 0.04259045817478534,
   "fourbet": 0.01398469437587969,
   "open_size": 2.115721355383313,
   "threebet_mult": 2.986042993615774,
   "steal_fold_bonus": 0.24867072248958733,
   "jam_m": 5.427072400055135,
   "jam_slope": 0.03351480024381321,
   "call_jam": 0.04053473490773174,
   "call_jam_short": 0.019181128869452592,
   "range_unraised": 0.436951027121131,
   "range_bet": 0.11903146769711612,
   "range_raise": 0.10727228289818252,
   "value_eq": 0.6837668284642665,
   "bluff_freq": 0.1525468341682556,
   "bet_frac": 0.7094379739844421,
   "call_margin": 0.138888330198514,
   "raise_eq": 0.8639456460099706,
   "commit_spr": 1.9783279590124558,
   "icm_margin": 0.10240616190576962
  },
  {
   "open_a": 0.17048881798508575,
   "open_b": 0.7673679812424996,
   "hu_open": 0.9565939230768672,
   "hu_jam": 0.8622691650115364,
   "sh_widen": 0.3224399606451786,
   "sh_range": 0.9697120922375784,
   "jam_scale": 0.7724074556130488,
   "call_open": 0.1057888591683694,
   "threebet": 0.038222220990180814,
   "fourbet": 0.013059262373658134,
   "open_size": 2.0920137103892475,
   "threebet_mult": 2.977110415522179,
   "steal_fold_bonus": 0.23966653284955097,
   "jam_m": 5.422486843999057,
   "jam_slope": 0.030519730898931015,
   "call_jam": 0.04381193587239352,
   "call_jam_short": 0.017979583221284377,
   "range_unraised": 0.40691241163592157,
   "range_bet": 0.1194352655734254,
   "range_raise": 0.10663353662394001,
   "value_eq": 0.6939488572787884,
   "bluff_freq": 0.13682818793789006,
   "bet_frac": 0.6723498733565694,
   "call_margin": 0.13864423598530615,
   "raise_eq": 0.8382939863083838,
   "commit_spr": 1.9814163455190084,
   "icm_margin": 0.09812851017862156
  },
  {
   "open_a": 0.17390210757208371,
   "open_b": 0.7596135977731993,
   "hu_open": 0.9731770449699678,
   "hu_jam": 0.8648109869127956,
   "sh_widen": 0.38429229005334975,
   "sh_range": 0.8301718180257405,
   "jam_scale": 0.8373006098925677,
   "call_open": 0.09644864125302453,
   "threebet": 0.03805910261269689,
   "fourbet": 0.012690881433594025,
   "open_size": 2.095944693766966,
   "threebet_mult": 3.0145489736355695,
   "steal_fold_bonus": 0.24614074547190173,
   "jam_m": 5.714088246871752,
   "jam_slope": 0.024682364610583638,
   "call_jam": 0.04589035793683627,
   "call_jam_short": 0.01667261104052505,
   "range_unraised": 0.37741361601768253,
   "range_bet": 0.1191756582794222,
   "range_raise": 0.09741072958959102,
   "value_eq": 0.6873712697436852,
   "bluff_freq": 0.11887632391470974,
   "bet_frac": 0.6898688737752008,
   "call_margin": 0.1384027103929482,
   "raise_eq": 0.8596315590633602,
   "commit_spr": 2.0583386354331337,
   "icm_margin": 0.0914571302217822
  },
  {
   "open_a": 0.1786314319480103,
   "open_b": 0.7583578939172803,
   "hu_open": 0.9686061708624192,
   "hu_jam": 0.8667965432881503,
   "sh_widen": 0.3884684690158996,
   "sh_range": 0.7939166331084284,
   "jam_scale": 0.851608193591426,
   "call_open": 0.09106161262697332,
   "threebet": 0.03336825643537756,
   "fourbet": 0.012756387463829908,
   "open_size": 2.0758285619700962,
   "threebet_mult": 3.0219478972668776,
   "steal_fold_bonus": 0.24696343379042457,
   "jam_m": 5.589939923448496,
   "jam_slope": 0.023411620097076577,
   "call_jam": 0.04393248906353345,
   "call_jam_short": 0.016769485531253313,
   "range_unraised": 0.37420089638835463,
   "range_bet": 0.1184135580558756,
   "range_raise": 0.10097299047633958,
   "value_eq": 0.6905356917136459,
   "bluff_freq": 0.12916301590251777,
   "bet_frac": 0.693001453397346,
   "call_margin": 0.14114739453476785,
   "raise_eq": 0.88022369670493,
   "commit_spr": 2.07222475538336,
   "icm_margin": 0.09644764353703966
  },
  {
   "open_a": 0.17741835840488485,
   "open_b": 0.76605361201931,
   "hu_open": 0.9623686839307659,
   "hu_jam": 0.8799498954741662,
   "sh_widen": 0.438936623239811,
   "sh_range": 0.7194856153377829,
   "jam_scale": 0.896516682149765,
   "call_open": 0.0895851906575708,
   "threebet": 0.036082515682146064,
   "fourbet": 0.012950177916325242,
   "open_size": 2.0741806459277683,
   "threebet_mult": 3.0351625446232786,
   "steal_fold_bonus": 0.24601477501841088,
   "jam_m": 5.491619930078975,
   "jam_slope": 0.025134597179467547,
   "call_jam": 0.041786460641275044,
   "call_jam_short": 0.016169440868820446,
   "range_unraised": 0.36911267217902616,
   "range_bet": 0.11423449509765612,
   "range_raise": 0.13468842456777672,
   "value_eq": 0.6722911848789412,
   "bluff_freq": 0.14773080015059195,
   "bet_frac": 0.6973726406988752,
   "call_margin": 0.13833928080421898,
   "raise_eq": 0.8932223493804019,
   "commit_spr": 2.1216836515755713,
   "icm_margin": 0.09837305797645342
  },
  {
   "open_a": 0.1757818625183531,
   "open_b": 0.7654950443077992,
   "hu_open": 0.974194853826461,
   "hu_jam": 0.874551058197748,
   "sh_widen": 0.4552109058033953,
   "sh_range": 0.7324084059007265,
   "jam_scale": 0.9003533308998516,
   "call_open": 0.09106339361079707,
   "threebet": 0.03728986456162825,
   "fourbet": 0.012542054298942736,
   "open_size": 2.084503517164194,
   "threebet_mult": 3.046062469264748,
   "steal_fold_bonus": 0.24923497874622375,
   "jam_m": 5.447133656697666,
   "jam_slope": 0.02793868562818342,
   "call_jam": 0.04145789714775966,
   "call_jam_short": 0.016682706452042353,
   "range_unraised": 0.37266850070471286,
   "range_bet": 0.11701893084290542,
   "range_raise": 0.13077239035766486,
   "value_eq": 0.6719107306994851,
   "bluff_freq": 0.14400572496546785,
   "bet_frac": 0.6855968117022267,
   "call_margin": 0.13884668598106914,
   "raise_eq": 0.895339104625666,
   "commit_spr": 2.0569469988943543,
   "icm_margin": 0.10336666870094852
  }
 ]
}
````

<!-- FILE: lab/exploit_0.json -->
````json
{
"mu": {
"open_a": 0.1724677678705957,
"open_b": 0.7252266805663437,
"hu_open": 0.9555095206665043,
"hu_jam": 0.9811960646289772,
"sh_widen": 0.7729148299249884,
"sh_range": 0.2722798703329023,
"jam_scale": 1.1440501944883787,
"call_open": 0.07960357846733165,
"threebet": 0.04088514867980683,
"fourbet": 0.011685095320543789,
"open_size": 2.113637005555376,
"threebet_mult": 3.081431803793298,
"steal_fold_bonus": 0.21591319263037995,
"jam_m": 6.040212220031699,
"jam_slope": 0.050641346274622065,
"call_jam": 0.03426656835013188,
"call_jam_short": 0.02608623099912937,
"range_unraised": 0.8170063624758167,
"range_bet": 0.12496025628189264,
"range_raise": 0.1557066277049791,
"value_eq": 0.6933851603603727,
"bluff_freq": 0.26518442698856026,
"bet_frac": 0.6032481369767818,
"call_margin": 0.1366461623204806,
"raise_eq": 0.8412842333627305,
"commit_spr": 2.42508975360683,
"icm_margin": 0.10671678467689988,
"w_0_0": -1.4225725403698313,
"w_0_1": 2.964585171340789,
"w_0_2": 3.0,
"w_0_3": 1.2710114634148315,
"w_0_4": 3.0,
"w_0_5": -2.1479494763528235,
"w_0_6": 2.535475005212124,
"w_0_7": 3.0,
"w_0_8": 0.7375841661003553,
"w_0_9": 3.0,
"w_0_10": 2.160412587195629,
"w_0_11": 3.0,
"w_0_12": 2.3546938033215055,
"w_0_13": 3.0,
"w_1_0": -3.0,
"w_1_1": -1.1483883164399424,
"w_1_2": 3.0,
"w_1_3": -3.0,
"w_1_4": 3.0,
"w_1_5": -1.1025579784555744,
"w_1_6": -2.150114563448407,
"w_1_7": -3.0,
"w_1_8": 0.24710027600936435,
"w_1_9": -2.460314237701632,
"w_1_10": 0.527233395369858,
"w_1_11": 0.4322224717874601,
"w_1_12": 0.7452750131148589,
"w_1_13": 0.8595268812981613,
"w_2_0": 3.0,
"w_2_1": 3.0,
"w_2_2": -3.0,
"w_2_3": -1.0665413429413022,
"w_2_4": -1.6230712962321985,
"w_2_5": 3.0,
"w_2_6": -3.0,
"w_2_7": 2.001427438941871,
"w_2_8": -1.233871635462343,
"w_2_9": -2.5075221895564574,
"w_2_10": -3.0,
"w_2_11": -1.6191702294117993,
"w_2_12": 3.0,
"w_2_13": 3.0,
"w_3_0": -3.0,
"w_3_1": 3.0,
"w_3_2": -0.7816161141080573,
"w_3_3": 2.4459425377910913,
"w_3_4": -3.0,
"w_3_5": 0.06116580599790833,
"w_3_6": 3.0,
"w_3_7": 1.4058828981793514,
"w_3_8": 1.5469687643698595,
"w_3_9": -1.6240406671882845,
"w_3_10": -2.580341769133672,
"w_3_11": -2.641278286043392,
"w_3_12": 3.0,
"w_3_13": -1.923359553417913,
"w_4_0": -3.0,
"w_4_1": -2.9343169929385304,
"w_4_2": -0.8081337936359727,
"w_4_3": -3.0,
"w_4_4": -1.6153802935339185,
"w_4_5": 2.1906549400634123,
"w_4_6": -2.97463711354268,
"w_4_7": 3.0,
"w_4_8": -3.0,
"w_4_9": -2.507228464647958,
"w_4_10": -2.0845720340621012,
"w_4_11": -1.4279215498555893,
"w_4_12": -3.0,
"w_4_13": -1.989558372724584
}
}
````

<!-- FILE: lab/exploit_1.json -->
````json
{
"mu": {
"open_a": 0.1724677678705957,
"open_b": 0.7252266805663437,
"hu_open": 0.9555095206665043,
"hu_jam": 0.9811960646289772,
"sh_widen": 0.7729148299249884,
"sh_range": 0.2722798703329023,
"jam_scale": 1.1440501944883787,
"call_open": 0.07960357846733165,
"threebet": 0.04088514867980683,
"fourbet": 0.011685095320543789,
"open_size": 2.113637005555376,
"threebet_mult": 3.081431803793298,
"steal_fold_bonus": 0.21591319263037995,
"jam_m": 6.040212220031699,
"jam_slope": 0.050641346274622065,
"call_jam": 0.03426656835013188,
"call_jam_short": 0.02608623099912937,
"range_unraised": 0.8170063624758167,
"range_bet": 0.12496025628189264,
"range_raise": 0.1557066277049791,
"value_eq": 0.6933851603603727,
"bluff_freq": 0.26518442698856026,
"bet_frac": 0.6032481369767818,
"call_margin": 0.1366461623204806,
"raise_eq": 0.8412842333627305,
"commit_spr": 2.42508975360683,
"icm_margin": 0.10671678467689988,
"w_0_0": 2.1537930427137937,
"w_0_1": -2.990314038175026,
"w_0_2": -0.4727596788521766,
"w_0_3": 2.4478689075720617,
"w_0_4": -2.126247802462452,
"w_0_5": -1.5019592091565093,
"w_0_6": 2.712065196865148,
"w_0_7": 2.885847654781897,
"w_0_8": -1.5486267442251815,
"w_0_9": 2.987006569010971,
"w_0_10": 3.0,
"w_0_11": -0.0011658724539218568,
"w_0_12": 0.1907936084612647,
"w_0_13": 0.7402589304319993,
"w_1_0": 2.151420268514043,
"w_1_1": 1.2866995154002563,
"w_1_2": -1.364553296222058,
"w_1_3": -1.5014570461338934,
"w_1_4": 0.37235046842819663,
"w_1_5": 2.598389189189165,
"w_1_6": -2.515501053237185,
"w_1_7": -1.9180017652588872,
"w_1_8": -3.0,
"w_1_9": 3.0,
"w_1_10": -2.561967111784098,
"w_1_11": 0.9590291944299252,
"w_1_12": 2.1130223929132974,
"w_1_13": -1.04235313002401,
"w_2_0": 2.741841241830283,
"w_2_1": 1.2408587989828872,
"w_2_2": 1.4993071236088014,
"w_2_3": -0.8812678952166633,
"w_2_4": 0.9722810546230316,
"w_2_5": 3.0,
"w_2_6": 1.1192722965140405,
"w_2_7": 0.8509158941343058,
"w_2_8": -0.3397591257524297,
"w_2_9": -3.0,
"w_2_10": -3.0,
"w_2_11": -2.2089591316542228,
"w_2_12": -1.325625259128162,
"w_2_13": 0.28798910668339417,
"w_3_0": -3.0,
"w_3_1": 0.3678306939660403,
"w_3_2": -2.136864555818511,
"w_3_3": -3.0,
"w_3_4": 1.9496112174964235,
"w_3_5": 2.5631098734933584,
"w_3_6": -2.004651831005898,
"w_3_7": -0.417037328618612,
"w_3_8": 2.0553855925937707,
"w_3_9": 0.6095477543950789,
"w_3_10": 2.5620334268915954,
"w_3_11": -0.8672160411481613,
"w_3_12": -2.9761720426801035,
"w_3_13": -1.2146595595492466,
"w_4_0": -0.8965719750985133,
"w_4_1": 2.686867931196959,
"w_4_2": 2.384505343322216,
"w_4_3": -2.1698177138411503,
"w_4_4": -2.5808750106265794,
"w_4_5": 0.16456140604331093,
"w_4_6": 2.0682302747260923,
"w_4_7": -0.09971240220690847,
"w_4_8": 0.35539259275427426,
"w_4_9": 2.5325188122194486,
"w_4_10": 0.4639384428260267,
"w_4_11": 0.9646071247503176,
"w_4_12": -1.794345856492833,
"w_4_13": 0.0707573035004696
}
}
````

<!-- FILE: lab/exploit_2.json -->
````json
{
"mu": {
"open_a": 0.1724677678705957,
"open_b": 0.7252266805663437,
"hu_open": 0.9555095206665043,
"hu_jam": 0.9811960646289772,
"sh_widen": 0.7729148299249884,
"sh_range": 0.2722798703329023,
"jam_scale": 1.1440501944883787,
"call_open": 0.07960357846733165,
"threebet": 0.04088514867980683,
"fourbet": 0.011685095320543789,
"open_size": 2.113637005555376,
"threebet_mult": 3.081431803793298,
"steal_fold_bonus": 0.21591319263037995,
"jam_m": 6.040212220031699,
"jam_slope": 0.050641346274622065,
"call_jam": 0.03426656835013188,
"call_jam_short": 0.02608623099912937,
"range_unraised": 0.8170063624758167,
"range_bet": 0.12496025628189264,
"range_raise": 0.1557066277049791,
"value_eq": 0.6933851603603727,
"bluff_freq": 0.26518442698856026,
"bet_frac": 0.6032481369767818,
"call_margin": 0.1366461623204806,
"raise_eq": 0.8412842333627305,
"commit_spr": 2.42508975360683,
"icm_margin": 0.10671678467689988,
"w_0_0": -1.4443337232605282,
"w_0_1": 2.5378718425503246,
"w_0_2": 1.3190782962349106,
"w_0_3": 2.198002951120958,
"w_0_4": 3.0,
"w_0_5": -3.0,
"w_0_6": 3.0,
"w_0_7": 3.0,
"w_0_8": 2.5623993475731126,
"w_0_9": 1.6598917549014889,
"w_0_10": 1.7317863973522005,
"w_0_11": -1.4815967302383872,
"w_0_12": 0.40436835604828403,
"w_0_13": 3.0,
"w_1_0": 2.4514033158381894,
"w_1_1": 1.927583936928424,
"w_1_2": -0.6652543198566985,
"w_1_3": 0.6520381928565104,
"w_1_4": -0.22935045313888835,
"w_1_5": -3.0,
"w_1_6": 1.7515475166192935,
"w_1_7": 0.3523476303576887,
"w_1_8": -3.0,
"w_1_9": -2.4839378904301777,
"w_1_10": 1.7482406126849144,
"w_1_11": 3.0,
"w_1_12": -3.0,
"w_1_13": -2.385713293859432,
"w_2_0": 0.16056019852391668,
"w_2_1": -2.7663775696651904,
"w_2_2": -1.062860008850639,
"w_2_3": -2.8230898229497376,
"w_2_4": 3.0,
"w_2_5": -0.3681061757837343,
"w_2_6": 1.838932272671805,
"w_2_7": -1.8748741486197225,
"w_2_8": -0.9768715744863021,
"w_2_9": 0.947101405688807,
"w_2_10": -2.2779272264696706,
"w_2_11": 3.0,
"w_2_12": 1.5505581565038469,
"w_2_13": -0.34005618257150383,
"w_3_0": 1.3312925226158514,
"w_3_1": 3.0,
"w_3_2": 2.0583536249568617,
"w_3_3": 0.9977216955214736,
"w_3_4": -3.0,
"w_3_5": 3.0,
"w_3_6": -2.4445841550446095,
"w_3_7": 1.7589601514751472,
"w_3_8": 2.6275023766740695,
"w_3_9": -2.903712086508393,
"w_3_10": -1.334926660533627,
"w_3_11": 0.5406801070318448,
"w_3_12": 1.424280388843572,
"w_3_13": -2.0567806582556547,
"w_4_0": -2.0424292647304063,
"w_4_1": 1.7426333135771692,
"w_4_2": -2.5686052213103507,
"w_4_3": 0.6454198936220674,
"w_4_4": 3.0,
"w_4_5": -2.4470967070324403,
"w_4_6": -0.398647255398457,
"w_4_7": -2.2426857234606796,
"w_4_8": -0.8265718190621367,
"w_4_9": -1.221396463737286,
"w_4_10": 2.2527534820386057,
"w_4_11": -2.3684297651465553,
"w_4_12": 0.526525642181646,
"w_4_13": -1.6734400862816396
}
}
````

<!-- FILE: lab/exploit_3.json -->
````json
{
"mu": {
"open_a": 0.1724677678705957,
"open_b": 0.7252266805663437,
"hu_open": 0.9555095206665043,
"hu_jam": 0.9811960646289772,
"sh_widen": 0.7729148299249884,
"sh_range": 0.2722798703329023,
"jam_scale": 1.1440501944883787,
"call_open": 0.07960357846733165,
"threebet": 0.04088514867980683,
"fourbet": 0.011685095320543789,
"open_size": 2.113637005555376,
"threebet_mult": 3.081431803793298,
"steal_fold_bonus": 0.21591319263037995,
"jam_m": 6.040212220031699,
"jam_slope": 0.050641346274622065,
"call_jam": 0.03426656835013188,
"call_jam_short": 0.02608623099912937,
"range_unraised": 0.8170063624758167,
"range_bet": 0.12496025628189264,
"range_raise": 0.1557066277049791,
"value_eq": 0.6933851603603727,
"bluff_freq": 0.26518442698856026,
"bet_frac": 0.6032481369767818,
"call_margin": 0.1366461623204806,
"raise_eq": 0.8412842333627305,
"commit_spr": 2.42508975360683,
"icm_margin": 0.10671678467689988,
"w_0_0": -3.0,
"w_0_1": -3.0,
"w_0_2": -1.0935917463999565,
"w_0_3": 1.6351024981365576,
"w_0_4": 3.0,
"w_0_5": 3.0,
"w_0_6": 3.0,
"w_0_7": 1.4763724696393368,
"w_0_8": 1.6037840515285486,
"w_0_9": 2.979298332584035,
"w_0_10": 1.493086401009184,
"w_0_11": 1.378853770970549,
"w_0_12": 2.337585213860147,
"w_0_13": 3.0,
"w_1_0": -0.6656644204693634,
"w_1_1": 1.6010934255053755,
"w_1_2": 2.460676268694569,
"w_1_3": -2.962549693496097,
"w_1_4": -3.0,
"w_1_5": 0.0400272792446259,
"w_1_6": 1.6188557829607326,
"w_1_7": -2.227927681860765,
"w_1_8": 0.10707616696364441,
"w_1_9": 0.08351305556416788,
"w_1_10": 3.0,
"w_1_11": 2.9308666065264752,
"w_1_12": 3.0,
"w_1_13": -1.1100809322705962,
"w_2_0": 2.5604028868069486,
"w_2_1": 2.9188506382286867,
"w_2_2": 2.2983510351108842,
"w_2_3": 1.6854975012513949,
"w_2_4": 0.12784711379316693,
"w_2_5": 2.265355329654269,
"w_2_6": 1.7041441735087162,
"w_2_7": 0.648612653072929,
"w_2_8": -2.299770669876587,
"w_2_9": -0.8371726269785289,
"w_2_10": -3.0,
"w_2_11": 0.3503566476381397,
"w_2_12": -3.0,
"w_2_13": -1.9091088499874491,
"w_3_0": 1.0673838958044968,
"w_3_1": -0.11987149617982418,
"w_3_2": 1.0874559166973388,
"w_3_3": -0.6511796169188502,
"w_3_4": -2.726569246829444,
"w_3_5": 3.0,
"w_3_6": -2.777723599171751,
"w_3_7": -3.0,
"w_3_8": 0.5026099400929791,
"w_3_9": -0.7789602076215081,
"w_3_10": -1.3892442646798076,
"w_3_11": -3.0,
"w_3_12": 1.7302461340576558,
"w_3_13": 0.5683595148215206,
"w_4_0": -3.0,
"w_4_1": -2.1124233799791368,
"w_4_2": -0.7192065571588682,
"w_4_3": -1.2729502242857182,
"w_4_4": -3.0,
"w_4_5": -0.05191475369815679,
"w_4_6": 3.0,
"w_4_7": -3.0,
"w_4_8": -2.8001152829540854,
"w_4_9": -1.1297464105857047,
"w_4_10": -2.9990307525245505,
"w_4_11": 3.0,
"w_4_12": -1.1807037214777676,
"w_4_13": 2.498526999111509
}
}
````

<!-- FILE: lab/table_holdem.json -->
````json
{"48,49": [0.00452, 0.8484], "44,45": [0.00905, 0.8303], "40,41": [0.01357, 0.7907], "36,37": [0.0181, 0.7739], "32,33": [0.02262, 0.7478], "28,29": [0.02715, 0.7248], "48,44": [0.03017, 0.6796], "24,25": [0.03469, 0.6993], "48,40": [0.03771, 0.663], "48,41": [0.04676, 0.6539], "48,36": [0.04977, 0.654], "48,32": [0.05279, 0.6528], "44,40": [0.05581, 0.6341], "48,45": [0.06486, 0.6394], "20,21": [0.06938, 0.6539], "48,37": [0.07843, 0.6445], "48,33": [0.08748, 0.6329], "48,28": [0.0905, 0.6382], "44,32": [0.09351, 0.6228], "44,41": [0.10256, 0.6116], "16,17": [0.10709, 0.6322], "48,24": [0.11011, 0.615], "44,36": [0.11312, 0.603], "44,28": [0.11614, 0.6158], "40,36": [0.11916, 0.5975], "48,29": [0.12821, 0.6152], "40,32": [0.13122, 0.6009], "48,20": [0.13424, 0.5995], "44,37": [0.14329, 0.5981], "48,16": [0.1463, 0.6018], "48,12": [0.14932, 0.602], "12,13": [0.15385, 0.6046], "48,8": [0.15686, 0.5935], "48,25": [0.16591, 0.6008], "44,33": [0.17496, 0.5776], "36,32": [0.17798, 0.564], "40,37": [0.18703, 0.5777], "44,29": [0.19608, 0.5786], "40,33": [0.20513, 0.5756], "40,28": [0.20814, 0.5716], "48,21": [0.21719, 0.5879], "48,4": [0.22021, 0.5829], "44,16": [0.22323, 0.5739], "48,13": [0.23228, 0.5799], "44,20": [0.23529, 0.5777], "36,28": [0.23831, 0.5537], "44,24": [0.24133, 0.5637], "48,0": [0.24434, 0.5735], "48,17": [0.25339, 0.5729], "8,9": [0.25792, 0.5727], "40,24": [0.26094, 0.5604], "44,25": [0.26998, 0.5629], "36,33": [0.27903, 0.548], "48,9": [0.28808, 0.5707], "32,28": [0.2911, 0.5387], "40,29": [0.30015, 0.5524], "44,21": [0.3092, 0.5559], "48,5": [0.31825, 0.5615], "48,1": [0.3273, 0.5481], "36,24": [0.33032, 0.5376], "44,4": [0.33333, 0.5429], "40,20": [0.33635, 0.5417], "36,29": [0.3454, 0.5343], "40,16": [0.34842, 0.5389], "44,12": [0.35143, 0.5426], "32,29": [0.36048, 0.5274], "4,5": [0.36501, 0.5467], "36,20": [0.36802, 0.5308], "44,0": [0.37104, 0.5292], "32,24": [0.37406, 0.52], "44,8": [0.37707, 0.5383], "40,25": [0.38612, 0.5353], "28,24": [0.38914, 0.505], "36,25": [0.39819, 0.5236], "44,17": [0.40724, 0.5323], "40,4": [0.41026, 0.5219], "40,17": [0.41931, 0.5316], "44,13": [0.42836, 0.5234], "32,20": [0.43137, 0.5041], "40,8": [0.43439, 0.5159], "40,21": [0.44344, 0.5258], "40,12": [0.44646, 0.509], "44,9": [0.45551, 0.5205], "36,16": [0.45852, 0.5008], "24,20": [0.46154, 0.4903], "28,20": [0.46456, 0.4936], "40,0": [0.46757, 0.5034], "32,16": [0.47059, 0.4976], "32,25": [0.47964, 0.495], "36,21": [0.48869, 0.5024], "44,1": [0.49774, 0.5104], "0,1": [0.50226, 0.5098], "44,5": [0.51131, 0.506], "36,12": [0.51433, 0.4893], "36,0": [0.51735, 0.4903], "28,25": [0.5264, 0.4768], "32,21": [0.53544, 0.494], "28,16": [0.53846, 0.4764], "36,8": [0.54148, 0.4873], "24,16": [0.54449, 0.4699], "40,13": [0.55354, 0.4944], "36,4": [0.55656, 0.4745], "40,9": [0.56561, 0.4883], "20,16": [0.56863, 0.4555], "40,1": [0.57768, 0.4898], "28,21": [0.58673, 0.4654], "32,12": [0.58974, 0.4734], "36,17": [0.59879, 0.4761], "24,21": [0.60784, 0.461], "40,5": [0.61689, 0.4789], "24,12": [0.61991, 0.4567], "28,12": [0.62293, 0.4629], "36,13": [0.63198, 0.474], "16,12": [0.63499, 0.4415], "32,4": [0.63801, 0.4531], "32,8": [0.64103, 0.4559], "32,17": [0.65008, 0.4617], "20,12": [0.65309, 0.4402], "36,9": [0.66214, 0.455], "28,8": [0.66516, 0.4432], "20,8": [0.66817, 0.4315], "36,5": [0.67722, 0.4544], "28,0": [0.68024, 0.4373], "28,17": [0.68929, 0.4395], "32,13": [0.69834, 0.4447], "32,0": [0.70136, 0.4406], "20,17": [0.71041, 0.4251], "32,9": [0.71946, 0.4415], "16,8": [0.72247, 0.419], "28,4": [0.72549, 0.431], "12,8": [0.72851, 0.4035], "24,8": [0.73152, 0.4228], "36,1": [0.74057, 0.4374], "20,13": [0.74962, 0.4195], "24,17": [0.75867, 0.4166], "24,13": [0.76772, 0.4176], "12,4": [0.77074, 0.3972], "16,13": [0.77979, 0.4041], "28,13": [0.78884, 0.417], "24,4": [0.79186, 0.4098], "20,4": [0.79487, 0.4036], "24,0": [0.79789, 0.4035], "32,5": [0.80694, 0.4093], "32,1": [0.81599, 0.4116], "8,4": [0.819, 0.3846], "16,9": [0.82805, 0.3881], "12,0": [0.83107, 0.38], "28,5": [0.84012, 0.4014], "16,4": [0.84314, 0.378], "20,9": [0.85219, 0.3919], "20,0": [0.8552, 0.3847], "24,9": [0.86425, 0.396], "28,1": [0.8733, 0.4024], "16,0": [0.87632, 0.3761], "12,9": [0.88537, 0.3792], "28,9": [0.89442, 0.3965], "4,0": [0.89744, 0.367], "12,5": [0.90649, 0.3693], "24,5": [0.91554, 0.3762], "8,5": [0.92459, 0.356], "8,0": [0.9276, 0.3549], "16,5": [0.93665, 0.3501], "24,1": [0.9457, 0.3603], "12,1": [0.95475, 0.349], "20,5": [0.9638, 0.36], "20,1": [0.97285, 0.3455], "16,1": [0.9819, 0.3351], "4,1": [0.99095, 0.3225], "8,1": [1.0, 0.3171]}
````

<!-- FILE: lab/strength_holdem.json -->
````json
{"4,1,5,0,0,1,1": [0.1163, 0.2614, 0.3594, 0.4814, 1631], "5,2,1,0,0,1,2": [0.3973, 0.4923, 0.559, 0.6499, 2541], "5,2,1,0,0,0,1": [0.8195, 0.8447, 0.8606, 0.8862, 1205], "4,2,1,0,0,1,1": [0.4537, 0.5593, 0.618, 0.7005, 2876], "4,0,2,1,0,0,2": [0.1609, 0.1827, 0.2092, 0.3227, 435], "4,1,3,0,0,0,2": [0.5119, 0.5776, 0.619, 0.6772, 92], "5,1,8,0,0,0,1": [0.228, 0.3213, 0.3888, 0.5108, 4276], "4,1,8,0,0,0,1": [0.2873, 0.3877, 0.447, 0.5587, 3901], "5,1,4,0,0,0,2": [0.362, 0.4362, 0.5167, 0.6514, 905], "3,0,1,0,0,0,1": [0.1669, 0.2061, 0.2598, 0.3662, 2505], "4,1,5,0,0,1,0": [0.1164, 0.27, 0.3642, 0.4837, 284], "3,1,5,0,0,1,0": [0.1941, 0.3259, 0.4208, 0.547, 911], "5,2,1,0,0,1,1": [0.4312, 0.5502, 0.6138, 0.7017, 5165], "3,1,4,0,0,0,1": [0.4309, 0.5142, 0.5768, 0.6832, 2478], "3,1,4,0,0,0,0": [0.4468, 0.5242, 0.5864, 0.6974, 1706], "5,1,6,0,0,1,2": [0.0, 0.0049, 0.0519, 0.245, 1189], "3,4,1,0,2,0,0": [0.9141, 0.9309, 0.9146, 0.9306, 84], "3,0,1,0,1,0,1": [0.279, 0.3005, 0.3329, 0.4221, 513], "5,1,2,0,0,0,2": [0.5361, 0.6161, 0.6767, 0.7514, 646], "3,0,1,0,0,0,0": [0.1674, 0.2105, 0.263, 0.369, 1820], "3,0,2,0,0,0,1": [0.1041, 0.1328, 0.1676, 0.2935, 6207], "5,6,1,0,0,1,2": [0.8956, 0.9133, 0.9335, 0.9472, 327], "4,0,1,0,0,0,1": [0.0729, 0.1165, 0.1833, 0.2831, 920], "4,1,8,0,1,0,1": [0.3766, 0.4434, 0.4974, 0.5646, 761], "5,1,8,0,0,0,2": [0.2061, 0.284, 0.3494, 0.466, 2756], "4,0,0,0,2,0,1": [0.2145, 0.3296, 0.402, 0.4372, 228], "3,0,0,0,0,0,0": [0.2027, 0.3489, 0.4222, 0.4837, 1201], "5,4,0,0,0,1,2": [0.4598, 0.4514, 0.4508, 0.4693, 85], "3,1,7,0,0,1,0": [0.1128, 0.1484, 0.173, 0.2672, 1027], "4,1,6,0,1,1,1": [0.1406, 0.1614, 0.193, 0.3835, 350], "3,0,0,0,0,0,1": [0.1993, 0.3341, 0.41, 0.4753, 1713], "3,1,8,0,0,0,1": [0.3496, 0.4321, 0.4777, 0.5611, 2682], "3,2,1,0,0,1,0": [0.4948, 0.589, 0.6457, 0.7161, 702], "5,1,6,0,0,1,1": [0.0, 0.0059, 0.054, 0.2594, 2523], "5,3,1,0,0,0,2": [0.7862, 0.8267, 0.8333, 0.833, 148], "4,0,2,1,1,0,2": [0.2235, 0.239, 0.2615, 0.3595, 244], "4,1,6,0,0,1,2": [0.0484, 0.0718, 0.1224, 0.2808, 171], "5,0,2,0,0,0,1": [0.0001, 0.0092, 0.0325, 0.146, 3849], "5,1,2,0,0,0,1": [0.5687, 0.6773, 0.7397, 0.8158, 977], "5,1,5,0,0,1,2": [0.0344, 0.1709, 0.2612, 0.3886, 1014], "3,1,4,0,0,0,2": [0.3712, 0.4247, 0.4833, 0.5836, 179], "3,3,1,0,0,1,0": [0.9048, 0.9138, 0.925, 0.941, 317], "3,1,0,0,0,0,0": [0.7185, 0.7787, 0.8078, 0.8144, 164], "4,3,1,0,0,1,1": [0.8904, 0.9072, 0.9216, 0.9363, 740], "3,1,3,0,0,0,1": [0.5633, 0.637, 0.6765, 0.7466, 836], "5,1,5,0,0,1,1": [0.0399, 0.1935, 0.2929, 0.4163, 2210], "3,1,5,0,0,1,1": [0.1931, 0.328, 0.4137, 0.5363, 878], "5,1,7,0,0,1,2": [0.0, 0.0, 0.0007, 0.0888, 1208], "5,3,0,0,0,1,1": [0.0186, 0.0792, 0.1391, 0.3125, 562], "4,0,2,0,1,0,1": [0.1179, 0.1406, 0.164, 0.2777, 2294], "4,2,1,0,0,0,1": [0.7972, 0.8277, 0.8459, 0.8779, 1056], "3,0,2,0,2,0,1": [0.3327, 0.3567, 0.3682, 0.4428, 473], "5,3,1,0,0,1,1": [0.8831, 0.9076, 0.9202, 0.9368, 887], "5,0,0,0,0,0,1": [0.0625, 0.2056, 0.2728, 0.3055, 823], "5,5,1,0,0,0,2": [0.8474, 0.8584, 0.8738, 0.9081, 904], "5,2,1,0,0,0,2": [0.7556, 0.7685, 0.7905, 0.8094, 837], "3,0,1,0,0,0,2": [0.1206, 0.1651, 0.1964, 0.3053, 165], "3,0,0,0,0,0,2": [0.1461, 0.2698, 0.3405, 0.388, 136], "4,1,4,0,1,0,1": [0.4457, 0.5249, 0.5894, 0.6759, 363], "4,1,8,0,0,0,0": [0.294, 0.3872, 0.4501, 0.5547, 532], "4,0,2,1,1,0,1": [0.303, 0.3017, 0.3263, 0.4019, 189], "3,1,8,0,1,0,1": [0.4709, 0.5282, 0.5733, 0.6114, 116], "3,1,2,0,0,0,0": [0.6246, 0.691, 0.7539, 0.8211, 914], "3,0,2,0,0,0,0": [0.1003, 0.1327, 0.1703, 0.3013, 4451], "5,0,2,0,0,0,2": [0.0001, 0.0094, 0.0312, 0.1364, 2334], "4,1,6,0,0,1,1": [0.0598, 0.0823, 0.137, 0.3339, 1778], "4,1,3,0,0,0,1": [0.5971, 0.667, 0.7284, 0.7795, 481], "5,3,1,0,0,1,2": [0.823, 0.8405, 0.8561, 0.877, 510], "4,1,7,0,2,1,1": [0.2052, 0.2372, 0.2392, 0.2742, 194], "5,2,0,0,0,1,2": [0.1437, 0.1976, 0.2559, 0.3945, 437], "4,0,2,0,2,0,2": [0.1513, 0.1731, 0.1848, 0.2776, 192], "5,4,1,0,0,1,2": [0.8042, 0.8293, 0.8428, 0.8597, 164], "3,1,6,0,0,1,0": [0.1361, 0.1673, 0.2215, 0.4034, 1059], "3,1,2,0,0,0,1": [0.5996, 0.6852, 0.7394, 0.8059, 1249], "5,1,7,0,0,1,1": [0.0, 0.0, 0.0009, 0.0983, 2607], "4,0,1,0,2,0,1": [0.2219, 0.2323, 0.2688, 0.3459, 285], "3,6,1,0,0,1,1": [0.9557, 0.9776, 0.984, 0.9693, 30], "4,0,2,0,0,0,1": [0.0298, 0.0528, 0.0858, 0.2193, 3730], "4,0,1,0,0,0,0": [0.0749, 0.1222, 0.1727, 0.2954, 143], "4,1,7,0,0,1,1": [0.0453, 0.0659, 0.0763, 0.1844, 1764], "4,1,7,0,0,1,0": [0.0498, 0.0648, 0.0794, 0.1803, 312], "4,0,2,0,0,0,0": [0.0289, 0.0548, 0.086, 0.2171, 534], "4,1,6,0,0,1,0": [0.0588, 0.0834, 0.1422, 0.3409, 306], "3,1,8,0,0,0,0": [0.3546, 0.4423, 0.4996, 0.5794, 1866], "4,2,1,0,0,0,0": [0.8135, 0.836, 0.8592, 0.887, 159], "3,1,2,0,0,0,2": [0.4981, 0.5638, 0.6253, 0.6793, 104], "5,0,0,0,0,0,2": [0.0485, 0.1628, 0.2352, 0.2815, 534], "4,0,2,0,0,0,2": [0.031, 0.0432, 0.0736, 0.1823, 650], "5,1,3,0,0,0,2": [0.5333, 0.6404, 0.6812, 0.692, 202], "5,2,0,0,0,1,1": [0.1466, 0.2131, 0.2641, 0.421, 1520], "3,2,1,0,0,0,1": [0.7804, 0.8085, 0.8244, 0.8563, 497], "5,1,4,0,0,0,1": [0.383, 0.484, 0.5634, 0.7086, 1410], "4,1,5,1,0,1,1": [0.3036, 0.3895, 0.4794, 0.6017, 126], "4,1,8,1,0,0,2": [0.3687, 0.446, 0.4802, 0.5961, 350], "4,1,4,0,0,0,2": [0.3587, 0.4361, 0.4963, 0.6252, 377], "3,0,1,0,2,0,1": [0.3766, 0.3985, 0.4204, 0.5013, 239], "4,1,2,0,0,0,2": [0.5041, 0.595, 0.6478, 0.7137, 265], "4,1,2,0,0,0,1": [0.602, 0.6869, 0.7549, 0.8277, 1235], "5,0,1,0,0,0,1": [0.0007, 0.036, 0.0863, 0.1619, 680], "4,4,1,0,2,0,1": [0.8917, 0.8872, 0.8872, 0.9071, 533], "4,5,1,0,0,0,2": [0.8287, 0.8446, 0.8622, 0.9055, 262], "4,0,2,0,1,0,2": [0.104, 0.1189, 0.1357, 0.2452, 410], "4,4,1,0,2,1,1": [0.8427, 0.8757, 0.885, 0.9031, 57], "3,1,7,0,0,1,1": [0.1135, 0.1491, 0.1664, 0.2616, 983], "4,1,4,0,0,0,1": [0.4242, 0.5018, 0.5826, 0.714, 1825], "5,0,1,0,0,0,2": [0.0006, 0.0383, 0.0736, 0.1518, 452], "5,5,1,0,0,1,2": [0.7789, 0.8144, 0.8437, 0.8849, 534], "5,4,1,0,0,1,1": [0.86, 0.8847, 0.9012, 0.9147, 365], "3,1,2,0,2,0,0": [0.5747, 0.7022, 0.7904, 0.8909, 10], "3,0,2,0,1,0,0": [0.2373, 0.2686, 0.2853, 0.3808, 854], "4,0,2,0,1,0,0": [0.124, 0.1329, 0.1563, 0.2832, 309], "4,0,2,0,2,0,1": [0.1726, 0.1904, 0.2145, 0.3238, 1126], "5,1,3,0,0,0,1": [0.6018, 0.6942, 0.7486, 0.7681, 278], "4,2,1,0,0,1,2": [0.4094, 0.4984, 0.5618, 0.6315, 330], "3,0,2,0,1,0,1": [0.2355, 0.2562, 0.2904, 0.3803, 1150], "3,1,8,0,0,0,2": [0.2882, 0.3611, 0.393, 0.4795, 206], "3,0,2,1,0,0,2": [0.3012, 0.3338, 0.3681, 0.4598, 321], "3,2,1,0,0,1,1": [0.4925, 0.5736, 0.6209, 0.6998, 699], "3,1,6,0,0,1,1": [0.1372, 0.1698, 0.2244, 0.3981, 940], "3,0,0,0,1,0,0": [0.2937, 0.4241, 0.5077, 0.5716, 189], "3,1,4,0,1,0,1": [0.5053, 0.5517, 0.631, 0.7043, 98], "3,0,1,1,0,0,1": [0.4685, 0.4846, 0.5065, 0.5963, 166], "3,1,0,0,0,0,1": [0.7095, 0.7774, 0.7871, 0.8023, 272], "3,0,2,1,0,0,1": [0.3879, 0.4158, 0.4439, 0.5284, 396], "4,0,0,0,2,0,0": [0.1911, 0.302, 0.3783, 0.4672, 35], "3,0,2,1,1,0,2": [0.398, 0.3925, 0.4429, 0.521, 45], "5,4,1,0,0,0,2": [0.8795, 0.8631, 0.8617, 0.8656, 615], "3,0,1,0,1,0,0": [0.2821, 0.3028, 0.3325, 0.4236, 401], "4,2,1,0,0,1,0": [0.4695, 0.5785, 0.6421, 0.7153, 500], "4,1,7,0,1,1,1": [0.141, 0.1602, 0.1704, 0.231, 430], "4,0,0,0,0,0,1": [0.1201, 0.2671, 0.341, 0.4017, 966], "4,1,8,1,1,0,2": [0.422, 0.499, 0.5097, 0.6, 66], "5,4,1,0,0,0,1": [0.9404, 0.9299, 0.9275, 0.9283, 961], "4,3,1,0,0,1,2": [0.807, 0.8318, 0.8159, 0.8482, 106], "4,0,2,0,2,0,0": [0.1736, 0.2022, 0.2102, 0.3281, 146], "4,0,1,0,1,0,1": [0.163, 0.18, 0.225, 0.3057, 665], "3,0,0,1,0,0,1": [0.468, 0.5788, 0.6384, 0.689, 109], "4,1,5,0,1,1,1": [0.1821, 0.3058, 0.396, 0.5254, 231], "4,1,6,0,2,1,1": [0.1954, 0.2195, 0.2617, 0.434, 149], "4,0,1,0,2,0,2": [0.1663, 0.2067, 0.2277, 0.3165, 56], "4,1,7,0,0,1,2": [0.0386, 0.0548, 0.0692, 0.1733, 177], "4,1,8,0,1,0,2": [0.3224, 0.4036, 0.4238, 0.4717, 154], "4,1,6,0,1,1,0": [0.1261, 0.1527, 0.1929, 0.3942, 70], "4,0,0,0,1,0,1": [0.1722, 0.3155, 0.3852, 0.4426, 501], "4,5,1,0,1,1,2": [0.8393, 0.8587, 0.8642, 0.9041, 16], "4,1,8,0,0,0,2": [0.2567, 0.3309, 0.3842, 0.4777, 793], "3,1,4,1,0,0,2": [0.5344, 0.6231, 0.6507, 0.7342, 82], "4,1,6,0,1,1,2": [0.1194, 0.1455, 0.1904, 0.3154, 33], "4,0,1,1,1,0,2": [0.2429, 0.2771, 0.3193, 0.4221, 81], "4,1,8,1,0,0,1": [0.4706, 0.5262, 0.5819, 0.6714, 166], "5,3,1,0,0,0,1": [0.8849, 0.9049, 0.9215, 0.9256, 188], "3,0,2,0,0,0,2": [0.0881, 0.1106, 0.1321, 0.2323, 434], "3,1,3,0,0,0,0": [0.5747, 0.6552, 0.7027, 0.7585, 567], "3,1,6,1,0,1,1": [0.42, 0.4133, 0.4892, 0.5989, 56], "4,1,3,1,0,0,1": [0.6563, 0.7838, 0.7848, 0.7737, 24], "5,7,1,0,0,1,1": [0.9992, 0.9991, 1.0, 1.0, 59], "4,1,2,0,1,0,2": [0.478, 0.5453, 0.5952, 0.699, 45], "4,1,4,0,1,0,2": [0.3998, 0.4204, 0.5066, 0.602, 72], "4,1,8,0,1,0,0": [0.4043, 0.4683, 0.5091, 0.5751, 91], "4,0,2,1,0,0,1": [0.221, 0.2366, 0.2706, 0.3849, 338], "4,4,1,0,2,0,2": [0.7699, 0.7627, 0.7675, 0.7758, 78], "5,1,0,0,0,0,2": [0.7372, 0.7743, 0.7584, 0.7537, 56], "4,0,2,1,2,0,2": [0.275, 0.2831, 0.3057, 0.4072, 106], "5,6,1,0,0,1,1": [0.8264, 0.8791, 0.9015, 0.9271, 879], "4,6,1,0,0,1,1": [0.8542, 0.8808, 0.906, 0.9299, 317], "3,3,1,0,0,0,0": [0.9151, 0.9307, 0.933, 0.9419, 107], "3,1,5,1,0,1,1": [0.4512, 0.5107, 0.6048, 0.6745, 57], "4,0,0,0,0,0,2": [0.1103, 0.2346, 0.2889, 0.357, 188], "3,2,1,0,0,0,2": [0.6798, 0.7067, 0.6991, 0.7209, 61], "3,6,1,0,0,1,0": [0.8836, 0.9133, 0.9547, 0.9579, 50], "4,1,4,0,0,0,0": [0.4168, 0.5133, 0.6007, 0.7213, 227], "5,5,0,0,0,1,2": [0.4428, 0.4506, 0.4572, 0.4737, 98], "4,1,4,1,0,0,1": [0.5271, 0.6321, 0.6669, 0.7778, 88], "4,0,1,0,1,0,0": [0.1654, 0.1903, 0.2311, 0.3121, 108], "4,0,1,0,0,0,2": [0.0619, 0.095, 0.1466, 0.2527, 171], "4,0,0,0,0,0,0": [0.117, 0.271, 0.3547, 0.4107, 145], "3,0,2,1,1,0,1": [0.4603, 0.5077, 0.5079, 0.6013, 76], "4,1,7,0,2,1,0": [0.2012, 0.2204, 0.2115, 0.2947, 33], "4,0,1,0,2,0,0": [0.2034, 0.2547, 0.2701, 0.351, 39], "4,1,4,0,2,0,1": [0.4656, 0.5353, 0.5835, 0.6701, 145], "4,2,1,0,0,0,2": [0.7015, 0.7291, 0.7411, 0.7582, 283], "3,1,7,0,2,1,0": [0.3575, 0.3848, 0.3858, 0.4251, 24], "4,0,0,0,2,0,2": [0.163, 0.2755, 0.3157, 0.3853, 35], "5,6,0,0,0,1,1": [0.3115, 0.393, 0.4197, 0.4582, 61], "3,3,0,0,0,1,0": [0.2012, 0.2777, 0.3336, 0.4661, 96], "4,1,0,0,0,0,1": [0.7723, 0.8192, 0.8277, 0.8188, 178], "4,1,7,1,0,1,1": [0.2137, 0.2441, 0.2486, 0.3423, 150], "4,1,5,0,0,1,2": [0.1086, 0.2458, 0.3268, 0.4234, 163], "4,2,0,0,0,1,1": [0.1612, 0.2241, 0.2667, 0.4074, 314], "4,3,1,0,0,0,1": [0.901, 0.9298, 0.9313, 0.9366, 264], "4,1,7,0,1,1,0": [0.1256, 0.1706, 0.1756, 0.2281, 78], "4,2,1,0,1,1,1": [0.4943, 0.6006, 0.6222, 0.7043, 107], "3,5,1,0,0,0,2": [0.8918, 0.9058, 0.9327, 0.9464, 78], "4,1,4,1,1,0,2": [0.4709, 0.5706, 0.63, 0.7203, 31], "3,0,1,0,2,0,0": [0.3984, 0.4111, 0.4363, 0.5104, 149], "4,2,1,0,1,0,1": [0.7, 0.6928, 0.7288, 0.7298, 47], "3,1,2,0,1,0,1": [0.6253, 0.6734, 0.7224, 0.7969, 39], "3,4,1,0,2,0,2": [0.7287, 0.7565, 0.7547, 0.7355, 9], "3,1,4,0,1,0,0": [0.5029, 0.5662, 0.6258, 0.7084, 69], "3,3,1,0,0,0,1": [0.8875, 0.8963, 0.9132, 0.9148, 201], "4,0,0,1,0,0,2": [0.2659, 0.3901, 0.4379, 0.498, 106], "3,1,4,0,2,0,0": [0.576, 0.6489, 0.6747, 0.6675, 27], "3,1,6,0,1,1,1": [0.2491, 0.2479, 0.2624, 0.4971, 28], "4,1,3,0,1,0,1": [0.5921, 0.669, 0.7153, 0.7311, 145], "4,1,2,1,0,0,1": [0.7097, 0.7576, 0.78, 0.8535, 69], "5,8,1,0,0,0,2": [1.0, 1.0, 1.0, 1.0, 9], "3,0,1,1,0,0,2": [0.3546, 0.3752, 0.4341, 0.524, 108], "3,1,6,0,1,1,0": [0.2387, 0.2658, 0.3168, 0.5061, 55], "4,1,5,0,2,1,2": [0.1616, 0.2557, 0.4078, 0.4633, 7], "4,3,1,1,0,1,2": [0.8487, 0.8381, 0.8716, 0.8968, 49], "4,1,6,1,0,1,1": [0.2367, 0.2658, 0.3226, 0.4716, 164], "3,1,8,0,2,0,1": [0.5348, 0.5675, 0.6022, 0.6599, 45], "3,2,1,0,0,0,0": [0.7915, 0.8399, 0.8468, 0.8834, 335], "3,0,0,1,1,0,2": [0.5181, 0.5672, 0.6308, 0.6763, 14], "3,0,2,0,2,0,0": [0.3335, 0.3363, 0.3693, 0.4563, 329], "3,4,1,0,2,0,1": [0.8843, 0.8897, 0.8911, 0.9036, 107], "4,2,1,1,0,1,2": [0.4782, 0.5683, 0.6203, 0.6901, 158], "4,2,1,1,0,1,1": [0.5677, 0.662, 0.7165, 0.7783, 110], "3,1,1,0,0,0,1": [0.5061, 0.628, 0.673, 0.6911, 25], "3,0,0,0,1,0,1": [0.2963, 0.4297, 0.4726, 0.5523, 258], "4,3,1,0,1,1,2": [0.787, 0.7713, 0.8178, 0.8302, 9], "4,1,5,1,0,1,2": [0.2363, 0.3664, 0.4579, 0.5363, 120], "4,1,6,0,2,1,2": [0.186, 0.2039, 0.191, 0.3929, 14], "3,3,1,0,0,1,1": [0.8769, 0.8924, 0.9061, 0.9214, 355], "4,1,4,0,1,0,0": [0.4164, 0.5091, 0.5766, 0.6474, 60], "4,3,1,0,0,1,0": [0.8919, 0.9126, 0.9236, 0.9416, 122], "4,3,1,0,0,0,2": [0.7924, 0.7888, 0.8321, 0.8199, 55], "4,1,2,0,0,0,0": [0.6169, 0.7057, 0.7647, 0.8418, 163], "4,1,2,0,1,0,1": [0.5632, 0.6599, 0.7179, 0.7902, 162], "4,0,1,0,1,0,2": [0.1278, 0.1651, 0.2018, 0.2655, 114], "5,4,0,0,0,1,1": [0.4696, 0.4605, 0.4663, 0.4898, 118], "4,2,1,1,2,1,2": [0.6184, 0.5971, 0.7455, 0.6606, 4], "5,3,0,0,0,1,2": [0.0234, 0.0811, 0.1319, 0.3035, 126], "4,4,1,1,2,0,2": [0.8596, 0.8538, 0.8508, 0.8596, 49], "4,1,5,0,1,1,0": [0.1942, 0.309, 0.3779, 0.5184, 40], "4,0,0,1,2,0,2": [0.2982, 0.3752, 0.4861, 0.4784, 15], "4,1,4,0,2,0,2": [0.3868, 0.4154, 0.4964, 0.5566, 37], "3,0,0,0,2,0,0": [0.3199, 0.4249, 0.5314, 0.5531, 77], "4,1,3,0,2,0,1": [0.5564, 0.6169, 0.6775, 0.7331, 61], "4,1,6,1,0,1,2": [0.1714, 0.1904, 0.2613, 0.4198, 100], "3,1,4,1,0,0,1": [0.6375, 0.684, 0.757, 0.7889, 56], "5,7,1,0,0,1,2": [1.0, 0.9955, 1.0, 1.0, 17], "4,2,1,1,0,0,2": [0.8054, 0.8107, 0.8229, 0.8534, 37], "4,0,2,1,2,0,1": [0.3293, 0.3357, 0.3883, 0.4534, 97], "3,1,5,0,1,1,0": [0.3263, 0.4553, 0.5185, 0.594, 31], "3,0,1,1,1,0,2": [0.4018, 0.4422, 0.4422, 0.54, 29], "4,2,1,0,1,0,2": [0.6315, 0.6097, 0.5425, 0.5658, 13], "4,1,4,1,0,0,2": [0.5021, 0.5485, 0.6219, 0.7285, 143], "3,1,1,0,1,0,1": [0.5734, 0.6869, 0.6909, 0.7082, 6], "5,1,0,0,0,0,1": [0.7542, 0.8315, 0.8131, 0.7812, 95], "3,1,8,1,0,0,1": [0.5806, 0.6412, 0.6769, 0.7147, 64], "3,1,2,1,0,0,1": [0.7575, 0.7859, 0.8491, 0.8917, 43], "4,1,3,1,1,0,1": [0.7058, 0.7469, 0.7448, 0.8218, 13], "3,5,1,0,2,0,2": [0.925, 0.8636, 0.9167, 0.975, 2], "4,3,0,0,0,1,1": [0.1056, 0.19, 0.2632, 0.4028, 247], "4,1,2,0,2,0,1": [0.5379, 0.6204, 0.6863, 0.7555, 76], "4,4,1,0,2,0,0": [0.9006, 0.8962, 0.9127, 0.9268, 97], "4,6,1,0,0,1,0": [0.7803, 0.8559, 0.8809, 0.9233, 73], "3,1,8,0,1,0,0": [0.4819, 0.5296, 0.5677, 0.6372, 83], "3,1,8,1,0,0,2": [0.4676, 0.5004, 0.5697, 0.6664, 85], "4,0,1,1,0,0,2": [0.2034, 0.2497, 0.3258, 0.41, 104], "4,1,6,1,2,1,1": [0.3792, 0.4503, 0.3821, 0.566, 7], "3,1,3,0,1,0,1": [0.5983, 0.6379, 0.6759, 0.7109, 61], "4,0,0,1,1,0,1": [0.346, 0.5152, 0.5524, 0.5567, 38], "4,2,1,0,2,1,1": [0.5144, 0.5821, 0.6262, 0.7072, 44], "4,3,1,0,0,0,0": [0.9277, 0.9633, 0.9539, 0.9468, 28], "3,0,1,1,1,0,1": [0.4867, 0.5292, 0.5489, 0.6603, 38], "4,1,3,0,0,0,0": [0.6056, 0.7151, 0.7341, 0.7935, 61], "3,1,3,1,0,0,1": [0.7121, 0.788, 0.7976, 0.8518, 23], "4,0,0,1,1,0,2": [0.2934, 0.3922, 0.488, 0.5324, 57], "3,1,2,1,0,0,2": [0.6889, 0.7401, 0.7558, 0.8403, 31], "4,1,8,0,2,0,1": [0.3926, 0.4507, 0.4965, 0.5621, 318], "3,1,7,1,0,1,1": [0.3677, 0.403, 0.4118, 0.5319, 72], "4,1,7,0,1,1,2": [0.1307, 0.1335, 0.1359, 0.1945, 46], "4,0,1,1,2,0,2": [0.277, 0.3162, 0.3357, 0.4245, 40], "4,0,1,1,1,0,1": [0.3056, 0.3819, 0.3749, 0.4405, 45], "4,1,2,1,0,0,2": [0.6217, 0.7118, 0.7401, 0.8204, 108], "3,1,1,0,0,0,0": [0.4356, 0.6523, 0.7049, 0.733, 14], "4,1,8,0,2,0,2": [0.3469, 0.403, 0.423, 0.4738, 77], "3,3,1,0,0,0,2": [0.8176, 0.7772, 0.8435, 0.8319, 18], "3,1,8,1,2,0,2": [0.6038, 0.6506, 0.6872, 0.7453, 3], "4,1,8,0,2,0,0": [0.449, 0.499, 0.4512, 0.5962, 39], "4,2,1,0,2,0,0": [0.4375, 0.448, 0.4947, 0.5204, 2], "3,5,1,0,1,0,2": [0.8784, 0.8761, 0.9263, 0.9544, 25], "3,0,0,0,2,0,1": [0.313, 0.4426, 0.5041, 0.5613, 93], "4,2,0,0,0,1,0": [0.1471, 0.1969, 0.2525, 0.3973, 60], "4,1,5,0,1,1,2": [0.1654, 0.3269, 0.3597, 0.4484, 19], "3,0,2,0,2,0,2": [0.2667, 0.3312, 0.3201, 0.3668, 36], "4,1,5,0,2,1,1": [0.1924, 0.3528, 0.4265, 0.5685, 88], "3,1,5,0,1,1,1": [0.301, 0.3956, 0.4233, 0.6229, 26], "4,1,4,0,2,0,0": [0.4369, 0.5224, 0.5298, 0.6533, 22], "4,1,8,1,1,0,1": [0.5046, 0.5453, 0.5828, 0.6422, 36], "4,2,0,1,0,1,1": [0.2808, 0.3146, 0.3365, 0.4326, 31], "4,1,7,1,1,1,1": [0.2785, 0.3047, 0.3477, 0.3746, 35], "4,1,7,1,0,1,2": [0.1451, 0.1659, 0.1978, 0.3013, 108], "3,1,3,0,0,0,2": [0.4577, 0.5129, 0.5791, 0.6436, 76], "4,0,0,1,2,0,1": [0.3843, 0.4956, 0.544, 0.5744, 15], "4,1,5,1,1,1,1": [0.3283, 0.4628, 0.4937, 0.6298, 18], "3,0,1,0,1,0,2": [0.2197, 0.2417, 0.2491, 0.3237, 27], "4,1,5,0,2,1,0": [0.1994, 0.3102, 0.3785, 0.5914, 22], "4,1,3,0,2,0,0": [0.596, 0.6782, 0.704, 0.7291, 10], "4,1,2,0,1,0,0": [0.5294, 0.6851, 0.7062, 0.7766, 26], "4,1,4,1,2,0,2": [0.553, 0.5682, 0.6186, 0.6918, 13], "4,3,0,0,0,1,0": [0.1226, 0.1697, 0.2561, 0.386, 76], "4,3,1,0,1,0,1": [0.8419, 0.8298, 0.7949, 0.8467, 7], "3,1,3,0,1,0,0": [0.5581, 0.6494, 0.6734, 0.6913, 40], "4,3,1,1,0,1,1": [0.8957, 0.9389, 0.9575, 0.9503, 15], "3,1,8,0,2,0,0": [0.5531, 0.591, 0.6031, 0.6819, 39], "3,1,8,1,1,0,1": [0.5833, 0.717, 0.7416, 0.7427, 2], "4,0,0,1,0,0,1": [0.2768, 0.4102, 0.4712, 0.5378, 78], "3,0,2,0,1,0,2": [0.2282, 0.234, 0.2617, 0.3149, 71], "3,1,7,0,1,1,1": [0.2744, 0.2856, 0.3102, 0.3544, 65], "4,1,3,0,1,0,0": [0.5574, 0.6149, 0.6973, 0.7163, 22], "3,0,0,1,0,0,2": [0.4391, 0.5426, 0.5686, 0.5936, 82], "4,1,1,1,1,0,2": [0.5, 0.7368, 0.6667, 0.7273, 1], "4,1,6,1,1,1,1": [0.2448, 0.3236, 0.3505, 0.5082, 20], "4,1,0,0,2,0,1": [0.6342, 0.6438, 0.7074, 0.6943, 14], "3,1,4,0,1,0,2": [0.3493, 0.493, 0.4918, 0.4984, 9], "4,5,1,0,1,0,2": [0.8236, 0.8348, 0.8699, 0.9086, 114], "4,0,1,1,0,0,1": [0.2561, 0.3119, 0.3424, 0.4569, 84], "3,0,2,1,2,0,1": [0.4741, 0.5579, 0.5709, 0.6221, 30], "4,1,2,0,2,0,0": [0.489, 0.5002, 0.625, 0.7831, 7], "4,0,0,0,1,0,0": [0.1715, 0.3354, 0.4082, 0.4531, 74], "4,4,1,1,2,0,1": [0.918, 0.9208, 0.9206, 0.9459, 47], "4,1,0,0,1,0,0": [0.8173, 0.7547, 0.7219, 0.5847, 3], "3,1,7,0,1,1,0": [0.2704, 0.2766, 0.3343, 0.3638, 63], "4,0,0,0,1,0,2": [0.132, 0.2285, 0.2936, 0.3551, 68], "4,5,1,0,0,1,2": [0.8534, 0.8658, 0.8823, 0.9218, 65], "3,1,6,0,2,1,0": [0.383, 0.4, 0.4207, 0.5918, 19], "3,1,2,0,1,0,0": [0.6599, 0.6594, 0.7449, 0.8012, 29], "3,1,3,1,0,0,2": [0.5865, 0.6522, 0.7173, 0.7776, 35], "4,1,6,1,1,1,2": [0.222, 0.2232, 0.3135, 0.4836, 20], "4,1,5,1,2,1,1": [0.3273, 0.4082, 0.6475, 0.6833, 5], "4,1,3,1,1,0,2": [0.6109, 0.6315, 0.6787, 0.7363, 10], "3,0,2,1,2,0,2": [0.458, 0.4091, 0.525, 0.6276, 22], "3,0,0,1,1,0,1": [0.5357, 0.6462, 0.6925, 0.7211, 18], "4,1,3,1,0,0,2": [0.6098, 0.6921, 0.7178, 0.7895, 26], "3,1,8,0,1,0,2": [0.4076, 0.4452, 0.4817, 0.5284, 6], "3,4,1,1,2,0,2": [0.7804, 0.7729, 0.8605, 0.859, 4], "4,1,6,1,2,1,2": [0.2374, 0.2951, 0.3813, 0.5417, 11], "4,6,1,0,0,1,2": [0.9569, 0.9748, 0.9754, 0.9906, 24], "4,1,0,0,0,0,0": [0.7508, 0.8497, 0.8255, 0.8364, 28], "4,1,1,0,2,0,0": [0.5652, 0.9048, 0.8, 0.7368, 1], "4,3,1,0,1,1,1": [0.9145, 0.8926, 0.891, 0.9067, 35], "4,1,8,1,2,0,1": [0.5483, 0.6336, 0.6263, 0.6651, 16], "4,2,1,0,1,1,2": [0.3432, 0.5104, 0.5432, 0.5732, 15], "4,2,1,1,1,1,2": [0.5834, 0.6124, 0.6273, 0.7349, 4], "3,1,4,0,2,0,1": [0.5405, 0.6271, 0.6207, 0.7154, 38], "4,1,4,1,1,0,1": [0.5444, 0.6131, 0.72, 0.7905, 19], "3,1,7,0,2,1,1": [0.4015, 0.445, 0.4503, 0.424, 17], "4,2,0,0,1,1,0": [0.2044, 0.3221, 0.2529, 0.3745, 6], "4,7,1,0,0,1,1": [0.9965, 1.0, 1.0, 1.0, 17], "3,1,3,0,2,0,1": [0.6311, 0.662, 0.6747, 0.7744, 20], "4,1,7,1,1,1,2": [0.1698, 0.2598, 0.2452, 0.2818, 20], "4,3,0,1,0,1,1": [0.188, 0.288, 0.3268, 0.4311, 16], "4,1,8,1,2,0,2": [0.4314, 0.4874, 0.5572, 0.6264, 26], "4,4,1,0,2,1,0": [0.8157, 0.8578, 0.8959, 0.912, 11], "4,3,0,0,1,1,1": [0.1478, 0.2076, 0.2693, 0.3991, 9], "4,1,3,1,2,0,1": [0.5773, 0.7538, 0.7215, 0.7481, 4], "4,1,2,1,1,0,2": [0.5877, 0.7457, 0.756, 0.7905, 11], "4,1,7,0,2,1,2": [0.1952, 0.1899, 0.2151, 0.2675, 23], "3,1,0,1,1,0,2": [0.5677, 0.628, 0.8054, 0.8264, 2], "3,1,0,0,2,0,1": [0.6431, 0.719, 0.7577, 0.9276, 4], "3,0,0,0,1,0,2": [0.1897, 0.3137, 0.4597, 0.4375, 20], "5,1,1,0,0,0,1": [0.6354, 0.811, 0.7757, 0.6556, 2], "4,2,1,0,2,0,1": [0.5184, 0.5576, 0.6012, 0.637, 10], "4,1,5,1,1,1,2": [0.3471, 0.3969, 0.4517, 0.5976, 14], "3,0,1,0,2,0,2": [0.3025, 0.353, 0.3044, 0.4607, 17], "4,5,1,0,2,0,2": [0.8659, 0.863, 0.8993, 0.9262, 62], "4,7,1,0,0,1,2": [1.0, 1.0, 1.0, 1.0, 5], "3,1,2,1,2,0,1": [0.6922, 0.7909, 0.8135, 0.825, 2], "4,1,0,0,1,0,1": [0.6504, 0.7237, 0.7282, 0.7719, 19], "4,1,0,0,0,0,2": [0.656, 0.6982, 0.6934, 0.7052, 22], "4,2,1,1,0,0,1": [0.8069, 0.8557, 0.8663, 0.9248, 22], "4,3,1,1,0,0,2": [0.857, 0.8812, 0.8584, 0.9131, 12], "3,1,0,1,0,0,2": [0.7848, 0.81, 0.832, 0.8627, 14], "4,1,3,0,1,0,2": [0.4853, 0.6078, 0.6026, 0.6516, 35], "3,1,4,1,1,0,2": [0.4891, 0.6236, 0.6678, 0.8002, 5], "3,7,1,0,0,1,0": [1.0, 1.0, 1.0, 1.0, 8], "4,1,1,0,1,0,1": [0.5706, 0.6792, 0.7366, 0.6751, 5], "3,1,0,0,1,0,0": [0.7857, 0.8134, 0.7692, 0.8174, 5], "3,1,3,1,2,0,1": [0.6856, 0.8043, 0.8295, 0.6845, 2], "4,2,0,0,1,1,1": [0.2493, 0.2928, 0.2261, 0.3564, 14], "5,7,0,0,0,1,1": [0.2094, 0.1853, 0.214, 0.4128, 13], "4,2,1,0,1,1,0": [0.4791, 0.6176, 0.649, 0.7115, 24], "4,7,0,0,0,1,0": [0.4109, 0.4529, 0.5153, 0.6375, 4], "4,8,1,0,2,0,2": [1.0, 1.0, 1.0, 1.0, 2], "4,2,1,0,1,0,0": [0.6511, 0.6188, 0.624, 0.7285, 4], "4,3,1,0,1,1,0": [0.8961, 0.8907, 0.9097, 0.9397, 5], "3,8,1,0,2,0,2": [1.0, 1.0, 1.0, 1.0, 1], "3,0,1,1,2,0,2": [0.4537, 0.5037, 0.4767, 0.5839, 14], "4,1,2,0,2,0,2": [0.4544, 0.6039, 0.6803, 0.7252, 9], "4,0,1,1,2,0,1": [0.396, 0.3603, 0.4101, 0.5033, 32], "3,1,5,0,2,1,0": [0.2956, 0.4809, 0.6361, 0.6537, 6], "3,0,1,1,2,0,1": [0.5417, 0.628, 0.6226, 0.695, 17], "3,1,3,0,2,0,0": [0.6611, 0.681, 0.7445, 0.7206, 15], "4,1,0,1,0,0,2": [0.7364, 0.7819, 0.8025, 0.8453, 20], "3,1,5,0,2,1,1": [0.3179, 0.4345, 0.4339, 0.6809, 6], "4,1,3,0,2,0,2": [0.4976, 0.5351, 0.6028, 0.6752, 11], "4,1,3,1,2,0,2": [0.5487, 0.667, 0.647, 0.7416, 7], "4,1,7,1,2,1,2": [0.2941, 0.2996, 0.3033, 0.4059, 17], "4,1,7,1,2,1,1": [0.3357, 0.4076, 0.3806, 0.4288, 12], "3,1,8,1,1,0,2": [0.5477, 0.5918, 0.6344, 0.7348, 5], "4,4,1,0,2,1,2": [0.8071, 0.7303, 0.8155, 0.7381, 6], "3,1,2,0,1,0,2": [0.3684, 0.7333, 0.5833, 0.8158, 1], "4,1,6,0,2,1,0": [0.2068, 0.2349, 0.2838, 0.4613, 24], "4,2,1,0,2,0,2": [0.3433, 0.3774, 0.509, 0.5113, 5], "3,1,0,0,1,0,1": [0.5979, 0.6252, 0.7291, 0.776, 5], "4,2,1,0,2,1,0": [0.6396, 0.7382, 0.7501, 0.7939, 7], "3,1,4,1,2,0,1": [0.7353, 0.7812, 0.7667, 0.9048, 1], "3,1,2,1,1,0,1": [0.7632, 0.6944, 0.675, 0.9706, 1], "4,1,2,1,1,0,1": [0.6323, 0.7303, 0.7597, 0.8752, 12], "3,1,4,1,1,0,1": [0.6734, 0.6978, 0.7804, 0.7486, 8], "4,2,1,0,2,1,2": [0.5029, 0.4559, 0.6002, 0.6603, 8], "3,1,2,0,2,0,1": [0.5839, 0.6908, 0.7706, 0.7967, 11], "4,3,1,0,2,1,1": [0.8838, 0.8849, 0.8945, 0.8861, 13], "4,1,5,1,2,1,2": [0.2846, 0.4029, 0.4366, 0.5639, 8], "4,2,0,0,2,1,1": [0.2881, 0.338, 0.2664, 0.4063, 7], "3,1,8,0,2,0,2": [0.5417, 0.499, 0.5862, 0.5625, 2], "3,1,0,0,0,0,2": [0.5726, 0.6179, 0.6433, 0.7095, 15], "4,3,0,0,1,1,0": [0.1784, 0.2154, 0.257, 0.3244, 7], "4,1,1,0,0,0,0": [0.6818, 0.6522, 0.7222, 0.7632, 1], "5,1,1,0,0,0,2": [0.5714, 0.75, 0.8333, 0.7778, 1], "4,1,1,0,2,0,1": [0.3641, 0.5823, 0.5208, 0.6177, 3], "3,4,1,1,2,0,1": [0.9268, 0.9114, 0.9463, 0.9274, 14], "4,4,1,1,2,1,1": [0.9013, 0.9185, 0.8859, 0.9322, 6], "4,4,1,1,2,1,2": [0.7821, 0.8106, 0.8264, 0.8054, 7], "4,7,1,0,0,1,0": [1.0, 1.0, 1.0, 1.0, 8], "4,1,0,0,1,0,2": [0.5691, 0.585, 0.7982, 0.5749, 4], "3,1,3,0,1,0,2": [0.4378, 0.5375, 0.6271, 0.6268, 6], "4,3,1,1,2,1,2": [0.9318, 0.7961, 0.653, 0.9142, 2], "3,0,0,0,2,0,2": [0.2347, 0.3101, 0.3783, 0.4793, 8], "4,2,1,1,1,0,2": [0.7476, 0.7216, 0.8344, 0.6411, 2], "3,1,3,1,1,0,2": [0.6364, 0.6364, 0.675, 0.4783, 1], "3,1,6,0,2,1,1": [0.3168, 0.4024, 0.4079, 0.6003, 10], "4,3,1,0,2,1,0": [0.921, 0.8927, 0.9225, 0.9417, 5], "4,5,1,0,2,1,2": [0.7274, 0.912, 0.9507, 0.9481, 3], "4,2,1,1,1,1,1": [0.6136, 0.5844, 0.7917, 0.8971, 2], "3,1,1,0,2,0,0": [0.6957, 0.65, 0.6429, 0.6818, 1], "3,1,1,0,1,0,0": [0.608, 0.7274, 0.6863, 0.7661, 2], "4,1,2,1,2,0,1": [0.5165, 0.6939, 0.7391, 0.7775, 5], "4,3,1,0,1,0,2": [0.7222, 0.6382, 0.7192, 0.799, 2], "5,8,1,0,0,1,2": [1.0, 1.0, 1.0, 1.0, 4], "3,1,3,1,1,0,1": [0.7014, 0.6545, 0.7841, 0.8361, 2], "4,1,0,1,1,0,2": [0.7253, 0.7171, 0.7596, 0.6865, 2], "3,1,3,1,2,0,2": [0.7083, 0.6957, 0.6957, 0.7368, 1], "3,1,0,0,2,0,2": [0.4545, 0.65, 0.5952, 0.6957, 1], "4,1,1,0,0,0,1": [0.4783, 0.625, 0.7826, 0.6429, 1], "4,3,1,0,2,0,1": [0.6041, 0.6909, 0.6031, 0.7472, 2], "4,3,0,0,2,1,1": [0.1667, 0.1875, 0.2381, 0.0556, 1], "3,0,0,1,2,0,1": [0.3917, 0.4737, 0.5122, 0.75, 2], "3,1,7,1,2,1,1": [0.5521, 0.6354, 0.6125, 0.625, 2], "4,1,2,1,2,0,2": [0.6421, 0.6034, 0.7884, 0.7543, 5], "4,1,4,1,2,0,1": [0.5057, 0.6165, 0.6781, 0.6027, 4], "4,3,1,0,2,0,0": [0.7826, 0.9091, 0.5714, 0.65, 1], "4,3,1,1,1,1,1": [0.9095, 0.9039, 0.8, 0.9659, 2], "3,1,7,1,1,1,1": [0.5714, 0.6522, 0.6458, 0.6667, 1], "3,0,0,1,2,0,2": [0.4212, 0.5962, 0.6196, 0.7411, 4], "3,1,6,1,1,1,1": [0.4, 0.6316, 0.3, 0.7045, 1], "4,1,0,0,2,0,2": [0.5779, 0.7344, 0.8594, 0.8177, 2], "3,7,1,0,0,1,1": [1.0, 1.0, 1.0, 1.0, 1], "4,2,0,1,1,1,1": [0.3056, 0.2353, 0.3, 0.6053, 1], "3,1,4,0,2,0,2": [0.5212, 0.5471, 0.6148, 0.583, 2], "3,1,1,1,0,0,2": [0.4369, 0.7229, 0.6667, 0.7601, 2], "5,8,0,0,0,1,2": [0.4722, 0.4375, 0.4643, 0.5, 1], "4,3,0,1,1,1,1": [0.3, 0.6429, 0.5, 0.7895, 1], "4,3,0,0,2,1,0": [0.0, 0.2368, 0.3636, 0.5476, 1], "3,1,2,1,1,0,2": [0.7333, 0.8056, 0.7206, 0.8532, 2], "4,8,1,0,2,1,2": [1.0, 1.0, 1.0, 1.0, 2], "4,1,0,0,2,0,0": [0.683, 0.5721, 0.8003, 0.803, 2], "4,3,1,0,2,1,2": [0.619, 0.85, 0.7647, 0.9091, 1], "4,3,1,1,1,1,2": [0.7778, 0.775, 0.8333, 0.9412, 1], "4,1,1,0,1,0,2": [0.4583, 0.8043, 0.6429, 0.525, 1], "4,3,1,0,1,0,0": [0.875, 0.8261, 0.8235, 0.75, 1], "3,1,6,1,2,1,1": [0.6, 0.5, 0.6053, 0.625, 1], "3,1,4,1,2,0,2": [0.4737, 0.4348, 0.5217, 0.8095, 1], "4,2,0,0,2,1,0": [0.1389, 0.3438, 0.2059, 0.3529, 1], "4,1,0,1,2,0,2": [0.6471, 0.625, 0.725, 0.7778, 1]}
````

<!-- FILE: lab/nash_hu_holdem.json -->
````json
{
"depths": [
1,
1.5,
2,
2.5,
3,
3.5,
4,
5,
6,
7,
8,
9,
10,
12,
14,
16,
18,
20,
25,
30,
40
],
"jam": {
"AA": 40,
"KK": 40,
"QQ": 40,
"JJ": 40,
"TT": 40,
"99": 40,
"AKs": 40,
"88": 40,
"AQs": 40,
"AQo": 40,
"AJs": 40,
"ATs": 40,
"KQs": 40,
"AKo": 40,
"77": 40,
"AJo": 40,
"ATo": 40,
"A9s": 40,
"KTs": 40,
"KQo": 40,
"66": 40,
"A8s": 40,
"KJs": 40,
"K9s": 40,
"QJs": 40,
"A9o": 40,
"QTs": 40,
"A7s": 40,
"KJo": 40,
"A6s": 40,
"A5s": 40,
"55": 40,
"A4s": 40,
"A8o": 40,
"KTo": 40,
"JTs": 40,
"QJo": 40,
"K9o": 20,
"QTo": 40,
"Q9s": 40,
"A7o": 30,
"A3s": 40,
"K6s": 40,
"A5o": 30,
"K7s": 40,
"J9s": 40,
"K8s": 40,
"A2s": 40,
"A6o": 30,
"44": 40,
"Q8s": 30,
"K8o": 18,
"JTo": 40,
"A4o": 30,
"T9s": 40,
"Q9o": 20,
"K7o": 16,
"A3o": 25,
"A2o": 25,
"J8s": 40,
"K3s": 18,
"Q7s": 30,
"J9o": 20,
"Q6s": 25,
"K5s": 25,
"T9o": 30,
"33": 40,
"J7s": 30,
"K2s": 18,
"T8s": 40,
"K4s": 25,
"Q8o": 12,
"98s": 40,
"J8o": 12,
"K6o": 14,
"Q3s": 12,
"Q6o": 9,
"K5o": 14,
"T7s": 30,
"Q4s": 14,
"Q7o": 10,
"Q5s": 25,
"K4o": 12,
"J6s": 14,
"87s": 30,
"97s": 30,
"Q2s": 12,
"T6s": 18,
"T8o": 16,
"J7o": 7,
"K2o": 10,
"22": 40,
"K3o": 12,
"J5s": 14,
"J2s": 8,
"98o": 20,
"T7o": 10,
"96s": 25,
"J4s": 12,
"86s": 25,
"Q5o": 9,
"J3s": 10,
"Q4o": 8,
"76s": 30,
"Q2o": 7,
"97o": 10,
"T5s": 10,
"J6o": 6,
"87o": 18,
"Q3o": 7,
"85s": 18,
"95s": 14,
"J5o": 6,
"65s": 20,
"T3s": 7,
"T4s": 10,
"T6o": 5,
"75s": 20,
"J4o": 5,
"94s": 5,
"74s": 10,
"J3o": 5,
"92s": 3,
"96o": 4,
"T5o": 4,
"T2s": 6,
"76o": 10,
"T4o": 3.5,
"64s": 16,
"93s": 4,
"54s": 20,
"84s": 10,
"J2o": 4,
"75o": 2.5,
"86o": 6,
"85o": 3,
"53s": 14,
"65o": 8,
"95o": 3.5,
"83s": 2.5,
"73s": 2,
"82s": 2.5,
"T3o": 3,
"T2o": 3,
"43s": 7,
"64o": 2,
"52s": 2,
"93o": 2,
"63s": 2,
"74o": 2,
"72s": 2,
"84o": 2,
"92o": 2,
"62s": 2,
"54o": 2,
"94o": 2.5,
"32s": 1.5,
"53o": 1.5,
"83o": 1.5,
"43o": 1.5,
"42s": 1.5,
"63o": 1.5,
"82o": 1.5,
"52o": 1.5,
"73o": 1.5,
"72o": 1.5,
"62o": 1.5,
"32o": 1,
"42o": 1
},
"call": {
"AA": 40,
"KK": 40,
"QQ": 40,
"JJ": 40,
"TT": 40,
"99": 40,
"AKs": 40,
"88": 40,
"AQs": 40,
"AQo": 40,
"AJs": 40,
"ATs": 40,
"KQs": 40,
"AKo": 40,
"77": 40,
"AJo": 40,
"ATo": 40,
"A9s": 40,
"KTs": 30,
"KQo": 30,
"66": 40,
"A8s": 40,
"KJs": 40,
"K9s": 20,
"QJs": 25,
"A9o": 30,
"QTs": 20,
"A7s": 30,
"KJo": 25,
"A6s": 30,
"A5s": 25,
"55": 40,
"A4s": 25,
"A8o": 30,
"KTo": 20,
"JTs": 18,
"QJo": 18,
"K9o": 16,
"QTo": 16,
"Q9s": 14,
"A7o": 25,
"A3s": 20,
"K6s": 14,
"A5o": 20,
"K7s": 16,
"J9s": 12,
"K8s": 18,
"A2s": 20,
"A6o": 20,
"44": 30,
"Q8s": 12,
"K8o": 14,
"JTo": 12,
"A4o": 18,
"T9s": 12,
"Q9o": 10,
"K7o": 12,
"A3o": 16,
"A2o": 14,
"J8s": 10,
"K3s": 10,
"Q7s": 10,
"J9o": 9,
"Q6s": 10,
"K5s": 12,
"T9o": 8,
"33": 20,
"J7s": 8,
"K2s": 10,
"T8s": 9,
"K4s": 12,
"Q8o": 9,
"98s": 8,
"J8o": 7,
"K6o": 10,
"Q3s": 7,
"Q6o": 7,
"K5o": 10,
"T7s": 7,
"Q4s": 8,
"Q7o": 8,
"Q5s": 8,
"K4o": 9,
"J6s": 7,
"87s": 6,
"97s": 7,
"Q2s": 7,
"T6s": 6,
"T8o": 6,
"J7o": 6,
"K2o": 8,
"22": 14,
"K3o": 8,
"J5s": 6,
"J2s": 5,
"98o": 6,
"T7o": 5,
"96s": 6,
"J4s": 6,
"86s": 5,
"Q5o": 6,
"J3s": 5,
"Q4o": 6,
"76s": 5,
"Q2o": 5,
"97o": 5,
"T5s": 5,
"J6o": 5,
"87o": 4,
"Q3o": 5,
"85s": 4,
"95s": 5,
"J5o": 5,
"65s": 4,
"T3s": 4,
"T4s": 5,
"T6o": 4,
"75s": 4,
"J4o": 4,
"94s": 4,
"74s": 4,
"J3o": 4,
"92s": 3.5,
"96o": 4,
"T5o": 4,
"T2s": 4,
"76o": 4,
"T4o": 3.5,
"64s": 4,
"93s": 4,
"54s": 4,
"84s": 4,
"J2o": 4,
"75o": 3.5,
"86o": 4,
"85o": 3.5,
"53s": 4,
"65o": 3.5,
"95o": 3.5,
"83s": 3.5,
"73s": 3.5,
"82s": 3.5,
"T3o": 3.5,
"T2o": 3.5,
"43s": 3.5,
"64o": 3,
"52s": 3.5,
"93o": 3,
"63s": 3.5,
"74o": 3,
"72s": 3,
"84o": 3,
"92o": 3,
"62s": 3,
"54o": 3,
"94o": 3,
"32s": 3,
"53o": 3,
"83o": 2.5,
"43o": 3,
"42s": 3,
"63o": 2.5,
"82o": 2.5,
"52o": 2.5,
"73o": 2.5,
"72o": 2.5,
"62o": 2.5,
"32o": 2.5,
"42o": 2.5
},
"summary": [
[
1,
0.999833388870378,
0.999833388870378
],
[
1.5,
0.9821168207882451,
0.999833388870378
],
[
2,
0.8957162594871605,
0.999833388870378
],
[
2.5,
0.8206372134376535,
0.999833388870378
],
[
3,
0.78604944656457,
0.9193021632306587
],
[
3.5,
0.755933793813325,
0.825453104369937
],
[
4,
0.7400617592024387,
0.7411312870571558
],
[
5,
0.7175091962809791,
0.6213602504544748
],
[
6,
0.6853499813787569,
0.5485991848870897
],
[
7,
0.6644982089931821,
0.4902586518420463
],
[
8,
0.6298953641898158,
0.4495582920323698
],
[
9,
0.6079348613307889,
0.4058725020267256
],
[
10,
0.5896262331862236,
0.3751084982733261
],
[
12,
0.5299839721601101,
0.3333114703344238
],
[
14,
0.48603683136289955,
0.2959292603822861
],
[
16,
0.4470201737681209,
0.26834971550458575
],
[
18,
0.42743092674488126,
0.24073699918026345
],
[
20,
0.39974684155055445,
0.217348113725792
],
[
25,
0.35431603241352966,
0.173578892505917
],
[
30,
0.3177289319849646,
0.1452399225396463
],
[
40,
0.2492042622293325,
0.11020986971160456
]
],
"variant": "holdem"
}
````

