#!/bin/zsh
PY=/Users/samuelchoi/Pokerbot/.venv/bin/python
cd /Users/samuelchoi/Pokerbot/snap2
while pgrep -f snap2/chain.sh > /dev/null; do sleep 5; done
for p in top3 linear; do
  $PY -u tune.py $p $p typical,strong,aggro,passive 12 60 10 > tune_$p.log 2>&1
done
$PY -u exp_specific.py > specific.log 2>&1
