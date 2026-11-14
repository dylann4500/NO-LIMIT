# The portal's "Tournament format" and "Getting started" pages, Boston regional (extract)

Source: two browser printouts in `~/Downloads/` (`Tournament format - NO LIMIT ’26 (1).pdf`, 5 pages, printed
11/9/26 18:14; `Getting started - NO LIMIT ’26 (1).pdf`, 11 pages, printed 11/9/26 18:11). Both are pages of
`pokerbot.sequoiacap.com/tournament/competitions/abb5539f-60...` with "Boston" in the page header. The Format page
shows a "BUILD TIME 59:56" counter, so it was printed seconds after the Boston build hour began (9 November 2026).
Below: our own words, exact numbers. "F" = Format page, "GS" = Getting started page.

## 1. Which event and variant

- Boston regional of NO LIMIT '26 (F header and heading "Boston"; GS header "Boston"). Team limit: **2 members** (F).
- Variant (F): no-limit hold'em, two hole cards, but the **flop is bought at a sealed auction** paid in a separate
  currency, **flop-chips**.
  - Each bot starts each table with **1,000 flop-chips**; they carry over between hands at that table, are never
    topped up, never enter a pot and are worth no points.
  - Normal preflop betting. If one player is left, the hand ends (no auction cards, no flop-chips move).
  - Otherwise **five auction cards** are dealt face up, numbered 0-4. Every player still in, all-ins included, bids;
    no other action during the auction.
  - A bid is five whole numbers (one per card) summing to at most your balance; 0 = no bid; spending it all is allowed.
  - Card score = total bid on it by all players. Top **three** become the flop (shown in auction order); the other
    two are dead for the hand (never turn or river).
  - Ties go to the earlier-dealt card; no bids at all = cards 0, 1, 2.
  - You pay your bids on the selected cards only; bids on dead cards are free. Paid chips are destroyed, never refunded
    (also if you fold or lose).
  - No negative bids or vetoes: to keep a card off you must outbid it on three others.
  - Turn, river, betting, side pots, showdown as reference hold'em. Showdown reveals both hole cards automatically, no
    mucking; folded hands and uncontested winners stay hidden.
  - All-in run-outs: hands shown before remaining board cards; for a preflop all-in the auction finishes first, then
    cards are shown, then the flop; bidders never see those cards while bidding. Otherwise hands are shown after river
    betting.
  - **Failed bid** (timeout, exception, invalid) = 0 on every card; it never folds the hand or removes betting options.
  - The variant supports **2-10 players**.
- Bot interface for the auction (F): at `state.phase == "auction"` return `Action("bid", cards=(b0..b4))` (cards holds
  amounts, `amount` must be 0; empty `cards` = all zeros). `state.can("bid").max_amount` = balance.
  `state.variant["flop_chips"]` (own balance, net of payments), `["flop_chips_by_seat"]` (all seats, busted ones too;
  updated only after every bid of an auction is in), `["auction_cards"]`, `["flop_chips_paid"]` after the auction;
  `state.board` holds the three chosen cards. Bids are asked one player at a time; each makes a public `bid` event
  naming only the bidder. Nobody sees others' amounts, card scores, who bid on what or tie-breaks; a seat's balance
  drop reveals its total paid, not the split. Hand histories carry `flop_chips_before` / `flop_chips_after` per seat.
  The page says to budget flop-chips because a table can last "a couple of hundred hands".

## 2. Table rules (F, "One table")

- **8 players**, **2,000 chips**, blinds **10/20**, blinds rise **every 20 hands**, **hand cap 250**.
- A table ends when one bot has every chip or at the hand cap.
- GS: scored rounds play the active bot at "thousands of 8-player sit-and-go tables".
- GS: "a round can change the defaults, and `state.config` holds each table's actual settings" (players, stack, blinds
  schedule, hands per level, hand cap, payouts, decision_ms, time_bank_ms, memory_bytes).

## 3. Points per place

- F: 1st **50**, 2nd **30**, 3rd **20**, 4th-8th **0**. At the hand cap the survivors split the remaining points by
  **ICM on their stacks**.
- GS **sharpens/qualifies this**: "A round may draw payouts per table, so read payouts rather than assuming 50/30/20"
  (read `state.config.payouts`). F shows only the fixed table. Not a contradiction, but GS says payouts can vary per
  table within a round; F does not mention that.
- F: if several bots bust in one hand, the one with more chips at the start of that hand places higher.
- GS: kit's local `play` with 3 seats plays 3-handed tables "where every place pays".

## 4. Schedule and round structure (F)

- Build **60 minutes** after the variant is announced; keep building between scored rounds.
- Default schedule (round, start after build, weight): 1 at build end **1x**; 2 at +20 min **2x**; 3 at +40 **3x**;
  4 at +60 **5x**; 5 at +80 **8x**; 6 at +100 **13x**. Six scored rounds, 20 minutes apart (start to start).
- 20 minutes is the interval between starts, not a time limit; a round finishes when all its iterations are done.
- Each scored round runs **at least 5,000 iterations**; each bot plays **one table per iteration**.
- Results normally arrive **in the following 20-minute window**, with a compute gap after the last round.
- **Practice:** "about 1,000 iterations every 10 minutes **during the build phase**". Practice never counts toward the
  final score. Neither page mentions practice rounds after the build phase.

## 5. Weights and the total (F)

- Round score = **average points per table**; results show the average and the finishes in every place.
- Final score = sum over rounds of round score x that round's **saved multiplier**. "The weighting setting applies when
  a new round starts; started rounds keep their multipliers" (i.e. the weighting can be changed between rounds and
  only affects rounds not yet started).
- Default weights sum to **32**; round 6 is 13/32 = 40.6% of the total; rounds 5+6 are 21/32 = 65.6%. (Our arithmetic.)
- Ties on the final total: **countback** = each team's share of tables won in each scored round x that round's weight,
  summed; then the same for 2nd places, and so on. Nothing by chance.
- A **disqualified** team has no rank and sits out later rounds.

## 6. Time, memory, size and sandbox limits

- Decision time: `state.config.decision_ms`, **1 ms** default (F and GS), plus "a small delivery allowance" (GS).
- Time bank (GS only; F does not mention one): per table, `state.config.time_bank_ms`, **100 ms** default;
  `state.time_bank_ms` is what remains. A timeout **empties the bank**; the next table starts with a full one.
- Import has its own **startup allowance** (value not stated; the rejection message states it). Load models at import
  and run one throwaway prediction there; a cold first call in `act` can exhaust the bank.
- Production: the microVM imports `agent.py` once and **forks** copies; each copy builds `Agent()`; any copy may answer
  any table. Threads started at import do not survive the fork.
- Threads: OpenMP, MKL, OpenBLAS limited to 1 thread. Set `OMP_NUM_THREADS`, `MKL_NUM_THREADS`,
  `OPENBLAS_NUM_THREADS` = 1 before importing NumPy/PyTorch; ONNX Runtime `intra_op_num_threads = 1`;
  `NUMBA_NUM_THREADS` = 1; on macOS `VECLIB_MAXIMUM_THREADS`.
- Memory between turns: bytes returned from `act`, `state.config.memory_bytes` **64 KB** default, truncated beyond;
  up to about **16 KB** costs nothing measurable; starts as `b""` at every table. `self` and globals cannot be relied
  on between calls.
- After a timeout, exception or crash the previous memory is kept and that turn's events are re-delivered; after an
  illegal action the returned memory is stored; memory that makes `act` raise comes back unchanged on every later turn.
- Upload size: **50 MB** uploaded (F: "current upload default"), **200 MB** unpacked, **1,000** archive entries,
  **1 MB** for `agent.py` code, paths up to **512 characters** and **16 levels** (GS).
- Sandbox: Python **3.12**; standard library, `poker_agent_sdk`, `poker_agent_protocol` and exactly `requirements.txt`
  (NumPy, SciPy, pandas, scikit-learn, PyTorch CPU, LightGBM, XGBoost, ONNX Runtime, Numba, eval7). `poker_engine` and
  `pokerkit` exist only locally. No network, no GPU. Bot directory read-only and not executable (compiled extensions
  or executables cannot load). `/tmp` is the only writable place: **64 MB**, not executable, shared by the team's
  copies.
- Advice (GS): benchmark `act` with `time.perf_counter_ns()` on realistic states including memory parsing; compare the
  **p99 and the maximum**, not the mean, with `decision_ms`.

## 7. Failed decisions

- F: a timeout, error or illegal action **checks when free, otherwise folds**. Auction: failed bid = all zeros.
- GS: same fallback, "or the automatic choice in a phase a variant adds"; showdowns ask no decision.
- Illegal includes: a kind not offered; a raise total outside min..max (**not clamped**). Floats (NumPy too) are
  **rounded down**, so a computed size can land one chip under the minimum; an undersized raise facing a bet folds.
  Returning an illegal action is a failed decision even when the fallback has the same effect.
- Check and call are never offered together; reference hold'em offers no fold when checking is free. Where neither
  check nor fold is offered, `Action(first.kind, first.min_amount)` with `first = state.legal_actions[0]` takes the
  automatic choice.
- Process failures: a copy that crashes, exits, keeps stalling its tables with late replies, gets stuck or breaks the
  protocol is killed and restarted on its next request; an exception in `act` fails only that decision. Each copy has
  a **limited number of starts per round** (number not stated); once every copy is given up on, the bot's remaining
  decisions **on that machine** play the fallback for the rest of the round.
- Team page shows per round: decisions, missed decisions, restarts, latest error reports (tracebacks, why a copy was
  killed, memory-cut notes). It never shows what the bot prints.

## 8. Uploads, the upload test, activation, cooldown, freeze

- Upload `agent.py`, or a zip with `agent.py` at its root plus the files it reads. `poker-agent pack DIR OUT.zip` zips
  reproducibly (skips hidden files, `__pycache__`, refuses symlinked files, skips symlinked folders) and runs `check`.
- `poker-agent check FILE` runs the server's upload checks without executing code; in a zip it parses every `.py` and
  **rejects the upload if any file imports `poker_engine` or `pokerkit`**, even one never loaded.
- **Cooldown: a team can upload once every 30 seconds** (GS). F does not state a cooldown.
- **Upload test** (GS): a heads-up match of **up to 20 hands** against a check-when-free-else-fold bot, in the
  competition's variant, with the **1 ms** limit and **no time bank**, "whatever the rounds use". Rejected if it does
  not start within the startup allowance, crashes or stops responding (no restart), or **fails more than 10% of its
  decisions**. Local `play` always gives a 100 ms bank, so a bot can pass locally and fail here. Rejections show a
  reason and validation log on the team page.
- **Activation:**
  - F: each upload becomes the active bot **once it is ready, unless a newer upload is already active**; you can switch
    back to any earlier ready upload.
  - GS: each upload that **passes its test match becomes active automatically**, unless the competition is frozen or
    has ended when the match finishes (then it stays "ready" until chosen). An earlier upload can be chosen on the team
    page.
  - The two wordings differ in their exception (F: a newer upload already active; GS: frozen or ended), not in
    substance: both say a passing upload goes active by itself.
- Each round (F: "its own snapshot") freezes every team's active bot **at its start**; later changes apply to later
  rounds. A team with no active bot **forfeits the round with zero**.
- A competition-wide **freeze** (by the organizer) pauses uploads and active-bot changes until unfrozen; GS: uploads
  and changes are refused while frozen.

## 9. Filler seats, seating, cross-table learning (F unless noted)

- Seats randomized each iteration.
- **Fields smaller than eight play short tables**; short tables are filled with bots not already seated, whose finishes
  **never score for their teams**.
- Memory starts empty at every table; opponents have **anonymized seat IDs** (GS: anonymized per table). Bots cannot
  learn across tables; GS: carrying information between tables breaks the rules; bots may not keep files between
  tables or compute between decisions.

## 10. Game state (GS)

- `state.events`: everything public since your last turn (since table start on your first turn). Kinds in reference
  hold'em: `hand`, `ante`, `blind`, `fold`, `check`, `call`, `raise` (total for the round), `board` (new cards only),
  `show`, `win` (can be several), `stack` (at hand end). Variants add kinds (here `auction`, `bid`); ignore unknown ones.
- Hand: seat, cards, board, pot, `to_call`, `legal_actions`, history (this hand), phase. Cards like "As", "Td".
- Table: seats (seat, stack, bet, status active/folded/all_in/busted, shown_cards), button.
- Tournament: blind_level, blinds, hands_until_next_level, hand_number, players_remaining, bust_order.
- `state.config`: table_id, seat, variant id, players, starting_stack, blinds schedule, hands_per_level, hand_cap,
  payouts, decision_ms, time_bank_ms, memory_bytes.
- Show events arrive on your next turn at the table and appear in completed hand histories.

## 11. Hand-history downloads (GS)

- When a round completes, the team page and the round page offer its hand history: **every table your bot played**, as
  **gzipped JSON lines**, with **opponents named**, your cards in every hand, others' cards only when public, and the
  actions played for your failed decisions.
- Either the **full set** ("can be quite large") or **a smaller subset**. The page does not say how the subset is
  chosen or how big it is.
- The kit's `hand-history/` folder has a sample in the same format and a streaming reader; the kit README documents
  the format. F adds the per-seat `flop_chips_before` / `flop_chips_after` fields for this variant.

## 12. Starter kit and local tools (GS)

- Kit (available, with uploads, only once the variant is announced): `agent.py` (legal template with a memory example),
  `examples/` (`check_or_fold`, `min_raiser`), `sdk/` (protocol, engine with local simulator, **ICM calculator**,
  `poker-agent` command), `requirements.txt`, `RULES.md` (the variant), `hand-history/`, `README.md`, `AGENTS.md` and
  `CLAUDE.md` (CLAUDE.md imports AGENTS.md; use the kit folder as the assistant's working directory).
- Setup: `python3.12 -m venv .venv`, `pip install -r requirements.txt`, `pip install -e` the three `sdk/` packages,
  `poker-agent check agent.py`, `poker-agent play . examples/check_or_fold examples/min_raiser --tables 200`.
- `play`: one seat per folder, **2 to 10**; repeat folders to fill the **8 seats a round uses**; each folder runs as two
  processes shared by its seats; prints the last 64 KB of stderr per process; JSON on stdout with average points,
  places and failed decisions per seat; `--seed` replays; changes under `sdk/` affect local play only.
- `Agent.act(self, state, memory)` returns `(action, memory_bytes)`. Betting actions: `Action.fold()`, `.check()`,
  `.call()`, `.raise_to(total)` (total = whole bet this betting round). `state.can(kind)` gives min/max or None.
- Advice: test in a virtualenv with nothing else installed (`check` catches only `poker_engine`/`pokerkit`).

## 13. Remote build machine (GS)

- One EC2 "build box" per team, Ubuntu, "similar to the tournament runtime". Each member logs in with their own SSH key
  (ed25519, RSA or ECDSA; no DSA or `-sk`); **five keys per account**; a key is live within **30 seconds**. Outbound
  port 22 must be open.
- Command from Your team -> Build box tab: `ssh ubuntu@<address>`. "Address not available yet" = fleet not started;
  "Build starts ..." = closed until then; before the opening time the login prints the opening time (UTC) and
  disconnects. Work in `~/work`.
- Optional SSH alias `no-limit-2026-build` (required for the Codex app). Codex: `codex login --device-auth` with the
  team's ChatGPT account (one sign-in per box, last one wins); or run `codex` in `~/work` inside
  `tmux new-session -A -s no-limit-2026`. If `codex` is missing: still installing, `cloud-init status --wait`.
- Troubleshooting table: Windows OpenSSH client, publickey denials, key permissions, host-key changes ("tell the
  organizers"), port 22 blocked or box stopped.

## 14. API, keys, setup skill (GS)

- API keys are generated in **Settings -> API keys**. The setup skill (one file) is at
  `https://pokerbot.sequoiacap.com/tournament/no-limit-2026-setup/SKILL.md`; it saves the API key, registers the SSH
  key, writes the alias, connects Codex or the Claude app; run it again after the announcement to put the kit on the
  box, or choose local-only to download the kit locally. A web chat alone cannot run it.
- The page advises running setup on a smaller model ("a frontier model such as Astra or Fable burns through your
  budget").
- No API endpoints are documented on either page.

## 15. Awards, credits, conduct

- Credits: every competitor can claim **$50 in OpenAI credits** for building.
- No prize money, awards or side prizes are mentioned on either page.
- Conduct stated: no carrying information between tables; no files kept between tables; no computing between
  decisions; generated code may import only the allowed packages. Disqualification exists (F) but its grounds are not
  listed.

## 16. Regionals and finals (F)

- Regionals: **Boston, Stanford and Pittsburgh**. **Five teams from each regional plus five wildcards** are invited to
  the finals (20 teams).
- "Finals use the **same tournament format** with a **different poker variant**."

## Against what the bundle assumes

Assumptions as briefed, plus `CLAUDE.md`, `strategy/DECISION_RULES.md` §3 and `strategy/PLAN.md` §§3-5.

**Confirmed (Boston defaults):** 8-player sit-and-go tables, 2,000 chips, 10/20 rising every 20 hands, 250-hand cap,
50/30/20 for 1st-3rd, 1 ms decision limit, 60-minute build, six scored rounds 20 minutes apart, round plays the active
bot snapshotted at its start, no-active-bot forfeits, hand histories downloadable per round (full or a subset), 20
finalists (`CLAUDE.md` line 3). Finals use "the same tournament format", so all of this is the default unless the Finals
Format page says otherwise.

**Differs:**
1. **Upload cooldown: 30 seconds** (GS), not "up to 5 minutes". `DECISION_RULES.md` §2 rule 2 ("Assume the upload
   cooldown may be up to 5 minutes ... plan at most two real uploads per window") and `prep/HANDOFF.md` §7 ("assume up
   to 5 minutes"). HANDOFF §9 already saw 30 s in the regional's API; these pages confirm it in writing for Boston. The
   binding constraint on a late upload is the upload test, not the cooldown (item 3).
2. **A passing upload goes active by itself.** `CLAUDE.md` §4 rule 2 and PLAN §3 treat activation as a separate click
   ("Dylan uploads it and makes it active", PLAN §5 b10; "he uploads it if it isn't on the portal yet", T-12). Per F
   and GS, uploading any zip that passes its test **replaces the active bot** as soon as the test ends (F: unless a
   newer upload is already active). Consequences: uploading a challenger or test build during a window makes it the
   bot for the next round unless someone clicks the live bot back; an upload intended "for later" must not be made
   inside the snapshot window of a round it should not play.
3. **Timing of a late upload.** PLAN §3 T-3 ("else uploaded around T-4 to T-3") assumes the zip is active at T-3. An
   upload first plays a heads-up test of up to 20 hands plus startup; it becomes active only when that finishes. The
   pages do not say how long that takes; a zip uploaded at T-3 may not be active at T-0, in which case the previous
   active bot plays.
4. **Upload test threshold.** GS: rejection at **more than 10%** failed decisions (plus startup failure or crash).
   `CLAUDE.md` §4 rule 1 demands zero failed decisions; that is stricter than the portal, which is fine, but the portal
   will accept a bot with some failures.
5. **Time bank exists in scored play:** 100 ms per table by default, emptied by one timeout, refilled next table (GS).
   The bundle mentions only "no time bank" for the upload test. Hard rule 1 is still right (the upload test has no
   bank), but scored play tolerates rare slow decisions up to the bank.
6. **"A bot that times out auto-folds"** (`CLAUDE.md` §4 rule 1): the pages say it **checks when free, otherwise folds**
   (and plays the variant's automatic choice in an added phase).
7. **Payouts can vary per table within a round** (GS: "A round may draw payouts per table, so read payouts rather than
   assuming 50/30/20"). The bundle reads payouts once into the rules card (`CLAUDE.md` §4 rule 3, PLAN §5 b0 `platform`
   brief). The bot should read `state.config.payouts` (and the other `state.config` fields) at every table; GS also
   says a round can change the table defaults.
8. **ICM at the hand cap:** survivors at hand 250 split the **remaining** points by ICM on stacks (F). This is how
   points are scored, not only a strategy tool; the bundle's briefs mention ICM thresholds but not that the cap itself
   pays by ICM.
9. **Weights are given, not "read later":** 1, 2, 3, 5, 8, 13 (total 32). Round 6 = 40.6% of all points, rounds 5-6 =
   65.6%. DECISION_RULES §3 "the last round is often 25-40% of all points": at these weights it is the top of that
   range. The 15%-of-weight trigger ("When to be bolder") is crossed after round 3 (6/32 = 18.8%); 30% of weight
   ("Exploration") after round 4 (11/32 = 34.4%). F adds that the weighting **can be changed** and applies to a round
   when it starts; started rounds keep theirs.
10. **Practice rounds only during the build phase.** F: "about 1,000 iterations every 10 minutes during the build
    phase". It does not mention a practice round before each scored round, which PLAN §3 ("A practice round starts 10
    minutes before each scored round"), §5 (T-10, T-9, T-8 rows) and DECISION_RULES §3 (challenger judged on its
    practice round) depend on. Also "every 10 minutes" during a 60-minute build could mean minute 10 as well as
    20/30/40/50 (HANDOFF §9: at the regional the first practice started about 20 minutes after the announcement).
11. **Practice size "about 1,000" and scored rounds "at least 5,000" iterations.** Consistent with DECISION_RULES §3
    "one 1,000-table practice round"; scored rounds may be larger than 5,000.
12. **Results timing:** F says results "normally arrive in the following 20-minute window". PLAN §3 T-13 assumes data
    about 7 minutes after a round starts; the page promises only "within the next 20 minutes", with a compute gap
    after the last round.
13. **Short tables and fillers.** "Fields smaller than eight play short tables" with fillers whose finishes do not
    score. With 20 teams this matters only if forfeits or disqualifications shrink a table's field; not in the bundle.
14. **Regional naming:** F lists the regionals as Boston, **Stanford** and Pittsburgh; the bundle calls ours the "Bay
    Area regional" (DECISION_RULES §1, PLAN §1, HANDOFF §9: the portal's team listing says "Bay Area").
15. **Tie-break by weighted countback** of table wins, then 2nds, etc., and disqualified teams sit out later rounds;
    not in the bundle.
16. **Cross-table information:** anonymized seat IDs and "bots cannot learn across tables" (F); "carrying information
    between tables breaks the rules" (GS). The bundle's `scout` counters and team-profile priors from earlier rounds
    (DECISION_RULES §5) are built into new uploads between rounds, which neither page addresses directly (see below).
17. **Process restarts are capped per round**, and once all copies are given up the rest of the round on that machine
    plays the fallback (GS). The bundle's hard rules cover speed and legality but not crash-proneness over 5,000+
    tables.

## Not stated in these pages

- Anything specific to the **Finals**: its variant, date, schedule, number of rounds, weights, payouts or table size.
  Only "same tournament format with a different poker variant".
- **Leaderboard**: nothing on whether standings are shown, hidden, held or revealed (the API's `leaderboard_held` and
  `final_weight` fields in HANDOFF §9 are not explained on either page). Nothing about a **hidden final weight**.
- **Culling or elimination** of teams between rounds: not mentioned (the API's `culling` field in HANDOFF §9 is
  unexplained). Only disqualification, grounds unstated.
- **Six-player tables**: not mentioned. Default is 8; the variant supports 2-10; short tables happen only when the
  field is smaller than eight.
- `icm_luck_correction` (HANDOFF §9): not mentioned.
- Practice rounds between scored rounds; whether practice also snapshots the active bot at its start.
- How long the upload test takes; the startup allowance's value; the number of restarts per copy per round; the
  "small delivery allowance".
- How the hand-history subset is chosen or sized (HANDOFF §9 found `?tables=N` in the API).
- Whether hand data can be fetched while a round is still running.
- Prize money, awards or side prizes.
- Whether using opponent profiles learned from downloaded hand histories (opponents are named there) inside a later
  upload is allowed; the pages forbid only learning across tables at runtime.
- API endpoints, rate limits, or the API's use beyond the setup skill.
- Whether build boxes stay open after the build phase (F only says "keep building between scored rounds").
