# Scenario audit: the night before → end of the build hour (until scored round 1 starts)

**Code audited:** `hub/hub.py`, `hub/bus.py` and `hub/roster.py` at HEAD **a3757f8**. Line numbers refer to HEAD (copy at `audit/head/hub.py`).
**Note:** while this audit ran, the working tree gained uncommitted schedule changes in `hub/hub.py`: `build`/`gap` fields, `round_starts()`, `pin_round()`, `set_schedule(event='format')`, and practice stage labels that count scored rounds. Each finding says whether that working-tree (WT) version still has the problem. I re-ran every probe against both HEAD and WT.

**Probes** (scratch, all in `.../scratchpad/audit/`). Each runs with `uv run --no-project --with aiohttp==3.14.5 --with claude-agent-sdk==0.2.181 --with modal==1.6.4 python <probe> [hubdir]`:
- `rx.py`: START_RX, AT_RX and PREFLIGHT_RX on realistic messages.
- `clock_probe_{head,wt}.py`: false start then correction, practice-1 time, 45-minute build, start on both laptops.
- `sync_probe_{head,wt}.py`: a clock correction that arrives by sync; a double start.
- `late_probe.py <hubdir>`: late announcement (4, 7, 12 min); schedule that arrives 6 minutes late over the link.
- `pm_probe.py <hubdir>`: "announced at 2:05", "go", "begins at 2pm".

Verdicts: OK · BUG (wrong behaviour, proven or plainly visible in code) · GAP (a case nobody handles) · INEFF (wastes time or usage) · RISK (depends on unknowns about the portal or format).

## Scenario table

| # | When | Scenario | Ideal | What the code does (HEAD) | Verdict |
|---|---|---|---|---|---|
| 1 | Sat | Saturday check run with the **Sunday** `--data ~/.avalon-hub-live/<p> --namespace=-live --portal-data ~/portal-data-live` (SUNDAY.md step 5 says so) | The Saturday check leaves nothing behind for Sunday | Shared state persists locally (bus.py:80-88 `shared.json`) and in the Modal `-live` Dicts. Portal state persists too (`portal_state.json`: `done`, `done_stages`, `landed_at`). So do the agent sessions: on Sunday the Chats resume Saturday's session (main 4197-4205, KICKOFF skipped) | BUG (see #2-#4) |
| 2 | Sat | On Saturday the key lists only the Bay Area team (no Finals competition yet) | The watcher learns nothing it keeps for Sunday | `identify` takes the newest competition (3439-3462). The first poll's catch-up handles every Bay Area round as `landed(quiet=True)`. That writes "Round k · finished" and "data · done" tiles (3572-3593, before the quiet return), downloads every round's hand file over the hotspot, and adds `done_stages` = Practice 1-4 and Round 1-6 | BUG |
| 3 | Sun | Stale `done_stages` from #2 | Fast polling (every 6 s) near each Finals round end | `finishing()` skips any stage in `done_stages` (3401). So for "Practice 1" … "Round 6" the watcher never switches to 6-s polling all day: results arrive up to 24 s later, inside a 5-minute decision window | BUG |
| 4 | Sat→Sun | Someone tries "Start building" (or a message trips START_RX, #9) on Saturday on `-live` | Sunday starts with no clock; Saturday's clock can be reset | A clock can't be cleared. On Sunday the Start button and the hero (with "Check everything works") are hidden because a schedule exists (ui 466). `start_event` refuses (3990). The fix needs a time, and the correction then carries over every step Saturday already sent (#11), so Sunday's minute-0 tasks never fire. The pre-flight Clock row is ✅ whatever the date (1163) | BUG |
| 5 | Sat | Portal key file missing or path typo | A clear ❌ | `PortalWatcher.__init__` reads the file (3363) inside `main()`: the hub crashes, and `start.sh` restarts it every 3 s forever. The UI never loads. It shows up in the Saturday check | RISK (visible) |
| 6 | Sat/Sun | Old key (lists Bay Area only, not the Finals) | ❌: the competition isn't the Finals | `identify` silently takes the newest competition the key lists, here Bay Area. The pre-flight shows ✅ "competition <Bay Area name>" (1127-1129). On Sunday nothing ever lands, and no alert fires (#7) | BUG |
| 7 | Sun 20-25 | No round seen on the portal although practice 1 should have started | Alert "no round seen on the portal; check the key or competition" | `check_clock` only looks at rounds that exist (3542-3568), and `check_team` alerts only on a missing *active bot*. Nothing notices a silent portal | GAP |
| 8 | Sat/Sun | Samuel's hub started **without** `--portal-base/--portal-key-file` | Pre-flight ❌ "no portal watcher on Samuel's laptop" | `else: row(True, "Portal", "watched from Samuel's laptop")` (1140-1141) runs on Samuel's laptop too, so it shows ✅ | BUG |
| 9 | Sun morning | Pre-event chat: "when does the competition start?", "is the variant announced yet?", "the event is on Sunday right?", "go" (answering the Chat), "the competition starts in 10 minutes", "tournament begins at 2pm" | Only a clear "it has started" starts the clock; questions never do | Every one of these starts the clock **now** (rx.py, pm_probe.py): START_RX (217-219) matches questions, a bare "go", and "in 10 minutes"; AT_RX needs HH:MM | BUG |
| 10 | 0 | "the variant was announced at 2:05" (12-hour habit) | 14:05 | `set_start` reads 24-hour time, so minute 0 is 02:05 (pm_probe). Every step is in the past, so nothing fires and the clock says "Event finished". The reply does show 02:05 | BUG |
| 11 | 0 | Correcting a false or early start (#4, #9, or "the competition starts now" said at the opening talk) | Each step fires at its corrected time | `set_start` copies **every** step already sent to the new start's keys (2955-2960), so b0 … b50 that fired under the false start never fire again. clock_probe #2 (HEAD and WT): `b0` is marked sent and s-data gets no tasks at real minute 0, and the build tiles aren't created | BUG (critical) |
| 12 | 0 | "the competition starts now" said a second time | Ignored, with a friendly reply | Once a schedule exists, chat_command passes the message to the Chat. `set_schedule` refuses without a digit (2230-2234), so the Chat explains | OK |
| 13 | 0 | Samuel and Dylan both say "starts now" within seconds | One minute 0, one minute-0 dispatch | Each hub sets its own `t0`, and sync adopts the newer one (bus.py:407) without carrying sent steps over. The laptop that adopts it re-fires b0: d-platform gets its minute-0 task twice (sync_probe: 1→2, HEAD and WT) | BUG |
| 14 | 0-60 | A clock correction made on one laptop reaches the other by sync | No duplicate steps | The receiving laptop never runs `set_start`'s carry-over, so any step whose new time is less than 5 minutes old re-fires. sync_probe: Dylan's d-platform got "minute 30" again | BUG |
| 15 | 0+ | Samuel is late: "the variant was announced at 14:02" typed at 14:09 | Every missed step still fires (marked late), minute 0 most of all | Grace is at most 300 s (3102-3104), so b0 (all the minute-0 worker tasks and the build tiles) **never fires** when you're more than 5 minutes late (late_probe: 7 min → nothing; 12 min → only b10, "v1 must be released now", with no minute-0 brief) | BUG (critical) |
| 16 | 0 | Modal link down at minute 0 (hotspot) | Dylan's side starts anyway | Only Samuel's hub has the schedule. Dylan's workers get nothing. When the link returns more than 5 minutes later, b0 is past grace and never fires on Dylan's side (late_probe "synced 6 min late": nothing). If Dylan also types "starts now", you get #13 | BUG |
| 17 | any | Laptop sleeps (lid closed; `caffeinate` doesn't stop lid-close sleep) or the hub restarts for more than 5 minutes | Missed steps fire late | Same 5-minute grace: lost. The LATE text claims "while the hub was restarting" (3109) | GAP |
| 18 | any | A step fires late | Worker sees which step it is | The header becomes `[clock: (LATE]` because the code splits the text on the first ':' (3124; late_probe output) | BUG (cosmetic) |
| 19 | 0 | Dylan's hub still on old code (didn't pull) | Pre-flight or startup ❌ "hubs on different code" | No version handshake: the directory has no git sha. With the WT changes this matters more: old code ignores `build`, `gap` and `round_at`, so the two clocks drift apart | GAP |
| 20 | 0 | Hubs started in either order | Works | Directory and shared sync handle it; startup waits up to 12 s for sync (main 4135-4138) | OK |
| 21 | Sat/0 | Pre-flight: Claude, Codex, repo, disk | ✅/❌ for each | Covered (1150-1162). Missing: `git push` access to the team repo (Samuel's s-tester needs Dylan's pushes), Python deps for the round card (#33), the laptops' clock offset, an API-key fallback | GAP |
| 22 | Sat | Pre-flight hand-history download | Proves the URL the day before | ✅ "no finished round to try yet" when the newest competition has none (1136-1137). It never tries a finished Bay Area round, which would prove or disprove the guessed URL and make SUNDAY step 7 unnecessary | GAP |
| 23 | 0-5 | Kit fetch fails | Dylan downloads it from the portal; agents wait for it | Human procedure (SUNDAY §3). The hub doesn't know about the kit: b0 tells d-platform to work "from the kit", which may not be there yet | OK (RISK) |
| 24 | 0-10 | Kit lands in `starter-kit/` | Every agent that needs it is told the path | Only via the human telling the Chat, then d-overview relaying it. s-data (parsers), s-tester (rig) and s-scout aren't told by the hub | GAP |
| 25 | 0-5 | Format page: build is **45 min** | Clock set to round 1 at minute 45; build steps re-timed | HEAD: "scored round 1 at X" moves minute 0 15 min earlier. `b10`/`b15` are marked sent and never fire, and practices land at real minutes 5/15/25/35 (clock_probe #4). WT: round 1 is pinned and b10/b15 fire, but practices still count back from round 1 (5/15/25/35), and the number of practices is fixed at 4 | BUG (HEAD) / GAP (WT) |
| 26 | 0-5 | Build is **90 min** | Same | HEAD: minute 0 moves 30 min later, so the v1 deadline (b10) fires at real minute 40. WT: round 1 pinned at +90, practices at 50/60/70/80; a 90-min build likely has more or other practices | BUG (HEAD) / GAP (WT) |
| 27 | 0-5 | "practice 1 is at 14:25" (minute 0 at 14:02) — SUNDAY.md step 2's own example | Only practice 1 moves | HEAD and WT: minute 0 moves to 14:05, so scored round 1 moves 3 min later too (clock_probe #3: +65) | BUG |
| 28 | 0-60 | Fewer practices in the build (2 or 3) | Labels and timing follow the portal | HEAD: the portal's 3rd practice (really Round 1.5) is labelled "Practice 3" (171-175). `check_clock` compares it with minute 40, and a 30-min "drift" alert tells the humans to move minute 0 by 30 min. Following it wrecks every scored window. DISPATCH b30/b40 still order "Style B/C for practice 2/3". WT: labels fixed (counts scored rounds first) | BUG (HEAD) / partly fixed (WT) |
| 29 | 0-60 | More than 4 build practices | Each gets a tile, fast polling and a pre-practice step | `events()` knows only practices 1-4 (2936-2937). Practice 5+ in the build gets no `check_team` T-2 check, no fast polling and no drift check | GAP |
| 30 | 20-60 | Practices start 2-3 min off (regional: 7-10 min before rounds) | No false alarm; never suggest moving minute 0 because of one practice | A drift over 180 s on any practice raises "the clock looks off … minute 0 was X; tell your Chat" (3558-3566). Moving minute 0 also moves scored round 1 | RISK |
| 31 | 0-5 | The Format page says 5 or 8 scored rounds | Chat sets the count | `set_schedule(scored_rounds=…)` works, but HEAD needs `at` too, so the Chat has to restate minute 0. WT adds `event='format'` | INEFF (HEAD) / OK (WT) |
| 32 | 0-5 | Rounds every 30 min | Settable | HEAD: impossible (20 is hard-coded in 2940, 3085, 3248 and stage_of). WT: `gap_minutes` | GAP (HEAD) / OK (WT) |
| 33 | ~22-25 | Practice 1 data lands; roundcard.py exists but imports numpy | The hub's run of the card succeeds in < 60 s | The hub runs `repo/.venv/bin/python` or else **system `python3 -I`** (3689-3692). On Samuel's laptop `python3 -c "import numpy"` fails. No prompt or doc tells s-data or s-scout to create `.venv` or stick to the standard library, so the hub run fails and s-data is told "FAILED, run it yourself" | GAP |
| 34 | ~22-25 | Practice 1 lands and roundcard.py isn't written yet | s-data runs it by hand; the others still hear about the data | s-data gets "Run the round card now" (3622-3626) ✅. s-scout and s-tester get **nothing**: `fp_job` only reacts to a script that exists (3660-3668), and `card_ready` is routed only on success | GAP |
| 35 | ~22-25 | Hand file not gzip (different format, zip, plain JSONL or CSV) | Save it anyway and say what arrived | `fetch_hands` keeps only gzip bodies (3717) and swallows every exception (3725). The bell then says "hasn't downloaded for 5 minutes" (3758) and gives no HTTP status or content type | RISK/BUG |
| 36 | ~22-30 | Hand-history link unknown (SUNDAY step 7): Samuel restarts his hub with `--hands-url` | Set the link without a restart | A restart is required. Ctrl+C kills every descendant (4156-4160), including s-data's foreground maths subagents and s-tester's rig runs at the busiest build minutes. Then all 4 agents are woken to re-read their context (4199-4202) | INEFF/RISK (high) |
| 37 | ~22-30 | The copied link is a signed or expiring URL, or needs the browser cookie | Detected, with the reason shown | `{tid}` substitution plus the Bearer key (3382-3386); failures are silent (#35) | RISK |
| 38 | 0-60 | Samuel types "run the tests on v3" or "can you check everything is on track?" into the Chat | Goes to the Chat as an instruction | PREFLIGHT_RX (221) matches (rx.py), so the hub runs the pre-flight instead and **drops the message**: `ov.pending_q = []` (3885) | BUG |
| 39 | 0-60 | Samuel asks s-data something mid-build (minute 18, while it runs the ranking/ICM subagents) | Answer without losing work | A human message is urgent (1581), and an urgent item interrupts any turn over 45 s old (1542-1550). Subagents are forced into the foreground (1368-1373), so the in-flight subagent work is cancelled and redone | RISK/INEFF |
| 40 | ~22-25 | Practice 1's "DATA LANDED" reaches s-data mid-maths | The card runs; the maths continues | Marked urgent (3619), so it preempts the same way: the m22-m30 tables lose their in-flight subagents | INEFF |
| 41 | 10 | v1 released on time | The bell tells Dylan "Upload v1 now" | Only if someone declared v1 live: `watch_live` (876-882) or b10's UPLOAD reminder (3135-3140, where `human=None` if nothing is live). d-overview's prompt doesn't say "declare v1 live at minute 10". If it forgets, Dylan gets no upload prompt (he can still use the Live menu) | GAP |
| 42 | 10-18 | v1 not ready at minute 10 | Lead re-scopes; Dylan knows | The b10 dispatch to d-platform plus a checkpoint in the lead's situation brief (CHECKPOINTS b10). No hub alert until practice 1's T-2 "NO active bot" (3790-3796) | OK (GAP minor) |
| 43 | 10+ | Upload rejected | Bell, Chat, d-overview; the previous bot stays | `check_team` (3777-3784) alerts both and tells d-overview | OK |
| 44 | 20/30/40/50 | Choosing and uploading a style for a build practice | Ask at P-8, upload by P-3 | The marks fire **at** the practice start: BUILD b20/b30/b40/b50 (2557-2561) = practice times (2936-2937). "Style A ready for practice 1" (DISPATCH b20) and Dylan's UPLOAD reminder arrive when the round is already playing. No clock step asks d-overview for the build-practice "Which bot?" that SUNDAY.md promises | GAP (high) |
| 45 | 18 | Practice without our bot (nothing active) | Urgent bell at T-2 | `check_team` practice T-2 (3787-3796) | OK |
| 46 | 18 | Practice with the wrong bot active (style B declared, A still active) | Bell | Scored rounds only (3797-3800); practices check only that *some* bot is active | GAP |
| 47 | 0-60 | Variant changes players per table (varying table sizes) or stacks | Rules card can hold it | `rule_conflict` compares one number (430-445), so results at a different table size are REJECTED | RISK |
| 48 | 0-10 | Rules card set wrong by d-platform | s-tester catches it; results recorded against it are rejected with "ask d-platform to correct the card" | b0 task to s-tester (2585) + `record_item` message (452-454) | OK |
| 49 | 0-60 | Variant adds a new action type, or the hand-history schema changes | Parsers adapt | Agent work (s-data stream 2, d-platform). The hub's `landed` reads only results fields (`average_points`, `team_name`); if those are renamed, it says "we had no result: forfeit?" (3609-3611) | RISK |
| 50 | 0-60 | d-builder and d-platform disagree on styles | d-overview decides with Dylan | Roles + `consistency_check` (1225) | OK |
| 51 | 25-45 | Practice 1-2 show a style nobody planned dominating | Re-plan practice 3 to test it | b30/b40 still dispatch "Style B/C for practice 2/3" (2592-2597). s-data's b30 analysis and d-challenger's b40 "best response to the measured mix" can redirect, but only if d-overview overrides | INEFF |
| 52 | 0-60 | Usage limit hit during the build (8 Opus agents, each fanning out to up to 6 subagents) | Keep going | The Opus limit switches to Sonnet; a subscription limit switches to an API key only if `~/.config/avalon-hub/anthropic-api-key` exists (1924-1941). Otherwise the agent waits until reset. The pre-flight doesn't check for the key | RISK |
| 53 | 0-60 | Human goes silent (no answer on a decision) | The rule plays at the deadline | `expire_decisions` (1317-1332) for notes d-overview posted. Build practices have no deadline mechanism (#44) | OK / GAP |
| 54 | 50-60 | Round-1 bot choice | A default "Which bot?" note at T-7; cut at T-4 | The T-8/T-6/T-5/T-3 WINDOW steps fire for round 1 (3088). The DeadlineGuard skips round 1 (`windows()` k ≥ 2, 3248), so there's no default note and no "chosen not ready" fallback | GAP |
| 55 | 52-58 | Round 1: the portal's active bot isn't the declared one | Bell at T-7 and T-2 | `check_team` (3790-3800) | OK |
| 56 | 0-60 | The other laptop's Chat needs a clock change it heard about | Both Chats told | `announce_change` (2999-3017) | OK |
| 57 | any | Message to another laptop's agent while the link is down | Queued and delivered later; red bar | bus outbox; heartbeat alert after 2 min (4213-4215) | OK |
| 58 | 0 | Samuel types "the competition starts now" into a worker instead of the Chat | Starts the clock or points him to the Chat | `chat_command` runs only for `*overview` (3878), so the worker just gets a message | GAP (minor) |

## BUG / GAP list, ranked by impact (with a fix for each)

1. **A clock correction marks the corrected build hour as already sent** (#11, #4). This happens after a false start, an early "starts now", or a clock left over from Saturday. `Clock.set_start` copies every sent key from the old start (2955-2960), so minute 0 (all worker tasks and build tiles) and later steps never fire. Probe: `clock_probe` #2 (HEAD and WT).
   **Fix:** carry a sent step over only when its time moved by 5 minutes or less (same occurrence). If the new time is still ahead, leave it unsent. If it's already past, list it once to the Chat as "missed: …" and fire `b0` regardless.

2. **The clock starts by accident, or at the wrong time** (#9, #10). START_RX matches questions, a bare "go", "in 10 minutes" and "at 2pm", and "2:05" is read as 02:05.
   **Fix:** start only on the button or an exact imperative phrase: no "?", no "in N", no "will". Parse "N min ago", "in N min" and "2pm". Read 1-11 as PM when that is within ±3 h of now. Add a pre-event "reset the clock" Chat command (and button) that clears `schedule` on both laptops.

3. **A late or missed minute 0 is dropped for good** (#15, #16, #17). The grace is at most 300 s (3102-3104). An announcement typed 7 minutes late, a link down at minute 0, or a laptop asleep means nobody gets the minute-0 tasks. Probe: `late_probe`.
   **Fix:** build-hour critical steps (b0, b10, b15) never expire before round 1. Fire them as LATE with the real reason, and fire `b0` the first time a laptop sees a schedule.

4. **Saturday's check pollutes Sunday** (#1-#4). It shares the Sunday data directories and namespace, which leaves tiles, `done_stages` (no fast polling all day, 3401), Chat sessions and possibly a clock behind. The pre-flight Clock row is always ✅ (1163).
   **Fix:** SUNDAY step 5 uses `--data ~/.avalon-hub-check/<p> --namespace=-check --portal-data ~/portal-data-check`, or add a `--fresh` flag. Key `done_stages` by competition id. The pre-flight shows ❌ for a schedule older than 12 h.

5. **The schedule shape is fixed at 60/20/30/40/50/+20** (#25-#29, #31, #32). Telling the Chat "practice 1 is at 14:25" moves scored round 1 too. A 45-minute build skips v1 and the rig steps (HEAD).
   **WT fixes:** `build`/`gap`/`pin_round` and the stage labels.
   **Still open in WT:**
   - The number of build practices is fixed at 4.
   - "practice N at" (N ≤ 4) still moves minute 0.
   - Practices always count back from round 1.

   **Fix:** a `practice_at` pin per build practice, plus a practice count (`event='format', practices=3`). Key the b20-b50 marks to those pins. `events()`, `check_team` and `finishing` follow them.

6. **Practice drift alerts suggest moving minute 0** (#30, HEAD #28). With different practice offsets that shifts every scored round.
   **Fix:** a practice's drift proposes "practice N at HH:MM" (a pin). Only scored-round drift pins rounds (WT already pins scored rounds), and never suggest moving minute 0 after round 1 is seen.

7. **Synced clock changes re-fire steps, and a double start runs the minute-0 dispatch twice** (#13, #14). Probe: `sync_probe`.
   **Fix:** run the carry-over rule from fix 1 in `tick()` whenever the observed `start` (or the pins) differs from the last one seen, whichever laptop changed it.

8. **Build-practice steps fire at the practice start, not before it** (#44, #46). The style choice and Dylan's upload reminder arrive when the round is already playing, and there's no build-practice "Which bot?" step.
   **Fix:** add P-8 (d-overview proposes kind=bot for practice N with a deadline at P-4) and P-4 (UPLOAD) marks for each build practice, and move DISPATCH b20/b30/b40 to P-10. `check_team` practice T-2 also compares live with active.

9. **The `--hands-url` step needs a mid-build restart** (#36, #22), killing Samuel's agents' in-flight work around minute 25.
   **Fix:** a Chat command or UI field "hands link: <url>". It sets `portal.hands_url`, saves it in `portal_state.json`, and calls `retry_hands()` at once. The Saturday pre-flight tries the default URL on any finished round of any competition the key can see (Bay Area), and if that works, SUNDAY step 7 goes away.

10. **Hand files that aren't gzip are silently dropped** (#35, #37; 3717, 3725).
    **Fix:** save any non-HTML 200 body under the right extension, and record the last HTTP status and content type for each round. Put them in the 5-minute alert ("401: the link needs the browser login", "got text/html").

11. **"run the check" phrasing swallows real instructions** (#38). PREFLIGHT_RX matches "run the tests on v3" and "check everything is on track?", and 3885 drops the message.
    **Fix:** anchor it as `^\s*(run (the )?(pre-?flight|check)|pre-?flight|check everything works)\s*[.!]?\s*$`.

12. **The hub's round-card run lacks the analysts' Python packages** (#33; 3689-3692; system python3 has no numpy here).
    **Fix:** run the scripts with `uv run --no-project --with numpy --with pandas python -I …`, or tell s-data and s-scout to create `.venv` and add a pre-flight row for it. Test both scripts on a Bay Area download on Saturday.

13. **The pre-flight shows ✅ when it shouldn't** (#6, #8, #19, #21).
    - Portal ✅ on Samuel's laptop with no watcher (1141).
    - The chosen competition isn't checked to be the Finals (3459-3462). Show ❌ if it has no rounds after today, or if its name or date isn't the Finals. Document `AVALON_COMPETITION_ID`.
    - No code-version parity: publish `git rev-parse HEAD` in the directory and show ❌ when the laptops differ.
    - No `git push --dry-run` row for the team repo, and no clock-offset row.

14. **Nothing notices a silent portal** (#7).
    **Fix:** an urgent bell to both laptops when no round is seen within 8 minutes after an expected practice start.

15. **Urgent items preempt workers mid-subagent** (#39, #40; 1542-1550, 1581, 1373).
    **Fix:** no preemption while foreground subagents are running. The hub replies to the human at once: "<agent> is mid-task since HH:MM; your message is next". In the build hour, practice "DATA LANDED" isn't urgent for s-data.

16. **v1 isn't made live automatically** (#41).
    **Fix:** when no live bot exists and the first release is registered `ready`, the hub calls `make_live` (by "hub: first legal bot"), so Dylan gets "Upload v1 now".

17. **Practice data reaches only s-data and the Chats** (#34).
    **Fix:** `landed`/`retry_hands` always send s-scout and s-tester a wake item with the paths, whether or not the scripts exist or succeed.

18. **Round 1 has no deadline guard** (#54; 3248).
    **Fix:** include k=1 for the `note` and `chosen` guards (the window starts at practice 4's end).

19. **The kit's arrival isn't an event** (#24).
    **Fix:** watch `repo/starter-kit/` (and the setup skill's folder). On first appearance, send its path to d-platform, s-data, s-tester and s-scout.

20. **The rules card holds a single number for players** (#47).
    **Fix:** accept a list or range ("6-9") in `rule_conflict`.

21. **The LATE header is garbled** (#18; 3109, 3124).
    **Fix:** build the header from the step key, and pass the reason (restart / late start / link / sleep).

22. **Minor items:**
    - "starts now" typed into a worker doesn't start the clock (#58).
    - The pre-flight doesn't check for an API-key fallback (#52).
    - b30/b40 style dispatches are fixed even when practice data says pivot (#51): make the dispatch text "the style d-overview names (default B)".
