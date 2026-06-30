"""
Planner Engine for AI Company OS.

The PlannerEngine is the first intelligence layer of the system. It is NOT
an AI model and NOT an LLM. It is a deterministic planning engine that
analyzes a CEO's free-text request and produces a structured ProjectBlueprint
before any execution begins.

The engine operates entirely through keyword scoring, lookup tables, and
rule-based inference. The same input always produces the same output.

Responsibilities:
- Detect the project type from the CEO's request.
- Determine which departments are required and why.
- Identify technical risks based on request signals.
- Estimate project complexity, sprint count, task count, and team size.
- Generate actionable recommendations for the Executive Engine.
- Assemble all findings into a ProjectBlueprint.

The Planner NEVER creates tasks.
The Planner NEVER assigns work to agents.
The Planner NEVER executes anything.
The Planner ONLY plans.

Architecture reference: §2.1 Executive Engine, §3 Layer 5 (Coordination),
§11 Task Lifecycle Phase 1, Constitution Chapter 4.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from core.department_requirement import Department, DepartmentRequirement
from core.project_blueprint import ProjectBlueprint
from core.project_type import ProjectType
from core.risk import Risk, RiskCategory, RiskLevel


# ---------------------------------------------------------------------------
# Module-level constants — all deterministic rule tables
# ---------------------------------------------------------------------------

# Keyword signals for project type detection.
# Each list entry is a substring searched (case-insensitive) in the normalized
# request. Longer phrases are inherently more specific and score as highly as
# single keywords, so more specific phrases act as natural tie-breakers.
_PROJECT_TYPE_SIGNALS: Dict[ProjectType, List[str]] = {
    ProjectType.MOBILE_APP: [
        "mobile", "ios", "android", "flutter", "react native",
        "smartphone", "tablet", "app store", "play store", "mobile app",
    ],
    ProjectType.DESKTOP_APP: [
        "desktop", "electron", "windows app", "mac app",
        "desktop application", "native desktop", "pc app",
    ],
    ProjectType.AI_TOOL: [
        "machine learning", "deep learning", "artificial intelligence",
        "neural network", "nlp", "natural language processing", "gpt", "llm",
        "chatbot", "ai-powered", "recommendation engine", "ai assistant",
        "computer vision", "speech recognition", "generative ai",
    ],
    ProjectType.API: [
        "rest api", "graphql", "api gateway", "backend api",
        "api service", "api endpoint", "microservice", "webhook",
        "openapi", "swagger", "api-first",
    ],
    ProjectType.AUTOMATION: [
        "automate", "automation", "scraper", "scraping",
        "workflow automation", "scheduled task", "robotic", "ci/cd",
        "data pipeline", "etl", "batch processing", "cron", "job scheduler",
    ],
    ProjectType.ECOMMERCE: [
        "ecommerce", "e-commerce", "online store", "online shop",
        "marketplace", "shopping cart", "checkout", "product catalog",
        "sell online", "retail platform",
    ],
    ProjectType.DATA_PIPELINE: [
        "data warehouse", "data lake", "big data", "data processing",
        "data ingestion", "analytics pipeline", "data engineering",
        "etl pipeline", "real-time analytics",
    ],
    ProjectType.GAME: [
        "game", "gaming", "multiplayer game", "rpg", "fps",
        "video game", "game engine", "puzzle game", "online game",
    ],
    ProjectType.SAAS: [
        "saas", "software as a service", "subscription", "b2b",
        "crm", "erp", "multi-tenant", "dashboard", "management platform",
        "business platform", "enterprise software", "tenant",
    ],
    ProjectType.WEB_PLATFORM: [
        "streaming", "social network", "web platform", "content platform",
        "community platform", "online platform", "portal", "web app",
        "platform", "media platform", "netflix", "youtube",
        "social media", "news platform", "streaming platform",
    ],
}

# Priority order for tie-breaking when two project types score equally.
# Earlier entries win over later ones.
_TYPE_PRIORITY: List[ProjectType] = [
    ProjectType.AI_TOOL,
    ProjectType.GAME,
    ProjectType.ECOMMERCE,
    ProjectType.MOBILE_APP,
    ProjectType.DESKTOP_APP,
    ProjectType.DATA_PIPELINE,
    ProjectType.AUTOMATION,
    ProjectType.API,
    ProjectType.SAAS,
    ProjectType.WEB_PLATFORM,
]

# Base complexity score per project type (1–10 scale).
_BASE_COMPLEXITY: Dict[ProjectType, int] = {
    ProjectType.API: 2,
    ProjectType.AUTOMATION: 3,
    ProjectType.DESKTOP_APP: 3,
    ProjectType.DATA_PIPELINE: 4,
    ProjectType.MOBILE_APP: 4,
    ProjectType.GAME: 5,
    ProjectType.WEB_PLATFORM: 5,
    ProjectType.ECOMMERCE: 6,
    ProjectType.SAAS: 6,
    ProjectType.AI_TOOL: 7,
}

# Estimated sprint count per complexity score (1–10).
_SPRINT_TABLE: Dict[int, int] = {
    1: 2,
    2: 3,
    3: 4,
    4: 6,
    5: 8,
    6: 10,
    7: 13,
    8: 16,
    9: 20,
    10: 24,
}

# Risk detection table.
# Maps RiskCategory → (keyword signals, risk level, description).
# Keyword signals are substrings searched in the normalized request.
_RISK_DEFINITIONS: Dict[RiskCategory, Tuple[List[str], RiskLevel, str]] = {
    RiskCategory.VIDEO_STREAMING: (
        [
            "stream", "streaming", "video", "media", "watch", "playback",
            "netflix", "hbo", "youtube", "player", "vod", "on-demand", "live stream",
        ],
        RiskLevel.CRITICAL,
        (
            "Video streaming demands adaptive bitrate delivery (HLS/MPEG-DASH), "
            "a CDN for global distribution, a video transcoding pipeline, and "
            "robust cross-device player compatibility. These are high-cost, "
            "high-effort infrastructure concerns that must be planned from Sprint 1."
        ),
    ),
    RiskCategory.AI_INTEGRATION: (
        [
            "ai", "artificial intelligence", "machine learning", "deep learning",
            "neural", "gpt", "llm", "recommend", "personali", "nlp", "chatbot",
            "predictive", "generative",
        ],
        RiskLevel.HIGH,
        (
            "AI integration introduces model latency, non-deterministic output, "
            "inference cost uncertainty, and dependency on external intelligence "
            "providers. Output quality validation and cost controls are non-trivial."
        ),
    ),
    RiskCategory.REAL_TIME: (
        [
            "real-time", "realtime", "live", "chat", "websocket", "socket",
            "instant", "broadcast", "feed", "live update", "push",
        ],
        RiskLevel.HIGH,
        (
            "Real-time features require persistent connections, message ordering "
            "guarantees, state synchronization between clients, and graceful "
            "handling of dropped connections and reconnection flows."
        ),
    ),
    RiskCategory.PAYMENTS: (
        [
            "payment", "billing", "subscription", "purchase", "checkout",
            "stripe", "pricing", "plan", "premium", "freemium", "netflix",
            "pay", "invoice", "revenue", "monetize", "paid",
        ],
        RiskLevel.HIGH,
        (
            "Payment processing requires PCI-DSS compliance, idempotent transaction "
            "handlers, and a complete subscription lifecycle: trials, upgrades, "
            "downgrades, cancellations, and failed-payment recovery flows."
        ),
    ),
    RiskCategory.AUTHENTICATION: (
        [
            "auth", "login", "user", "account", "register", "sign in", "sign up",
            "password", "oauth", "sso", "session", "platform", "member",
            "profile", "credential",
        ],
        RiskLevel.HIGH,
        (
            "Authentication and session management introduce critical security "
            "vulnerabilities if implemented incorrectly. Token lifecycle, "
            "refresh rotation, rate limiting, and secure credential storage "
            "require deliberate design."
        ),
    ),
    RiskCategory.SCALING: (
        [
            "scale", "million", "billion", "global", "distributed",
            "high traffic", "large", "enterprise", "platform", "concurrent",
            "worldwide", "performance", "load",
        ],
        RiskLevel.HIGH,
        (
            "Scaling requires stateless service design, horizontal scaling "
            "capability, database read replicas, multi-layer caching, and "
            "CDN configuration. Retrofitting scalability after launch is "
            "expensive and risky."
        ),
    ),
    RiskCategory.DATA_PRIVACY: (
        [
            "privacy", "gdpr", "personal data", "user data", "sensitive",
            "pii", "data protection", "ccpa", "compliance", "regulation",
        ],
        RiskLevel.MEDIUM,
        (
            "Handling personal user data requires GDPR/CCPA compliance, "
            "data minimization, consent management, right-to-erasure "
            "implementation, and a documented data retention policy."
        ),
    ),
    RiskCategory.FILE_STORAGE: (
        [
            "upload", "file", "storage", "cloud storage", "s3", "blob",
            "attachment", "document", "image upload", "media upload",
            "asset", "cdn", "static files",
        ],
        RiskLevel.MEDIUM,
        (
            "File storage requires content validation, virus scanning, "
            "per-user access control, cost management at scale, "
            "and a CDN strategy for efficient delivery."
        ),
    ),
    RiskCategory.MAPS: (
        [
            "map", "location", "geo", "geolocation", "gps",
            "coordinates", "directions", "navigate", "mapping",
        ],
        RiskLevel.MEDIUM,
        (
            "Maps and geolocation features require third-party provider "
            "agreements, API quota management, caching of frequent requests, "
            "and graceful fallback when the provider is unavailable."
        ),
    ),
    RiskCategory.NOTIFICATIONS: (
        [
            "notification", "email", "push notification", "sms",
            "alert", "remind", "notify", "message", "inbox",
        ],
        RiskLevel.LOW,
        (
            "Notification delivery requires opt-in/opt-out preference management, "
            "delivery rate monitoring, bounce handling, and provider "
            "redundancy for business-critical alerts."
        ),
    ),
    RiskCategory.THIRD_PARTY_INTEGRATIONS: (
        [
            "third-party", "integration", "api integration", "webhook",
            "zapier", "slack integration", "google api", "facebook api",
            "twitter api", "external service",
        ],
        RiskLevel.LOW,
        (
            "Third-party integrations introduce external dependencies, "
            "API version drift, rate limits, and availability risk. "
            "Each integration must be isolated behind an abstraction layer."
        ),
    ),
}

# Risk severity weights used for complexity calculation.
_RISK_WEIGHTS: Dict[RiskLevel, int] = {
    RiskLevel.CRITICAL: 2,
    RiskLevel.HIGH: 1,
    RiskLevel.MEDIUM: 0,
    RiskLevel.LOW: 0,
}

# Base departments for each project type.
# Tuple: (Department, rationale, is_critical)
_BASE_DEPARTMENTS: Dict[ProjectType, List[Tuple[Department, str, bool]]] = {
    ProjectType.SAAS: [
        (Department.BACKEND, "Core application logic, multi-tenant API design, and server-side processing.", True),
        (Department.DATABASE, "Data modeling, multi-tenant isolation, and query optimization.", True),
        (Department.FRONTEND, "User dashboard, feature interfaces, and browser-based interactions.", True),
        (Department.DESIGN, "UX flows, interface wireframes, and a scalable design system.", False),
        (Department.QA, "Test coverage across all application layers and user subscription flows.", True),
        (Department.DEVOPS, "Cloud infrastructure, CI/CD pipelines, and environment management.", True),
    ],
    ProjectType.WEB_PLATFORM: [
        (Department.BACKEND, "Server-side logic, content delivery APIs, and platform services.", True),
        (Department.FRONTEND, "Web interface, interactive components, and browser-based client.", True),
        (Department.DATABASE, "Content storage, user data management, and query performance.", True),
        (Department.DESIGN, "Platform UX design, visual identity, and component library.", False),
        (Department.QA, "Functional testing, performance testing, and cross-browser compatibility.", True),
        (Department.DEVOPS, "Cloud infrastructure, CDN configuration, and deployment automation.", True),
    ],
    ProjectType.MOBILE_APP: [
        (Department.BACKEND, "Mobile APIs, push notification services, and backend business logic.", True),
        (Department.ENGINEERING, "Native or cross-platform mobile development and platform integration.", True),
        (Department.DATABASE, "Local and remote data synchronization and schema design.", True),
        (Department.DESIGN, "Mobile UX, screen flows, and platform-specific UI components.", True),
        (Department.QA, "Device compatibility testing and mobile performance profiling.", True),
        (Department.DEVOPS, "App store deployment pipelines and backend hosting.", False),
    ],
    ProjectType.AUTOMATION: [
        (Department.BACKEND, "Automation logic, task scheduling engine, and execution orchestration.", True),
        (Department.DATABASE, "Job state persistence, execution logs, and result storage.", True),
        (Department.QA, "Automation reliability testing, idempotency validation, and edge case coverage.", True),
        (Department.DEVOPS, "Infrastructure for scheduled execution, monitoring, and alerting.", True),
    ],
    ProjectType.DESKTOP_APP: [
        (Department.ENGINEERING, "Desktop application development and OS-level integrations.", True),
        (Department.BACKEND, "Backend services and API integrations supporting the desktop client.", False),
        (Department.DESIGN, "Desktop UX, native UI patterns, and accessibility compliance.", True),
        (Department.QA, "Cross-platform testing and OS compatibility validation.", True),
    ],
    ProjectType.AI_TOOL: [
        (Department.BACKEND, "AI model integration, inference API, and prompt orchestration.", True),
        (Department.ENGINEERING, "ML pipeline, model evaluation infrastructure, and data preprocessing.", True),
        (Department.DATABASE, "Training data management, inference result caching, and audit logs.", True),
        (Department.FRONTEND, "User interface for AI interaction and result visualization.", False),
        (Department.QA, "Model output validation, accuracy evaluation, and regression testing.", True),
        (Department.DEVOPS, "GPU/CPU infrastructure, model deployment, and autoscaling.", True),
    ],
    ProjectType.API: [
        (Department.BACKEND, "API design, endpoint implementation, and business logic.", True),
        (Department.DATABASE, "Data model design, schema migrations, and query optimization.", True),
        (Department.QA, "API contract testing, load testing, and security scanning.", True),
        (Department.DEVOPS, "API gateway setup, rate limiting, versioning, and deployment.", True),
    ],
    ProjectType.ECOMMERCE: [
        (Department.BACKEND, "Product catalog, order management, inventory, and payment processing.", True),
        (Department.FRONTEND, "Storefront, product pages, cart, and checkout flow.", True),
        (Department.DATABASE, "Product, order, customer, and inventory data management.", True),
        (Department.DESIGN, "Storefront UX, product imagery guidelines, and checkout design.", True),
        (Department.QA, "Order flow testing, payment testing, and cross-device validation.", True),
        (Department.DEVOPS, "Hosting, product image CDN, and deployment pipelines.", True),
        (Department.MARKETING, "Product discovery, SEO strategy, and promotional campaigns.", False),
        (Department.LEGAL, "Terms of service, return policies, and consumer protection compliance.", True),
        (Department.FINANCE, "Payment reconciliation, tax calculation, and revenue reporting.", True),
    ],
    ProjectType.DATA_PIPELINE: [
        (Department.BACKEND, "Pipeline orchestration, transformation logic, and scheduling.", True),
        (Department.DATABASE, "Source and target data store management and schema design.", True),
        (Department.ENGINEERING, "Data processing framework implementation and performance optimization.", True),
        (Department.QA, "Data quality validation, pipeline reliability, and regression testing.", True),
        (Department.DEVOPS, "Pipeline scheduling, monitoring, and cloud data infrastructure.", True),
    ],
    ProjectType.GAME: [
        (Department.ENGINEERING, "Game logic, physics, and platform or engine integration.", True),
        (Department.BACKEND, "Game servers, matchmaking, leaderboards, and player accounts.", True),
        (Department.DATABASE, "Player data, game state, save data, and analytics storage.", True),
        (Department.DESIGN, "Game UI, level design concepts, and visual design language.", True),
        (Department.QA, "Gameplay testing, balance validation, and performance profiling.", True),
        (Department.DEVOPS, "Game server hosting, deployment, and session scaling.", True),
    ],
}

# Conditional department additions driven by detected risk categories.
# Tuple: (RiskCategory, Department, rationale, is_critical)
_RISK_DRIVEN_DEPARTMENTS: List[Tuple[RiskCategory, Department, str, bool]] = [
    (
        RiskCategory.AUTHENTICATION,
        Department.SECURITY,
        "Authentication systems, authorization policies, user data protection, and security hardening.",
        True,
    ),
    (
        RiskCategory.PAYMENTS,
        Department.FINANCE,
        "Payment processing integration, subscription lifecycle management, and revenue reconciliation.",
        True,
    ),
    (
        RiskCategory.DATA_PRIVACY,
        Department.LEGAL,
        "Data privacy compliance, consent management, and regulatory requirements (GDPR/CCPA).",
        True,
    ),
]

# Consumer-facing project types that always benefit from Marketing.
_CONSUMER_PROJECT_TYPES: Set[ProjectType] = {
    ProjectType.WEB_PLATFORM,
    ProjectType.MOBILE_APP,
    ProjectType.GAME,
    ProjectType.ECOMMERCE,
    ProjectType.SAAS,
}

# Keyword signals that add departments not covered by the above rules.
# Tuple: (keyword signals, Department, rationale, is_critical)
_KEYWORD_DRIVEN_DEPARTMENTS: List[Tuple[List[str], Department, str, bool]] = [
    (
        ["stream", "streaming", "broadcast", "media", "video", "content license",
         "music", "podcast", "audio"],
        Department.LEGAL,
        "Content licensing agreements, distribution rights, and intellectual property compliance.",
        True,
    ),
    (
        ["security", "penetration", "vulnerability", "audit", "compliance",
         "encrypt", "drm", "firewall"],
        Department.SECURITY,
        "Security hardening, vulnerability management, and compliance auditing.",
        True,
    ),
    (
        ["marketing", "campaign", "seo", "brand", "growth", "acquisition",
         "social", "ad ", "ads", "advertis"],
        Department.MARKETING,
        "User acquisition strategy, brand positioning, and growth campaigns.",
        False,
    ),
]

# Recommendations keyed by risk category, ordered by severity.
_RISK_RECOMMENDATIONS: Dict[RiskCategory, str] = {
    RiskCategory.VIDEO_STREAMING: (
        "Implement HLS or MPEG-DASH adaptive bitrate streaming. "
        "Integrate a CDN for global video delivery. "
        "Build a dedicated video transcoding pipeline. "
        "Test playback across all target devices and browsers before launch."
    ),
    RiskCategory.AI_INTEGRATION: (
        "Abstract all AI provider calls behind an internal gateway. "
        "Implement prompt validation, output filtering, and content safety checks. "
        "Monitor inference costs per user and enforce rate limits. "
        "Design for provider substitution from day one."
    ),
    RiskCategory.REAL_TIME: (
        "Use WebSocket or Server-Sent Events for real-time delivery. "
        "Implement client-side reconnection logic with exponential backoff. "
        "Design message ordering guarantees and a delivery queue for offline clients."
    ),
    RiskCategory.PAYMENTS: (
        "Use a PCI-DSS compliant payment gateway. "
        "Build idempotent payment handlers to prevent double-charging. "
        "Implement the full subscription lifecycle: trials, upgrades, "
        "downgrades, cancellations, and failed-payment recovery."
    ),
    RiskCategory.AUTHENTICATION: (
        "Implement OAuth 2.0 with JWT and refresh token rotation. "
        "Enforce HTTPS on all endpoints. "
        "Apply rate limiting on authentication endpoints to prevent brute-force attacks. "
        "Store credentials using a modern hashing algorithm (bcrypt or Argon2)."
    ),
    RiskCategory.SCALING: (
        "Design stateless, horizontally scalable services from Sprint 1. "
        "Implement multi-layer caching (in-memory, CDN, database query cache). "
        "Use database read replicas for read-heavy workloads. "
        "Define and validate performance benchmarks before each major release."
    ),
    RiskCategory.DATA_PRIVACY: (
        "Implement data minimization: collect only what is strictly necessary. "
        "Build a consent management system with granular opt-in/opt-out. "
        "Provide user data export and deletion endpoints. "
        "Conduct a Privacy Impact Assessment before any public launch."
    ),
    RiskCategory.FILE_STORAGE: (
        "Use cloud object storage with server-side encryption. "
        "Implement file type validation and maximum size enforcement at ingestion. "
        "Scan all uploads for malware before making them accessible. "
        "Apply per-user access controls and signed URL expiry for private assets."
    ),
    RiskCategory.MAPS: (
        "Select a maps provider with sufficient API quotas for your traffic projection. "
        "Implement caching for repeated map tile and geocoding requests. "
        "Design a fallback strategy for when the provider API is unavailable."
    ),
    RiskCategory.NOTIFICATIONS: (
        "Use a dedicated notification service with delivery tracking. "
        "Build user notification preference management from Sprint 1. "
        "Monitor delivery rates and implement failure fallbacks for critical alerts."
    ),
    RiskCategory.THIRD_PARTY_INTEGRATIONS: (
        "Isolate every third-party integration behind an abstraction layer. "
        "Implement circuit breakers to prevent cascading failures. "
        "Monitor integration health and design graceful degradation paths."
    ),
}

# General recommendations appended after risk-specific ones.
_TYPE_RECOMMENDATIONS: Dict[ProjectType, List[str]] = {
    ProjectType.SAAS: [
        "Define API contracts between all frontend and backend services before implementation.",
        "Design the multi-tenant data isolation strategy before writing a single database query.",
    ],
    ProjectType.WEB_PLATFORM: [
        "Define API contracts between all frontend and backend services before implementation.",
        "Establish a content moderation and abuse prevention strategy before accepting user-generated content.",
    ],
    ProjectType.MOBILE_APP: [
        "Validate the app design with usability testing on physical devices before Sprint 3.",
        "Plan App Store submission timelines early — review processes can add 1–2 weeks.",
    ],
    ProjectType.AUTOMATION: [
        "Make every automated task idempotent so it can safely be retried on failure.",
        "Implement a dead-letter queue for failed jobs and an alerting policy for repeated failures.",
    ],
    ProjectType.DESKTOP_APP: [
        "Agree on target OS versions (Windows, macOS, Linux) in Sprint 1 — late changes are expensive.",
        "Plan the auto-update mechanism before shipping; retrofitting it disrupts the distribution model.",
    ],
    ProjectType.AI_TOOL: [
        "Establish accuracy and quality benchmarks before writing any AI integration code.",
        "Build a human-review path for low-confidence AI outputs before trusting them in production.",
    ],
    ProjectType.API: [
        "Publish an OpenAPI specification before writing any endpoint implementation.",
        "Version the API from Sprint 1 — breaking changes are far more expensive after clients exist.",
    ],
    ProjectType.ECOMMERCE: [
        "Validate the checkout flow with real users before any payment integration goes live.",
        "Define the inventory management strategy before building the product catalog.",
    ],
    ProjectType.DATA_PIPELINE: [
        "Define data quality contracts (schemas, nullability, cardinality) before pipeline implementation.",
        "Build observability into the pipeline from the start: record row counts, error rates, and latency.",
    ],
    ProjectType.GAME: [
        "Prototype core gameplay mechanics in Sprint 1 — fun cannot be added retroactively.",
        "Define the anti-cheat and fair-play policy before multiplayer features are built.",
    ],
}

# Universal recommendations always appended at the end, regardless of project type.
_UNIVERSAL_RECOMMENDATIONS: List[str] = [
    "Establish the CI/CD pipeline and automated test suite in Sprint 1 — do not defer infrastructure.",
    "Write acceptance criteria for every task before implementation begins.",
    "Schedule a formal security review at the project midpoint and before any public launch.",
]

# Leading words stripped when extracting the project title from a request.
_TITLE_STRIP_PREFIXES: Set[str] = {
    "build", "create", "make", "develop", "design", "implement",
    "deploy", "launch", "write", "code", "produce", "deliver", "ship",
    "a", "an", "the", "me", "us",
}

# Human-readable type context strings used in objective generation.
_TYPE_GOAL: Dict[ProjectType, str] = {
    ProjectType.SAAS: "delivering a complete SaaS product",
    ProjectType.WEB_PLATFORM: "building a production-ready web platform",
    ProjectType.MOBILE_APP: "shipping a polished mobile application",
    ProjectType.AUTOMATION: "deploying a reliable automation system",
    ProjectType.DESKTOP_APP: "releasing a native desktop application",
    ProjectType.AI_TOOL: "launching an AI-powered tool",
    ProjectType.API: "publishing a robust API service",
    ProjectType.ECOMMERCE: "launching a fully functional e-commerce platform",
    ProjectType.DATA_PIPELINE: "operating a reliable data pipeline",
    ProjectType.GAME: "shipping a complete game experience",
}

# Descriptive strings used in the blueprint description field.
_TYPE_DESCRIPTION_CONTEXT: Dict[ProjectType, str] = {
    ProjectType.SAAS: (
        "a software-as-a-service application with multi-tenant architecture, "
        "subscription management, and continuous delivery"
    ),
    ProjectType.WEB_PLATFORM: (
        "a web-based platform accessible via modern browsers, designed for "
        "scalability and performance under real-world user load"
    ),
    ProjectType.MOBILE_APP: (
        "a mobile application targeting smartphone and tablet users, "
        "optimized for performance and platform-native interaction patterns"
    ),
    ProjectType.AUTOMATION: (
        "an automation system that executes scheduled or event-driven workflows "
        "reliably and without manual intervention"
    ),
    ProjectType.DESKTOP_APP: (
        "a native desktop application providing deep OS integration, "
        "offline capability, and a platform-appropriate user experience"
    ),
    ProjectType.AI_TOOL: (
        "an AI-powered tool that integrates intelligence capabilities into "
        "a user-facing product with quality-controlled, observable outputs"
    ),
    ProjectType.API: (
        "a well-documented, versioned API service providing reliable, "
        "performant access to business logic for internal and external consumers"
    ),
    ProjectType.ECOMMERCE: (
        "a full-featured e-commerce platform covering product discovery, "
        "cart, checkout, order management, and post-purchase experience"
    ),
    ProjectType.DATA_PIPELINE: (
        "a data pipeline system for ingesting, transforming, and delivering "
        "reliable data to downstream consumers at the required cadence"
    ),
    ProjectType.GAME: (
        "a game experience built around a defined core loop, "
        "delivered across target platforms with multiplayer or progression systems"
    ),
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RequestAnalysisError(Exception):
    """Raised when a CEO request cannot be analyzed by the Planner Engine."""


# ---------------------------------------------------------------------------
# Planner Engine
# ---------------------------------------------------------------------------

class PlannerEngine:
    """
    Deterministic planning engine for AI Company OS.

    Receives a free-text CEO request and produces a structured ProjectBlueprint
    through a pipeline of keyword scoring, rule-based inference, and lookup-table
    estimation. No external services, AI models, or randomness are used.

    The engine is stateless — every call to analyze() operates independently
    and can be called any number of times on the same instance.

    Architecture reference: §2.1 Executive Engine, §3 Layer 5 (Coordination).
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, request: str) -> ProjectBlueprint:
        """
        Analyze a CEO request and produce a deterministic ProjectBlueprint.

        This is the single entry point for all planning operations. The
        analysis pipeline runs in strict order:

        1. Validate and normalize the request.
        2. Detect the project type via keyword scoring.
        3. Detect technical risks via keyword matching.
        4. Determine required departments from type + risks + keywords.
        5. Compute the complexity score.
        6. Estimate sprint count, team size, and task count.
        7. Generate ordered recommendations.
        8. Assemble and return the ProjectBlueprint.

        Args:
            request: Free-text description of what the CEO wants to build.
                Must be at least 10 characters long.

        Returns:
            A fully populated ProjectBlueprint ready for handoff to the
            Executive Engine.

        Raises:
            RequestAnalysisError: If the request is empty, too short, or
                consists entirely of whitespace.
        """
        self._validate(request)

        normalized = self._normalize(request)
        title = self._extract_title(request)
        project_type = self._detect_project_type(normalized)
        risks = self._detect_risks(normalized)
        departments = self._detect_departments(normalized, project_type, risks)
        complexity = self._compute_complexity(project_type, risks)
        sprint_count = self._estimate_sprints(complexity)
        team_size = self._estimate_team(departments)
        task_count = self._estimate_tasks(sprint_count, team_size)
        recommendations = self._generate_recommendations(project_type, risks)
        objective = self._generate_objective(title, project_type)
        description = self._generate_description(project_type, departments, risks)

        return ProjectBlueprint(
            project_title=title,
            objective=objective,
            description=description,
            project_type=project_type,
            departments=departments,
            estimated_task_count=task_count,
            estimated_sprint_count=sprint_count,
            estimated_team_size=team_size,
            complexity_score=complexity,
            risks=risks,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc),
            raw_request=request.strip(),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self, request: str) -> None:
        """
        Raise RequestAnalysisError if the request is not analyzable.

        Args:
            request: The raw CEO request string.

        Raises:
            RequestAnalysisError: If request is empty, whitespace-only,
                or shorter than 10 characters after stripping.
        """
        if not request or not request.strip():
            raise RequestAnalysisError(
                "The CEO request is empty. Provide a description of what to build."
            )
        if len(request.strip()) < 10:
            raise RequestAnalysisError(
                f"The CEO request is too short to analyze "
                f"({len(request.strip())} characters). "
                "Provide at least a brief description of the project."
            )

    # ------------------------------------------------------------------
    # Text processing
    # ------------------------------------------------------------------

    def _normalize(self, request: str) -> str:
        """
        Return a lowercase, whitespace-normalized version of the request.

        Args:
            request: The raw CEO request string.

        Returns:
            Normalized string suitable for keyword matching.
        """
        return " ".join(request.lower().split())

    def _extract_title(self, request: str) -> str:
        """
        Extract a professional project title from the raw CEO request.

        Strips leading action verbs ("Build", "Create", "Make") and articles
        ("a", "an", "the"), then title-cases the remainder while preserving
        existing capitalization on proper nouns and acronyms.

        Args:
            request: The raw CEO request string.

        Returns:
            A concise title string. Falls back to title-casing the full
            request if nothing can be stripped.
        """
        text = request.strip().rstrip(".!?")
        words = text.split()
        while words and words[0].lower() in _TITLE_STRIP_PREFIXES:
            words = words[1:]
        if not words:
            return request.strip().title()
        return " ".join(self._capitalize_title_word(w) for w in words)

    def _capitalize_title_word(self, word: str) -> str:
        """
        Capitalize a single word for use in a project title.

        Preserves hyphenated compound words by capitalizing only the first
        component. Preserves words that already contain interior uppercase
        letters (e.g. "iOS", "JavaScript", "Netflix-like").

        Args:
            word: A single word from the title.

        Returns:
            The capitalized word.
        """
        if "-" in word:
            parts = word.split("-", 1)
            return parts[0].capitalize() + "-" + parts[1]
        if any(c.isupper() for c in word[1:]):
            return word
        return word.capitalize()

    # ------------------------------------------------------------------
    # Project type detection
    # ------------------------------------------------------------------

    def _detect_project_type(self, normalized: str) -> ProjectType:
        """
        Score all project types against the normalized request and return
        the best match.

        Each type's keyword signals are counted as substring matches in the
        normalized request. The type with the highest total score wins. Ties
        are resolved by the priority order defined in _TYPE_PRIORITY.

        Args:
            normalized: The lowercase, normalized CEO request.

        Returns:
            The detected ProjectType. Defaults to WEB_PLATFORM when no
            signals match.
        """
        scores: Dict[ProjectType, int] = {pt: 0 for pt in ProjectType}
        for project_type, signals in _PROJECT_TYPE_SIGNALS.items():
            for signal in signals:
                if signal in normalized:
                    scores[project_type] += 1

        best_score = max(scores.values())
        if best_score == 0:
            return ProjectType.WEB_PLATFORM

        # Among all types that share the highest score, pick by priority.
        for project_type in _TYPE_PRIORITY:
            if scores[project_type] == best_score:
                return project_type

        return ProjectType.WEB_PLATFORM

    # ------------------------------------------------------------------
    # Risk detection
    # ------------------------------------------------------------------

    def _detect_risks(self, normalized: str) -> List[Risk]:
        """
        Identify technical risks from the normalized request via keyword matching.

        Each risk category has a set of keyword signals. A risk is recorded
        when at least one signal appears in the normalized request. Risks are
        returned sorted by severity (CRITICAL first, then HIGH, MEDIUM, LOW).

        No risk category is reported more than once.

        Args:
            normalized: The lowercase, normalized CEO request.

        Returns:
            Ordered list of Risk objects. Empty if no risk signals are found.
        """
        level_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        detected: Dict[RiskLevel, List[Risk]] = {level: [] for level in level_order}

        for category, (signals, level, description) in _RISK_DEFINITIONS.items():
            if any(signal in normalized for signal in signals):
                detected[level].append(Risk(category=category, level=level, description=description))

        result: List[Risk] = []
        for level in level_order:
            result.extend(detected[level])
        return result

    # ------------------------------------------------------------------
    # Department detection
    # ------------------------------------------------------------------

    def _detect_departments(
        self,
        normalized: str,
        project_type: ProjectType,
        risks: List[Risk],
    ) -> List[DepartmentRequirement]:
        """
        Determine the full set of required departments for this project.

        The selection follows a three-pass process:

        Pass 1 — Base departments: always required for this project type.
        Pass 2 — Risk-driven departments: added when specific risks are present
            (e.g., AUTHENTICATION risk → Security department).
        Pass 3 — Consumer-platform and keyword-driven departments: Marketing
            for consumer-facing types; Legal when streaming/content keywords
            are present; and other keyword-driven additions.

        Each department appears at most once. If a department would be added
        by multiple passes, the first pass that adds it wins.

        Args:
            normalized: The lowercase, normalized CEO request.
            project_type: The detected project type (used for base selection).
            risks: The detected risk list (used for risk-driven additions).

        Returns:
            Ordered list of DepartmentRequirement objects.
        """
        seen: Set[Department] = set()
        result: List[DepartmentRequirement] = []

        def _add(dept: Department, rationale: str, is_critical: bool) -> None:
            if dept not in seen:
                seen.add(dept)
                result.append(DepartmentRequirement(
                    department=dept,
                    rationale=rationale,
                    is_critical=is_critical,
                ))

        # Pass 1: base departments for this project type.
        base = _BASE_DEPARTMENTS.get(project_type, _BASE_DEPARTMENTS[ProjectType.WEB_PLATFORM])
        for dept, rationale, is_critical in base:
            _add(dept, rationale, is_critical)

        # Pass 2: risk-driven department additions.
        risk_categories = {r.category for r in risks}
        for risk_cat, dept, rationale, is_critical in _RISK_DRIVEN_DEPARTMENTS:
            if risk_cat in risk_categories:
                _add(dept, rationale, is_critical)

        # Pass 3a: Marketing for consumer-facing project types.
        if project_type in _CONSUMER_PROJECT_TYPES:
            _add(
                Department.MARKETING,
                "User acquisition strategy, brand positioning, and growth campaigns.",
                False,
            )

        # Pass 3b: keyword-driven department additions.
        for signals, dept, rationale, is_critical in _KEYWORD_DRIVEN_DEPARTMENTS:
            if any(sig in normalized for sig in signals):
                _add(dept, rationale, is_critical)

        return result

    # ------------------------------------------------------------------
    # Complexity and estimation
    # ------------------------------------------------------------------

    def _compute_complexity(self, project_type: ProjectType, risks: List[Risk]) -> int:
        """
        Compute a complexity score from 1 (trivial) to 10 (maximum).

        The score starts from the project-type baseline and increases by the
        sum of risk severity weights (CRITICAL: +2, HIGH: +1, MEDIUM/LOW: +0).
        The result is clamped to the [1, 10] range.

        Args:
            project_type: The detected project type.
            risks: All detected risks for this project.

        Returns:
            Integer complexity score in the range [1, 10].
        """
        base = _BASE_COMPLEXITY.get(project_type, 5)
        risk_penalty = sum(_RISK_WEIGHTS[r.level] for r in risks)
        return min(10, max(1, base + risk_penalty))

    def _estimate_sprints(self, complexity: int) -> int:
        """
        Estimate the number of two-week sprints from a complexity score.

        Uses a fixed lookup table so the same complexity always produces
        the same sprint estimate.

        Args:
            complexity: Integer score in [1, 10].

        Returns:
            Estimated sprint count (always a positive integer).
        """
        return _SPRINT_TABLE.get(complexity, 24)

    def _estimate_team(self, departments: List[DepartmentRequirement]) -> int:
        """
        Estimate the peak team size from the required department count.

        Formula: department_count + 2 (to account for cross-cutting roles
        such as the Executive AI and a project lead). Minimum of 3.

        Args:
            departments: All required departments for this project.

        Returns:
            Estimated team size (minimum 3).
        """
        return max(3, len(departments) + 2)

    def _estimate_tasks(self, sprint_count: int, team_size: int) -> int:
        """
        Estimate the total task count for the project.

        Formula: sprint_count × team_size. This models the rough principle
        that each agent contributes approximately one CEO-level task per
        sprint on average.

        Args:
            sprint_count: Estimated number of sprints.
            team_size: Estimated number of active agents.

        Returns:
            Estimated total task count (always positive).
        """
        return sprint_count * team_size

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------

    def _generate_objective(self, title: str, project_type: ProjectType) -> str:
        """
        Generate a structured, single-sentence project objective.

        Args:
            title: The extracted project title.
            project_type: The detected project type.

        Returns:
            A professional objective statement suitable for inclusion in
            governance documents and CEO review requests.
        """
        goal = _TYPE_GOAL.get(project_type, "completing a software project")
        return (
            f"Achieve {goal} — {title} — meeting professional quality standards, "
            "passing all QA requirements, and receiving CEO approval before "
            "any external deployment or publication."
        )

    def _generate_description(
        self,
        project_type: ProjectType,
        departments: List[DepartmentRequirement],
        risks: List[Risk],
    ) -> str:
        """
        Generate a paragraph-length description of the project scope.

        Combines the project type context, the engaged departments, and
        the identified risk areas into a concise, professional statement.

        Args:
            project_type: The detected project type.
            departments: All required departments.
            risks: All detected risks.

        Returns:
            A multi-sentence description string.
        """
        type_context = _TYPE_DESCRIPTION_CONTEXT.get(
            project_type,
            "a software system meeting the CEO's specified requirements",
        )
        dept_names = ", ".join(d.department.value for d in departments)
        high_risks = [r for r in risks if r.level in (RiskLevel.CRITICAL, RiskLevel.HIGH)]
        risk_clause = ""
        if high_risks:
            risk_names = ", ".join(r.category.value for r in high_risks[:4])
            risk_clause = (
                f" Primary technical challenges identified during analysis: "
                f"{risk_names}."
            )
        return (
            f"This project delivers {type_context}. "
            f"The scope engages {len(departments)} functional departments: "
            f"{dept_names}.{risk_clause}"
        )

    def _generate_recommendations(
        self,
        project_type: ProjectType,
        risks: List[Risk],
    ) -> List[str]:
        """
        Generate an ordered, deduplicated list of actionable recommendations.

        Recommendations are collected in three passes:
        1. Risk-specific recommendations, ordered by severity (CRITICAL first).
        2. Project-type specific recommendations.
        3. Universal recommendations always appended at the end.

        Args:
            project_type: The detected project type.
            risks: All detected risks.

        Returns:
            Ordered list of recommendation strings. Empty strings are excluded.
        """
        seen: Set[str] = set()
        result: List[str] = []

        def _add_rec(text: str) -> None:
            if text and text not in seen:
                seen.add(text)
                result.append(text)

        # Pass 1: risk-specific recommendations, highest severity first.
        for risk in risks:
            rec = _RISK_RECOMMENDATIONS.get(risk.category)
            if rec:
                _add_rec(rec)

        # Pass 2: project-type specific recommendations.
        for rec in _TYPE_RECOMMENDATIONS.get(project_type, []):
            _add_rec(rec)

        # Pass 3: universal recommendations.
        for rec in _UNIVERSAL_RECOMMENDATIONS:
            _add_rec(rec)

        return result
