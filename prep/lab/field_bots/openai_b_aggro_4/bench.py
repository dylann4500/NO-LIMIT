"""Extra opponents and workload scaling through the published field-kit runner.

Examples, from the repo root:
  python lab/field_bots/openai_b_aggro_4/bench.py --tables 100 --workload 3
  python lab/field_bots/openai_b_aggro_4/bench.py --tables 300 --seats self,self,rock,rock,station,station,nit,nit

The runtime agent does not import this file. Simulator sources are never opened.
"""
import argparse
import pathlib
import sys

folder=pathlib.Path(__file__).resolve().parent
kit=folder.parents[1]/'field_kit'
sys.path.insert(0,str(kit))
import play
from test_opponents import Rock,Station,Nit

parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--workload',type=int,default=1)
args,rest=parser.parse_known_args()
if args.workload<1:raise SystemExit('--workload must be >= 1')
play.EXAMPLES.update({name:(lambda cls=cls:play.Plat([cls(),cls()])) for name,cls in [('rock',Rock),('station',Station),('nit',Nit)]})
if args.workload>1:
 original=play.load_agent
 def load(*pos,**kw):
  base=original(*pos,**kw)
  class Repeated(base):
   def act(self,state,memory):
    result=base.act(self,state,memory)
    for _ in range(args.workload-1):base.act(self,state,memory)
    return result
  return Repeated
 play.load_agent=load
sys.argv=[str(kit/'play.py'),str(folder),*rest]
play.main()
