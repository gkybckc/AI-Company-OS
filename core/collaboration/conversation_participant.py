"""
ConversationParticipant — membership record for one agent in a Conversation.

Intentionally decoupled from core.discussion_participant so each system
can evolve independently. No FastAPI, no networking, no async.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class ConversationParticipant:
    """
    Represents one agent admitted to a Conversation.

    Attributes:
        participant_id: Unique identifier (e.g. employee ID or role slug).
        name: Display name (e.g. "Alice Chen").
        role: Organisational role at time of joining (e.g. "Backend Agent").
        department: Optional department name.
        joined_at: UTC timestamp set by CollaborationHub on join().
    """

    participant_id: str
    name: str
    role: str
    department: str = ""
    joined_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def initials(self) -> str:
        """Return up to two uppercase initials for avatar display."""
        parts = self.name.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return self.name[:2].upper() if self.name else "??"

    def display_label(self) -> str:
        """Return 'Name (Role)' for UI display."""
        return f"{self.name} ({self.role})"

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "participant_id": self.participant_id,
            "name": self.name,
            "role": self.role,
            "department": self.department,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "initials": self.initials(),
        }
