from core.event import Event


class EventBus:

    def __init__(self):
        self.events = []

    def publish(self, event: Event):
        self.events.append(event)

    def dispatch(self, agents):

        for event in self.events:

            for agent in agents:

                if agent.name == event.receiver:
                    agent.receive_message(event.message)

    def history(self):
        return self.events

    def clear(self):
        self.events.clear()