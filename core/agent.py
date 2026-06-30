from dataclasses import dataclass, field
from typing import List


@dataclass
class Agent:
    name: str
    role: str
    status: str = "Idle"
    current_task: str = ""
    inbox: List[str] = field(default_factory=list)

    def assign_task(self, task: str):
        self.current_task = task
        self.status = "Working"

    def receive_message(self, message: str):
        self.inbox.append(message)

    def read_messages(self):
        return self.inbox

    def clear_messages(self):
        self.inbox.clear()

    def finish_task(self):
        self.current_task = ""
        self.status = "Idle"

    def info(self):
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "task": self.current_task,
        }