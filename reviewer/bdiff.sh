#!/bin/zsh
# Behavior diff: plays CANDIDATE and BASE (default bots/v3b) in identical local tables against the
# field-proxy opponents, then compares every preflop and first-flop decision frequency (behavior.py).
#   usage: reviewer/bdiff.sh CANDIDATE_BOT_DIR [BASE_BOT_DIR]
# Exit 0 = no unintended shifts, 1 = flagged, 2 = a run produced no history.
R=${0:A:h}; REPO=${R:h}; K=$REPO/starter-kit; C=${1:A}; BASE=${${2:-$REPO/bots/v3b}:A}
P=$REPO/tests/opponents; H=$(mktemp -d)
F=($P/station $P/station $P/maniac $P/tag $P/tag $REPO/bots/m10 $REPO/bots/v2)
cd $K
.venv/bin/poker-agent play --tables 150 --seed bdiff1 --variant flop_discard_reveal --history $H/base.jsonl --hero 0 $BASE $F > $H/base.log 2>&1 &
.venv/bin/poker-agent play --tables 150 --seed bdiff1 --variant flop_discard_reveal --history $H/cand.jsonl --hero 0 $C $F > $H/cand.log 2>&1 &
wait
for x in base cand; do [ -s $H/$x.jsonl ] || { echo "BEHAVIOR: ERROR, no $x history"; tail -3 $H/$x.log; exit 2; }; done
$K/.venv/bin/python -I $R/behavior.py $H/base.jsonl $H/cand.jsonl; r=$?; rm -rf $H; exit $r
