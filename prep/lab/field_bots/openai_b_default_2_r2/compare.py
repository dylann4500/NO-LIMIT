"""Run the supplied field-kit entry point with a frozen SDK bot as a rival.
Only field_kit/play.py is loaded; no simulator source is read or imported here.
"""
import importlib.util
import os
import sys
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.abspath(os.path.join(HERE,'../../..'))
spec=importlib.util.spec_from_file_location('field_play',os.path.join(ROOT,'lab/field_kit/play.py'))
play=importlib.util.module_from_spec(spec)
spec.loader.exec_module(play)
spec=importlib.util.spec_from_file_location('reference',os.path.join(HERE,os.environ.get('POKER_REFERENCE','baseline_v1.py')))
reference=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
play.EXAMPLES['v1']=lambda:play.Plat([reference.Agent(),reference.Agent()])
from rivals import Tight,Balanced,Loose
for name,cls in [('tight',Tight),('balanced',Balanced),('loose',Loose)]:
    play.EXAMPLES[name]=lambda cls=cls:play.Plat([cls(),cls()])
play.main()
