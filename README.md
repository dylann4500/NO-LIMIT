# avalon: No Limit 2026 pokerbot (Bay Area regional)

This is everything team **avalon** built during the No Limit pokerbot tournament on 2026-11-06. It covers every bot version, the exact zips we uploaded, the release gate, the analysis tools, and the research that drove each change.

**Result: 6th of 148 teams.**
- We went from 31st of 92 in the first practice round to 3rd in scored round 3.
- Every scored round ran with 0 failed decisions.

The bot was built from scratch on the night. The only inputs were the knowledge docs in `rebuild/`; no prepared code was used.

## The game

The variant is `flop_discard_reveal`:
- Each player gets three hole cards. Preflop betting is normal.
- On the flop, each player discards one card face down and exposes one of the two cards it keeps.
- So after the flop, every opponent holds one visible card and one hidden card.

Tables are 8-seat sit-and-gos paying 50/30/20 points. Decisions have a 1 ms limit plus a 100 ms bank, and the upload test runs with **no** bank. Six scored rounds were weighted 1× to 6×.

## Results

| Round | Bot | Points per table | Round rank | Notes |
|---|---|---|---|---|
| Practice 1 | m10 | 14.61 | 31 / 92 | minute-10 bot, rules first |
| Practice 2 | v3 | 18.87 | 8 / 116 | |
| Practice 3 | v3b | 19.02 | 7 / 123 | |
| Practice 4 | v4 | 9.17 | 100 / 125 | **rolled back** within one round (see below) |
| **Scored 1** (×1) | v3b | 18.10 | 13 | |
| **Scored 2** (×2) | v5r | 16.73 | 14 | the field got tougher |
| **Scored 3** (×3) | v6 | **19.05** | **3** | flop/turn fold rules |
| **Scored 4** (×4) | v7 | 18.26 | 6 | ICM bug live (unknown at the time) |
| **Scored 5** (×5) | v9s | 17.95 | 6 | ICM bug still live |
| **Scored 6** (×6) | v10 | | | ICM bug fixed |
| **Final** | | | **6 / 148** | |

## Version history

Every version is in `bots/<name>/`, and every uploaded zip is in `releases/`. Each change sits behind its own flag in the `K` dict at the top of `agent.py`.

| Version | What changed | Evidence / outcome |
|---|---|---|
| m10 | Minute-10 bot: keep the best 2 of 3 on the flop; tight preflop; bet or call with top pair+ | Rules-safe live bot within 10 minutes |
| v2 | 3-card preflop percentile tables; flop selection by equity Monte Carlo; opponent ranges = {visible card + 1 hidden} | |
| v3 | Fold-to-bet prior 0.45 (from real field data); tighter opens; 50/50 reveal | Practice 2: 18.87 |
| v3b | v3 + least-leak reveal | Practice 3: 19.02; scored 1: 18.10 |
| v4 | One value function + softmax over all actions | **Failed:** it 3-bet 58% when facing a raise, card-independently, then folded 96% to 4-bets. It beat our own old bots locally by +4.4 |
| v5 / **v5r** | v3 + no river bluffs into visible strength (v5 also had an ICM call mask, which v5r drops) | River fix confirmed: those bluffs got 10.5% folds and lost 4.3 bb each |
| **v6** | + `visible_pair_rule` + `fold_weak_vs_hu_bet` | Three independent studies agreed. Scored 3: **19.05**. Flop fold-to-bet went from 22% to 59% |
| v7 | + hide top pair (`reveal_random: False`), ICM call mask, BB folds vs non-SB opens | Scored 4: 18.26. The BB folds turned out obsolete after v6 |
| v8 / v8b | + heads-up jam widening, heads-up broadway/Ax opens, wider late steals; v8b turns the BB folds off | Practice 8: 17.82 (steals suspected) |
| v9 / **v9s** | + BB jams vs late opens; v9s turns the steals off | Scored 5: 17.95 |
| **v10** | v9s + **ICM bug fix**: the mask applies only at 4-5 alive | `poker_agent_sdk.icm()` scores a busted stack as 0 points, so heads-up the old mask demanded about 88% equity to call where about 45% is correct |

`BUILDLOG.md` has the build agent's per-version test logs. `STEERING.md` is the full, time-stamped steering log the reviewer wrote during the event: every decision, with its numbers.

## How it was run

Three AI roles worked in parallel; the humans uploaded and relayed research:
- **Build agent** (Claude, this repo): wrote the bots, ran its own tests, and packed `releases/<name>.zip`.
- **Reviewer** (Claude): gated every release (`reviewer/gate.sh`), analyzed each round's hand histories within seconds (`reviewer/`), and steered the build agent through `STEERING.md`. It built the small flag-flip variants v3b, v5r, v8b, v9s and v10.
- **Research:**
  - A Claude competitor-research session (`research/competitors/`): forward-EV studies of our own decisions and of the top teams.
  - Samuel's matched-hand analyses: the BB, heads-up jam and reveal experiments, and the heads-up ICM symptom.
  - Astra (Codex): the variant math handoff and the round-2 review in `research/`.

**Cadence:** a scored round every 20 minutes. Rules locked 15 minutes before each round, the release was packed 8 minutes before, gated 6 minutes before, and uploaded 3 minutes before. A missed deadline meant the previous bot stayed live.

## Findings that held up (real-field, multi-round)

- **Fold more to flop and turn bets.** Calling heads-up with air, middle pair or one pair against a visible pair lost 1.6-6.3 bb per call. Folding these was worth about +2.3 points a round.
- **Never bluff into visible strength.** When the opponent's exposed card plus the board already beats us, they fold only 8-15% of the time.
- **Hide top pair.** Randomized round 2 data: revealing it cost 0.27 ± 0.05 points per hand at the time.
- **Our preflop jams beat folding in every spot and strength band** (112k jams). Value-jamming strong hands earns less than raising them, because the field folds to jams.
- **Heads-up and 3-handed all-in calls beat folding** (+0.3 to +2.3 points per call). That's what exposed the ICM bug.
- **Rules have a shelf life.** BB calls vs CO/BTN opens lost points before v6 and broke even or won after it. Re-check old rules after big changes.

## Lessons

1. **Judge changes on real-field hand data from the first practice round.** The flop-calling leak was live through scored round 2. Fixing it earlier would have been worth about 4-7 weighted points, more than the gap to 5th.
2. **Unit-test every library function a decision depends on,** with edge cases like 2 players, busted stacks and paid places. The ICM bug cost about 2-2.5 weighted points in rounds 4-5.
3. **Local wins against your own old bots mean nothing.** Gate on a behavior diff against the last *proven* bot, plus VPIP/PFR bands from the real field.
4. **1,000-table samples swing by ±2 points.** Practice rounds also run 1.5-2 points high, so compare same-file or scored results only.

## Repo layout

```
bots/<version>/          agent.py (+ tables) for every build, including test variants
releases/<version>.zip   the exact zips uploaded or considered
tests/                   match.py (local matches with rule overrides; --bank 0 = upload-test conditions),
                         fuzz.py, validate.py, stats_check.py, opponents/ (field-proxy bots)
tools/                   table builders (3-card preflop tables, heads-up 2-card equity)
reviewer/                gate.sh, bdiff.sh + behavior.py (behavior diff), analyze_round.sh and the
                         hand-history analyses (hh*.py, x*.py; see the docstring at the top of each)
research/                Astra's handoff + paper, the round-2 review, the competitor-research report + scripts
rebuild/                 the knowledge-only docs the bot was built from
STEERING.md, BUILDLOG.md, TUNING.md
```

## Running it

1. Download the official starter kit from the portal into `starter-kit/` (it isn't redistributed here). Then set it up:
   ```bash
   cd starter-kit && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
   Follow the kit's README for the exact steps.
2. Run a local match under upload-test conditions:
   ```bash
   cd starter-kit && .venv/bin/python ../tests/match.py --tables 20 --bank 0 --hand-cap 20 ../bots/v10 examples/check_or_fold
   ```
3. Gate a release:
   ```bash
   reviewer/gate.sh releases/v10.zip
   ```
   Set `GATE_BOX=<ssh host>` to also run the no-bank test on the build box.
4. Analyze a round's hand history:
   ```bash
   reviewer/analyze_round.sh ~/Downloads/hands-<id>.jsonl.gz
   ```
   Hand histories aren't committed: they're large and contain other teams' play.
