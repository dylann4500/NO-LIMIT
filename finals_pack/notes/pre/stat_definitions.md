# Field statistics: the definitions behind `field.md` (for `analyst` and `scout`)

> **Case label (14 November, evening).** Written for case R: 8 seats, 2,000 chips, no ante. The team's main case is
> now case F (6 seats, 6,000 chips, antes): `CLAUDE.md` §8 has the two side by side and `notes/pre/format_finals.md`
> what changes. "Re-check on Sunday's format" below lists what breaks.

The definitions behind the regional reference values in `field.md` Appendix A.

## Conventions

- **Unit.** Chances and events are counted per team, over all its seats in the file. Filler seats and our
  own actions are excluded; hands we are in are not.
- **Default: the team-equal mean.** Average the teams' rates, counting only teams that raise (PFR 3%+) and
  have 20+ chances. Every threshold in `field.md` section 3 and every number in the plan means this figure.
  (Appendix A averaged all teams seen, which differs only for limps and short shoves.)
- **Pooled by opportunity** (all opponents' chances added up) is the rate we meet at a random spot. Use it
  only for break-even arithmetic; the last column shows how far it can differ. In section 3, "a pooled rate"
  means practices 1 and 2 added together, not this.
- **Too few.** Under 20 chances: left out of the mean, reported as "too few". From 20 to 99: in the mean, but
  shown alone only with its standard error (5-11 points). Class labels need 300 hands dealt and 30 chances of
  each rate used.
- **Stack depth**: the actor's chips behind plus chips in on this street, over the big blind, when it acts.
  Bands: 10bb or less; over 10 to 15; over 15 to 20.
- Multiway pots and all-in situations are included unless a row says otherwise.
- **VPIP and PFR** (the class labels and the "teams that raise" filter use them): of the hands a seat starts with
  chips, those where it calls or raises before the flop (VPIP) and those where it raises before the flop, all-in
  included (PFR). Posting a blind is neither.

## The statistics

| Statistic | A chance is... | The event | Round 3: team-equal / pooled |
|---|---|---|---|
| Open first in | a preflop decision with no raise and no limper before it (not the big blind's free option) | a raise, all-in included | 34 / 34 |
| Open-limp | same chance | a call | 4 / 2 |
| Open-shove by depth | same chance, actor's stack in the band | an all-in raise | 41, 20, 8 / 33, 19, 8 |
| 3-bet | any decision by a player other than the opener when exactly one raise has gone in and the opener is not all-in; callers in between and the blinds count | a raise, all-in included | 9 / 8 |
| Flat-call outside the big blind | a 3-bet chance where the actor is not the big blind and has over 10bb | a call | 12 / 10 |
| Big blind folds to an open | a 3-bet chance where the actor is the big blind and nobody has called | a fold | 65 / 67 |
| Fold to a 3-bet; 4-bet | the opener's decision facing exactly one re-raise (all-in or not, by anyone) | a fold; a raise | 68 / 73; 7 / 6 |
| Fold to a 4-bet | the 3-bettor's decision after a third raise by anyone | a fold | 31 / 47 |
| Call a shove of 10bb or less | any preflop decision facing a bet to call when the last raise was all-in and that raise totals 10bb or less (the shove's size, not the caller's stack) | anything but a fold | 21 / 19 |
| C-bet | on the flop, the last preflop raiser acting with no bet to call | a bet | 69 / 70 |
| Fold to a flop, turn, river bet | any decision on that street with chips to call (a bet or a raise; a bettor facing a raise counts) | a fold | 52, 46, 52 / 53, 45, 51 |
| Raise a flop bet | same chance, flop only | a raise | 9 / 9 |
| Bettor folds to a flop raise | the flop's first bettor facing a raise | a fold | 42 / 49 |
| Collisions before hand 40 | per table (fillers count): hands numbered 40 or lower that end with two or more seats all-in | mean per table | 1.0 |
| Players left at hand 40 | per table that reaches hand 41: seats with chips at its start | mean | 6.5 |

Chances per team per table are a team's chances over the tables it sat at. A team's modal open is its most
common non-all-in open at over 20bb, in 0.25bb bins; its modal 3-bet is the raise-to over the open's raise-to.

## Re-check on Sunday's format

- Amounts: a call's amount was chips added; a raise's was the raise-to total for the street; an all-in was a
  raise whose added chips met or passed the chips behind. A street's first bet may be logged as a `raise` event
  (it was in a mock kit on 14 November): check before counting bets.
- The big blind was the seat of the last blind posted. An ante, straddle or dead blind breaks that, and every
  row naming the big blind with it. Check heads-up on its own (the button posts the small blind and acts first before
  the flop): on that mock kit the rule mislabelled 25% of heads-up hands.
- A street began at each board event. The twist's events (discards, reveals, bids) were skipped; a twist that
  adds a betting round or moves the flop shifts the postflop rows. Nothing here counts the twist itself: add today's
  (how often each option is taken, with which card) once the format is known.
- Depth bands and the hand-40 marker assume 2,000 chips and the regional blind schedule (about 133 hands per
  table). Chances per table, and so every noise figure, scale with seats and hands per table.
- Filler seats were flagged per table; confirm the flag exists (about one table in five has four).
