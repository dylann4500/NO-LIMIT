#!/bin/zsh
# Field bots written by Codex with the same team prompts the Claude agents got (lab/field_kit/teams/).
# Sign in yourself first; the key never needs to leave your terminal:
#   codex login                                        # ChatGPT account
#   printenv OPENAI_API_KEY | codex login --with-api-key  # or an API key already in your environment
# usage: [CODEX_HOME=~/.codex-b] tools/gen_codex_bots.sh [-m MODEL] [-e EFFORT] [-n PARALLEL] [-t TAG] [brief ...]
#   default briefs: default x4, iterate, equity, icm, exploit, gto, aggro, tuned  ->  lab/field_bots/openai_<TAG>_<brief>_<k>/
#   CODEX_HOME picks which signed-in account runs the batch; give each account its own TAG so names don't collide.
# Each run gets its own workspace outside the repo holding only the kit and the simulator it needs, so Codex
# can't pick up this repo's AGENTS.md or strategy files. Finished bots are skipped on a rerun.
ROOT=${0:A:h:h}; PY=$ROOT/.venv/bin/python; L=$ROOT/lab
MODEL=""; PAR=3; TAG=a; EFFORT=high
while getopts "m:n:t:e:" o; do case $o in m) MODEL=$OPTARG;; n) PAR=$OPTARG;; t) TAG=$OPTARG;; e) EFFORT=$OPTARG;; *) exit 2;; esac; done
shift $((OPTIND - 1))
BRIEFS=(${@:-default default default default iterate equity icm exploit gto aggro tuned})
WS=${TMPDIR:-/tmp}/codex_field; LOGS=$L/field_bots/_codex_logs
mkdir -p $WS $LOGS

run_one() {  # NAME WORKSPACE PROMPT
  codex exec --skip-git-repo-check --approve-for-me -c model_reasoning_effort=\"$EFFORT\" ${MODEL:+-m $MODEL} -C $2 \
    -o $LOGS/$1.summary.md "$3" < /dev/null > $LOGS/$1.log 2>&1
  if [[ -f $2/lab/field_bots/$1/agent.py ]]; then cp -R $2/lab/field_bots/$1 $L/field_bots/; echo "done $1"; else echo "FAILED $1 (see $LOGS/$1.log)"; fi
}

k=0; pids=()
for b in $BRIEFS; do
  k=$((k + 1)); NAME=openai_${TAG}_${b}_$k
  if [[ -f $L/field_bots/$NAME/agent.py ]]; then echo "skip $NAME (done)"; continue; fi
  W=$WS/$NAME; rm -rf $W; mkdir -p $W/lab/field_bots
  cp -R $L/field_kit $L/fake_sdk $W/lab/; rm -rf $W/lab/field_kit/teams
  cp $L/engine.py $L/pk.py $L/platform_sim.py $L/event_config.json $L/table_holdem.json $W/lab/
  PROMPT="You are an AI coding assistant working for one team in a live pokerbot tournament. Your team wants to win, and you have the strongest model available, so build the best bot you can, not a demo.

Workspace root: $W (Python: $PY). Everything your team has is in lab/field_kit/ (read README.md first) and the SDK in lab/fake_sdk/. The other files under lab/ are the simulator behind lab/field_kit/play.py: run play.py, but don't read or import them.

Work the way a strong team works in a 60-minute build: design, implement, run the local tests, fix failures, and improve over two or three iterations. The bot must pass the upload test, never time out on the real machines (about 2.5x slower than this one), and return only legal actions.

Write your bot to lab/field_bots/$NAME/agent.py (plus any files it reads, in that folder) and lab/field_bots/$NAME/NOTES.md covering your approach, what you tested, and your final play.py results. Finish with a short summary of the design and the final results.

NAME: $NAME

$(cat $L/field_kit/teams/$b.md)"
  while true; do  # at most PAR runs at once
    alive=(); for p in $pids; do kill -0 $p 2>/dev/null && alive+=($p); done; pids=($alive)
    (( ${#pids} < PAR )) && break
    sleep 5
  done
  echo "start $NAME"
  run_one $NAME $W "$PROMPT" &
  pids+=($!)
done
for p in $pids; do wait $p; done
echo "all done; bots in $L/field_bots"
