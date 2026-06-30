from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    sender: str
    receiver: str
    event_type: str
    message: str
    timestamp: datetime = datetime.now()