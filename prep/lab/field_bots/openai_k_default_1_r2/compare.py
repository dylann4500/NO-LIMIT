"""Run the public play.py entry point with additional public-SDK bot seats.

No simulator implementation is read or imported by this development script.
The kit itself supplies its usual SDK adapter and runs every match.
"""
import importlib.util, os, runpy, sys
ROOT=os.path.dirname(os.path.abspath(__file__))
kit=os.path.abspath(os.path.join(ROOT,'..','..','field_kit','play.py'))
runner=runpy.run_path(kit)
old=runner['load_agent'](os.path.join(ROOT,'..','openai_k_default_1'),'round_one_reference')
runner['EXAMPLES']['old']=lambda: runner['Plat']([old(),old()])

# A separate sensitivity opponent increases the reference's continuation bets
# and probes. Its style tests the direction seen in public field frequencies;
# it is not an implementation or reconstruction of another team's bot.
spec=importlib.util.spec_from_file_location('aggressive_reference',os.path.join(ROOT,'..','openai_k_default_1','agent.py'))
pressure=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pressure)
original_post=pressure._postflop
def pressure_post(state,m,me,opponents,legal,noise,deadline):
    action=original_post(state,m,me,opponents,legal,noise,deadline)
    if action[0]!='check' or state.to_call or 'raise' not in legal:
        return action
    live=[s for s in opponents if s.stack and pressure._kind(s.status)=='active']
    if len(opponents)!=1 or not live:
        return action
    hp=m['h']['p'].get(state.seat,pressure._new_player())
    street=len(state.board)-3
    ring=[s.seat for s in state.seats]; btn=ring.index(state.button)
    position=lambda seat:(ring.index(seat)-btn-1)%len(ring)
    in_position=all(position(state.seat)>position(s.seat) for s in live)
    features=pressure._features(state.cards,state.board)
    bet=False
    if street==0:
        bet=noise<(.90 if hp[1] else .65 if in_position else .15)
    elif street==1:
        bet=in_position and noise<.52
    else:
        bet=in_position and not features[1] and noise<.45
    if bet:
        return 'raise',int(me.bet+max(state.blinds[1],state.pot*(.6 if street<2 else .75)))
    return action
pressure._postflop=pressure_post
runner['EXAMPLES']['pressure']=lambda: runner['Plat']([pressure.Agent(),pressure.Agent()])
runner['main']()
