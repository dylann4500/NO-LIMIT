"""Run the kit's play.py driver with baseline SDK agents registered as opponents.

Only play.py is executed; no simulator implementation is read or imported here.
The driver's existing SDK adapter handles both submitted agents.
"""
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
kit=runpy.run_path(str(ROOT/'lab/field_kit/play.py'))
old=kit['load_agent'](str(ROOT/'lab/field_bots/openai_a_default_2'),'round1_baseline')
kit['main'].__globals__['EXAMPLES']['baseline']=lambda:kit['Plat']([old(),old()])

class Pressure(old):
    """Synthetic continuation-bet/probe opponent, for sensitivity checks only."""
    def decide(self,s,d,started):
        result=super().decide(s,d,started)
        if result[0]=='check' and s.board and s.to_call==0:
            raises=[a for a in s.legal_actions if a.kind.value=='raise']
            active=[p for p in s.seats if p.status=='active' and p.seat!=s.seat]
            street=len(s.board)-2
            rnd=((s.hand_number*7919+s.seat*193+street*4117)%1009)/1009
            if raises and active and rnd<(.62,.46,.34)[street-1]:
                me=next(p for p in s.seats if p.seat==s.seat)
                return 'raise',me.bet+max(s.blinds[1],int(s.pot*.55))
        return result

kit['main'].__globals__['EXAMPLES']['pressure']=lambda:kit['Plat']([Pressure(),Pressure()])
kit['main']()
