# STEERING (from the reviewing assistant: read before every step, never edit)

Updated 18:39.

## Live status
- **m10:** uploaded, gated **SAFE**. Upload-test conditions with no bank: 0 failed decisions on the Mac (5 seeds) and on the build box (3 seeds). 8-seat test: 0 failed decisions.
- **Gate:** every new `releases/*.zip` gets gated automatically within about 15 s (rules, no-bank upload test on the Mac and the build box, 8-seat match against m10). The verdict appears here.
- **v2:** in progress. Tables were built; `bots/v2/agent.py` was started 18:38.

## Facts verified in the kit's SDK source (stop spending time on these)
- **Conventions:** `Seat.stack` excludes the street bet (all_in ⇔ stack == 0); `state.pot` includes current bets; events are "every event since this seat's last answered decision", so your own action is echoed; kinds and statuses are plain strings. **Skip convention detection.** Keep the legality funnel and the try/except.
- **Variant pin:** the local engine defaults to plain hold'em. Every test must pin `flop_discard_reveal`, as `tests/match.py` does.

## Every release must
1. **Live in its own folder** `bots/<name>/`, packed with `poker-agent pack bots/<name> releases/<name>.zip`. Never pack the repo root or `tests/`, and no `.py` in the zip may import `poker_engine` or `pokerkit`.
2. **Warm up and fix GC at import:** run one throwaway decision (including a select), then `gc.collect(); gc.freeze(); gc.set_threshold(20000, 50, 100)`. m10's 2.6 ms laptop outlier is the GC pause this prevents.
3. **Always return a valid select** `(discard, reveal)`, distinct ints 0-2, including for all-in seats. Fall back to `(2, 0)` on any error.
4. **Stay fast:** p99 under about 0.4 ms on the laptop, with no single decision over 1 ms in the fuzz test. Cap Monte Carlo by a deadline of about 0.3 ms after `act()` starts.
5. **Beat the current release** in the same run: 8 seats with the new bot ×4 and the previous release ×2 plus the examples, 300+ tables. If it doesn't beat it, don't release it.

## 18:50: v3 gated SAFE. Upload test 0 failed on the Mac and the build box; 8-seat: v3 15.0 vs m10 11.7, 0 failed. **v3 is the ACTIVE bot** (uploaded 18:51) and is playing the practice round now. The reviewer will analyze its hand history when it lands.
**19:50: v6 is ACTIVE** (the user confirmed it) for round 3 at 20:00. v5r plays round 2 until then.

**20:59: v10 is ACTIVE for the final round 6** (the user confirmed it).
- **Practice 9 (v10):** 16.98, within noise. Its all-in calls at ≤5 alive beat folding by +1.30 pts each (n=646). The fix is live: 2-3 alive calls 22-23%.
- **Samuel and the research session both agree:** no changes.

## 20:52: FINAL LOCK for round 6 = v10
- **Round 5 (v9s), first 1,000 tables:** 19.95 points, places 26/16/10%, 0 automatic decisions, rules live. The 2-3 alive all-in calls are still at 18% because of the bug, which v10 fixes.
- **No more builds.**

**20:50: v10 is going up for the practice round,** a live check of the ICM fix. Round 5 stays on v9s, locked at its start. Round 6 = v10 unless the round 5 or practice data says otherwise.

## 20:48: ROUND 6 candidate = v10 = v9s + an ICM BUG FIX (reviewer-built, gated SAFE)
- **The bug:** `poker_agent_sdk.icm()` gives a busted stack **0 points**, e.g. `icm([0,4000],[50,30,20]) = [0, 50]`.
  - With 2-3 alive our bust place is *paid* (30 or 20), so `icm_call_threshold` demanded about 88% equity heads-up where pot odds say 45%.
  - Samuel R1-R4: heads-up all-in calls beat folding every round (+1.04 to +1.71). Round 4's heads-up call rate fell 23.8 → 15.2%, costing about 0.21 pts/table.
- **The fix:** `icm_on` only applies at 4-5 alive (`icm_min_players: 4`), where busting really is 0 points.
- **Local diff vs v9s:** 2-3 alive all-in call rate 17-22% → 24-25%, matching R3. No other shift.
- **Any future build starts from v10.**

**20:39: v9s is ACTIVE** (the user confirmed it) for scored round 5.
**Round 6 (final, ×6) default = v9s, unchanged.** Change it only if round 5 data shows a clear problem; v7 is the fallback. No new build unless the reviewer sends one.

## 20:38: ROUND 5 LOCK = v9s = v9 with `late_steal_widen: False`
- **Why:** the v8b practice came in at 17.82 vs v7's practice at 19.06, which is −1.24 ± 0.95.
  - v8b moved preflop the most since v4: VPIP 28.5 → 33, 5-4 unopened raise 28 → 36%, own-jam busts 46 → 55%. Steals drive most of that.
  - The steals rest on the oldest evidence (o1/o2), and Samuel shows the field now re-raises opens more.
  - The changes validated on R3 stay: HU jams and opens, bb_fold off, bb_jam.
- **v9s gate:** SAFE. Upload test 0 failed on the Mac and the box. VPIP 30.2, PFR 24.5, no shifts.
- **Round 4 full (v7):** 18.26, 5th by our measure.
- **The next build (round 6, ×6) starts from v9s.** Don't re-enable steals without R4+ evidence.

## 20:34: v9 gated SAFE (checksum cab2672d…). It goes up now, for the practice round and scored round 5.
- **Gate:** upload test 0 failed on the Mac and the box. VPIP 31.4 and PFR 25.8.
- **v9 vs v8b, identical tables:** the only move is BB jams at 5-4 alive, 10.9 → 12.1 (intended). The bots/v8b base matches the reviewer's v8b except for one whitespace change.
- **Round 4 (v7), first 1,000 tables:** 18.55 points, 7th overall. Fixes live, 0 automatic decisions.
- **Samuel:** the field keeps converging, and opens are getting re-raised more often (BTN 14 → 17%, CO 18 → 22%). Judge steals on R3+ data only.

## 20:28: v9 SPEC = v8b + `bb_jam_widen`. Pack by 20:52 for round 6 (×6 weight).
- **Rule:**
  - BB, 5-8 alive, facing a single non-all-in open from CO, BTN or SB, eff < 40 bb.
  - Where v8b folds a hand containing an ace or ≥2 cards T+, jam.
- **Evidence:** Samuel R2/R3 from our own cards, three matching checks. Jams vs fold: two broadway +0.83 to +1.18, Ax +0.48 to +1.10.
- **Rejected for v9:**
  - The turn low-pair rule: +0.01 pts/table, since v6 already folds 96% there.
  - Copying Lemonade's limping or 2 Curry's small 3-bets: they can't be measured from our files.
- **PFR cap is 29 for this release only,** because the jams are intended.

## 20:23: round 5 ships v8b = v8 with `bb_fold_oop_weak: False`. Build v9 on v8b.
- **Why the flag is off:**
  - In scored round 3, v6's postflop play turned the weak BB calls (pct > 0.30) from losers into break-even or winners: vs BTN **+0.14 ± 0.03** pts per call (n=9.1k), vs CO +0.03 ± 0.04, vs EP/MP 0.00 ± 0.02, 3-handed +0.05 ± 0.07.
  - In o1 and r2 they lost −0.15 to −0.48, so the flag was right for v3b and v5r, but it's obsolete after v6.
- **Gate result:** latency 0 failed (Mac and box). PFR 27.0-27.2 vs v8's 26.2-26.5. That's a composition effect from playing more short-handed hands; the raise logic is identical. The reviewer overrode the band edge for this build only.
- **v8 (bb_fold ON) also gated SAFE.** It's the fallback.

**20:15: v7 is ACTIVE** (the user confirmed it) for round 4 at 20:20.

## 20:13: v8 SPEC, FINAL. v8 = v7 + `hu_jam_widen`. Pack by 20:32.
- **The rule:** exactly 2 alive, effective stack 10-20 bb. Where v7 would fold, jam instead if pct ≤ 0.75. This covers (a) first-in as SB/button and (b) the BB facing a single non-all-in open. Nothing else changes.
- **Evidence:**
  - Samuel's R1 and R2 matched-hand tests: heads-up first-in jams +0.41 to +0.48 pts per jam, BB-vs-open jams +0.8 to +1.2.
  - The reviewer's o1 jam study: 2-3 alive unopened jams beat folding in every band.
  - Expected gain about +0.3 pts/table.
- **Withdrawn:** Samuel's two BB call adds. They depended on his simulated lookup.
- **v7's BB-fold rule stays.** The reviewer's replication used our own tables and real outcomes in o1 and r2, not Samuel's lookup.
- **Still out of v8:** late_steal_widen, and any 3-handed changes (nothing passes cleanly).

## 20:10: SCORED round 3 confirms v6. First 1,000 tables: **19.38 points, about 2nd of 127**
- That's up from v5r's 15.6 (first 1,000) and 16.7 (full). Places 27.5/12.2/9.7. Real flop fold-to-bet 22% → 59%. 0 automatic decisions.
- v7 goes up now for round 4.
- **v8 (pack by 20:32) builds on v7.** Candidates, decided by 20:25:
  - Samuel's two BB call adds: SB-open calls at 40+ bb with equity ≥ 0.434, and heads-up 4-10 bb shove calls with the top 40%.
  - Samuel's 3-handed and heads-up opening test, if it's positive in both rounds.
  - `late_steal_widen` top-45%-only, with PFR ≤ 27 allowed.
  - **No new thin-value rule:** the research found none.

## 20:05: v7 gated SAFE (flags 1, 2 and 4; late_steal_widen OFF). It goes up for round 4 at 20:20.
- **Gate:**
  - Upload test 0 failed on the Mac and the build box.
  - Behavior vs v3b OK. Behavior vs v6, in identical tables, OK: VPIP 29.6 → 27.7, PFR 24.3 → 23.6.
- **Keeping late_steal_widen OFF was the right call.** It's a v8 candidate in its top-45%-only form, which had PFR 26.3.
  - Top teams run PFR 25-31%, so a PFR band of 18-25 is too tight for an *intended* steal change.
  - The reviewer will allow PFR up to 27 for that flag only, *if* round 3 confirms v6 and v7 is clean.

## 19:58: v6 VALIDATED on the real field (practice round, 1,000 tables)
- **Result:** **19.75 points, 4th of 127**, against v5r's 15.6-16.7. Places 28/12/10%. Showdown +2.4 bb per hand, up from +1.3. 0 automatic decisions.
- **Real-play diff, v6 vs v5r:** fold to a flop bet went from about 22% to **57-69%**, and flop calls from about 60% to 17-26%. VPIP and PFR are unchanged.
- **v7 must not change v6's fold rules or their thresholds.** Stack the four v7 flags on top of v6 exactly as specified.

## 19:57: v7's #1 PRIORITY. `K["reveal_random"] = False` (back to v3b's least-leak reveal)
- **This is a randomized natural experiment from Samuel, round 2.** v5r's 50/50 reveal is a coin flip.
  - When one kept card makes **top pair**, revealing it earns +0.38 points per hand against +0.65 for hiding it: **−0.27 ± 0.05** (n≈19.4k each way).
  - Revealed top pair wins more often (79% vs 72%) but gets paid far less (+2.15 vs +4.39 bb).
  - The other reveal cases show no clear effect.
  - Expected gain: **+0.2-0.27 pts/table.** It was the cleanest evidence of the night.
- **Use v3b's existing `expose_index` path**, which never reveals the card that pairs the board. It ran about 40k real tables in v3b, so no new code.
- **v7 flag priority if time runs short:**
  1. `reveal_random False`
  2. `icm_mask_calls True`
  3. `late_steal_widen`
  4. `bb_fold_oop_weak`
- **Samuel replicated the BB rule on round 2:** vs CO −0.39, vs BTN −0.23, vs SB +0.25. That's consistent with the reviewer's results. Keep flag 4.

## 19:55: v7 gets a THIRD flag: `bb_fold_oop_weak` ON (replicated in two rounds plus Samuel's matched-hand study)
- **Rule:**
  - We're in the BB with ≥3 alive, facing a **single non-all-in open** from EP, MP, CO or BTN, with no limpers or callers before us.
  - With a hand **outside the top 30%** (pre_info pct > 0.30), **fold instead of calling.**
  - Keep top-30% calls, and keep our jams and 3-bets exactly as they are.
  - **Change nothing when the SB opens.** Those calls win +0.13 to +0.40 points.
- **Evidence:**
  - BB call minus fold, in ICM points: vs CO −0.32 to −0.49, vs BTN −0.19 to −0.37, vs EP/MP −0.14 to −0.17. That's on 31-100% hands, in o1 and r2, each about ±0.05-0.09, n≈3-8k per cell. Samuel's matched-hand study agrees.
  - Expected gain is about +0.15-0.2 pts/table, halved for the overlap with v6's postflop folds.
- **Expected behavior move:** BB fold-vs-raise up, overall VPIP down about 1 point. **No other preflop change** apart from late_steal_widen.
- **If it isn't ready and tested by 20:12, ship v7 without it.** Flags 1 and 2 come first.

## 19:49: v7 SPEC, FINAL. Pack by 20:12. v7 = v6 + these two flags ON
1. **`icm_mask_calls: True` again.** The research report's top section shows the mask only triggers where the ICM break-even is ≥10 points above pot odds, about 13% of calls, and those calls lose: postflop −2.07 ± 0.77 points. My all-calls average hid that, so the research is right. Use v5's exact code path; the flag already exists.
2. **`late_steal_widen` ON, scoped exactly as REPORT.md "FOR THE v7 BUILD" item 2:**
   - When CO, BTN or SB is first in with ≥3 alive and ≥15 bb, open 2.2-2.5 bb with every top-45% hand, plus the 45-60% band (the best two cards have ≥0.54 heads-up equity vs a random hand).
   - Early position, jams and short-stack play stay as they are.
   - **Tests:**
     - Late open rate at 8-6 players goes to 50-55%.
     - Overall VPIP stays ≤32%, and the early-position open rate is unchanged.
     - The behavior diff will flag the unopened raise rate. That's the intended move here, so note it in BUILDLOG.
- **Round 2 (v5r), first 1,000 tables:** 15.61 points, 26th.
  - Behavior is identical to v3b's: VPIP 29 and PFR 22. River bluffs into visible strength are now 0.
  - The field changed: new top teams fold to bets 59-69% of the time. Our showdown result fell from +2.9 to +0.9 bb, so we're paying off more, which is what v6 addresses.

## 19:44: v6 gated SAFE and goes up for round 3 (20:00)
- **Gate:**
  - Upload test 0 failed on the Mac (at load average 10) and on the build box.
  - Behavior diff OK: VPIP 29.1 vs 28.2, PFR 23.5 vs 23.0, nothing preflop moved.
  - Your own diff shows only the intended moves.
- **v7 (pack by 20:12)** waits on two inputs:
  1. Research's verdict on late-position steal widening, due 20:05.
  2. Samuel's big-blind defense analysis, also due 20:05.
- **Until then, prepare v7 = v6 + `late_steal_widen`, flag OFF by default.**
  - The rule: CO/BTN/SB first in, open about 50% at 8-6 players, about 55% at 5-4 and about 65% at 3, at 2.2-2.5 bb. Keep the early-position range.
  - The reviewer will decide at 20:05 whether to turn it on.
  - The behavior diff will flag the preflop unopened raise rate. That's intended *only* for this flag.
- **Run CPU-heavy tests before 20:08,** then stay quiet for the 20:12-20:15 gate.

## 19:40: third source agrees on flop folds; shoves stay as they are
- **Samuel's correlational study** of official round 1 against the top 12:
  - Facing a flop bet: we fold **32%**, call 52% and raise 15%. The top-12 median is fold **61%**, call 35%, raise 7%.
  - We cash less often (44.8% vs about 51%), and we lose the most points at 5-6 players left.
  - **This supports v6's fold rules.** The forward-EV research, Astra and Samuel now all point the same way.
- **The reviewer tested "cut shoves at 4-6 left" directly and it's REJECTED.**
  - Across our 112,894 preflop jams in official round 1, the ICM points actually won beat folding at every stage, in both contexts (unopened and over a raise) and in every strength bucket.
  - The range is +0.03 to +1.42 points per jam. At 4-6 alive it's +0.39 to +1.29 (n≈60k).
  - **Don't reduce jams or 3-bet shoves.** v4 already showed what touching 3-bets does.
- **Heads-up and 3-handed play:** already at or above top-12 level. Don't change them.

## TIMING (fixed, every agent follows it): a scored round starts every 20 min, at :00, :20 and :40
| Round | Starts | Pack the release by | Reviewer gates by | User uploads by |
|---|---|---|---|---|
| Round 2 (v5r, live) | 19:40 | — | — | done |
| Round 3 | 20:00 | **19:52** (v6) | 19:54 | 19:57 |
| Round 4 | 20:20 | **20:12** (v7) | 20:14 | 20:17 |
| Round 5 | 20:40 | **20:32** | 20:34 | 20:37 |
| Round 6 | 21:00 | **20:52** | 20:54 | 20:57 |
- **A release that misses its pack time is skipped,** and the current bot stays active. Never pack late.
- **Run the latency tests alone,** with nothing else running. The reviewer won't run CPU-heavy analysis while gating.

## 19:35: v6 spec, final (start now, pack by 19:52)
- **v6 = `bots/v5` with `icm_mask_calls: False`** (that's v5r) + **`visible_pair_rule`** + **`fold_weak_vs_hu_bet`**. See `research/competitors/REPORT.md` §6 rules 1-2, both confirmed in r2, r3 and r4.
- **Don't** reduce flop c-bets. Report §3 shows our heads-up air bets into a visible draw or miss card beat checking (+1.2/+1.35 bb vs +0.45/+0.96). Only bets into a visible pair lose, and rule 1 covers those.
- **Not in v6:** late-position steal widening (report §4, tentative, +2-3.5 bb). It's the v7 candidate after v6 has been tested on the real field.
- **Allowed behavior-diff moves:** heads-up flop and turn fold-to-bet up toward 50-55%, and heads-up flop bets into a visible pair down. Nothing preflop may change.

**19:33: v5r is ACTIVE** (the user confirmed it) for scored round 2.

## 19:32: switch to v5r for scored round 2 (19:40). v6 must build on v5 with `icm_mask_calls: False`.
- **The reviewer cross-validated v5 on official round 1** (v3b, all ~20,000 tables):
  - **River fix: confirmed.** There were 2,437 heads-up river bets into visible strength, each losing 4.3 bb from that point on, so the fix gains +0.52 bb/table.
  - **ICM call masking: harmful.** Across v3b's 15,423 heads-up all-in calls with ≤5 alive, calling beat folding on ICM points in **every** strength bucket. Preflop: top 10% +2.0 points per call, 10-25% +0.6, 25-45% +0.4, weakest +0.4. Postflop +0.7. The field's bubble jams are wide, so folding gives points away.
- **v5r = v5 with `icm_mask_calls: False`, nothing else.** It gated SAFE with no behavior shifts, and the user is uploading it now.
- **For v6:** start from v5 and set `icm_mask_calls: False`. Add `visible_pair_rule` and `fold_weak_vs_hu_bet` from the competitor report. **Don't re-enable any ICM masking.**
- **Official round 1:** we placed 13th of 127 on the portal (9th in our own table count) with 18.10 points. Top teams: TeamBallHog 20.4, Lemonade 20.0, AZ 20.0, Team 72 19.4, WAYS-ER 19.0.

**19:28: v5 was uploaded and active (superseded by v5r).** (the user confirmed it). It plays the 19:40 round. Compare its results against v3b (19.02 points, places 29/10/9%).

## NOW 19:27: v5 gated SAFE and goes up for the 19:40 round. v6 is due 19:52 for the 20:00 round.
- **v5 gate:** upload test 0 failed on the Mac and the build box. Behavior diff OK: VPIP 28.1 vs v3b's 28.7, PFR 22.4 vs 23.2, with no unintended shifts.
- **v6 = v5 + the competitor study's top two rules.** Read `research/competitors/REPORT.md` §1, §2 and §5. These are direct forward-EV measurements, replicated across rounds r2 and r3. Put each behind its own flag:
  1. **`visible_pair_rule`.** Heads-up, when the opponent's visible card pairs the board and we hold only one pair or air:
     - Don't bet.
     - Fold to bets on the flop and turn.
     - Continue only with two pair or better, or a flop flush draw.
     - Evidence: calling with "our pair beats their visible pair" has forward EV of -6.3 bb (n=1,946), and the top six fold 70% here where we fold 61%.
  2. **`fold_weak_vs_hu_bet`.** Heads-up on the flop and turn, facing a bet where the bettor's visible card is an overcard or low: fold air and middle pair. Keep calling with top pair or better and with flush draws. Evidence: air calls lose 1.6-1.8 bb and middle-pair calls lose 2.1-3.6 bb (n≈9k).
- **Expected and allowed behavior-diff moves:** flop/turn facing-bet fold rate up toward 50-55%, and flop no-bet bet rate down a little. **Nothing preflop may move.**
- **Not now:** rules 3-5 (turn/river air checks, wider opens, bubble folds). They're tentative or correlational.

## RULES FROM 19:25: every round is SCORED now. A new round starts every 20 minutes, and later rounds weigh more.
**Anti-overfitting: the real field is the only judge.** Local matches against our own bots predicted +4.4 for v4, and it scored -9.9 on the real field.
1. **Start from v3b's behavior.** Every release = v3 + a few **targeted** changes, each behind its own flag in K. Each change must be backed by real hand-history evidence (STEERING, `research/`, Astra's reports), not by local win rate.
2. **Never tune knobs to maximize local points against our own bots** (m10, v2, v3, v4). Local runs are for legality, latency and sanity only.
3. **The reviewer's gate now runs a behavior diff.** The candidate and v3b play identical tables against frozen field proxies (station, maniac, tag, m10, v2), and every preflop and flop decision frequency is compared.
   - **VPIP outside 22-35% or PFR outside 17-27% blocks the release.**
   - Any other frequency that moves more than 10 points is flagged. It's allowed only if the change was meant to move it; say which in BUILDLOG.
   - Run the same check yourself before packing: `tests/stats_check.py` plus a side-by-side against v3.
4. **In BUILDLOG, list for each change which real-field leak it fixes and which frequencies you expect to move.**
5. **Release cadence:** about 8 minutes before each round start, with v3b as the default. A missed deadline means v3b stays live, which is fine.

**19:20: v3b is the ACTIVE bot again** (the user confirmed it).

## STOP. 19:18: v4 FAILED on the real field. We rolled back to v3b. Read this before anything else.
- **Round 4 (v4), first 1,000 tables:** **9.59 points a table, 97th of 125.** v3b got 19.02, 7th of 123. There were 0 automatic decisions, so this is strategy, not latency.
- **v4's real-field stats against v3b:**

| Stat | v3b | v4 |
|---|---|---|
| VPIP | 29% | **42%** |
| PFR | 23% | **40%** |
| Postflop raise share | 59% | 64% |
| Fold-to-bet | 42% | 36% |
| Average stack at a postflop bust | — | 58 bb |
| Showdown result per hand | **+3.9 bb** | **-3.8 bb** |
| Flop folds | -2.8 bb | **-10.5 bb** |
| Busts with 7-8 players left | ~16% | **44%** |
| Average bust hand | 69 | **41** |

- **The local gate was misleading.** v4 beat v3 locally (+4.4) because v3 and m10 copies fold to aggression. The real field calls 46% of the time and has strong hands when it does. **Local head-to-head against our own old versions doesn't predict real-field results.**
- **The next bot builds on v3 (`bots/v3`), not v4.** Add changes one at a time. Each must pass a real-field sanity check before release:
  1. **Stats check.** In a local 8-seat run, VPIP must be 25-32% and PFR 18-25% (field top quartile: 27-30% / 22%), with postflop raise share ≤ 60%. Fail any one and the build isn't released.
  2. **Field-proxy opponents.** Build 3 tiny bots in `tests/opponents/` and gate against them plus v3b:
     - `station`: calls any bet with a pair or better or a draw, folds about 45% of the time to bets, rarely raises.
     - `maniac`: jams 95% of hands preflop.
     - `tag`: opens the top 20%, bets made hands, folds weak hands to bets.
- **v5 = v3 + only these two targeted changes,** each switchable by its own flag:
  - (a) **The river-bluff fix:** no bluff when the villain's visible card + board beats us. This is real-field confirmed (10.5% folds).
  - (b) **ICM masking of jams and jam-calls at ≤5 players**, porting only `icm_*` from v4. Leave out v4's softmax/value-function preflop, its jam tracking and its candidate betting. One of those caused the PFR 40%.
- **The reviewer found the cause** (round 4 against round 3, our preflop decisions):

| 8-6 players, facing one raise | Fold | Call | 3-bet | Jam |
|---|---|---|---|---|
| v4 | 31% | 4% | **58%** | 6% |
| v3b | 76% | 16% | 3.6% | 4.7% |

  - Then, facing a 4-bet, v4 **folds 96% of the time.** It's the same at 5-4 players: v4 3-bets 59%.
  - Unopened play is identical to v3b's (fold 73%, open 23.5%, 2.2 bb), so the bug is **v4's value-function/softmax for preflop facing a raise.** Its raise candidate must be getting fold equity it doesn't have, or a wrong cost.
  - Postflop sizing also inflated: the top quarter of v4's bets are 1.67× the pot or more, against 1.00× for v3b.
- **Confirmed on all 12,500 tables:** 9.17 points, 100th of 125. Chips per table: v4 -12.3 bb, v3b +31.8 bb.
  - v4's 3-bet lines net **-19.1 bb/table**: 3-bet then fold preflop -18.4, 3-bet then see a flop -19.6, 3-bet and win preflop +18.9. v3b's same lines net +6.7.
  - v4 also gave up v3b's profitable flat calls: +0.2 bb/table against +5.9.
  - **The facing-a-raise logic explains about 70% of the gap.** The rest comes from 3-bet pots played postflop: showdowns averaged -4.2 bb against v3b's +3.9.
- **Diagnose in BUILDLOG which v4 component raised PFR from 23% to 40%.** Run v4 with each new component disabled in the stats check. Don't release v4 parts until we know.
- **Pack `releases/v5.zip` only if it passes the stats check.** The deadline is 19:32 again. If it misses, v3b stays active.

## (superseded) 19:12: v4 was the active bot for the 19:20 round. v5 = v4 + the fixes below. Pack `releases/v5.zip` by 19:32 for the 19:40 round.
- **v4 confirmed:**
  - Strength: over 600 tables (seeds p1-p3), v4×4 averaged 14.7 per seat against v3×4's 10.3.
  - Latency: on the build box, 6 seeds of the no-bank upload test, run alone, had 0 failed decisions for both v4 and v4n.
- **Reveal A/B on the real field is settled.** Round 2 ran v3 with 50/50: 18.87 points. Round 3 ran v3b with least-leak (confirmed at 75% lower-card exposure): 19.02 points over 10,000 tables. That's within noise, so the rule doesn't matter. Keep 50/50 and stop spending time on reveals.
- **Round 3 (v3b):** 7th of 123. Places 1st/2nd/3rd were 28.7% / 9.6% / 9.0%, the same bubble pattern v4's ICM targets. River folds cost 99k bb in total and turn folds 70k bb.
- **#1 for v5: no river bluffs into visible strength.** See `research/round2_review/avalon_before_after_analysis.md`, and `diagnostic_hands.json` for 262 flagged hands.
  - In 117 heads-up river spots, we bet or raised when the opponent's exposed card plus the board already beat us. They folded only **7.7%** of the time, and those plays lost 42k chips.
  - The fix: before any bet that's a bluff, check whether the villain's *minimum* hand (exposed card + board + their worst hidden card) beats ours. If it does, set that seat's fold probability to about 0.08, so bet EV comes out negative and we check or fold instead.
  - More generally, condition fold probability on how strong the villain's visible card makes them, not only on the seat's fold-to-bet average.
  - **The reviewer confirmed this on round 3 (v3b, 10,000 tables):**
    - There were 1,164 heads-up river bets where the villain's exposed card plus the board already beat us. The villain **folded only 10.5%** of the time, and we lost 16.1 bb per hand.
    - River bets where we weren't visibly beaten got folds 25.7% of the time and made +9.6 bb.
    - So even a 1/3-pot bluff, which needs 25% folds, loses in the visibly-beaten case. v4's value function will still make these bluffs unless fold probability drops there.
- **#2: trim latency.** Same as below: get the clean-fuzz max under 0.5 ms.
- **#3, review only and not a global change:** one-pair turn all-in calls. There were 53, losing 37.7k chips in total. Check them against the diagnostic hands, and change them only if the calls were clearly wrong given the visible cards.
- **Gate v5 against v4,** paired, 600+ tables, before packing.

**19:08 gate verdicts:**
- **v4: SAFE.** It had 0 failed decisions on the Mac and the build box.
- **v4n: BLOCKED.** It had 1 failed decision in the build box no-bank test. v4n is v4 without ICM, so this is timing in the code they share.
- **Latency budget, act on it now:** cut the postflop candidate and Monte Carlo work so the clean-fuzz max is under 0.5 ms, not 0.83 ms. The box is slower than the Mac. Lower `post_iters` and the candidate count first.
- **A yellow flag on strength:** on gate seed g8, v4 scored 13.05 against m10's 13.60, where v3 had scored 15.03 against 11.70. The reviewer is running v4×4 against v3×4 over 600 tables to check.

**19:07: the reviewer killed `tests/match.py` processes by mistake** while restarting its gate. Any match you had running at 19:07 died, so rerun it. v4 and v4n are being gated now; the verdicts follow here.

**18:59: the reviewer made `v3b` for this practice round.** It's v3 with `K["reveal_random"]=False`, the only change, and it gated SAFE. The user is uploading it now: a real-field A/B test of the reveal rule against v3's round-2 score of 18.87. Don't build on it. v4 still starts from v3, and the reviewer will report which reveal rule won.

**DEADLINE: pack `releases/v4.zip` by 19:12** so it can be gated before the 19:20 round. v3 stays active until then.
- Ship v4 with only the ICM change if the other items aren't done.
- Before packing, run a clean fuzz alone, with nothing else on the CPU. A max over 1 ms means don't pack.
- Run the no-bank upload test, with 0 failed decisions required.
- If v4 can't make 19:12, pack it for the following round instead. Don't rush an untested build.

**NEW 18:58: practice round 2 with v3 is analyzed (2,589 tables). Read this before the v4 plan.**
- **Result:** v3 averaged **18.87 points a table, 8th of 116.** The top team scored 22.1. There were 0 automatic (failed) decisions.
- **The leak is ICM.** Our places 1st/2nd/3rd were **27% / 11% / 10%**. Top teams run about 22% / 20% / 18%. We win often, then bust 4th (12.6%) or 5th (15.0%).
- **37% of our busts come from our own preflop jam,** at an average stack of 14 bb. Of those, 382 happened with 4-5 players left, right at the money bubble (3 places pay).
- **Chip-EV push/fold is costing us points.** Our jam rate is 7.4% against the top quartile's 4.0%, and we call jams 21% against their 14%.
- **So item 3b (ICM) is now v4's #1 priority, ahead of everything else:**
  - With 5 or fewer players left, choose jams and jam calls by points EV, using Malmuth-Harville ICM over the real stacks and `state.config.payouts`.
  - Tighten hard at 4 left unless we're the short stack.
  - Test it locally with `--hands-per-level` set to the real schedule, and check that 2nd+3rd rises without 1st collapsing.
- **Postflop:** folds on the river cost about 12 bb each on average, and on the turn about 7 bb, with 4,767 turn and river folds in total. We're putting chips in, then giving up. Look at our turn and river barrels after the ICM fix.

**NEW 19:05: jams vs raises in round 2. Our unopened pots, compared at the same hand strength and stack depth:**
| Hands | Raise | Jam | Jam called |
|---|---|---|---|
| Top 5% | +2.6 to +5.9 bb | +1.1 to +1.5 bb | 7-16% |
| Weakest (30%+) | +0.0 to +0.7 bb | +0.6 bb | 11-16% |

- **The field folds to jams.** It doesn't call them wide, so value-jamming strong hands just wins the blinds.
- **Keep raising strong hands** to a normal size. Jams make chips only as steals, and those steals are the bubble busts the ICM item fixes.
- **Don't add "jam strong hands for value".**

**v4 plan, in this order. Run the tests in parallel.**
1. **Folder layout fix** (section below). It's quick, so do it first.
2. **Reveal A/B test, don't ship it yet.** Your own data says 50/50 reveal alone lost 13.45 vs 14.84 over 500 tables. v2 reads exposed cards, so least-leak plausibly fools naive readers.
   - Run v3 against v3 with `K["reveal_random"]=False`, paired seeds, 600+ tables. Include v2 seats, since v2 is a reveal-reader.
   - Report the numbers in BUILDLOG. The reviewer decides with the user whether to keep 50/50.
3. **Call wide deep jams.** The field jams from 40 bb or deeper about 25% of the time, with an average jam depth of 39 bb.
   - Track each seat's jam count and preflop-opportunity count in memory, with a Beta prior of about 10 at roughly 3% jams.
   - Set the calling threshold by the shover's estimated range: wider callers for seats that jam often.
3b. **ICM for all-in calls and shoves.** v3 never reads `state.config.payouts`.
   - When 5 or fewer players are left, call or shove all-in only if equity ≥ `(U_fold-U_lose)/(U_win-U_lose)`.
   - Compute U with Malmmuth-Harville over the full stack vector and the actual payouts. Precompute it once per decision; it's cheap at this size.
   - This matters most for the wide deep-jam calls in item 3.
3c. **Later, only if time allows: multiway equity.** Postflop currently multiplies heads-up equities (`e *= ...`, line ~505). That underestimates equity in multiway pots, so it plays too tight there. A joint sample per iteration fixes it, but only if it stays inside the 0.3 ms deadline.
4. **Fuzz max was 3.2 ms under CPU contention.** Run a clean fuzz alone, with no matches in parallel, and report its max. Anything over 1 ms on a clean run must be fixed.

## URGENT 18:49: release folder layout (a real upload just failed)
The user uploaded `releases/v2_src/agent.py` by itself. The portal rejected it with `FileNotFoundError: /bot/tables_bayarea.json`, because agent.py opens that file at import. Fix this now, before anything else:
1. **`releases/` holds only `<name>.zip` files.** Delete `releases/v2_src/`, `releases/v3_src/` and `releases/m10_agent.py`. The source already lives in `bots/<name>/`. A loose agent.py in `releases/` looks uploadable and isn't.
2. **The import must never crash on a missing data file.** Wrap the table load in try/except and fall back to a built-in heuristic, or embed the tables in agent.py as a Python literal (about 110 KB is fine under the 1 MB limit). Embedding is better: a single-file upload then also works.
3. **Write `releases/LATEST.txt`:** one line naming the newest zip and its time, for example `v3.zip 18:52`. The reviewer still gates it and posts SAFE or BLOCKED here.

## NOW (18:48): v2 gated SAFE (0 failures on the Mac and the build box); upload it. v3 = small and fast
- **The fixes, in priority order:**
  1. Fold-to-bet prior 0.55 → **0.45**, with less bluffing.
  2. Reveal **50/50**.
  3. Preflop opens at roughly the **top 20-25%**.
- **Parallelize:** run fuzz, the no-bank upload test and the 400-table head-to-head against v2 **at the same time**, as separate background processes with their own seeds. Multiprocess anything over 30 s.
- **Pack `releases/v3.zip`** as soon as fuzz and the upload test pass. The reviewer gates it within about 15 s.
- **If v3 can't ship within about 4 minutes,** keep v2 live for that round.

## NEW 18:46: REAL FIELD DATA from the practice round (1,042 tables, 148 teams). Calibrate to this, not to the simulations
- **m10's result:** 14.6 points per table (fair 12.5), about 31st of 92 teams seen. The top teams scored about 19-23.
- **Postflop, facing a bet or raise:** the field folds **45%**, calls **46%** and raises **9%**. That's much stickier than our docs assumed (50-70% folds).
  - Set the fold-to-bet prior to about **0.45**.
  - **Bluff less, value-bet thinner and bigger.** Bluffs need real fold equity: per seat, not the population.
- **Preflop:** raises are 19% of actions and jams 3.1%.
  - **25% of jams come from 40 bb or deeper**, with an average jam depth of 39 bb. Example: a 100 bb shove with AsTs, called by Jc9c.
  - Deep shoves are **wide and loose**: call them with strong 3-card hands, and size the calling range from the shover's own jam rate.
- **m10 was too loose:** VPIP 42% and preflop raises 29%. The "any 2 of 3 cards" rule admits too much. Use the table percentiles: open roughly the top 20-25%, wider late and short-handed.

## NEW 18:42: our math researcher's handoff (adopt it)
Read `research/CODING_AGENT_HANDOFF.md` now. The full paper is in `research/poker_variant_research.md`; read the relevant sections as you build each part. It agrees with the plan below. Adopt these specifically:
1. **Selection:** compare the 3 retained pairs on **flop-only expected value: made strength plus draw and nut potential.** Never use raw eval7 integer gaps as equity, and never choose the discard using a sampled turn or river (that's clairvoyance). Equity Monte Carlo of the kept pair on the flop against a range counts draws correctly, so use that if it fits the time budget. Otherwise use the paper's feature score in §6.2.
2. **Reveal 50/50** between the two kept cards as the baseline (paper §6.4), not "always the lower card", which is a tell. A bias can come later, only if a test shows it helps.
3. **Unavailable-card mask:** all **three** of your dealt cards (the discard too), the board, and **every** exposed card, including folded players'. Other players' discards are unknown, not known.
4. **Opponents after selection:** exposed card plus a weighted distribution over **one** hidden card. Start broad and shrink toward priors (Beta counts, prior weight about 10).
5. **ICM in points:** use `state.config.payouts` (paper §9) for big late commitments.
6. **Later, if time allows:** a small softmax mix over near-tied legal actions (§8). It's not needed for the first v2 release.
7. **Validation gate (handoff, end):** test all six selection actions, own-discard removal, folded exposed-card removal, short all-ins, malformed memory and replayed events.

## Priorities for v2, in order (biggest edge first)
1. **Selection by equity:** for each of the 3 discards, compute the kept pair's equity on this flop against a strong 2-card range (eval7 Monte Carlo, about 100 iterations each). Reveal 50/50, per the research note above.
2. **Postflop with exposed cards.** Each opponent's hand is {their `shown_cards` card + one hidden card}, about 45 combos. Narrow it by their betting and compute equity exactly against it. Dead cards are `state.variant["discarded"]` plus every exposed card.
3. **Preflop from your tables** (pct and equity against width), plus the ICM push/fold from `rebuild/03_STRATEGY.md`.
4. **Table quality.** `tables_bayarea.json` looks noisy: AA5 ranks above AAK, and 987 suited sits at about 0.60. Rebuild with 5-10× the samples when there's a free moment, keeping the build under about 3 minutes.

## Cadence
Release to `releases/` about every 10 minutes when the new version beats the previous one. The reviewer gates each release and writes SAFE or BLOCKED here.
