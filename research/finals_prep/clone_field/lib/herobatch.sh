#!/bin/zsh
# usage: herobatch.sh FIELDDIR TAG SEED TABLES EPS BETA bot1 bot2 ...   (from the repo root)
S=${0:A:h}; F=$1; TAG=$2; SEED=$3; N=$4; EPS=$5; BETA=$6; shift 6
O=$S/../out; PY=starter-kit/.venv/bin/python
for b in $@; do
  nice -n 10 $PY $S/simrun.py --field $F --hero bots/$b --tables $N --seed $SEED --eps $EPS --beta $BETA --out $O/${TAG}_$b.pkl
done
