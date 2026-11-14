# Scenario audit: scored rounds 1..N, every T-20..T-0 window, end of event

Audited against the working tree on 13 Nov 23:00. That is HEAD `a3757f8` plus **uncommitted edits that were
being made while this audit ran**: round pinning (`round_starts`, `pin_round`, `build`/`gap`), practice labels that
follow the scored-round count, and guard keys `{minute0}:r{k}`. Line numbers refer to that tree (`hub/hub.py` unless
another file is named). Proof script: `scratchpad/audit/rounds_probe.py` (with `probe2.py`; output in
`rounds_probe.out`), which runs real hub code against fakes and touches no network or agents.
"PROVEN" means the script reproduces the behaviour.

Verdicts: OK / BUG / GAP (nothing handles it) / RISK (works only if an LLM or a human gets it right, or rests on
an unverified portal assumption) / INEFF (works, but wastes time or causes noise).

## A. Scenario table

| # | Scenario | Ideal behaviour | What the code and prompts do (file:line) | Verdict |
|---|---|---|---|---|
| 1 | Normal window: data lands T-14..T-12 | Card in under 60 s; s-data, s-tester and s-scout start; T-8 rule answer; T-3 upload | `landed()` 3673 wakes s-data (urgent), s-overview and d-overview; `analyse()` 3760 runs the card and fp; ROUTES; DISPATCH T13 2637+; guard 3247 | OK |
| 2 | Results land after T-10 | Data cut at T-10; when they land, they feed the profiles and the next window, not this window's change | Guard `data` cuts at T-10 (3297, 3377). `landed()` still sends s-data an urgent "DATA LANDED… finish within 2 min". The `change` cut then fires at T-8 and stops s-data. s-data gets two conflicting orders, 2 minutes apart | INEFF |
| 3 | Results land after T-8 | Profiles and leaks only; nothing ships | As in #2. s-data is woken urgently (and interrupted) after T-8. Nothing says "for the next window" | INEFF |
| 4 | Results never land | Live bot plus validated changes; a human fetches the files | `land_fail` alert after 3 tries, gives up at 15 (3593) and asks for a manual drop; data cut at T-10 | OK |
| 5 | Results JSON lands, hand file never does | Same as #4, with one clear human ask | `need_hands`; humans pinged after 5 min, warned again at 20 min (3832+); `landed_at` stays unset, so the T-10 data cut fires | OK |
| 6 | Practice (k.5) result late, after T-8 | The rule has no challenger number, so the live bot plays; say so explicitly | Nothing computes the rule. The T-8 recommendation (DISPATCH T8) may go out without the number, and nothing re-triggers it when the practice lands. DECISION_RULES §3 says only "Otherwise the live bot plays" | GAP |
| 7 | Practice result lands T-9..T-7 (the usual case: 1-3 min after a T-10 start) | The decision waits for it, at most to T-7 | s-data gets an **urgent** "DATA LANDED" (3735). That interrupts its one-change work just before the T-8 `change` cut-off, so the cut can fire on work that was nearly done | RISK |
| 8 | Practice round skipped by the organizers | The challenger can't be measured. The rule should fall back to grade-B evidence or pooled data, not freeze | New labelling (3564) maps the next practice correctly (fixed in the working tree). The rule needs a practice score, so the challenger can never qualify until a later practice: a freeze | GAP (rules) |
| 9 | Two practices between scored rounds | Distinct labels | Both are labelled "Round k.5" with the same `_n` (PROVEN). `landed_at`, `done_stages` and the tiles collide | BUG (low) |
| 10 | A 5th practice in the build hour | Label "Practice 5"; no clock alarm | `_n=5` (PROVEN), so `check_clock` compares it with practice 5's expected time (before scored round 2). The result is a false "clock is off ~15 min, move minute 0" alert to both Chats | BUG |
| 11 | Scored round delayed, organizers announce it early | Human tells the Chat; that round and later ones move | `set_schedule scoredN`, then `pin_round` 3043: later rounds and deadlines move; guard keys unchanged | OK (new code) |
| 12 | Scored round delayed **silently** (it just starts late) | Guard holds its cut-offs while the previous round hasn't visibly started; ask the humans | Guard fires the next window's cut-offs on the old times ("no data", "no challenger", a default "Which bot?" note) before the portal shows the round and pins it. After the pin, `r{k}` keys and clock keys `{t0}:s{k}-o` are already done, so the real window is unguarded and its steps don't re-fire (PROVEN) | BUG |
| 13 | Round started early or ended early | Pin; fast poll; data earlier | Pins when drift > 90 s (3659); `finishing()` 3483 runs fast polls 2-15 min after start | OK |
| 14 | Clock 2 min off, found during a window | Correct it before T-3 | A scored round pins only when it starts. A practice drift under 180 s raises no alert (3659+). With a clock 2 min late, the T-3 upload really lands at T-1 | GAP |
| 15 | Human corrects minute 0 mid-event ("minute 0 was X", as the drift alert tells them to) | Deadlines move; work already done stays done | `set_start` copies the sent clock keys, but guard keys `{start}:r{k}` change. The guard re-checks done work against the new window start: one-change, challenger and note are "not met", so spurious cut-offs fire (PROVEN, 4 cuts) | BUG |
| 16 | Scored round cancelled and re-run | Rerun keeps the label "Round k"; the cancelled round is ignored | `cancelled_at` is ignored. The cancelled round stays "playing vN" forever (3613). The rerun is labelled "Round k+1" (PROVEN), so the guard never sees "Round k" data and cuts "no data" next window | BUG |
| 17 | Last or final round has another `kind` ("final") | Treated as the last scored round | Labelled "Round 1", `_n=1` (PROVEN). `check_clock` pins **scored round 1 to now** and drops later pins, so every later deadline jumps (PROVEN) | BUG (if the kind differs) |
| 18 | Portal pre-creates rounds before they start | No false pins | `created_at` is used only if it is less than 600 s before first seen. The round is "seen running" at creation (no `started_at` check), so it can be pinned to its creation time | RISK |
| 19 | Round with zero hands for us (forfeit, crash, culled) | Say "we played no hands"; don't ask humans to download a file that doesn't exist | "(we had no result: forfeit?)" (3717). An empty hand file is under 100 bytes and is never saved, so the 5-min and 20-min "download it by hand" pings fire | GAP |
| 20 | Culled from contention (`contender=false`) | Tell both humans at once; switch to maximum variance or learning (nothing to lose); stop the T-8 ceremony | Nothing reads `contender` or `culled_at_look`. The rule keeps applying the SE bars | GAP |
| 21 | Leaderboard held: `/standings` returns 403 or an error | Everything else keeps working; agents told "standings unknown, use rule X" | `poll()` fetches standings **before** the team, submissions and active bot. An error aborts the poll: `portal_active` is never updated; no rejection, no-active-bot or wrong-bot alerts; after 3 polls, "portal not answering" (PROVEN) | **BUG (critical)** |
| 22 | Leaderboard held: empty `items` | Rule has a defined fallback for "top 3 or not" | Tile shows "N rounds seen"; DECISION_RULES §3 has no branch for unknown standing. Agents guess or stall | GAP |
| 23 | `final_weight` revealed late | Rules card updated; last-round plan re-weighted; humans told | `/competitions/{cid}` is read only once, in `identify()`. Nothing watches `final_weight` or `final_revealed_at`; the situation shows "weight: read it…" (2837) | GAP |
| 24 | Last round worth about 40% of the points | Plan it from the round before; hold exploits back; consider a bolder bar | Only prose (DECISION_RULES "When to be bolder"). No DISPATCH item for k = N-1 or N; the T-13 tasks are the same every window | GAP |
| 25 | ICM luck correction on | Card uses corrected points | Not read anywhere | GAP (low) |
| 26 | Challenger not ready at T-12 | Practice plays the best already-tested bot; challenger keeps building | Guard `challenger` cut 3247 (the challenger is not woken); humans told. No clock bell asks Dylan to upload the challenger when it *is* ready, because the clock's UPLOAD alert only asks for the declared live bot (3222) | OK / GAP (no T-12 upload bell) |
| 27 | Challenger ahead by 0.9 SE, outside the top 3, not the last two rounds | Live bot plays, plus up to 3 changes; the challenger replays next practice | That is the rule's answer. Fine **if** an agent computes it; the hub never computes it | OK (rule) / RISK (computed by an LLM) |
| 28 | Challenger ahead by 0.9 SE, behind 3rd, last two rounds | Challenger plays (bar 0.5 SE) | Rule says so; same caveat | OK / RISK |
| 29 | SE arithmetic | z = (C - L) / sqrt(SE_C² + SE_L²) using the portal's `margin_of_error` | The rule fixes "about 0.65 per table" for the *difference*. A practice-vs-practice comparison is √2 noisier, so 1.0 "SE" is about z=0.7 on noise. It also compares different fields (other teams experiment in practice) | RISK (rules) |
| 30 | The practice result is credited to the wrong bot | Record which bot was active when the practice **started** | The round tile is rewritten every poll with the *current* active bot (3613-3615). Dylan reverts at T-9, so the practice shows "playing v5" (live), not the challenger. The result line never names the bot. The rule then reads the wrong row | **BUG** |
| 31 | The portal reads the active bot per match, not per round | Don't switch back at T-9 while the practice is still running | WINDOW T-9 "put the live bot back straight away" (2621+). If the portal swaps bots mid-round, the challenger's practice score is a blend | RISK (unverified portal semantics) |
| 32 | `d-overview` is mid-turn at T-5 expiry | The rule's answer applies anyway (hub-side) | `expire_decisions` 1351 only queues a **non-urgent** item for the author; nothing changes `live` (PROVEN). A long turn pushes the switch past T-3 | **BUG** |
| 33 | Two humans give opposite answers (approve, then reject) | Both see the conflict; the default or rule plays unless they agree | `human_act` has no status check. Reject after approve sets status "rejected" but `make_live` has already run, so v7 stays live and Dylan is still asked to upload it (PROVEN) | **BUG** |
| 34 | Reject, then approve | Same as #33 | Last click wins, with no conflict message (PROVEN). SUNDAY.md says "you disagree… the live bot plays", but code and doc disagree | BUG |
| 35 | Human answers after T-5 on the board | One consistent policy | A late approve is refused ("Too late", 1027), but its thread entry and `human_item` were already sent. A late reject is accepted (PROVEN). The same answer in the Chat succeeds: `update_proposal` accepts the "expired" status (2560) | BUG (inconsistent) |
| 36 | Conditional answer ("yes if the tester passes") | Recorded as conditional; at T-5 the rule's answer applies if the condition is unresolved | `CONDITIONAL` (247) sets status "approved" with a condition, so `expire_decisions` never fires and the live bot stays even when the rule said challenger. The regex also matches "yes, even if risky" or "go, if ready", which then never goes live | RISK |
| 37 | Human says "use v7" in the Chat; v7 untested | Refuse, or label it "override: untested" and run the T-6 test; 2.1 is a hard rule | `declare_live` 2243 and `make_live` 848 run no test check. Bot status "ready" means only "a zip exists" (releases watcher; `propose()` also sets "ready") | RISK |
| 38 | Guard T-4 "chosen bot released and tested" | Checks a real upload-test result | `met('chosen')` 3320 accepts status "ready" plus the file exists (PROVEN). An untested zip passes | BUG |
| 39 | Upload rejected at T-3 | `live` reverts to the previous bot; humans told "do nothing, v5 plays" | Alert "previous bot stays active", but `live` stays the rejected v7 (PROVEN). At T-2: "active is v5 but declared v7". At the next T-9, Dylan is asked to upload v7 again. The zip isn't marked failed either | BUG |
| 40 | Upload still validating at T-0 | The previous bot plays; say so | T-2 mismatch alert; no "round started with X" check | OK / GAP |
| 41 | Wrong bot active at round start | Alert early enough to fix (T-3), plus a T+0 confirmation | Checks only at T-7 (any bot) and T-2 (3895). T-2 leaves under 2 min, and an upload needs a test match plus 30 s. No check after the start | GAP |
| 42 | Dylan uploads the wrong zip (right name, other file; or "v7 (1).zip") | sha256 compare against `releases/vN.zip` | Names only (`norm_bot` and `same_bot` 263; " (1)" is stripped); `live.sha256` is usually "" | GAP (low) |
| 43 | The active bot is someone's experiment (challenger left on after practice) | T-9 bell; T-2 alert | Clock UPLOAD at T-9 fires when live != active (3222); T-2 alert | OK |
| 44 | Live bot crashes or times out in a scored round | Detect from the card (our timeouts or illegal actions) and alert humans; fix next window | Nothing mid-round. The card is LLM-written and no hub check counts our errors | GAP |
| 45 | An opponent team starts exploiting us (profiled-us) | Fingerprint card flags it; disguise memo | FINGERPRINTING §5 plus fp_train `profiled_us`; prompt-level only | RISK (prompt) |
| 46 | The field's style shifts between rounds | Re-measure; the challenger answers the measured mix | DISPATCH T13 to d-challenger "revise it from this round's data" | OK (prompt) |
| 47 | Data contradicts the plan's priors | Real data overrides the priors (grade A over C) | DECISION_RULES §4-5; s-data T13 reminder | OK (prompt) |
| 48 | s-tester disputes a number at T-8 | Only a reproduced counter-number blocks; otherwise decide labelled "unverified" | DECISION_RULES §4. Consistency check is prompt plus `consistency_check` | OK (prompt) |
| 49 | Ledger items invalidated mid-window | Recommendation re-cited; note updated | `invalidate` tool exists; nothing re-wakes the T-8 note when one of its cited ids is invalidated | GAP (low) |
| 50 | Two agents edit the same file | Separate folders | Prompt only ("each in its own folder"); no lock | RISK (low) |
| 51 | Modal containers exhausted | Fall back to local or Codex; shrink shards | FANOUT asks for 40+20+20+20+… concurrent containers at T-13; nothing tracks quota | RISK |
| 52 | Round-card script crashes on a new hand-format quirk | s-data runs it by hand; guard "card" cut | `analyse()` failure goes to s-data urgently. But `met('card')` takes any `*card*.md` under `analysis/` newer than landing, **including the fingerprint job's `fp/card.md`**, so the cut never fires (PROVEN with fp/card.md) | BUG (if fp writes card.md) |
| 53 | Round card or fp script hangs | Killed at 90 s | `run_card` timeout | OK |
| 54 | Hub restarted mid-window | Missed steps fire, marked LATE; guard and portal state survive | `clock_sent.json`, `guard_done.json`, `portal_state.json` (with `landed_at`); grace up to 5 min (3160+) | OK |
| 55 | Hub down at a round's start | Use `created_at` | Uses `created_at` within 600 s (3646+) | OK |
| 56 | Portal unreachable 3 polls | Alert | Alert at 3 (loop) | OK |
| 57 | "Decision time" bell at T-8 | Humans see it until the note exists | `tidy_bell` dismisses it in the **same tick** if the note isn't posted yet, and d-overview posts at T-8 (PROVEN) | BUG (low) |
| 58 | No note by T-7 | Hub posts a default note with the live bot | `post_default_note` 3413 | OK |
| 59 | Rule says challenger, note expires, d-overview idle | d-overview declares live; Dylan uploads by T-3 | Prompt in `expire_decisions`; watch_live asks Dylan | OK (if idle) |
| 60 | Round 1 (after the build hour) | Same cut-offs as other windows | Guard windows start at k=2 (`windows()`), so round 1 has no T-4 or T-7 safety net | GAP |
| 61 | Same `team_name` text differs ("Avalon" vs "avalon") | Match | Exact-string compare (`ours`), so "we had no result: forfeit?" and no standings | RISK (low) |
| 62 | Last round finished | Final result to both humans; agents stop; Modal apps stopped | `landed()` treats it like any round: urgent analysis, card, fp, ROUTES, s-tester verify. "PHASE: the event is over" only after +20 min; `stage_of` says "Round N" forever (PROVEN). No wind-down | GAP (cost / noise) |
| 63 | Last round: no practice after it | No T-12/T-8 machinery after round N | WINDOW only before rounds; correct | OK |
| 64 | Practice landing closes the scored round's analysis tile | Keep it open until the change is recorded | `landed()` 3705 marks every other in-progress analysis tile done, so at about T-8 the round-k analysis shows "done" mid-analysis | INEFF |

## B. Bugs and gaps ranked by impact, with fixes

1. **Standings error kills the active-bot watch** (#21, PROVEN). A held leaderboard is plausible at the Finals. With it, rejection, no-active-bot and wrong-bot alerts all stop for the rest of the event.
   *Fix:* in `poll()`, put `/standings` in its own `try`, and fetch team, submissions and `check_team` first. On error, keep the last standings and set `st["standings_held"]=True`. Situation line: "Standings unavailable (held)". Add a unit test that raises on `/standings`.
2. **Practice result credited to the wrong bot** (#30). The whole §3 rule rests on "the challenger's practice score".
   *Fix:* in `check_clock` (first seen running), store `st["played_by"][rid] = portal_active.filename`. Never overwrite the round tile after the first poll. Put "played by vN" in `landed()`'s line and in `results.json`.
3. **T-5 expiry never applies the rule** (#32, PROVEN), and **opposite human answers** (#33/#34, PROVEN). Together these make "who plays" undefined in exactly the stressed cases.
   *Fix:* store `rule_answer` (bot file) on the "Which bot?" note at creation (a `propose` arg; the guard's default note sets the live bot). In `expire_decisions`, call `make_live(rule_answer)` itself, with the alert "rule applied", and send the author an **urgent** item. In `human_act`:
   - if status is already approved or rejected by the *other* person with the opposite verdict, set status `conflict`, ping both Chats, and keep the rule's answer;
   - a reject after approve calls `make_live(prev)`;
   - check the deadline **before** appending to the thread;
   - apply the same deadline policy to reject and to `update_proposal` (or move both deadlines to T-4, the real cut-off).
4. **Silent round delay, or a minute-0 correction, triggers spurious cut-offs** (#12 and #15, PROVEN). These mean false "no data / no challenger" bells, a default note, an expiry 20 min early, and an unguarded real window afterwards.
   *Fix:*
   - Guard `data`: if round k-1 hasn't been *seen started* on the portal (`seen_start`) by its expected time + 3 min, don't cut. Alert "round k-1 hasn't started: delayed?" once, and pause the window's cut-offs.
   - Key the guard and clock marks by round start (`int(round_ts)`) rather than minute 0, and on `pin_round` drop the not-yet-due keys of the moved rounds so they re-fire.
   - Judge "met" by absolute recency (for example "since the previous round started"), not by the new `start`.
5. **Rejected live upload keeps the bot "live"** (#39, PROVEN).
   *Fix:* in `check_team`, when a rejected filename equals `live.filename`, `make_live(prev)` with `tell=False`, mark `bot:vN` `failed`, and change the alert to "v7 rejected (reason). v5 stays active; upload nothing unless your Chat gives a fixed file."
6. **Guard T-4 and `make_live` accept untested zips** (#37/#38, PROVEN).
   *Fix:* a separate status `upload_tested` (set by d-platform's upload-test or s-tester's `verify`). `met('chosen')` requires it. In T-8..T-0, `declare_live`/`make_live` of a bot without it returns a warning that needs `override=true` from a human turn.
7. **Kind or label fragility: cancelled reruns, "final" kind, extra practices** (#9, #10, #16, #17, PROVEN).
   *Fix:*
   - Skip rounds with `cancelled_at`.
   - Count every non-practice kind in one scored counter (`stage_of_round("scored", n_all_scored)`).
   - Build-hour practices beyond 4: no drift check.
   - Label a second practice in the same gap "Round k.5b".
   - Never pin a round whose `_n` is far (> 2 rounds) from the clock's expected index; alert instead.
8. **The hub doesn't compute the §3 rule** (#6, #27-29). It is left to two LLM hops in 3 minutes.
   *Fix:* a hub function `rule_answer(k)`:
   - inputs: the practice row of the bot that played (from fix 2), the live bot's last comparable row, and z from the portal's `margin_of_error` (combined √(a²+b²));
   - standing from the standings, weights and rounds left;
   - output: the bar and the answer.
   Post it in the note body at T-8 and recompute it when the practice lands. Rule text: use the combined SE; if the practice hasn't landed by T-7, the answer is "live".
9. **Leaderboard held, culled, `final_weight`** (#20, #22, #23).
   *Fix:*
   - Re-read `/competitions/{cid}` every poll and alert on changes to `final_weight`, `final_revealed_at` or `leaderboard_held`. Update the rules card's weights.
   - Read `contender`/`culled_at_look` from our results row and alert "we're culled".
   - DECISION_RULES §3:
     - standings unknown: compute our own totals from per-round results × weights; if impossible, treat us as "outside the top 3" (1.0 SE);
     - culled: always play the challenger or experiment;
     - final weight unknown: assume the largest plausible weight.
10. **Practice landing interrupts s-data before T-8** (#7), and the scored analysis tile closes (#64).
    *Fix:* send practice "DATA LANDED" non-urgent to s-data when `T < 9`, with the text "for the T-8 rule: the challenger's practice number only". Close older analysis tiles only when a *scored* round lands.
11. **Practice swap timing** (#31).
    *Fix:* confirm with the organizers or the portal docs whether a round snapshots the active bot at its start. Until confirmed, change WINDOW T-9 to "put the live bot back as soon as the practice result lands (by T-6 at the latest)", and the T-9 HUMAN_STEPS bell to match.
12. **Wrong-bot checks too late, none after the start** (#41, #40).
    *Fix:* add the declared-live check at T-3 + 60 s, and a T+1 check ("round k started with vX; declared vY"). Compare sha256 with `releases/vN.zip` (#42).
13. **Card guard satisfied by the fp card** (#52).
    *Fix:* match only `analysis/<stage-slug>/card.md` (and the variants `Round-k`, `round-k`), and exclude `*/fp/*`.
14. **Round 1 has no guard** (#60).
    *Fix:* let `windows()` include k=1, with only `note` and `chosen` active, start = round 1 - 10 min.
15. **Zero hands, forfeit or crash** (#19, #44).
    *Fix:*
    - When the results row shows us at 0 tables, or the hand file is valid gzip with 0 lines, alert "we played no hands in Round k: forfeit or crash?" and skip the manual-download pings.
    - Have `roundcard.py` print our timeouts and illegal actions first. Add a hub-side grep over the hand file for our error markers that raises an urgent alert.
16. **End of event** (#62).
    *Fix:* when the last scored round lands, post the final line to both Chats and send no card or ROUTES. Tell every worker "event over: record, stop", stop Modal apps, and make `stage_of` return "Finished".
17. **Last-round planning** (#24).
    *Fix:* add DISPATCH `T20` for k = N-1 ("plan round N: held-back exploits, durable fixes, bar per standings and weights").
18. **"Decision time" bell dismissed instantly** (#57).
    *Fix:* in `tidy_bell`, dismiss it only after a bot note for this round exists *and* is no longer waiting, or after 5 min.
19. **Conditional regex too broad; conditional approval bypasses expiry** (#36).
    *Fix:* keep status `needs_call` with a `condition` field, so expiry still applies the rule. Tighten the regex (require "if/once/provided" followed by a clause about a test or result).
20. **No T-12 practice-upload bell** (#26).
    *Fix:* at T-12, if a challenger released this window isn't active, bell Dylan with "Upload vN for the practice".

## C. Do the §3 rules decide well?

- **They don't freeze in the normal case.** 1.0 SE ≈ +0.65 points per table on one practice, which is a low bar. With the fixed 0.65 used as the SE of a *difference*, the real z is about 0.7, so outside the top 3 they switch on noise fairly often. That fits "only the top 3 pay", but inside the top 3 the 1.5 bar is only z ≈ 1.06.
- **Use the portal's own `margin_of_error`, combined, and pool practices when a challenger replays.**
- **They freeze in three cases:**
  - no practice (skipped, late, or credited to the wrong bot): the challenger can never qualify;
  - standings unknown (held): the bar is undefined;
  - final weight unknown: the "one round's swing" clause is undefined.
  Each needs a written default (see fix 9). With the defaults, the team keeps moving: outside the top 3 or unknown standing gives the lower bar; no practice number gives the live bot, and the challenger gets the next practice.
- **When the hub, not an LLM, computes the rule's answer**, the T-5 default becomes real (fixes 3 and 8). Today "the rule's answer plays" depends on d-overview being idle at T-5.
