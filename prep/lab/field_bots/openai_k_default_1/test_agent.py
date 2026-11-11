"""Contract, numerical and adversarial tests using only the public fake SDK."""
import itertools
import gc
import os
import pickle
import random
import statistics
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "fake_sdk"))
import agent
from poker_agent_sdk import ActionKind, Config, Event, LegalAction, Seat, State


def make_state(cards=("As", "Ad"), board=(), n=8, hero=2, stack=2000,
               call=20, minimum=40, maximum=None, events=None):
    maximum = stack if maximum is None else maximum
    seats = [Seat(s, stack if s == hero else 2000, 0, "active") for s in range(n)]
    villain = (hero + 1) % n
    seats[villain].bet = call
    legal = [LegalAction(ActionKind.FOLD), LegalAction(ActionKind.CALL)] if call else [LegalAction(ActionKind.CHECK)]
    if maximum:
        legal.append(LegalAction(ActionKind.RAISE, min(minimum, maximum), maximum))
    if events is None:
        events = [Event("hand", amount=1), Event("blind", 0, 10), Event("blind", 1, 20)]
        if board:
            events.append(Event("board", cards=list(board[:3])))
            for c in board[3:]:
                events.append(Event("board", cards=[c]))
        if call:
            events.append(Event("raise", villain, call))
    return State(seat=hero, cards=list(cards), board=list(board), pot=max(30, call + 30),
                 to_call=call, legal_actions=legal, history=events, seats=seats, button=n - 1,
                 blind_level=1, blinds=[10, 20], hands_until_next_level=20, hand_number=1,
                 players_remaining=n, bust_order=[], config=Config(payouts=[50, 30, 20, 0, 0, 0, 0, 0],
                 memory_bytes=65536, decision_ms=1, time_bank_ms=100, hand_cap=250),
                 events=events, time_bank_ms=100)


class Contracts(unittest.TestCase):
    def assert_legal(self, state, action):
        offered = {a.kind: a for a in state.legal_actions}
        self.assertIn(action.kind, offered)
        if action.kind == ActionKind.RAISE:
            a = offered[action.kind]
            self.assertIsInstance(action.amount, int)
            self.assertLessEqual(a.min_amount, action.amount)
            self.assertLessEqual(action.amount, a.max_amount)

    def test_premiums_and_free_checks(self):
        s = make_state()
        a, m = agent.Agent().act(s, b"")
        self.assertEqual(a.kind, ActionKind.RAISE)
        self.assert_legal(s, a)
        s = make_state(cards=("7s", "2c"), call=0, maximum=0)
        a, _ = agent.Agent().act(s, b"")
        self.assertEqual(a.kind, ActionKind.CHECK)

    def test_short_all_in_raise_bounds(self):
        for amount in (1, 7, 19, 21, 39, 41, 2011):
            s = make_state(stack=amount, minimum=amount, maximum=amount)
            a, _ = agent.Agent().act(s, b"")
            self.assert_legal(s, a)

    def test_shared_nuts_never_fold(self):
        for board in (("As", "Ks", "Qs", "Js", "Ts"),
                      ("As", "Kd", "Qc", "Jh", "Tc"),
                      ("Ah", "As", "Ad", "Ac", "Kh"),
                      ("Kh", "Ks", "Kd", "Kc", "Ah")):
            s = make_state(cards=("7c", "2d"), board=board, stack=100, call=1000, maximum=0)
            self.assertTrue(agent._locked_board(board))
            a, _ = agent.Agent().act(s, b"")
            self.assertEqual(a.kind, ActionKind.CALL)
        self.assertFalse(agent._locked_board(("As", "Kd", "Qc", "Jc", "Tc")))
        self.assertFalse(agent._locked_board(("9h", "9s", "9d", "9c", "Kh")))

    def test_memory_is_table_local_and_replay_safe(self):
        s = make_state()
        a, first = agent.Agent().act(s, b"")
        # Another table, handled by a different copy in the shared pool.
        agent.Agent().act(make_state(cards=("2c", "7d"), n=2, hero=0), b"")
        s.events = [Event("call", 4, 40), Event("board", cards=["Ah", "5c", "8d"])]
        s.board = ["Ah", "5c", "8d"]
        s.to_call = 0
        s.legal_actions = [LegalAction(ActionKind.CHECK), LegalAction(ActionKind.RAISE, 20, 1960)]
        _, second = agent.Agent().act(s, first)
        _, replayed = agent.Agent().act(s, first)
        self.assertEqual(pickle.loads(second), pickle.loads(replayed))
        self.assertLess(len(second), 16000)

    def test_inaccessible_side_pot_is_excluded(self):
        s = make_state(stack=50, call=500)
        s.pot = 1010
        m = {"h": {"invest": {2: 10, 0: 500, 1: 500}}}
        self.assertEqual(agent._eligible_pot(s, m, s.seats[2], 50), 130)

    def test_multiway_elimination_risk_and_side_pot_icm(self):
        s = make_state(stack=2000, call=2000, maximum=0)
        for seat in s.seats:
            if seat.seat != s.seat:
                seat.stack, seat.bet, seat.status = 0, 2000, 'all_in'
        s.pot = 14000
        # Folding locks a top-two finish when seven equal stacks clash.
        self.assertGreater(agent._call_threshold(s, s.seats[2], s.seats[3], 2000, 14000), .64)
        s.seats[2].stack = 200
        # Winning only the main pot cannot award the inaccessible side pot.
        self.assertGreater(agent._call_threshold(s, s.seats[2], s.seats[3], 200, 1400), .90)
        self.assertAlmostEqual(agent._icm({i: 2000 for i in range(8)}, 0, [50, 30, 20]), 12.5)

    def test_gc_setting_is_restored(self):
        initial = gc.isenabled()
        try:
            for enabled in (True, False):
                gc.enable() if enabled else gc.disable()
                agent.Agent().act(make_state(), b'')
                self.assertEqual(gc.isenabled(), enabled)
        finally:
            gc.enable() if initial else gc.disable()

    def test_reraise_range_is_tighter_than_open(self):
        events = [Event("hand", amount=1), Event("blind", 0, 10), Event("blind", 1, 20),
                  Event("raise", 2, 45), Event("raise", 3, 140), Event("raise", 4, 400)]
        s = make_state(hero=5, events=events)
        m = agent._memory(s, b"")
        opened = agent._prior_fraction(2, m)
        threebet = agent._prior_fraction(3, m)
        fourbet = agent._prior_fraction(4, m)
        self.assertLess(fourbet, threebet)
        self.assertLess(threebet, opened * .5)
        self.assertLess(fourbet, .05)

    def test_wide_opening_is_not_constant_raising(self):
        st = [0] * 15
        st[0], st[1], st[2], st[14] = 100, 80, 70, 70
        st[4], st[6] = 20, 10
        self.assertFalse(agent._profile(st)[4])
        st[14] = 200
        self.assertTrue(agent._profile(st)[4])

    def test_icm_against_permutations(self):
        rng = random.Random(84)
        for n in range(2, 6):
            for _ in range(15):
                stacks = {i: rng.randint(1, 5000) for i in range(n)}
                payouts = random.Random(n + _).choice(([50, 30, 20, 0, 0], [100, 0, 0, 0, 0], [40, 25, 20, 10, 5]))[:n]
                expected = 0.0
                for order in itertools.permutations(stacks):
                    probability, total = 1.0, sum(stacks.values())
                    for sid in order:
                        probability *= stacks[sid] / total
                        total -= stacks[sid]
                    expected += probability * payouts[order.index(0)]
                self.assertAlmostEqual(agent._icm(stacks, 0, payouts), expected, places=9)

    def test_draw_lookup(self):
        rng = random.Random(912)
        windows = [31 << i for i in range(9)] + [0x100F]
        for _ in range(3000):
            board = rng.sample(range(13), rng.randint(1, 4))
            mask = sum(1 << r for r in board)
            a, b = rng.randrange(13), rng.randrange(13)
            whole = mask | (1 << a) | (1 << b)
            slow = any((mask & w).bit_count() < 4 and (whole & w).bit_count() == 4 for w in windows)
            self.assertEqual(bool(agent._STRAIGHT_DRAWS[mask * 169 + a * 13 + b]), slow)

    def test_multiple_streets_and_large_pots(self):
        cpu = []
        examples = [(('As', 'Kh'), ('Ah', '9h', '7s', '2c', '4d')),
                    (('9s', '9d'), ('Ah', '9h', '7s', '2c', '4d')),
                    (('Jh', 'Th'), ('Ah', '9h', '7s', '2c')),
                    (('Ac', 'Ad'), ('Ah', '9h', '7s', '9c', '2d'))]
        for cards, board in examples:
            for bank in (100, 64, 0):
                for _ in range(30):
                    events = [Event('hand', amount=1), Event('blind', 0, 10), Event('blind', 1, 20),
                              Event('raise', 2, 45), Event('call', 3, 45), Event('call', 4, 45),
                              Event('board', cards=list(board[:3])), Event('raise', 3, 100),
                              Event('call', 4, 100), Event('call', 2, 100)]
                    for card in board[3:]:
                        events += [Event('board', cards=[card]), Event('raise', 3, 250),
                                   Event('call', 4, 250), Event('call', 2, 250)]
                    events.append(Event('raise', 3, 600))
                    s = make_state(cards=cards, board=board, n=5, call=350, minimum=950, events=events)
                    s.pot = 2500
                    s.time_bank_ms = bank
                    for seat in s.seats:
                        if seat.seat in (0, 1):
                            seat.status = 'folded'
                    start = time.thread_time_ns()
                    a, _ = agent.Agent().act(s, b'')
                    cpu.append((time.thread_time_ns() - start) / 1000)
                    self.assert_legal(s, a)
        cpu.sort()
        print('\n360 multi-street decisions:', {'cpu_us_p50': round(statistics.median(cpu), 1),
              'cpu_us_p99': round(cpu[int(len(cpu) * .99)], 1), 'cpu_us_max': round(max(cpu), 1),
              'max_cpu_at_2_5x_ms': round(max(cpu) * 2.5 / 1000, 3)})

    def test_randomized_legal_states(self):
        rng = random.Random(3781)
        deck = list(agent._CARDS)
        cpu, wall = [], []
        maximum_memory = 0
        for i in range(2500):
            n = rng.randint(2, 8)
            hero = rng.randrange(n)
            length = rng.choice((0, 0, 0, 3, 4, 5))
            cc = rng.sample(deck, 2 + length)
            stack = rng.choice((1, 7, 19, 45, 150, 500, 2000, 8000))
            cost = rng.choice((0, 0, 20, 40, 100, 1000, stack))
            maximum = rng.choice((0, stack, stack))
            s = make_state(cc[:2], cc[2:], n=n, hero=hero, stack=stack,
                           call=cost, minimum=rng.randint(1, max(1, stack)), maximum=maximum)
            # Folds, prior actions and all-in seats broaden state coverage.
            for seat in s.seats:
                if seat.seat != hero and seat.bet == 0:
                    seat.status = rng.choice(("active", "folded", "all_in"))
                    if seat.status == "all_in":
                        seat.stack = 0
            s.time_bank_ms = rng.choice((0, 5, 30, 100))
            c, w = time.thread_time_ns(), time.perf_counter_ns()
            action, memory = agent.Agent().act(s, b"")
            wall.append((time.perf_counter_ns() - w) / 1000)
            cpu.append((time.thread_time_ns() - c) / 1000)
            maximum_memory = max(maximum_memory, len(memory))
            self.assert_legal(s, action)
            self.assertIsInstance(memory, bytes)
        cpu.sort()
        wall.sort()
        print("\n2500 randomized decisions:", {"cpu_us_p50": round(statistics.median(cpu), 1),
              "cpu_us_p99": round(cpu[int(.99 * len(cpu))], 1), "cpu_us_max": round(max(cpu), 1),
              "wall_us_p99": round(wall[int(.99 * len(wall))], 1),
              "memory_bytes_max": maximum_memory})


if __name__ == "__main__":
    unittest.main()
