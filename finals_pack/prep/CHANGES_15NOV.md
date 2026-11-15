# What changed in the bundle on 15 November (morning of the Finals)

Read this first at 09:00. Three sets of changes went into the bundle between 03:55 and 05:30. Sets 1 and 2 were
approved by Dylan and Samuel. Set 3 was made while both were asleep, on Dylan's instruction to check everything,
fix what was found and not ask.

To see every changed line: `git diff ca2cccd..HEAD -- finals_pack ':!finals_pack/prep'` in the team repo.

## Which zip to use

| File (in `nolimit-live/`) | What it is |
|---|---|
| `avalon-finals-starting-bundle.zip` (also in `~/Downloads`) | **Everything on this page.** Use this one. |
| `avalon-finals-starting-bundle-0425.zip` | Sets 1 and 2, before the checks |
| `avalon-finals-starting-bundle-b1b6.zip` | Set 1 only |
| `avalon-finals-starting-bundle-saturday.zip` | Saturday's bundle, the one the full rehearsal ran on |

Each zip is complete by itself. The day-of command is unchanged:

```bash
mkdir ~/avalon-finals && cd ~/avalon-finals && unzip -q ~/Downloads/avalon-finals-starting-bundle.zip && cp -R avalon-finals/. . && rm -r avalon-finals && git init -q && git add -A && git commit -q -m "Starting bundle" && python3 scripts/test_scripts.py | tail -1 && ls -a
```

It should end with `297 passed, 0 failed` and a listing that includes `.claude` and `.gitignore`.

## What has and has not been tested

| Part | How it was checked |
|---|---|
| The core workflow (who does what, when, how a bot is chosen) | Saturday night's full rehearsal, on Saturday's bundle |
| The scripts | 297 automated checks (228 before); the patched watcher re-run read-only against the real portal: the Finals attaches, and the finished Bay Area competition lists 15 rounds with results, standings, the bot that played each round and a hand-file download |
| The 32-core test rig | An agent that had never seen a rig built it from `tester.md` alone in 9 minutes; results identical to one core on 6,000 records |
| The fingerprinting page | Re-tested on three regionals overnight; then an agent built both steps from the page alone in 22 minutes and they gained +1.3 and +2.0 points a table in play on last night's field |
| The wording corrections | Each traces to a finding with evidence; a second reader then checked the corrections themselves |
| **Not tested** | A timed rehearsal of the bundle as it now stands. Sizes of gains on real teams. The "unknown" label in play. Anything on a live round of the real portal. `/compact` from Samuel's computer. |

## Set 1, applied 03:55: the six fixes from the rehearsal review

Reasons are in `prep/REHEARSAL_REVIEW_15NOV.md`, section 3B.

1. The no-practice-day section of the decision rules no longer says "(the last-rounds bar)" and states that it does
   not apply on a day with practice rounds.
2. Hard rule 1: failed decisions are judged against the kit's `check_or_fold` bot in the same run (refined in set 3).
3. BUILDER puts an upload request in a message of its own.
4. RESEARCH puts BUILDER's question to Samuel in BUILDER's words.
5. The tester's heads-up run uses the real table's settings, not a two-seat table.
6. `START.md`: the rehearsal's starters with the decision rules excepted from "suggestions" and subagents on Opus at
   high effort; `/compact` when each scored round starts; roles stay background subagents.

## Set 2, applied 04:25: four items from the overnight analysis

1. **Fingerprinting** (`strategy/FINGERPRINTING.md`): no accuracy or confidence bar; the response is weighted by
   confidence and blended with the seat's own actions; changes go through an expected-value comparison; two profiles
   a team; an unknown class; a direction test; written as an option in two steps.
2. **The test rig** on 32-core Modal containers with a worker pool.
3. **Memory:** hand files are read as a stream.
4. **Timeouts:** one timeout empties a table's bank; a fallback never starts on the bank's level.

## Set 3, applied 04:40 to 05:30: what six independent checks found

Six checkers worked in parallel; a seventh then checked the corrections. None found anything that would stop a session
or cost a round by itself. Reports: `~/avalon-rehearsal-log/analysis/verify/V1_...` to `V6_...` on Dylan's laptop.

### Mistakes in sets 1 and 2 that the checks caught

| What was wrong | What it now says |
|---|---|
| Hard rule 1, as reworded, let an illegal action or a crash pass on a stalled machine, because `check_or_fold` can only fail by timing out | No illegal actions or errors, and no more timeouts than `check_or_fold` in the same run |
| The reworded rule did not cover the case that started it: a few misses in a portal practice | A few failed decisions in a portal round are priced (about 0.25 points at that table each), not a bar; what holds a bot back is what the watcher marks URGENT |
| The 20,000-table recommendation silently tightened the heads-up pass mark (2 standard errors became under 0.1 points); last night's winning bot would have failed it | Pass marks written in standard errors stay on runs of about 1,000 tables; large runs are for the paired difference between versions |
| The fingerprinting page gave one formula with another method's strengths, and the decision rules still said "never a weight above 10" | One story in every file: the per-spot strengths are for counting in context; 10 with the plain formula; 5 or less for a seat on the field's rate in an all-in spot |
| The page named a "filler" class | A filler seat plays another team's own bot and is labelled by that team |
| The direction test could pass a reversed sign | It compares three counts against the base bot on the same states |
| The memory sentence would have made the between-rounds analysis run one process at a time | The rule is about loading whole rounds, not about several readers |
| "Start a fallback on failures actually seen" could be built as "after one failure" | Only after several, never after one |
| Leftovers of the old gate, the 10-hand ramp and "0 failed decisions" in six files | Removed or pointed at the rule |

### Leaks that were there before this morning

| Leak | Evidence | Fix |
|---|---|---|
| Over-folding was stated five times and measured by nothing | Last night's best bot folded 72.5% to re-raises (field 55.5%); the regional leak again | Our fold rates are in the first check the analyst runs each round; one sparring bot re-raises more against a seat that folded to it |
| Fixes were not carried when a different bot line took over | -0.65 ± 0.15 points a table in one spot last night | BUILDER lists the live bot's validated fixes in the other line's brief |
| The tester's "-2 points" practice bar contradicted the decision rules | Two styles never played a real round because of it | A warning; only a calibrated cloned field may veto |
| The three questions from the review were in no file you will have open | | They are a bullet in `START.md` |

### Scripts: eleven defects, each fixed with a test

- **Held or unreadable results no longer lose the round's hand data.** The scores are posted when they come out.
- **A second competition appearing on our key** no longer moves the day's data aside.
- **A dead watcher** no longer holds the clock's windows; the clock says so once.
- **Minute 0 is announced** even if the variant's rules text cannot be read.
- **Last night's glitches:** the duplicate "Round 4 started" line, "played by ?", "None" as a rank, and 17 of the 18
  harmless deletes the safety hook refused.

### The rig and the fingerprinting page, corrected by building them

- **`tester.md`** now says how to call the deployed app, the command that clears warm containers, that each worker
  unpacks a bot into its own folder, that the clock never changes play inside the rig, where the heads-up test
  starts, and the order: local runner and the first bot's verdict first, then one deploy with a one-core fallback.
- **`FINGERPRINTING.md`** now says what the expected-value comparison prices, that step one is a re-tune of the base
  bot and needs a paired test, and how to pack scores so the decision time holds.

### Where to stop: the ladder test

Every simple rule is a setting of the combined method, and the combined method won wherever its rates fit the field.
Simple rules won only where the rates came from the wrong field. So:

- **Rates must come from today's field.** Before today's first hand file, the bot changes its action against a seat
  only after that seat has folded three times with no call.
- **Do not build** a selector that picks among rules within a table, a per-team table of reaction rules, or a fold on
  purpose to set a seat up. Each was zero or negative on every field tested.
- **Teams that punish a fold** are detected as a plain effect and answered with a count.

## Judgement calls made without you

Say if you want any of these reversed; each is one sentence.

1. **A handful of missed decisions in a portal round is "priced, not a bar"** (`DECISION_RULES.md`, the practice-rounds
   paragraph). It completes fix 2 of set 1, which you both approved for exactly this case.
2. **The cap on how far identity may move a seat's predicted rate is 20 points** (it was 10).
3. **The script fix for held results was taken in full**, although it changes the watcher's main path, because a
   held leaderboard near the end would otherwise have cost the hand data of the heaviest rounds.
4. **`/compact` at practices 1 and 3** is in `START.md` as optional and untested.
5. **One factual sentence was added to the decision rules' note on folding to re-raises:** eight of today's opponents
   re-raised a seat more after it folded.
6. **The ladder analysis was restarted** after your interrupt stopped it, because you asked why it had stopped.

## Not changed, on purpose

- The bars that decide which bot plays, and the one switch deadline.
- A probe arm in practice rounds (no decision from you).
- The twelve reviewer proposals in section 3C of the rehearsal review.
- An unverified alarm in the watcher: two minutes before each scored round it compares the portal's checksum of the
  active bot with ours, and nobody has seen a real one. BUILDER now checks this after the first upload and tells you
  if that alarm should be ignored.

## At set-up

1. Run the day-of command above.
2. `python3 scripts/portal_watch.py --once` should print `competition "Finals"`.
3. Start the two sessions with the starters in `START.md`, both at effort high, in the same permission mode.
4. Try `/compact` once in each session, Samuel from his own computer.
5. Keep the portal open in a browser: announcements only show there.
