"""Minute-10 bot for Bay Area (3 hole cards, discard one + expose one at the flop).

Built on the kit template. Stateless: everything per-table lives in `memory`.
- select: keep the best 2 of 3 on this flop (made hand, draw, high cards); expose the
  kept card that leaks least.
- preflop: play hands where some 2 of the 3 are a pair 66+, two cards >= T, or a suited ace.
- postflop: bet 2/3 pot / call with top pair or better, otherwise check or fold.
"""

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import json
from itertools import combinations

import eval7
import poker_agent_sdk
from poker_agent_sdk import Action, GameState

RANKS = "23456789TJQKA"
RANK = {r: i for i, r in enumerate(RANKS)}  # 2 -> 0 ... A -> 12
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in "shdc"}

# (discard, keep_a, keep_b) for each discard index.
KEEP = ((0, 1, 2), (1, 0, 2), (2, 0, 1))

# Warm eval7 at import.
eval7.evaluate([CARD[c] for c in ("As", "Kd", "Qc", "2d", "7h")])


class Agent(poker_agent_sdk.Agent):
    def act(self, state: GameState, memory: bytes) -> tuple[Action, bytes]:
        mem = _load(memory)
        try:
            for event in state.events:
                if event.kind == "raise" and event.seat is not None and event.seat != state.seat:
                    k = str(event.seat)
                    mem[k] = int(mem.get(k, 0)) + 1
        except Exception:
            mem = {}
        try:
            action = decide(state)
        except Exception:
            action = _fallback(state)
        try:
            out = json.dumps(mem, separators=(",", ":")).encode()
            if len(out) > 8000:
                out = b""
        except Exception:
            out = b""
        return action, out


def _load(memory: bytes) -> dict:
    try:
        d = json.loads(memory) if memory else {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _fallback(state: GameState) -> Action:
    try:
        if state.phase == "select":
            return Action("select", cards=(2, 0))
        if state.can("check"):
            return Action.check()
        if state.can("fold"):
            return Action.fold()
        first = state.legal_actions[0]
        return Action(first.kind, int(first.min_amount))
    except Exception:
        return Action("select", cards=(2, 0)) if getattr(state, "phase", "") == "select" else Action.fold()


# ---------------------------------------------------------------- hand evaluation

def _draw_value(cards: list[str]) -> float:
    """Flush draw = 2, open-ended = 1.5, gutshot = 0.5 (only if not already made)."""
    val = 0.0
    suits: dict[str, int] = {}
    for c in cards:
        suits[c[1]] = suits.get(c[1], 0) + 1
    if max(suits.values()) == 4:
        val += 2.0
    ranks = {RANK[c[0]] for c in cards}
    if 12 in ranks:
        ranks.add(-1)
    if _has_straight(ranks):
        return val
    outs = 0
    for r in range(-1, 13):
        if r not in ranks and _has_straight(ranks | {r}):
            outs += 1
    if outs >= 2:
        val += 1.5
    elif outs == 1:
        val += 0.5
    return val


def _has_straight(ranks: set[int]) -> bool:
    for lo in range(-1, 9):
        if all(r in ranks for r in range(lo, lo + 5)):
            return True
    return False


def _score_keep(keep: tuple[str, str], board: tuple[str, ...]) -> tuple:
    cards = list(keep) + list(board)
    v = eval7.evaluate([CARD[c] for c in cards])
    draw = _draw_value(cards) if len(board) < 5 else 0.0
    highs = sorted((RANK[keep[0][0]], RANK[keep[1][0]]), reverse=True)
    return (v >> 24, draw, v, highs[0], highs[1])


def _expose_choice(keep: tuple[str, str], board: tuple[str, ...]) -> int:
    """Return 0 or 1: which kept card to expose (the one that gives away least)."""
    a, b = keep
    board_ranks = {c[0] for c in board}
    pa, pb = a[0] in board_ranks, b[0] in board_ranks
    if pa != pb:
        return 1 if pa else 0  # expose the one NOT pairing the board
    suits: dict[str, int] = {}
    for c in list(keep) + list(board):
        suits[c[1]] = suits.get(c[1], 0) + 1
    fa, fb = suits[a[1]] >= 4, suits[b[1]] >= 4
    if fa != fb:
        return 1 if fa else 0  # expose the one NOT in the flush draw
    return 0 if RANK[a[0]] <= RANK[b[0]] else 1  # expose the lower card


def select_action(state: GameState) -> Action:
    cards = tuple(state.cards)
    board = tuple(state.board)
    if len(cards) != 3 or len(set(cards)) != 3 or any(c not in CARD for c in cards + board):
        return Action("select", cards=(2, 0))
    best = None
    for d, i, j in KEEP:
        keep = (cards[i], cards[j])
        s = _score_keep(keep, board)
        if best is None or s > best[0]:
            best = (s, d, i, j)
    _, d, i, j = best
    expose = (i, j)[_expose_choice((cards[i], cards[j]), board)]
    return Action("select", cards=(int(d), int(expose)))


def _preflop_playable(cards: tuple[str, ...]) -> tuple[bool, bool]:
    """(playable, premium) over all 2-card subsets."""
    playable = premium = False
    for a, b in combinations(cards, 2):
        ra, rb = RANK[a[0]], RANK[b[0]]
        hi, lo = max(ra, rb), min(ra, rb)
        suited = a[1] == b[1]
        if ra == rb and ra >= RANK["6"]:
            playable = True
            if ra >= RANK["T"]:
                premium = True
        if lo >= RANK["T"]:
            playable = True
            if hi == 12 and lo >= RANK["K"]:
                premium = True
        if suited and hi == 12:
            playable = True
    return playable, premium


def _top_pair_or_better(cards: tuple[str, ...], board: tuple[str, ...]) -> bool:
    if len(board) < 3:
        return False
    v = eval7.evaluate([CARD[c] for c in cards + board])
    cat = v >> 24
    board_cat = eval7.evaluate([CARD[c] for c in board]) >> 24 if len(board) >= 5 else _board_cat(board)
    if cat <= board_cat:
        return False  # hole cards add nothing to the board's category
    if cat >= 2:
        return True
    # One pair made with a hole card: must be >= highest board rank.
    hole_ranks = [RANK[c[0]] for c in cards]
    board_ranks = [RANK[c[0]] for c in board]
    top = max(board_ranks)
    if len(hole_ranks) == 2 and hole_ranks[0] == hole_ranks[1]:
        return hole_ranks[0] > top
    for r in hole_ranks:
        if r in board_ranks and r == top:
            return True
    return False


def _board_cat(board: tuple[str, ...]) -> int:
    counts: dict[str, int] = {}
    for c in board:
        counts[c[0]] = counts.get(c[0], 0) + 1
    m = max(counts.values())
    pairs = sum(1 for n in counts.values() if n >= 2)
    if m >= 4:
        return 7
    if m == 3:
        return 3
    if pairs >= 2:
        return 2
    if pairs == 1:
        return 1
    return 0


def _me(state: GameState):
    for s in state.seats:
        if s.seat == state.seat:
            return s
    return None


def _shove_or_call(state: GameState) -> Action:
    r = state.can("raise")
    if r:
        return Action.raise_to(int(r.max_amount))
    if state.can("call"):
        return Action.call()
    return Action.check() if state.can("check") else Action.fold()


def _check_fold(state: GameState) -> Action:
    if state.can("check"):
        return Action.check()
    return Action.fold() if state.can("fold") else _fallback(state)


def decide(state: GameState) -> Action:
    if state.phase == "select":
        try:
            return select_action(state)
        except Exception:
            return Action("select", cards=(2, 0))
    if state.phase != "betting":
        first = state.legal_actions[0]
        return Action(first.kind, int(first.min_amount))

    cards = tuple(state.cards)
    board = tuple(state.board)
    bb = max(1, int(state.blinds.big_blind))
    me = _me(state)
    my_stack = int(me.stack) if me else 0
    my_bet = int(me.bet) if me else 0
    eff_bb = (my_stack + my_bet) / bb
    to_call = int(state.to_call)

    if not board:  # preflop
        playable, premium = _preflop_playable(cards)
        if not playable:
            return _check_fold(state)
        if eff_bb <= 10:
            return _shove_or_call(state)
        r = state.can("raise")
        unopened = to_call <= bb - my_bet or to_call == 0
        if unopened:
            if r:
                target = max(int(r.min_amount), int(2.5 * bb))
                return Action.raise_to(min(int(r.max_amount), target))
            return Action.call() if state.can("call") else Action.check()
        # Facing a raise.
        if premium:
            if r and to_call < my_stack * 0.35:
                target = max(int(r.min_amount), int(3 * (my_bet + to_call)))
                return Action.raise_to(min(int(r.max_amount), target))
            return Action.call() if state.can("call") else _check_fold(state)
        if to_call <= max(3 * bb, int(my_stack * 0.08)) and state.can("call"):
            return Action.call()
        return _check_fold(state)

    # Postflop.
    if _top_pair_or_better(cards, board):
        r = state.can("raise")
        if to_call == 0 and r:
            target = max(int(r.min_amount), int(state.pot * 2 // 3))
            return Action.raise_to(min(int(r.max_amount), target))
        if state.can("call"):
            return Action.call()
        return Action.check() if state.can("check") else _fallback(state)
    return _check_fold(state)
