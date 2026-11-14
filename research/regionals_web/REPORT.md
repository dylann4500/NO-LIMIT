# Other regionals: Pittsburgh standings and public traces of the top teams (14 November, evening)

Sources: a screenshot of Pittsburgh's final standings (top 12, posted by Pluto's side; Samuel has it), our cached
Bay Area official scores (`research/finals_prep/adaptation/res_q1.txt`), and a GitHub + X + LinkedIn sweep on
14 November. Tags: **[C]** computed from the standings, **[I]** second-hand (a team's own post or repo),
**[J]** our judgement. Scratch scripts were not kept; every number below can be recomputed from the table in §1.

## 0. What changes for Sunday

1. **The Finals almost certainly weight rounds 1, 2, 3, 5, 8, 13.** Pittsburgh used them (every total in the
   screenshot recomputes to within 0.1) and Boston did too; only Bay Area used 1-6. Round 6 is then **41%** of
   the score, rounds 5-6 are **66%**, and rounds 1-3 are only **19%**. The bundle already reads the weights from the
   Format page; this is the prior to expect. [C]
2. **The weighting decided a Finals place at Pittsburgh.** Under 1-6 weights LLinusLLoveBot would have been 4th
   and Claude Mythos 5.5 6th. Under 1, 2, 3, 5, 8, 13, Bay Area's top 5 would have had Team 123 3rd and no
   sandylikesfrogs, and avalon would have been 8th, not 6th. Late rounds are where places change. [C]
3. **Pittsburgh's top teams were far closer together than Bay Area's.** The top 12's spread in a round fell from
   SD 1.80 (round 1) to 0.48 (round 6); Bay Area's stayed at 1.2-1.4. Round 6 range: 1.66 points against Bay
   Area's 4.6. Expect the Finals, 20 regional top teams, to be tighter still: places will turn on small edges
   and on the last round. [C for Pittsburgh; J for Sunday]
4. **Early leaders fade; steady bots climb.** This happened at both regionals. LLinusLLoveBot was 2nd after
   rounds 1-4 and finished 6th, out of the Finals by 0.15 points per table in round 6. Cold Decks (never below
   17.79) won round 6 and took 2nd. Plan for the field to counter whatever is winning in rounds 1-3, and protect
   rounds 5-6. [C]
5. **Pluto's 60-minute bot was the best seen at Pittsburgh.** It scored 21.03 in round 1, 2.2 above anyone else
   in the top 12. It was best in 4 of the 6 rounds and 2nd in the other two, like 2 Curry at Bay Area. Expect it to be the
   strongest bot at the Finals' first scored round. [C; I that the "4 No.1s and 2 No.2s" post is Pluto's]

## 1. Pittsburgh final standings (top 12 of the screenshot)

Weights 1, 2, 3, 5, 8, 13 (sum 32). "Avg" = total / 32, the comparable points per table. Arrow = change in rank
in round 6.

| # | Team (school if shown) | R1 | R2 | R3 | R4 | R5 | R6 | Total | Avg | Shape |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Pluto** (Penn, Carnegie Mellon) | **21.03** | **20.15** | 19.68 | **19.35** | **18.41** | 17.99 | 598.31 | 18.70 | best start, slow fade, never below 2nd in a round |
| 2 ▲1 | **Cold Decks** | 18.73 | 18.51 | 17.79 | 18.87 | 18.16 | **18.42** | 588.27 | 18.38 | steadiest of the top 3 (SD 0.36); won round 6 |
| 3 ▼1 | **Poker is all you need** (Carnegie Mellon) | 15.66 | 18.66 | **19.89** | 18.61 | 17.99 | 17.00 | 570.54 | 17.83 | weak start, rebuilt, peaked R3, faded |
| 4 ▲1 | **Hold Em Trophies** | 18.01 | 17.96 | 17.43 | 17.77 | 17.66 | 17.96 | 569.84 | 17.81 | flattest (SD 0.21): likely one bot all night |
| 5 ▲1 | **Claude Mythos 5.5** | 18.18 | 18.04 | 18.49 | 17.28 | 17.27 | 17.76 | 565.12 | 17.66 | good early, dipped R4-R5, in by 0.06 |
| 6 ▼2 | LLinusLLoveBot | 18.81 | 18.92 | 19.36 | 18.35 | 17.35 | 16.76 | 563.09 | 17.60 | 2nd after R1-R4; collapsed late; wildcard candidate |
| 7 ▲1 | AEPi AK | 15.95 | 15.31 | 16.16 | 16.63 | 17.89 | 17.90 | 553.93 | 17.31 | late riser (+1.7 R4-6 vs R1-3) |
| 8 ▼1 | Cheng Theory (Illinois) | 16.99 | 17.50 | 16.59 | 17.39 | 17.38 | 17.25 | 552.04 | 17.25 | steady |
| 9 ▲1 | Ferdabot II (Carnegie Mellon) | 18.20 | 16.64 | 16.73 | 15.78 | 16.81 | 17.91 | 547.87 | 17.12 | |
| 10 ▼1 | PHASEONE10841 (Carnegie Mellon) | 15.95 | 14.61 | 17.13 | 16.98 | 17.20 | 17.18 | 542.29 | 16.95 | late riser |
| 11 | BREAD FROM GERMANY (CMU) | 17.48 | 16.90 | 15.88 | 15.96 | 16.79 | 17.19 | 536.5 (computed; hidden in the screenshot) | 16.77 | |
| 12 ▲2 | leMinecraft (Carnegie Mellon) | 13.81 | 16.13 | 17.12 | 15.97 | 16.41 | 17.23 | 532.63 | 16.64 | late riser |

Bold = best of the top 12 that round (a team below 12th could have beaten it; unlikely given the totals).
Other Pittsburgh team names seen in the screenshot's chat list: Chansey, verity, Game Theory Optimal, AABLAHAJ,
SIGSEGV. Field size: **146 teams** (leMinecraft's repo description: "Team LeMinecraft, rank 12/146") [I].

**Rank after each round** (cumulative): Pluto 1st throughout. LLinusLLoveBot 2nd after R1-R4, 4th after R5, 6th
after R6. Poker is all you need 6th → 3rd (R3) → 2nd (R5) → 3rd. Cold Decks 3rd → 5th (R3) → 2nd. Claude Mythos 5.5
4th-6th all night; Hold Em Trophies 5th-6th all night, 4th at the end. [C]

## 2. What decided the places [C]

- **Pluto over Cold Decks (+10.1 total).** Weighted round margins: +2.3, +3.3, +5.7, +2.4, +2.0, then −5.6 in
  round 6. Pluto won it in rounds 1-5; Cold Decks won the 13x round outright.
- **Claude Mythos 5.5 over LLinusLLoveBot (+2.0 total).** LLinusLLoveBot led by 10.9 weighted points after round 5;
  round 6 swung 13.0 the other way (17.76 vs 16.76). LLinusLLoveBot needed 16.91 in round 6 and scored 16.76.
- **Noise.** Bay Area's official round scores had SE about 0.15. With these weights the SE of a team's average is
  about 0.08, so 5th vs 6th (0.06 apart) was a coin flip, 1st vs 2nd (0.31) was not. Effective number of rounds:
  3.8 under these weights against 4.9 under 1-6: one round's luck matters more.

## 3. Pittsburgh against Bay Area [C]

| | Bay Area (148 teams, weights 1-6) | Pittsburgh (146 teams, weights 1, 2, 3, 5, 8, 13) |
|---|---|---|
| Winner's average per table | 20.43 (2 Curry) | 18.70 (Pluto) |
| 5th place average | 18.16 | 17.66 |
| Gap 1st-2nd / 5th-6th / 1st-12th | 0.38 / 0.22 / 3.43 | 0.31 / 0.06 / 2.05 |
| Top-12 SD, R1 → R6 | 3.22 → 1.43 | 1.80 → 0.48 |
| Top-12 range in R6 | 4.6 | 1.66 |
| R1's top 5 (within the top 12): mean R1 → R6 | 21.4 → 17.4 | 19.0 → 17.8 |
| Winner best-of-top-12 in | 4 of 6 rounds | 4 of 6 rounds |
| Rank correlation of rounds, top 12 | (see adaptation report: 0.79-0.88 over 127 teams) | 0.64, 0.78, 0.79, 0.85, then 0.45 into R6 |

Boston, for scale: Du-o 727.26 = 22.7 per table, 5th 641.48 = 20.0 [I]. Bigger field (231-270 teams), so more
weak tables to farm.

Why Pittsburgh compressed [J, untested]: the two-board, half-pot variant splits more pots, which shrinks every
edge; and Pittsburgh teams had two regionals' worth of public write-ups to learn from (one team's playbook
cited ours). Field size doesn't explain it: 146 teams against Bay Area's 148. Whatever the cause, the Finals
field is stronger than any regional's top 12.

## 4. Pittsburgh's finalists, read from the score shapes [J unless tagged]

- **Pluto**: the best minute-60 build of the regional; decayed about 0.3-0.9 a round as the field adapted, yet
  stayed top 2 every round. Treat its first scored-round bot as the strongest in the room. A team member's post
  says the policy was "insanely dominant ... 4 No.1s and 2 No.2 across 6 rounds" [I; LinkedIn repost of an X
  post, team name not shown in the snippet, but the round record matches Pluto's rows exactly].
- **Cold Decks**: steady, and best in the 13x round. Probably a robust, not very exploitable bot that the field's
  late counters did not hurt.
- **Poker is all you need**: 15.66 → 18.66 → 19.89 means a rebuild after round 1; then 18.61 → 17.99 → 17.00. It fits
  a public Pittsburgh bot's notes: the round-3 winner "applied steady pressure with small raises", and by round 4
  "opponents learned to fight back" (`finals_pack/notes/pre/field.md` §5). Expect it to change bots between rounds.
- **Hold Em Trophies**: SD 0.21 over six rounds, never best, never bad. Its practice-round stats should predict
  its scored rounds well.
- **Claude Mythos 5.5**: solid early, dipped, recovered in round 6.
- **LLinusLLoveBot** (6th): strongest early-round profile after Pluto; likely wildcard candidate if wildcards go
  by regional placing.

## 5. Finalists as far as known

Bay Area: 2 Curry, Lemonade, AZ, sandylikesfrogs, Team 72, plus avalon (wildcard). Boston: Du-o, Situational
Awareness, BHTG, Preesh, 0_o GTO Slop [I]. Pittsburgh: Pluto, Cold Decks, Poker is all you need, Hold Em Trophies,
Claude Mythos 5.5 [C, top 5 of the standings]. That is 16 of 20. Four wildcards unknown; candidates: LLinusLLoveBot
(Pittsburgh 6th), Team 123 (Bay Area 7th, 19.7-19.8 in R4-R5), and a Boston team "Magnus RLsen" whose member's
LinkedIn says "6th out of 231" [I, snippet only, and another snippet from the same profile claims a win:
unconfirmed].

## 6. Public traces found on 14 November (GitHub, X, LinkedIn)

Read through `gh` and web search only; nothing cloned or run, nothing copied. Already covered in
`finals_pack/notes/pre/field.md` §5 and not repeated: CapitanoZ, noe2971, tranthuanhieu1610 (Pittsburgh),
nnicholas-c (Bay Area), AlexPha45 (Boston).

**No repo or post names a Finals variant, a finalist list, or Boston's or Pittsburgh's full standings.** No top-5
team from any regional has public code. Nobody's commits on 13-14 November look like Finals preparation.

- **Pittsburgh's winner, X/LinkedIn** [I]: the X post itself isn't indexed by search; a LinkedIn repost of it by
  a team member reads "Our policy was insanely dominant, scoring 4 No.1s and 2 No.2 across 6 rounds, winning
  the regional by a huge margin" (search snippet; LinkedIn blocks fetching). The screenshot in §1 is the useful
  part. No strategy is described.
- **leMinecraft, Pittsburgh 12th** (github.com/KeyaanMatrix/no-limit-poker-bot, post-event write-up pushed 14
  Nov) [I]: "rank 12/146". Their own downloads: "the best team we met scored between about 18 and 21 points per
  table" (matches Pluto), their bot7/bot8 scored 16.0-17.0 and "placed between about 5th and 13th", and "the
  field changed between rounds as teams updated their bots". Bot: push/fold at 12bb or less, re-shove over raises
  at 25bb or less, small re-raise deeper, sampled strength averaged over both boards, discard keeps the pair that
  wins most over sampled rivers, 14 counters per seat. Same family as the two Pittsburgh bots in field.md §5.
- **Bay Area field statistics from a participant's downloads** (github.com/YeziShanYang/ml-poker-bot,
  `docs/RESULTS.md`, about 127 entries per round, team and rank not stated) [I; checked against the raw file]:
  - Points correlated with opening more (+0.43), c-betting more (+0.40) and folding to opens (+0.36); against
    limping (−0.46) and calling opens (−0.31). "The top entries raised or folded preflop, opened 20-30% of hands,
    c-bet about 75% of flops."
  - Heads-up flop c-bet fold-out (everyone folds) by size: 0.45 at 0.4 pot, 0.60 at 0.55, 0.68 at 0.7, 0.73 at
    0.9, 0.78 at 1.2, against bluff break-evens of 0.29-0.55: the field over-folded at every size. This agrees
    with our own fold-by-size table (`strategy/EVIDENCE_TABLE.md` row 33); it's an independent check, not new.
  - Re-jams over a single open at 15-50bb: 74-78% fold-out, +1.5 to +2.8bb each; worse by 8-10 points per extra
    player left to act; over 50bb they lost. Open-jams at 12-60bb: 80-85% fold-out.
  - "4 BB opens earned about twice what 2.5 BB opens did in every position": observational (different bots chose
    different sizes), so grade it D for a sizing decision.
- **Bay Area practice-round group profile** (github.com/juanponcedeleon/PokerBotArena,
  `strategy/05-opponent-modeling.md`, practice 1, 123 teams; the author's team was 99th) [I]: top 10 median VPIP
  34.5%, PFR 26%, 22.1 points; bottom 30 VPIP 35.5%, PFR 14.5%. 19 "tight folder" teams scored 14-19 in that practice
  (fits field.md §2: practice 1 overstates tight play). The top 10 almost never exposed the card that paired the
  flop (0.5%), against 50% for the bottom 30.
- **"AZ-style preflop"** (github.com/denfujita/poker, `validation/az-v4-candidate.md`, a Bay Area entry built during
  the event) [I]: a "teammate candidate" with 2.5bb opens, open cut-offs by seat (early .17, HJ .26, CO .34, BTN .65,
  SB .70 of hands), continue against 3-bets with only the top 3-6%. **Whether "AZ" is Bay Area's 3rd-place team is
  unconfirmed.**
- **Boston** [I]: one entry's notes (github.com/mjyu20277/boston-pokerbot, `STRATEGY_README.md`): busting before hand
  50 was "almost always terrible", turn and river calls were very bad, tables that spent more flop-chips did
  better. A LinkedIn snippet puts a team "Magnus RLsen" 6th of 231 (unconfirmed, §5).
- **Sequoia, 10 November** (x.com/sequoia/status/2120270083830493656, read via a public mirror): top 20 teams of
  800+ participants; a company side event (Etched, Factory, Applied Compute, DoorDash, fal and others); proceeds to
  Khan Academy. Nothing on the variant or the format.
- **Nothing useful:** jerry-m-xu/pokerbots (Boston, written before the kit), EthanXu07/poker-bot-overview (code
  private, simulator only), lemonteaustin/pokerbot (simulator only; no link to Bay Area's "Lemonade" found),
  Brady-5300/pokerBot (a different platform), AbsCtrl/sequoia-pokerbot (empty), and about fifteen unrelated
  poker repos.
- **Searched, nothing found:** any X or LinkedIn post by the other 14 named top-5 teams; a Sequoia recap of Boston
  or Pittsburgh; university news about Pittsburgh.
