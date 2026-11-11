# v2

`agent.py` (platform shim, optional `params.json`) wraps `core/agent.py`, the strategy. Upload this folder.

## Variant at kickoff

Everything that depends on the variant is in `core/engine.py`: card parsing, hand classes, evaluation and equity. `core/agent.py` only calls it. Hold'em runs on eval7 through the same code paths as before (decision-identical to the untouched core over 310k decisions with seeded RNGs). Every other variant runs on a stdlib evaluator in the same file, vendored from `lab/pk.py`, which is not in the upload.

Ready now, with tables built: `holdem`, `flushfh` (flush beats full house), `shortdeck` (36 cards, flush beats full house, A-6-7-8-9 straight), `hole3` (three hole cards, best five of eight), `omaha` (four hole cards, exactly two plus three).

**1. Set the variant.** Edit `VARIANT = "holdem"` near the top of `core/engine.py`. That constant is what ships. `POKER_VARIANT` overrides it when set, which is how the lab runs variants, so check with it unset:

```bash
cd lab && env -u POKER_VARIANT ../.venv/bin/python -c "import importlib.util as u; s = u.spec_from_file_location('e', 'v2/core/engine.py'); m = u.module_from_spec(s); s.loader.exec_module(m); print(m.VARIANT, m.ENGINE, m.N_HOLE, m.TABLE is not None)"
```

**2. A variant not listed above.** Add a branch to the RULES section of `core/engine.py` that sets `N_HOLE`, `DECK` and `showdown(hole, board)`. Cards are ints, `rank * 4 + suit` with 2 = 0 .. A = 12 and suits `shdc`; `showdown` takes two lists of them and returns a number where higher wins. Nothing else in the bot changes. To test it in the lab, the same rules also go in `lab/pk.py` (then `POKER_VARIANT=<v> python build_tables.py` in `lab/` for the lab bots' table), because the lab engine and lab bots play by `pk`.

**3. Rebuild the table** (from `lab/`, 8 processes):

```bash
../.venv/bin/python v2/core/build_tables.py <variant>              # writes v2/core/tables_<variant>.json
```

At the default `--scale 1` on this Mac with 8 idle cores: shortdeck 2 s, flushfh 4 s, hole3 5 s, omaha 18 s. Under heavy load that became 8, 21, 26 and 107 s. `--scale` multiplies the samples and the time; noise falls as 1/sqrt(scale). Two-card tables are already tight at scale 1, about 0.005 in equity between independent builds. Omaha hands are close in equity, so at scale 1 a hand's percentile moves by about 0.15 between builds; build bigger when there is time. The shipped tables are hole3 at `--scale 4` (19 s) and omaha at `--scale 12` (208 s, about 0.03 percentile noise), so don't rebuild those at kickoff unless the rules differ from `pk`'s. Don't rebuild `holdem`: `tables_holdem.json` is the eval7 table hold'em was tuned on (`--legacy field_bots/claude_default_b/tables.json` recreates it).

**4. Verify** (from `lab/`, with the variant in the environment so the lab plays it too):

```bash
POKER_VARIANT=<v> ../.venv/bin/python v2_varcheck.py v2 --field typical --tables 400
POKER_VARIANT=<v> ../.venv/bin/python v2_varcheck.py v2 --field strong --tables 400
POKER_VARIANT=<v> ../.venv/bin/python conv_check.py v2 --lab-field typical --tables 150
```

A pass is points well above the fair 12.5, `swallowed 0 raised 0 illegal 0`, and CPU p99 under about 0.45 ms. `v2_varcheck.py` counts the exceptions the core swallows (its `act()` turns them into check or fold, so `conv_check` reports 0 either way). Use CPU time to judge speed: wall time on a loaded Mac is mostly scheduling.

**Speed knobs.** Non-hold'em Monte Carlo stops `MC_DEADLINE_S` (0.34 ms) after `act()` starts (`core/agent.py`). On the river it counts exactly instead. `CAND_MAX` and `PER_RUN` in `core/engine.py` cap the villain hands scored per decision and set how many share one runout. Hold'em ignores all three and runs eval7 as before.

**Caveats.** Strategy constants such as `OPEN_W`, `POSF` and `shove_width` are fractions of all starting hands, tuned for hold'em. For 3 or 4 hole cards the implied-odds bonus (`PS`, a pair or two suited cards) applies to most hands. Non-hold'em postflop equity is noisier than eval7's: the standard deviation of one flop estimate is about 0.03 for two or three hole cards and about 0.07 for Omaha, against eval7's 0.015; the river is exact.

## Discard or another extra phase at kickoff

Ready now: `hole3discard`, the MIT 2026 rules as `lab/variants/DISCARD.md` describes them (3 hole cards, a 2-card flop, each player in the hand discards one card face up onto the board in postflop order, then betting, turn and river; showdown is the 2 kept cards plus the board). Tables are built: `core/tables_hole3discard.json` here and `lab/table_hole3discard.json` for the lab.

**Where the code is.** All kit-facing discard code is in `core/discard.py`: the `KIT:` constants at its top, `discard_action(state, Action, deadline)` (finds the discard-like legal action and builds the reply) and `discard_choice` (the strategy). `core/agent.py` calls it in `act()`, in the block marked `DISCARD-VARIANT`, before any betting logic: a discard turn returns there, and in a discard variant a betting turn sets `E.TO_COME` (board cards still to come, because discards make `len(board)` vary). The rules are in `core/engine.py` under `RULES` (`hole3discard`: `N_HOLE = 3`, `DISCARD = True`; a 3-card hand counts as its best two). Plan B gets the same file: `make_bot.py` inlines `core/discard.py` into the generated bot, and `lab/adapter.py` calls `discard_action` at its `KIT: variant phases` line.

**What to map from the real kit** (`RULES.md`, `sdk/`, one sample state), all in `core/discard.py` unless noted:

| Kit fact | Where | Lab guess |
|---|---|---|
| The discard action kind's name | `DISCARD_KINDS` | `"discard"` (also matched: any non-betting phase named `*discard*` with one non-betting kind) |
| How a card is chosen: index or card | `DISCARD_INDEX` | `True`: `Action(kind, i)` drops `state.cards[i]`, legal range `min_amount..max_amount`. `False` sends the card string. If the kit uses something else (`Action.discard("Ks")`, a `cards=` field), edit the two `return Action(...)` lines at the end of `discard_action` |
| Do discards go on the board for everyone? | `DISCARD_TO_BOARD` | `True` (MIT). `False`: revealed but dead |
| Board cards dealt in a hand, discards excluded | `DISCARD_DEALT` | `4` (2-card flop, turn, river). Pineapple-style 3-card flop: `5` |
| How discards appear in `state.history` | `discard_to_come` | Events of a kind in `DISCARD_KINDS` with `cards=[card]`. With no such events, betting turns overestimate the cards to come, which isn't fatal |
| Phase name | nothing to set | Detection keys on the legal kind first, so `state.phase` only needs to be non-`"betting"` |
| Hole cards, flop size, showdown | `core/engine.py` RULES, `lab/pk.py` | 3 cards, `FLOP_N = 2`, 2 kept + board. Change both files together, then rebuild tables |

**Steps:**
1. Set `VARIANT = "hole3discard"` in `core/engine.py` (or the new variant name, after adding its RULES branch).
2. Map the constants above.
3. If the rules differ from `hole3discard`, edit `lab/pk.py` (`DISCARD`, `FLOP_N`, `showdown`) and the RULES branch, then `../.venv/bin/python v2/core/build_tables.py <variant> --procs 6 --scale 2` (18 s) and `POKER_VARIANT=<variant> ../.venv/bin/python -c "import pk; pk.build_table(procs=6)"` (4 s).
4. Verify with `POKER_VARIANT=<variant>` and `v2_varcheck.py` (it reports a `disc` latency row), then `field_kit/play.py v2`.

**Measured** (this Mac under load from other jobs, lab fields; CPU time per decision):
- **Points:** v2 scored 26.7 ± 0.7 against `typical` (1000 tables) and 24.7 ± 0.9 against `strong` (600 tables), with 0 exceptions, 0 illegal actions and 0 platform failures. One `strong` run with 6 processes at load average 13 had 95 wall-clock timeouts and 0 CPU overruns.
- **Discard speed:** in play, p50 323 µs, p99 353 µs, p99.9 368 µs and max 563 µs. Standalone `discard_choice` over 5000 calls: p50 317 µs, p99 339 µs, max 435 µs. Its rank cache is capped at 40k entries, because dict resizes beyond that each stalled for 1-4 ms.
- **Showdown equity:** on 30,000 shared heads-up deals, all in after the flop, `discard_choice` won 2.0 ± 0.17 points more than "drop the lowest card" and 3.1 ± 0.19 more than the lab default "keep the best preflop pair".
- **Game level:** four v2 copies using `discard_choice` against four that drop their lowest card scored +0.71 ± 0.38 points per seat over 1200 tables (each deal played with the seats swapped).
