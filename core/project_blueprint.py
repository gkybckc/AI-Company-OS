"""
Project blueprint model for AI Company OS.

A ProjectBlueprint is the primary output of the Planner Engine. It is an
immutable, structured planning document that captures everything the
Executive Engine needs to begin project execution: what is being built,
who is needed, how complex it is, what risks exist, and what the
strategic recommendations are.

The blueprint is produced before any task is created and before any
department is engaged. It is the contract between the planning phase
and the execution phase.

Architecture reference: §2.1 Executive Engine, §5 Coordination Layer,
§11 Task Lifecycle (Phase 1 — CREATION).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from core.department_requirement import DepartmentRequirement
from core.project_type import ProjectType
from core.risk import Risk


@dataclass(frozen=True)
class ProjectBlueprint:
    """
    Immutable planning document produced by the Planner Engine.

    A blueprint describes the full scope of a project at the planning level.
    It does not contain tasks, agent assignments, or implementation details —
    those are the Executive Engine's responsibility after receiving the blueprint.

    All numeric estimates are deterministic approximations based on the
    detected project type, risk profile, and department composition. They
    provide a planning baseline, not a contractual commitment.

    Attributes:
        project_title: A concise, professional title derived from the
            CEO's request.
        objective: A single structured statement of what the project
            must achieve and under what quality conditions.
        description: A paragraph-length description of the project scope,
            the functional areas it covers, and its primary challenges.
        project_type: The detected category of the project.
        departments: Ordered list of departments required for this project,
            each with a project-specific rationale and criticality flag.
        estimated_task_count: Approximate number of tasks the Executive
            Engine will need to create to deliver this project.
        estimated_sprint_count: Approximate number of two-week sprints
            required from kickoff to CEO approval.
        estimated_team_size: Approximate number of agents that will need
            to be active simultaneously at peak execution.
        complexity_score: Integer from 1 (trivial) to 10 (maximum
            complexity), computed from the project type baseline and
            the severity of detected risks.
        risks: Ordered list of detected risks, sorted by severity
            (CRITICAL first). Empty for very simple projects.
        recommendations: Ordered list of actionable recommendations,
            starting with risk-mitigation actions and followed by
            general best-practice guidance for this project type.
        generated_at: UTC timestamp of the moment this blueprint was
            produced by the Planner Engine.
        raw_request: The original CEO request string, preserved verbatim
            for auditability.
    """

    project_title: str
    objective: str
    description: str
    project_type: ProjectType
    departments: List[DepartmentRequirement]
    estimated_task_count: int
    estimated_sprint_count: int
    estimated_team_size: int
    complexity_score: int
    risks: List[Risk]
    recommendations: List[str]
    generated_at: datetime
    raw_request: str
