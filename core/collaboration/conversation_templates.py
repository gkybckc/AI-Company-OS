"""
ConversationTemplate — reusable conversation blueprints.

Six built-in templates define the standard collaboration patterns:
Architecture Review, Security Review, Sprint Planning, Code Review,
Risk Assessment, and CEO Briefing.

Templates are pure data — they prescribe which roles should participate,
which message categories are expected, and which policies apply.
No AI, no networking, no async.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TemplateType(str, Enum):
    """Standard collaboration template types."""

    ARCHITECTURE_REVIEW = "architecture_review"
    SECURITY_REVIEW = "security_review"
    SPRINT_PLANNING = "sprint_planning"
    CODE_REVIEW = "code_review"
    RISK_ASSESSMENT = "risk_assessment"
    CEO_BRIEFING = "ceo_briefing"

    def __str__(self) -> str:
        return self.value

    def label(self) -> str:
        labels = {
            "architecture_review": "Mimari Inceleme",
            "security_review": "Guvenlik Incelemesi",
            "sprint_planning": "Sprint Planlamasi",
            "code_review": "Kod Incelemesi",
            "risk_assessment": "Risk Degerlendirmesi",
            "ceo_briefing": "CEO Brifing",
        }
        return labels.get(self.value, self.value.replace("_", " ").title())


@dataclass
class ConversationTemplate:
    """
    Blueprint for a standard conversation type.

    Attributes:
        name: Human-readable name (e.g. "Architecture Review").
        description: What this template is for.
        template_type: TemplateType enum value.
        default_roles: Ordered list of roles that should participate.
        suggested_categories: Message categories in typical workflow order.
        policy_names: Names of ConversationPolicy objects that apply.
        opening_message: Suggested first message content for the creator.
        required_roles: Roles that MUST participate (subset of default_roles).
    """

    name: str
    description: str
    template_type: TemplateType
    default_roles: List[str]
    suggested_categories: List[str]
    policy_names: List[str]
    opening_message: str
    required_roles: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def requires_role(self, role: str) -> bool:
        """True if the given role is required by this template."""
        return role in self.required_roles

    def category_count(self) -> int:
        return len(self.suggested_categories)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type.value,
            "template_label": self.template_type.label(),
            "default_roles": list(self.default_roles),
            "required_roles": list(self.required_roles),
            "suggested_categories": list(self.suggested_categories),
            "policy_names": list(self.policy_names),
            "opening_message": self.opening_message,
        }


# ---------------------------------------------------------------------------
# Built-in templates
# ---------------------------------------------------------------------------

BUILT_IN_TEMPLATES: Dict[TemplateType, ConversationTemplate] = {

    TemplateType.ARCHITECTURE_REVIEW: ConversationTemplate(
        name="Architecture Review",
        description=(
            "Multi-department review of a proposed system architecture. "
            "Backend proposes, Security and QA review, Executive summarises."
        ),
        template_type=TemplateType.ARCHITECTURE_REVIEW,
        default_roles=[
            "Backend Agent",
            "Security",
            "QA Engineer",
            "Executive",
        ],
        required_roles=["Backend Agent", "Security"],
        suggested_categories=["proposal", "review", "risk", "decision"],
        policy_names=["security-review-required", "qa-review-required"],
        opening_message=(
            "Architecture proposal ready for review. "
            "Please evaluate the attached design for security, scalability, and quality concerns."
        ),
    ),

    TemplateType.SECURITY_REVIEW: ConversationTemplate(
        name="Security Review",
        description=(
            "Security team reviews authentication and data handling code "
            "produced by Backend. QA validates. Executive records decision."
        ),
        template_type=TemplateType.SECURITY_REVIEW,
        default_roles=[
            "Backend Agent",
            "Security",
            "QA Engineer",
            "Executive",
        ],
        required_roles=["Backend Agent", "Security"],
        suggested_categories=["proposal", "review", "warning", "risk", "decision"],
        policy_names=["security-review-required"],
        opening_message=(
            "Authentication code submitted for Security review. "
            "Focus areas: token handling, session management, input validation."
        ),
    ),

    TemplateType.SPRINT_PLANNING: ConversationTemplate(
        name="Sprint Planning",
        description=(
            "Cross-team sprint planning session. Teams share capacity, "
            "raise blockers, propose task assignments, reach consensus."
        ),
        template_type=TemplateType.SPRINT_PLANNING,
        default_roles=[
            "Backend Agent",
            "Frontend Agent",
            "QA Engineer",
            "DevOps Engineer",
            "Executive",
        ],
        required_roles=["Executive"],
        suggested_categories=["proposal", "question", "answer", "decision"],
        policy_names=["executive-summary-required"],
        opening_message=(
            "Sprint planning session open. "
            "Each team: report capacity, flag blockers, propose sprint goal contributions."
        ),
    ),

    TemplateType.CODE_REVIEW: ConversationTemplate(
        name="Code Review",
        description=(
            "Structured peer code review. Author proposes, peers review, "
            "QA signs off, author acknowledges and records final decision."
        ),
        template_type=TemplateType.CODE_REVIEW,
        default_roles=[
            "Backend Agent",
            "QA Engineer",
            "Security",
        ],
        required_roles=["QA Engineer"],
        suggested_categories=["proposal", "review", "question", "answer", "decision"],
        policy_names=["qa-review-required"],
        opening_message=(
            "Code review initiated. "
            "Reviewers: please assess correctness, test coverage, and code style."
        ),
    ),

    TemplateType.RISK_ASSESSMENT: ConversationTemplate(
        name="Risk Assessment",
        description=(
            "Structured risk identification and mitigation planning. "
            "Any agent may raise risks; all teams contribute mitigations; "
            "Executive records accepted risks and actions."
        ),
        template_type=TemplateType.RISK_ASSESSMENT,
        default_roles=[
            "Backend Agent",
            "Security",
            "QA Engineer",
            "DevOps Engineer",
            "Executive",
        ],
        required_roles=["Executive"],
        suggested_categories=["risk", "proposal", "review", "decision"],
        policy_names=["executive-summary-required"],
        opening_message=(
            "Risk assessment session open. "
            "Raise all known risks using the RISK category. "
            "Propose mitigations using PROPOSAL. Executive will record accepted actions."
        ),
    ),

    TemplateType.CEO_BRIEFING: ConversationTemplate(
        name="CEO Briefing",
        description=(
            "Executive summary session for CEO sign-off. "
            "Executive presents consolidated summary; CEO approves or requests changes."
        ),
        template_type=TemplateType.CEO_BRIEFING,
        default_roles=[
            "Executive",
            "CEO",
        ],
        required_roles=["Executive", "CEO"],
        suggested_categories=["proposal", "approval_request", "decision"],
        policy_names=["ceo-approval-required"],
        opening_message=(
            "CEO briefing ready. "
            "All team discussions have been completed and summarised. "
            "Awaiting CEO review and approval."
        ),
    ),
}


def get_template(template_type: TemplateType) -> ConversationTemplate:
    """
    Return the built-in template for the given TemplateType.

    Args:
        template_type: One of TemplateType.

    Returns:
        The ConversationTemplate.

    Raises:
        KeyError: If the template type is not in BUILT_IN_TEMPLATES.
    """
    return BUILT_IN_TEMPLATES[template_type]


def list_templates() -> List[ConversationTemplate]:
    """Return all built-in templates, sorted by name."""
    return sorted(BUILT_IN_TEMPLATES.values(), key=lambda t: t.name)


# ---------------------------------------------------------------------------
# Default policies that match built-in template policy_names
# ---------------------------------------------------------------------------

def default_policies() -> List["ConversationPolicy"]:
    """
    Return the set of ConversationPolicy objects referenced by built-in templates.

    Import ConversationPolicy here to avoid circular imports.
    """
    from core.collaboration.conversation_policy import ConversationPolicy
    return [
        ConversationPolicy(
            name="security-review-required",
            description="Any Backend proposal must receive a Security review before conversation close.",
            trigger_role="Backend Agent",
            trigger_category="proposal",
            required_reviewer_role="Security",
            required_response_category="review",
            is_blocking=True,
            applies_to_template=None,
        ),
        ConversationPolicy(
            name="qa-review-required",
            description="Any proposal must receive a QA review before conversation close.",
            trigger_role="",
            trigger_category="proposal",
            required_reviewer_role="QA Engineer",
            required_response_category="review",
            is_blocking=True,
            applies_to_template=None,
        ),
        ConversationPolicy(
            name="executive-summary-required",
            description="Discussions must conclude with an Executive decision message.",
            trigger_role="",
            trigger_category="proposal",
            required_reviewer_role="Executive",
            required_response_category="decision",
            is_blocking=False,
            applies_to_template=None,
        ),
        ConversationPolicy(
            name="ceo-approval-required",
            description="CEO briefings require an explicit CEO decision before close.",
            trigger_role="Executive",
            trigger_category="approval_request",
            required_reviewer_role="CEO",
            required_response_category="decision",
            is_blocking=True,
            applies_to_template="ceo_briefing",
        ),
    ]


from typing import Any  # noqa: E402
