"""
Workflow template definitions for AI Company OS.

A WorkflowTemplate is a named, reusable blueprint for a class of work.
Each template value maps to a pre-defined ordered list of WorkflowStage
objects that reflect the standard operating procedure for that type of
project within AI Company OS.

Built-in templates cover the most common project types. Custom workflows
can bypass templates by supplying explicit stages to
WorkflowEngine.create_workflow().

Architecture reference: §2.7 Workflow Engine, §3 Layer 5 (Coordination Layer),
§15 Extensibility.
"""

from enum import Enum
from typing import List

from core.workflow_stage import WorkflowStage


class WorkflowTemplate(str, Enum):
    """
    Built-in workflow templates supported by the Workflow Engine.

    Each template represents a class of company work with a defined
    sequence of stages. Calling create_stages() on a template value
    returns a fresh, ordered list of WorkflowStage objects.

    Templates:
        SOFTWARE_PROJECT   — Full software product lifecycle: planning
                             through architecture, design, backend,
                             frontend, QA, CEO review, and deployment.
        WEB_APPLICATION    — Streamlined web product: discovery through
                             design, development, testing, and launch.
        MOBILE_APPLICATION — Mobile app: discovery, UX, UI, development,
                             testing, and store submission.
        SAAS_PLATFORM      — SaaS-specific: includes auth/billing stage
                             and two approval gates.
        AUTOMATION         — Process automation workflow: analysis, design,
                             implementation, testing, and deployment.
        MARKETING_CAMPAIGN — Campaign lifecycle: strategy through content
                             creation, review, launch, and analytics.
    """

    SOFTWARE_PROJECT = "SOFTWARE_PROJECT"
    WEB_APPLICATION = "WEB_APPLICATION"
    MOBILE_APPLICATION = "MOBILE_APPLICATION"
    SAAS_PLATFORM = "SAAS_PLATFORM"
    AUTOMATION = "AUTOMATION"
    MARKETING_CAMPAIGN = "MARKETING_CAMPAIGN"

    def __str__(self) -> str:
        return self.value

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    def display_name(self) -> str:
        """Return a human-readable label for this template."""
        return self.value.replace("_", " ").title()

    def stage_count(self) -> int:
        """Return the number of stages in this template's default stage list."""
        return len(self.create_stages())

    # ------------------------------------------------------------------
    # Stage factory
    # ------------------------------------------------------------------

    def create_stages(self) -> List[WorkflowStage]:
        """
        Return a fresh ordered list of WorkflowStage objects for this template.

        Calling create_stages() multiple times returns independent lists with
        equal content. The returned stages have the correct ordering (starting
        at 1) and template-appropriate governance flags.

        Returns:
            List[WorkflowStage] sorted by order ascending.
        """
        return list(_TEMPLATE_STAGES[self])


# ---------------------------------------------------------------------------
# Stage definitions — module-level to keep the enum body small
# ---------------------------------------------------------------------------

def _s(
    stage_id: str,
    name: str,
    order: int,
    departments: List[str] = None,
    inputs: List[str] = None,
    outputs: List[str] = None,
    approval: bool = False,
    discussion: bool = False,
    memory: bool = False,
) -> WorkflowStage:
    """Compact helper for defining template stages."""
    return WorkflowStage(
        id=stage_id,
        name=name,
        order=order,
        responsible_departments=departments or [],
        required_inputs=inputs or [],
        expected_outputs=outputs or [],
        approval_required=approval,
        discussion_allowed=discussion,
        memory_required=memory,
    )


_TEMPLATE_STAGES = {
    WorkflowTemplate.SOFTWARE_PROJECT: [
        _s("planning", "Planning", 1,
           departments=["Product", "Engineering"],
           inputs=["CEO Request"],
           outputs=["Project Plan", "Scope Document"],
           discussion=True),
        _s("architecture", "Architecture Design", 2,
           departments=["Engineering"],
           inputs=["Project Plan"],
           outputs=["Architecture Document", "Tech Stack Decision"],
           discussion=True),
        _s("ui_design", "UI Design", 3,
           departments=["Design"],
           inputs=["Architecture Document"],
           outputs=["Wireframes", "Design System"]),
        _s("backend_development", "Backend Development", 4,
           departments=["Backend", "Database"],
           inputs=["Architecture Document"],
           outputs=["API", "Database Schema"],
           memory=True),
        _s("frontend_development", "Frontend Development", 5,
           departments=["Frontend"],
           inputs=["UI Design", "API Specification"],
           outputs=["Frontend Application"],
           memory=True),
        _s("quality_assurance", "Quality Assurance", 6,
           departments=["QA"],
           inputs=["Application Build"],
           outputs=["Test Report", "Bug Report"],
           discussion=True, memory=True),
        _s("ceo_review", "CEO Review", 7,
           departments=["Product"],
           inputs=["Test Report", "Application Demo"],
           outputs=["Approval Decision"],
           approval=True, discussion=True),
        _s("deployment", "Deployment", 8,
           departments=["DevOps"],
           inputs=["Approval Decision", "Application Build"],
           outputs=["Deployed Application", "Deployment Record"],
           approval=True, memory=True),
    ],

    WorkflowTemplate.WEB_APPLICATION: [
        _s("discovery", "Discovery and Requirements", 1,
           departments=["Product"],
           inputs=["CEO Brief"],
           outputs=["Requirements Document"],
           discussion=True),
        _s("design", "Design", 2,
           departments=["Design"],
           inputs=["Requirements Document"],
           outputs=["Mockups", "Design Specification"]),
        _s("development", "Development", 3,
           departments=["Engineering", "Frontend", "Backend"],
           inputs=["Design Specification"],
           outputs=["Web Application"],
           memory=True),
        _s("testing", "Testing", 4,
           departments=["QA"],
           inputs=["Web Application"],
           outputs=["Test Report"],
           memory=True),
        _s("launch", "Launch", 5,
           departments=["DevOps", "Marketing"],
           inputs=["Test Report"],
           outputs=["Live Website"],
           approval=True),
    ],

    WorkflowTemplate.MOBILE_APPLICATION: [
        _s("discovery", "Discovery", 1,
           departments=["Product"],
           inputs=["CEO Brief"],
           outputs=["Product Specification"],
           discussion=True),
        _s("ux_design", "UX Design", 2,
           departments=["Design"],
           inputs=["Product Specification"],
           outputs=["User Flows", "Wireframes"],
           discussion=True),
        _s("ui_design", "UI Design", 3,
           departments=["Design"],
           inputs=["Wireframes"],
           outputs=["High-Fidelity Mockups", "Asset Package"]),
        _s("development", "Development", 4,
           departments=["Engineering"],
           inputs=["UI Design Package"],
           outputs=["Mobile Application"],
           memory=True),
        _s("testing", "Testing", 5,
           departments=["QA"],
           inputs=["Mobile Application"],
           outputs=["Test Report"],
           memory=True),
        _s("store_submission", "Store Submission", 6,
           departments=["DevOps"],
           inputs=["Test Report", "Application Build"],
           outputs=["Published Application"],
           approval=True),
    ],

    WorkflowTemplate.SAAS_PLATFORM: [
        _s("product_definition", "Product Definition", 1,
           departments=["Product"],
           inputs=["CEO Vision"],
           outputs=["PRD", "Feature List"],
           discussion=True),
        _s("architecture", "Architecture", 2,
           departments=["Engineering"],
           inputs=["PRD"],
           outputs=["Architecture Document"],
           discussion=True, memory=True),
        _s("backend_development", "Backend Development", 3,
           departments=["Backend", "Database"],
           inputs=["Architecture Document"],
           outputs=["Backend API", "Database"],
           memory=True),
        _s("frontend_development", "Frontend Development", 4,
           departments=["Frontend"],
           inputs=["Backend API", "Design System"],
           outputs=["Frontend Application"],
           memory=True),
        _s("auth_and_billing", "Authentication and Billing", 5,
           departments=["Backend", "Security"],
           inputs=["User Management Requirements"],
           outputs=["Auth System", "Billing Integration"],
           discussion=True, memory=True),
        _s("testing", "Testing", 6,
           departments=["QA"],
           inputs=["Complete Application"],
           outputs=["Test Report"],
           memory=True),
        _s("ceo_review", "CEO Review", 7,
           departments=["Product"],
           inputs=["Test Report", "Application Demo"],
           outputs=["Approval Decision"],
           approval=True, discussion=True),
        _s("deployment", "Deployment", 8,
           departments=["DevOps"],
           inputs=["Approval Decision"],
           outputs=["Production System"],
           approval=True, memory=True),
    ],

    WorkflowTemplate.AUTOMATION: [
        _s("process_analysis", "Process Analysis", 1,
           departments=["Engineering", "Product"],
           inputs=["Process Description"],
           outputs=["Process Map", "Automation Requirements"],
           discussion=True),
        _s("design", "Automation Design", 2,
           departments=["Engineering"],
           inputs=["Process Map"],
           outputs=["Automation Blueprint"]),
        _s("implementation", "Implementation", 3,
           departments=["Engineering"],
           inputs=["Automation Blueprint"],
           outputs=["Automation Script"],
           memory=True),
        _s("testing", "Testing", 4,
           departments=["QA"],
           inputs=["Automation Script"],
           outputs=["Test Report"],
           memory=True),
        _s("deployment", "Deployment", 5,
           departments=["DevOps"],
           inputs=["Test Report"],
           outputs=["Live Automation"],
           approval=True),
    ],

    WorkflowTemplate.MARKETING_CAMPAIGN: [
        _s("strategy", "Strategy", 1,
           departments=["Marketing", "Product"],
           inputs=["Campaign Brief"],
           outputs=["Campaign Strategy", "Target Audience"],
           discussion=True),
        _s("creative_brief", "Creative Brief", 2,
           departments=["Marketing", "Design"],
           inputs=["Campaign Strategy"],
           outputs=["Creative Brief", "Brand Guidelines"]),
        _s("content_creation", "Content Creation", 3,
           departments=["Marketing"],
           inputs=["Creative Brief"],
           outputs=["Campaign Content", "Assets"],
           discussion=True, memory=True),
        _s("review", "Review", 4,
           departments=["Marketing", "Product"],
           inputs=["Campaign Content"],
           outputs=["Approval"],
           approval=True, discussion=True),
        _s("launch", "Launch", 5,
           departments=["Marketing", "DevOps"],
           inputs=["Approved Content"],
           outputs=["Live Campaign"]),
        _s("analytics", "Analytics", 6,
           departments=["Marketing"],
           inputs=["Campaign Performance Data"],
           outputs=["Analytics Report"],
           memory=True),
    ],
}
