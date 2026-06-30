from core.agent import Agent


class Company:

    def __init__(self):
        self.agents = []

    def hire(self, agent: Agent):
        self.agents.append(agent)

    def list_agents(self):
        for agent in self.agents:
            print(
                f"{agent.name} | {agent.role} | {agent.status}"
            )

    def get_agents(self):
        return self.agents