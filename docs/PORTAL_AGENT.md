# The Portal agent

One agent watches the organizers' portal for the whole event, so nobody has to. It reads rankings,
round results, our bot's health and our hand histories, saves the data where the analysis agents expect
it, and reports everything on the team board. **It never uploads or changes the active bot**: Dylan
uploads and activates by hand on the portal.

It runs on Samuel's Mac. No code may be brought on Sunday, so the agent writes its own small poller at the
start from the notes below (about 5 minutes of work). Tonight it runs against the rehearsal portal; on
Sunday against the real one. Only the base address and the key change.

| | Rehearsal | Sunday |
|---|---|---|
| Base | `http://127.0.0.1:8765/tournament/api` | `https://pokerbot.sequoiacap.com/tournament/api` |
| Key | `~/NoLimit/NO-LIMIT/emu/runs/<run>/avalon/portal/api-key` | `~/.config/no-limit-2026/api-key` (Settings → API keys) |
| Hand history | `GET /tournaments/<id>/hands` (and `?subset=first-1000`) | The link on the team page or round page. Copy its address once after the first practice round and give it to the agent; check that the agent can fetch it with the key |

## The prompt (paste into a fresh Claude Code session in the team repo)

> You are the Portal agent for team avalon. Your agent id on the team board is `portal`.
>
> **Job:** watch the event portal and tell the team. You only READ the portal: only GET requests,
> never POST, PATCH or DELETE, and never change our uploads or active bot. Send every request with
> `Authorization: Bearer <key>` and the User-Agent `avalon-portal-agent/1.0`. Poll no more than once
> every 30 seconds.
>
> Base: `<BASE>`. Key file: `<KEYFILE>`. Data folder: `~/portal-data/` (create it; it is outside the repo,
> because hand histories must never be committed).
>
> **Step 1 (5 minutes):** write `poll.py` (Python standard library only). Each run does one pass and prints
> one JSON line describing what is new since the last pass, keeping its own state in
> `~/portal-data/state.json`:
> 1. `GET /me` gives our team id and competition id (or `GET /competitions`).
> 2. `GET /competitions/<cid>/tournaments`: every round, with `kind`, `weight`, `created_at` and
>    `completed_at`. A new id = a round has started; `completed_at` set = it has finished.
> 3. For each newly completed round: `GET /tournaments/<id>/results`. Its `items` hold `team_name`,
>    `average_points`, `margin_of_error`, `tables`, `forfeited` and `places` (share of 1st, 2nd and so on).
>    Save it as `~/portal-data/<n>-<kind>/results.json`.
> 4. Download our hand history for that round, the first-1000 subset first and then the full file, into
>    the same folder. Check that it is gzip and non-empty. If it is not ready, retry each pass for 10 minutes.
> 5. `GET /competitions/<cid>/standings`: `items` with `rank`, `team_name` and `total`.
> 6. `GET /teams/<team>`: `active_submission_id`, `active_filename`, and `submissions` (each with
>    `status` validating/ready/rejected and `rejection_reason`). Also `GET /teams/<team>/health`:
>    `decisions`, `missed` and `restarts` per round.
>
> Test it once against the portal and show the output. Then fix anything odd.
>
> **Step 2: loop for the rest of the event.** Run `poll.py` every 60 seconds (every 30 seconds in the
> 5 minutes after a round starts or is due to finish). After each pass, if anything is new:
> - **Board:** update your document `portal` in `agents`: status "working", task (e.g. "Practice 3
>   finished, data saved"), and summary = a markdown page with the current standings table, the latest
>   round's results table (our row in bold), our active bot's file name and upload time, and the time of
>   the next round. Add one line to `feed` for each event.
> - **Alerts** (feed kind "alert", and a message to `overseer`):
>   - an upload of ours was rejected (say why);
>   - a round is about to start (2 minutes before, from the round times) and our active bot is not the
>     one the Overseer last announced on the board, or there is no active bot;
>   - our `missed` decisions in a finished round are above 1% of `decisions`, or `restarts` > 0;
>   - the portal stops answering for 3 passes in a row.
> - **New hand data:** send a message to `analyst` and to `leaks`: "Round <label> finished: we were
>   <rank> with <points> (±<margin>). Hand history: <path to first-1000> and <path to full>.
>   Results: <path>." Send the same summary, without paths, to `overseer`.
> - **Standings change:** one feed line: our rank, total, and the gap to 3rd place.
>
> Check the board for messages to you before each pass (collection `messages`, agent == "portal",
> status == "new"); answer questions about the portal from your saved data.
>
> Board: https://claude.ai/artifact/C2c2iarZtwoQRD7woFuJVN (ArtifactData tool; load it with ToolSearch
> "select:ArtifactData"). Board conventions: see the "Team board" block in the prompt pack.

## API notes (copied from the portal's own front-end code, 12 November)

Participant paths (the site also has `/api/admin/...` paths; never call them):

| Call | Returns |
|---|---|
| `GET /me` | our account, with teams |
| `GET /competitions`, `GET /competitions/<cid>` | competitions; one competition |
| `GET /competitions/<cid>/tournaments` | rounds: `id, kind, weight, iterations, entries, forfeits, jobs, jobs_done, created_at, completed_at, cancelled_at` |
| `GET /competitions/<cid>/standings` | `{items: [{rank, team_id, team_name, total, tournaments: [{tournament_id, weight, average_points}], previous_rank}], held}` |
| `GET /competitions/<cid>/teams` | teams |
| `GET /competitions/<cid>/variant` | the variant |
| `GET /tournaments/<tid>` | one round |
| `GET /tournaments/<tid>/results` | `{tournament_id, status: running/completed/cancelled/held, items: [{team_id, team_name, forfeited, tables, average_points, margin_of_error, places}]}` |
| `GET /teams/<team>` | our team: `active_submission_id, active_filename, active_created_at, submissions, health` |
| `GET /teams/<team>/submissions` | uploads: `id, filename, status (validating/ready/rejected/cancelled), rejection_reason, check_log, size_bytes, created_at` |
| `GET /teams/<team>/health` | per round: `decisions, missed, restarts, gave_up, error_log` |
| `GET /announcements` | organizer announcements |

Write calls the website itself uses (the Portal agent never makes these; listed so nobody is surprised):
upload is `POST /teams/<team>/submissions?filename=<name>` with the zip as the body; setting the active bot
is `PATCH /teams/<team>` with `{"active_submission_id": "<id>"}`.

Not found in the front-end code: the hand-history download address. The Getting started page says the
team page and the round page offer it (full set or a smaller subset). Find it on the page after the first
practice round.

## Running the rehearsal portal

```
cd ~/NoLimit/NO-LIMIT
prep/.venv/bin/python emu/portal_server.py --run <run>
```

It prints the address for Dylan (same Wi-Fi) and the key. Sign in on the page with the key. Upload a zip
with `agent.py` at its root; the upload test runs at once; then press **Make active**. A new upload is not
made active by itself, so always check "Active bot" after uploading. That is the habit for Sunday too.
