#!/bin/zsh
# Round analyzer used between rounds: summary + busts + jam analysis, run in parallel (~10 s for 20k tables).
#   usage: reviewer/analyze_round.sh ~/Downloads/hands-<id>.jsonl.gz
# Writes full outputs to reviewer/out/<file>/ (git-ignored) and prints the key sections.
R=${0:A:h}; REPO=${R:h}; PY=$REPO/starter-kit/.venv/bin/python; F=${1:A}; T=$REPO/bots/v3/tables_bayarea.json
o=$R/out/${F:t:r:r}; mkdir -p $o
$PY -I $R/hh2.py $F > $o/summary.txt 2>&1 &
$PY -I $R/hh3.py $F > $o/busts.txt 2>&1 &
$PY -I $R/hh4b.py $F $T > $o/jams.txt 2>&1 &
wait
cat $o/summary.txt; echo; cat $o/busts.txt; echo; sed -n '/P(jam/,/top jam/p' $o/jams.txt
