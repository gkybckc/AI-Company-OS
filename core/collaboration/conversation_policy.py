"""
ConversationPolicy — data-driven collaboration governance rules.

Policies say: "IF a participant with role X sends a message of category Y,
THEN a participant with role Z must respond with category W."

No hardcoded department logic. No AI. No networking. No async.
All policies are plain Python data objects; the PolicyEngine evaluates them
against live Conversation state.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# PolicyViolation — result of a failed policy check
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PolicyViolation:
    """
    Record of a policy that is currently unsatisfied.

    Attributes:
        policy_name: Name of the violated policy.
        description: Human-readable explanation.
        is_blocking: If True, the conversation MUST NOT be closed until resolved.
        trigger_message_id: Optional ID of the message that triggered the policy.
    """

    policy_name: str
    description: str
    is_blocking: bool
    trigger_message_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "policy_name": self.policy_name,
            "description": self.description,
            "is_blocking": self.is_blocking,
            "trigger_message_id": self.trigger_message_id,
        }


# ---------------------------------------------------------------------------
# ConversationPolicy — one data-driven rule
# ---------------------------------------------------------------------------

@dataclass
class ConversationPolicy:
    """
    One data-driven governance rule for conversations.

    Attributes:
        name: Unique policy name (slug-style, e.g. "security-review-required").
        description: Human-readable explanation of the rule.
        trigger_role: The participant role that activates this policy
            (e.g. "Backend Agent"). Empty string means ANY role.
        trigger_category: The MessageCategory value that activates this policy
            (e.g. "proposal"). Empty string means ANY category.
        required_reviewer_role: Role that must send a required_response_category
            message in response (e.g. "Security").
        required_response_category: The category the required reviewer must use
            (e.g. "review"). Empty string means ANY category.
        is_blocking: If True, violations from this policy block conversation close.
        applies_to_template: Optional template type name this policy applies to.
            Empty string or None means it applies to all conversations.
    """

    name: str
    description: str
    trigger_role: str = ""
    trigger_category: str = ""
    required_reviewer_role: str = ""
    required_response_category: str = ""
    is_blocking: bool = True
    applies_to_template: Optional[str] = None

    # ------------------------------------------------------------------
    # Matching helpers
    # ------------------------------------------------------------------

    def matches_trigger(self, sender_role: str, category_value: str) -> bool:
        """
        Return True if this policy is activated by a message from sender_role
        of category_value.

        Empty trigger_role or trigger_category acts as a wildcard.
        """
        role_match = (not self.trigger_role) or (
            self.trigger_role.lower() == sender_role.lower()
        )
        cat_match = (not self.trigger_category) or (
            self.trigger_category.lower() == category_value.lower()
        )
        return role_match and cat_match

    def is_satisfied_by(
        self,
        reviewer_role: str,
        response_category_value: str,
    ) -> bool:
        """
        Return True if a reviewer response satisfies this policy.

        Empty required_reviewer_role or required_response_category acts as
        a wildcard (any role / any category satisfies the requirement).
        """
        role_ok = (not self.required_reviewer_role) or (
            self.required_reviewer_role.lower() == reviewer_role.lower()
        )
        cat_ok = (not self.required_response_category) or (
            self.required_response_category.lower() == response_category_value.lower()
        )
        return role_ok and cat_ok

    def applies_to(self, template_type: Optional[str]) -> bool:
        """
        True if this policy applies to the given template type.

        A policy with applies_to_template=None or "" applies to all templates.
        """
        if not self.applies_to_template:
            return True
        if template_type is None:
            return False
        return self.applies_to_template.lower() == template_type.lower()

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "trigger_role": self.trigger_role,
            "trigger_category": self.trigger_category,
            "required_reviewer_role": self.required_reviewer_role,
            "required_response_category": self.required_response_category,
            "is_blocking": self.is_blocking,
            "applies_to_template": self.applies_to_template,
        }


# ---------------------------------------------------------------------------
# PolicyEngine — evaluates a set of policies against a Conversation
# ---------------------------------------------------------------------------

class PolicyError(Exception):
    """Base for policy engine errors."""


class PolicyNotFoundError(PolicyError):
    """Raised when get_policy() / remove_policy() can't find the policy."""


class DuplicatePolicyError(PolicyError):
    """Raised when add_policy() is called with an already-registered name."""


class PolicyEngine:
    """
    In-memory store and evaluator of ConversationPolicy objects.

    Usage:
        engine = PolicyEngine()
        engine.add_policy(ConversationPolicy(
            name="security-review-required",
            description="Backend proposals must be reviewed by Security.",
            trigger_role="Backend Agent",
            trigger_category="proposal",
            required_reviewer_role="Security",
            required_response_category="review",
            is_blocking=True,
        ))
        violations = engine.evaluate(conversation)
    """

    def __init__(self) -> None:
        self._policies: Dict[str, ConversationPolicy] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add_policy(self, policy: ConversationPolicy) -> None:
        """
        Register a policy.

        Raises:
            DuplicatePolicyError: If a policy with this name already exists.
        """
        if policy.name in self._policies:
            raise DuplicatePolicyError(
                f"Policy '{policy.name}' already registered. "
                "Use remove_policy() first or choose a different name."
            )
        self._policies[policy.name] = policy

    def remove_policy(self, name: str) -> None:
        """
        Deregister a policy.

        Raises:
            PolicyNotFoundError: If the policy name is not found.
        """
        if name not in self._policies:
            raise PolicyNotFoundError(f"Policy '{name}' not found.")
        del self._policies[name]

    def get_policy(self, name: str) -> ConversationPolicy:
        """
        Return a policy by name.

        Raises:
            PolicyNotFoundError: If the policy name is not found.
        """
        if name not in self._policies:
            raise PolicyNotFoundError(f"Policy '{name}' not found.")
        return self._policies[name]

    def list_policies(self) -> List[ConversationPolicy]:
        """Return all registered policies, sorted by name."""
        return sorted(self._policies.values(), key=lambda p: p.name)

    def policy_count(self) -> int:
        return len(self._policies)

    def has_policy(self, name: str) -> bool:
        return name in self._policies

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def get_applicable_policies(
        self, sender_role: str, category_value: str, template_type: Optional[str] = None
    ) -> List[ConversationPolicy]:
        """
        Return all policies triggered by a message from sender_role of category_value.

        Args:
            sender_role: Role of the message sender.
            category_value: MessageCategory value string.
            template_type: Optional template type to filter by.

        Returns:
            List of matching ConversationPolicy objects.
        """
        return [
            p for p in self._policies.values()
            if p.matches_trigger(sender_role, category_value)
            and p.applies_to(template_type)
        ]

    def evaluate(self, conversation: "Any") -> List[PolicyViolation]:
        """
        Evaluate all applicable policies against a Conversation.

        For each trigger message found in the conversation, check whether
        the required reviewer role has responded with the required category.
        Return a list of PolicyViolation for each unsatisfied policy.

        Args:
            conversation: A core.collaboration.conversation.Conversation instance.

        Returns:
            List of PolicyViolation (empty if all policies are satisfied).
        """
        violations: List[PolicyViolation] = []

        # Build participant-role map
        role_map: Dict[str, str] = {
            p.participant_id: p.role for p in conversation.participants
        }

        for msg in conversation.messages:
            sender_role = role_map.get(msg.sender, "")
            applicable = self.get_applicable_policies(
                sender_role, msg.category.value, conversation.template_type
            )

            for policy in applicable:
                # Check if any subsequent message from required reviewer satisfies this
                satisfied = any(
                    role_map.get(later.sender, "") == policy.required_reviewer_role
                    and policy.is_satisfied_by(
                        role_map.get(later.sender, ""), later.category.value
                    )
                    and later.timestamp >= msg.timestamp
                    for later in conversation.messages
                    if later.id != msg.id
                )
                if not satisfied:
                    violations.append(PolicyViolation(
                        policy_name=policy.name,
                        description=(
                            f"Message from '{msg.sender}' ({sender_role}) "
                            f"requires a '{policy.required_response_category}' "
                            f"from role '{policy.required_reviewer_role}' — not yet received."
                        ),
                        is_blocking=policy.is_blocking,
                        trigger_message_id=msg.id,
                    ))

        return violations

    def has_blocking_violations(self, conversation: "Any") -> bool:
        """True if any blocking policy is unsatisfied."""
        return any(v.is_blocking for v in self.evaluate(conversation))


from typing import Any  # noqa: E402
