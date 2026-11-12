#!/bin/zsh
# usage: calibrate.sh FIELDDIR EPS BETA TAG [quick]   (run from the repo root)
S=${0:A:h}; F=$1; EPS=$2; BETA=$3; TAG=$4; O=$F/calib_$TAG; PY=starter-kit/.venv/bin/python
rm -rf $O; mkdir -p $O/q1 $O/q2; rm -f $F/cdf.json $F/adj.json
R="nice -n 10 $PY $S/simrun.py --field $F --hero none --eps $EPS --beta $BETA"
CLONE_QLOG=$O/q1 ${=R} --tables 1500 --seed c0 --out $O/c0.pkl >/dev/null
$PY $S/calib.py cdf $F $O/q1 >/dev/null
${=R} --tables 2000 --seed c1 --out $O/c1.pkl >/dev/null
$PY $S/calib.py adj $F $O/c1.pkl >/dev/null
if [[ "$5" != quick ]]; then
CLONE_QLOG=$O/q2 ${=R} --tables 1500 --seed c2 --out $O/c2.pkl >/dev/null
$PY $S/calib.py cdf $F $O/q2 >/dev/null
${=R} --tables 2500 --seed c3 --out $O/c3.pkl >/dev/null
$PY $S/calib.py adj $F $O/c3.pkl >/dev/null
fi
${=R} --tables 3000 --seed c4 --out $O/c4.pkl
$PY $S/calib.py compare $F $O/c4.pkl
