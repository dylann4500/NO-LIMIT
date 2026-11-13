#!/bin/bash
# Live simulation sim4: emulator (2 simulated teams) + mock portal + both hubs (Sonnet everywhere) + simulated humans.
set -u
SP=/private/tmp/claude-501/-Users-samuelchoi-NoLimit-NO-LIMIT/c63e719e-259f-4689-a23e-2d16971ed9cb/scratchpad/sim4
NL=~/NoLimit/NO-LIMIT
UVH="uv run --no-project --with aiohttp==3.14.5 --with claude-agent-sdk==0.2.181 --with modal==1.6.4"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $SP/run.log; }
# 1. the Sunday repo, exactly as SUNDAY.md says
R=$SP/repo; rm -rf $R; mkdir -p $R && cd $R && git init -q
for f in START_HERE DECISION_RULES FIRST_PROMPT TWIST_NOTES PORTAL_AGENT EVIDENCE_TABLE FINALS_PLAYBOOK FINGERPRINTING; do cp $NL/docs/$f.md $R/ || log "MISSING doc $f.md"; done
for d in bot candidates releases notes; do mkdir -p $R/$d; touch $R/$d/.keep; done
printf '.venv/\n__pycache__/\n*.pyc\n*.gz\n*.csv\nportal-data*/\n' > $R/.gitignore
git add -A && git -c user.email=sim@x -c user.name=sim commit -qm "Sunday repo (sim4)"
log "repo ready"
# 2. emulator + portal
cd $NL
rm -rf emu/runs/sim4
prep/.venv/bin/python emu/rehearsal.py --run sim4 --teams 2 --scale 0.5 --weights 1,2,3 --wait > $SP/emu.log 2>&1 &
for i in $(seq 1 60); do grep -q READY $SP/emu.log && break; sleep 5; done; log "emu: $(tail -1 $SP/emu.log)"
prep/.venv/bin/python emu/portal_server.py --run sim4 > $SP/portal.log 2>&1 &
sleep 4
# 3. hubs
cd $NL/hub
$UVH python hub.py --person samuel --repo $R --data $SP/s --namespace=-sim4 --port 7791 --model claude-sonnet-5-5 --scale 0.5 \
  --portal-base http://127.0.0.1:8765/tournament/api --portal-key-file ~/.config/avalon-rehearsal/portal-key --portal-data $SP/pd > $SP/hub-s.log 2>&1 &
$UVH python hub.py --person dylan --repo $R --data $SP/d --namespace=-sim4 --port 7792 --model claude-sonnet-5-5 --scale 0.5 > $SP/hub-d.log 2>&1 &
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:7791/api/state && curl -s -o /dev/null http://127.0.0.1:7792/api/state && break; sleep 3; done
log "hubs up"
sleep 20
# 4. minute 0 two minutes from now, on the emulator and the hubs together
T0=$(date -v+2M +%H:%M)
cd $NL && prep/.venv/bin/python emu/rehearsal.py --run sim4 --start $T0 >> $SP/emu.log 2>&1
curl -s -X POST -H 'Content-Type: application/json' -d "{\"start\":\"$T0\",\"scored\":3,\"scale\":0.5}" http://127.0.0.1:7791/api/schedule | tee -a $SP/run.log; echo
log "minute 0 = $T0"
# 5. simulated humans
cd $NL/hub
$UVH python simhuman.py --person samuel --hub http://127.0.0.1:7791 --repo $R --log $SP/sim-samuel.log --min-gap 40 --max-gap 80 > $SP/simh-s.out 2>&1 &
$UVH python simhuman.py --person dylan --hub http://127.0.0.1:7792 --repo $R --portal http://127.0.0.1:8765/tournament/api \
  --portal-key-file ~/.config/avalon-rehearsal/portal-key --log $SP/sim-dylan.log --min-gap 40 --max-gap 80 > $SP/simh-d.out 2>&1 &
log "sim humans started"
# 6. the kit: Dylan puts it in starter-kit/ when announced and tells his Chat
for i in $(seq 1 120); do [ -d $NL/emu/runs/sim4/avalon/kit ] && [ "$(date +%H:%M)" \> "$T0" -o "$(date +%H:%M)" = "$T0" ] && break; sleep 5; done
sleep 30
cp -R $NL/emu/runs/sim4/avalon/kit $R/starter-kit && log "kit copied to starter-kit/"
curl -s -X POST -H 'Content-Type: application/json' -d '{"text":"The kit is in starter-kit/ (I just put it there). The Format page: 3 scored rounds, weights 1, 2, 3."}' http://127.0.0.1:7792/api/agents/d-overview/send >> $SP/run.log
log "told Dylan's Chat about the kit"
wait
