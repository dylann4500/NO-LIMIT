# Before Sunday: what to test and improve in this bundle (for a Claude Code session on Saturday)

> Delete this `prep/` folder before the event (the Sunday sessions shouldn't read it).

You are helping team avalon (Samuel, Dylan) get ready for the No Limit poker-bot Finals on Sunday 15 November. This
repo is the bundle the two Claude Code sessions will run in: read `CLAUDE.md`, `START.md`, `prompts/`,
`.claude/agents/`, `strategy/` (esp. `DECISION_RULES.md`, `PLAN.md`, `LESSONS.md`) and `scripts/README.md` first.
The team's edge on Sunday comes from two things: (1) the agent structure (who does what, how sessions and subagents
work together) and (2) the research baked into `strategy/`. Most teams will also use Claude Code, so both must be
excellent. Below: what is known, what is untested, and how to test or improve each, most important first.

Ground rules: no pre-written bot code may be brought to the event (notes, prompts, analysis plans and these
scripts are fine; anything that plays poker is written on the day). Hand histories never go into git. Keep the
bundle's docs consistent with each other when you change one.

## Already verified (13-14 November)

- Claude Code features the bundle relies on (from the docs, 14 Nov): the `Monitor` tool streams a command's stdout
  lines to the session (30 min max per watch in an interactive session: re-arm on expiry; `--continue` does not
  restore monitors); subagents from a main session run in the background by default and report when done; a
  finished subagent can be continued with `SendMessage` to its id; subagents can spawn subagents up to 3 levels;
  about 20 concurrent subagents per session by default (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`); built-in
  cross-session messaging between local sessions (`ListAgents` / `SendMessage`, Claude Code v2.1.224+; sessions in
  bypass-permissions mode hold incoming messages, so don't use bypass); PreToolUse hooks apply to subagents and in
  every permission mode; deny rules beat allow rules and are checked per subcommand; effort levels
  low/medium/high/xhigh/max (`/effort`, frontmatter `effort`); auto-compaction threshold via `autoCompactWindow`.
- In the previous setup (a custom hub, now retired): four live simulations and one practice run with the same roles
  and decision rules. `strategy/LESSONS.md` lists what broke and the rule that now prevents each.
- The scripts have unit tests: `python3 scripts/test_scripts.py`.

## 1. Run one full rehearsal with this bundle (highest value)

Nothing has run end to end in Claude Code yet. A simulator of the tournament (simulated rival teams, a copy of the
organizers' portal) lives in the other repo (`NoLimit/NO-LIMIT/emu/`, on Samuel's Mac; `emu/README.md`). Plan:
1. Samuel's Mac: start a rehearsal with an unseen mock variant and the finals field, e.g.
   `prep/.venv/bin/python emu/rehearsal.py --run reh5 --field finals --variant flop_auction_holdem --variant-rules emu/variants/flop_auction_holdem.md --round-iterations 3000 --wait`
   then `emu/portal_server.py --run reh5` (portal copy on port 8765; reachable from Dylan's laptop over Tailscale),
   and `emu/rehearsal.py --run reh5 --start HH:MM`.
2. Dylan's laptop: a SEPARATE clone of this repo (`~/avalon-rehearsal`, never the Sunday clone `~/avalon-finals`), four tabs as in `START.md`, with `portal_watch.py --base http://<samuel-tailscale-ip>:8765/tournament/api --key-file <rehearsal key>`
   and the clock started at the rehearsal's minute 0. Tell both sessions it's a rehearsal (portal facts don't carry
   over to Sunday).
3. Watch and write down (in `notes/rehearsal_findings.md`): every place a session was confused, idle, slow, wrong
   or noisy; whether each clock step and portal event woke the right session; time from data landing to the T-9
   recommendation; whether the practice picks and uploads happened on time; how the humans felt (too many questions?
   unclear asks?); context size of each main session over time (`/context`); any subagent that ran wild.
4. Fix the bundle for each finding (prompts, role files, scripts), and note it in `strategy/LESSONS.md`.
Success: every window's decision asked by T-8 with numbers, the chosen bot active by T-3, no forfeits, no silent
failures, and both humans able to follow what's happening by reading their own terminal.

## 2. Confirm the mechanics that the docs don't settle (15 minutes, before the rehearsal)

- **Trust the folder first:** a fresh clone is untrusted, and Claude Code then ignores `.claude/settings.json`'s
  allow list (found in the 14 Nov speedrun: "Ignoring 9 permissions.allow entries ... this workspace has not been
  trusted"). Run `claude` in the repo once and accept the trust question; check `/permissions` shows the lists.

- **Does a Monitor event wake an idle session?** Start a session, run the Monitor on `python3 scripts/feed.py builder`,
  stop typing, and from another terminal run `python3 scripts/say.py builder "test"`. The session must react without
  any human input. Repeat after 30+ minutes (expiry: does it re-arm by itself?). If it doesn't wake reliably, switch
  the clock and portal events to Claude Code's cross-session messaging (a script can send through the session's
  messaging socket, `CLAUDE_CODE_MESSAGING_SOCKET`; see the cross-session messaging docs), or have a third tiny
  session relay them.
- **Cross-session messaging between BUILDER and RESEARCH:** `ListAgents` shows the other; a `SendMessage` wakes it.
- **Hook and permissions:** in a session, ask it to run `pkill -f test`, `sleep 60`, `rm -rf ~/x`: each must be refused
  with the reason; `rm -rf build/` inside the repo must run; no permission prompt for ordinary commands; same from a
  subagent.
- **Background subagents:** a main session spawns 3 at once and keeps answering the human while they run; it gets
  each result when done; a finished one can be continued with SendMessage.
- **Concurrency:** both sessions at full fan-out can exceed 20 concurrent subagents per session; if so, start the
  sessions with `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=40 claude` and note it in `START.md`.

## 3. Build-hour throughput (where most of the outcome is set)

The bot at the end of the build hour matters a lot (rank correlations between rounds 0.84-0.91 for the whole field;
top-20 places move 3-4.5 per round). The structure has one writer of `bot/` (`platform`), styles and the challenger
in their own folders, and theory tables arriving from RESEARCH at minutes 15-45. Risks: `platform` is a bottleneck
(rules card, v1, harness, interface, table integration, every release); the kit's Python environment setup eats
minutes; the styles wait for `bot/INTERFACE.md`; theory tables arrive after the styles that should use them.
Test: a timed speedrun (a fresh copy of the bundle, an unseen mock variant kit built with
`emu/variants/make_kit.py <variant> <out>`, BUILDER and RESEARCH sessions told "minute 0 is now", no portal), with
milestone times logged (rules card, v1 released and upload-tested, harness, INTERFACE.md, each style, design D,
each theory table, the round-card script). Targets: rules card ≤ 5 min, v1 ≤ 10, harness ≤ 15, INTERFACE ≤ 12, styles
A/B/C + D legal by ≤ 35, ranking ≤ 15, push/fold ≤ 30. Then improve whatever is slowest, e.g.: `platform` spawns its
own helpers (engine adapter / evaluator / packaging) from minute 0; publish the interface before v1; set up the
kit's venv once at minute 0 (`uv venv && uv pip install -r requirements.txt`) for everyone; give `stylist` one
helper per style; ship v1 as the kit's own safe example plus the safety shell. (A first speedrun was run on 14 Nov;
see `prep/SPEEDRUN_14NOV.md` if present.)

## 4. Main-session context over four hours

Each main session reads every inbox line and every subagent report for 4+ hours. Watch `/context` in the rehearsal.
`.claude/settings.json` sets `autoCompactWindow` (compaction before the context gets slow); after a compaction the
session re-reads its PLAN file (`notes/PLAN-<session>.md`), `state/*` and the inbox tail. Check that this recovery
works (force one with `/compact` mid-rehearsal and see whether it loses a promise or a deadline). If it degrades, make
the PLAN file template stricter or have each main session restart from its PLAN file between rounds (`--continue`
then "re-read your PLAN file").

## 5. Subagent continuity

Subagents are spawned per task; memory between tasks lives in files (LEDGER, PLAN files, each role's folder) or in
continuing the same agent with SendMessage. Check in the rehearsal: does `platform` keep consistent code across
releases? Does `scout` reuse its fingerprint model between rounds? If a role keeps re-learning context, give it a
`notes/<role>.md` memory file to read first and update last (add that to its role file).

## 6. Two humans, one laptop

Both sessions run on Dylan's laptop. Decide how Samuel types into RESEARCH: side by side at one laptop, or from his
own laptop (`ssh` into Dylan's over Tailscale and run the RESEARCH session inside `tmux` so it survives a dropped
connection). Test whichever you choose in the rehearsal.

## 7. Strategy research still worth doing (if time allows)

The research is in `strategy/` (EVIDENCE_TABLE grades every claim; LESSONS covers process). Open items, by value:
- **The Finals meta, anticipated:** finalists have read both regionals; the Boston top 20 had already swung to
  folding only ~57% to 3-bets and 4-betting ~23% by round 5. A one-page memo: which styles will be crowded on Sunday,
  what punishes them, and which signs in practice 1-2 tell us (the "contrarian memo" is scheduled as morning research
  on Sunday; doing it Saturday saves an hour of the morning).
- **Pittsburgh's variant and results** (unknown so far): search; ask on the event's Discord/socials.
- **Twist valuation drills:** `strategy/TWIST_NOTES.md` has 12 plausible twists; a session could rehearse valuing one
  or two by enumeration (notes only, no code kept) to check the instructions are fast and correct.
- **Cloned-field ordering test** (low priority now): the decision rules no longer depend on the simulator ranking
  candidates under 2 points, so skip unless everything else is done.

## 8. Before you finish

- Run `python3 scripts/test_scripts.py`.
- Re-read `CLAUDE.md`, both prompts and the role files for contradictions with anything you changed.
- Make sure nothing in the repo is bot code that plays poker, and no hand data is committed.
- Delete `prep/` before Sunday (or move it out of the repo).
