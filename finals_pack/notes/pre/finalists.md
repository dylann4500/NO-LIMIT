# The known finalists: what each did at its regional, and how to recognise it on Sunday

Drafted Saturday 14 November 2026, 06:30-06:55 PST, by a research session, for `scout` and `challenger`. Notes only: the
scripts behind the numbers were throwaway and have been deleted. Rates are counted exactly as in
`stat_definitions.md`; classes are `field.md`'s.

**Grades** (as in `strategy/EVIDENCE_TABLE.md`): **A** = measured on the Bay Area hand files, a description of what a
team did, with its sample size. **C** = a judgement, or a way to use a fact that nobody has tested. **[I]** =
second-hand (another session's summary of Boston data, or a public page). Nothing here is grade B: no counter in this
note has been played against anyone.

**Everything about Sunday is a prior.** Every bot is written new on the day for a new variant, 80-90% of regional
teams changed bot every round, and three of the eight Bay Area teams below ended the regional on a bot unrelated to
the one they started with. Use a card only after the recognition table (section 2) says the team is playing the same
family, and then as a candidate (grade C), never as a reason to block a change.

## 1. Summary

- **Measured:** the Bay Area's top five, the three teams just behind us (possible wildcards) and our own bot, in all
  six scored rounds and eight practice files: about 1,100 tables per team per scored round, always with us at the
  table. **Second-hand:** Boston's five and its 6th. **Nothing usable:** Pittsburgh's winner.
- **Four of the eight Bay Area teams read each seat during a table, and so do at least four of Boston's five [I].**
  2 Curry and Team 123 re-raise a seat again once it folds; Team 72 and Team 123 bet into seats that fold; AZ defends
  its big blind and calls down by how often a seat raises and bets. Lemonade, Team 82 and pocket rockets show nothing.
  These rules were in the very first practice bots (2 Curry in practices 1 and 2 together: 55% against 9%, n = 354
  and 553), so they are the part of a team most likely to come back. (A; C for Sunday)
- **The two teams that scored 20 a round did opposite things and neither chased the field.** 2 Curry: wide pressure,
  small tweaks every round. Lemonade: limps and shoves, one rewrite, then the same bot for four rounds. (A)
- **Fold to a 4-bet splits the group in two (A).** The teams that re-raise wide fold to 4-bets 73-86% (2 Curry,
  Team 72, Team 123, pocket rockets in round 6). The teams whose re-raises are mostly all-in almost never fold
  (Lemonade 1%, AZ 7%, sandylikesfrogs 15%).
- **Against us (A).** Our points fell at every one of these teams' tables. Beyond what each team's own score predicts,
  the losses that stand out are Team 123's last four rounds (-3.1 ± 0.3 a table against our other tables),
  2 Curry (-1.05 ± 0.25 beyond its score) and sandylikesfrogs (-1.11 ± 0.26). Team 82 is the only one we did
  relatively well against (+0.35 ± 0.27, not significant). Appendix D has the table.
- **When these teams changed bot, we usually saw it first in the scored round:** of their 12 larger changes after
  round 2, 8 were not in the practice round before (3 were, 1 was half there), and AZ's practice bot differed from
  its scored bots in 3 of 4 practices. (A)
- **Most dangerous on Sunday (C):** 2 Curry, Du-o and Lemonade, with Team 123 if it is a wildcard. Reasons in
  section 3.

## 2. Recognition table for practice 1

Each opposing team sits at about 7 of our 19 opponents' seats, so a 1,000-table practice file holds about 370 of its
tables. **Same family** = at least two of its three rates inside the band. **Rewritten** = two or more outside.
Otherwise **unclear**: test again on practice 2. Bands are the team's regional range widened by about 5 points,
because a new variant moves every level. "Tables" is how many of that team's tables give enough chances for a rate
5 points inside the band to be 2 standard errors from its edge (or, for a contrast, 150 chances on each side), at
the regional's 90 hands dealt per seat per table. Run the cross-tabs A, B, D and H of Appendix C on every team
(E as well, for shove calls): they are the same code for all of them.

| Team (regional result) | Regional family | Rate 1 | Rate 2 | Rate 3 | Tables | Also look for |
|---|---|---|---|---|---|---|
| **2 Curry** (Bay Area 1st) | Wide pressure, learns seats | 3-bet 28%+ with under 5% of them all-in (was 32-39%, 3%) | Opener folds to a 3-bet 75%+ (80-87%) | Cross-tab A: re-raise after one fold minus after one non-fold, +20 or more (+30 to +43) | 10 / 40 / 80 | Every open exactly 2.00bb, every 3-bet 3.25x; never limps, flat-calls 1-2%; small blind opens 97% |
| **Lemonade** (2nd) | Limp or shove | Open-limp 15%+ while raising first in under 12% (21-24%; 8-11%) | 60%+ of its 3-bets all-in (72-93%) | A limper facing a raise folds under 25% (7% from round 3; 24% before) | 10 / 65 / 45 | Level 1: raises first in under 1%; 0% from early and middle seats |
| **AZ** (3rd) | Shove re-raiser with seat reads | 75%+ of its 3-bets all-in, 3-bet 12-22%, no limps (80-86%; 14-20%) | Cross-tab H: big blind folds to a tight opener minus to a loose opener, +25 or more (+36 to +54) | Open-shove at 10-15bb 40%+ (43-47% from round 4; 29-31% before) | 40 / 120 / 300 | Big blind folds 74-81% at level 1 but 49-57% overall; folds to 4-bets under 10% |
| **sandylikesfrogs** (4th) | Loose, three styles | Raise a flop bet 13%+ (16-22%) | Opens in hands 11-20 of a blind level minus hands 1-10, +6 or more (+7 to +13) | 15%+ of its non-all-in 3-bets at or near the minimum, 1.5x the open (19-31%) | 30 / 15 / 110 | Open-limp 4-11%; 4-bet 9-14% |
| **Team 72** (5th) | Exploits folders | Cross-tab B: heads-up bet into a seat that folds over 67% minus one under 34%, +25 or more (+37 to +41) | Cross-tab D: button and small-blind opens against a folding big blind minus a defending one, +12 or more (+18 to +19) | Opener folds to a 3-bet 48-62% (53-59%) | 90 / 70 / 70 | 3-bets 2.5x, at the same rate from the blinds as elsewhere (26% and 26%) |
| **Team 123** (7th, wildcard?) | Hyper-aggressive, learns seats | Big blind folds to an open under 10% (3-5%) | Big blind re-raises an open 70%+ (87-89%) | 3-bet 35%+ and folds to 4-bets 65%+ (41-46%; 66-86%) | 15 / 30 / 240 | Cross-tab A +15 or more (+20 to +21); calls shoves of 10bb or less 45% |
| **Team 82** (8th, wildcard?) | Tight opener that folds | Opener folds to a 3-bet 78%+ (78-87%, all six rounds) | Calls a shove of 10bb or less under 22% (17-19%) | Small blind opens first in 95%+ (100% from round 3) | 40 / 80 / 5 | Flat-calls 1-4%; heads-up opens 100% |
| **pocket rockets** (9th, wildcard?) | Raise or fold, small raises when short | Open-shove at 10-20bb under 8% while raising 45%+ there (0-5%; 51-53%) | Opener with 10-20bb folds to a 3-bet 72%+ (79-80%) | Flat-calls under 4% and never limps (1%; 0%, rounds 3-6) | 10 / 200 / 10 | Opens 2.25bb, 3-bets 2.5-2.75x; bets the river only 30-35% when checked to |
| **avalon** (6th; how others see us) | Folds to pressure, shoves short | Opener folds to a 3-bet 82%+ (84-87%) | Open-shove at 10bb or less 72%+ (78-80%) | 70%+ of its 3-bets all-in (77-80%) | 50 / 300 / 50 | Opens 2.25bb, 3-bets 3.5x; folds to river bets 70-76% |
| **Du-o** (Boston 1st) [I] | Wide pressure, learns seats on every test | 3-bet 35%+ against a lone opener (44% in the measured spot) | Cross-tab A +15 or more | Cross-tabs D and B both clearly positive (it had Boston's largest re-raise response and the largest steal response at either regional) | 10 / 80 / 90 | Button and small-blind opens only about 49% |
| **Situational Awareness** (Boston 2nd) [I] | Wide pressure, learns seats | 3-bet 30%+ (39% in the measured spot) | Cross-tab A +10 or more | Cross-tab E: calls shoves more from seats that shove often | 10 / 80 / 150 | No response to folding big blinds or to folders postflop |
| **BHTG** (Boston 3rd) [I] | Steals and bets, mild reads | 3-bet 20-32% (26%) | Button and small-blind opens 60%+ (67%) | Cross-tabs D and B mildly positive; A weak | 10 / 15 / 90 | |
| **Preesh** (Boston 4th) [I] | Static: no seat response | 3-bet 18-28% (23%) | Button and small-blind opens 62%+ (69%) | Cross-tabs A, B, D all flat | 10 / 15 / 90 | 19.8 a table in Boston's last round |
| **0_o GTO Slop** (Boston 5th) [I] | Copies the leaders from data | Button and small-blind opens 70%+ (78%) | Cross-tab A +8 or more (it was fading: half as strong in the last round) | Cross-tab B positive | 15 / 80 / 90 | 12 versions in six rounds: most likely of all to be rewritten |
| **Pittsburgh's winner** (Steven Peng's team) [I] | Unknown | | | | | First in four rounds, second in two; nothing else found |

The Boston bands are looser than the Bay Area ones: they come from a regression summary in the archive, measured at
one friend's tables, and its unit (response per 10 points of a seat's deviation) is not our cross-tab's. For scale,
the same summary gave 2 Curry +31.9 where our cross-tab A gives +35, and Team 72 +12.2 on bets into folders where
cross-tab B gives +39. (C for the conversion.)

**Three things that make a practice-1 reading wrong** (A, regional): two of these eight teams were not seated in
practice 1 (Lemonade, Team 72); Lemonade and Team 123 played throwaway bots in the build practices (Team 123 an
all-in-every-hand bot in practice 3); and a team's rates in a field of drafts differ from its scored rates. The seat
rules were the stable part: 2 Curry's, Team 72's and AZ's were all measurable by practice 2.

## 3. What the known finalists have in common, and where our bot differs

**In common** (round 6, the eight Bay Area teams; A):

1. **They open wide and don't limp.** Seven of eight opened 39-53% first in (the top 20's median was 42%); the small
   blind opened 68-100% in seven. Only Lemonade (21%) and sandylikesfrogs (6%) limped.
2. **Half had turned to pressure by round 6.** 2 Curry, Team 72, Team 123 and pocket rockets re-raised 26-41%; the
   other four 13-20%. From the big blind the eight re-raised a single open 23-87% of the time (median 46%; the whole
   field's median was 12%). Boston's five re-raised 23-44% in the spot the archive measured [I].
3. **They defend the big blind:** six of eight folded it under 50% in round 6 (field 58%), and three teams cut their
   fold rate by 25-50 points in the last round alone (Team 82, pocket rockets, sandylikesfrogs at level 1).
4. **Fold to a 3-bet stayed high in five:** 2 Curry 81%, Team 82 83%, AZ 77%, pocket rockets 76%, sandylikesfrogs 72%.
   Team 72 and Team 123 call instead (53% and 52% folds). Nobody in the group 4-bet more than 14%.
5. **Postflop is plain:** c-bets 55-90% (median 73%), flop bets raised 1-11% of the time by seven of eight
   (median 6.5%; sandylikesfrogs 16%), and the flop bettor folds to a raise 60% in the median.
6. **Short stacks shove, but less than we do:** first-in shoves at 10bb or less 27-61% (median 47%).
7. **Half learn seats** (section 1), and so do both regional winners we have data on.

**Where our round-6 bot differed most from the eight** (A; gap measured against the spread of the eight):

| Our rate | Us | The eight: median (range) | Reading (C) |
|---|---|---|---|
| Fold to a river bet | 76% | 50% (39-64%) | The highest of the nine; a river bet against us is close to free |
| Fold to a small 3-bet (under 2.6x) | 80% | 49% (9-66%) | In the median the eight continue half the time against a cheap re-raise |
| Fold to any 3-bet | 87% | 74% (30-83%) | Highest of the nine; what 2 Curry's and Team 123's rule feeds on |
| Open first in; from the button; from the small blind | 34%; 44%; 59% | 42%; 58%; 78% | We steal less than every team but Lemonade |
| Raise over limpers | 16% | 36% (21-49%) | Lowest of the nine |
| Open-shove at 10bb or less | 78% | 47% (27-61%) | Highest of the nine |
| Share of our 3-bets that are all-in | 78% | 25% (2-84%) | Only AZ and Lemonade are similar |
| Raise a flop bet | 13% | 6.5% (1-16%) | Only sandylikesfrogs is higher |
| Heads-up: call a first-in shove; open | 21%; 68% | 37%; 79% | Only Team 82 calls less when two are left |

**Most dangerous (C).** *2 Curry*: the only team above 20 in all six rounds, the same family from practice 1 to
round 6, and the team whose rule fits our largest gap. *Du-o* [I]: won Boston clearly (727 to the 5th's 641),
responded to seats on almost every test the archive ran, and re-raised about as often as 2 Curry. *Lemonade*:
19.3-20.7 with a style none of the other seven used and no rule of ours aimed at it; a field of pressure bots has
little to act on, because it rarely raises first in. *Team 123*, if invited, is the opponent that cost us most per
table and the fastest rewriter in the group.

## 4. Bay Area cards

Per-round rates for every team are in Appendix B; seat tests in C; our results in D; practice against scored in E.
"Beyond its score" is our loss at a team's tables after removing what a team of that strength costs an average
opponent (Appendix A). Each card's "use" lines are grade C: the rate is measured, using it is untested.

### 2 Curry (1st: 20.4, 20.2, 21.2, 20.5, 20.4, 20.1)

- **Class:** wide pressure with seat learning, all six rounds. Opens 43-54% (always 2.00bb), 3-bets 32-39% (always
  3.25x, 1% all-in), never limps, flat-calls 1-2%, c-bets 90%.
- **Changed:** small steps every round, never a rewrite: opens 54% to 43%, big blind folds 54% to 32%, turn bets when
  checked to 57% to 77% (round 4), more steals from folding big blinds (rounds 5-6). Practice showed the next scored
  bot in 3 of 4; round 3's changes were not in the practice before it.
- **Within a table:** re-raises a lone opener 18% with no history, 42% after one fold, 7% after one non-fold, 77%
  after three or more with 80%+ folds (n = 48,846; 16,683; 12,802; 17,574). It also reads who re-raises it: it folds
  83% to a seat's re-raise, 65% once that seat has re-raised three times, and then 4-bets 13% (n = 4,932; 4,981).
- **Against us:** 15.9 at its tables against 18.1 elsewhere: -2.21 ± 0.25, of which -1.05 is beyond its score.
- **Use:** (1) Do not fold the first re-raise at a table; 4-bet it. It folded to 80% of 4-bets (n = 10,940; 74% to
  all-in ones in rounds 3-6). (2) Re-raise its 2bb opens: 83% folds (n = 38,630), 88% to all-in re-raises. (3) Raise
  its flop bet: as the first bettor it folded to a raise 63% (n = 3,292); this one depends on the twist.
- **To have removed it:** two thresholds. Our public write-up names its 81% fold, so allow 50% that it folds under 70%
  on Sunday. The seat rule is its edge and will stay.

### Lemonade (2nd: 19.8, 19.3, 20.7, 20.6, 20.1, 19.6)

- **Class:** limp or shove, all six rounds. Open-limps 21-24%, raises first in 8-11% (0% from early and middle seats,
  2% on the button, 46% in the small blind).
- **Changed:** one rewrite before round 3, already in the practice before it: 3-bets 22% to 13% (all-in 20% to 10%),
  flat-calls 9% to 19%, turn bets when checked to 13% to 80%, folds to turn bets 35% to 54%. Then the same bot for
  four rounds.
- **Within a table:** nothing from round 3 on (cross-tabs A, B and D all within 3 points).
- **Against us:** -1.44 ± 0.25; -0.34 beyond its score (not significant).
- **Use:** (1) Its limp is not weak: raised, the limper folds 7% and re-raises 44% (n = 20,581). Raise its limps
  for value only. (2) 72% of its 3-bets are all-in and it folds to a 4-bet 1% (n = 627): never 4-bet as a bluff.
  (3) It folds to 73% of flop bets and raises under 1% (n = 24,988); its own flop bet folds to a raise 79%
  (n = 3,135). Twist-dependent.
- **To have removed it:** these are the design, not leaks. A team that froze a 20-point bot for four rounds will
  probably bring the same plan; expect limps again and nothing to steal from, since it never raises light.

### AZ (3rd: 21.2, 19.4, 17.9, 19.1, 18.0, 17.3)

- **Class:** none of `field.md`'s four. A shove re-raiser with seat reads: 3-bets 14% (11 all-in) in rounds 1-3 and 20%
  (17 all-in) after; folds to a 4-bet 6.5% (n = 872).
- **Changed:** one jump at round 4: opens 2.50bb to 2.25bb, folds to 3-bets 68% to 79%, open-shoves at 10-15bb 29% to
  47%, calls of small shoves 40% to 31%. **Its practice bot differed from the scored bots on both sides in 3 of 4
  practices** (in two of them it re-raised 12-15% and folded the big blind 60-64%, against 20% and 49% scored).
- **Within a table:** big blind folds 75% to a seat that has opened under 25% of its chances and 30% to one over 45%
  (n = 9,359; 8,555). Folds to a first-time 3-bettor 81%, to a seat with three earlier 3-bets 58% (n = 4,211; 4,310).
  Folds to a bet 72% from a seat that rarely bets, 45% from one that bets often. Bets into folders (+13).
- **Against us:** -1.38 ± 0.25; -0.46 beyond its score.
- **Use:** (1) Steal its big blind early in each table: at level 1 it folded 78% (n = 9,043). (2) The first two
  re-raises against it at a table get 78-81% folds. (3) Never 4-bet it as a bluff, and do not expect a bet to work
  once we have bet often.
- **To have removed it:** these are deliberate counters and will return. The use is to stay under its thresholds,
  which a rewrite could move.

### sandylikesfrogs (4th: 20.7, 19.7, 18.3, 18.3, 18.5, 16.9)

- **Class:** three styles. Round 1 loose (opens 58%, VPIP 50%, limps 11%). Rounds 2-5 medium (opens 34-36%) and hard
  to push: folds to 3-bets 38-57%, 4-bets 12-14%. Round 6 loose again (opens 52%), and it lost 1.6 points.
- **Changed:** every round; practice showed the previous scored bot 4 of 4 times, so round 6's bot was never seen.
- **Within a table:** a clock, not a read: it opens 7-13 points more in hands 11-20 of each blind level than in hands
  1-10, in every round and at every level (the other eight: +1 to +4). Mild reads: steals more from folding big
  blinds (+6),
  re-raises frequent openers (+7).
- **Against us:** -2.02 ± 0.26; -1.11 beyond its score (round 5: -3.2).
- **Use:** (1) Its opens late in a blind level are about 10 points wider: re-raise and defend more in hands 11-20.
  (2) It raises 16-22% of flop bets (n = 44,944; field 9%) and folds to 4-bets 15% (n = 2,067): no thin c-bets, no
  4-bet bluffs. (3) Heads-up it calls a first-in shove 50% (n = 4,328): shove for value only.
- **To have removed it:** this team changes style, so the rates may be void; the clock survived all three styles.

### Team 72 (5th: 22.2, 20.2, 17.9, 17.9, 17.8, 17.4)

- **Class:** rounds 1-3 a wide opener that calls (opens 45-48%, 3-bets 3-5%, folds to 3-bets 55%); rounds 5-6 wide
  pressure (3-bets 26-27% at 2.5x, the same from the blinds as elsewhere). Best round-1 score of anyone, then faded.
- **Changed:** added 3-bets in round 4 (17%) and round 5 (27%), then 4-bets (14%) and open-shoves at 10-15bb (1% to
  32%) in round 6. **It uploaded after every practice:** none of the three changes was in the practice before it.
- **Within a table:** heads-up it bets 53% into a seat that has folded under 34% of the bets it faced and 92% into one
  over 67% (n = 18,975; 11,577; the same in every round and from practice 2). Opens the button and small blind 62%
  against a defending big blind, 81% against a folding one (n = 13,721; 27,702).
- **Against us:** -1.57 ± 0.26; -0.64 beyond its score.
- **Use:** (1) Once a seat has folded twice, its bet is nearly any two cards: call down or raise then, or do not fold
  the first two. (2) 4-bet its 3-bets: it folded 74% (n = 3,377, rounds 4-6). (3) 3-bet it for value only: it folds 55%
  (n = 34,033).
- **To have removed it:** betting into folders is what won it round 1 and is why it faded as the folders left.
  Expect it again.

### Team 123 (7th: 9.9, 12.8, 17.8, 19.8, 19.7, 18.1; possible wildcard)

- **Class:** three unrelated bots. Round 1 tight (VPIP 14%); round 2 shove-heavy; rounds 3-6 a hyper-aggressive
  rewrite, never shown in the practice before round 3.
- **Rounds 3-6:** 3-bets 42% (65% from the blinds). In the big blind it folds to a single open 3.8% and re-raises
  89% (n = 28,282). Folds to 4-bets 79% (n = 5,199; 66% rising to 86%). Calls shoves of 10bb or less 46%, and 75%
  heads-up. Folds to flop bets 39%.
- **Within a table:** 2 Curry's rule, milder: re-raises 44% after one fold, 24% after one non-fold, 9.5% after two
  non-folds (n = 11,846; 6,133; 1,774). Bets into folders 72% to 91%; steals more from folding big blinds (+9).
- **Against us:** in rounds 3-6 we scored 15.3 at its tables against 18.4 elsewhere: -3.1 ± 0.3, the worst of any
  team.
- **Use:** (1) 4-bet its re-raises, above all the ones from its big blind. (2) Do not open light when it is in the
  big blind. (3) No light shoves into it; bet for value postflop.
- **To have removed it:** its fold to 4-bets rose all night, so nobody punished it there. But this team rewrote
  twice in six rounds: a different bot on Sunday is more likely than not.

### Team 82 (8th: 18.6, 17.1, 16.2, 17.9, 17.7, 18.5; possible wildcard)

- **Class:** rounds 1-5 one tight family (VPIP 20-24%, 3-bets 3-8%, flat-calls 1-4%, big blind folds 75-89%), shoving
  when short. Round 6 rewrite, half-visible in the practice before: big blind folds 75% to 25% and re-raises 53%,
  3-bets 17%, folds to 4-bets 65% (n = 395).
- **Within a table:** nothing on A, B or D.
- **Against us:** -0.41 ± 0.27, and +0.35 beyond its score: the one team here we did relatively well against.
- **Use:** (1) Re-raise its opens: it folded 84% in all six rounds (n = 27,812), and still 76% to a seat that had
  re-raised three times. (2) Shove wide into it: it called shoves of 10bb or less 18% (n = 19,157), of 10-15bb 8%,
  and 19% heads-up. (3) Its small-blind open is any two cards (100% from round 3, n = 30,394).
- **To have removed it:** the fold to 3-bets survived the round-6 rewrite, so it is probably in the team's plan.

### pocket rockets (9th: 18.9, 16.9, 18.0, 17.6, 16.6, 17.8; possible wildcard)

- **Class:** rounds 1-2 limped 21-24%; rounds 3-5 raise or fold (opens 45%, 3-bets 15%); round 6 wide pressure (3-bets
  28% at 2.5-2.75x, big blind folds 64% to 40%), shown in the practice before it.
- **Within a table:** nothing on A, B or D.
- **Against us:** -1.00 ± 0.26; -0.25 beyond its score.
- **Use:** (1) It never open-shoved above 15bb (0 of 259,671 chances) and 5% at 10-15bb; it makes a small raise
  instead (51-53% of first-in chances at 10-20bb) and folds to a re-raise 79-80% there (n = 5,693). Re-shove over
  its raises when it has 10-20bb. (2) 4-bet its round-6 3-bets: 73% folds (n = 1,115). (3) It bets the river 33%
  when checked to (n = 5,721): its river bet is rarely a bluff.
- **To have removed it:** the short-stack habit survived three versions; adding a push-or-fold table would end it.

### avalon (6th: 18.1, 16.7, 19.1, 18.3, 18.0, 17.5; our final bot, for contrast)

- Folds to 3-bets 84-87% in every round, 80% even to small ones; folds to river bets 70-76%; open-shoves 78% at 10bb
  or less; 78% of its 3-bets are all-in; opens 33-34%; raises over limpers 16%.
- Its own seat rules show in the same tests: bets into folders (+13), big blind defends against frequent openers
  (-25), nothing on re-raises.
- What a team that profiled us would do (C): re-raise our opens with any two cards after one fold, bet every river,
  call our short shoves at the right price. A public repository already summarises our write-up, including a
  counter to a "write-up copy" (`field.md` section 5).

## 5. Boston's and Pittsburgh's finalists (all second-hand)

There is no raw Boston or Pittsburgh hand data on this laptop. The Boston rows come from the archive's summaries of
13 files from a friend's team (about 370 tables per team per round, one viewpoint, no official scores:
`research/finals_prep/adaptation/res_boston*.txt`; the order of its rounds was inferred there), and from public pages
found today. The archive has no per-team style rates for Boston, only the seat-response tests and the rate in each
tested spot.

| Team | From the archive [I] | Public [I] |
|---|---|---|
| **Du-o** (1st, 727.26) | Re-raised 44% of the time against openers with a history at the table (52,179 decisions) and more against seats that had folded (+21.7 per 10 points, 19-24 in every round). Opened the button and small blind 49%, and more against big blinds that fold (+8.0, the largest in either regional). Bet 74% when checked to heads-up, more into folders (+16.2). Opened 8.3 points less into the friend's big blind than into others' in matched spots | A rival's agent summed it up as aggressive play and larger auction payments, and built proxies of it from hand histories. Members: nothing found |
| **Situational Awareness** (2nd, 715.32) | Re-raised 39%, more against seats that had folded (+15.3, steady 14-17) and against frequent openers (+4.5). Called shoves 19%, more from frequent shovers (+6.1). No response to folding big blinds or to folders postflop | Possibly Bryan Chung's team: he wrote that his "local agents" beat 268 others and that he is going to the Finals; the team is not named. Nothing on strategy |
| **BHTG** (3rd, 680.77) | Re-raised 26% with a weak fold response (+5.1). Opened the button and small blind 67%, more against folding big blinds (+6.6). Bet 71% when checked to, slightly more into folders (+5.3) | Nothing found |
| **Preesh** (4th, 656.03) | No strong response on any test (re-raise +1.2, steal +2.8, shove calls +3.6). Re-raised 23%; opened the button and small blind 69%; called shoves 23% | 19.82 points a table in the last round, from a rival's screen. Nothing else |
| **0_o GTO Slop** (5th, 641.48) | Re-raise response +17.3 over six rounds, falling from +21.7 in the first to +10.2 in the last; re-raised 24%. Opened the button and small blind 78% (+4.1 against folders). Bet 61% when checked to, more into folders (+12.2); folded 68% to bets, less to frequent bettors (-5.3). Folded to the friend's 3-bets 67% (61% to others') | Artem Saraiev (MIT): CFR did not work in time; "tons of stats, a few good heuristics, and fast testing". Two coding agents checking each other, 12 versions, a local arena, study of the leaders' hand histories. Reached 5th only in the last round, by 0.59 |
| **Magnus RLsen** (6th, 640.89; possible wildcard) | Re-raise response grew from +4.5 to +27 by the last two rounds; re-raised 24%; opened the button and small blind 80%. Folded to the friend's 3-bets 80% (75% to others') | Daniel Potapo (Harvard). 19.38 in the last round. Wildcard status not found |
| **Pittsburgh's winner** | No data | Steven Peng's team, by his own post seen as a search snippet: first in four rounds and second in two, "by a huge margin". Team name, school and method: nothing found. No Pittsburgh standings or recap exist publicly |

Reading (C): four of Boston's five re-raise seats that fold, and the top two do it as strongly as Team 123 or more.
Add 2 Curry and a possible Team 123, and **a seat that folds to its first re-raise will be re-raised again by a third
or more of the known field.** Preesh is the exception: a bot that showed no response to seats and still finished 4th.
0_o GTO Slop is the team most likely to arrive looking like whoever led the last round it studied.

Also public and relevant to every card: the per-round scores of the Bay Area leaders and the line that 2 Curry folded
to 81% of re-raises are in a public Pittsburgh team's notes, which took them from our own write-up. Any finalist can
read them, 2 Curry included.

## Appendix A: method and limits

- **Data.** The 14 Bay Area files in `data/README.md` (6 scored rounds, about 20,150 tables each; practices 1-4 and
  6-9), one pass each. Every team is seen only at tables where we also sat, about 1,100 a round. Filler seats are
  excluded as actors but count as opponents. Official scores are from `data/results-bay-area/`.
- **Definitions** are `stat_definitions.md`'s, re-implemented in a throwaway script and checked against `field.md`
  Appendix A: the top 20's means match to the point in every round; the whole-field means differ by up to 3 points
  on open and limp rates because this note averages only teams that raise (the default in `stat_definitions.md`),
  where Appendix A averaged all teams seen (the same reason moves flat-calls by 2).
- **Extra rates** used here and not in `stat_definitions.md`: a limper facing a raise (folds, re-raises); the big
  blind re-raising a single open; fold to a 3-bet by its size and by the opener's depth; first-in opens by position
  and by players left; calls of a first-in shove with no callers by players left; and "level 1" versions (hands
  1-20) of the main rates.
- **Seat-history cross-tabs (Appendix C)** bucket a decision by what the other seat had done earlier at the same
  table, counting everything public (not only against this team). They are raw cross-tabs, not regressions: time in
  the table and stack depth are only partly controlled (A restricts to both stacks at 25bb or more and no callers).
  Three checks: the archive's controlled regressions flag the same teams on A, B and D; our own bot is flat on the
  rules it did not have (A, E) and positive on the ones it had (B, H); and each test's row for all other teams gives
  the background. On C, G and E that background is not zero, so only teams well past its 10th-90th percentile range
  count. E (shove calls) is the weakest: late-table play is mixed in.
- **"Beyond its score"** (Appendix D). Our points at a team's tables minus our points at our other tables, per round,
  regressed on the team's official score over all 756 team-rounds: difference = 1.82 - 0.146 x score. A 20-point team
  costs an average opponent of ours 1.1 points. The residual is what is specific to us and that team; its spread
  across all teams is 0.89 a round against sampling noise of 0.65.
- **Bot changes** (Appendix E): for each pair of files, 29 rates compared; "same" = mean squared z under 3.5 and no
  rate moved 4 points at |z| of 4 or more. A practice file holds 35-72 of a team's tables, so only large changes
  show there.
- **Not done:** no controlled regressions, no showdown ranges, no replay of any counter. Nothing here says a counter
  gains points: every "use" line is grade C.

## Appendix B: style cards by scored round

Percent. A cell with fewer than 300 chances shows its count; fold to a 4-bet and bettor folds to a flop raise always
show it. "none" means no class by the thresholds in `field.md` Appendix A.

### B.0 Reference: the field and the top 20 (team-equal means, raising teams, without us)

| Statistic | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Open first in | 33 / 40 | 35 / 39 | 36 / 40 | 36 / 40 | 37 / 41 | 37 / 39 |
| Open-limp | 5 / 4 | 4 / 4 | 2 / 2 | 2 / 2 | 2 / 2 | 3 / 3 |
| 3-bet | 9 / 10 | 8 / 13 | 9 / 13 | 11 / 16 | 11 / 19 | 14 / 24 |
| Flat-call outside the big blind | 10 / 8 | 11 / 7 | 10 / 9 | 9 / 8 | 9 / 8 | 9 / 8 |
| Big blind folds to an open | 67 / 59 | 66 / 59 | 65 / 55 | 64 / 51 | 61 / 50 | 58 / 40 |
| Fold to a 3-bet | 59 / 64 | 65 / 67 | 68 / 71 | 69 / 71 | 70 / 71 | 67 / 68 |
| 4-bet | 12 / 8 | 9 / 8 | 7 / 6 | 7 / 6 | 7 / 6 | 8 / 7 |
| Fold to a 4-bet | 21 / 22 | 26 / 28 | 31 / 29 | 35 / 36 | 36 / 39 | 39 / 50 |
| Open-shove at 10bb or less | 35 / 49 | 40 / 54 | 42 / 54 | 43 / 54 | 43 / 52 | 44 / 51 |
| Open-shove at 10-15bb | 14 / 25 | 19 / 31 | 21 / 25 | 23 / 32 | 22 / 28 | 24 / 29 |
| Call a shove of 10bb or less | 22 / 25 | 21 / 23 | 21 / 24 | 22 / 28 | 22 / 27 | 24 / 28 |
| C-bet | 62 / 74 | 66 / 72 | 69 / 74 | 70 / 76 | 75 / 77 | 74 / 77 |
| Fold to a flop bet | 47 / 51 | 49 / 53 | 53 / 57 | 53 / 58 | 52 / 55 | 54 / 58 |
| Fold to a turn bet | 38 / 46 | 40 / 48 | 46 / 54 | 48 / 54 | 47 / 52 | 47 / 51 |
| Fold to a river bet | 43 / 53 | 47 / 54 | 52 / 60 | 53 / 57 | 50 / 55 | 51 / 53 |
| Raise a flop bet | 11 / 10 | 10 / 9 | 9 / 8 | 8 / 8 | 9 / 10 | 9 / 9 |
| Bettor folds to a flop raise | 29 / 47 | 35 / 46 | 42 / 51 | 45 / 55 | 48 / 56 | 49 / 62 |

Each cell: all raising teams / the other 19 of the final top 20.

### B.1 2 Curry (final rank 1)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 20.40 | 20.24 | 21.15 | 20.47 | 20.41 | 20.08 |
| Class by `field.md`'s thresholds | wide | wide | wide | wide | wide | wide |
| Open first in | 54 | 48 | 44 | 44 | 44 | 43 |
| Open-limp | 0 | 0 | 0 | 0 | 0 | 0 |
| VPIP / PFR | 43 / 41 | 41 / 38 | 38 / 34 | 38 / 35 | 39 / 36 | 38 / 35 |
| 3-bet (of which all-in) | 34 (1) | 36 (1) | 32 (1) | 34 (1) | 37 (1) | 39 (1) |
| Flat-call outside the big blind | 1 | 1 | 2 | 2 | 2 | 2 |
| Big blind folds to an open | 54 | 45 | 36 | 42 | 38 | 32 |
| Fold to a 3-bet | 87 | 86 | 83 | 80 | 82 | 81 |
| 4-bet | 3 | 4 | 4 | 4 | 4 | 5 |
| Fold to a 4-bet | 82 (n=1778) | 86 (n=1913) | 76 (n=1600) | 76 (n=1751) | 77 (n=1991) | 79 (n=1907) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 59 / 23 / 9 | 55 / 21 / 7 | 56 / 22 / 9 | 58 / 25 / 8 | 55 / 21 / 7 | 53 / 21 / 5 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 28 / 18 / 11 / 10 | 29 / 19 / 11 / 12 | 33 / 14 / 12 / 10 | 31 / 12 / 11 / 10 | 31 / 13 / 11 / 10 | 31 / 13 / 11 / 9 |
| C-bet | 94 | 89 | 89 | 91 | 90 | 90 |
| Fold to a flop / turn / river bet | 62 / 45 / 40 | 72 / 48 / 45 | 67 / 45 / 41 | 63 / 45 / 42 | 61 / 41 / 37 | 61 / 46 / 43 |
| Raise a flop bet | 5 | 5 | 4 | 6 | 6 | 6 |
| Bettor folds to a flop raise | 66 (n=662) | 68 (n=542) | 60 (n=560) | 59 (n=456) | 63 (n=548) | 63 (n=524) |
| Modal open, bb (share of opens) | 2.00 (100%) | 2.00 (100%) | 2.00 (100%) | 2.00 (100%) | 2.00 (100%) | 2.00 (100%) |
| Modal 3-bet, x the open (share) | 3.25 (100%) | 3.25 (100%) | 3.25 (100%) | 3.25 (100%) | 3.25 (100%) | 3.25 (100%) |
| Tables with us | 1121 | 1104 | 1136 | 1081 | 1119 | 1096 |

### B.2 Lemonade (final rank 2)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 19.78 | 19.34 | 20.67 | 20.62 | 20.09 | 19.61 |
| Class by `field.md`'s thresholds | shove/limp | shove/limp | shove/limp | shove/limp | shove/limp | shove/limp |
| Open first in | 11 | 10 | 9 | 8 | 8 | 8 |
| Open-limp | 24 | 24 | 21 | 20 | 20 | 21 |
| VPIP / PFR | 28 / 16 | 27 / 16 | 25 / 10 | 25 / 10 | 25 / 10 | 25 / 10 |
| 3-bet (of which all-in) | 22 (20) | 22 (20) | 13 (10) | 13 (10) | 13 (9) | 13 (10) |
| Flat-call outside the big blind | 9 | 9 | 19 | 19 | 19 | 20 |
| Big blind folds to an open | 51 | 52 | 54 | 53 | 53 | 54 |
| Fold to a 3-bet | 22 (n=49) | 15 (n=55) | 33 (n=113) | 32 (n=107) | 33 (n=121) | 30 (n=112) |
| 4-bet | 10 (n=49) | 9 (n=55) | 5 (n=113) | 7 (n=107) | 2 (n=121) | 5 (n=112) |
| Fold to a 4-bet | 51 (n=89) | 42 (n=55) | 0 (n=130) | 2 (n=165) | 1 (n=162) | 2 (n=170) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 36 / 28 / 24 | 33 / 29 / 25 | 30 / 18 / 15 | 26 / 17 / 14 | 27 / 14 / 13 | 28 / 17 / 13 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 28 / 18 / 12 / 11 | 26 / 14 / 11 / 13 | 27 / 16 / 15 / 14 | 25 / 17 / 14 / 15 | 25 / 20 / 16 / 15 | 25 / 18 / 15 / 14 |
| C-bet | 64 | 64 | 87 | 84 | 87 | 83 |
| Fold to a flop / turn / river bet | 68 / 30 / 28 | 71 / 35 / 32 | 74 / 54 / 49 | 73 / 53 / 52 | 71 / 51 / 47 | 73 / 51 / 50 |
| Raise a flop bet | 7 | 6 | 1 | 0 | 1 | 1 |
| Bettor folds to a flop raise | 92 (n=140) | 89 (n=148) | 77 (n=775) | 82 (n=738) | 79 (n=815) | 78 (n=807) |
| Modal open, bb (share of opens) | 2.00 (95%) | 2.00 (90%) | 2.00 (73%) | 2.00 (77%) | 2.00 (79%) | 2.00 (76%) |
| Modal 3-bet, x the open (share) | 2.00 (45%) | 2.00 (45%) | 3.25 (39%) | 3.25 (38%) | 3.25 (37%) | 3.25 (37%) |
| Tables with us | 1073 | 1064 | 1073 | 1082 | 1087 | 1121 |

### B.3 AZ (final rank 3)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 21.22 | 19.44 | 17.93 | 19.06 | 18.04 | 17.27 |
| Class by `field.md`'s thresholds | none | none | none | none | none | none |
| Open first in | 40 | 38 | 41 | 41 | 41 | 41 |
| Open-limp | 0 | 0 | 0 | 0 | 0 | 0 |
| VPIP / PFR | 30 / 26 | 29 / 25 | 30 / 26 | 31 / 28 | 31 / 28 | 32 / 28 |
| 3-bet (of which all-in) | 14 (11) | 14 (12) | 14 (11) | 20 (17) | 20 (17) | 20 (17) |
| Flat-call outside the big blind | 4 | 3 | 3 | 3 | 4 | 4 |
| Big blind folds to an open | 57 | 57 | 58 | 50 | 48 | 49 |
| Fold to a 3-bet | 60 | 64 | 68 | 79 | 78 | 77 |
| 4-bet | 7 | 7 | 7 | 6 | 6 | 6 |
| Fold to a 4-bet | 7 (n=169) | 7 (n=153) | 6 (n=139) | 8 (n=119) | 5 (n=131) | 7 (n=161) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 73 / 31 / 8 | 74 / 31 / 8 | 84 / 29 / 5 | 62 / 47 / 9 | 57 / 43 / 8 | 61 / 46 / 10 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 41 / 28 / 24 / 21 | 39 / 28 / 24 / 22 | 40 / 24 / 20 / 18 | 31 / 17 / 8 / 11 | 30 / 17 / 9 / 11 | 30 / 18 / 8 / 11 |
| C-bet | 79 | 78 | 78 | 76 | 74 | 78 |
| Fold to a flop / turn / river bet | 61 / 37 / 42 | 61 / 40 / 45 | 69 / 46 / 53 | 66 / 42 / 47 | 62 / 40 / 45 | 62 / 39 / 39 |
| Raise a flop bet | 4 | 3 | 2 | 3 | 3 | 3 |
| Bettor folds to a flop raise | 57 (n=402) | 57 (n=319) | 69 (n=257) | 61 (n=239) | 68 (n=270) | 60 (n=293) |
| Modal open, bb (share of opens) | 2.50 (100%) | 2.50 (100%) | 2.50 (94%) | 2.25 (58%) | 2.25 (59%) | 2.25 (59%) |
| Modal 3-bet, x the open (share) | 3.00 (100%) | 3.00 (100%) | 3.00 (100%) | 3.00 (100%) | 3.00 (100%) | 3.00 (100%) |
| Tables with us | 1161 | 1103 | 1148 | 1100 | 1136 | 1136 |

### B.4 sandylikesfrogs (final rank 4)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 20.65 | 19.72 | 18.33 | 18.30 | 18.49 | 16.87 |
| Class by `field.md`'s thresholds | shove/limp | shove/limp | shove/limp | shove/limp | none | none |
| Open first in | 58 | 36 | 34 | 33 | 36 | 52 |
| Open-limp | 11 | 6 | 4 | 3 | 4 | 6 |
| VPIP / PFR | 50 / 36 | 31 / 23 | 27 / 22 | 27 / 21 | 29 / 23 | 41 / 31 |
| 3-bet (of which all-in) | 15 (7) | 13 (7) | 12 (5) | 12 (5) | 12 (5) | 14 (5) |
| Flat-call outside the big blind | 17 | 10 | 7 | 8 | 9 | 14 |
| Big blind folds to an open | 36 | 57 | 64 | 63 | 60 | 49 |
| Fold to a 3-bet | 46 | 38 | 54 | 55 | 57 | 72 |
| 4-bet | 10 | 14 | 12 | 13 | 12 | 8 |
| Fold to a 4-bet | 16 (n=383) | 12 (n=261) | 9 (n=287) | 12 (n=349) | 15 (n=337) | 22 (n=450) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 33 / 26 / 22 | 55 / 21 / 24 | 56 / 18 / 20 | 57 / 17 / 18 | 58 / 18 / 18 | 56 / 14 / 17 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 53 / 26 / 27 / 33 | 26 / 19 / 22 / 30 | 30 / 21 / 21 / 23 | 28 / 21 / 20 / 20 | 30 / 23 / 22 / 21 | 32 / 24 / 21 / 17 |
| C-bet | 83 | 82 | 74 | 65 | 59 | 55 |
| Fold to a flop / turn / river bet | 59 / 50 / 59 | 56 / 44 / 54 | 56 / 56 / 59 | 65 / 56 / 67 | 62 / 59 / 59 | 67 / 65 / 64 |
| Raise a flop bet | 16 | 17 | 22 | 17 | 19 | 16 |
| Bettor folds to a flop raise | 67 (n=1340) | 59 (n=706) | 63 (n=465) | 71 (n=372) | 66 (n=451) | 66 (n=565) |
| Modal open, bb (share of opens) | 2.00 (53%) | 2.00 (57%) | 2.00 (50%) | 2.00 (52%) | 2.00 (51%) | 2.00 (47%) |
| Modal 3-bet, x the open (share) | 1.50 (25%) | 1.50 (19%) | 1.50 (29%) | 1.50 (31%) | 1.50 (31%) | 1.50 (28%) |
| Tables with us | 1125 | 1079 | 1113 | 1075 | 1118 | 1060 |

### B.5 Team 72 (final rank 5)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 22.19 | 20.23 | 17.89 | 17.86 | 17.83 | 17.39 |
| Class by `field.md`'s thresholds | none | none | none | none | wide | wide |
| Open first in | 48 | 46 | 45 | 45 | 45 | 44 |
| Open-limp | 0 | 0 | 0 | 0 | 0 | 0 |
| VPIP / PFR | 34 / 27 | 32 / 25 | 34 / 25 | 34 / 29 | 37 / 32 | 36 / 32 |
| 3-bet (of which all-in) | 3 (1) | 3 (1) | 5 (1) | 17 (1) | 27 (4) | 26 (3) |
| Flat-call outside the big blind | 13 | 13 | 17 | 7 | 6 | 7 |
| Big blind folds to an open | 64 | 65 | 63 | 63 | 60 | 60 |
| Fold to a 3-bet | 55 | 55 | 55 | 59 | 56 | 53 |
| 4-bet | 5 | 5 | 5 | 4 | 5 | 14 |
| Fold to a 4-bet | 20 (n=109) | 22 (n=88) | 33 (n=217) | 67 (n=859) | 73 (n=1219) | 80 (n=1299) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 39 / 3 / 2 | 40 / 2 / 2 | 40 / 1 / 2 | 37 / 1 / 2 | 39 / 1 / 2 | 41 / 32 / 1 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 31 / 21 / 23 / 33 | 30 / 20 / 23 / 35 | 32 / 22 / 23 / 30 | 31 / 19 / 19 / 25 | 31 / 21 / 21 / 24 | 33 / 21 / 20 / 20 |
| C-bet | 69 | 62 | 65 | 63 | 63 | 63 |
| Fold to a flop / turn / river bet | 64 / 52 / 58 | 66 / 56 / 58 | 69 / 65 / 64 | 68 / 58 / 60 | 65 / 59 / 59 | 61 / 59 / 59 |
| Raise a flop bet | 7 | 7 | 6 | 6 | 7 | 7 |
| Bettor folds to a flop raise | 57 (n=756) | 47 (n=574) | 58 (n=684) | 53 (n=435) | 62 (n=448) | 59 (n=444) |
| Modal open, bb (share of opens) | 2.50 (42%) | 2.50 (44%) | 2.50 (44%) | 2.50 (47%) | 2.50 (47%) | 2.50 (51%) |
| Modal 3-bet, x the open (share) | 2.75 (68%) | 2.75 (69%) | 2.75 (48%) | 2.50 (85%) | 2.50 (89%) | 2.50 (90%) |
| Tables with us | 1112 | 1109 | 1152 | 1070 | 1104 | 1141 |

### B.6 avalon (final rank 6)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 18.10 | 16.73 | 19.05 | 18.26 | 17.95 | 17.53 |
| Class by `field.md`'s thresholds | none | none | none | none | none | none |
| Open first in | 34 | 33 | 33 | 33 | 34 | 33 |
| Open-limp | 0 | 0 | 0 | 0 | 0 | 0 |
| VPIP / PFR | 30 / 23 | 29 / 22 | 30 / 23 | 29 / 23 | 31 / 23 | 31 / 23 |
| 3-bet (of which all-in) | 16 (13) | 16 (12) | 17 (14) | 18 (14) | 18 (14) | 17 (14) |
| Flat-call outside the big blind | 9 | 9 | 9 | 10 | 11 | 11 |
| Big blind folds to an open | 32 | 32 | 28 | 47 | 25 | 26 |
| Fold to a 3-bet | 85 | 86 | 86 | 86 | 87 | 87 |
| 4-bet | 5 | 5 | 4 | 4 | 4 | 4 |
| Fold to a 4-bet | 64 (n=4120) | 58 (n=3272) | 58 (n=3465) | 57 (n=3427) | 55 (n=3276) | 57 (n=3373) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 78 / 26 / 12 | 78 / 25 / 11 | 78 / 25 / 11 | 80 / 27 / 10 | 80 / 29 / 12 | 78 / 28 / 11 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 34 / 19 / 16 / 11 | 34 / 19 / 15 / 10 | 33 / 18 / 15 / 8 | 32 / 15 / 11 / 7 | 31 / 16 / 11 / 7 | 32 / 16 / 13 / 8 |
| C-bet | 94 | 93 | 87 | 87 | 86 | 87 |
| Fold to a flop / turn / river bet | 32 / 48 / 70 | 33 / 49 / 73 | 70 / 65 / 75 | 65 / 61 / 72 | 68 / 64 / 74 | 69 / 65 / 76 |
| Raise a flop bet | 15 | 14 | 12 | 14 | 13 | 13 |
| Bettor folds to a flop raise | 32 (n=16985) | 33 (n=14631) | 65 (n=11056) | 61 (n=8331) | 66 (n=12678) | 66 (n=12622) |
| Modal open, bb (share of opens) | 2.25 (50%) | 2.25 (52%) | 2.25 (52%) | 2.25 (52%) | 2.25 (52%) | 2.25 (52%) |
| Modal 3-bet, x the open (share) | 3.50 (72%) | 3.50 (72%) | 3.50 (73%) | 3.50 (74%) | 3.50 (73%) | 3.50 (72%) |

### B.7 Team 123 (final rank 7)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 9.86 | 12.82 | 17.77 | 19.82 | 19.69 | 18.13 |
| Class by `field.md`'s thresholds | tight | shove/limp | hyper-aggressive | hyper-aggressive | hyper-aggressive | hyper-aggressive |
| Open first in | 16 | 36 | 36 | 40 | 40 | 39 |
| Open-limp | 2 | 0 | 2 | 1 | 1 | 1 |
| VPIP / PFR | 14 / 10 | 24 / 21 | 43 / 36 | 44 / 36 | 45 / 35 | 43 / 35 |
| 3-bet (of which all-in) | 4 (1) | 6 (2) | 46 (6) | 42 (7) | 41 (7) | 41 (6) |
| Flat-call outside the big blind | 8 | 9 | 15 | 18 | 19 | 19 |
| Big blind folds to an open | 88 | 84 | 3 | 3 | 5 | 5 |
| Fold to a 3-bet | 49 | 77 | 49 | 55 | 55 | 52 |
| 4-bet | 14 | 12 | 14 | 4 | 4 | 5 |
| Fold to a 4-bet | 9 (n=157) | 0 (n=185) | 66 (n=1300) | 79 (n=1301) | 85 (n=1374) | 86 (n=1224) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 12 / 3 / 0 | 58 / 50 / 9 | 38 / 12 / 2 | 32 / 13 / 2 | 36 / 10 / 3 | 34 / 11 / 2 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 5 / 7 / 11 / 14 | 12 / 15 / 17 / 25 | 47 / 25 / 28 / 24 | 46 / 25 / 24 / 21 | 45 / 25 / 24 / 23 | 45 / 25 / 22 / 20 |
| C-bet | 77 | 77 | 80 | 87 | 87 | 81 |
| Fold to a flop / turn / river bet | 17 / 14 / 18 | 21 / 22 / 30 | 35 / 42 / 54 | 41 / 46 / 51 | 40 / 46 / 51 | 39 / 45 / 48 |
| Raise a flop bet | 19 | 16 | 9 | 10 | 11 | 11 |
| Bettor folds to a flop raise | 0 (n=248) | 6 (n=283) | 40 (n=534) | 56 (n=733) | 56 (n=685) | 53 (n=533) |
| Modal open, bb (share of opens) | 3.00 (100%) | 2.50 (100%) | 2.00 (59%) | 2.00 (58%) | 2.00 (60%) | 2.00 (58%) |
| Modal 3-bet, x the open (share) | 3.00 (33%) | 3.00 (40%) | 3.75 (72%) | 3.75 (72%) | 3.75 (72%) | 3.75 (71%) |
| Tables with us | 1084 | 1082 | 1095 | 1144 | 1138 | 1075 |

### B.8 Team 82 (final rank 8)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 18.63 | 17.11 | 16.18 | 17.90 | 17.69 | 18.47 |
| Class by `field.md`'s thresholds | none | shove/limp, tight | shove/limp | shove/limp | shove/limp | shove/limp |
| Open first in | 34 | 33 | 40 | 40 | 40 | 42 |
| Open-limp | 0 | 0 | 0 | 0 | 0 | 0 |
| VPIP / PFR | 23 / 19 | 20 / 18 | 23 / 21 | 24 / 23 | 24 / 22 | 31 / 26 |
| 3-bet (of which all-in) | 3 (1) | 3 (1) | 3 (1) | 8 (6) | 8 (5) | 17 (8) |
| Flat-call outside the big blind | 4 | 1 | 1 | 1 | 1 | 3 |
| Big blind folds to an open | 75 | 89 | 89 | 75 | 75 | 25 |
| Fold to a 3-bet | 78 | 83 | 87 | 86 | 87 | 83 |
| 4-bet | 3 | 5 | 3 | 4 | 4 | 4 |
| Fold to a 4-bet | 1 (n=132) | 4 (n=136) | 7 (n=138) | 11 (n=129) | 4 (n=147) | 65 (n=395) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 34 / 3 / 3 | 48 / 25 / 6 | 62 / 29 / 11 | 59 / 26 / 10 | 61 / 28 / 9 | 60 / 26 / 12 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 18 / 9 / 9 / 12 | 17 / 7 / 9 / 10 | 18 / 7 / 8 / 8 | 19 / 9 / 7 / 7 | 19 / 7 / 8 / 8 | 17 / 8 / 9 / 8 |
| C-bet | 67 | 67 | 65 | 64 | 65 | 66 |
| Fold to a flop / turn / river bet | 41 / 36 / 39 | 39 / 35 / 38 | 42 / 38 / 44 | 42 / 39 / 44 | 39 / 46 / 46 | 48 / 60 / 54 |
| Raise a flop bet | 10 | 10 | 10 | 10 | 9 | 8 |
| Bettor folds to a flop raise | 24 (n=431) | 24 (n=224) | 30 (n=260) | 34 (n=216) | 31 (n=198) | 35 (n=387) |
| Modal open, bb (share of opens) | 2.25 (54%) | 2.25 (72%) | 2.25 (59%) | 2.25 (58%) | 2.25 (57%) | 2.25 (54%) |
| Modal 3-bet, x the open (share) | 3.75 (51%) | 3.25 (52%) | 3.25 (54%) | 3.25 (50%) | 3.25 (53%) | 3.50 (56%) |
| Tables with us | 1083 | 1112 | 1086 | 1030 | 1080 | 1127 |

### B.9 pocket rockets (final rank 9)

| | R1 | R2 | R3 | R4 | R5 | R6 |
|---|---|---|---|---|---|---|
| Official points per table | 18.93 | 16.87 | 18.03 | 17.60 | 16.64 | 17.78 |
| Class by `field.md`'s thresholds | shove/limp | shove/limp | none | none | none | wide |
| Open first in | 35 | 39 | 46 | 45 | 45 | 46 |
| Open-limp | 25 | 21 | 0 | 0 | 0 | 0 |
| VPIP / PFR | 40 / 23 | 39 / 24 | 32 / 29 | 32 / 28 | 32 / 28 | 36 / 34 |
| 3-bet (of which all-in) | 10 (1) | 10 (1) | 15 (2) | 14 (2) | 15 (2) | 28 (2) |
| Flat-call outside the big blind | 4 | 4 | 1 | 1 | 2 | 1 |
| Big blind folds to an open | 69 | 68 | 66 | 66 | 64 | 40 |
| Fold to a 3-bet | 65 | 68 | 76 | 76 | 73 | 76 |
| 4-bet | 13 | 12 | 9 | 8 | 10 | 8 |
| Fold to a 4-bet | 33 (n=555) | 42 (n=467) | 54 (n=652) | 55 (n=625) | 55 (n=633) | 73 (n=1115) |
| Open-shove at 10bb or less / 10-15 / 15-20 | 23 / 6 / 0 | 21 / 4 / 0 | 26 / 4 / 0 | 25 / 5 / 0 | 24 / 5 / 0 | 27 / 5 / 0 |
| Call a shove of 10bb or less / 10-15 / 15-20 / over 20 | 30 / 19 / 17 / 18 | 29 / 16 / 18 / 17 | 30 / 17 / 15 / 14 | 31 / 18 / 18 / 13 | 29 / 20 / 17 / 15 | 30 / 18 / 18 / 13 |
| C-bet | 72 | 71 | 70 | 71 | 73 | 69 |
| Fold to a flop / turn / river bet | 55 / 48 / 50 | 56 / 48 / 49 | 55 / 52 / 51 | 55 / 51 / 51 | 51 / 48 / 45 | 53 / 48 / 51 |
| Raise a flop bet | 6 | 6 | 6 | 5 | 6 | 7 |
| Bettor folds to a flop raise | 38 (n=468) | 36 (n=445) | 41 (n=335) | 38 (n=324) | 44 (n=326) | 41 (n=328) |
| Modal open, bb (share of opens) | 2.75 (50%) | 2.50 (51%) | 2.25 (77%) | 2.25 (77%) | 2.25 (79%) | 2.25 (76%) |
| Modal 3-bet, x the open (share) | 2.75 (53%) | 2.75 (55%) | 2.75 (56%) | 2.75 (56%) | 2.75 (57%) | 2.50 (54%) |
| Tables with us | 1141 | 1120 | 1073 | 1105 | 1094 | 1098 |

## Appendix C: seat-history tests

### C.1 Seat-history cross-tabs (percent; chances in brackets)

**A. Re-raise a lone opener (both stacks 25bb or more, no callers): after it did not fold to its one earlier re-raise / after it folded / no history**

| Team | Rounds | First | Second | Third | Second minus first |
|---|---|---|---|---|---|
| 2 Curry | 1-6 | 7.4 (12802) | 42.5 (16683) | 18.0 (48846) | +35.1 (z +78) |
| Lemonade | 1-6 | 3.0 (10493) | 3.8 (22230) | 2.1 (59339) | +0.8 (z +4) |
| AZ | 1-6 | 6.6 (11858) | 7.3 (24096) | 5.3 (62976) | +0.7 (z +3) |
| sandylikesfrogs | 1-6 | 8.5 (11870) | 8.7 (21832) | 7.7 (57884) | +0.2 (z +0) |
| Team 72 | 1-6 | 13.9 (11841) | 13.8 (21774) | 11.8 (56456) | -0.1 (z -0) |
| avalon | 1-6 | 5.3 (227895) | 5.3 (386094) | 5.2 (1048074) | +0.0 (z +1) |
| Team 123 | 3-6 | 23.6 (6133) | 44.4 (11846) | 31.3 (27160) | +20.8 (z +29) |
| Team 82 | 1-6 | 5.2 (11019) | 5.1 (22699) | 4.7 (59493) | -0.1 (z -0) |
| pocket rockets | 1-6 | 13.2 (10913) | 13.6 (21602) | 12.4 (53891) | +0.4 (z +1) |
| All 124 other teams with 200+ chances each side | 1-6 | | | | median +0.1, 10th-90th percentile -0.4 to +1.1 |

**F. Opener folds to a 3-bet: from a seat with no earlier 3-bets / with 3 or more**

| Team | Rounds | First | Second | Second minus first |
|---|---|---|---|---|
| 2 Curry | 1-6 | 83.2 (4932) | 65.0 (4981) | -18.2 (z -21) |
| Lemonade | 1-6 | 89.9 (69) | 69.8 (53) | -20.0 (z -3) |
| AZ | 1-6 | 80.8 (4211) | 57.6 (4310) | -23.2 (z -24) |
| sandylikesfrogs | 1-6 | 53.3 (5724) | 55.7 (3786) | +2.4 (z +2) |
| Team 72 | 1-6 | 51.4 (5062) | 45.3 (4435) | -6.0 (z -6) |
| avalon | 1-6 | 87.7 (68223) | 89.5 (70998) | +1.8 (z +10) |
| Team 123 | 3-6 | 39.0 (2671) | 26.4 (2222) | -12.7 (z -10) |
| Team 82 | 1-6 | 79.8 (3393) | 75.8 (3484) | -4.0 (z -4) |
| pocket rockets | 1-6 | 66.3 (4974) | 72.6 (5070) | +6.4 (z +7) |
| All 121 other teams with 200+ chances each side | 1-6 | | | median +4.2, 10th-90th percentile -5.2 to +13.1 |

**D. Open from the button or small blind: big blind has folded under 34% of opens / over 67%**

| Team | Rounds | First | Second | Second minus first |
|---|---|---|---|---|
| 2 Curry | 1-6 | 75.1 (16491) | 79.5 (25967) | +4.4 (z +11) |
| Lemonade | 1-6 | 10.6 (13870) | 12.5 (27065) | +2.0 (z +6) |
| AZ | 1-6 | 69.4 (14086) | 71.2 (29216) | +1.8 (z +4) |
| sandylikesfrogs | 1-6 | 54.0 (12823) | 60.0 (27606) | +6.0 (z +11) |
| Team 72 | 1-6 | 62.2 (13721) | 81.2 (27702) | +19.0 (z +40) |
| avalon | 1-6 | 43.7 (173184) | 46.5 (594888) | +2.7 (z +20) |
| Team 123 | 3-6 | 53.1 (8021) | 61.9 (14042) | +8.7 (z +13) |
| Team 82 | 1-6 | 64.0 (12841) | 62.7 (25555) | -1.4 (z -3) |
| pocket rockets | 1-6 | 62.1 (12781) | 60.7 (27836) | -1.4 (z -3) |
| All 124 other teams with 200+ chances each side | 1-6 | | | median +0.6, 10th-90th percentile -2.3 to +7.3 |

**H. Big blind folds to an open: opener has opened under 25% / over 45%**

| Team | Rounds | First | Second | Second minus first |
|---|---|---|---|---|
| 2 Curry | 1-6 | 43.8 (8952) | 37.7 (8306) | -6.2 (z -8) |
| Lemonade | 1-6 | 54.9 (8428) | 52.0 (10189) | -3.0 (z -4) |
| AZ | 1-6 | 74.9 (9359) | 29.5 (8555) | -45.4 (z -68) |
| sandylikesfrogs | 1-6 | 60.0 (9273) | 51.9 (9287) | -8.1 (z -11) |
| Team 72 | 1-6 | 68.8 (9408) | 55.2 (8713) | -13.6 (z -19) |
| avalon | 1-6 | 47.2 (148475) | 22.7 (204216) | -24.6 (z -154) |
| Team 123 | 3-6 | 5.5 (4978) | 1.2 (4653) | -4.3 (z -12) |
| Team 82 | 1-6 | 80.6 (8319) | 67.1 (9405) | -13.5 (z -21) |
| pocket rockets | 1-6 | 65.9 (8827) | 59.9 (8679) | -6.0 (z -8) |
| All 124 other teams with 200+ chances each side | 1-6 | | | median -2.3, 10th-90th percentile -16.1 to +0.7 |

**B. Heads-up, bet with no bet to call: opponent has folded under 34% of bets faced / over 67%**

| Team | Rounds | First | Second | Second minus first |
|---|---|---|---|---|
| 2 Curry | 1-6 | 68.5 (18556) | 72.9 (10613) | +4.4 (z +8) |
| Lemonade | 1-6 | 62.7 (17087) | 68.7 (10263) | +6.0 (z +10) |
| AZ | 1-6 | 62.3 (13275) | 75.4 (7008) | +13.1 (z +20) |
| sandylikesfrogs | 1-6 | 77.4 (25695) | 69.1 (8526) | -8.3 (z -15) |
| Team 72 | 1-6 | 52.8 (18975) | 91.5 (11577) | +38.6 (z +87) |
| avalon | 1-6 | 77.4 (410251) | 90.4 (164782) | +12.9 (z +133) |
| Team 123 | 3-6 | 71.7 (9748) | 91.4 (7314) | +19.7 (z +35) |
| Team 82 | 1-6 | 60.9 (13346) | 66.0 (8984) | +5.1 (z +8) |
| pocket rockets | 1-6 | 59.8 (16722) | 62.8 (11195) | +3.0 (z +5) |
| All 125 other teams with 200+ chances each side | 1-6 | | | median -2.4, 10th-90th percentile -9.7 to +16.7 |

**C. Heads-up, fold to a bet: bettor has bet under 40% of its chances / over 70%**

| Team | Rounds | First | Second | Second minus first |
|---|---|---|---|---|
| 2 Curry | 1-6 | 65.9 (5436) | 51.8 (23608) | -14.2 (z -20) |
| Lemonade | 1-6 | 67.6 (4030) | 57.2 (17109) | -10.4 (z -13) |
| AZ | 1-6 | 71.9 (3426) | 45.2 (19218) | -26.7 (z -32) |
| sandylikesfrogs | 1-6 | 68.4 (6303) | 52.9 (22997) | -15.5 (z -23) |
| Team 72 | 1-6 | 69.2 (5912) | 58.7 (26972) | -10.5 (z -16) |
| avalon | 1-6 | 60.4 (79304) | 57.2 (233679) | -3.2 (z -16) |
| Team 123 | 3-6 | 47.0 (3506) | 36.2 (17273) | -10.8 (z -12) |
| Team 82 | 1-6 | 48.8 (3892) | 38.0 (16927) | -10.7 (z -12) |
| pocket rockets | 1-6 | 60.1 (5451) | 44.6 (23021) | -15.5 (z -21) |
| All 125 other teams with 200+ chances each side | 1-6 | | | median -8.8, 10th-90th percentile -15.4 to -4.0 |

**G. Re-raise a lone opener: opener has opened under 25% / over 45%**

| Team | Rounds | First | Second | Second minus first |
|---|---|---|---|---|
| 2 Curry | 1-6 | 30.6 (21389) | 36.5 (22430) | +5.9 (z +13) |
| Lemonade | 1-6 | 5.1 (20749) | 8.1 (25029) | +3.0 (z +13) |
| AZ | 1-6 | 6.2 (23380) | 12.6 (24238) | +6.5 (z +24) |
| sandylikesfrogs | 1-6 | 7.1 (21425) | 13.9 (23095) | +6.8 (z +24) |
| Team 72 | 1-6 | 13.5 (22745) | 15.9 (24123) | +2.4 (z +7) |
| avalon | 1-6 | 4.2 (361712) | 6.7 (507989) | +2.5 (z +52) |
| Team 123 | 3-6 | 41.7 (13037) | 48.2 (14010) | +6.5 (z +11) |
| Team 82 | 1-6 | 4.8 (20716) | 6.4 (24632) | +1.6 (z +7) |
| pocket rockets | 1-6 | 14.1 (21460) | 17.6 (22515) | +3.6 (z +10) |
| All 124 other teams with 200+ chances each side | 1-6 | | | median +0.8, 10th-90th percentile -0.1 to +4.6 |

**E. Call a first-in shove with no callers, by how many times that seat had already shoved at this table (0 / 1 / 2 or more), rounds 1-6**

| Team | Shove of 10bb or less | 10-15bb | Over 15bb |
|---|---|---|---|
| 2 Curry | 31 / 31 / 29 (n 2363-10151) | 16 / 16 / 14 (n 1144-6132) | 6 / 5 / 12 (n 1118-8196) |
| Lemonade | 25 / 25 / 27 (n 2241-9874) | 18 / 19 / 16 (n 1249-6469) | 13 / 11 / 12 (n 1235-7669) |
| AZ | 33 / 33 / 38 (n 2210-7605) | 11 / 15 / 22 (n 1155-4425) | 6 / 7 / 11 (n 1023-5990) |
| sandylikesfrogs | 27 / 29 / 34 (n 2261-7468) | 14 / 15 / 19 (n 1168-5078) | 12 / 12 / 17 (n 1166-6355) |
| Team 72 | 24 / 23 / 29 (n 2276-8064) | 11 / 11 / 17 (n 1112-4635) | 20 / 18 / 26 (n 1152-5383) |
| avalon | 35 / 33 / 33 (n 43017-168557) | 20 / 19 / 18 (n 22308-95292) | 9 / 9 / 8 (n 21593-140047) |
| Team 123 | 33 / 33 / 33 (n 1724-6338) | 19 / 22 / 24 (n 907-3939) | 18 / 18 / 22 (n 914-5170) |
| Team 82 | 14 / 13 / 16 (n 2208-10891) | 6 / 6 / 7 (n 1195-6473) | 4 / 5 / 8 (n 1278-11728) |
| pocket rockets | 24 / 23 / 28 (n 2292-8659) | 10 / 10 / 14 (n 1168-5237) | 8 / 8 / 15 (n 1269-9002) |

**Clock. Open first in, hands 11-20 of a blind level minus hands 1-10 of the same level (points; levels 1 to 4 weighted), by round pair**

| Team | R1-R2 | R3-R4 | R5-R6 | 3-bet, all rounds |
|---|---|---|---|---|
| 2 Curry | +3.7 | +3.8 | +2.3 | +4.2 |
| Lemonade | +0.6 | +0.0 | +0.1 | -0.2 |
| AZ | +1.9 | +2.8 | +2.5 | -0.5 |
| sandylikesfrogs | +12.6 | +7.2 | +11.3 | +3.1 |
| Team 72 | +4.6 | +4.2 | +3.8 | +0.3 |
| avalon | +1.0 | +0.9 | +1.1 | -0.8 |
| Team 123 | +0.5 | +2.8 | +3.1 | +3.4 |
| Team 82 | +2.4 | +1.9 | +2.0 | +0.1 |
| pocket rockets | +3.0 | +2.4 | +2.6 | +1.0 |

Our own row is the check: avalon tracked how often a seat raised, bet and folded to bets, and did not track
re-raises or shoves.

## Appendix D: our results against each team

### D.1 Our points per table where the team sat (in brackets: minus our other tables that round)

| Team | R1 | R2 | R3 | R4 | R5 | R6 | Pooled, minus our other tables | Beyond what its score predicts |
|---|---|---|---|---|---|---|---|---|
| 2 Curry | 16.58 (-1.61) | 14.62 (-2.24) | 17.27 (-1.88) | 16.09 (-2.30) | 15.20 (-2.92) | 15.42 (-2.23) | -2.21 ± 0.25 | -1.05 ± 0.25 |
| Lemonade | 16.20 (-2.01) | 15.91 (-0.87) | 17.64 (-1.48) | 17.02 (-1.31) | 16.36 (-1.69) | 16.33 (-1.27) | -1.44 ± 0.25 | -0.34 ± 0.25 |
| AZ | 16.86 (-1.31) | 14.94 (-1.90) | 17.26 (-1.90) | 17.05 (-1.28) | 16.88 (-1.13) | 16.80 (-0.78) | -1.38 ± 0.25 | -0.46 ± 0.25 |
| sandylikesfrogs | 15.59 (-2.66) | 14.82 (-2.02) | 17.19 (-1.97) | 17.37 (-0.95) | 14.98 (-3.15) | 16.36 (-1.23) | -2.02 ± 0.26 | -1.11 ± 0.26 |
| Team 72 | 16.27 (-1.94) | 15.66 (-1.14) | 17.02 (-2.15) | 16.91 (-1.43) | 16.73 (-1.30) | 16.12 (-1.50) | -1.57 ± 0.26 | -0.64 ± 0.26 |
| Team 123 | 19.13 (+1.09) | 16.35 (-0.41) | 15.92 (-3.31) | 15.59 (-2.83) | 14.37 (-3.80) | 15.37 (-2.28) | -2.09 ± 0.25 | -1.47 ± 0.25 |
| Team 82 | 17.97 (-0.14) | 16.71 (-0.03) | 18.39 (-0.70) | 17.57 (-0.73) | 18.21 (+0.27) | 16.55 (-1.04) | -0.41 ± 0.27 | +0.35 ± 0.27 |
| pocket rockets | 16.44 (-1.76) | 16.25 (-0.51) | 18.98 (-0.07) | 17.33 (-0.99) | 16.39 (-1.66) | 16.68 (-0.89) | -1.00 ± 0.26 | -0.25 ± 0.26 |
| Our average, all tables | 18.10 | 16.73 | 19.05 | 18.26 | 17.95 | 17.53 | | |

Standard error of one round's difference: about 0.6. Team 123 in rounds 3-6 only: -3.06 ± 0.30.

## Appendix E: practice rounds against the scored rounds around them

"Same" = the practice bot matches the next scored bot. "Old" = it matches the previous scored bot and the change came
after the practice. "New" = the next scored bot was already in the practice. (A; a practice holds 35-72 tables per team.)

| Team | Practice before round 3 | Before round 4 | Before round 5 | Before round 6 |
|---|---|---|---|---|
| 2 Curry | Old: round 3's lower 3-bet rate (40% to 32%) unseen | Same | Same, except a one-practice size trial (2.25bb on 35% of opens) | Same |
| Lemonade | New: the rewrite was in the practice | Same | Same | Same |
| AZ | Differs from both (3-bets 21%; 14% scored either side) | Differs from both (opens 36%, short shoves 55%; 41% and 84% before) | Differs from both (3-bets 12%, big blind folds 64%; 20% and 49% scored) | Differs from both (3-bets 15%, big blind folds 60%, c-bets 60%) |
| sandylikesfrogs | Same | Same | Same | Old: round 6's loose bot unseen |
| Team 72 | Same (one small change) | Old: 3-bets 6% to 17% unseen | Old: 3-bets 18% to 27% unseen | Old: 4-bets and 10-15bb shoves unseen |
| Team 123 | Old: the hyper-aggressive rewrite unseen | Same (small changes) | Same | Same |
| Team 82 | Same | New: 3-bets 3% to 9% in the practice | Same | Half-way: big blind folds 75%, 49% in practice, 25% scored |
| pocket rockets | Old: the end of limping unseen | Same | Same | New: the round-6 bot was in the practice |

Of these teams' 11 changes of bot after round 2, 8 were first seen in the scored round and 3 in the practice before.
In the build hour: 2 Curry, AZ, sandylikesfrogs, Team 123, Team 82 and pocket rockets were seated in practice 1
(58-90 tables each); Lemonade and Team 72 first appeared in practice 2. Lemonade's practice-2 and practice-3 bots and
Team 123's practice-3 bot had nothing in common with what they played in round 1.

## Appendix F: splits

**F.1 Opener folds to a 3-bet, by its size relative to the open** (rounds 3-6; percent, chances in brackets)

| Team | under 2.6x | 2.6-3.2x | 3.2-4x | over 4x | all-in |
|---|---|---|---|---|---|
| 2 Curry | 68 (1675) | 74 (5924) | 73 (2888) | 77 (640) | 88 (14753) |
| Lemonade | 58 (66) | 82 (57) | 71 (38) | too few | 8 (280) |
| AZ | 45 (1206) | 77 (5686) | 77 (3015) | 86 (488) | 78 (9848) |
| sandylikesfrogs | 29 (1152) | 63 (6131) | 71 (3055) | 82 (598) | 60 (6716) |
| Team 72 | 38 (1306) | 44 (6939) | 61 (3059) | 77 (575) | 62 (12363) |
| avalon | 78 (21012) | 89 (103682) | 91 (39130) | 93 (8308) | 84 (94112) |
| Team 123 | 12 (1051) | 34 (4591) | 43 (2269) | 59 (432) | 69 (9774) |
| Team 82 | 62 (1379) | 86 (5113) | 85 (2331) | 87 (368) | 89 (11227) |
| pocket rockets | 52 (1579) | 74 (7795) | 78 (3376) | 79 (599) | 78 (14272) |
| Raising teams: median [10th-90th percentile] | 58 [15-87] | 71 [27-87] | 76 [32-88] | 77 [49-90] | 78 [61-91] |

**F.2 Opener folds to a 3-bet, by the opener's own depth** (rounds 3-6; percent, chances in brackets)

| Team | 10-15bb | 15-20bb | over 20bb |
|---|---|---|---|
| 2 Curry | 88 (1806) | 88 (2982) | 80 (21092) |
| Lemonade | 14 (44) | 16 (45) | 44 (301) |
| AZ | 67 (248) | 80 (2415) | 76 (17579) |
| sandylikesfrogs | 47 (968) | 59 (1069) | 63 (15615) |
| Team 72 | 46 (1766) | 56 (2607) | 57 (19869) |
| avalon | 86 (11670) | 85 (22287) | 87 (232179) |
| Team 123 | 69 (890) | 54 (1005) | 52 (15927) |
| Team 82 | 90 (2182) | 91 (3626) | 84 (14255) |
| pocket rockets | 79 (2625) | 80 (3068) | 75 (21079) |
| Raising teams: median [10th-90th percentile] | 79 [53-93] | 79 [59-93] | 74 [40-86] |

**F.3 3-bettor folds to a 4-bet: all-in 4-bet, smaller 4-bet** (rounds 3-6; percent, chances in brackets)

| Team | all-in | not all-in |
|---|---|---|
| 2 Curry | 74 (4917) | 84 (2332) |
| Lemonade | 0 (453) | 5 (174) |
| AZ | 8 (229) | 6 (321) |
| sandylikesfrogs | 21 (731) | 9 (692) |
| Team 72 | 69 (1606) | 74 (1988) |
| avalon | 34 (6076) | 75 (7465) |
| Team 123 | 79 (3120) | 78 (2079) |
| Team 82 | 34 (399) | 37 (410) |
| pocket rockets | 68 (1579) | 54 (1446) |
| Raising teams: median [10th-90th percentile] | 38 [5-74] | 36 [0-77] |

**F.4 Big blind against a single open with no callers** (rounds 3-6; percent, chances in brackets)

| Team | folds, open of 2.05bb or less | folds, 2.05-2.6bb | folds, 2.6-3.1bb | folds, over 3.1bb | re-raises (any size) |
|---|---|---|---|---|---|
| 2 Curry | 31 (3071) | 36 (25237) | 41 (3994) | 46 (2246) | 46 (34548) |
| Lemonade | 43 (3638) | 53 (25440) | 61 (4322) | 62 (2606) | 23 (36006) |
| AZ | 29 (3374) | 51 (24019) | 61 (4073) | 66 (2333) | 36 (33799) |
| sandylikesfrogs | 48 (3614) | 58 (25732) | 67 (4434) | 73 (2811) | 24 (36591) |
| Team 72 | 52 (3335) | 62 (24773) | 65 (4068) | 71 (2310) | 19 (34486) |
| avalon | 10 (77459) | 27 (442724) | 54 (76847) | 76 (48881) | 34 (645911) |
| Team 123 | 0 (2435) | 1 (20484) | 6 (3506) | 36 (1857) | 89 (28282) |
| Team 82 | 52 (3599) | 66 (24762) | 71 (4053) | 80 (2401) | 23 (34815) |
| pocket rockets | 49 (3612) | 58 (24093) | 71 (3830) | 76 (2175) | 29 (33710) |
| Raising teams: median [10th-90th percentile] | 57 [18-83] | 66 [31-85] | 71 [45-87] | 77 [56-89] | 11 [4-25] |

**F.5 3-bet rate from the blinds and from other seats** (rounds 3-6; percent, chances in brackets)

| Team | blinds | other seats |
|---|---|---|
| 2 Curry | 44 (86092) | 25 (65308) |
| Lemonade | 16 (90175) | 10 (79954) |
| AZ | 27 (84076) | 7 (65937) |
| sandylikesfrogs | 19 (89284) | 4 (68539) |
| Team 72 | 18 (85878) | 18 (64466) |
| avalon | 26 (1578635) | 7 (1149970) |
| Team 123 | 65 (70958) | 13 (54360) |
| Team 82 | 14 (86375) | 3 (66122) |
| pocket rockets | 24 (84386) | 10 (63788) |
| Raising teams: median [10th-90th percentile] | 10 [4-21] | 7 [3-13] |

**F.6 Call a first-in shove with no callers, by players left at the table** (rounds 3-6; percent, chances in brackets)

| Team | 2 left | 3 | 4 | 5-6 | 7-8 |
|---|---|---|---|---|---|
| 2 Curry | 40 (3667) | 20 (4758) | 14 (5126) | 13 (7142) | 10 (4164) |
| Lemonade | 26 (4228) | 21 (4900) | 12 (5311) | 18 (6642) | 17 (4136) |
| AZ | 42 (2738) | 25 (3261) | 18 (4060) | 17 (5903) | 15 (3799) |
| sandylikesfrogs | 54 (2754) | 33 (3478) | 17 (4372) | 13 (6284) | 8 (4010) |
| Team 72 | 50 (2433) | 32 (3267) | 20 (4102) | 16 (5914) | 12 (3874) |
| avalon | 19 (90029) | 24 (75674) | 21 (80002) | 21 (119888) | 18 (74328) |
| Team 123 | 75 (1809) | 49 (2530) | 30 (3086) | 27 (4421) | 23 (3196) |
| Team 82 | 18 (4462) | 11 (5023) | 7 (5658) | 8 (7049) | 7 (4092) |
| pocket rockets | 32 (3829) | 22 (4127) | 15 (4561) | 13 (6334) | 10 (3941) |
| Raising teams: median [10th-90th percentile] | 22 [10-37] | 16 [8-26] | 11 [6-19] | 11 [5-18] | 9 [4-16] |

**F.7 Open first in, by position** (rounds 3-6; percent, chances in brackets)

| Team | 5+ players behind | 3-4 behind | button | small blind |
|---|---|---|---|---|
| 2 Curry | 17 (61466) | 30 (69695) | 66 (35622) | 97 (34062) |
| Lemonade | 0 (57545) | 0 (67625) | 2 (35891) | 46 (31581) |
| AZ | 18 (62694) | 32 (66413) | 71 (31919) | 79 (28556) |
| sandylikesfrogs | 26 (59984) | 35 (68709) | 50 (34229) | 58 (30847) |
| Team 72 | 24 (61362) | 35 (66261) | 62 (33380) | 87 (30413) |
| avalon | 21 (1074486) | 27 (1219582) | 44 (609214) | 57 (616271) |
| Team 123 | 19 (51834) | 33 (54926) | 56 (27674) | 71 (26260) |
| Team 82 | 15 (61381) | 28 (69775) | 58 (35009) | 100 (30394) |
| pocket rockets | 25 (59931) | 43 (65728) | 55 (33478) | 80 (31899) |
| Raising teams: median [10th-90th percentile] | 20 [12-31] | 32 [21-42] | 51 [35-66] | 64 [42-85] |

**F.8 Open first in, by players left** (rounds 3-6; percent, chances in brackets)

| Team | 2 left | 3 | 4 | 5-6 | 7-8 |
|---|---|---|---|---|---|
| 2 Curry | 98 (15123) | 78 (17718) | 53 (24655) | 39 (62304) | 27 (81045) |
| Lemonade | 69 (13226) | 18 (18132) | 6 (27582) | 1 (57887) | 1 (75815) |
| AZ | 79 (11769) | 76 (14158) | 56 (22171) | 39 (58486) | 27 (82998) |
| sandylikesfrogs | 57 (13254) | 56 (16071) | 49 (24206) | 34 (61644) | 33 (78594) |
| Team 72 | 85 (13129) | 67 (15694) | 55 (22778) | 43 (58027) | 32 (81788) |
| avalon | 63 (303214) | 49 (299825) | 39 (425557) | 30 (1097703) | 25 (1393254) |
| Team 123 | 78 (11188) | 60 (13010) | 51 (19715) | 37 (46820) | 27 (69961) |
| Team 82 | 100 (12934) | 68 (16796) | 54 (24865) | 37 (61373) | 24 (80591) |
| pocket rockets | 77 (14909) | 62 (15990) | 53 (23532) | 45 (57098) | 34 (79507) |
| Raising teams: median [10th-90th percentile] | 69 [48-89] | 55 [38-70] | 44 [27-55] | 36 [23-45] | 28 [19-36] |

**F.9 Raise first in (any size) by stack depth** (rounds 3-6; percent, chances in brackets)

| Team | 10bb or less | 10-15bb | 15-20bb | over 20bb |
|---|---|---|---|---|
| 2 Curry | 56 (7553) | 52 (11690) | 54 (12782) | 42 (168820) |
| Lemonade | 30 (7148) | 18 (9019) | 15 (12257) | 6 (164218) |
| AZ | 69 (3078) | 49 (6619) | 52 (10746) | 39 (169139) |
| sandylikesfrogs | 56 (5393) | 32 (13637) | 35 (15853) | 39 (158886) |
| Team 72 | 39 (6671) | 56 (8698) | 56 (11510) | 43 (164537) |
| avalon | 79 (79824) | 48 (150833) | 40 (225060) | 31 (3063836) |
| Team 123 | 69 (1976) | 66 (3401) | 43 (5675) | 38 (149642) |
| Team 82 | 67 (10523) | 51 (17741) | 54 (17752) | 36 (150543) |
| pocket rockets | 42 (9991) | 53 (11217) | 51 (13414) | 45 (156414) |
| Raising teams: median [10th-90th percentile] | 46 [29-63] | 41 [26-54] | 43 [30-55] | 36 [24-45] |

**F.10 Fold to a postflop bet, by the amount to call over the pot after the bet** (rounds 3-6; percent, chances in brackets)

| Team | under 0.25 | 0.25-0.4 | 0.4-0.6 | over 0.6 | call is all-in |
|---|---|---|---|---|---|
| 2 Curry | 30 (7580) | 57 (14410) | 70 (11935) | 85 (726) | 60 (2239) |
| Lemonade | 49 (3927) | 65 (16637) | 74 (13025) | 81 (724) | 54 (1407) |
| AZ | 29 (5911) | 58 (11184) | 75 (8748) | 90 (565) | 55 (1202) |
| sandylikesfrogs | 38 (6510) | 63 (16948) | 74 (13203) | 82 (796) | 53 (1713) |
| Team 72 | 38 (6865) | 65 (18390) | 76 (14819) | 85 (820) | 53 (1787) |
| avalon | 41 (47336) | 68 (235391) | 76 (148861) | 78 (12008) | 63 (21913) |
| Team 123 | 22 (9152) | 39 (19190) | 55 (14562) | 76 (848) | 49 (2173) |
| Team 82 | 20 (5262) | 46 (10386) | 60 (7659) | 72 (537) | 43 (1515) |
| pocket rockets | 26 (7885) | 54 (13340) | 68 (11284) | 78 (715) | 46 (2105) |
| Raising teams: median [10th-90th percentile] | 27 [15-46] | 50 [35-65] | 64 [47-77] | 78 [62-90] | 55 [36-72] |

**F.11 Limping: open-limp at level 1; a limper facing a raise folds; a limper facing a raise re-raises** (rounds 3-6; percent, chances in brackets)

| Team | limp, level 1 | folds | re-raises |
|---|---|---|---|
| 2 Curry | 0 (25714) | too few | too few |
| Lemonade | 24 (24644) | 7 (20581) | 44 (20581) |
| AZ | 0 (26614) | 92 (279) | 5 (279) |
| sandylikesfrogs | 8 (24832) | 34 (4488) | 15 (4488) |
| Team 72 | 0 (26023) | 97 (176) | 0 (176) |
| avalon | 0 (436675) | too few | too few |
| Team 123 | 0 (24387) | 6 (769) | 76 (769) |
| Team 82 | 0 (24875) | 83 (94) | 0 (94) |
| pocket rockets | 0 (25357) | 84 (755) | 0 (755) |
| Raising teams: median [10th-90th percentile] | 0 [0-8] | 73 [7-100] | 0 [0-36] |

**F.12 Sizes in round 6** (most common first; share of that team's non-all-in raises of that kind)

| Team | Open, bb (stack over 20bb) | 3-bet, x the open | C-bet, share of pot |
|---|---|---|---|
| 2 Curry | 2.00 100% | 3.25 100% | 0.50 71%, 0.70 29% |
| Lemonade | 2.00 76%, 3.00 23%, 2.25 0% | 3.25 37%, 3.50 31%, 3.00 15% | 0.50 100% |
| AZ | 2.25 59%, 2.50 35%, 2.00 6% | 3.00 100% | 0.80 46%, 0.50 29%, 0.40 15% |
| sandylikesfrogs | 2.00 47%, 3.50 15%, 2.25 13% | 1.50 28%, 3.00 17%, 2.75 15% | 0.50 36%, 0.20 19%, 0.10 15% |
| Team 72 | 2.50 51%, 2.00 31%, 2.25 14% | 2.50 90%, 2.75 8%, 3.00 2% | 0.80 35%, 0.40 30%, 1.10 16% |
| avalon | 2.25 52%, 2.00 19%, 2.50 18% | 3.50 72%, 3.00 24%, 4.00 3% | 1.00 42%, 0.30 24%, 0.80 16% |
| Team 123 | 2.00 58%, 2.25 29%, 2.50 11% | 3.75 71%, 3.00 26%, 4.75 3% | 1.00 48%, 0.70 46%, 0.30 6% |
| Team 82 | 2.25 54%, 2.00 46% | 3.50 56%, 3.75 16%, 3.25 14% | 0.60 28%, 0.70 26%, 0.50 22% |
| pocket rockets | 2.25 76%, 2.50 22%, 10.00 0% | 2.50 54%, 2.75 41%, 3.00 2% | 0.60 59%, 0.70 31%, 0.50 9% |

## Appendix G: sources

- Hand files and results: `/Users/dylan/Documents/GitHub/nolimit-live/data/hands/` and `data/results-bay-area/` (never in git).
- Earlier studies this note builds on: `research/finals_prep/adaptation/REPORT.md` (bot changes, 2 Curry's rule, seat
  regressions), `res_boston.txt`, `res_boston_q3a.txt`, `res_boston_q3b2.txt` (Boston); `research/finals_prep/identity/REPORT.md`;
  `finals_pack/strategy/FINGERPRINTING.md`; `notes/pre/field.md`, `stat_definitions.md`, `variants.md`.
- Public pages, read 14 November by a web-research helper (through a fetch tool that summarises pages, so check a
  figure against the page before relying on it; LinkedIn items are search snippets only):
  - Boston standings and 0_o GTO Slop's method, from a finalist's post and screen photo: https://x.com/artemsaraiev/status/2120625066253946924
  - Sequoia's Boston recap: https://x.com/sequoia/status/2120649414691963202 ; Finals invitation: https://x.com/sequoia/status/2120270083830493656
  - A Boston finalist's reply: https://x.com/bryanchunng/status/2120652050853937527
  - Magnus RLsen's member: https://danielpotapo.com
  - Pittsburgh's winner (snippet only): surfaced via https://www.linkedin.com/in/cuijiaxun/ and https://www.linkedin.com/in/artem-saraiev/
  - A Pittsburgh team's public notes that restate our write-up and the Boston standings: https://github.com/tranthuanhieu1610/no-limit-pittsburgh-playbook (`references/sam/intel-earlier-regionals.md`, `references/ours/7-knowledge.md`)
  - A Pittsburgh team's own estimate that the best team it met scored 18-21 a table: https://github.com/KeyaanMatrix/no-limit-poker-bot
  - Hearsay that "the winner" let its coding agent work it out, regional not stated: https://x.com/flenrik/status/2119997406318321812
- **Nothing found:** members or any strategy for Du-o, Situational Awareness, BHTG, Preesh, Lemonade, AZ, Team 72,
  Team 123, Team 82 and pocket rockets; anything first-hand from 2 Curry (its members are reported second-hand as
  two UC Berkeley students); Steven Peng's team name; Pittsburgh's standings; the list of 20 finalists or of
  wildcards; any team's plan for the Finals. The full search log is in the sessions' shared notes folder
  (`finalists_web_findings.md`), outside the repo.
