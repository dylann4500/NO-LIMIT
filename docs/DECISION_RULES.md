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

**Unverified is not wrong.** A `proposed` ledger item may be cited with the label "unverified". Only an item
**disputed with a reproduced counter-number** blocks a switch. If s-skeptic runs out of time, say so and decide.

## 5. Starting values, not limits

These came from one regional, one variant and simulated opponents. Use them, measure them, override them when
this event's data says otherwise, and say why.
- **Folding to re-raises:** fold to a 3-bet of our open no more than the break-even rate for our open size and
  range (usually 65-75%; we folded 82-89% at the regional and strong bots 70-77%). This is about our opens
  facing 3-bets; it does not apply to folding to 4-bets after our own light 3-bets.
- **Styles A/B/C and the cycle** (wide beats tight, shove beats wide, tight beats shove) held in simulation
  when about half the field played one style; with a mixed field they were within about 1 point. The real
  field decides.
- **Opponent exploitation is core work, not optional:** each team sits at about 7 of our 19 tables at the
  Finals; profiles and counters run every window.
- **Read the round weights and payouts from the Format page**; never assume weights 1-6.
