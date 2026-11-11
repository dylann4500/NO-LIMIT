"""Execute the supplied play.py entry point with extra named SDK policies.

Uses only objects exposed in play.py (which is part of the readable kit).
Does not read or import simulator implementation modules.
"""
from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parent
kit=runpy.run_path(str(ROOT.parents[1]/'field_kit'/'play.py'),run_name='kit_entry')

def register(name,path):
    cls=kit['load_agent'](str(path),name='test_'+name)
    kit['EXAMPLES'][name]=lambda:kit['Plat']([cls(),cls()])
register('baseline',ROOT.parent/'openai_k_default_2')
register('v1',ROOT/'test_v1')
register('pressure',ROOT/'test_pressure')
if __name__=='__main__':
    kit['main']()
