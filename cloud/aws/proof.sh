#!/bin/bash
# The AWS proof run (prep only, not for Sunday): measures the fleet on the regional kit and bots with the same
# field and table counts as cloud/README.md's Modal measurement, plus the minute-0 drill. Run from the repo root
# of a checkout that has starter-kit/ (or set KIT=/path/to/kit). Needs: signed in, setup done, envelope agreed.
#   cloud/aws/proof.sh [count] [type]        e.g. cloud/aws/proof.sh 1 c7a.48xlarge
# Leaves the instances UP at the end (so they can be reused); `python3 cloud/aws/fleet.py down` stops them.
set -euo pipefail
COUNT=${1:-1}
TYPE=${2:-c7a.48xlarge}
KIT=${KIT:-starter-kit}
F="python3 cloud/aws/fleet.py"
FIELD=${FIELD:-"bots/v10 bots/v10 bots/v9s bots/v9s bots/v6 bots/v6 bots/v3b bots/v3b"}
now() { python3 -c 'import time; print(f"{time.time():.1f}")'; }
since() { python3 -c "print(f'{$(now) - $1:.1f}')"; }
LOG=cloud/results/aws-proof-$(date +%m%d-%H%M).log
mkdir -p cloud/results
exec > >(tee -a "$LOG") 2>&1

echo "== $(date) proof: $COUNT x $TYPE"
if [ -z "${AVALON_FLEET_HOSTS:-}" ]; then  # (AVALON_FLEET_HOSTS = local test hosts: skip AWS)
  $F check --type "$TYPE"
  t=$(now); $F up --count "$COUNT" --type "$TYPE" --fleet proof; echo "UP: $(since $t)s"
fi

echo "== minute-0 drill, cold (no install cache): push kit + bots, build, 1,000 tables"
$F sh 'rm -rf ~/w/starter-kit ~/.cache/uv' >/dev/null
t=$(now)
$F push "$KIT:starter-kit" bots cloud;             echo "  push done at $(since $t)s"
$F build starter-kit;                              echo "  build done at $(since $t)s"
$F run --name drill_cold --items 1000 --merge tables "starter-kit/.venv/bin/python cloud/kit_match.py $FIELD --seed drill --tables {count} --first-table {first} --out {out}"
echo "DRILL COLD (push+build+1000 tables): $(since $t)s"

echo "== minute-0 drill, warm cache (the Sunday plan: the regional kit built earlier)"
$F sh 'rm -rf ~/w/starter-kit' >/dev/null
t=$(now)
$F push "$KIT:starter-kit"; $F build starter-kit
$F run --name drill_warm --items 1000 --merge tables "starter-kit/.venv/bin/python cloud/kit_match.py $FIELD --seed drill --tables {count} --first-table {first} --out {out}"
echo "DRILL WARM (push+build+1000 tables): $(since $t)s"

[ -n "${DRILL_ONLY:-}" ] && exit 0
echo "== the cloud/README.md comparison: 4,000 tables, same field"
$F run --name aws_field4k --items 4000 --merge tables "starter-kit/.venv/bin/python cloud/kit_match.py $FIELD --seed s4k --tables {count} --first-table {first} --out {out}"
echo "== steady state: 20,000 tables"
$F run --name aws_field20k --items 20000 --merge tables "starter-kit/.venv/bin/python cloud/kit_match.py $FIELD --seed s20k --tables {count} --first-table {first} --out {out}"
$F status
echo "== $(date) done; log $LOG. Instances are still up: python3 cloud/aws/fleet.py down"
