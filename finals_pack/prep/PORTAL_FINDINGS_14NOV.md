# What the portal's code and our key say about the Finals (14 November, 15:30 Pacific)

Read-only research for team avalon. Sources: the scripts the public sign-in page serves (19 files fetched at 05:03,
re-fetched at 15:25: the site was **redeployed today**, two files changed, see section 9), the Next.js build
manifest, and GET requests with our key to the participant API. Nothing was posted, no `/api/admin` path was called,
no sign-in was attempted. Scratch copies (raw and pretty-printed) are outside the repo, in this session's temp
folder; they are not needed to act on this page.

How sure each finding is, in brackets:

- **[code]** stated in code that runs for participants (their pages, or the shared schema that every page parses
  the API with).
- **[default]** a default in the code that an organizer can override per competition or per round.
- **[organizer code]** in organizer-only screens that happen to ship in the same bundle. It shows what the platform
  can do, not what Sunday will use.
- **[measured]** what the API returned to our key today.
- **[guess]** inferred from a name or a shape; treat as a hypothesis.

---

## 0. What Sunday probably looks like, and how sure

1. **Table rules: 6-max, 6,000 chips, antes from the first level, 20 hands a level, 250-hand cap.** If the Finals
   competition's variant id is `finals` or `finals_community`, the organizer screen fills these in wherever a round's
   rules are empty: players 6, starting_stack 6000, hands_per_level 20, hand_cap 250, and 12 levels from 10/20/4 to
   2000/4000/800 (small blind, big blind, ante). That is 300 big blinds at the start, against 100 at the regional.
   [default; that the Finals uses one of these two ids is a guess, a strong one: no other variant id appears anywhere
   in the front end.] Payouts, decision time and time bank are **not** in the Finals defaults, so they stay at the
   platform's defaults (regional: 50/30/20, 1 ms, 100 ms bank) unless set. [default]
2. **Table rules are set per round, not per competition.** Every queued round carries its own `rules` object
   (players, stack, blinds, payouts, decision_ms, time_bank_ms, luck correction, resampling). The organizers can
   change any of them between rounds. The bot must read `state.config` at every table and hard-code nothing.
   [organizer code: the round-queue schema]
3. **Six scored rounds, 20 minutes apart, named "Round 1" to "Round 6" by weight.** The organizer's "add round"
   default (new in today's deploy) takes the next unused weight from 1 to 6, defaults the gap to 1,200 s, and
   applies the Finals table defaults. [organizer code, default] The regional ran exactly that: 4 practice rounds at
   +20/+30/+40/+50 minutes after the announcement, Round 1 at +60, then scored rounds 19.5 to 21.6 minutes apart,
   each preceded by a practice round 7 to 10 minutes before it. [measured]
4. **Round multipliers are visible, not secret.** A round's points count `score_multiplier ?? weight` times; the
   competition's `round_weighting` is `linear` (1..6, Bay Area), `powers_of_two` (1, 2, 4, 8, 16, 32) or
   `fibonacci` (1, 2, 3, 5, 8, 13; Pittsburgh). Both fields are in the API before any round starts. [code]
5. **`final_weight` is not a hidden weight. It names the final round, whose results are held.** If set to, say, 6,
   "Round 6 is the final round. Its results are held back until the organizers reveal them", and **the team's own
   bot health for that round is hidden too** ("Held from the team until you reveal it"). [code] Whether the Finals
   sets it is unknown (null at the regional). Since the feature exists and a prize ceremony follows, expect the last
   round to be dark. [guess, medium]
6. **The leaderboard can be held at any moment.** When held, standings return `held: true` and are hidden from
   participants and from the venue screens, and every round that completes after the hold has its results held as
   well. Release shows them again (with the final round's results if that round was held). [code] Not used at the
   regional. [measured]
7. **Culling, if switched on for a round, is a within-round early stop, not elimination from the event.** The
   round "looks" every N iterations; a team that is, at the given confidence, outside the top K for that round
   stops getting tables and is shown as "Culled at look k". Its round still scores (average over the tables it
   played). Nothing marks a team as culled at competition level. [code for the fields and labels; the statistical
   test itself is server-side: guess] Off at the regional. [measured] **Our watcher's "URGENT ... out of
   contention" line overstates this** (section 4).
8. **ICM luck correction and "resampling" exist per round.** Luck correction modes: `all_in_only`, or `legacy`
   (all-in and river). Off at the regional. [code, measured] Resampling (`resampling_continuations` 1-8,
   `resampling_threshold` 2-9) is a table rule whose meaning the code does not show. [guess: replaying the end of a
   table several times to cut variance]
9. **20 teams at 6 seats means 4 tables an iteration with 4 filler seats.** The help text says 100 teams at 8 seats
   make 13 tables an iteration, so seats are rounded up and filled with non-scoring copies of other bots. For 20
   finalists: 24 seats, 4 fillers, each iteration. [code for the rule; 20 teams is from HANDOFF]
10. **Announcements are invisible to our key.** `GET /announcements` and `GET /me` answer 403 "This account is not
    allowed to do that" with the API key; the website shows announcements as a banner, refreshed every 5 minutes,
    only in a signed-in browser. **Someone must keep the portal open in a browser on Sunday.** [measured]
11. **No Finals competition is visible to our key yet.** The key still lists one team, avalon in "Bay Area"
    (status open, private, variant `bay_area`). [measured, 15:25 Pacific]

---

## 1. Variants the front end knows

- No variant list is shipped for participants. Variant ids are free strings matching `^[a-z0-9_]{1,64}$`; a variant
  is `{id, title, rules}` (rules in Markdown), fetched per competition from `GET /competitions/<id>/variant`; the
  full list is admin-only (`/api/admin/variants`). File: `3k84k3sz2a56o.js` (was `15s9fq83pp39e.js`):
  `f_ = fn.string().regex(/^[a-z0-9_]{1,64}$/), fx = fn.strictObject({ id: f_, title: fn.string(), rules: fn.string() })`.
- The only ids named in code: `finals` and `finals_community`, both in the same test in `062ln3b073mtx.js` (was
  `298gx_04khy6u.js`):

  ```js
  function B(e, a) {
    return "finals_community" !== e && "finals" !== e ? a : { ...a,
      players: a.players ?? 6, starting_stack: a.starting_stack ?? 6e3,
      hands_per_level: a.hands_per_level ?? 20, hand_cap: a.hand_cap ?? 250,
      blinds: a.blinds ?? [[10,20,4],[20,40,8],[30,60,12],[50,100,20],[80,160,32],[125,250,50],
                           [200,400,80],[300,600,120],[500,1e3,200],[800,1600,320],[1200,2400,480],[2e3,4e3,800]] };
  }
  ```

  It is used in two places, both in the organizer's round queue: exported as `withFinalsTableRules`, and inside the
  new `newQueuedRound` (`rules: B(a, {})`). Nothing else in any file branches on these ids. **[organizer code]**:
  it fills the form an organizer submits; the server may apply its own defaults too (unknown).
- **What "community" means: undetermined.** Both ids get identical treatment. Competitions have a `visibility` of
  `public`, `private` or `admin_only`, so a public "community" edition of the Finals variant (for example a follow-on
  open competition) fits the shapes. [guess] It could also be a variant with a community-cards twist; nothing in the
  code says.
- Bay Area today: `GET /competitions/<id>/variant` returns `{id: "bay_area", title: "Bay Area", rules: <5.7 KB
  Markdown>}` (three hole cards, discard one and expose one after the flop). [measured]
- **Hints about variant mechanics, from the RedZone hand-replay format** (`0_2hpuit_-191.js`): every replay frame
  has `boards` (a list of boards), per-seat `exposed` and `discarded` cards, `pending` simultaneous choices,
  `spread.stakes` (per-seat amounts, with `picks`), a per-seat `counter` with a `public` flag, and `awards` (labels
  with seats). The replayer was built for multi-board hands, discard/expose, simultaneous choices, sealed amounts
  (bids or allocations), a second per-seat number, and split awards. [code for the shapes; that the Finals uses any
  of them: guess] This matches the families in `notes/pre/variants.md` and `TWIST_NOTES.md` (T14 two boards, T6/T7
  auctions, T19 sealed allocation).

## 2. The table-rules model

Per-round `rules` (`mg` in `3k84k3sz2a56o.js`, all optional and nullable, meaning "use the default"):

| Field | Type / bounds | Regional (Format page, 6 Nov) | Finals default in code |
|---|---|---|---|
| `players` | int | 8 | **6** |
| `starting_stack` | int | 2,000 | **6,000** |
| `blinds` | up to 100 `[sb, bb, ante]` | 10/20 start, no ante shown | **12 levels, 10/20/4 to 2000/4000/800** |
| `hands_per_level` | int | 20 | 20 |
| `hand_cap` | int | 250 | 250 |
| `payouts` | up to **5** entries, each an int or a `[int, int]` pair | 50/30/20 | not set |
| `payout_total` | int 1-100 | (100) | not set |
| `decision_ms` | int | 1 | not set |
| `time_bank_ms` | int | 100 (Getting started page) | not set |
| `icm_luck_correction`, `_mode` | bool; `legacy` / `all_in_only` | off | not set |
| `resampling_continuations` | int 1-8 | not shown | not set |
| `resampling_threshold` | int 2-9 | not shown | not set |

- **Payouts**: at most 5 paid places, so with 6 seats at most 5 of 6 can be paid. The `[int, int]` form is
  unexplained by the code: a range of places sharing points, or `[points, places]`. [guess] `payout_total` (1-100)
  is probably the points pool. [guess] Read `state.config.payouts` at minute 0.
- **Antes**: the third number is called ante; whether it is per player or a big-blind ante is decided by the
  engine, not the portal. Check the kit's engine. Level 12 is reached at hand 221, before the 250-hand cap.
- **Fillers**: "With 100 teams and eight seats per table, one iteration has 13 table games" (the iteration help
  text in `062ln3b073mtx.js`), so tables are filled up with fillers; the 6 Nov Format page: "Short tables use bots
  not already seated as fillers; their finishes never score for their teams." RedZone seats carry `filler: true`.
  [code] Fillers still take places at the table, so a scoring bot can finish behind one. [guess, follows from the
  rule]
- **Time limits and bank**: per round (`decision_ms`, `time_bank_ms`); 1 ms and 100 ms per table at the regional
  (Getting started capture in `prep/docs/portal_getting_started.md`). No Finals value in code.
- **Iterations and blocks**: a scored round runs `iterations` (1-20,000) in blocks (`iterations_per_job` 1-500, now
  defaulting to 10). Bay Area: 20,000 iterations a scored round, 7 per block, 2,858 blocks; practice 1,000 to
  12,500. [measured] With 20 teams that is 80,000 tables a round, 20,000 per team (if the organizers keep 20,000).
- **Compute allocation** (organizer code): rounds can carry `allocation_hosts` (now defaulting to 25),
  `allocation_slots_per_host` (5), a strategy `demand` / `score_and_demand` / `copy_demand` and copies per host; the
  worker schema has modes `local_bots` and `bot_hosts`, `warm_bots`, and a `cpu_pinned` flag. Bots may run as warm,
  long-lived copies on dedicated bot hosts. [organizer code; effect on a bot: guess, likely none beyond the
  documented sandbox]

## 3. Scoring and ranking

- **Round weight** = the round's number (scored rounds need a weight 1-100; practice rounds take none: "Scored
  rounds need a weight; practice rounds take none."). Rounds are labelled `Round ${weight}`. [code]
- **Multiplier**: `roundMultiplier(e) { return e.score_multiplier ?? e.weight; }` (`3qrxkfy__l_37.js`). Options:
  "Linear (1, 2, 3, 4, 5, 6)", "Powers of two (1, 2, 4, 8, 16, 32)", "Fibonacci (1, 2, 3, 5, 8, 13)". [code] Bay
  Area: `round_weighting: linear`, every round `score_multiplier` = weight. [measured]
- **Total** = sum over scored rounds of average points a table × multiplier (the team page computes
  `average_points * roundMultiplier(...)` and sums). [code]
- **`final_weight`** (1-100, nullable) and **`final_revealed_at`**: `isFinalRound(round) = scored && weight ===
  final_weight`; until revealed, that round's results are held ("Results are held back until the organizers reveal
  them.") and its bot health is held from the team ("Held from the team until you reveal it"). The organizer picks
  None or Round 1-6 (`finalRoundOptions`). File `3kfo3k-mohgkk.js`, module 31382. [code] **This corrects
  `docs/FINALS_PLAYBOOK.md`, `FIRST_PROMPT.md` and the watcher's docstring, which call it "a final weight revealed
  late"**: the weight is known; the results are what is hidden.
- **Tie-break**: standings carry `tie_broken` and `previous_rank`. The rule text (6 Nov Format page): countback on
  the weighted share of 1st places, then 2nd places, and so on; nothing by chance. Within one round's results, equal
  averages share a rank. [code + captured page]
- **Margin**: round results carry `margin_of_error` (95%), shown as "± x". [code]
- **Disqualified**: "Disqualified. This team is excluded from later rounds and has no standing rank." [code]
- **ICM luck correction**: "ICM luck correction: all-in only" or "Legacy ICM luck correction: all-in and river".
  [code] Exact maths is server-side. [guess: realised all-in outcomes replaced by equity-weighted ICM values]
- **Resampling**: see section 2. [guess]
- **Forfeit**: no active bot at the snapshot: "No active bot at the snapshot. This round scores zero." [code]

## 4. Culling

Fields (`3k84k3sz2a56o.js`):

```js
contender_places: int 1-100, look_iterations: int 1-20000, max_looks: int 1-100, cull_confidence: int 50-99
// on a round, once running: + looks, active (nullable), culled, settled, minting
// on each team's round result: contender: bool, culled_at_look: int >= 1
```

- Label shown on rounds: `Contender culling: top ${contender_places}, looks every ${look_iterations} iterations, at
  most ${max_looks}, ${cull_confidence}% confidence` (`062ln3b073mtx.js`). All four are set together or not at all
  ("Contender culling needs places, iterations per look, max looks and confidence."). [code]
- On the results table a culled team shows "Culled at look k" where a forfeited team shows "Forfeited"; the progress
  bar reads "N / M blocks **so far**" while `minting` is true, so a culled round creates blocks as it goes rather
  than a fixed number. [code]
- **Meaning** (from the shapes): within one round, every `look_iterations` iterations the server checks which teams
  can still finish in the top `contender_places`; those outside it at `cull_confidence` stop being dealt tables;
  after `max_looks` or once `settled`, the round ends. The culled team keeps its average from the tables it played.
  [guess on the test; the per-round scope is code: every culling field lives on a round or a round result, none on
  the competition or the team]
- **What a culled team still does**: plays every later round as normal (nothing carries over). [code, by absence]
  Whether its bot is used as a filler for the remaining tables of that round: unknown.
- **For us**: being culled in a round only means the round decided early that we would not be top K in it. It
  does not change our standing rules. `scripts/portal_watch.py` line 576 says "URGENT: ... the portal marks us out of
  contention"; that wording overstates it (lead's call whether to change it; this session did not touch it).
- Contenders' remaining tables are among stronger bots only, so their averages after a cull come from a harder
  field. [guess] Not used at the regional (`culling: null` on every round). [measured]

## 5. The leaderboard

- Competition fields: `leaderboard_held` (bool), `leaderboard_held_at`, `leaderboard_top` (1-30, nullable),
  `leaderboard_page_seconds` (5-60; Bay Area 8). [code, measured]
- Held: the organizer's button "Hold leaderboard" ("Hide every leaderboard from participants and the screens");
  participants see "The leaderboard is held until the organizers reveal it."; standings return `held: true`; every
  round whose `completed_at` is after `leaderboard_held_at` shows "Results held". Release: "Participants and the
  screens will see the standings again, with Round N's results." [code]
- Participants read `GET /competitions/<id>/standings?public=true` and `GET /tournaments/<id>/results?public=true`
  (the site adds `?public=true` for the teams view). [code]
- `leaderboard_top` and `leaderboard_page_seconds` look like settings for the venue screens (rows shown, seconds a
  page). Whether `leaderboard_top` also cuts the participants' view to the top N is not visible. [guess]
- Chat "standing cards" cannot be made while the leaderboard is held. [code]

## 6. Uploads, the active bot, machines

- Upload: `POST /teams/<team>/submissions?filename=...` with the zip as the body; the browser gives it 120 s.
  Statuses `validating`, `ready`, `rejected`, `cancelled`; a check queue position (`check_position`) and attempts;
  failure codes `variant_unavailable`, `sandbox_unavailable`, `storage_unavailable`, `worker_timeout`,
  `worker_error`. [code] Limits on the 6 Nov Getting started page: 50 MB uploaded, 200 MB unpacked, 1 MB of code in
  `agent.py`; the upload test is a heads-up match of up to 20 hands with no time bank.
- Cooldown: `submission_cooldown_seconds` per competition (0-86,400; Bay Area 30). [code, measured]
- Active: the team's `active_submission_id`, set separately from the upload; "Each round freezes its own snapshot
  of every team's active bot at the start." A competition-wide `frozen` flag stops uploads and changes. [code +
  captured page]
- Team object today: `machine: null`, `locked_for_members: true`, `openai_credits_urls` and a new
  `third_openai_credits_url` (today's deploy). [measured] Teams can have a build box (`machine: {name, host,
  opens_at}`) and the competition a `machines_open_at`; the Getting started page: "We need your SSH public key so
  you can log in to your team's build box, where you can build and test your bots in an environment similar to the
  tournament's." [code] Expect a build box and OpenAI credits for the Finals. [guess, medium] What
  `locked_for_members` locks is not shown (probably membership changes). [guess]
- The API key: "lets an assistant or script act as you on every team you are on: read the team and its build
  machine, register SSH keys and upload bots. It expires 30 days after it is made." Ours expires 6 December.
  [code, measured]

## 7. Text for participants about the Finals

- **None in the shipped code.** No date, venue, schedule, number of rounds or table count appears in any of the 21
  files. The Format and Getting started pages are separate route chunks that are only served after sign-in (the
  page URLs answer 307 to the sign-in page; the build manifest lists only `/_app` and `/_error`; no script loads
  chunks lazily). Their text must be read in a signed-in browser (section 10).
- Navigation for participants: Dashboard, Your team, Rounds, **Getting started** (emphasised), **Format**, plus
  Chats and RedZone (a live replay of selected hands, with commentary). Signed-in users land on Getting started
  until the variant is announced. [code]
- Help texts: iteration ("One shuffle of all participating teams into tables...") and block ("A batch of iterations
  assigned to one worker..."). [code]

## 8. Our participant access today (15:25 Pacific)

| GET | Answer |
|---|---|
| `/auth/api-key` | 200: key valid to 6 Dec; one team: avalon, competition "Bay Area" |
| `/competitions` | 200: one competition, "Bay Area" (open, private, `bay_area`, linear, cooldown 30, `final_weight` null, `leaderboard_held` false, `leaderboard_page_seconds` 8) |
| `/competitions/<bay>` | 200, same object |
| `/competitions/<bay>/variant` | 200, Bay Area rules |
| `/competitions/<bay>/tournaments` | 200: 15 rounds (9 practice, 6 scored), all `culling: null`, `icm_luck_correction: false` |
| `/teams/<avalon>` | 200 (fields above) |
| `/announcements` | **403** forbidden for the key |
| `/me` | **403** forbidden for the key |

No Finals competition and no announcement are visible to the key. No hidden ids were probed.

Bay Area timeline (UTC, 7 Nov): announced 02:20:59; practice 02:41, 02:51, 03:01, 03:11; Round 1 03:21:07, then
03:40:38, 04:02:15, 04:23:04, 04:43:05, 05:03:13. Scored rounds took 5:56 to 7:32 to complete (148 entries, 20,000
iterations). Practice between scored rounds started 6.6 to 10 minutes before the next round.

## 9. Today's redeploy

Re-fetching the sign-in page at 15:25 Pacific found new names for two files: `15s9fq83pp39e.js` became
`3k84k3sz2a56o.js` (adds `third_openai_credits_url` to the team schemas) and `298gx_04khy6u.js` became
`062ln3b073mtx.js` (adds `newQueuedRound`, with Finals table defaults, weights 1-6 in order, 1,200 s gaps, 10
iterations a block, 25 hosts × 5 slots). Every other string is identical. The organizers were preparing the Finals
round queue today. [measured]

## 10. Only visible in a signed-in browser (for Dylan to open; this session did not)

| Page | What it should show |
|---|---|
| Any portal page, signed in | The **announcements** banner (the API key gets 403 on `/announcements`). On Sunday keep one browser tab signed in. |
| `/tournament/competitions/5f8be52b-8038-4c43-a0fa-971abcacec1b/format` (Bay Area, today) | Whether the Format page template now mentions culling, luck correction, a final round or a held leaderboard. It is rendered from settings, so today's version shows the template's current wording. |
| Same, `/start` | Current Getting started text: build box, limits, time bank, hand history. Compare with `prep/docs/portal_getting_started.md` (6 Nov). |
| The dashboard `/tournament/` | Whether a Finals competition is already listed for the account (the key may lag behind the account). |
| On Sunday: the Finals' `/format` and `/start` | Players, stack, blinds and antes, payouts, schedule and weights, any culling, luck correction or final-round text. |

---

## Confirm at minute 0, and where

| Check | Where |
|---|---|
| The Finals competition id and its variant id (`finals`? `finals_community`?) | `GET /competitions` with the key (the watcher follows the key by itself); portal dashboard |
| `round_weighting` (linear, powers of two or Fibonacci) and `final_weight` | `GET /competitions/<id>`; Format page |
| `leaderboard_held`, `leaderboard_top` | `GET /competitions/<id>` |
| `submission_cooldown_seconds`, `frozen`, `machines_open_at` | `GET /competitions/<id>` |
| Players, stack, blinds and antes, hands a level, hand cap, payouts, `decision_ms`, `time_bank_ms` | The kit's `state.config` and `RULES.md`; Format page |
| Whether the ante is per player | The kit's engine source |
| Each round's `culling`, `icm_luck_correction(_mode)`, `iterations`, `score_multiplier` | `GET /competitions/<id>/tournaments` as soon as practice 1 starts, and again for every scored round (rules are per round) |
| Resampling settings, if any | `state.config` (keys `resampling_*`), kit docs |
| Announcements | A signed-in browser tab |
| Build box and credits | Team page (`machine`, credits links); Getting started |
| The final round's health is hidden | If `final_weight` is set: the bot for that round must already have run cleanly in an earlier round or practice; we will not see its errors |
