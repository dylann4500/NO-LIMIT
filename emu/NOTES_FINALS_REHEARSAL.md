# Finals rehearsal tonight (14 Nov): how to run it

The emulator now plays the Finals table, against a fixed field of 17 bots, with avalon as the only live team. avalon
works from any folder: a human uploads zips on the mock portal's page, and `finals_pack/scripts/portal_watch.py`
reads rounds, results and hand files from the mock portal the same way it reads the real one. No simulated AI team
is started, no sandbox, no Modal secret.

## 1. Start it (real clock)

Use the Python in `nolimit-live/prep/.venv`. It has the Modal client (1.6.3) and is signed in. There is no
`nolimit-hub/prep/.venv` on this laptop, so the path in the brief does not exist.

Terminal 1, the event (it sets everything up, then waits for the start signal):

```bash
cd /Users/dylan/Documents/GitHub/nolimit-hub
PY=/Users/dylan/Documents/GitHub/nolimit-live/prep/.venv/bin/python
$PY emu/rehearsal.py --run dress1 --table finals --variant flop_pass_holdem \
    --field-file emu/fields/finals_dress.json --weights 1,2,3,4,5,6 --cooldown 30 \
    --practice-iterations 1000 --round-iterations 5000 --wait
```

Wait for `READY` (about 10 s). Then, in terminal 2, the mock portal:

```bash
cd /Users/dylan/Documents/GitHub/nolimit-hub
/Users/dylan/Documents/GitHub/nolimit-live/prep/.venv/bin/python emu/portal_server.py --run dress1 --port 8790
```

Then the start signal, from any terminal (`now` = 20 s from now; or a clock time such as `21:30`):

```bash
/Users/dylan/Documents/GitHub/nolimit-live/prep/.venv/bin/python emu/rehearsal.py --run dress1 --start now
```

- The clock: a 60-minute build; practice rounds at minutes 20, 30, 40 and 50; scored rounds 1 to 6 at minutes 60, 80,
  100, 120, 140 and 160 (weights 1 to 6); a practice round at minutes 70, 90, 110, 130 and 150 (10 minutes before
  each later scored round). Upload cooldown 30 s. The run ends by itself once Round 6 is delivered, at about
  minute 162.
- Round sizes, as the real Format page counts them: **1,000 iterations a practice and 5,000 a scored round**.
  Every entry plays one table an iteration, so avalon gets 1,000 and 5,000 tables. 18 entries (17 + avalon) fill
  3 tables an iteration, so that is 3,000 and 15,000 tables in all. Measured on Modal: 114 s and 219 s
  (section 6).
- Rounds play on Modal (19 shard containers plus 1 merge container, never more than 20; see section 6). To play on
  this laptop instead, add `--local-rounds`. If Modal fails, the rehearsal falls back to local play by itself.
- Order matters. Start `rehearsal.py` first, then the portal. Never restart `rehearsal.py` with the same `--run`
  after uploads have begun: it rebuilds `emu/runs/<run>/avalon/`, which holds the portal's uploads and state. To
  start over, use a new run name.
- Ports: 8765 (the old default) is held by a local whisperx service on this laptop, and 8770 by macOS. Use 8790.

## 2. The mock portal, for the human and for the watcher

- Pages: `http://127.0.0.1:8790/tournament/` on this Mac. Other machines on the network or Tailscale use
  `http://<this Mac's IP>:8790/tournament/`; the portal prints the address at start (it listens on 0.0.0.0).
- Sign in: `http://127.0.0.1:8790/tournament/login`, then paste the key from the key file.
- **Key file: `/Users/dylan/Documents/GitHub/nolimit-hub/emu/runs/dress1/portal-key`** (mode 600). It is the
  run's own mock key and is git-ignored. A copy is in `emu/runs/dress1/avalon/portal/api-key`.
- API base for the watcher: `http://127.0.0.1:8790/tournament/api`.
- Watcher, run from the team's rehearsal folder (its own copy of `finals_pack/`):

  ```bash
  python3 scripts/portal_watch.py --base http://127.0.0.1:8790/tournament/api \
      --key-file /Users/dylan/Documents/GitHub/nolimit-hub/emu/runs/dress1/portal-key
  ```

  Do not point a watcher at the mock from the real `finals_pack/`. The watcher sees a new competition id, archives
  that folder's `data/rounds/` and resets its `state/`, which would mix rehearsal data into tomorrow's folder.

## 3. Minute 0: the kit, the Format page, the "announcement"

Before the start, the Format page shows "To be announced". Uploads are refused (409 "Uploads open when the event
starts...") and `GET /competitions/<id>/variant` answers 404, as on the real portal.

At minute 0:

- **Format page** `http://127.0.0.1:8790/tournament/format` shows the variant (titled "San Francisco":
  flop_pass_holdem), the Finals table (6 players, 6,000 chips, blinds and antes 10/20/4 to 2000/4000/800, 20 hands
  a level, hand cap 250, 50/30/20, 1 ms plus a 100 ms bank), the schedule and the 30 s cooldown.
- **Starter kit**: a "Download the starter kit" link appears at the top of the Format and Getting started pages
  (`http://127.0.0.1:8790/tournament/kit.zip`, a zip with one top folder `starter-kit/`). The same kit is also in
  `emu/runs/dress1/avalon/kit/`. It is the mock kit for flop_pass_holdem at the Finals table. Its engine defaults,
  README and `poker-agent play` (which fills 6 seats) all use the Finals table.
- **"Announced"** means the competition object gets `variant` and `variant_announced_at` (the start time), and
  `GET /competitions/<id>/variant` returns `{id, title, rules}`. The watcher reports "THE VARIANT IS ANNOUNCED",
  saves `state/variant.md` and takes that time as minute 0. A notice is also written to
  `emu/runs/dress1/avalon/inbox/`. There is no banner on the pages (the real portal has one, in a browser only).

## 4. Uploading

On the Team page (`/tournament/team`), choose a .zip with `agent.py` at its root and press Upload. The upload test
runs at once: heads-up against check-or-fold, up to 20 hands, 1 ms, no time bank, Finals stack and antes, reject at
more than 10% failed decisions. It takes about 2 s. **An upload that passes becomes the active bot by itself**,
unless a newer upload is already active, as the Finals Getting started and team pages say. A "Make active" button
switches back to any earlier ready upload. The portal copies the active bot to `emu/runs/dress1/avalon/submission/`,
and each round snapshots that folder when it starts. A second upload within 30 s gets 429 with Retry-After. A team
with no active bot at a round's start forfeits it with 0 points (results show `forfeited: true`).

API equivalents (the same paths as the real site): `POST /api/teams/<team>/submissions?filename=x.zip` with the zip
as the body, `PATCH /api/teams/<team>` `{"active_submission_id": ...}`.

## 5. Stopping everything

1. Terminal 1 (rehearsal): Ctrl+C. Or `kill <pid>`, with the pid from `emu/runs/dress1/event.json` (`"pid"`). It
   also stops on its own after Round 6.
2. Terminal 2 (portal): Ctrl+C.
3. Modal: `/Users/dylan/Documents/GitHub/nolimit-live/prep/.venv/bin/modal app list`. If a `nolimit-emu-rounds`
   app is still listed as running or ephemeral, run `.../modal app stop --yes <ap-...>`. A rehearsal that exits
   normally closes its app.

Never stop these with `pkill` or `killall`: the team's own processes run on this laptop too.

## 6. Speed, size and cost (measured tonight)

All rounds below are 18 entries at the Finals table on flop_pass_holdem. Wall time runs from the round's start
(upload snapshot) until results and avalon's downloads are on this Mac and delivered.

| Where | Round | Iterations (= avalon's tables) | Tables in all | Wall time | Tables/s |
|---|---|---|---|---|---|
| **Modal, 19 shards + 1 merge** | **practice** (first round of the run: image layers rebuilt) | **1,000** | **3,000** | **114.1 s** | 26 |
| **Modal, 19 shards + 1 merge** | **scored** | **5,000** | **15,000** | **218.5 s (3 min 39 s)** | 69 |
| Modal | practice (first round of its run) | 334 | 1,002 | 92.4 s | 11 |
| Modal | scored | 1,667 | 5,001 | 124.9 s | 40 |
| this laptop (`--local-rounds`, 4 processes x 4 tables) | practice | 100 | 300 | 24.9 s | 12 |
| this laptop | practice | 334 | 1,002 | 80.7 s | 12.4 |
| this laptop | practice / scored, 1,000 / 5,000 iterations | 1,000 / 5,000 | 3,000 / 15,000 | about 4 min / 20 min (estimated, not run) | 12.4 |

- The bold rows are tonight's sizes, run as throwaway run `modaltime_full`. In the 5,000-iteration round, avalon's
  hand files were **65.9 MB** (full, 5,000 tables) and 13.1 MB (`-first-1000`, 1,000 tables). Both pass the kit's
  validator. Rare failed decisions appeared: 11 of about 13 million, spread over 5 teams including the kit's
  min_raiser (avalon 1 of 387,870). They look like timing noise on Modal's CPUs at the 1 ms limit, not bot faults.
  There were none at the smaller sizes.
- About a minute of each Modal round is overhead: container start-up and the merge. Playing 5,001 tables took
  25 to 30 s per container.
- Two Modal fixes went in tonight. (1) Each container runs 4 round processes, because one process uses one core.
  (2) For a fixed field, only avalon's hand files are merged, and they are returned directly instead of being
  written to the Modal volume. Before the fixes, a 5,001-table scored round had not finished after 12 minutes,
  because writing every team's downloads to the volume ran at about 1.5 MB/s.
- **Recommendation: Modal** (the command above). At the real sizes, a practice takes about 2 minutes and a
  scored round under 4, well inside the 10 minutes between round starts. **Do not use `--local-rounds` at these
  sizes**: a 5,000-iteration round would take about 20 minutes on this laptop and overlap the next round. If
  Modal is down, use `--local-rounds --practice-iterations 334 --round-iterations 1667`: about 80 s and 7 minutes,
  with avalon getting 334 and 1,667 tables a round. The automatic fallback (Modal failing mid-event) plays the round at its
  full size locally: a scored round would then take about 20 minutes. If that happens, restart under a new run
  name with the smaller sizes. Local rounds raised the load average to about 4.5 (15 cores)
  while they ran.
- Container cap: `EMU_MAX_CONTAINERS` (default 20) caps the whole round app: `play_shard` gets 19 and
  `merge_round_local` 1. This holds within one rehearsal, which uses one app for the whole event. Two rehearsals at
  once would each take 20, so run only one.
- Cost on Modal (an estimate from list prices, not a bill): a shard container is 8 CPU and 16 GB, about
  $0.00014 a second. At the real sizes, a round holds about 19 containers for 2 to 3.5 minutes, which is roughly $0.3
  a practice and $0.6 a scored round. The evening's 9 practices and 6 scored rounds come to roughly $6 to $8. Check the
  workspace's usage page for the real figure. `--local-rounds` costs nothing on Modal.

## 7. The field (`emu/fields/finals_dress.json`)

These are the 15 release zips of today's timed run (`/Users/dylan/avalon-dress/releases`, copied with their
`VERSIONS.md` into `emu/runs/field_dress/`, every sha256 matching `VERSIONS.md`; the originals are untouched), plus
the kit's two examples. Latest versions of each design come first:

Sim D3 (v14), Sim A5 (v13), Sim B4 (v15), Sim C3 (v12), Sim Base11 (v11); then Sim Base9 (v9), Sim B3 (v10),
Sim D2 (v7), Sim A2 (v4), Sim C1 (v8), Sim Base6 (v6), Sim D1 (v2), Sim A1 (v3), Sim B1 (v5); weak teams:
Sim Placeholder (v1), Sim Check Or Fold, Sim Min Raiser.

All 17 pass the upload test at the Finals table. All played rounds of 100 to 5,000 iterations, with 0 failed
decisions up to 1,667 iterations and at most 6 in 782,685 at 5,000 (section 6).
None was dropped. The rehearsal re-checks every fixed bot before READY and drops, loudly, any bot that fails.
Zips are extracted into `emu/runs/<run>/field/<team>/`. Each opponent keeps the same bot all event.

## 8. What does NOT match the real Finals

- **The field**: 17 of our own designs plus the kit examples, not 20 other teams. Opponents never change their bots
  (real teams upload all event). 18 entries make 3 full tables, so **no filler seats** occur. The real Finals has
  21 teams, which makes 24 seats with 3 fillers. Filler seating itself works and is tested (17 entries give 1
  filler per iteration).
- **The variant** is our mock flop_pass_holdem, not the real Finals variant.
- **Round sizes**: 1,000 iterations a practice and 5,000 a scored round, so avalon gets 1,000 and 5,000 tables,
  as the real Format page describes. The real scored rounds are "at least" 5,000 iterations, and Bay Area ran
  20,000, so the real ones may be bigger, with narrower margins.
- **Results timing**: results land about 2 minutes (practice) and 3.5 minutes (scored) after a round starts on
  Modal. Bay Area's took 6 to 7.5
  minutes. The real portal also has a compute gap after the last round.
- **Format page text**: the mock shows the Finals table (6 x 6,000, antes). As of today, the real Finals Format page
  still shows the template's 8 players, 2,000 chips, 10/20 and no ante (`finals_pack/prep/PORTAL_SIGNED_IN_14NOV.md`).
  Read `state.config` on the day.
- **Payouts** are fixed at 50/30/20. A real round may draw payouts per table.
- **No hold, final round, culling, luck correction or resampling.** `final_weight` is null and `leaderboard_held`
  false throughout.
- **Announcements**: no banner. The real portal shows announcements only in a signed-in browser (the key gets 403).
  The mock answers `/me`, where the real portal answers 403 for a key; the watcher uses `/auth/api-key` first
  anyway.
- **The upload test** runs on this laptop under the same conditions (2 seats, 20 hands, 1 ms, no bank). The mock
  enforces 50 MB, at most 1,000 zip entries, `agent.py` at the root, and no poker_engine or pokerkit imports. It
  does not enforce the startup allowance, the 200 MB unpacked limit or the 1 MB `agent.py` limit.
- **Decision timing** is measured on Modal's or this laptop's CPUs, not on the organizers' workers.
- **Round names**: the mock labels rounds "Practice round N" and "Scored round N (xW)". The real portal has no
  labels (the watcher names the stages itself: Practice 1 to 4, Round 1, Round 1.5, ...).
- **One team only**: the mock portal serves avalon alone. There is no build box, no credits, no chats, no RedZone and
  no Members tab.
- **Hand downloads**: the mock answers both the real shape (`/teams/<team>/tournaments/<round>/hands`, with
  `?tables=1000` for the first-1,000 file) and its older one (`/tournaments/<round>/hands?subset=first-1000`). The
  real portal's file might be served from a signed storage link. The files are in the real format and pass the
  kit's validator.
- **A forfeited avalon** still fills its seats with a check-or-fold placeholder, scored 0 and flagged `forfeited`.
  On the real portal a forfeiting team plays no tables.
- **Overlapping rounds**: if a round is still running when the next one starts, both run at once. The real portal
  queues them. This happened in tonight's fast-clock test, with rounds 30 s apart, and worked; the merges then wait
  for each other (one merge container). At the real clock, rounds finish in 2 to 3.5 minutes, so it should
  not happen.

## 9. What changed in `emu/` tonight

- `tables.py` (new): the regional and Finals table rules, in one place.
- `variants/make_kit.py`: `--table finals` (`patch_format`): the kit's TableRules defaults, the CLI, the README and a
  6-seat sample.
- `rehearsal.py`: `--table`, `--field-file` (fixed bots, checked before READY), `--local-workers` and
  `--local-concurrency`, `--shards` default 19, full table rules in every round's field file, a self-check that the
  kit's defaults match the table, `pid` and weights in `event.json`.
- `portal_server.py`: auto-activation of a passing upload; uploads refused before the start; the variant
  endpoint and `variant_announced_at`; the real hand-download path; the kit download; the per-run key file; the
  real portal's competition fields.
- `modal_rounds.py`: the container cap (`EMU_MAX_CONTAINERS`), 4 processes per container, and an avalon-only merge
  returned directly.
- `tournament.py`: `merge --download-teams`.
- `teams/run_team.py` and `portal/pages/*.md`: the table rows and player counts filled per table.
- `test_variant_install.py`: `... flop_pass_holdem finals` checks the Finals table end to end (both tables pass).
- `fields/finals_dress.json` (new). The bots themselves stay in git-ignored `emu/runs/`.

## 10. Tonight's proof runs (all stopped; output under git-ignored `emu/runs/`)

- `stage1`: a local 300-table Finals practice through the rehearsal's own `play()`. 6-seat tables, antes from
  10/20/4, 6,000 stacks, 0 failed decisions. avalon's download passes the kit's validator.
- `modaltime_full`: on Modal, a 1,000-iteration practice (3,000 tables) took 114.1 s and a 5,000-iteration
  scored round (15,000 tables) 218.5 s. avalon's full file was 65.9 MB, and both of its files pass the validator.
- `localtime`: a local 1,002-table practice took 80.7 s. `modaltime3`: on Modal, a 1,002-table practice took
  92.4 s and a 5,001-table scored round 124.9 s. avalon's 1,667-table download passes the kit's validator.
- `e2e` (local rounds) and `e2em` (Modal rounds), at `--scale 0.05`. Before the start, uploads were refused and
  the variant endpoint answered 404. At minute 0, `kit.zip` was downloaded after signing in, the kit's
  `examples/min_raiser` was zipped and uploaded the way the Team page does it, the upload passed and became active
  by itself, and 4 practices, 2 scored rounds and 1 practice in between were played. Then
  `python3 -I scripts/portal_watch.py --once --base http://127.0.0.1:<port>/tournament/api --key-file
  emu/runs/<run>/portal-key`, run from a copy of `finals_pack/` without `prep/`, printed "Portal OK: team avalon
  ..., competition "No Limit rehearsal (e2em)"", 7 rounds finished, "Active bot: avalon_v1.zip", and saved
  results.json, round.json, hands-full and hands-first-1000 for every round. It also announced the variant.
