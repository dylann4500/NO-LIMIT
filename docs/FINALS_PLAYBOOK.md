# Finals playbook (Sunday 2026-11-15, San Francisco)

For Dylan and Samuel. No code may be brought into the event; prepared prompts and knowledge may. Everything
below is knowledge or a prompt. Numbers are from our regional hand histories, the portal's API (read with our
key on 2026-11-11), and the Boston regional (a friend's data and account).

## 1. What went wrong at the regional, and what first place took

| Place | Team | R1 | R2 | R3 | R4 | R5 | R6 | Weighted total |
|---|---|---|---|---|---|---|---|---|
| 1 | 2 Curry | 20.40 | 20.24 | 21.15 | 20.47 | 20.41 | 20.08 | 428.72 |
| 2 | Lemonade | 19.78 | 19.34 | 20.67 | 20.62 | 20.09 | 19.61 | 421.08 |
| 6 | avalon | 18.10 | 16.73 | 19.05 | 18.26 | 17.95 | 17.53 | 376.71 |

**The gap to 1st was 52 weighted points: about 2.5 points per table in every round.** Our known mistakes
explain about half of it:

| Mistake | Cost (weighted points) |
|---|---|
| Over-calling flop and turn bets in R1-R2 (fixed in v6; the data showed it after practice round 1) | 4-7 |
| Over-folding after v6: we folded 73/66/78% to heads-up bets by street, the field 52/45/48% | up to ~16 (≤0.9/table over R3-R6) |
| SDK `icm()` bug: busted stacks scored 0, so we folded profitable 2-3-handed all-in calls in R4-R5 | ~1.4 |
| Folding 82-87% to 3-bets while the field's 3-bet rate doubled (6.9% → 12.3%) | part of R6's -0.43 |
| **Total of known fixes** | **~22-25 → about 400: 3rd place** |

**The other ~27 points was a different bot.** 2 Curry scored 20+ in *every* round, including round 1, so
its first hour decided its result. Its style, measured from our tables:

| | 2 Curry | Lemonade | avalon |
|---|---|---|---|
| VPIP / PFR | 38-43% / 34-41% | 25-28% / 10-16% | 30% / 23% |
| 3-bet | **32-39%**, wide (half its shown 3-bets were outside the top 10%) | 13-22%, mostly jams | 16-17%, premiums only |
| Fold to 3-bet | 81-87% | 22-33% | 85-87% |
| Flop / turn fold to bet | 61-67% / 45% | 68-74% / 30-54% | 32% → 70% / 48% → 65% |

- **Our own release gate would have blocked the winner.** It required PFR 17-27%; 2 Curry ran 34-41%. The
  band was set from the field's median after v4's failure, so it protected us from bad aggression and from
  good aggression alike. v4 failed because it 3-bet blindly and then folded 96% to 4-bets and played badly
  postflop, not because its PFR was high.
- **Ranks barely move after round 1.** Bay Area round-to-round rank correlation was 0.76-0.83; Boston's was a
  median of 0.68. Most teams' placing was set by the bot they had at the end of the build.
- **Big jumps come from rewrites, not tweaks.** Boston: a team stuck around 45th had a subagent write a fresh
  "hail mary" bot after round 3 and gained 18 places in one round (+2 points per table). Our own v4 rewrite
  failed, but it was released without real-field evidence.
- **The Boston winner researched before the start.** Fable ran for ~1.5 hours before the build on past
  competitions (including our Stanford/Bay Area regional) and pokerbot design, then the team kept prompting
  all night. Teams at the Finals will have done the same about all three regionals.

**What it takes to win on Sunday:**
1. A strong first bot within the build hour, starting from research done beforehand.
2. Postflop calibrated to the field from the first practice round: fold to bets near the field's rates, not
   far above or below.
3. Real preflop aggression (wide 3-bets with disciplined folds to 4-bets) judged by the field's response
   (their fold to 3-bet, re-raise rates), never blocked by a fixed VPIP/PFR band.
4. A second, independently written bot from minute 0 (two-track build), chosen by practice-round results.
5. Every library function a decision depends on unit-tested with edge cases (the ICM bug).

## 2. What we know about the Finals format

- 20 teams (5 per regional + 5 wildcards): 3 tables per iteration (8 + 8 + 4 teams + 4 non-scoring fillers).
  Opponents are all strong teams, so the soft spots that paid at the regional are gone.
- A different variant, announced at the start with the kit. Regionals so far: Bay Area = 3 hole cards,
  discard one and expose one on the flop; Boston = the flop is bought at a sealed auction with a separate
  currency. **Pittsburgh runs tomorrow (11-12): get its variant and results.** Each variant added a decision
  phase with a new action kind and new `state.variant` fields.
- **Round weights vary**: Bay Area 1-6 (`round_weighting: linear`), Boston 1, 2, 3, 5, 8, 13. Read the Format
  page; with Boston's weights the last round is 13/32 of the total.
- The platform supports, per competition: a `final_weight` revealed late (`final_revealed_at`), a held
  leaderboard (`leaderboard_held`), per-round culling of teams out of contention (`contender`,
  `culled_at_look` in results) and ICM luck correction (`icm_luck_correction`). None were used at the
  regional. Expect any of them.
- Practice rounds grow during the build (Bay Area: 1,000 → 2,500 → 10,000 → 12,500 iterations), and a
  1,000-iteration practice runs between scored rounds. Scored rounds: 20,000 iterations at Bay Area,
  10,000+ at Boston.
- Uploads auto-activate when they pass the test match (the portal now says so). 30-second cooldown.

## 3. Roles and timeline

| Who | Owns |
|---|---|
| **Dylan** | the coding agent (build, changes, tests), packing, uploads, confirming the active bot |
| **Samuel** | the clock and deadlines; every practice and scored round's hand history; the live dashboard; the one-change recommendation per round |

**Per-round deadlines** (worked at the regional; a missed deadline means the previous bot stays live):
T-15 change locked · T-8 packed · T-6 tested under upload-test conditions (no time bank) · T-3 uploaded and
the active bot confirmed on the team page.

**Build hour:**
- 0-5: read the kit (RULES.md, README.md, AGENTS.md, `state.config`), the Format page (weights!).
- by 10: a minimal legal bot uploaded and confirmed active (track A).
- 0-50: track A grows into the main bot; track B (a subagent) writes an independent bot from scratch.
- every practice round: Samuel's analysis of field response, our leaks and A vs B.
- 50-60: hands off; the better track (by practice results, not local wins) is active.

**Between rounds:** one or two changes with real-field evidence, each behind a flag; or a switch to the other
track if it's clearly better; or a rewrite if we're stuck mid-table after two rounds.

## 4. Prompt pack (paste-ready; fill the <...>)

### P0 · Pre-event research (start ~2 hours before; Fable or Opus)
```
We're competing in the No Limit pokerbot Finals today: 8-player no-limit sit-and-gos, bots as Python agents with a
1 ms decision limit, a poker variant announced at the start, a 60-minute build, then six scored rounds 20 minutes
apart. Before the start, research and write notes to notes/ (no bot code yet):
1. The three regional variants of this competition (Bay Area: 3 hole cards, discard one and expose one on the flop;
   Boston: the flop bought at a sealed auction with flop-chips; Pittsburgh: <what we learn tomorrow>) and how a
   strong bot plays each; what kinds of twist the Finals variant could have and how to adapt quickly.
2. What wins AI-built sit-and-go fields: ICM and push/fold by stack depth, preflop aggression (wide 3-bets with
   disciplined folds to 4-bets), postflop folding calibrated to how often opponents bluff.
3. A fast architecture: a platform layer (memory, legality, fallback), precomputed tables at import, Monte Carlo
   equity under a deadline, per-seat opponent stats with priors.
4. A checklist of traps: library functions with wrong edge cases (e.g. ICM scoring a busted stack 0 when that
   place pays), floats in raise sizes, time banks, memory limits.
Finish with notes/plan.md: the first 10 minutes, the first hour, and what to measure in each practice round.
```

### P1 · The announcement (minute 0; Dylan)
```
The variant is announced. Read the starter kit fully (README.md, RULES.md, AGENTS.md, the SDK, the examples) and the
Format page. Report: the API, the new phase/action kinds and state.variant fields, the round weights and anything
unusual in state.config (payouts, final weight, time bank). Then, using notes/plan.md, get a minimal legal bot that
handles every phase into submission/ within 10 minutes, test it under upload-test conditions (heads-up vs
check_or_fold, 20 hands, no time bank, zero failed decisions) and tell me when it's ready to upload.
```

### P2 · Track B, the independent bot (minute 10; Dylan, as a subagent)
```
Spawn a subagent to write a second bot from scratch in trackB/, without reading our main bot: a strong, aggressive
design for this variant (wide but disciplined 3-bets, equity-based postflop with folds calibrated to the field,
ICM push/fold). Same tests as the main bot. It reports when ready; we'll pick between the two on practice results.
```

### P3 · Practice and round analysis (every round; Samuel)
```
Here is our hand history for <round>: <path>. With a script, report, in this order:
1. Failed or automatic decisions (anything nonzero first).
2. How the field responds to us vs to others: fold to our opens, 3-bets of our opens, fold to our 3-bets, fold to our
   bets by street, how often they call our jams.
3. Our rates vs the field's: VPIP, PFR, 3-bet, fold to 3-bet, fold to bets by street, c-bet, showdown rate, and the
   top 3 teams' rates.
4. Chips won/lost by decision class (open, 3-bet, call, flop/turn/river bet, call, fold), with error bars.
5. The single change with the largest expected gain that's backed by these numbers, and the frequencies it should move.
Use team names from the header; count only non-filler seats for scores.
```

### P4 · The live dashboard (start of the event; Samuel's agent)
```
Using our portal API key (~/.config/no-limit-2026/api-key, Bearer auth, base https://pokerbot.sequoiacap.com/tournament/api),
write a small poller that every 60 seconds reads GET /competitions/<id>/standings and GET /competitions/<id>/tournaments,
prints our rank and the top 5, notices when a round completes (GET /tournaments/<id>/results), and downloads our hand
history for it from <the download URL copied from the browser's Network tab> into data/<round>/, then runs the P3
analysis automatically. Never upload or change anything; read only.
```

### P5 · A change between rounds (Dylan)
```
Change exactly this, behind a flag defaulting to the old behaviour: <rule>, because <evidence from P3>. Expected moves:
<frequencies>. Show me a behaviour diff against the current live bot on identical tables (every preflop and flop
decision rate), the upload-test result with no time bank, and a fuzz test (no illegal action, no exception, p99 and
max latency). Don't block a change for moving PFR or 3-bets if that's the intended move.
```

### P6 · Hail mary (if stuck mid-table after round 2 or 3)
```
We're stuck at <rank>. Have a subagent write a fresh bot from scratch for this variant in rewrite/, informed only by
these field numbers: <P3 summary>. Test it against our live bot and track B on identical tables, then we'll decide on
the next practice round's real-field result.
```

## 5. Rehearsal

`emu/` replays all of this with 19 simulated teams (see `emu/README.md`). Practise the roles above in it, on a
mock variant, before Sunday.
