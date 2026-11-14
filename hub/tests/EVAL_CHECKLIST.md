# Hub eval checklist (lean hub, 13 Nov night)

Every feature, and every way the day could be slowed, blocked or misled. What "working" means, and how it's tested.
Results: `hub/tests/eval/RESULTS.md`.

Methods:
- **U**: unit test, simulated laptop, no network, no model (`tests/eval/unit_*.py`).
- **I**: integration: two real hubs linked over Modal, fake portal, agents off (`tests/eval/integration.py`).
- **V**: live browser checks and screenshots from both screens (`tests/eval/screens.py`, `lean.py`, `perf.py`).
- **P**: plan battery: decisions under the real instructions, tuning and held-out scenarios, peer pressure
  (`tests/plan_battery/reinforce.py`).
- **L**: live simulation: real agents, the emulated tournament, AI teammates asking what people ask (`tests/eval/live_sim.sh`).
- **S**: static checks (pyflakes, JS syntax, name consistency).
- **D**: documents agree with the code.

## A. Team structure (lean)
| ID | Check | How |
|---|---|---|
| A1 | Four agents per laptop, one lead (the Chat) each; every name used by the hub exists | U |
| A2 | No prompt or doc mentions a removed agent (overseers, pipeline, skeptic, theory) | U/D |
| A3 | The clock hands every worker its own task at each mark (no relay); the lead is told what was handed out | U/I |
| A4 | Each worker knows its job and whom to ask (directory); jobs don't overlap | P/L |
| A5 | A human message to any agent is treated as an instruction: done first, answered | P/L |
| A6 | Leads coordinate: T-8 recommendation reaches Dylan's Chat; the decision gets asked | L |

## B. Board (progress tiles)
| ID | Check | How |
|---|---|---|
| B1 | Build tiles at minute 0 on both laptops (one per stream); later starters say "starts later" | I |
| B2 | Round tiles: "playing vN" when a round runs, "finished" when it ends | I |
| B3 | Data tiles: "in progress" when the download starts, "done" when the hand file is saved; late hands → done later | I |
| B4 | Analysis tiles: "in progress" when data lands, "done" when the one-change is recorded | I/U |
| B5 | Bot tiles follow register_bot (in progress / testing / done / failed) | U |
| B6 | Decision tiles: "waiting for your answer" → "decided: use vN" / "decided: no" / "no answer: the rule decides" | U |
| B7 | report_progress makes/updates one tile per item, no duplicates, states normalised | U |
| B8 | Tiles are plain (label + state + age); clicking opens the owner (the Chat for leads) | I/V |
| B9 | No prompting notes, no "New idea", no Chat button on the board | V |
| B10 | Stages fold/unfold; NOW and previous right; a red bar when a decision waits | V |

## C. Chat and decisions
| ID | Check | How |
|---|---|---|
| C1 | Chat is in the agent list (first); opens as a full page; tabs switch to the teammate's Chat | V |
| C2 | Waiting decisions are pinned at the top of the Chat with the question, evidence, deadline | V |
| C3 | A decision is recorded only from a clear human answer (in the Chat or a thread), with their words kept | U |
| C4 | An agent can't flip a recorded decision; an expiry never undoes one (both laptops) | U |
| C5 | Approving a bot makes it live; the other lead is told; Dylan gets one upload ask | U/I |
| C6 | "the competition starts now" starts the clock in the hub; vague words never move a running clock | I/U |
| C7 | "run the check" runs the pre-flight on both laptops (link, portal read + hand download, Claude, Codex, repo + docs, disk) | I |
| C8 | Unanswered human messages are raised again (Chat 150 s; notes 300 s) and the human told after 6/15 min | I |
| C9 | Attachments staged until Enter; routed; thumbnails open on the other laptop | I/V |
| C10 | Hub messages never appear under a human's name | I/L |

## D. Agents' pages
| ID | Check | How |
|---|---|---|
| D1 | Brief pinned at the top; activity readable; message box with quick buttons | V |
| D2 | Status age shown to leads; stale briefs labelled | U |
| D3 | Remote agents: brief + "runs on X's laptop", messages reach them as tasks | I |

## E. Clock, deadlines, pacing
| ID | Check | How |
|---|---|---|
| E1 | Stage labels right incl. the last round (no "Round k.5" after the last) | U |
| E2 | Each mark once; a clock change carries sent marks (no bursts); steps missed in a restart fire LATE | U/I |
| E3 | Clock drift vs the portal flagged with the corrected minute 0 | I |
| E4 | Deadline cut-offs fire only when really late; fallbacks safe; heads-ups to the lead only, never "hurry" | U |
| E5 | Rate-targeting changes show their rate locally before shipping (prompt + rules) | P/D |

## F. Portal and data path
| ID | Check | How |
|---|---|---|
| F1 | Read-only GETs, non-default UA; 6 s near round ends, 10 s while an upload is pending, 30 s otherwise | U/I |
| F2 | Results that fail are retried (not skipped); empty results retried first | I |
| F3 | Hands verified gzip, atomic; card + fingerprint run in the background; agents told first | I |
| F4 | Rejected upload / no active bot / wrong bot → urgent on both screens, never auto-cleared | I |
| F5 | Data-landed time only once hands exist; survives restart | I |

## G. Robustness
| ID | Check | How |
|---|---|---|
| G1 | Two linked hubs converge on notes/tiles/decisions under races (merge, verify) | U/I |
| G2 | Restart: notes, tiles, clock, live bot, landed times, unsent values survive; leftovers stopped | I/U |
| G3 | Background loops supervised; errors.log empty in a clean run | I/L |
| G4 | Stall watchdog (12 min no output → interrupt → reconnect, task resumes); long-turn check to the lead | U |
| G5 | No undefined names; JS parses | S |

## H. Speed and load
| ID | Check | How |
|---|---|---|
| H1 | 20 parallel /api/state < 3 s | I |
| H2 | Redraw with a full day's data (300 tiles, 200 decisions, long Chat) < 50 ms | V |
| H3 | Data landed → Analyst and lead told < 45 s (agents off); clock mark → worker item same tick | I |
| H4 | No sideways scroll at 1440/1024/390; light palette in OS dark mode; reduced motion | V |

## I. Game plan
| ID | Check | How |
|---|---|---|
| I1 | Decisions right under the real instructions, compacted context, peer pressure (22 scenarios, tune + held-out) | P |
| I2 | Reinforcement method chosen on evidence (base vs reminders vs rules card vs self-check) | P |
| I3 | Shared style defaults + defaults check in every round analysis; rate check | D/L |
| I4 | Docs (START_HERE, SUNDAY, DECISION_RULES, FIRST_PROMPT, FINGERPRINTING) match the lean roster | D |

## J. Exploration and plan challenges (14 Nov)
| ID | Check | How |
|---|---|---|
| J1 | The plan is a default, not a mandate: every agent may challenge a task; PLAN CHALLENGE reaches both Chats and both humans once | U |
| J2 | The Challenger builds a clean-room design D from minute 0 (no A/B/C notes) | U/D |
| J3 | No clock task forces a style onto a practice round; Dylan's Chat picks the most informative test | U |
| J4 | Field trend every download (s-scout) with the plan assumptions checked; winners lens every round (s-data) | D/L |
| J5 | The T-8 bar is field-adjusted (yardstick teams), practice SE ≥ 0.7, exploration budget until 30% of the weight | D |
| J6 | "start the research" hands every worker its pre-event topic on both laptops, notes only | U |

## K. Two laptops for real
| ID | Check | How |
|---|---|---|
| K1 | share_file / fetch_file move a file or folder between laptops; the tool is on the allow-list | U/I |
| K2 | Each round's results and hand sample reach Dylan's laptop; the Challenger is told the path | I |
| K3 | The pre-flight compares both laptops' hub code and clocks | I |
| K4 | A local write always wins over a remote stamp from a clock that runs ahead | U |

## L. The format isn't what we expect
| ID | Check | How |
|---|---|---|
| L1 | Build length, round spacing and round count can be set from the Chat; defaults unchanged | U |
| L2 | A scored round seen late on the portal pins it; later rounds and deadlines follow | U/I |
| L3 | A window whose previous round hasn't started gets no false cut-offs | U |
| L4 | A false start corrected later still fires minute 0; a small correction never re-fires it; synced changes don't re-fire | U |
| L5 | Questions or future times never start the clock; "2:05" in the afternoon is 14:05; "reset the clock" before the event | U |
| L6 | Held standings, changed competition settings, culling, a "final"-kind round, a cancelled round, zero tables | U |
| L7 | The rule's answer is stored with the decision and applied by the hub at the deadline; opposite answers reopen it | U |
| L8 | A rejected upload of the live bot reverts the live bot; the chosen-bot cut needs a released bot | U |
| L9 | Hands link pasted in the Chat (no restart); plain JSON-lines hand files kept; download errors shown | U |
| L10 | Brief 429/overloaded errors are retried, not treated as a usage limit | U/D |

Scenario walk-throughs behind these (14 Nov): `tests/scenarios/`.
