#!/bin/zsh
PY=/Users/samuelchoi/Pokerbot/.venv/bin/python
cd /Users/samuelchoi/Pokerbot/snap2
$PY -u tune.py robust top3,linear,steep,wta typical,strong,aggro,passive 12 60 10 > tune_robust.log 2>&1
$PY -u exp_final.py tuned_robust.json > final.log 2>&1
$PY -u exp_abl.py tuned_robust.json > abl.log 2>&1
$PY -u exp_icm.py tuned_robust.json > icm.log 2>&1
$PY -u exp_hu.py tuned_robust.json > hu.log 2>&1
for v in shortdeck flushfh hole3 omaha; do POKER_VARIANT=$v $PY -u exp_variant.py tuned_robust.json > variant_$v.log 2>&1; done
POKER_VARIANT=shortdeck POKER_TABLE_FROM=holdem $PY -u exp_variant.py tuned_robust.json > variant_shortdeck_stale.log 2>&1
