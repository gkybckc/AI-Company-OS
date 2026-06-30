from core.event import Event


class EventBus:

    def __init__(self):
        self.events = []

    def publish(self, event: Event):
        self.events.append(event)

    def history(self):
        return self.events

    def clear(self):
        self.events.clear()