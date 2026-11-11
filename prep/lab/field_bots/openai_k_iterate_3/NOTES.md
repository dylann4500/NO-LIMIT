# openai_k_iterate_3

The production entry point is `agent.py:Agent`. Its only runtime data file is
`equity.json`; both must be uploaded together. It uses the standard library,
`eval7`, and the provided SDK. No network, subprocesses, runtime file writes, or
information shared between tables are used by the playing agent.

**Approach**

- Preflop: an offline equity grid for all 169 hole-card classes against ten
  opponent ranges, with 50,000 Monte Carlo iterations per grid entry. Premium
  ordering includes domination and playability rather than ranking everything
  by equity against random cards. Opening ranges depend on position, limpers,
  depth, and table-local opponent reads. Opponent opening ranges also depend on
  position. Short-stack shoves estimate folds, single callers, multiple callers,
  and tournament risk.
- Postflop: infer a preflop range, condition it on betting pressure, made hands,
  and draws, then use compiled eval7 equity. Conditioning examines at most 128
  candidate combinations. Ordinary decisions use 400 runouts; large calls use
  1,000. River equity is exact against the retained range. Multiway equity is a
  bounded approximation, applied separately to eligible side-pot layers.
- Tournament decisions: large calls use exact marginal ICM for up to three
  prizes, with win/lose/fold stack scenarios. Multiway outcome scenarios are
  approximate. Simultaneous busts account for starting-stack order and average
  equal-stack ties. Other payout structures use a risk-premium approximation.
  Payouts, blinds, stacks, and remaining-player counts come from the state.
- Exploitation: smoothed VPIP, PFR, and postflop aggression update from public
  events. Repeatedly passive opponents invite wider steals. Loose preflop play
  alone does not establish automatic postflop bluffing. Against confirmed
  maniacs, the bot keeps deeper pots smaller while four or more players remain,
  then takes stronger opportunities to commit its stack. Heads-up and short
  stacks permit wider value aggression.
- Portability and legality: all learned state travels in JSON bytes. Copies of
  `Agent` hold no table state. Action kinds are matched to SDK action objects;
  the final adapter selects an offered kind and clamps integer raise totals to
  the exact offered bounds. Preflop order skips busted seats and handles the
  heads-up blind order.
- Timing: models load at import. Cyclic GC is deferred during the decision and
  its previous setting is restored afterward. Below 25 ms of bank, conditioning
  drops to at most 64 candidates and equity sampling to 200 iterations. Hand
  history is bounded, memory stays below the free 16 KB allowance, and truncated
  JSON can be recovered from.

**Build iterations**

1. Legal baseline with preflop tables, reads, and fast equity: **20.14 points**
   over 200 default-mix tables; 123,719 decisions, zero failures.
2. Board/action-conditioned ranges: **21.69 points** over 200 tables;
   137,894 decisions, zero failures.
3. ICM, short-stack EV, smaller range supports, and runtime hardening:
   **22.53 points** in the initial 300-table run. Further calibration favored
   controlling pots against maniacs. Review caught and fixed blind ordering
   after eliminations; opponent ranges were made position-dependent, and loose
   preflop play was separated from automatic postflop aggression. The frozen
   version's final results are below.

Some development/instrumented timing trials did time out under host contention.
Separate probes found wall-clock pauses much larger than thread CPU time. This
prompted bounded work, GC protection, and the low-bank path. An initial CPU-padding
wrapper also allowed GC around wrapper method allocation; the final harness uses
a cached direct call with the same GC protection as the bot. Final tests retain
the simulator's normal timeout enforcement and action validation.

**Final play.py results**

All eight final runs passed upload with zero failed upload decisions. All
**2,800 tables and 1,613,341 tournament decisions had zero failed decisions**:
no exceptions, illegal actions, or timeouts. These are local baseline results,
not evidence of a guaranteed score against the other tournament teams.

- Standard mix, 1,000 tables, seed 103: four self, two check-or-fold, two
  min-raiser. **23.63 mean points per self seat**, reported SE 0.30; fair share
  12.5. 734,971 decisions. Wall latency p50/p99: 50.2/245.6 microseconds.
  [Raw report](reports/default_1000.json).
- One self, seven check-or-fold, 200 tables, seed 107: **50.00 points**, all 200
  first places. [Raw report](reports/passive_200.json).
- One self, seven min-raiser, 300 tables, seed 109: **41.66 points**, all 300
  top-two finishes. [Raw report](reports/aggressive_300.json).
- Seven self, one min-raiser, 300 tables, seed 113: **14.29 points per self
  seat**. [Raw report](reports/dense_300.json).
- Eight self, 200 tables, seed 127: **12.50 points**, as required by symmetry.
  This tests endgames and runtime rather than comparative strength.
  [Raw report](reports/selfplay_200.json).
- One self, four check-or-fold, three min-raiser, 500 tables, seed 131:
  **42.10 points**, 421 first places.
  [Raw report](reports/solo_mixed_500.json).
- At **2.5x CPU cost**, standard mix, 200 tables, seed 401: **23.62 points**,
  147,348 decisions, zero failures; p99/p99.9 556.3/691.2 microseconds.
  [Raw report](reports/slow_default_200.json).
- At **2.5x CPU cost**, one self and seven min-raiser, 100 tables, seed 409:
  **41.70 points**, 6,369 decisions, zero failures; p99/p99.9 643.4/730.0
  microseconds. [Raw report](reports/slow_aggressive_100.json).

The normal matrix has 1,459,624 decisions; the CPU-padded matrix has 153,717.
Maximum observed memory was **2,497 bytes**. Some normal-run wall measurements
exceeded 1 ms, with no timeout: the provided time bank covers occasional overruns.
CPU padding is a timing approximation rather than an actual hardware benchmark;
arbitrary operating-system pauses cannot be guaranteed away.

**Regression and timing checks**

`verify.py 30000` passed 30,000 randomized legal-action cases, including all
streets, calls with no raise available, single-kind offers, all-in opponents,
fresh agent copies, replayed events, truncated memory, low-bank decisions, and
different payouts. It also passed 280 independently enumerated ICM cases,
1,016 seating-order cases, four position/range checks, two side-pot cases, and
two simultaneous-bust cases. Thread CPU p99/p99.9/max was
234.2/276.2/333.7 microseconds; none of these CPU measurements exceeds 1 ms after
multiplication by 2.5. [Verification report](reports/verification.json).

The packaged slowdown CLI also passed a separate two-table smoke test.
The slowdown wrapper pads measured thread CPU time, rather than multiplying
unrelated wall-clock scheduling pauses. It leaves simulator timing enforcement
unchanged. [Smoke report](reports/slow_helper_smoke.json).

**Reproduction**

Run from the workspace root with the supplied Python environment:

```sh
PY=/Users/dylan/Documents/GitHub/pokerbot/.venv/bin/python
$PY lab/field_bots/openai_k_iterate_3/verify.py 30000
$PY lab/field_kit/play.py lab/field_bots/openai_k_iterate_3 --tables 1000 --seed 103
$PY lab/field_bots/openai_k_iterate_3/slow_check.py --tables 200 --seed 401
$PY lab/field_bots/openai_k_iterate_3/slow_check.py --tables 100 --seed 409 --seats self,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser,min_raiser
```

Use the counts/seeds and seat mixes listed above for the other reports.
`prepare_tables.py` regenerates the offline equity asset and is not run by the
agent. Sampling and host scheduling can change exact rerun results.
`reports/summary.json` contains final totals and SHA-256 hashes of the playing
code and equity asset. Earlier iteration reports are also retained.

Only the field-kit README/play command, the provided SDK, this bot's files, and
installed library APIs were inspected. Simulator internals were neither read
nor imported by development code. Strategy remains heuristic: in particular,
opponent ranges and multiway equity are approximations, not a solved equilibrium.
