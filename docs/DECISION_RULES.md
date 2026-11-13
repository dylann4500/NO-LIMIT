# How we decide (every agent, every turn)

This page is always in every agent's instructions. It overrides anything older or vaguer in the other
documents. The research behind each line is in `EVIDENCE_TABLE.md` and `FIRST_PROMPT.md` Part 6.

## 1. What we are playing for

Only 1st, 2nd and 3rd are paid (50 / 30 / 20). Finishing 4th pays the same as finishing 20th, so our
goal is the best chance of a top-3 finish, not the smallest chance of a bad round. Standing still is not
safe either: at the regional, top-20 bots that never changed lost about 0.65 points per table per round,
the same as the ones that did change (measured, 18 bots). And our most cautious calls there (a stats band
on releases, a freeze on the fold rules) cost us more than any risky one. When a choice is close, prefer
the option that learns more or gains more.

## 2. The few hard rules (and why)

These protect against losing a whole round. Nothing else on this page is a hard rule.

1. **Every bot we upload is legal and fast**: zero failed decisions in the checks, the kit's check passes,
   and it passes the upload test with no time bank. *(A bot that times out or acts illegally can zero a
   round.)*
2. **Only upload a zip that has been through that test**, put the live bot back as active at T-9, and have
   a tested bot active by T-3 every round. *(A missed upload or an untested zip can zero a round. A missed
   deadline is a failure to report and fix, not a safe outcome.)*
3. **The rules card is right**: players per table, stacks, blinds, hands per match, round weights and
   payouts come from the kit and the Format page. *(At a rehearsal we ran every test at the wrong table
   size.)*
4. **No pre-written bot code; hand histories never go into git.** *(Event rules.)*

## 3. Decisions, written in advance

The rule's answer **is** the default. If nobody answers in time, the rule's answer plays, not "no change".

**Which bot plays a scored round** (worked out by s-overseer at T-8, decided by d-overseer and the humans):
- Measure the challenger against the live bot on the **real field**: its practice-round score minus the
  live bot's most recent comparable score, in standard errors (practice SE is about 0.65 points per table).
- Play the challenger if it passed rule 2.1 and:
  - **we are outside the top 3, or behind 3rd**: it is ahead by **1.0 SE or more** (0.5 SE in the last two
    rounds);
  - **we are in the top 3**: it is ahead by **1.5 SE or more**, or by 1.0 SE if our lead over 4th is smaller
    than one round's typical swing (about 3 points per table times the round's weight share).
- Otherwise the live bot plays, with this window's changes (below).
- Write the note with the rule, both bots' numbers and the rule's answer. The rule's answer plays at T-5
  if no human has answered; a human can always overrule it.

**Changes to the live bot each window:** up to **three independent changes**, each in a different situation,
each behind its own on/off setting, each with a branch-fired count, and the combined build passing rule
2.1. Bundle them; attribution comes from the settings and counts, not from shipping less. Each change needs
real-data support of **1.0 SE or more** (z ≥ 1) when we're outside the top 3, and **1.5 SE or more** when we're
in the top 3; below that, it goes to the challenger or the next practice round to be measured first.

**Deadlines:** if the chosen bot can't be tested and uploaded by T-3, the live bot (active again since T-9)
plays: confirm it's active, report the miss and its cause, and fix the cause for the next window. Don't wait
past T-3 for a release.

**Cut-offs (the hub enforces these; deadlines cut scope, never care).** At the regional, countdown reminders
made bots rush and ship untested. Here a late step simply loses its slot and the safe default plays, so there
is nothing to gain by hurrying, and you are never asked to. If you won't make a cut-off, deliver a smaller
version or let the fallback happen; never skip a test to make one. Give an honest `eta_minutes` in set_status:
a late estimate only lets your Overseer re-scope early.

| Cut-off | If it hasn't happened | Who is told |
|---|---|---|
| T-12: a new challenger released | Practice plays an already-tested bot (else the live bot); the challenger keeps building for next window | Overseer, Dylan (the challenger isn't interrupted) |
| T-10: last round's data landed | No change from new data; live bot plus already-validated changes | Overseer, both humans |
| 3 min after data: round card written | s-data computes the decision numbers by hand; the card script is fixed after T-3 | s-pipeline stopped, Overseer |
| T-8: one-change proposal recorded | No new-data change in the live bot; the idea goes to the challenger or next practice | s-data stopped, Overseer |
| T-7: "Which bot?" note posted | The hub posts it with the live bot as default | Overseer, both humans |
| T-4: the chosen bot released and tested | The live bot (active since T-9) plays; nothing is uploaded | d-platform stopped, Overseer, both humans (urgent) |

Before a cut-off only the Overseer gets a heads-up (at the times above, or earlier if an ETA is late), so it can
cut scope or add a helper. A missed cut-off is reported with its cause at the next T-20 sync.

**The challenger:** two to four changes, a new style, or a fresh rewrite. Its job is to find what the field
pays. Default design: the best response to the field's **measured mix** of styles (Part 4 profiles), not to
whoever is leading.

**Practice rounds are experiments.** Any bot that passes rule 2.1 may play one. Pick the most informative
candidate; a strength verdict from local tests is not required.

**When to be bolder:**
- Outside the top 6 once rounds worth 15% or more of the total weight have been played: put a fresh rewrite
  in the challenger slot.
- Behind 3rd going into the last two rounds: lower the bar (above) and take the bigger swing.
- The last round is often 25-40% of all points: plan it from the round before (durable fixes plus any
  exploit we've been holding back).

**Worked examples** (how these rules play out):
- We're 5th, 1.2 behind 3rd before round 3; the challenger beat the live bot by +0.9 in practice (+1.4 SE),
  passed the upload test; the skeptic isn't done. → Play the challenger, labelled "unverified".
- We're 1st by 4 points before round 5; a +0.4 change is unvalidated at 1.0 SE. → Keep the live bot; play the
  change in the next practice round to measure it.
- We're 8th; three independent fixes (+0.3, +0.35, +0.25, z about 2 each, each behind a setting, combined
  build legal). → Ship all three.
- The challenger fails the no-time-bank test once in three runs. → It doesn't play, whatever its score
  (hard rule 2.1); fix it for the next window.

**When behind schedule:** drop extra verification passes and polish first; keep idea generation, opponent
profiles and the challenger. Never drop the hard rules.

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
When you pick the best of k candidates, discount its edge by about 0.5 x SE x sqrt(2 ln k) before comparing
it with the bar (the best of 10 looks about +0.5 better than it is by chance alone).

**Unverified is not wrong.** A `proposed` ledger item may be cited with the label "unverified". Only an item
**disputed with a reproduced counter-number** blocks a switch. If s-skeptic runs out of time, say so and decide.

## 5. Starting values, not limits

Two regionals with different variants (Bay Area discard-and-expose, Boston flop auction) produced nearly the
same field: fold to 3-bets 67% in both, open-shove at 10bb or less 41% in both, the same drift toward
aggression, and 75-90% of teams changing bots each round. So **behaviour rates and arithmetic are priors;
hand rankings, equity cut-offs, twist values and the style cycle's sizes are not** (s-theory recomputes those
for today's variant).
- **Seat priors:** start each seat at the field rate with weight 4 (as if 4 observations). Until the first
  practice download use the regional values (FIRST_PROMPT Part 1); from that download on, s-pipeline replaces
  them with the Finals field's rates (analysis/field_priors.json). Never use a weight above 10 for a field
  prior; team-profile priors from Finals rounds get weight about 30, capped.
- Use them, measure them, override them when this event's data says otherwise, and say why.
- **Folding to re-raises:** fold to a 3-bet of our open no more than the break-even rate for our open size and
  range (usually 65-75% for 3-bets of 3-3.5x; s-theory recomputes it for today's sizes; we folded 82-89% at the
  regional, the strong bots and both regional fields 63-68%). This is about our opens
  facing 3-bets; it does not apply to folding to 4-bets after our own light 3-bets.
- **Styles A/B/C are three corners to try, not a ranking:** the cycle (wide beats tight, shove beats wide,
  tight beats shove) was simulated on the Bay Area variant only, so its sizes don't carry over. Practice
  rounds decide.
- **Opponent exploitation is core work, not optional:** each team sits at about 7 of our 19 tables at the
  Finals; profiles and counters run every window.
- **Read the round weights and payouts from the Format page**; never assume weights 1-6.
