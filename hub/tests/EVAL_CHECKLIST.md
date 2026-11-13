# Hub eval checklist

Every feature of the hub, what "working" means, and how it is tested. Run results go in `hub/tests/eval/RESULTS.md`.

Methods:
- **U**: unit test with a simulated laptop (no network, no LLM).
- **I**: integration: two real hubs (Samuel + Dylan) linked over Modal, mock portal, agents switched off
  (`AVALON_NO_AGENTS=1`).
- **V**: visual: live browser screenshots from Samuel's and Dylan's screens, plus automatic checks (no page errors,
  no sideways scroll, the element exists and reacts).
- **L**: live simulation: real agents, the emulated tournament, AI teammates playing Samuel and Dylan who ask what
  a person would ask. Judged from logs and transcripts.
- **D**: documents agree with the code.

## 1. Start-up, restarts, isolation
| ID | Check | How |
|---|---|---|
| S1 | `start.sh` pins versions; hub starts and serves `/` and `/api/state` within 20 s | I |
| S2 | Namespaces isolate runs: a hub on `-a` never sees `-b`'s messages or notes | I |
| S3 | Restart resumes: notes, ledger, alerts, Chat history, clock and sent clock marks survive; no clock step is re-sent | I |
| S4 | Agents that were running restart with a "hub restarted" note; stopped agents stay stopped | L |
| S5 | View-only preview starts no agents and no services; Chat answers with the preview notice | I |
| S6 | Worktrees: d-builder and d-challenger each get their own branch and folder; no collision | I |
| S7 | A hung `/api/...` handler never blocks the page: other endpoints answer within 2 s | I |

## 2. Clock and schedule
| ID | Check | How |
|---|---|---|
| C1 | "Start building" sets minute 0 on BOTH laptops; stage becomes Build | I |
| C2 | Telling the Chat "the competition starts now" sets the clock (and "the variant was announced at 14:02") | L |
| C3 | `/api/schedule` HH:MM works; a bad value gives a clear error | I |
| C4 | Stage labels: Build, Practice 1-4, Round k, Round k.5 at the right minutes (scale honoured) | U |
| C5 | Each Overseer gets its own dispatch at b0..b50 and T-20..T-3, once each, with the right person's tasks | U/L |
| C6 | Standing reminders reach the right agents; "[reminders-only]" marks don't wake the Overseer | U |
| C7 | Human steps go to the right person's bell; UPLOAD reminders follow the real state (no "upload v3" when v3 is active) | U/I |
| C8 | Countdown strip shows the next step and time for this person | V |

## 3. Deadline guard (cut-offs) and pacing
| ID | Check | How |
|---|---|---|
| G1 | Each of the six cut-offs fires only when its condition is really unmet, once | U |
| G2 | Fallbacks: default note at T-7, live bot restored at T-4, card fallback to Data, change goes to the challenger | U/L |
| G3 | Heads-ups go to the Overseer only and never say "hurry"; a late ETA triggers one early heads-up | U |
| G4 | No agent rushes after a heads-up: no untested release, no skipped upload test (transcript review) | L |
| G5 | Missed cut-offs show in the Deadlines service and the bell | I/V |

## 4. Agent runtime robustness
| ID | Check | How |
|---|---|---|
| R1 | Stall watchdog: 12 min of no output → interrupt, then reconnect; the task resumes, not dropped | U |
| R2 | Errors retry with backoff; the retry prompt says to check what already happened | U/L |
| R3 | Usage limit: Opus to Sonnet switch, then API key if present; alert says so | U |
| R4 | Compaction triggers above threshold, never T-15..T-2 or within 8 min of data landing | U |
| R5 | Urgent input interrupts a long turn (>45 s) and the interrupted work resumes | U/L |
| R6 | Subagents always run in the foreground (hook) | U |
| R7 | Permission requests appear in the bell; allow / always / deny work; denial is survivable | I/L |

## 5. Link between laptops (bus)
| ID | Check | How |
|---|---|---|
| B1 | Message Samuel → Dylan agent delivered once, in order, within 10 s | I |
| B2 | Shared state (notes, live bot, bots, schedule) converges on both laptops | I |
| B3 | Link outage: messages queue and deliver after; the "Not linked" bar shows and clears | I |
| B4 | Unknown agent names are rejected with a clear answer | I |
| B5 | Pair limits stop two agents ping-ponging | U |

## 6. Roster and roles
| ID | Check | How |
|---|---|---|
| A1 | Every agent knows its role, owner and whom to ask (role quiz) | L |
| A2 | Missing information: an agent asks the owner on the other laptop instead of guessing | L |
| A3 | Overseer is not chatty with humans; humans talk to the Chat | L |
| A4 | Codex jobs run (or fail cleanly to Claude helpers); Modal fan-out within caps | L |

## 7. Overseers
| ID | Check | How |
|---|---|---|
| O1 | Situation brief: phase, current step, next step, checkpoints, team load, idle list, queue, live bot | U/I |
| O2 | Overseer dispatches the plan's tasks at each mark and gives idle workers work | L |
| O3 | T-8: s-overseer recommendation reaches d-overseer applying the pre-registered rule | L |
| O4 | d-overseer posts the "Which bot?" note with numbers and a deadline | L |
| O5 | No decision by its deadline → note expires, rule's answer applied and said in the note | U/L |

## 8. Chat (per person)
| ID | Check | How |
|---|---|---|
| H1 | Samuel's and Dylan's Chats are separate; each person can open the other's (read and write) | I/V |
| H2 | Chat answers status questions correctly from Overseer context ("what's going on", "what should I do") | L |
| H3 | Quick-question chips send their text | V |
| H4 | Failures are pinged into the Chat (urgent alerts) | I |
| H5 | Chat panel drags wider/narrower; state remembered | V |
| H6 | Chat fonts stay Inter/Newsreader; board fonts IBM Plex | V |

## 9. Attachments
| ID | Check | How |
|---|---|---|
| F1 | Choosing or pasting a file stages it (chip + thumbnail); nothing sent until Enter | I/V |
| F2 | Remove a staged file (×) before sending | V |
| F3 | Enter sends text + files; the Chat routes the file to the right agent | I/L |
| F4 | A file from Samuel's laptop can be fetched on Dylan's (`fetch_file`) | I |
| F5 | Image thumbnails load from `/api/inbox/<id>` | V |

## 10. Board and notes
| ID | Check | How |
|---|---|---|
| N1 | Notes are grouped by stage, newest stage first; NOW and previous labels correct | V |
| N2 | Every past stage collapses and expands; your click wins over the automatic default | V |
| N3 | Auto notes appear: Build 1..7 at b0, "vN live · stage" at round start, "Analysis for <stage>" on data, "Which bot? vN" | I/L |
| N4 | Build notes close: B1 on portal active, B4 on card ok, all at minute 60 | U/I |
| N5 | New idea: one text box; posts to the right Overseer; Enter clears it | I/V |
| N6 | Open a note: full-screen chat with live updates; ask in it; answers land in the note | I/L |
| N7 | Greenlight / Reject / Suggest on a "Which bot?" note work from both screens and the decision syncs | I/V |
| N8 | Remove (close) a note; it disappears on both laptops and the Overseer is told | I |
| N9 | "What's going on" summary (report) is accurate and readable | L |
| N10 | Simple cards: type, status, title, key number, two-line gist, last update; decide-in countdown only when due | V |
| N11 | Red screen edge pulses while a permission request or a decision due within 3 min waits; stops after | I/V |
| N12 | Narrator posts only to notes the turn referenced | L |

## 11. Live menu and bots
| ID | Check | How |
|---|---|---|
| L1 | Bots listed by name only (v1, v2...); in-progress ones greyed | V |
| L2 | Clicking a ready bot downloads exactly that zip (same bytes as releases/) | I |
| L3 | Make live from the menu sets the live bot on both laptops and tells d-overseer | I |
| L4 | Live chip turns green when the portal runs the live bot; warns when not | I/V |
| L5 | Bot files reach the other laptop (download works on Dylan's even if built on Samuel's side) | I |

## 12. Portal watcher
| ID | Check | How |
|---|---|---|
| P1 | Polls read-only with a non-default User-Agent | I |
| P2 | A finished round: results saved, hands downloaded, analysis note, s-pipeline + s-overseer woken, d-overseer told | I/L |
| P3 | Round card script runs within 90 s; card_ready routed even if fp_train fails | U/I |
| P4 | Hands not downloadable: retried; bell says so after 20 min | I |
| P5 | Upload rejected / no active bot / wrong active bot at T-9 and T-2 → urgent alert on both screens | I |
| P6 | Standings shown in the Portal service | I/V |

## 13. Ledger
| ID | Check | How |
|---|---|---|
| E1 | Record validation: results need n and method; answers need a lens | U |
| E2 | Rule conflicts rejected (wrong players/stack), subgame scope allowed | U |
| E3 | Verify, dispute, invalidate cascade to dependants | U |
| E4 | Persistent leaks (same slug, same sign, two stages) flagged | U |
| E5 | Team digest is size-capped and priority-ordered | U |

## 14. Routing (who gets what)
| ID | Check | How |
|---|---|---|
| M1 | card_ready → s-data (task), s-skeptic (task), s-tester (fyi); fp_ready → s-scout; candidate → s-tester + s-skeptic | U |
| M2 | Overseer woken only by task/question/human/high priority | U |
| M3 | Work queue: claim is atomic across laptops; a free agent is nudged to queued work | I |

## 15. Bell, alerts, approvals
| ID | Check | How |
|---|---|---|
| X1 | Bell shows only urgent items + permission requests + decisions due; count is right | V |
| X2 | Dismiss works; "clear done" / "clear all" work | I/V |
| X3 | Duplicate alerts within 10 min collapse into one | U |
| X4 | Alerts raised on one laptop for both (palert) show on the other | I |

## 16. Screen quality (both people)
| ID | Check | How |
|---|---|---|
| Q1 | No page errors on any view; no sideways scroll at 1440, 1024 and 390 px | V |
| Q2 | The other person's side stays hidden until clicked; Agents drawer hidden by default | V |
| Q3 | Light palette even when the computer is in dark mode; text contrast ≥ 4.5:1 | V |
| Q4 | Animations smooth, none on every refresh; reduced-motion respected | V |
| Q5 | Keyboard: notes open with Enter/Space; Esc closes a note | V |
| Q6 | Demo mode (`?demo=1`) works without a hub run, including Greenlight/Reject | V |
| Q7 | Empty states make sense: before the start, no bots, no notes | V |

## 17. Documents
| ID | Check | How |
|---|---|---|
| D1 | SUNDAY.md and START_HERE.md commands use flags that exist | D |
| D2 | DECISION_RULES cut-off table matches `GUARD` in hub.py | D |
| D3 | The prompt pack's times match DISPATCH and the clock | D |
