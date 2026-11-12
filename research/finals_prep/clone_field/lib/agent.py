"""A clone of one team's observed behaviour: the generic policy in clonecore.py driven by the
parameter table params.json in this folder (fitted from a hand-history download)."""
import json
import os

import poker_agent_sdk
from poker_agent_sdk import Action

import clonecore

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "params.json")) as _f:
    _CLONE = clonecore.Clone(json.load(_f), Action)


class Agent(poker_agent_sdk.Agent):
    def act(self, state, memory):
        return _CLONE.act(state, memory)
