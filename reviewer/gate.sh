#!/bin/zsh
# Release gate used during the event. Every release was run through this before upload.
#   usage: reviewer/gate.sh releases/<name>.zip
# Checks, in order:
#   1. rules: no packaged .py imports poker_engine/pokerkit; `poker-agent check` passes
#   2. upload-test conditions on this machine: heads-up vs check_or_fold, 20 hands, NO time bank, 5 seeds
#   3. 8-seat local match (bot x4, m10 x2, examples) with failed-decision count
#   4. optional: the same no-bank upload test on the build box (set GATE_BOX=<ssh host>; expects
#      ~/work/live/starter-kit with a .venv and ~/work/live/tests/match.py there)
#   5. behavior diff vs bots/v3b in identical tables against the field-proxy opponents (bdiff.sh):
#      VPIP outside 22-35% or PFR outside 17-27% blocks; any other decision rate moving >10 points is flagged
# Prints a VERDICT: SAFE or BLOCKED line. Requires the official starter kit at starter-kit/ with its .venv.
Z=${1:A}; R=${0:A:h}; REPO=${R:h}; K=$REPO/starter-kit; PY=$K/.venv/bin/python
T=$(mktemp -d); B=$T/bot; mkdir -p $B; cd $B && unzip -qo $Z || { echo "BLOCKED: unzip failed"; exit 1; }
name=${Z:t:r}
bad=0
echo "== $name ($(unzip -l $Z | tail -1 | awk '{print $2}') files)"
if grep -rlE 'import (poker_engine|pokerkit)|from (poker_engine|pokerkit)' $B --include='*.py' >/dev/null 2>&1; then echo "BLOCKED: a .py imports poker_engine/pokerkit"; bad=1; fi
$K/.venv/bin/poker-agent check $Z >/dev/null 2>&1 && echo "check: ok" || { echo "check: FAILED"; bad=1; }
cd $K
f=0; for s in g1 g2 g3 g4 g5; do r=$($PY $REPO/tests/match.py --tables 20 --seed $s --bank 0 --hand-cap 20 $B examples/check_or_fold 2>&1 | grep -E '^  bot ' ); n=${${r##*failed=}%% *}; f=$((f + ${n:-99})); done
echo "upload test (local, no bank, 5 seeds x 20): failed $f"; (( f > 0 )) && bad=1
r=$($PY $REPO/tests/match.py --tables 100 --seed g8 --bank 100 $B $B $B $B $REPO/bots/m10 $REPO/bots/m10 examples/check_or_fold examples/min_raiser 2>&1 | tail -4)
echo "8 seats (local):"; echo "$r"
echo "$r" | grep -E '^  bot ' | grep -q 'failed=0' || bad=1
if [ -n "$GATE_BOX" ]; then
  ssh -o ConnectTimeout=10 $GATE_BOX "rm -rf ~/work/live/gate_$name && mkdir -p ~/work/live/gate_$name" && scp -q -r $B/* $GATE_BOX:work/live/gate_$name/ && \
    bx=$(ssh $GATE_BOX 'cd ~/work/live/starter-kit && f=0; for s in b1 b2 b3; do r=$(.venv/bin/python ../tests/match.py --tables 20 --seed $s --bank 0 --hand-cap 20 ../gate_'"$name"' examples/check_or_fold 2>&1 | grep -E "^  gate_'"$name"' "); n=${r##*failed=}; n=${n%% *}; f=$((f + ${n:-99})); done; echo $f') && \
    { echo "upload test (build box, no bank, 3 seeds x 20): failed $bx"; if [ "$bx" != "0" ]; then bad=1; fi; true; } || echo "build box: unavailable (not gated there)"
else
  echo "build box: skipped (set GATE_BOX=<ssh host> to run the no-bank test on tournament-like hardware)"
fi
bo=$(zsh $R/bdiff.sh $B 2>&1); echo "$bo" | grep -E "MOVED|VPIP|PFR|BEHAVIOR"
echo "$bo" | grep -qE "VPIP [0-9]+% outside|PFR [0-9]+% outside" && { echo "BLOCKED: VPIP/PFR outside the real-field band"; bad=1; }
echo "$bo" | grep -q "BEHAVIOR: FLAGGED" && echo "STRATEGY: REVIEW the MOVED lines (intended changes only)" || echo "STRATEGY: no unintended shifts"
rm -rf $T
(( bad )) && echo "VERDICT: BLOCKED" || echo "VERDICT: SAFE"
