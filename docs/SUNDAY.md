# Sunday, step by step

For Dylan and Samuel. Read `docs/START_HERE.md` first; this is the checklist. Each step says who does it.
Times are from the variant announcement (minute 0).

## Saturday (the night before), about 30 minutes

1. **Both: update the code.**
```
cd ~/NoLimit/NO-LIMIT && git fetch && git checkout emu/rehearsal && git pull
```
2. **Both: check the tools.** Each line should work without errors:
```
claude --version                                   # Claude Code, logged in
uv --version                                       # if missing: brew install uv
uv run --no-project --with modal modal app list    # Modal, team workspace
/Applications/Codex.app/Contents/Resources/codex login status   # Codex (optional): "Logged in using an API key"
```
3. **Samuel: make the Sunday repo.** A fresh private GitHub repo (e.g. `avalon-finals`), invite Dylan,
   and add these from `~/NoLimit/NO-LIMIT/docs/`:
   - `START_HERE.md`, `FIRST_PROMPT.md`, `TWIST_NOTES.md`, `PORTAL_AGENT.md` and `EVIDENCE_TABLE.md`;
   - empty `bot/`, `candidates/`, `releases/` and `notes/` folders (put a `.keep` file in each);
   - a `.gitignore` containing:
```
.venv/
__pycache__/
*.pyc
*.gz
*.csv
portal-data*/
```

   No code goes in it. Both of you clone it, e.g. `git clone <url> ~/avalon-finals`.
4. **Samuel: check the portal key still works** (the watcher uses it):
```
curl -s -H "Authorization: Bearer $(cat ~/.config/no-limit-2026/api-key)" -A avalon-check https://pokerbot.sequoiacap.com/tournament/api/auth/api-key | head -c 200
```
   It should list a team, ideally including the Finals competition. If you have a new key for the
   Finals, save it in that file.
5. **Both: run each hub once for a minute** on a phone hotspot, using the Sunday commands below. Open
   http://127.0.0.1:7777: no red "Not linked" bar under the header means the laptops are linked. Then press Ctrl+C.
6. **Decide who claims the $250 Codex credit** before either of you opens the link.

## Sunday morning, before minute 0

- **Both:** plug in, lids open, phone hotspot on, notifications off.
- **Both:** start the hub and leave its Terminal window open all day. If you close it, your agents stop.

  **Samuel:**
```
cd ~/NoLimit/NO-LIMIT
./hub/start.sh samuel ~/avalon-finals --data ~/.avalon-hub-live/samuel --namespace=-live --portal-data ~/portal-data-live --portal-base https://pokerbot.sequoiacap.com/tournament/api --portal-key-file ~/.config/no-limit-2026/api-key --small-hands
```
  **Dylan:**
```
cd ~/NoLimit/NO-LIMIT
./hub/start.sh dylan ~/avalon-finals --data ~/.avalon-hub-live/dylan --namespace=-live
```
  `--small-hands` saves hotspot data by downloading only the first-1000 hand file; drop it on good Wi-Fi.
- **Both:** open http://127.0.0.1:7777 and click your name. Your Overseer starts and reads the plan.
- **Dylan:** have the organizers' portal open in a browser tab, logged in. Uploads happen there.

## Minute 0: the variant is announced

1. **Samuel: press Start building** on the board the moment the variant is announced (or, if you're
   late, type the announcement time next to it, or tell your Overseer "the variant was announced at
   14:02"). Both laptops' clocks start and both Overseers start the plan: they send each agent its
   instructions at the right minute, so you don't have to.
2. **Both:** read the Format page on the portal: round weights, payouts, anything unusual. If the times
   differ from the usual schedule, tell your Overseer, e.g. "practice 1 is at 14:25".
3. **Dylan:** fetch the kit. Either run the setup skill with `/no-limit-2026-setup` in Claude Code with
   the API key, or download it from the portal. Put it in `~/avalon-finals/starter-kit/`, then tell your
   Overseer "the kit is in starter-kit/". The Overseer starts Platform on the first prompt and the twist
   notes.

## The build hour

| When | Who | What to do |
|---|---|---|
| ~10 | Dylan | When your Overseer says "upload releases/v1.zip", upload it on the portal and make it **active**. Check the team page shows it as the active bot |
| 20, 30, 40 | Dylan | Before each practice round your Overseer posts which style plays and the file. Upload, make active |
| after practice 1 | Samuel | **Step 7 below:** give the watcher the hand-history link |
| any time | Both | Read the bell. Greenlight or reject notes; click one to ask about it. Post ideas with + New idea |
| 50-60 | Dylan | The best real-field scorer goes active for scored round 1. Your Overseer posts it as a Live bot note; greenlight, upload, make active |

### Step 7 (Samuel, once): the hand-history link

The organizers' code doesn't reveal where hand histories download from.
1. After practice round 1 finishes, open the portal's team page (or the round page) and right-click
   **Download** (the small/first-1000 one) → **Copy Link Address**.
2. Paste it somewhere and replace the round's ID in it with `{tid}`. If there is a part that picks the
   small file, replace it with `{q}`; if not, leave it.
3. Stop your hub (Ctrl+C) and start it again with the same command plus
   `--hands-url '<the link with {tid}>'` at the end.
4. Your agents resume where they were. The watcher fetches any hand data it couldn't get before, and
   says so in the bell after 20 minutes if it still can't.

## Every 20-minute window

The countdown strip shows the next step. The clock reminds each of you when a step needs your hands.

| Time to scored round | Who | What to do |
|---|---|---|
| T-13 | Samuel | Results land. Read your Overseer's brief and new findings. Push back if something looks off |
| T-12 | Dylan | If your Overseer says the challenger is ready: upload it and make it active (it plays the practice round) |
| T-9 | Dylan | **Put the live bot back as active straight away** |
| T-8 | Both | **Decide.** The green Live bot note is on the board. Greenlight, reject or suggest. Either of you can decide |
| T-5 | | No decision means the live bot plays; nothing to upload |
| T-3 | Dylan | Upload the greenlit bot (exactly the file named on the note, e.g. `releases/v4.zip`), make it active, check the team page |

Between those, steer when you like: ask "why?", redirect, post ideas.

## When something goes wrong

| What you see | What to do |
|---|---|
| A red bar: "Not linked to …'s laptop" | Agents keep working; messages wait and are delivered later. Talk to each other directly. If it lasts, check the hotspot |
| An agent shows **Usage limit · resumes HH:MM** | Its messages are kept. Ask your Overseer to move urgent work to another agent or to Codex. Optional: add an API key (`START_HERE.md` section 8) |
| An agent shows **Error · retrying** | It retries by itself. If it stays red for over 5 minutes, open it and read the last error; tell your Overseer |
| **Upload rejected** (bell) | The previous bot stays active. Tell your Overseer; Platform fixes it and gives you a new file |
| **No active bot / wrong active bot** (urgent bell) | Make the right file active on the portal now |
| The clock is wrong | Tell your Overseer the right time ("scored round 3 is at 15:42"), or tell it when minute 0 was |
| A permission request you don't understand | Deny it. The agent finds another way |
| The hub page won't load | Look at its Terminal window. It restarts itself after a crash; if the window is closed, start it again with the same command (agents resume) |
| Codex jobs fail | Nothing to do; agents fall back to Claude helpers. The bell says if Codex needs a login |
| You disagree with your teammate at T-8 and there's no time | The live bot plays |

## After the last round

Results land about 8 minutes after scored round 6. Leave the hubs running until the final standings are
in, then Ctrl+C.
