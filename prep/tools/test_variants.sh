#!/bin/zsh
ROOT=${0:A:h:h}
PY=${PY:-$ROOT/.venv/bin/python}
OUT=$(mktemp -d)
cd $ROOT/lab
for v in holdem flushfh shortdeck hole3 omaha; do
  d=$OUT/bot_$v; mkdir -p $d
  POKER_VARIANT=$v $PY make_bot.py tuned_final.json $d/bot.py lookup >/dev/null
  echo "=== $v  $(wc -c < $d/bot.py) bytes"
  POKER_VARIANT=$v $PY test_bot.py $d 2>&1 | tail -5 | cut -c1-125
  POKER_VARIANT=$v $PY test_parity.py $d 60 2>&1 | head -2 | cut -c1-120
done
