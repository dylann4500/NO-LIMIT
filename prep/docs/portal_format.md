# Portal: Tournament format (verbatim, captured Nov 6 morning)

Pasted from the event portal's Format page. `state.config` and the kit override this at runtime. Condensed notes are in `event_portal.md`.

## Team limit

2 members

## The variant

The organizers announce this competition's poker variant when the event starts. Its rules and starter kit appear here then, and uploads open.

## One table

| | |
|---|---|
| Players | 8 |
| Starting stack | 2,000 chips |
| Starting blinds | 10 / 20 |
| Blind increases | Every 20 hands |
| Hand cap | 250 |

A table ends when one bot holds every chip or reaches the hand cap.

## Points by place

Default table payouts

| Place | Points |
|---|---|
| 1st | 50 |
| 2nd | 30 |
| 3rd | 20 |
| 4th–8th | 0 |

Payouts reward finishing place. At the hand cap, surviving bots split the remaining points by ICM on their stacks.

## Default schedule

Default scored round schedule

| Round | After build | Weight |
|---|---|---|
| 1 | Build ends | 1x |
| 2 | +20 min | 2x |
| 3 | +40 min | 3x |
| 4 | +60 min | 4x |
| 5 | +80 min | 5x |
| 6 | +100 min | 6x |

## Scoring

- Build for 60 minutes after the variant is announced. Keep building between scored rounds.
- Scored rounds start 20 minutes apart. Each finishes when all its iterations complete; 20 minutes is the interval between starts, not a time limit.
- Each scored round runs at least 5,000 iterations. Every bot plays one table per iteration.
- A round score is average points per table. Results show the average and finishes in every place.
- Final score is the sum of each round score multiplied by its weight. The last round contributes 6 of the 21 total weight units.
- Practice runs use about 1,000 iterations every 10 minutes during the build phase. Practice never contributes to the final score.
- Results normally arrive in the following 20-minute window, with a compute gap after the last round.

## Bots and snapshots

- Select a ready upload as your active bot. An upload alone does not activate it.
- Each round freezes its own snapshot of every team's active bot at the start. Uploads and changes afterward apply to future rounds.
- A team without an active bot forfeits that round and scores zero.
- A competition-wide freeze pauses uploads and active-bot changes until the organizer unfreezes it.
- The default decision allowance is 1 ms. A timeout, error or illegal action checks when free, otherwise folds.
- Upload agent.py or a zip with agent.py at its root. The current upload default is 50 MB; follow the starter kit for package and unpacked-file limits.

## Fairness

- Seats are randomized each iteration. Short tables use bots not already seated as fillers; their finishes never score for their teams. Fields smaller than eight play short tables.
- When multiple bots bust in one hand, the bot with more chips at the start of the hand places higher.
- Memory starts empty at every table, and opponents use anonymized seat IDs. Bots cannot learn across tables.
- Equal final totals are ordered by countback: the share of tables each team won in every scored round, multiplied by that round's weight and added up, then the same for second places, and so on. Nothing is decided by chance. A disqualified team has no rank and sits out later rounds.

## Regionals and finals

The event format includes regionals at Harvard/MIT, Stanford and CMU. Five teams from each regional, plus five wildcard teams, are invited to finals. Finals use the same tournament format with a different poker variant.
