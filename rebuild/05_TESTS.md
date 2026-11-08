# 05 · Tests (run before every upload)

Use the kit's tools: `poker-agent check agent.py`, `poker-agent play <bot> examples/check_or_fold examples/min_raiser ...`, and `poker-agent pack DIR OUT.zip`. Repeat folders in `play` to fill 8 seats.

## Must pass
1. **`poker-agent check` and `pack`** pass. Pack a folder holding only the bot.
2. **Legality fuzz:** call `act` on 100k+ random and hostile states: random stacks, bets, pots, 2-8 players, empty or garbage memory, missing fields.
   - Every return must be an offered kind, with an int raise inside [min, max].
   - `act` never raises.
   - Memory stays under 16 KB.
3. **Upload-test conditions:** heads-up against check-or-fold for 20 hands with **no bank**, run several seeds. Zero failed decisions.
4. **Full tables:** `poker-agent play` with 8 seats (your bot ×4, check_or_fold ×2, min_raiser ×2), 200+ tables. Zero failed decisions; score well above check_or_fold. Our design scored about 20-22 per seat in that mix.
5. **Conventions:** feed `act` the same game state under each convention, through a tiny wrapper that rewrites the state:
   - stack with and without the bet;
   - pot with and without this street's bets;
   - own actions echoed or not;
   - string or enum kinds;
   - seat ids 0..n-1, shuffled, or 1-based.

   The strategy's decisions should be **identical** across them. A difference means the platform layer is wrong.
6. **Failure semantics:** occasionally drop the returned memory and re-send the same events (simulating a timeout). Opponent stats must not double-count.
7. **Latency on the team build box,** not the laptop (`ssh` into it; kit commands work there). Measure `act` with `time.perf_counter_ns()` over realistic states, memory included:
   - p99 well under 1 ms;
   - max under 1 ms after the GC-threshold fix;
   - import within the startup allowance (ours: 15-90 ms).
8. **Variant:** check the variant constant matches `RULES.md`, by running with any override unset. A wrong variant misplays silently.

## Measuring strength
- **Noise:** points per table have SE ≈ 0.7 at 1,000 tables and ≈ 0.25 at 8,000.
- **Paired comparisons:** compare versions in the **same** run (both as seats, same seeds), never against an old number.
- **Opponents:** test against the strongest opponents you have, not just check_or_fold and min_raiser. Weak opponents reward exploiting them and reorder rankings.
