# Event-night runbook (v2)

The plan for Fri Nov 6, from kickoff to the last round. It replaces `BUILD_PROMPT.md` Part C wherever they disagree, because the bot changed: the submission is now **v2** (`lab/v2/`), with our tuned rule-based policy as Plan B. The rest of `BUILD_PROMPT.md` (known traps, the failure table in Part E) still applies.

## What we're submitting and why

| | v2 (Plan A) | Field-tuned policy (Plan B) |
|---|---|---|
| What | The strongest AI-built strategy (claude_default_b with its round-2 improvements, merged into a variant engine) behind `lab/shim.py` | Our original rule-based policy, retuned against the generated field (`lab/tuned_gen1.json`) behind `lab/adapter.py` |
| Mock rounds vs the generated field | 1st of 54 in the library league (17.9; every bot version we built); 1st of 27 vs the round-3 field (17.5). Fair share 12.5 | 15.5 (4th of 22) in round 1 |
| Variants | holdem, shortdeck, flushfh, hole3, omaha via `lab/v2/core/engine.py` | The same five via `lab/pk.py` |
| Speed on the build box | hold'em p99 220 us, max 291 us; omaha p99 388 us, max 466 us; 0 of 220k decisions over 1 ms | p99 147 us, none over 1 ms |
| Platform conventions | The shim detects them at runtime: flat across all 18 combinations | The adapter detects them: 100% decision parity in all 16 |

Our original untuned bot came **last** in every mock round (4-7 points). Don't fall back to `tuned_final.json` or `tuned_real1.json`.

## Before 5 PM

- [ ] Everyone: pull `prep/adapter-field-cluster`, set up `.venv`, and run `lab/test_engine.py` and the commands below once.
- [ ] Everyone: SSH key on the portal. Dylan's is done; Samuel's is pending.
- [ ] **Get an answer on whether prepared code is allowed** (rule 3.4). If it isn't, use `docs/CODEX_PROMPTS.md`, and use what we learned (section "What the field taught us") as prompts.
- [ ] Bring chargers. Plug both laptops in.

## Default: submit v2 first

Jason's 8000-iteration cluster leagues (±0.23) show v2 is the most robust library bot. It was top 3 in all six conditions:

| Field | fast | mid | slow |
|---|---|---|---|
| Latest field (20) | **1st** 15.75 | 3rd 15.68 (`exploit_r3` 16.6) | 2nd 15.73 (tied 1st) |
| All 56 versions | 2nd 16.57 | 2nd 16.92 | 3rd 16.34 |

Ship v2 for T1. Switch to `portfolio/exploit` only if the real blinds look like "mid" **and** the kickoff league on `--schedule event` agrees.

## Picking the bot for the announced variant

The library is v2 plus every variant-ready entry in `lab/portfolio/` (ports of the strongest generated strategies), and Plan B. Once the variant is known:

```bash
cd lab && ../.venv/bin/python pick.py <variant> --tables 600 --procs 10
```

- **What it does:** every candidate plays the same seeded tables in that variant against the lab's variant-aware bots, then it ranks them and prints `pick: ...`. About 3-5 minutes.
- **The opponents are weaker than the real field,** so treat the ranking as a guide. If we regenerate opponent bots in the variant, pass them with `--extra` (they become candidates too) and also run a `league.py` round with the top 2-3 candidates as entrants.
- **Hold'em:** prefer the league against the generated field. Put the kit's blinds in `lab/event_config.json` first, then run:
  ```bash
  cd lab && ../.venv/bin/python league.py --iters 3000 --procs 10 --hh-iters 0 --ours "" --schedule event --entrants $(ls -d field_bots/claude_*_r3 field_bots/openai_*_r2) v2 portfolio/exploit portfolio/default_c
  ```
- **The winner depends on the blind schedule.** In 3000-iteration leagues against the latest field:

  | Bot | mid (faster) | slow |
  |---|---|---|
  | `exploit` | **16.7, 1st** | 14.4, 8th |
  | v2 | 14.7, 7th | **15.2, 3rd** |
  | `default_c` | 15.4, 5th | 14.9, 5th |

  Decide on the real schedule, not on these.

## Kickoff, minute 0-15: a safe bot live

1. **Get the kit.** Run `/no-limit-2026-setup` again (it fetches the kit to the box), and download it locally too. Read `RULES.md`, `README.md` and `AGENTS.md`.
2. **Answer from the kit** (one person, 5 minutes):
   - **Variant:** is it one of holdem / shortdeck / flushfh / hole3 / omaha? If not, what's the rule change?
   - **Conventions:** does `Seat.stack` include the street bet? Does `state.pot` include this street's bets? Is our own action echoed in our next turn's events? Are event kinds strings or enums? The shim and adapter detect these at runtime, but write the answers into the `KIT:` constants in `lab/adapter.py` anyway.
   - **Schedule:** blind schedule and payouts. Put them in `lab/event_config.json` (`"blinds": [[10,20], ...]`).
3. **Submit a safe bot by minute 15:**
   - **Hold'em or a supported variant:** v2.
     1. Set the `VARIANT` constant in `lab/v2/core/engine.py` (see `lab/v2/README.md`). **Check it with `POKER_VARIANT` unset**, because a wrong variant misplays silently.
     2. For hold'em, run `cd lab && ../.venv/bin/python v2_parity.py 30`, which must show 0 action differences.
     3. Zip `lab/v2/` with `agent.py` at the root: `poker-agent pack lab/v2 v2.zip`.
   - **Unsupported variant:** Plan B. Add the variant to `lab/pk.py` and `lab/make_bot.py`, as described in `BUILD_PROMPT.md` Part D. Then run `./make_submission.sh lab/tuned_gen1.json lookup '<points>'` and upload `submission/upload/agent.py`.
   - **Before uploading either:** run `poker-agent check` and `poker-agent play <bot> examples/check_or_fold examples/min_raiser` (8 seats, 100+ tables). The run needs 0 failed decisions. After uploading, **confirm "Active bot" on the team page.**

## Minute 15-55: verify, then improve

- **Real-kit parity:**
  - Run `lab/test_adapter.py` with the real SDK on the path. It should still show 100% parity.
  - Run v2 through `poker-agent play` with 8 seats, and compare its score against the `check_or_fold` and `min_raiser` examples with our local `field_kit/play.py` numbers.
- **Build-box latency:** run v2 there (`ssh no-limit-2026-build`) and check p99 and max.
- **If Claude is allowed, regenerate the field in the real variant:**
  1. Point `lab/field_kit/README.md` at the real rules.
  2. Rerun the team agents, or `tools/gen_codex_bots.sh`, with the kit's SDK.
  3. About 40 minutes later we'll have a realistic field for tuning before T2-T3.
- **Tune v2's parameters** against the generated field (see `lab/v2/README.md`).
  - Promote only if the bots it never saw (`gen_hold`) agree.
  - Then submit at least 3 minutes before T1.

## Between rounds (T1 at 7:00, then every 20 minutes; T4-T6 are 71% of the score)

Results arrive in the next window, so round k's data shapes the bot for round k+2. **One person owns submissions.**

1. **Check for failures first.** On the team page: failed decisions, restarts, tracebacks. Any nonzero count gets fixed before anything else.
2. **Download our hand histories** (the smaller subset). Edit `read_hands()` in `lab/hhprofile.py` to the kit's format, once.
3. **Profile the field and diagnose ourselves:**
   ```bash
   cd lab
   ../.venv/bin/python hhprofile.py ROUND_HH --stream --viewer <our team> --diagnose <our team>
   ../.venv/bin/python hhprofile.py ROUND_HH --stream --rebuild lib.json --exclude <our team> --min-hands 300 --soft 0.5 --field-out mix.json
   ```
   The library is `lab/profile_lib.json`: profiles of all 54 bot versions we built, from 350 tables each. Pass it as `--rebuild profile_lib.json`.
4. **Retune** v2's parameters against the rebuilt field:
   ```bash
   ../.venv/bin/python tune_event.py --cls portal --dir v2 --base live --out v2_tk.json --tables 20000 --fields seen,gen_mix --worst 0.3 --verdict-fields gen_hold --procs 10
   ```
   Load the rebuilt field first as `FIELDS["seen"]` from `mix.json`. Keep the change only if it beats the current bot on the held-out generated bots too.
   - Before the event, two tunes against the generated field did not beat v2's defaults. So expect small or no gains here; the field-specific strategy fixes in step 5 matter more.
   - In the mock tournament, a bot that stood still dropped from 1st to 5th by round 2.
5. **Optional:** a Claude agent reads our histories and proposes one targeted strategy change, as the generated teams did. Gate it the same way.
6. **Submit:**
   - At least 3 minutes before the freeze, then confirm the active bot.
   - **T6:** ship only a clear gate win; otherwise keep T5's bot.
   - Never be without an active bot.

## What the field taught us (mock rounds 1-3)

- **Generation 1:** AI-built bots over-folded and used fixed thresholds. Our tight bot got run over.
- **Generations 2-3:** independent teams found the same things in their histories:
  - The field folds about 50-70% to postflop bets.
  - Big turn and river bets and raises are almost always strong (63-100% two pair or better), so calling them down with one pair is the biggest leak.
  - Shove and re-jam ranges are much wider than the textbooks say (about 40-60% of hands at 20 big blinds or less).
  - Heads-up, players raise first-in about 70% of the time.
- **OpenAI-written bots** trailed the Claude-written ones in every round (8-12.5 points against 13-18).
- **Every v2 version finished top 4 of 27 against the generation-3 field.** Differences between core generations are within about 0.5 points.
