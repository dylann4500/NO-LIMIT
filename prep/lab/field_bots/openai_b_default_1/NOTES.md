# openai_b_default_1

A latency-bounded, adaptive no-limit hold'em tournament agent. Runtime requires
only the standard library, `eval7`, the documented SDK, and `preflop.json` beside
`agent.py`. There are no simulator imports, network calls, subprocesses or file
writes in the agent. All learned information stays in per-table memory; agent
instances and module globals retain no table-specific information.

## Strategy

- Position-specific opening charts, wider heads-up play and steals against
  observed folders. Equity tables cover 169 starting hand classes against 14
  continuing ranges; the offline builder uses 50,000 runouts per entry. Opening
  charts and value-reraise ranges are separate, so suited speculative hands do
  not displace AK in premium reraising decisions.
- Per-opponent voluntary participation, raising, aggression and folding
  statistics, with population priors while samples are small. Observed extreme
  aggression produces wider opponent ranges, fewer bluffs and larger value
  bets. Ranges tighten after cold calls, reraises and large commitments.
- Postflop ranges remove known cards and condition on betting, calling,
  check-raising, made-hand strength and draws. Native `eval7` runout equity is
  used on flop/turn; river equity enumerates the sampled range. Wide ranges
  have at most 128 stratified combinations; narrow ranges retain every combo.
- Multiway equity uses a conservative approximation with explicit corrections
  for correlated draws and shared-board ties. Cumulative contributions help
  distinguish a short all-in's main pot from bets against active opponents.
- Calls consider pot odds, position, future equity realization and stack depth.
  Large calls use exact ICM for the configured three-paid payout schedule.
  Other payout schedules remain supported with a conservative risk adjustment.
  Short-stack opens and reshoves use modeled fold equity and showdown equity,
  with extra caution on a four-player bubble.
- Value and protection bets use pot fractions, stack-to-pot ratio and opponent
  tendencies. Selective continuation bets, draw semibluffs and blocker bluffs
  supplement the value range. Thin river bets are restricted.

## Reliability and timing

The final action adapter selects only offered SDK action kinds, produces integer
raise totals and clamps them to the actual offered bounds. Free checking never
produces an unoffered fold. A last-resort exception guard returns a legal action
and records a diagnostic counter in memory; SDK tests assert that it never fires.

The working CPU budget is 65% of `config.decision_ms`, checked before strategy
work and periodically while filtering ranges, with time reserved for equity and
serialization. Below 25 ms of remaining time bank it uses a 45% budget, at most
64 sampled combinations and 160 runouts. Event processing avoids unnecessary
allocations. Cyclic garbage collection is disabled during action computation
and restored immediately afterward; the bot's temporary structures are acyclic. Ordinary decisions use approximately 2 KB of memory, far below
both the 16 KB free threshold and the 64 KB limit. Import-time assets are fixed;
there is no runtime training or preflop Monte Carlo.

A detailed timing probe found rare cyclic garbage-collection pauses, motivating
the final scoped collection control. Timing here also includes substantial
operating-system scheduling jitter. A measured
88.2 ms wall-time decision consumed only 183 microseconds of CPU. Such stalls
cannot be prevented by shortening a poker calculation. Tests therefore report
both actual play.py wall-time failures and separate CPU-budget measurements;
no zero-timeout claim is made for all local runs.

## Build iterations

1. Initial equity/range strategy: 100 mixed tables, seed 1; 19.62 points per self
   seat, upload passed, no illegal actions or exceptions, 17 timeouts. Profiling
   identified excessive Python work in range filtering as well as host stalls.
2. Reduced and optimized range samples; fixed a zero-stack all-in dealer edge
   case, position handling and side-pot accounting; separated opening and
   reraising ranges. A 200-table run, seed 17, scored 21.42 ± 0.71 points per self
   seat, upload passed, zero failed decisions.
3. Added EV-based reshoves, better reraise-conditioned ranges, tie-aware
   multiway evaluation and paired-board classification, then ran the release
   validation matrix. A preceding 1,000-table build (seed 41) scored
   20.85 ± 0.32 points; all 660,881 decisions were legal and exception-free,
   but 108 wall-time timeouts occurred on this loaded host. Reports are retained
   rather than filtering out these results.

## Tests

`test_agent.py` uses only the public fake SDK and eval7. It checks 2,500 generated
states across 2–8 players, every street, varying pot/stack/call sizes, all-in
calls and strict raise bounds. Regression cases cover an all-in or dead dealer,
free checks, AA value raises, weak-hand folds, royal-flush board ties with up to
8 players, paired-board hand classification, ICM symmetry and a short-stack
bubble, custom payouts, corrupt memory, and event/memory transfer between copies.
It also asserts that no exception guard was needed and memory stays under 16 KB.

`--cpu-scale 2.5` advances the agent's budget clock 2.5 times faster to exercise
its work limits for the slower tournament machines; reported process CPU times
are still the machine's actual measurements. This is a budget stress test,
not a substitute for running on the actual tournament hardware.

The public `play.py` is the only simulator entry point used. The release matrix
and multiple upload seeds are reproducible with `run_validation.py`. Test scripts
and offline builders are not imported by the runtime agent.

## Final results

The ordinary matrix plus the 200-table slowdown test totals **1,200 tables and
721,282 table decisions with zero failed decisions**.

All results below use the final agent and included equity asset. The final
ordinary matrix completed **1,000 tables and 592,035 decisions with zero failed
decisions**: no illegal actions, exceptions or timeouts. All four matrix upload
tests passed. Additional upload tests across seeds 701–732 passed **32/32**,
with 320 decisions and zero failures.

- Standard mix, 600 tables, seed 101: **21.23 ± 0.41** points per self seat versus
  12.5 fair share. Four copies, two check-or-fold bots, two min-raisers.
  Latency: median 47.6 µs, p99 247.7 µs. Report: `results_release_mixed.json`.
- Seven copies and one min-raiser, 150 tables, seed 211: **14.29 ± 0.57** points
  per self seat; the min-raiser earned zero points. Report:
  `results_release_7_self.json`.
- One copy and seven min-raisers, 150 tables, seed 307: **38.25 ± 0.83** points;
  63 first places, 87 second places, no lower finishes. Report:
  `results_release_7_raisers.json`.
- One copy and seven check-or-fold bots, 100 tables, seed 401:
  **49.69 ± 0.03** points; first by stack in every table. Residual hand-cap ICM
  accounts for the small difference from 50 points. Report:
  `results_release_7_passive.json`.
- Maximum memory across the ordinary matrix: **2,152 bytes**.
- The 2,500-state SDK regression suite passes both normally and with its budget
  clock scaled by 2.5. The scaled-clock run measured CPU p99 of 256 µs and max
  309 µs locally (640 µs and 772.5 µs after multiplying by 2.5). Both runs assert
  zero legality violations and zero exception-guard activations.

The final end-to-end **2.5× CPU probe**, seed 659, completed **200 tables,
129,247 table decisions, plus 10 upload decisions, with zero failed decisions**.
Upload passed and the exception guard was disabled. It scored **20.63 ± 0.72**
points. Across 129,257 measured calls, charged CPU was p99 **559 µs**, maximum
**926 µs**, with **zero CPU calls above 1 ms**. Per-thread CPU independently
measured p99 559.166 µs, max 927.542 µs. The public tester's wall latency was
median 127.7 µs, p99 636.8 µs, max 43.1 ms; the time bank absorbed the host pauses.
Report: `results_release_slow_machine.json`.

The proxy keeps cyclic GC disabled through its artificial CPU-burn loop and
restores it before returning, matching the final bot's collection policy.
Earlier diagnostic harness versions could charge collection during that extra
loop; their raw reports are retained under `results_pre_gc_*` and
`results_gc_scope_*`. A preceding 100-table probe of this same final agent also
measured zero CPU calls above 1 ms in 63,006 calls (max 937 µs), but had one
wall-time timeout on this host. Its report is retained as
`results_release_slow_machine_100.json`. The final tests establish a computational
margin on the provided slowdown model, not an absolute guarantee against OS
scheduling pauses.

The final agent SHA-256 is `5e863281475892ded204ba2260d589f9e33b72ba3e866aa1cfac40b4589241aa`.
The equity asset SHA-256 is
`36f9b434fbb3f154738f42870ff2af6cb82e90d2ad1bb0c6ebafa2ebdd4aaffa`.

Reproduce from the workspace root using the provided Python interpreter:

```sh
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_1/test_agent.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_1/test_agent.py --cpu-scale 2.5
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_1/run_validation.py
/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python lab/field_bots/openai_b_default_1/test_slow_machine.py --tables 200 --scale 2.5 --seed 659
```

Local opponents include exploitable check-or-fold and min-raise bots; these
scores measure local performance and do not establish an advantage against the
unseen tournament field. Range inference and multiway equity remain heuristic,
not a solved equilibrium strategy. The CPU slowdown test exercises the budget
policy but does not guarantee operating-system wall-time behavior on other
machines.
