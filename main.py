from core.company import Company
from core.agent import Agent
from core.event import Event
from core.event_bus import EventBus

company = Company()
bus = EventBus()

alex = Agent("Alexander", "Executive AI")
emily = Agent("Emily", "UI Director")
david = Agent("David", "Backend Architect")

company.hire(alex)
company.hire(emily)
company.hire(david)

bus.publish(
    Event(
        sender="Alexander",
        receiver="Emily",
        event_type="TASK",
        message="Create dashboard design"
    )
)

bus.publish(
    Event(
        sender="Alexander",
        receiver="David",
        event_type="TASK",
        message="Prepare backend architecture"
    )
)

company.list_agents()

print("\nEvent History\n")

for event in bus.history():
    print(
        f"{event.sender} -> {event.receiver} : {event.message}"
    )