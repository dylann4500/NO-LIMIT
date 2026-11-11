"""Protocol, state portability, edge-case, and latency tests. No simulator internals."""
import collections
import json
import itertools
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'fake_sdk'))
import agent
from poker_agent_sdk import ActionKind, Config, Event, LegalAction, Seat, State


def check_icm():
    rng = random.Random(71)
    checks = 0
    for n in range(2, 9):
        for trial in range(40):
            stacks = [rng.randint(1, 10000) for _ in range(n)]
            total = sum(stacks)
            prizes = [50,30,20] if trial % 2 else [70,30,0]
            exact = 0.
            for order in itertools.permutations(range(n), min(3,n)):
                if 0 not in order:
                    continue
                p, remaining = 1., total
                for seat in order:
                    p *= stacks[seat] / remaining
                    remaining -= stacks[seat]
                exact += p * prizes[order.index(0)]
            got = agent.icm_value(stacks[0], stacks[1:], prizes)
            assert abs(got-exact) < 1e-8, (stacks, got, exact)
            checks += 1
    assert agent.icm_value(0,[100,200],[50,30,20]) == 20
    assert agent.icm_value(0,[100,200,300],[50,30,20]) == 0
    return checks


def check_seat_order():
    checks = 0
    for n in range(2, 9):
        for live in itertools.combinations(range(8), n):
            for b in live:
                seats = [Seat(i,100 if i in live else 0,0,'active' if i in live else 'busted') for i in range(8)]
                p = live.index(b)
                start = 0 if n == 2 else 3
                expected = [live[(p+start+i)%n] for i in range(n)]
                assert agent.preflop_order(seats, b) == expected, (live,b,expected)
                checks += 1
    return checks


def check_position_ranges():
    prof = (.30,.18,.30,False,False)
    early = [[0,0,'r',40]]
    button = [[0,i,'f',0] for i in range(5)] + [[0,5,'r',40]]
    small_blind = [[0,i,'f',0] for i in range(6)] + [[0,6,'r',40]]
    a = agent.Agent.pre_range(0,prof,early,20,2000,8)
    b = agent.Agent.pre_range(5,prof,button,20,2000,8)
    c = agent.Agent.pre_range(6,prof,small_blind,20,2000,8)
    d = agent.Agent.pre_range(0,prof,early,20,2000,2)
    assert a < b < c < d, (a,b,c,d)
    assert abs(a-.15)<1e-8 and abs(b-.37)<1e-8 and abs(c-.50)<1e-8
    return 4


def check_sidepots():
    seats = [Seat(0,900,0,'active'), Seat(1,900,0,'active'), Seat(2,0,0,'all_in'), Seat(3,40,0,'folded')]
    mem = {'p': {str(i): [0]*10+[start] for i,start in enumerate([1000,1000,10,50])}}
    state = State(seats=seats, pot=220)
    got, pot = agent.equity_layers(state, mem, seats[0], seats[1:3], 0, .7)
    assert pot == 220
    assert abs(got - (40*.7**(2**.78)+180*.7)/220) < 1e-10
    seats[1].stack = 0
    seats[1].status = 'all_in'
    state.pot = 1120
    got, pot = agent.equity_layers(state, mem, seats[0], seats[1:3], 50, .7)
    assert pot == 270
    assert abs(got - (40*.7**(2**.78)+280*.7)/320) < 1e-10
    return 2


def check_simultaneous_busts():
    seats = [Seat(0,2000,0,'active')] + [Seat(i,0,2000,'all_in') for i in range(1,8)]
    state = State(seats=seats, config=Config(payouts=[50,30,20,0,0,0,0,0]), players_remaining=8)
    mem = {'p': {str(i): [0]*10+[2000] for i in range(8)}}
    got = agent.call_requirement(state,seats[0],seats[1:],seats[1],14000,2000,mem)
    expected = (32.5 - 50/7)/(50 - 50/7)
    assert abs(got-expected)<1e-8, (got,expected)
    # A larger starting stack places above the simultaneous busts.
    mem['p']['0'][10] = 2100
    got = agent.call_requirement(state,seats[0],seats[1:],seats[1],14000,2000,mem)
    assert abs(got-.125)<1e-8, got
    return 2


def run(n=12000):
    icm_checks = check_icm()
    sidepot_checks = check_sidepots()
    bust_checks = check_simultaneous_busts()
    seat_checks = check_seat_order()
    position_checks = check_position_ranges()
    rng = random.Random(15901)
    deck = list(agent.CARDS)
    times, cpu_times, actions = [], [], collections.Counter()
    max_mem = 0
    for i in range(n):
        count = rng.randint(2, 8)
        hero = rng.randrange(count)
        villain = (hero + 1) % count
        street = (0, 3, 4, 5)[i % 4]
        dealt = rng.sample(deck, street + 2)
        stack = rng.randint(1, 15000)
        bb = rng.choice((20, 50, 100, 300, 1000))
        bet = rng.choice((0, bb, 2*bb))
        cost = rng.choice((0, 0, min(stack, bb), min(stack, 3*bb), stack))
        seats = [Seat(s, rng.randint(0, 15000), bet, 'active') for s in range(count)]
        seats[hero].stack = stack
        seats[villain].bet = bet + cost
        if i % 9 == 0:
            seats[villain].stack = 0
            seats[villain].status = 'all_in'
        for s in seats:
            if s.seat not in (hero, villain) and rng.random() < .5:
                s.status = 'folded'
        legal = [LegalAction(ActionKind.CHECK)] if not cost else [LegalAction(ActionKind.FOLD), LegalAction(ActionKind.CALL)]
        if rng.random() < .7 and stack > cost:
            low = min(bet + stack, bet + cost + bb)
            legal.append(LegalAction(ActionKind.RAISE, low, bet + stack))
        # Protocol robustness includes single-kind offers, not just typical poker menus.
        if i % 97 == 0 and stack > cost:
            legal = [LegalAction(ActionKind.RAISE, bet+cost+1, bet+stack)]
        elif i % 101 == 0:
            legal = [LegalAction(ActionKind.CALL)]
        elif i % 103 == 0:
            legal = [LegalAction(ActionKind.CHECK)]
        evs = [Event('hand', amount=1)]
        if i % 3:
            evs.append(Event('raise', seat=villain, amount=2*bb))
            evs.append(Event('call', seat=hero, amount=bb))
        if street:
            evs.append(Event('board', cards=dealt[2:5]))
            if street > 3:
                evs.extend([Event('raise', seat=hero, amount=bb), Event('call', seat=villain, amount=bb), Event('board', cards=dealt[5:6])])
            if street > 4:
                evs.append(Event('board', cards=dealt[6:7]))
            if cost:
                evs.append(Event('raise', seat=villain, amount=bet+cost))
        config = Config(starting_stack=2000, payouts=rng.choice(([50,30,20,0,0,0,0,0], [100,0,0,0,0,0,0,0], [70,30,0,0,0,0,0,0])),
                        decision_ms=1, time_bank_ms=100, memory_bytes=65536, players=count)
        state = State(seat=hero, cards=dealt[:2], board=dealt[2:], pot=max(1, rng.randint(1,12000)+cost), to_call=cost,
                      legal_actions=legal, history=evs, phase='betting', seats=seats, button=rng.randrange(count),
                      blind_level=0, blinds=[bb//2,bb], hands_until_next_level=10, hand_number=1,
                      players_remaining=count, bust_order=[], config=config, time_bank_ms=0 if i % 7 == 0 else 100, events=evs)
        t = time.perf_counter_ns()
        c = time.thread_time_ns()
        action, memory = agent.Agent().act(state, b'')
        cpu_times.append(time.thread_time_ns() - c)
        times.append(time.perf_counter_ns() - t)
        offered = {a.kind: a for a in legal}
        assert action.kind in offered, (i, action, legal)
        if action.kind == ActionKind.RAISE:
            assert isinstance(action.amount, int)
            assert offered[action.kind].min_amount <= action.amount <= offered[action.kind].max_amount
        assert isinstance(memory, bytes) and len(memory) < 16000
        max_mem = max(max_mem, len(memory))
        decoded = json.loads(memory)
        assert decoded['b'] == street, decoded
        if i % 200 == 0:
            # A fresh process copy gets all reads from the bytes alone.
            _, replay = agent.Agent().act(state, b'')
            assert replay == memory
            state.events = []
            _, next_memory = agent.Agent().act(state, memory)
            assert json.loads(next_memory)['p'] == decoded['p']
            # SDK memory limits may truncate an old upload's bytes mid-JSON.
            recovered, _ = agent.Agent().act(state, memory[:20])
            assert recovered.kind in offered
        actions[action.kind.value] += 1
    times.sort(); cpu_times.sort()
    def quantile(v, p): return round(v[min(len(v)-1,int(len(v)*p))] / 1000, 1)
    print(json.dumps({'decisions': n, 'legal_failures': 0, 'icm_checks': icm_checks, 'sidepot_checks': sidepot_checks, 'bust_order_checks': bust_checks, 'seat_order_checks': seat_checks, 'position_range_checks': position_checks, 'actions': actions, 'memory_max': max_mem,
                      'wall_us': {'p50': quantile(times,.5), 'p99': quantile(times,.99), 'p999': quantile(times,.999), 'max': quantile(times,1)},
                      'cpu_us': {'p50': quantile(cpu_times,.5), 'p99': quantile(cpu_times,.99), 'p999': quantile(cpu_times,.999), 'max': quantile(cpu_times,1)},
                      'cpu_over_1ms_at_2_5x': sum(t*2.5 > 1000000 for t in cpu_times)}, indent=2))


if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv)>1 else 12000)
