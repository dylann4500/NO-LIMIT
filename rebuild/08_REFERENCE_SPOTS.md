# 08 · Reference decisions (v2, fresh table, default opponent priors)

Use these to check a rebuild: same state in, same action out. They're preflop and deterministic (no Monte Carlo); postflop depends on sampling, so it isn't listed. Blinds 10/20, 8 players, everyone at the same stack, nobody has acted except as stated. 'raise Xbb' is the raise-to total in big blinds.

These are **v2's choices, not proven optimal.** Match them first, then improve with real hand histories. Some cells are random by design:
- A 3-bet to 3.2× the open (e.g. 7.0 bb against 2.2 bb, 8.0 bb against 2.5 bb) is the light 3-bet. It fires 35% of the time for hands ranked 8-22% against openers who fold to raises more than 55% of the time.
- Hands in that band may show call, fold or a 3.2× raise on different runs.

Everything else should match exactly. A mismatch elsewhere usually means one of these:
- wrong hand percentiles;
- wrong players-behind counting (count active seats from us to the big blind);
- the push/fold utility missing the ICM blend.

## Unopened pot (folded to us)

| hand | UTG · 100bb | CO · 100bb | BTN · 100bb | SB · 100bb | UTG · 25bb | CO · 25bb | BTN · 25bb | SB · 25bb | UTG · 12bb | CO · 12bb | BTN · 12bb | SB · 12bb | UTG · 7bb | CO · 7bb | BTN · 7bb | SB · 7bb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AA | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| QQ | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| 77 | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| 22 | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | fold | fold | fold |
| AKs | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| AQo | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| AJo | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| A5s | fold | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | ALL-IN | ALL-IN | ALL-IN |
| KQs | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | raise 2.2bb | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | ALL-IN | fold | ALL-IN | ALL-IN | ALL-IN | ALL-IN | ALL-IN |
| KJo | fold | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | fold | ALL-IN | ALL-IN |
| K9o | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | fold | fold | ALL-IN |
| QJs | fold | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | raise 2.2bb | raise 2.5bb | raise 3.0bb | fold | ALL-IN | fold | fold | fold | fold | fold | ALL-IN |
| T9s | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | fold | fold | fold |
| Q8o | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | fold | fold | fold |
| J7o | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | raise 2.5bb | raise 3.0bb | fold | fold | fold | fold | fold | fold | fold | fold |
| 72o | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold | fold |

UTG = 7 players behind, CO = 4, BTN = 2, SB = 1.

## Facing a raise

Columns: who raised, to how much, and where we sit.

| hand | UTG opens 2.2bb, we're BTN, 100bb | CO opens 2.5bb, we're BB, 100bb | BTN shoves 10bb, we're BB | UTG shoves 15bb, we're BTN | SB shoves 8bb, we're BB |
|---|---|---|---|---|---|
| AA | raise 6.6bb | raise 8.8bb | call | call | call |
| QQ | raise 6.6bb | raise 8.8bb | call | call | call |
| 77 | call | call | call | call | call |
| 22 | fold | call | call | fold | call |
| AKs | raise 6.6bb | raise 8.8bb | call | call | call |
| AQo | raise 6.6bb | raise 8.8bb | call | call | call |
| AJo | call | raise 8.8bb | call | call | call |
| A5s | raise 7.0bb | raise 8.0bb | call | fold | call |
| KQs | call | raise 8.0bb | call | fold | call |
| KJo | fold | call | call | fold | call |
| K9o | fold | call | call | fold | call |
| QJs | fold | call | call | fold | call |
| T9s | fold | call | fold | fold | call |
| Q8o | fold | fold | fold | fold | fold |
| J7o | fold | fold | fold | fold | fold |
| 72o | fold | fold | fold | fold | fold |
