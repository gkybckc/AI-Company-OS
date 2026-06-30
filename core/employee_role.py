"""
Employee role and seniority taxonomy for AI Company OS.

Defines the complete set of specialist roles that agents fill within the
company, and the seniority levels that qualify those roles. The Executive
Engine uses roles when determining which employees to assign to a task.
The WorkforceRegistry uses seniority when reporting workforce composition.

Architecture reference: §2.2 Agent Runtime, §3 Layer 4 (Agent Layer),
Constitution Chapter 5 (Hierarchy and Roles).
"""

from enum import Enum


class EmployeeRole(str, Enum):
    """
    Specialist roles that employees occupy within AI Company OS.

    Each role defines a domain of expertise and a set of permitted task
    types. Agents are specialized — a Backend Agent does not design
    interfaces; a UI Designer does not write server-side code. Role
    boundaries are enforced by the Agent Runtime.

    Role — Primary Domain:

    BACKEND_AGENT       — Server-side development: APIs, business logic,
                          data access layers, and backend service integration.

    FRONTEND_AGENT      — Client-side development: browser applications,
                          component libraries, and frontend build pipelines.

    UI_DESIGNER         — User interface design: visual composition,
                          design systems, component specifications, and
                          high-fidelity mockups.

    UX_DESIGNER         — User experience design: user research synthesis,
                          information architecture, user flows, wireframes,
                          and interaction design.

    QA_ENGINEER         — Quality assurance: test planning, test case
                          authoring, defect identification, regression
                          testing, and quality reporting.

    DEVOPS_ENGINEER     — Infrastructure and delivery: CI/CD pipelines,
                          cloud infrastructure, deployment automation,
                          monitoring, and operational tooling.

    SECURITY_SPECIALIST — Security engineering: threat modelling, code
                          review for vulnerabilities, security testing,
                          and compliance documentation.

    PRODUCT_ANALYST     — Product and business analysis: requirements
                          definition, feature scoping, user story writing,
                          and acceptance criteria authorship.

    MARKETING_SPECIALIST — Marketing execution: copywriting, content
                           creation, campaign management, brand guidelines
                           application, and growth strategy.

    RESEARCH_ANALYST    — Research and knowledge work: market research,
                          competitive analysis, technical discovery, and
                          synthesis of findings into actionable reports.
    """

    BACKEND_AGENT = "Backend Agent"
    FRONTEND_AGENT = "Frontend Agent"
    UI_DESIGNER = "UI Designer"
    UX_DESIGNER = "UX Designer"
    QA_ENGINEER = "QA Engineer"
    DEVOPS_ENGINEER = "DevOps Engineer"
    SECURITY_SPECIALIST = "Security Specialist"
    PRODUCT_ANALYST = "Product Analyst"
    MARKETING_SPECIALIST = "Marketing Specialist"
    RESEARCH_ANALYST = "Research Analyst"

    def __str__(self) -> str:
        return self.value


class Seniority(str, Enum):
    """
    Experience and authority levels for employees.

    Seniority determines the complexity of tasks an employee can own
    independently, the degree of Director oversight required, and how
    their contributions are weighted in department capacity planning.

    JUNIOR    — Early-career. Requires close Director oversight. Suited
                for well-defined, bounded tasks with clear acceptance
                criteria. Output requires peer review before submission.

    MID       — Established practitioner. Works autonomously on standard
                tasks within their domain. Can review JUNIOR output.
                Escalates ambiguous cases to SENIOR or Director.

    SENIOR    — Experienced specialist. Can own complex, multi-part tasks.
                Provides technical guidance to JUNIOR and MID employees.
                Can review all output within their role domain.

    LEAD      — Domain leader within a department. Coordinates a cluster
                of agents, defines standards, and resolves technical
                conflicts. Reports directly to the Director.

    PRINCIPAL — Highest individual-contributor seniority. Cross-department
                technical authority. Can advise the Director and Executive
                Engine on matters within their domain. Rarely assigned to
                routine tasks; engaged for architectural or strategic work.
    """

    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"
    PRINCIPAL = "Principal"

    def __str__(self) -> str:
        return self.value
