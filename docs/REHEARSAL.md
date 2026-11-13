# Running a practice run (rehearsal)

For Dylan and Samuel. A rehearsal is a full Finals day on our own laptops: a copy of the tournament runs on
Samuel's Mac (and Modal), with simulated opponent teams, a copy of the organizers' portal, and both hubs.
Read `docs/START_HERE.md` first.

## What runs where

| Piece | Where | Started by |
|---|---|---|
| Simulated tournament: opponent teams on Modal, the rounds, the clock | Samuel's Mac (`emu/rehearsal.py`) | Samuel's Claude session (ask it: "start a rehearsal") |
| Portal copy: same API as the real site, uploads, results, hand downloads | Samuel's Mac, port 8765 | Same |
| Samuel's hub | Samuel's Mac | Samuel |
| Dylan's hub | Dylan's laptop | Dylan |

Dylan reaches the portal copy through Tailscale. Both laptops need the Tailscale app connected, and Samuel's
Mac must be shared with Dylan:

**http://100.111.100.112:8765/tournament/login?key=nlk_5dc6b1951721cd6d66981d62333a7fd3**

The link and key stay the same for every rehearsal.

## Steps

1. **Samuel: ask your Claude session to "reset and start a rehearsal"** (normal speed, or "4x speed" for a
   45-minute run). It:
   - wipes the rehearsal repo (`nolimit-rehearsal`) back to the setup files;
   - starts the tournament and the portal copy;
   - tells you minute 0 and a run name, e.g. `reh3`.
2. **Both: start your hub with that run name** (fresh state and message line, so nothing from old runs
   carries over).

   **Samuel:**
```
cd ~/NoLimit/NO-LIMIT && git pull
./hub/start.sh samuel ~/nolimit-rehearsal --data ~/.avalon-hub-reh3/samuel --namespace=-reh3 --portal-data ~/portal-data-reh3 --portal-base http://127.0.0.1:8765/tournament/api --portal-key-file ~/.config/avalon-rehearsal/portal-key
```
   **Dylan:**
```
cd ~/NoLimit/NO-LIMIT && git pull
./hub/start.sh dylan ~/nolimit-rehearsal --data ~/.avalon-hub-reh3/dylan --namespace=-reh3
```
   For a sped-up run, the Claude session sets the clock's speed for you.
3. **Both: open http://127.0.0.1:7777**, pick your name, and check the sidebar says "linked".
4. **Samuel: set minute 0** on Home (or tell your Overseer the time).
5. **Play the day exactly as in `docs/SUNDAY.md`.** The only differences:
   - **Dylan uploads on the portal copy** (the Tailscale link above): Upload a zip, then **Make active**.
     The upload test runs at once; a rejected upload shows the reason.
   - The kit is already in the rehearsal repo (`starter-kit/`).
   - No hand-history link to copy: the watcher already knows where the portal copy keeps them.
6. **Debrief afterwards** (15 minutes):
   - Which reminder or card was late, unclear or wrong?
   - Did anything need you that never reached the bell?
   - Did an agent ask for something you couldn't do?
   - Which findings were wrong, and did anyone catch them?

   Tell the Claude session; it fixes the hub and the prompts.

## Simulated teammates (optional, for finding bugs without you)

The Claude session can also run AI stand-ins for you both (`hub/simhuman.py`). They look at each hub's
screen like a person would, answer the bell, greenlight or reject cards, post ideas, and (as Dylan)
upload bots to the portal copy, and they write down anything confusing. Tonight's run with them found
eight problems, all fixed.

## Viewing the screen without running anything

To look around with saved data and no agents running, start a hub with `--view-only`, e.g.:
```
./hub/start.sh samuel ~/nolimit-rehearsal --data <a saved hub folder> --view-only --port 7781
```
