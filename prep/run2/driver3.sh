#!/bin/zsh
PY=/Users/samuelchoi/Pokerbot/.venv/bin/python
cd /Users/samuelchoi/Pokerbot/run2
until grep -q "ALL DONE" progress2.log 2>/dev/null; do sleep 5; done
cp ../lab/field.py . 
TUNE_TABLE=1 TUNE_BASE=1 START_JSON=tuned_meta1.json CAND_PATH=tuned_meta1.json CAND_TABLE=1 $PY -u tune.py blend top3,steep,linear,wta typical,strong,aggro,all_mirror,mirror 12 50 10 > H_tune_blend.log 2>&1
$PY -u exp_blend.py > H_blend.log 2>&1
echo "BLEND DONE" > blend.done
