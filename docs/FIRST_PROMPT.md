# The first prompt: building a strong bot for an unknown variant

For Dylan and Samuel. Part 1 is the prompt to paste into the coding agent at the announcement. Parts 2 and 3
are the follow-up prompts that find the big improvements once real data arrives. Part 4 is the evidence, so
you can judge how far to trust each line. Nothing here is code; it is knowledge, checks and procedures, which
the rules allow us to bring.

How to use it: fill the two `<...>` slots in Part 1, paste it as the first message, and keep Parts 2 and 3
ready for the first practice-round download. Roles and deadlines are in `docs/FINALS_PLAYBOOK.md`.

---

## Part 1 · The first prompt (paste at the announcement)

```
We're one of 20 teams in the finals of a live pokerbot tournament. The variant was just announced and we
have 60 minutes to build a bot from scratch, then six scored rounds 20 minutes apart, with later rounds
weighted more. The other 19 teams are strong and are also using frontier coding agents, so a merely
correct bot finishes mid-table. Only the top 3 win anything, so 4th and 20th are worth the same to us:
when a choice trades a small chance of a worse result for a real chance of a much better one, take it.
That applies to strategy and to evidence: act on a promising signal without waiting for certainty, while
keeping the things that can zero a round (legality, speed, an active bot) absolutely safe. I'll explain
what a winning bot takes, because the reasons matter more than the rules.

THE FORMAT
8-player no-limit sit-and-go tables, 2,000 chips, blinds from 10/20 rising every 20 hands; a table pays
points by finishing place (default 50/30/20 for 1st-3rd, nothing for 4th-8th) and our score is average
points per table over thousands of tables. The bot is one Python file with act(state, memory) that must
return in 1 ms. The kit in this folder is the authority on everything: read README.md, RULES.md, AGENTS.md
and the SDK source before writing anything, and tell me the variant's new phase(s), action kinds and
state.variant fields, the round weights and anything unusual in state.config. Round weights today:
<weights from the Format page>. Our research notes are in <notes folder, or "none">.

FIRST 10 MINUTES: A BOT THAT CANNOT LOSE US THE ROUND
Before any strategy, get a minimal legal bot into submission/ and tell me to upload it. A team with no
active bot scores zero, and practice rounds on the real field start within minutes, so every minute
without an upload wastes real measurements. It must handle every phase the variant adds (use the kit's
default action for anything unfamiliar), and it needs the safety shell every later version keeps:
- one final function that turns any intended action into a legal one (whole-number raise sizes clamped to
  the offered range; if raising isn't offered, call; if that isn't, check; then fold);
- a catch-all around the whole decision that plays the passive action, and COUNTS every time it fires.
  A swallowed exception doesn't crash us, it silently switches off part of the strategy; that has cost
  other bots whole features. The count must be zero in every local run.
- everything the bot remembers about a table lives in the memory bytes, parsed defensively. Nothing in
  globals or on self; any copy of the bot can answer any table.
- one file, with every table it needs embedded in it. A previous upload of ours was rejected because the
  file opened a data file that wasn't there. Test the exact artifact from an empty folder.

SPEED: DESIGN FOR THE WORST DECISION, NOT THE AVERAGE
The upload test gives no time bank, and the slowest decisions come from garbage-collection pauses, cold
first calls and machine jitter, not from our logic. So: build all tables at import; run one full throwaway
decision of every phase at import; then collect garbage once, freeze it and raise the collector's
thresholds; cap any sampling by both an iteration count and a deadline around 0.3 ms from the start of
the call. Measure the maximum and the 99.9th percentile over 100,000 varied states on an idle machine,
not the mean. Aim for 99.9% under 0.3 ms.

ARCHITECTURE: THREE LAYERS, SO THE VARIANT TOUCHES ONE OF THEM
1. Platform: the safety shell above, memory, and a per-seat record of what each opponent has done.
2. Variant engine: everything that depends on today's rules (cards, hand evaluation, equity, the new
   phase). Hand equity against a range of opponent hands is the one function everything else calls.
3. Strategy: decisions from equity, pot odds, tournament equity and opponent tendencies.

THE TWIST IS WHERE THE EDGE IS; VALUE IT BY ENUMERATION
Whatever decision the variant adds (a discard, a draw, a bid, a pass), list the legal options, score each
with the same equity function, and take the best, inside the time limit. Three traps:
- compute equity against opponents who ALSO use the twist well. Tables built against opponents who
  ignore it overstate our hands; that mistake sank a past winner's bot.
- use every piece of information the twist makes public (exposed cards, bid totals, thrown cards) to
  narrow what opponents can hold, and remove every card we know is dead from all sampling.
- if the twist has a budget or resource (chips of another kind, a limited number of uses), plan it over
  a whole table of roughly 120-140 hands, and check what a failed decision costs under the rules.
Preflop hand rankings change when the rules do. Build today's ranking by simulation at import or at build
time rather than assuming standard hold'em values.

STRATEGY: WHAT WON AND WHAT LOST AT OUR REGIONAL (127 TEAMS, MOSTLY AI-BUILT BOTS)
Treat these as starting values to be replaced by today's data, not as truths about today's field.
- Aggression before the flop won. The winner raised first in about 40% of the time and re-raised (3-bet)
  a third of the opens it faced, with a wide range, and folded most of those to a fourth bet. We re-raised
  only premiums, 5 times a table against its 12, and lost about 2.5 points per table to it in every round.
  AI-built bots tend to re-raise only their best hands and fold to re-raises about 70-85% of the time, so
  wide re-raises against openers who fold are profitable. But every raise needs a plan for being
  re-raised: a bot of ours that 3-bet 58% of hands and then folded 96% of the time to the next raise lost
  10 points per table. Raise or fold before the flop; limping and flat-calling raises lost money for
  almost every bot we measured, except cheap big-blind defence.
- After the flop, big bets and raises from these bots are strong hands far more often than bluffs. Calling
  down raises with one pair was the single most common leak in 17 of 30 bots that reviewed their own
  histories, and ours cost us our placing. Fold one pair to raises and to large late bets unless that
  opponent is shown to bluff. But don't overshoot: after we fixed it we folded 73% to single bets where the
  field folded 52%, and opponents began betting every time we checked. Against a bet, fold near the rate
  that makes their bluffs break even, adjusted by what that opponent has actually shown.
- Bet when checked to while opponents fold more than the bet needs; never bluff into a hand that already
  beats us on what's visible.
- Tournament equity, not chips, decides all-in calls. With 50/30/20: calling an all-in for our whole stack
  needs about 56% equity on the first hand, 65-74% on the bubble with four left, about 57% three-handed,
  and heads-up it is plain chip odds. So shove much wider than we call. Compute these yourself from the
  payouts in state.config and check them against these figures. One specific trap: a library ICM function
  that gives a busted player zero even when their finishing place pays. The kit's function did exactly
  that, and it made our bot fold winning calls for two rounds. Test it with two and three players left.
- At about 12 big blinds or less, play shove-or-fold, and widen sharply short-handed. Opponents' shoves
  were far wider than textbook charts (40-60% of hands at 20 big blinds or less), so call them wider than
  a chart says, within the tournament-equity limits above.
- Heads-up and three-handed play decide whether a table pays 50 or 30. Give them their own ranges and test
  them; every bot that neglected them paid for it.

OPPONENTS: ESTIMATES THAT START FROM A PRIOR AND SHARPEN
Keep running counts for every seat in the table's memory and update them from the events on every call;
this costs microseconds and a few hundred bytes. For each tendency (how often they raise first in, re-raise,
fold to a re-raise, fold to a bet on each street, bet when checked to, raise a bet, call an all-in), the
estimate is (times they did it + weight x prior rate) / (chances + weight), so it starts at the field's rate
and moves as evidence arrives. Three things we got wrong and want right:
- our own bets and raises change the situation for everyone else, so count opponents' responses to OUR
  actions too. Ours silently never did, and the bot never learned who folded to it.
- every rate is opportunities-based and must lie between 0 and 1; ours had one inverted.
- when a hand is shown down, replay that seat's actions with the cards known and record what the bets and
  calls were made with: bluff, draw or value, by street and size. A called river bet is a fair sample of
  what they bet with; earlier streets are skewed toward strong hands.
Build in team recognition from the start, even though the profiles arrive later. With only 19 opponents,
a seat's exact open-raise size and its bet sizes as a fraction of the pot identify the team within a few
dozen hands (in our regional data: the right team 54% of the time after 10 hands, 67% after 20, 73% after
40, from profiles two rounds old). So: record those sizes for every seat from hand 1; keep a running
match score for each seat against each team profile embedded in the bot; and make every prior a blend of
the field's rate and the candidate teams' rates, weighted by how well each matches so far. Use the blend
from the first hand, with no waiting for certainty: a weighted guess is better than ignoring evidence, and
a wrong guess is diluted automatically. Until we have downloads, the profile table is empty and the blend
is just the field's rate. Nothing learned at one table is carried to another; profiles come only from the
hand histories between rounds.

CHECKS, BEFORE I UPLOAD ANYTHING (report the numbers, not "passed")
1. The packed upload imports from an empty folder; the upload-test conditions (heads-up against the kit's
   check-or-fold bot, 20 hands, no time bank) give zero failed decisions on several seeds.
2. 100,000 random legal states, including 2 and 3 players, all-in seats, cut or garbage memory: zero
   illegal actions, zero exceptions, zero catch-all hits, and the latency figures above.
3. Tournament equity: equal stacks get equal shares; shares sum to the prize pool; a busted player gets
   exactly their place's payout; 2- and 3-player cases match hand calculation.
4. Scripted event sequences for every statistic: a seat folds to our bet three times -> 3 of 3; a seat
   that never raises in ten chances -> a rate below the prior.
5. Position, blinds, who acts first and effective stack are right at 8, 3 and 2 players and after a bust.
6. A hand made entirely by the board counts as no hand of ours; equity for a fixed hand falls as the
   opponent's action strengthens from check to bet to raise.
7. Every strategy branch and every variant option reports how often it fired over 1,000 hands; zero or
   absurd counts mean it's broken.
8. A style report from local play, by players remaining: how often we enter pots, raise, re-raise, fold
   to a re-raise, fold to bets by street and size, bet when checked to, and our heads-up open rate.

HOW WE JUDGE STRENGTH (THIS IS WHERE TEAMS FOOL THEMSELVES)
Beating our own earlier versions means nothing: a bot of ours beat them by 4.4 points locally and came
100th of 125 in the real field, because our old versions folded to aggression and the field didn't. Local
play is for legality, speed and sanity, against sparring bots that behave unlike us: one that calls
everything, one that shoves constantly, one that only plays premiums, one that re-raises wide. Run the
same bot against itself first to learn the noise (about 20 / sqrt(tables) points) and ignore differences
smaller than that. The real judge is the practice rounds on the real field, which I'll feed you. Don't
reject a change because it makes us look unlike the average team; the winner looked nothing like it.

HOW TO WORK
- Strategy before infrastructure. The best first-hour build we've seen shipped nine versions in 41
  minutes; the weakest spent the hour benchmarking one parameter. Have a better version ready for upload
  about every 10 minutes, each change behind a named setting so it can be switched off.
- Never wait idle on timers or long jobs; if something runs long, work on the next thing.
- Keep a short notes file next to the bot: what each version changed, what was measured, what's
  suspected. A later session of you will need it.
- Build three bots with deliberately different styles, not three versions of one bot, because a different
  design is the only thing that has ever moved a team many places, and the practice rounds can tell us
  which style this field pays. You write track A; spawn two subagents now for B and C, each in its own
  folder, sharing only the platform layer and the variant engine once those exist:
    A. balanced: equity-driven, opens a normal range, folds to bets near break-even;
    B. pressure: opens and re-raises wide (the regional winner's style), with planned folds to the next
       raise, and bets whenever checked to while the field folds enough;
    C. shove-heavy: small-ball avoided; limp-or-fold never; wide shoves and re-shoves by stack depth and
       tournament equity (the regional runner-up's style).
  Each must pass every check below. I'll rotate which one is active through the practice rounds, so each
  gets a real score against this field, and we'll play the winner, then keep one challenger alive in the
  practice round between scored rounds.
- Tell me plainly when something is untested or a number looks wrong. I'd rather hear "I'm not sure this
  branch fires" now than find it in round 3.
Start by reading the kit, then give me the summary and the minimal bot.
```

---

## Part 2 · The leak finder (paste with the first practice-round download, then every round)

Tested on our regional files: this would have flagged our biggest leak from the first practice round.

```
Here is our hand history for <round>: <path> (format in the kit's README and hand-history folder). Write a
script that streams it and reports, in this order. A full pass should take well under a minute.

1. Failures first: any automatic or failed decisions, by phase.

2. Our own losing actions. Classify every decision by street (number of board deals so far), situation
   (unopened; checked to; facing one bet or raise; facing a re-raise) and action (fold, check, call, small
   raise, large raise, all-in), with the variant's own phase as its own class. Credit each decision with
   the hand's value to us: our tournament-points equity after the hand minus before (both are in the
   file). List every action whose average value is WORSE than our own fold (or check, when checking is
   free) in the same situation, with uses per table, the difference, and a z-score from splitting the
   tables into 20 blocks. Rank by uses per table x difference. An action we chose that still does worse
   than folding is a real leak, and this figure is a floor on what stopping it recovers.

3. What the best teams do that we don't. Take the 10 best other teams in this file by points per table.
   For each situation and action, show their frequency and ours, and how that action performs for THEM
   against their own fold. Rank the biggest "they do it more, and it pays for them" gaps. Trust the
   direction, not the size: they choose their hands, so the average overstates what a marginal hand earns.

4. Across all teams, which action rates correlate most with points per table.

5. How the field treats us compared with others: how often our opens get re-raised, how often our bets
   get called or raised by street, how often our shoves get called.

Then give me the three largest leaks from (2), the two largest gaps from (3) that (4) supports, and one
recommended change with the rates it should move. Count only non-filler seats, and use team names from the
header: entry ids change every round.
```

## Part 3 · Team profiles (paste after the first scored round, refresh every round)

```
From the hand histories so far, build a profile for each of the other 19 teams: the distribution of their
exact open-raise sizes in big blinds by position, their bet sizes as a fraction of the pot by street,
their rates for every tendency the bot tracks, and from showdowns, what their bets and raises on each
street turned out to be (bluff, draw, value) and how weak they call. Embed the profiles in the bot. At the
table, score each seat against every profile from its sizes and preflop actions as hands go by, and from the
first hand use a blend of the teams' rates weighted by how well each matches, mixed with the field's rate,
as the seat's priors; then keep updating with what the seat does at this table. Don't wait for a
confident match: the weighting already discounts weak evidence, and waiting throws away the first third of
every table. Cap how far any single team's profile can pull a decision, because about one confident match
in five is wrong when a team has changed its bot, and treat a seat that fits no profile as a new bot.
For showdown-based rates, correct for what's never shown: a bet that ends the action is a fair sample of
that bet whether it was called or not, but earlier bets are only shown when the bettor kept going, so
count how often each team gives up after betting (that's public) and treat those unseen hands as the weak
end, giving a low and a high estimate of its bluff share; use the middle unless a decision is close.
Nothing learned at one table may be carried to another; profiles come only from the downloads.
```

---

## Part 4 · The evidence behind each line

| Claim in the prompts | Evidence | Strength |
|---|---|---|
| The first hour decides most of the placing | Round-to-round rank correlation 0.76-0.83 (Bay Area), median 0.68 (Boston); 2 Curry scored 20+ from round 1 | Strong, two regionals |
| Wide 3-betting with disciplined folds won | 2 Curry: 12 3-bets/table vs our 5-6, ~+0.4 points each; head-to-head it beat us by 1.6-3.3 points/table; sized 3-bet rate correlates with points (rho 0.38-0.49) | Good; observational, one field |
| One-pair call-downs are the commonest leak | 17 of 30 self-reviewing AI-built bots; our flop fold-to-bet 33% vs the leaders' ~60%; fixing it gained ~2.3 points/table | Strong |
| Over-folding is the next leak | We folded 73/66/78% to heads-up bets vs the field's 52/45/48%; 16 of 30 bots over-folded preflop | Good |
| Local wins don't predict the field | v4: +4.4 locally, 100th of 125; 18 of 30 bots found local simulation neutral or wrong-signed | Strong |
| Library ICM can zero a busted stack | The SDK did; two independently written bots made the same error | Strong |
| ICM call thresholds (56% / 65-74% / 57% / chip odds) | Computed for 50/30/20; the three-handed and heads-up cases checked by hand | Exact for equal stacks |
| Swallowed exceptions disable features | A pre-event bot lost its big-blind shoves to a hidden TypeError; a pilot bot shipped a dead feature flag | Good |
| The own-outcome leak list works | On real files it ranked "calling a flop raise" first from practice 1 (z 6.6); its round-2 size (+2.6) matches v6's realized gain (+2.3) | Tested retrospectively |
| Reference-gap sizes are unreliable | The frequency-gap score undersized the over-calling leak 20x and had the wrong sign when valued by others' outcomes | Tested retrospectively |
| Three styles, rotated through practice rounds | Practice rounds play the active bot on the real field at 1,000-12,500 iterations; the regional's top two used opposite styles (wide 3-bets; limp-or-jam) and both beat every "balanced" bot; a Boston team gained 18 places with a fresh design | Reasoned from data; untested as a procedure |
| Take risks: only top 3 pays | Payoff is all-or-nothing beyond 3rd; our most cautious calls (a style band, "don't copy the winner") cost more than our risky ones | Judgment |
| Teams can be recognised by bet sizes | 19 candidates, profiles two rounds old: 54% correct at 10 hands, 67% at 20, 73% at 40; 81% when gated on a clear margin; ~1 in 5 confident calls wrong after a bot change | Tested on six rounds |
| Fold rates can't be learned live in one table | A seat faces a flop bet ~5-10 times and reaches showdown ~5 times per table | Measured |
| Equity must assume opponents use the twist | A 2017 MIT prize-winner reported this as its main flaw | One source, self-reported |
| Strategy iteration beats infrastructure in the hour | Pilot: nine versions in 41 minutes (15.3 points) vs one parameter tuned all hour (9.7); one agent idle 31 of 60 minutes | Four simulated teams |
| Latency tail is GC, cold calls and jitter | Our 2.6 ms GC outlier; 0.4-7.7 ms outliers measured even with GC disabled | Measured |

**What we could not establish.** Whether aggression wins in a field of 20 strong teams (the regional
field was softer; published evidence is mixed). Whether Sunday's organizers switch on options the platform
has (a late-revealed final weight, a hidden leaderboard, culling, ICM luck correction). How any of the
strategy numbers transfer to a variant we haven't seen: that is why Part 2 exists and why every number in
Part 1 is labelled a starting value.

Sources: our six scored-round files and four practice files; `research/`, `docs/STEERING.md`,
`docs/BUILDLOG.md`; 55 pre-event AI-built bots and their notes (`prep/lab/field_bots/`); the four-team
pilot (`emu/runs/pilot1/`); the Boston regional's files; public write-ups (MIT Pokerbots teams' READMEs,
the GTO Wizard benchmark paper arXiv 2603.23660, Miltersen-Sorensen 2007 and Ganzfried-Sandholm 2008 on
jam/fold).
