# Rebuild kit: a strong bot from scratch in under an hour

Drop this folder into a fresh repo next to the starter kit and give the assistant the prompt below. It holds **knowledge only**: rules and traps, an architecture, a strategy specified in words and numbers, what the field does, the tests, and the timeline. **There's no code in it on purpose.** If the event requires bots built from scratch, carrying our prepared code in, even pasted into markdown, is the same thing as bringing the code. Everything here is what a well-prepared team knows.

## Paste this first (fill in the variant line)

```
We're in a live 60-minute pokerbot build. Tonight's variant: <paste the announcement, or the link to its rules>.
Read every file in rebuild/ in order (01 to 08), then the starter kit's README.md, RULES.md and AGENTS.md. The kit wins wherever they disagree with rebuild/.
Then follow rebuild/06_TIMELINE.md:
- get a minimal legal bot uploaded by minute 15;
- then build the strategy in rebuild/03_STRATEGY.md behind the platform layer in rebuild/02_ARCHITECTURE.md, adapting every variant-specific part (deck, hole cards, board, hand ranking, extra phases) to tonight's rules inside engine.py only;
- test each step with rebuild/05_TESTS.md, and check preflop against rebuild/08_REFERENCE_SPOTS.md (exactly for hold'em; as a sanity check for a close variant).
Work in small steps, run every test, and report measured numbers. Never break the uploaded bot: keep the last good version and only upload after the tests pass. Don't upload anything without telling me first.
```

## Files

| File | What it gives you |
|---|---|
| `01_RULES.md` | Format, scoring, hard limits, the platform API and every trap we found |
| `02_ARCHITECTURE.md` | The three-layer design (platform layer, strategy, variant engine), memory format, warm-up and GC settings |
| `03_STRATEGY.md` | The winning strategy as a spec: preflop, push/fold with ICM, postflop equity with range narrowing, bet-sizing EV, opponent stats, all constants |
| `04_FIELD.md` | What AI-built bots do (measured over 3 simulated rounds and 56 bots), and what beats them |
| `05_TESTS.md` | Must-pass checks before every upload, and how to run them with the kit's tools |
| `06_TIMELINE.md` | Minute-by-minute build plan, the between-round loop, the decision rules |
| `07_PROMPTS.md` | Paste-ready prompts for each step |
| `08_REFERENCE_SPOTS.md` | v2's actual preflop decisions in 336 standard spots. Check the rebuild against them to find bugs fast |

## How much to trust it

This comes from a full day of simulation: 56 AI-generated opponent bots (Claude and Codex, three generations improving between rounds), mock rounds of up to 8,000 tables, and tests on the team build box.
- The strategy in `03_STRATEGY.md` finished top 3 in every field and blind-schedule combination we tried, and 1st of 27 against the most evolved field.
- An earlier rule-based design, tuned against hand-written opponents, finished **last** in every mock round.
