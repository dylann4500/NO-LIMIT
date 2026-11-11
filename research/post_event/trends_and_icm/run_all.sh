#!/bin/zsh
# Re-run extraction for all six rounds (6 worker processes at a time), then: python -I aggregate.py
D=${0:A:h}; REPO=${D:h:h:h}; PY=$REPO/starter-kit/.venv/bin/python
while read R F; do
  $PY -I $D/analyze.py $REPO/$F $D/$R.pkl 6
done < $D/files.txt
