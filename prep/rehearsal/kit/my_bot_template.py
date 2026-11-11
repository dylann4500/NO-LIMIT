from agent import Agent


class MyAgent(Agent):
    def get_action(self, state):
        return {"action": "check"} if state["legal"]["can_check"] else {"action": "fold"}
