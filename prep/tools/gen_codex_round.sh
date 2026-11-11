#!/bin/zsh
# Next-round versions of Codex-written field bots: each gets its own league results and hand histories, like a real
# team between rounds, and writes <name>_r<N> next to the original. Uses the same signed-in accounts as gen_codex_bots.sh.
# usage: [CODEX_HOME=~/.codex-b] tools/gen_codex_round.sh -r 2 -l league/r1 [-n 2] [-e high] bot_name ...
ROOT=${0:A:h:h}; PY=$ROOT/.venv/bin/python; L=$ROOT/lab
R=2; LG=""; PAR=2; EFFORT=high
while getopts "r:l:n:e:" o; do case $o in r) R=$OPTARG;; l) LG=${OPTARG:A};; n) PAR=$OPTARG;; e) EFFORT=$OPTARG;; *) exit 2;; esac; done
shift $((OPTIND - 1))
WS=${TMPDIR:-/tmp}/codex_field; LOGS=$L/field_bots/_codex_logs
mkdir -p $WS $LOGS

run_one() {  # NAME NEW WORKSPACE PROMPT
  codex exec --skip-git-repo-check --approve-for-me -c model_reasoning_effort=\"$EFFORT\" -C $3 \
    -o $LOGS/$2.summary.md "$4" < /dev/null > $LOGS/$2.log 2>&1
  if [[ -f $3/lab/field_bots/$2/agent.py ]]; then cp -R $3/lab/field_bots/$2 $L/field_bots/; echo "done $2"; else echo "FAILED $2 (see $LOGS/$2.log)"; fi
}

pids=()
for NAME in $@; do
  NEW=${NAME%_r*}_r$R
  if [[ -f $L/field_bots/$NEW/agent.py ]]; then echo "skip $NEW (done)"; continue; fi
  W=$WS/$NEW; rm -rf $W; mkdir -p $W/lab/field_bots
  cp -R $L/field_kit $L/fake_sdk $W/lab/; rm -rf $W/lab/field_kit/teams
  cp $L/engine.py $L/pk.py $L/platform_sim.py $L/event_config.json $L/table_holdem.json $W/lab/
  cp -R $L/field_bots/$NAME $W/lab/field_bots/
  mkdir -p $W/lab/field_bots/$NAME/round$((R - 1))
  cp $LG/leaderboard.json $W/lab/field_bots/$NAME/round$((R - 1))/
  cp $LG/hh/$NAME.jsonl.gz $W/lab/field_bots/$NAME/round$((R - 1))/hand_history.jsonl.gz
  PROMPT="You are the AI coding assistant for one team in a live pokerbot tournament, and round $((R - 1)) has just finished. Your team's bot is in lab/field_bots/$NAME/ (read its NOTES.md first). Workspace root: $W (Python: $PY). The kit is lab/field_kit/ (README.md, play.py) and the SDK is lab/fake_sdk/; the other files under lab/ are the simulator behind play.py, so run play.py but don't read or import them.

Your round results are in lab/field_bots/$NAME/round$((R - 1))/:
- leaderboard.json: every team's average points per table (fair share 12.5), finishing places and failures.
- hand_history.jsonl.gz: hands from tables your bot played, one JSON object per hand. Fields: names (seat -> team), seat (yours), hole (your cards), button, blinds, stacks, events [kind, seat, amount, cards] including showdown reveals, and failed (your failed decisions).

Like a strong team between rounds, you have about 20 minutes:
- Analyze the histories with your own code and find what cost you points against this field.
- Improve the bot and write the new version to lab/field_bots/$NEW/ (agent.py plus any files it reads, and NOTES.md with what you changed and why). Leave lab/field_bots/$NAME/ unchanged.
The upload test in play.py must still pass, with no illegal actions or timeouts. Finish with a short summary of the changes and your local results."
  while true; do
    alive=(); for p in $pids; do kill -0 $p 2>/dev/null && alive+=($p); done; pids=($alive)
    (( ${#pids} < PAR )) && break
    sleep 5
  done
  echo "start $NEW"
  run_one $NAME $NEW $W "$PROMPT" &
  pids+=($!)
done
for p in $pids; do wait $p; done
echo "all done"
