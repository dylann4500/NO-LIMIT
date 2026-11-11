#!/bin/zsh
# usage: ./make_submission.sh <params.json> <lookup|mc> '<points JSON>'  ->  submission/bot.py, gated.
# lab/adapter.py is appended automatically when it exists. Set POKER_VARIANT for non-hold'em.
# submission/upload/agent.py is the same file under the name the platform imports: poker-agent pack submission/upload out.zip
set -e
ROOT=${0:A:h}; PY=${PY:-$ROOT/.venv/bin/python}; PARAMS=${1:A}
mkdir -p $ROOT/submission/upload $ROOT/reference_bot
cd $ROOT/lab
$PY make_bot.py $PARAMS $ROOT/submission/bot.py ${2:-lookup} ${3:-'[50,30,20,0,0,0,0,0]'}
$PY test_bot.py $ROOT/submission
cp $ROOT/submission/bot.py $ROOT/reference_bot/bot.py
cp $ROOT/submission/bot.py $ROOT/submission/upload/agent.py
rm -rf $ROOT/submission/__pycache__
echo "PASSES only if: 0 illegal, and latency looks fine above. Then test through the kit before submitting."
