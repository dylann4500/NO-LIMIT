# How we decide (every agent, every turn)

This page is always in every agent's instructions. It overrides anything older or vaguer in the other
documents. The research behind each line is in `EVIDENCE_TABLE.md` and `FIRST_PROMPT.md` Part 6.

## 1. What we are playing for

Only 1st, 2nd and 3rd are paid (50 / 30 / 20). Finishing 4th pays the same as finishing 20th, so our
goal is the best chance of a top-3 finish, not the smallest chance of a bad round.

Freezing doesn't hold a lead. At the Bay Area regional, top-20 teams fell back about 0.65 points per table per
round **whether or not they changed** (changed minus unchanged: −0.01 ± 0.18). For top teams, **rewrites had the
same average as standing still but three times the spread**: 24% improved, by up to +3.8, against none of the
unchanged ones. Most big gains in the whole field came from rewrite-scale changes. And our most cautious calls
there (a stats band on releases, a freeze on the fold rules) cost us more than any risky one. When a choice is
close, prefer the option that learns more or gains more.

**The plan is a default, not a mandate.** Everything below §2 was written before anyone saw today's variant or
this field. Strong teams will do things nobody predicted, and the field moves every round. When today's data
says a better path exists, take it; the only things that never bend are the hard rules.

## 2. The few hard rules (and why)

These protect against losing a whole round. Nothing else on this page is a hard rule.

1. **Every bot we upload is legal and fast**: zero failed decisions in the checks, the kit's check passes,
   and it passes the upload test with no time bank. *(A bot that times out or acts illegally auto-folds and
   can zero a round.)*
2. **Only upload a zip that has been through that test**, put the live bot back as active after the practice
   round, and have a tested bot active by T-3 every round. *(A missed upload or an untested zip can zero a round.
   A missed deadline is a failure to report and fix, not a safe outcome.)* Each round plays a snapshot of every
   team's **active** bot taken at its start. Making an already-uploaded bot active is a click on the portal, not
   an upload. Assume the upload **cooldown** may be up to 5 minutes (read it from the Format page at minute 0), so
   plan at most two real uploads per window (§3, "Uploads").
3. **The rules card is right**: players per table, stacks, blinds, hands per match, round weights, payouts
   and the cooldown come from the kit and the Format page. *(At a rehearsal we ran every test at the wrong
   table size.)*
4. **No pre-written bot code; hand histories never go into git.** *(Event rules.)*

## 3. Decisions, written in advance

The rule's answer **is** the default. If nobody answers in time, the rule's answer plays, not "no change".

**Which bot plays a scored round** (worked out by Samuel's Chat at T-8, asked by Dylan's Chat, decided by the humans):
- **Measure the challenger against the field, not against a different field.** The challenger's practice round
  and the live bot's last scored round had different opponents (in practice rounds most teams test new bots). So
  compare each with **yardstick teams**, the teams s-scout's drift check says did not change bot between the two
  rounds: edge = (challenger's practice score − the yardsticks' practice scores) − (live bot's last scored score
  − the yardsticks' scored scores). With fewer than 4 yardsticks, use scores minus the field median, and say so.
  Pool the challenger's practice rounds when its core is unchanged. Practice SE is **at least 0.7** points per
  table (more with 20 teams); z = edge / SE of the edge.
- Play the challenger if it passed rule 2.1 and:
  - **we are outside the top 3, or the standings are hidden and we weren't clearly in it**: z ≥ **0.5**
    (≥ 0 in the last two rounds: a coin flip with upside beats certain 4th);
  - **we are in the top 3**: z ≥ **1.0**, or z ≥ 1.5 if our lead over 4th is more than one round's typical
    swing (about 3 points per table times the round's weight share).
- Otherwise the live bot plays, with this window's changes (below).
- Write the question with the rule, both bots' numbers and the rule's answer. The rule's answer plays at T-5 if
  no human has answered; a human can always overrule it.

**Changes to the live bot each window:** every independent change that clears the bar, each in a different
situation, each behind its own on/off setting, each with a branch-fired count, the combined build passing rule
2.1. Usually one to three; more is fine when each is independent and tested. A change that targets a rate (e.g.
"fold to 3-bets at 74%") must show that rate in a local run (within about 5 points of the target) before it ships.
*(In a rehearsal a change aimed at 74.6% played at 92.8% because only "it fired" was checked.)* Each change needs
real-data support of z ≥ 1 when we're outside the top 3 and z ≥ 1.5 in the top 3; below that, it goes to the
challenger or the next practice round to be measured first.

**Exploration (every window, at any standing).** One 1,000-table practice round can only tell apart bots about
1.4 points apart, so small tweaks are invisible there and the practice slot is wasted on them. Use it for
**different designs**. Explore-then-commit is the classic way to lose a moving game; keep several whole
alternatives alive and re-choose as results come in.
- **Build hour:** at least one practice round plays a design derived fresh from today's rules (d-challenger's
  clean-room design D), not from the regional style notes. Which bot plays each practice is the most
  informative test, chosen by Dylan's Chat.
- **Until 30% of the total weight has been played:** at least every other practice round plays a *divergent*
  challenger (a different style class or a rewrite, not the live bot plus tweaks), even when we're in the top 3,
  unless our lead over 4th is more than one round's typical swing.
- **After that:** d-challenger keeps one divergent line alive as insurance against a field shift; raise the
  budget again whenever a PLAN CHALLENGE stands or we are behind 3rd.
- Divergent candidates are judged by the real field (practice rounds). The cloned field may veto one only if it
  predicts a loss of 2 points or more and the reason is understood.

**Plan challenges.** Any agent whose evidence says a plan assumption (§5) or the base style is wrong for today
sends a PLAN CHALLENGE to both Chats and d-challenger. The Chats put it to the humans at once, in plain words;
by default d-challenger builds the alternative and the next practice round judges it. A challenge never waits
for the next scheduled step, and never skips a hard rule or a test.

**Uploads.** A window has at most two real uploads, about 8 minutes apart: the challenger at T-12 (it plays the
practice round at T-10) and, only if the chosen bot is a new zip, the chosen bot at about T-4 to T-3. Putting the
live bot back at T-9, and choosing the challenger, are clicks on bots already uploaded: tell Dylan which version to
click in the portal's uploads list. Never let a cooldown leave the chosen bot unuploaded at T-3. When in doubt, the
live bot stays active.

**Deadlines:** if the chosen bot can't be tested and uploaded by T-3, the live bot (active again after the practice
round) plays: confirm it's active, report the miss and its cause, and fix the cause for the next window. Don't wait
past T-3 for a release.

**Cut-offs (the hub enforces these; deadlines cut scope, never care).** At the regional, countdown reminders
made bots rush and ship untested. Here a late step simply loses its slot and the safe default plays, so there
is nothing to gain by hurrying, and you are never asked to. If you won't make a cut-off, deliver a smaller
version or let the fallback happen; never skip a test to make one. Give an honest `eta_minutes` in set_status:
a late estimate only lets your Chat (the lead) re-scope early.

| Cut-off | If it hasn't happened | Who is told |
|---|---|---|
| T-12: a new challenger released | Practice plays the most informative already-tested bot (else the live bot); the challenger keeps building for next window | the lead, Dylan (the challenger isn't interrupted) |
| T-10: last round's data landed | No change from new data; live bot plus already-validated changes | the lead, both humans |
| 3 min after data: round card written | s-data computes the decision numbers by hand; the card script is fixed after T-3 | s-data stopped, the lead |
| T-8: one-change proposal recorded | No new-data change in the live bot; the idea goes to the challenger or next practice | s-data stopped, the lead |
| T-7: "Which bot?" decision asked | The hub asks it, with the rule's answer as the default | the lead, both humans |
| T-4: the chosen bot released and tested | The live bot (active since the practice round) plays; nothing is uploaded | d-platform stopped, the lead, both humans (urgent) |

Before a cut-off only the lead (your laptop's Chat) gets a heads-up (at the times above, or earlier if an ETA is late), so it can
cut scope or add a helper. A missed cut-off is reported with its cause at the next T-20 sync.

**The challenger** is the team's exploration. Its job is to find what this field pays: a clean-room design, a new
style, the best response to the field's **measured** mix of styles, what a PLAN CHALLENGE or the winners lens points
to, or a fresh rewrite. A rewrite is a normal option at any standing, not an emergency. Data for a round lands at
about T-13 and the challenger releases at T-12, so each challenger is built from the data already in hand and
targets the next window.

**Practice rounds are experiments.** Any bot that passes rule 2.1 may play one. Pick the most informative
candidate; a strength verdict from local tests is not required.

**When to be bolder:**
- Behind 3rd, or outside the top 3 once 15% of the total weight has been played: the challenger slot carries a
  divergent design, and the bar drops as above.
- A PLAN CHALLENGE stands, or two or more plan assumptions (§5) are off by 2 SE or more: the plan's premise is
  false today; say so to both humans and put the alternative in the next practice round.
- The last round is often 25-40% of all points: plan it from the round before (durable fixes plus any exploit
  we've been holding back).

**Worked examples** (how these rules play out):
- We're 5th, 1.2 behind 3rd before round 3; the challenger beat the live bot by +0.9 field-adjusted (z 1.3) in
  practice, passed the upload test; the Tester's verification isn't done. → Play the challenger, labelled "unverified".
- We're 1st by 4 points before round 5; a +0.4 change is at z 1.0. → Keep the live bot; play the change in the next
  practice round to measure it.
- We're 8th; three independent fixes (+0.3, +0.35, +0.25, z about 2 each, each behind a setting, combined
  build legal). → Ship all three.
- After round 2, s-scout's field trend shows the top 5 teams now limp-or-shove at 15bb or less and fold to 3-bets
  58%; our wide-3-bet base loses to them. → PLAN CHALLENGE; d-challenger builds the counter-style; it plays the
  next practice round whatever our standing.
- The challenger fails the no-time-bank test once in three runs. → It doesn't play, whatever its score
  (hard rule 2.1); fix it for the next window.

**When behind schedule:** drop extra verification passes and polish first; keep idea generation, the field trend,
opponent profiles and the challenger. Never drop the hard rules.

## 4. Evidence: what each grade lets you do

- **A: measured on real event data** (practice or scored rounds, our hand histories). Act on it.
- **B: replay tests, the cloned field, paired local tests that agree with A-signals.** Act on it in the
  challenger and the practice slot; ship to the live bot when it is consistent with what the real field
  shows.
- **C: simulation, the regional only, or judgment.** A starting value or a hypothesis: try it where it is
  cheap to be wrong (practice rounds, the challenger, a setting that defaults off), and let the real field
  judge. Never block a change because a C-grade rule says otherwise.

Local wins do not predict the field (a bot of ours was +4.4 locally and 100th of 125). Use local play for
legality, speed and sanity; use the practice rounds for strength.

**Weigh signals by how solid they are.** A leak seen in two rounds' data in the same direction (the hub flags
these as persistent) is strong evidence: ship its fix. One round's number is weaker; pool rounds when you can.
When you pick the best of k candidates, discount its edge by about 0.5 x SE x sqrt(2 ln k) (the best of 10 looks
about +0.5 better than it is by chance alone). Never re-tune toward one practice round's difference under 2 SE.

**Unverified is not wrong.** A `proposed` ledger item may be cited with the label "unverified". Only an item
**disputed with a reproduced counter-number** blocks a switch. If s-tester runs out of time verifying, say so and decide.

## 5. Starting values, not limits

**Behaviour rates and arithmetic are priors; hand rankings, equity cut-offs, twist values and style sizes are not**
(s-data recomputes those for today's variant). Two regionals' *whole* fields looked alike (fold to 3-bets 67% in
both, open-shove at 10bb or less 41% in both), but their **top 20s did not**: Boston's top teams went from folding
75% to 3-bets to 57.5% by round 5 and 4-betting 23%, then partly reversed; Bay Area's barely moved. The Finals
field is the top teams of all three regionals, who studied the same lessons, so expect them to start near or past
that counter-wave.
- **Seat priors:** start each seat at the field rate with weight 4 (as if 4 observations). Until the first
  practice download use the regional values (FIRST_PROMPT Part 1); from that download on, s-data replaces
  them with the Finals field's rates (analysis/field_priors.json). Never use a weight above 10 for a field
  prior; team-profile priors from Finals rounds get weight about 30, capped.
- Use them, measure them, override them when this event's data says otherwise, and say why.
- **Folding to re-raises:** recompute the break-even fold rate for our open size and range (usually 65-75% for
  3-bets of 3-3.5x). Folding far above it invites the seat-learners (2 Curry re-raised a seat 18% fresh, 43% after
  one fold, 62% after two). It is a default, not a cap: the regional winner itself folded 81-87%. It is about our
  opens facing 3-bets, not folding to 4-bets after our own light 3-bets.
- **Styles A/B/C are three corners to try, not a menu:** the cycle (wide beats tight, shove beats wide, tight beats
  shove) held only in pure simulated fields on the Bay Area variant; at realistic mixes no lead exceeded 1.4 points,
  and the clones could not rank strong teams. Today's rules may make another axis matter more (the twist,
  postflop, short stacks). Practice rounds decide.
- **Opponent exploitation is core work, not optional:** each team sits at about 7 of our 19 tables at the
  Finals; profiles and counters run every window.
- **Read the round weights, payouts and cooldown from the Format page**; never assume weights 1-6.

**Plan assumptions** (s-scout checks each against every download; one off by 2 SE or more is a PLAN CHALLENGE):
1. The field folds to 3-bets of our opens at about 60-70%.
2. Open-limping and flat-calling opens at 10bb+ lose money in this field.
3. The field open-shoves 35-50% of first-in chances at 10bb or less.
4. After the flop, big bets and raises are mostly strong hands (one pair should fold to raises).
5. Our base style is the best response to the field's measured mix (no style the top 5 share beats it).
6. The twist is worth what s-data's tables say, and the field uses it about as well as we do.
7. Scores are compressed near 12.5 points per table; differences under 1.4 between two practice rounds are noise.
