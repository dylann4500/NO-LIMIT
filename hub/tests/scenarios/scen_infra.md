# Infrastructure failures and agent dynamics: scenario audit

Scope: (A) infrastructure failures and (B) agent dynamics and human interaction, across the whole Finals day.
Code audited: **committed HEAD a3757f8** (`hub/hub.py` 4,224 lines, `hub/bus.py`, `hub/roster.py`, `hub/ui/index.html`).
Line numbers below refer to HEAD. A snapshot is in `audit/head/`.
Note: while I worked, someone else had **uncommitted** changes in `hub/hub.py`: a clock rework with `round_starts`, `pin_round`,
`set_schedule format`, and guard keys `rid`. I did not audit those changes. Where a finding touches the clock, I say whether
it still applies.

Proof scripts (no network, no model, run against the HEAD snapshot):
`uv run --no-project --with aiohttp==3.14.5 --with claude-agent-sdk==0.2.181 --with modal==1.6.4 python -u <script>`
- `audit/infra_proofs.py`: probes P1 to P9. Seven of them confirmed a bug. P8 is a code-reading GAP (the probe's string test gave a false negative). P9 measured the cost of a late-day `state()` call and found it fine.
- `audit/infra_p6_control.py`: P6 control. With no clock skew, the newer value wins, which shows the bug comes only from the skew.
- `audit/infra_proof_limit.py`: P10, a transient rate-limit error treated as a usage limit.

Verdicts: **OK**, **BUG** (wrong behaviour, proven or plain in code), **GAP** (a needed path is missing), **RISK** (works,
but likely to fail on the day), **INEFF** (inefficiency).

## Scenario table

| # | Scenario | Ideal behaviour | What the code does (HEAD file:line) | Verdict |
|---|---|---|---|---|
| A1 | Venue Wi-Fi drops for 2 min mid-round | Both laptops carry on locally; cross-laptop messages queue and arrive after the drop | Outbox resends until acked; failed puts don't count against a message (bus.py:186-211, 220-243). Shared values stay dirty and re-upload (bus.py:306-368). The heartbeat alerts after 2 min (hub.py:4216) | OK |
| A2 | Hotspot switch while an agent's API stream is open | The stream fails fast and the turn retries within about a minute | No hub-side detection. Only the stall watchdog acts: interrupt at **12 min** of silence, disconnect 90 s later (hub.py:187, 1283-1315). A lead can be silent for ~13.5 min across T-8 | RISK |
| A3 | Hotspot switch during a hand download | Partial file never counted; retry; ask a human if it keeps failing | gzip check before saving (hub.py:3717-3723); `need_hands` retry; alert at 5 and 20 min (3729-3766) | OK |
| A4 | Modal outage, clock already set | Each laptop keeps its clock and dispatch | Schedule persisted in shared.json (bus.py:81-89, 315-322); Clock runs on each laptop (hub.py:3061) | OK |
| A5 | Modal outage at minute 0 (clock not yet shared) | Either human can start their own clock; it reconciles cleanly afterwards | Each Chat's "starts now" sets a local clock (hub.py:1091). On reconnect the newer write wins, but the other laptop's `Clock.sent` keys (keyed by int(t0)) are not remapped, so marks still in their grace window fire again (P5) | BUG |
| A6 | Modal outage at T-8 | Dylan decides with what his side can see; Samuel's recommendation is relayed verbally; the rule plays | s-overview's recommendation sits in the outbox. The 'Which bot?' note exists only on Dylan's laptop. Hub, prompts and SUNDAY.md give no outage-mode rule beyond the alert "talk to your teammate directly" (hub.py:4217) | GAP |
| A7 | Modal outage: decisions board | Notes merge after reconnect, nothing lost | merge_note keeps both threads (hub.py:79-95); notes re-shared at start (4141-4145) | OK |
| A8 | Modal outage: work queue | Same-laptop claims still work | `queue_claim` needs the Modal `put(skip_if_exists)`; on any error `won=False`, so nobody can claim anything (hub.py:583-587). Proven (P7) | BUG |
| A9 | Modal outage: uploads / Live menu | Dylan can still download locally built bots | Local zip first, then the Modal store (hub.py:789-797). Releases are built on Dylan's laptop | OK |
| A10 | Modal outage: portal facts on Dylan's laptop | Dylan's side knows it is blind | `portal_active` and round results come only from Samuel's watcher via the bus. Dylan's "Upload vN now" alert can't auto-clear (hub.py:868-882). The 'checked HH:MM' time in situation() is the only hint (2837) | RISK |
| A11 | Modal compute down (paired tests, sparring) | Run smaller local tests; label results as lower-n | No fallback guidance anywhere (prompts push Modal: roster.py:130-133, 155-156) | GAP |
| A12 | Modal link never comes up at start (no token) | Clear error, retried | `start()` sets "retrying"; loops retry while q/d exist; preflight shows ❌ (bus.py:102-115, hub.py:1117) | OK |
| A13 | Samuel's hub crashes; start.sh restarts it in 3 s | Agents resume, the clock catches up, nothing duplicates | Children of the old run are killed (hub.py:4147-4152). Sessions resume, inbox persisted (1398-1403). Steps missed within grace fire marked "LATE" (3103-3109). The portal state persists | OK |
| A14 | Hub restart while Codex jobs run | Agents are told their jobs died | `Codex.jobs` lives only in memory (hub.py:2852). The codex processes are killed as leftover children. The agent waits forever for "the result arrives as a new turn" | GAP |
| A15 | Hub restart while a background Modal job (from Bash) runs | The agent learns the job is gone | The `modal run` client is killed with the children, so the app stops. The agent gets only a generic "hub restarted" note (hub.py:4200) | RISK |
| A16 | Hub restart: human messages not yet answered | Still tracked | `pending_q` and `note_pending` are in memory only (hub.py:1416, 298) and lost on restart | GAP (minor) |
| A17 | Laptop sleeps (lid closed) across T-13..T-3 | On wake: every missed step reported once, late | `tick` fires a mark only if `at <= now < at+grace` (grace ≤ 5 min, hub.py:3100-3111). Older marks are dropped silently with no LATE note. caffeinate prevents idle sleep only (start.sh) | GAP |
| A18 | Samuel's laptop dies for good | Dylan's laptop takes over the portal watcher and s-* roles | The portal watcher runs only where `--portal-base` is given (hub.py:4181). No documented failover command. The key file is only on Samuel's laptop | GAP |
| A19 | Subscription limit hit on one laptop, no API key saved | Agents wait for the reset and pick up a key as soon as one is saved | They sleep until `resets_at`+30 s, possibly hours (hub.py:1937-1951), and never re-check `API_KEY_FILE` while asleep. The alert says "save a key" but not that each agent then needs Stop/Start | BUG |
| A20 | Transient 429 / "overloaded" from the API | Back off 30-90 s, same auth | `handle()` returns "limited" for any `rate_limit`/`overloaded`/`429` text (hub.py:1969, 1983). `run()` raises LimitHit, so `is_limit` is true (1919). Result: a 5.5-min sleep and a false urgent alert, or a **permanent switch to the paid API key**. Proven (P10) | BUG |
| A21 | Opus weekly allowance used up | Switch to Sonnet; return to Opus after the reset | Switches (hub.py:1926-1930) but `model_switch` is sticky for the rest of the day | INEFF (minor) |
| A22 | Hub's own model calls (consistency, report, preflight) at a usage limit | Degrade quietly | Each fails, is logged and skipped (hub.py:1260-1262, 920-922) | OK |
| A23 | Codex not logged in | Agents told once; recovers after login | `broken` is set and an alert says "restart the hub" (hub.py:2913-2917). That restart kills every agent's processes. `broken` is never re-probed | RISK |
| A24 | Codex hangs | Bounded | 30-min timeout, at most 6 at once (hub.py:2893, 2853) | OK |
| A25 | Disk fills up | Warned before it bites | Only the preflight checks (>5 GB, hub.py:1160). At runtime `atomic_write` raises: a clock mark is added to `sent` before its write, so the dispatch is lost (3110-3111), and the heartbeat dies (A35) | RISK (low prob.) |
| A26 | Runaway subagent in a worker | The lead is told promptly in the crunch | 25-min long-turn notice goes to the lead **non-waking** (hub.py:1292-1297). No cap | RISK |
| A27 | Runaway / detached Modal app | Spend and container count visible; stopped at shutdown | No Modal monitor; prompts only say "check `modal app list`" (roster.py:133). Shutdown stops local processes only (hub.py:4156-4159) | GAP |
| A28 | A tool call hangs (Bash, WebFetch) | Interrupted and retried | Stall watchdog: 12 min, then interrupt, then disconnect, then retry (hub.py:1283-1315, 1879-1884) | OK (slow for leads, A2) |
| A29 | `get_context_usage` (compaction check) hangs | Bounded | No timeout (hub.py:1736). Recovered only by the 12-min watchdog | RISK (minor) |
| A30 | Huge tool output | Truncated before it reaches the context or the UI | Events store 1,200 chars (hub.py:1974); CLI truncates Bash. `read_agent` can return 200 x 400 chars (≈20k tokens) (2118-2126) | OK / INEFF |
| A31 | Compaction loses the plan | PLAN file + role list survive | COMPACT_KEEP + role "keep"; `compact_boundary` triggers a "re-read PLAN" note and the full digest (hub.py:193-198, 1990-1997); not during T-15..T-2 (1720-1730) | OK |
| A32 | Hub memory/CPU after 4 h (45 notes x160 lines, 500 ledger items) | Flat | Measured (P9): `state()` 11 ms, `props()` 5 ms, shared.json 1.6 MB dumped in 4 ms. Bounded: events 4,000, alerts 50, ovchat 40, traffic 30, guard log 200, bus.seen 5,000. `events.jsonl` grows on disk only | OK |
| A33 | /api/state payload and refresh rate | Small, debounced | 1.8 MB late in the day. Fetched every 6 s **and on every `shared` event** (each Chat line, tile, bot) with no debounce (index.html:823-824) | INEFF |
| A34 | Hotspot data used by the bus | Small | `_dir_loop` downloads the **entire** directory Dict (every agent entry, every `ver:` key, leftover `ack:`/`claim:`) every 5 s (bus.py:370-374, 431-436). Each Chat line re-uploads the whole 40x4,000-char ovchat (hub.py:1601-1607). Estimate: 50-100 MB/h per laptop | INEFF |
| A35 | An exception in the heartbeat | Restarted | `heartbeat()` is a bare task, not `hub.forever` (hub.py:4208-4219). If it dies, the other laptop marks every agent here OFFLINE after 120 s and drops them from "Team load" (2816) | RISK |
| A36 | Clock skew between laptops (one 3 min slow) | Detected; no effect on data | Version stamps are each writer's `time.time()`. A newer value from the slow laptop looks "older", gets treated as a race, and is **re-overwritten** (bus.py:407-416). Proven (P6; control without skew passes). Freshness tests also use remote timestamps (bus.py:126, 138; hub.py:860, 1346) | BUG |
| A37 | Clock skew: timing of steps | Same steps at the same instant on both laptops | The schedule is absolute epoch time, so each laptop's T-8 is offset by the skew. The preflight doesn't measure skew (1107-1171) | GAP |
| A38 | Git: d-builder / d-challenger vs d-platform | Separate trees; merges, not clobbers | Own worktrees and branches (hub.py:1514-1534); only d-platform on main; stash/rebase/restore need a click (38-49) | OK |
| A39 | Git on Samuel's laptop: s-data, s-tester, s-scout share ONE working tree | Testing a candidate never swaps the tree under the others | No worktrees for s-* (roster.py:208-286). `git checkout <branch>` isn't blocked (DANGER only blocks `--`/`.`/`-f`), so s-tester checking out a candidate swaps files under s-data | RISK |
| A40 | **Files one laptop writes that the other needs** (s-data's tables → d-platform; hand data → d-challenger/d-builder; d-* candidates → s-tester; releases → s-tester) | A defined path: shared store, branch push/fetch, or a mirror | **None.** Each laptop has its own clone (SUNDAY.md step 3). Only d-platform commits to main (roster.py:177-179); nobody is told to push or fetch branches. The portal data exists only on Samuel's laptop, yet every agent's prompt says "hand data are in {portal_data}" (hub.py:1803-1805). `fetch_file` covers human attachments only. The live sim ran both hubs on **one** repo (live_sim.sh:24-26), so this path was never exercised | GAP (critical) |
| A41 | A message bigger than the queue limit | Sender told at once | RequestSizeError goes to the dead letters, and the bounce is **non-waking** (bus.py:202-203, hub.py:335-338) | RISK (minor) |
| A42 | A message to an offline agent | Queued, delivered later; a typo errors at once | bus.py:122-135 | OK |
| A43 | Browser tab open for hours / two tabs | Stable | Events capped 1,500 per agent; SSE resync on overflow (index.html:802, 851-856) | OK |
| A44 | Clock loop blocked by a slow job | Steps fire on time | `Clock.loop` runs tick, guard, stalls, unanswered and **consistency (a Haiku call up to 90 s)** one after another (hub.py:3061-3069). A slow Haiku delays T-8 dispatch by up to 90 s | INEFF/RISK |
| B1 | Two agents give the humans contradictory numbers | The contradiction check flags it | Facts: the clock, live/active, 8 open notes, **local** agents' one-line task, 6 human items (hub.py:1233-1246). No summaries, no other-laptop agents, no ledger results. `disagreements()` only covers same-`question` ledger items (133-150) | GAP |
| B2 | An agent claims what it can't see (Dylan's agents on "hand data") | Its prompt reflects what's actually on that laptop | Every agent is told the hand data is in `portal_data` (hub.py:1803), which is empty on Dylan's laptop. Facts about rounds are "only from the portal watcher" (roster.py:56-58) | RISK |
| B3 | Agents wait on each other (d-platform needs s-tester's "correct"; s-tester needs d-platform's commit) | Non-blocking messages; guard fallback | Messages never block; guard cut-offs (hub.py:3159-3181). But the cross-laptop dependency has no transport (A40) and no SLA | RISK |
| B4 | A blocked / waiting agent | Surfaced to the lead | `situation()` lists idle and done only (hub.py:2818). A 'blocked'/'waiting' worker shows up only via its "Needs from a human" line, which is non-waking (2163) | GAP (minor) |
| B5 | A worker gets a clock task while doing a human instruction | The human's instruction first, then the clock task | Human items are urgent and listed as "override anything else" (hub.py:1640). Clock items queue behind; T-13/T-8 critical ones preempt (3123) | OK |
| B6 | A human instruction conflicts with the decision rules | Humans win; the conflict is stated | Human items go to the top of every digest. The guard still acts on observed state (3232-3240) | OK |
| B7 | A human instruction to ONE worker | That worker (and its lead) treat it as binding | `human_item("to d-builder: ...")` goes to **every agent on both laptops** as "override anything else", and stays among the last 8 for hours (hub.py:1887-1888, 550-556, 1638-1641) | RISK |
| B8 | The lead floods a worker | Loop guard at a higher limit for lead↔worker | The lead limit (45) never applies: it checks `endswith("overseer")` but the leads are `*-overview` (bus.py:154). Proven (P4) | BUG (minor) |
| B9 | Workers idle while critical work is queued | Idle agents pull | `queue_post` wakes one idle worker; end of turn pulls (hub.py:572-577, 1900-1905); IDLE NOW shows in the lead's brief (2818-2824) | OK |
| B10 | Humans send many messages quickly to the Chat | All batched into one turn, all answered | Batched; a preempt happens only if the turn is past 45 s (1542-1550). Tracking is cleared by any Chat text (B13) | OK/BUG |
| B11 | A message to an agent mid-turn | Agent-to-agent waits; humans and data preempt | Agent messages wait for the end of the turn (up to ~25 min with 5-min subagents); human messages and T-13/T-8 preempt | RISK (see B20) |
| B12 | A human message to a worker, unanswered | Reminded at 150 s; the Chat told at 6 min | Done (hub.py:1181-1195) | OK |
| B13 | A human asks the Chat while it's mid-turn on something else | Tracked until a reply that saw the question | `ov_log("Chat", ...)` clears `pending_q` on **any** Chat text, including mid-turn text written before the question was seen (hub.py:1602-1603, 1964). Proven (P2) | BUG |
| B14 | A worker answers at once ("working on it, ready 14:30"), then works 5 min in the same turn | No nag | `pending_q` is cleared only at the **end of the turn** (hub.py:1893-1894). At 150 s an **urgent** nudge arrives and preempts the turn (1184, 1542-1550), killing the running test. The worker then sends a second short reply. Proven (P1) | BUG |
| B15 | A human asks a worker on the OTHER laptop | Tracked, and the reply visible to the asker | `receive()` never adds to `pending_q` for workers (1555-1567), proven (P3). The remote agent's page shows only its brief, never its transcript (index.html agentHtml), so the asker can't see the reply | GAP |
| B16 | An agent spots a plan-level insight ("the whole field is limp-shoving; our plan is wrong") | A defined escalation path to both Chats and both humans, fast | No dedicated path. A worker's `notify_human` goes to its own lead (wake) (2175-2178). "Needs from a human" is non-waking (2163). The consistency check ignores strategy (1247-1255). Prompts say "talk to your human rarely, and only once" (roster.py:158-162). The only automatic path is `persistent_leaks` (480-499). Whether humans hear it depends on one lead's judgment | GAP |
| B17 | Agents repeat the plan's priors as facts | Priors labelled as priors | `record` requires n + method for results (455-456). Nothing checks Chat prose; the EVIDENCE_TABLE grades live only in docs | RISK |
| B18 | Clock tasks crowd out exploration | Room for the challenger/scout | Every window hands every worker a critical T-13 task (2602-2607), plus `every10` reminders (2632-2635). The challenger is protected from guard cuts (3293) | INEFF (by design) |
| B19 | Unanswered-tracking nags produce short, useless replies | Nag only real silence | B14 makes this happen to workers that already answered | BUG (=B14) |
| B20 | The T-8 handoff: s-overview's recommendation vs d-overview's question | The recommendation lands before the question is asked | Both fire at T-8 on both laptops (2609-2610). The recommendation is a normal agent message (non-urgent), so it waits behind d-overview's urgent T-8 turn | RISK |
| B21 | Samuel says yes, Dylan says no to the same 'Which bot?' note | Shown as a disagreement, and the rule plays (START_HERE "If you disagree... the rule's answer plays") | Approve calls `make_live` (1000-1003, 2517-2518). A later reject only flips the status (1007-1009) and never reverts `live`. With merge_note, the newer status wins. The live bot stays the approved one while the note may say "rejected" | BUG |
| B22 | A greenlight with a condition ("yes if the tester passes it") | Recorded, not live, until the condition holds | hub.py:994-999 | OK |
| B23 | No answer by the deadline | The rule plays; the author is told | expire_decisions (1317-1332); the guard posts a default note at T-7 (3324-3340) | OK |
| B24 | A permission prompt while the humans are away | Refused after a stated time | Refused after **120 s** but the text says "3 minutes" (hub.py:200 vs 2048-2049, 2061; START_HERE) | BUG (cosmetic) |
| B25 | A worker wants to tell a human something | Routed via its lead | notify_human from a worker goes to its lead (wake) (2175-2178) | OK |
| B26 | The lead promises "I'll tell you when..." | No promise without a wake source | Role text forbids it (roster.py:231-233, 316-318) | OK |
| B27 | A lead stuck in a long turn while a human waits | Human told why | At 360 s: "busy with a long turn" (1205-1207). For a limited agent it says "I've asked it again" | OK (wording) |
| B28 | A stale brief passed on as fact | Age shown | "brief last updated N min ago; may be stale" (1696-1700) | OK |
| B29 | A disputed or invalidated result cited for a switch | Blocked | Invalidation cascades and tells users (511-537); the digest prioritises it (1655) | OK |
| B30 | The clock moved by a human on one laptop | Both Chats told, old times void | `announce_change` + palert to the other laptop (2999-3017). But the receiving laptop does not remap `sent` keys (A5) | OK/BUG |
| B31 | The lead sets the clock without a human time | Refused | `human_in_turn` + a digit check (2227-2234) | OK |
| B32 | Dead code after the rename | none | `set_schedule` looks up `...overseer` (2236), always None | BUG (cosmetic) |

## BUG / GAP list, ranked by impact, with fixes

1. **GAP: no way to move files between laptops (A40, B2, B3).** This is the biggest structural risk. s-data's tables have to reach
   d-platform, round hand data has to reach d-challenger/d-builder, and d-* candidates and releases have to reach s-tester. None
   of these has a defined path. The rehearsal ran both hubs on one repo, so the problem never showed.
   *Fix:* (a) Add two hub tools on the existing Modal file store (`hub.file_store()`):
   `share_file(path)` returns an id and path, and `get_shared(id|path)`. Cap them at 50 MB and have them return the local path.
   (b) The portal watcher writes each round's `results.json` and `hands-first-1000.jsonl.gz` to the store under
   `round/<stage>/...`. Dylan's hub polls a `rounds` shared key and mirrors each file into its own `portal_data`
   (≈50 lines; hand data stays out of git).
   (c) Git rules in COMMON_RULES: d-builder and d-challenger `git push origin builder|challenger` after each
   candidate commit. s-* commit only under `theory/`, `analysis/` and `notes/` on branch `samuel` and push it. d-platform
   `git fetch && git checkout origin/samuel -- theory/out/` to take tables. s-tester `git fetch` and tests in
   `git worktree add /tmp/t-<sha> <sha>`, never `git checkout` in the shared tree (A39).
   (d) Add preflight rows: "git push works" (push a throwaway branch) and "shared store round-trip".
   (e) Rehearse once on two laptops with two clones.

2. **BUG: a transient 429 or "overloaded" error is treated as a subscription limit (A20, P10).** The agent sleeps ~5.5 min, a false urgent "usage limit"
   alert goes up, and if an API key is saved the agent switches to paid billing for the rest of the day.
   *Fix:* in `run()` (hub.py:1919), set `is_limit = self.usage.get("status") == "rejected" or re.search(r"usage limit|limit reached|resets? at", text, re.I)`.
   Everything else that matches LIMIT_RX is `transient` (wait 30-90 s, keep the auth). In `handle()`, return "error" rather
   than "limited" for `rate_limit`/`overloaded` unless a rejected RateLimitEvent arrived in the same turn.

3. **BUG: the unanswered-message nudge preempts a worker that already answered (B14, B19, P1).** It kills the running tool and
   produces a second, empty reply.
   *Fix:* in `handle()`, on the first top-level TextBlock of a turn with `human_in_turn`, clear
   `pending_q` entries older than `turn_started` at once (not at the end of the turn). In `watch_unanswered`, skip the nudge
   when `a.state == "working"` and the current turn started after `q["at"]`, and send the worker nudge with `urgent=False`.

4. **BUG: two humans give opposite answers on one decision (B21).** The approve wins silently: `live` stays set and a later
   reject doesn't revert it.
   *Fix:* in `human_act`/`update_proposal`, when a note already has `decided_by` from the other person with
   the opposite status, set `status="disputed"`. Revert `live` to `live.prev` if this note set it, and `alert_all` urgent
   in both Chats: "Samuel said yes, Dylan said no: the rule's answer plays at T-5 unless you agree." `expire_decisions` then treats
   "disputed" like "needs_call".

5. **GAP: no escalation path for a plan-level insight (B16).**
   *Fix:* add an `escalate(text, evidence_ids)` tool, open to any agent, at most 1 per agent per 20 min. The hub posts it verbatim to
   **both** Chats (`chat_ping`), wakes both leads with an urgent item, and opens a `kind="question"` note "Plan change?"
   with a deadline at the next T-8. Add one line to PROTOCOL: "If evidence says the plan's premise is wrong (the field
   plays differently from our model), escalate; that is never 'talking too often'."

6. **BUG: clock skew between laptops reverts newer shared values (A36, P6) and skews the timing of steps (A37).**
   *Fix:* (a) In the preflight, write `skew:<person> = time.time()` to the Modal Dict, read the other's, and compare with
   the round-trip time. Mark ❌ if the difference is over 3 s, with the fix "System Settings → Date & Time → Set automatically".
   (b) Make the version stamps skew-proof. In `set_shared`, use `ver = max(time.time(), self.shared_ver.get(key, 0) + 0.001)`,
   and in `_dir_loop`, drop the "older copy overwrote ours → re-send" branch (bus.py:414-416) for non-mergeable keys unless the
   value differs and the local write is less than 10 s old.
   (c) Freshness checks (`FRESH`, `stale`, palert 900 s) should use the local time the entry was **received**, not the
   remote's `seen`.

7. **GAP: Modal outage around the T-8 decision (A6, A8, A10, A11).**
   *Fix:* add an outage rule to DECISION_RULES and SUNDAY.md: "Link down at T-8 → Samuel reads s-overview's recommendation
   to Dylan aloud. Dylan's Chat decides with the rule on what Dylan's side has; if nothing new, the live bot plays." Let
   `queue_claim` fall back to a local claim when the claimant and the poster are on the same laptop. Show "Portal facts
   from HH:MM (link down)" in Dylan's situation. Add a Modal-down line to the worker prompts: "Modal down → run
   locally at reduced n and label it."

8. **BUG: a schedule that arrives from the other laptop re-fires marks already sent (A5, B30, P5).** These are duplicate dispatches
   (b0, p-checks, T-steps).
   *Fix:* key the marks by schedule-independent labels (`b20`, `s3-8`, `p14`) plus a "schedule generation" counter,
   not by `int(t0)`. Or, in `tick`, when the shared schedule's `start` differs from the last one seen, remap the
   sent keys exactly as `set_start` does. This still applies with the uncommitted clock rework: keys are still `{int(t0)}:...` and
   the remap is still only in `set_start`.

9. **RISK: a hung API stream after a network change silences a lead for ~13.5 min (A2).**
   *Fix:* use a per-role STALL_S: 4 min for the leads (they do no long tools by rule), and 6 min for workers in the crunch
   window with no tool in flight. When `bus.online` flips from False to True (a network change), interrupt any agent silent for
   more than 90 s.

10. **GAP: clock marks missed beyond their grace window are silently dropped (A17), and the clock loop is blocked by the Haiku
    check (A44).**
    *Fix:* run `consistency_check` as its own `hub.forever` task. In `tick`, collect unsent marks with
    `last_tick < at < now - grace` and send the lead one "MISSED while the hub was paused: ..." item (urgent if any is a
    T-13/T-8/T-3 step). Record `last_tick`.

11. **GAP: Codex jobs are lost on a hub restart (A14), and Codex `broken` stays set until a restart (A23).**
    *Fix:* persist `jobs` to `codex/jobs.json`. On start, mark the running ones failed and `add_item` to their agents:
    "Codex job X died with the hub restart; resubmit or use a subagent". Clear `broken` when a later `submit` finds
    `codex login status` OK (in a thread, 10 s timeout).

12. **BUG: a limited agent sleeps through a newly saved API key (A19).**
    *Fix:* sleep in 15 s steps. If `API_KEY_FILE.exists() and not self.use_api_key`, break, switch, and set `wait=0`. The alert
    text then reads "...save a key; agents pick it up within 15 s." Also add a top-level "Use API key now" button that does the same for all
    agents.

13. **BUG: the Chat's question tracking is cleared by any Chat text (B13, P2).**
    *Fix:* clear `pending_q` only for questions with `at < turn_started` of the turn that produced the text. Take `turn_started`
    from the Agent at the moment `handle()` sees the TextBlock.

14. **GAP: human messages to the other laptop's workers (B15, P3).**
    *Fix:* in `receive()`, when `from_kind=="human"` and the receiver is not a lead, append to `pending_q` exactly as
    `human()` does. Mirror each agent's last 20 top-level texts in its directory entry (or an `agentlog:<name>` shared key,
    20 x 600 chars), and show them on the remote agent page.

15. **GAP: the contradiction check sees only half the picture (B1).**
    *Fix:* add to the facts both laptops' agent summaries (from the `bus.directory`, first 300 chars) and the last 10
    ledger results with effect, se and n. Run it on Samuel's laptop only, posting to both Chats via `alert_all(chat=True)`, so two
    checkers don't report the same issue twice.

16. **RISK: an instruction to one worker becomes an override for every agent, for hours (B7).**
    *Fix:* store `to=<agent>` on human ledger items. In `team_digest`, show the item as an override only to that agent and its
    lead, and to the others as "(for d-builder)". Show only the items from the last 2 windows, or the ones a human pinned.

17. **RISK: the T-8 handoff race (B20).**
    *Fix:* move s-overview's recommendation step to T-9 (`DISPATCH["T9"]`, urgent). Let agent messages between the two
    leads during T-10..T-3 carry `urgent` (preempt), so d-overview reads the recommendation before asking.

18. **GAP: no Modal spend or app monitor (A27).**
    *Fix:* add a hub service that runs `modal app list --json` in a thread every 2 min. It shows running apps,
    container counts and ages in the Hub services panel, alerts at more than 80 containers or an app running over 45 min, and on Ctrl+C
    runs `modal app stop` for apps whose name has a prefix the hub sets (`AVALON_MODAL_PREFIX` exported to agents).

19. **INEFF: hotspot data used by the bus (A34), and the UI refresh storm (A33).**
    *Fix:* in `_dir_loop`, fetch one `index` blob (each writer keeps a `{key: ver}` map) instead of `d.items()`. Trim the
    directory `summary` to 600 chars. Share `ovchat` as an append delta (last 5 items) rather than all 40. In the UI, debounce
    `refresh()` to one per 1.5 s.

20. **RISK: loops that can die or hang (A35, A29, A26).**
    *Fix:* run the heartbeat via `hub.forever`, and wrap `get_context_usage` in `wait_for(..., 20)`. Make the long-turn notice
    wake the lead when `crunch()` is true.

21. **GAP: no recipe for the permanent loss of one laptop (A18).**
    *Fix:* put the portal key on both laptops. Add to SUNDAY.md: `./hub/start.sh samuel ~/avalon-finals --port 7778 --data
    ~/.avalon-hub-live/samuel-failover --namespace=-live --portal-data ~/portal-data-live --portal-base ... --portal-key-file ...`
    on Dylan's laptop (s-* agents then resume fresh from the PLAN files and the ledger).

22. **RISK: s-tester swaps the working tree under s-data and s-scout (A39).**
    *Fix:* give s-tester `worktree: True` in roster.py, plus the rule "test candidates in `git worktree add /tmp/...`".
    Add `git\s+checkout\s+(?!-b)\S+` to DANGER for agents whose cwd is the shared repo.

23. **Small fixes:** set `PAIR_LIMIT_LEAD` on `endswith("overview")` (P4, bus.py:154). Remove the `overseer` lookup (hub.py:2236).
    Set `APPROVAL_TIMEOUT=180` or change the text to "2 minutes" (B24). Make the dead-letter bounce wake the sender (A41). List
    `blocked`/`waiting` workers in situation() with their age (B4). Have watch_unanswered say "paused by a usage limit until HH:MM"
    for limited agents. Let `model_switch` revert to Opus after `resets_at` (A21). Persist `pending_q`/`note_pending` (A16).
    Check free disk in the heartbeat and alert under 2 GB (A25).
