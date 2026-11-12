#!/bin/zsh
# build bundle/ for Modal: code + fitted parameters only (no hand histories, no acc.pkl, no calibration logs)
M=${0:A:h}; rm -rf $M/bundle; mkdir -p $M/bundle
cp $M/mrun.py $M/bundle/; rsync -a --exclude __pycache__ $M/lib $M/bundle/
for f in $@; do
  rsync -a --prune-empty-dirs --include '*/' --include 'field.json' --include 'cdf.json' --include 'adj.json' --include 'params.json' --include 'arch/*.json' --exclude 'calib_*/**' --exclude '*' $M/fields/$f $M/bundle/fields/
done
du -sh $M/bundle; find $M/bundle -name '*.pkl' -o -name '*.gz' | head
