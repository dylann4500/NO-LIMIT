"""Run the PUBLIC kit runner with its seat-loading branch extended for the original.
No private simulator source is read. Only the public play.py is copied and run.
The official upload/default tests separately invoke the unchanged kit directly.
"""
import argparse,subprocess,sys,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tables',type=int,default=400);p.add_argument('--seed',type=int,default=9127);args=p.parse_args()
here=Path(__file__).resolve().parent;kit=here.parents[1]/'field_kit'
src=(kit/'play.py').read_text()
replacements={
 'HERE = os.path.dirname(os.path.abspath(__file__))':'HERE = '+repr(str(kit)),
 'pool = [Agent(), Agent()]':'pool = [Agent(), Agent()]\n    Old = load_agent('+repr(str(here.parent/'openai_b_gto_3'))+', "round1_agent")\n    old_pool = [Old(), Old()]',
 'EXAMPLES[k]() for k in order':'Plat(old_pool) if k == "old" else EXAMPLES[k]() for k in order',
}
for old,new in replacements.items():
 assert src.count(old)==1,old
 src=src.replace(old,new)
with tempfile.TemporaryDirectory(prefix='gto3-public-comparison-') as temp:
 runner=Path(temp)/'play.py';runner.write_text(src)
 subprocess.run([sys.executable,str(runner),str(here),'--tables',str(args.tables),'--seed',str(args.seed),'--seats','self,self,self,self,old,old,old,old'],check=True)
