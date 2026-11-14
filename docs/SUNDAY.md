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
   - `START_HERE.md`, `DECISION_RULES.md`, `FIRST_PROMPT.md`, `TWIST_NOTES.md`, `PORTAL_AGENT.md`,
     `EVIDENCE_TABLE.md`, `FINALS_PLAYBOOK.md` and `FINGERPRINTING.md`;
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
5. **Both: run each hub once** on a phone hotspot, with **check** folders so nothing carries into Sunday
   (Sunday's commands below use different ones):
```
./hub/start.sh samuel ~/avalon-finals --data ~/.avalon-hub-check/samuel --namespace=-check --portal-data ~/portal-data-check --portal-base https://pokerbot.sequoiacap.com/tournament/api --portal-key-file ~/.config/no-limit-2026/api-key --small-hands
./hub/start.sh dylan ~/avalon-finals --data ~/.avalon-hub-check/dylan --namespace=-check
```
   Open http://127.0.0.1:7777 and type "run the check" in the Chat. Both Chats list the results: the link,
   the portal (reading it, and downloading a hand file once a round exists), Claude, Codex, the repo and its
   plan docs, disk space. Fix every ❌. Both run `git -C ~/NoLimit/NO-LIMIT rev-parse --short HEAD` and
   compare: the two laptops must run the same hub code. Then press Ctrl+C.
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
- **Both:** open http://127.0.0.1:7777 and click your name. Your Chat (the lead of your side) starts and reads the plan. Type "run the check" in it.
- **Dylan:** have the organizers' portal open in a browser tab, logged in. Uploads happen there.
- **About 2 hours before minute 0, either of you: type "start the research" in your Chat.** Every worker on both
  laptops gets a pre-event research topic (notes only, no bot code: the regionals and Pittsburgh, what the
  Finals field will do, a contrarian memo on what beats a field that read the same lessons, the build and test
  plans). Notes land in `notes/pre/`; Samuel's Chat merges them into `notes/plan.md`. Read the contrarian memo.

## Minute 0: the variant is announced

1. **Samuel: tell the Chat "the competition starts now"** (or press Start building) the moment the variant is announced (or, if you're
   late, type the announcement time next to it, or tell your Chat "the variant was announced at
   14:02"). Both laptops' clocks start and the clock gives each agent its
   instructions at the right minute, so you don't have to.
2. **Both:** read the Format page on the portal: round weights, payouts, the **upload cooldown**, anything
   unusual. If the shape differs from 60-minute build / a round every 20 minutes / 6 rounds, tell your Chat in
   one line ("the build is 90 minutes", "rounds are every 30 minutes", "there are 5 scored rounds"). Times you
   learn later go in the same way ("scored round 3 is at 15:40"); a scored round's real start is also picked up
   from the portal automatically, and later deadlines follow it.
3. **Dylan:** fetch the kit. Either run the setup skill with `/no-limit-2026-setup` in Claude Code with
   the API key, or download it from the portal. Put it in `~/avalon-finals/starter-kit/`, then tell your
   Chat "the kit is in starter-kit/". Platform starts on the first prompt and the twist
   notes.

## The build hour

| When | Who | What to do |
|---|---|---|
| ~10 | Dylan | When the bell says "Upload v1.zip now": Live menu → click v1 to download it → upload it on the portal and make it **active**. The Live chip turns green when the portal runs it |
| 17, 27, 37, 47 | Dylan | Your Chat names the bot for the next practice round (the most informative test, not a fixed style rota; one of them is the Challenger's clean-room design D). The bell reminds you 3 minutes before each practice: download it from the Live menu, upload, make active |
| after practice 1 | Samuel | **Step 7 below:** give the watcher the hand-history link |
| any time | Both | Read the bell and your Chat. Decisions are pinned at the top of the Chat: answer in words; ask anything first. A **plan challenge** (an agent saying the plan looks wrong for today's field) appears in both Chats: read it and say what you think |
| 50-60 | Dylan | The best real-field scorer goes active for scored round 1. Your Chat asks "which bot?"; answer it in words, then upload and make active |

### Step 7 (Samuel, once): the hand-history link

The organizers' code doesn't reveal where hand histories download from. If the watcher already downloads them
(the Analyst's tile for practice 1 data turns "done"), skip this.
1. After practice round 1 finishes, open the portal's team page (or the round page) and right-click
   **Download** (the small/first-1000 one) → **Copy Link Address**.
2. Paste it into your Chat as `hands link: <the link>`. The hub finds the round's id in it, keeps it across
   restarts and fetches any hand data it couldn't get before. No restart.

## Every 20-minute window

The countdown strip shows the next step. The clock reminds each of you when a step needs your hands.

| Time to scored round | Who | What to do |
|---|---|---|
| T-13 | Samuel | Results land. Open the Analyst (or ask your Chat) for the findings. Push back if something looks off |
| T-12 | Dylan | If your Chat says the challenger is ready: upload it and make it active (it plays the practice round) |
| T-9 | Dylan | **Put the live bot back as active straight away** (if the cooldown is long, your Chat re-plans the uploads: DECISION_RULES §3 "Uploads") |
| T-8 | Both | **Decide.** The "Which bot?" question is pinned at the top of your Chat with both bots' numbers and the rule's answer. Answer in words ("yes, use v13" / "no, keep v8"). Either of you can decide |
| T-5 | | No answer: the hub applies the rule's answer itself (it may be the challenger; the bell then asks Dylan to upload it) |
| T-3 | Dylan | Upload the decided bot (exactly the file the bell names, e.g. `releases/v4.zip`), make it active, check the team page |

Between those, steer when you like: ask "why?", redirect, ask an agent to research something.

## When something goes wrong

| What you see | What to do |
|---|---|
| A red bar: "Not linked to …'s laptop" | Agents keep working; messages wait and are delivered later. Talk to each other directly. If it lasts, check the hotspot |
| An agent shows **Usage limit · resumes HH:MM** | Its messages are kept. Ask your Chat to move urgent work to another agent or to Codex. Optional: add an API key (`START_HERE.md` section 8) |
| An agent shows **Error · retrying** | It retries by itself. If it stays red for over 5 minutes, open it and read the last error; tell your Chat |
| **Upload rejected** (bell) | The previous bot stays active. Tell your Chat; Platform fixes it and gives you a new file |
| **No active bot / wrong active bot** (urgent bell) | Make the right file active on the portal now |
| The clock is wrong | Tell your Chat the right time ("scored round 3 is at 15:42"), or tell it when minute 0 was |
| A permission request you don't understand | Deny it. The agent finds another way |
| The hub page won't load | Look at its Terminal window. It restarts itself after a crash; if the window is closed, start it again with the same command (agents resume) |
| Codex jobs fail | Nothing to do; agents fall back to Claude helpers. The bell says if Codex needs a login |
| You disagree with your teammate at T-8 and there's no time | The hub notices opposite answers, says so in both Chats and keeps the rule's answer until you agree |
| The link between laptops is down at T-8 | Samuel reads his Chat's recommendation to Dylan aloud; Dylan answers in his Chat. With nothing new, the live bot plays |
| The leaderboard is hidden | The hub says so; the Chats work out our total from each round's results and weights, and treat us as outside the top 3 unless we clearly weren't |

## After the last round

Results land about 8 minutes after scored round 6. Leave the hubs running until the final standings are
in, then Ctrl+C.
