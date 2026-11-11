# default_c

`claude_default_c_r3`'s strategy (`lab/field_bots/claude_default_c_r3`, see its `NOTES.md`), variant-ready. `agent.py` (platform shim, optional `params.json`, import-time warm-up, GC settings as in `lab/v2/agent.py`) wraps `core/agent.py`, the strategy. Upload this folder.

## Variant at kickoff

Same procedure as `lab/v2/README.md`. Everything variant-dependent goes through `core/engine.py` (a copy of v2's, plus `class_members`, `sample_member`, `entry`, `value` and `equity_exact`) and `core/discard.py` (v2's, unchanged).

1. Set `VARIANT = "holdem"` near the top of `core/engine.py`. Check with `POKER_VARIANT` unset:
   ```bash
   cd lab && env -u POKER_VARIANT ../.venv/bin/python -c "import importlib.util as u; s = u.spec_from_file_location('e', 'portfolio/default_c/core/engine.py'); m = u.module_from_spec(s); s.loader.exec_module(m); print(m.VARIANT, m.ENGINE, m.N_HOLE, m.TABLE is not None)"
   ```
2. For hold'em, run `cd lab && ../.venv/bin/python default_c_parity.py 60`. It must show 0 action and 0 memory differences.
3. A new variant needs its RULES branch in `core/engine.py` (as for v2), then a table: `../.venv/bin/python portfolio/default_c/core/build_tables.py <variant> --procs 6 --scale 1`. Don't rebuild `holdem`: `tables_holdem.json` is the bot's original `tables.json`, values unchanged (`--legacy field_bots/claude_default_c_r3/tables.json` recreates it).

Tables shipped (6 processes, loaded Mac): flushfh and shortdeck at scale 1 (5 s, 3 s), hole3 at scale 3 (34 s), hole3discard at scale 2 (36 s), omaha at scale 4 (171 s).

## What differs from the original outside hold'em

- **Tables:** same fields (`eq1`, `eq3`, `shove_order`, `open_order`, `grid`, `eq_top`) computed under the variant's showdown. "Top p" is whole classes (the original split the last hold'em class).
- **Class-name checks:** pair (set-mining), speculative (limp-behind) and premium (3-bet for value) are per-class flags. For 3+ hole cards: a pair among the hole cards; a pair, or two suited cards with an ace or a rank gap of 2 or less; the top 3.8% by shove order (the hold'em premium set's share).
- **Postflop sampling:** hand spaces over 5000 hands use 60 sampled hands per chunk of the open order. The stdlib engine scores at most `engine.CAND_MAX` villain hands per villain (half that in discard variants), and its Monte Carlo stops at `MC_DEADLINE_S` (0.30 ms after `act()` starts), shared among the villains. A villain that would overrun gets the average equity of those already computed, as the original's own time guard does.
- `config.variant` is no longer read; the variant is `engine.VARIANT`.
