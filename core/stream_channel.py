"""
Stream channel definitions for AI Company OS Event Stream.

A StreamChannel identifies the logical topic area that a StreamEvent belongs
to. Every published event is assigned to exactly one channel. Subscribers
declare which channels they want to receive events from.

Channel design follows the architectural layers defined in §3 and the event
categories listed in §10 of the architecture document.

Architecture reference: §2.8 Event Bus, §10 Event Flow,
§3 Layer 3 (Infrastructure Layer).
"""

from enum import Enum


class StreamChannel(str, Enum):
    """
    Enumeration of all channels available in the AI Company OS Event Stream.

    Each channel corresponds to a logical domain of the system. Publishers
    choose the channel that best describes where the event originated.
    Subscribers choose channels relevant to their responsibilities.

    Channels:
        SYSTEM     — Infrastructure events: startup, shutdown, health checks,
                     system errors. Published by the EventStream itself or
                     low-level infrastructure components.
        PROJECT    — Project lifecycle events: project created, analyzed,
                     completed, or failed. Published by the Planner and
                     Executive Engine.
        WORKFLOW   — Workflow Engine events: stage transitions, workflow
                     started, advanced, paused, completed, cancelled.
                     Published by the Workflow Engine.
        DISCUSSION — Discussion Engine events: discussions started,
                     contributions received, discussions closed, outcomes
                     recorded. Published by the Discussion Engine.
        MEMORY     — Memory Engine events: entries stored, retrieved,
                     updated, or archived. Published by the Memory Engine.
        DECISION   — Decision Engine events: decisions evaluated, options
                     scored, recommendations produced. Published by the
                     Decision Engine.
        RUNTIME    — Agent Runtime events: agents started, tasks executed,
                     sessions opened and closed. Published by the Agent
                     Runtime and Company Orchestrator.
        CEO        — CEO-directed events: approvals granted or rejected,
                     new directives issued. Published by the CEO Interface
                     and Governance Layer.
    """

    SYSTEM = "SYSTEM"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"
    DISCUSSION = "DISCUSSION"
    MEMORY = "MEMORY"
    DECISION = "DECISION"
    RUNTIME = "RUNTIME"
    CEO = "CEO"

    def __str__(self) -> str:
        return self.value

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def is_system_channel(self) -> bool:
        """Return True if this is the SYSTEM infrastructure channel."""
        return self == StreamChannel.SYSTEM

    def is_ceo_channel(self) -> bool:
        """Return True if this is the CEO governance channel."""
        return self == StreamChannel.CEO

    def is_operational_channel(self) -> bool:
        """
        Return True if this channel relates to active company operations.

        Operational channels: PROJECT, WORKFLOW, DISCUSSION, MEMORY,
        DECISION, RUNTIME. Excludes SYSTEM (infrastructure) and CEO
        (governance).
        """
        return self in {
            StreamChannel.PROJECT,
            StreamChannel.WORKFLOW,
            StreamChannel.DISCUSSION,
            StreamChannel.MEMORY,
            StreamChannel.DECISION,
            StreamChannel.RUNTIME,
        }

    def is_governance_channel(self) -> bool:
        """Return True if this channel relates to governance activity."""
        return self in {StreamChannel.CEO, StreamChannel.SYSTEM}

    def display_name(self) -> str:
        """Return a human-readable label for this channel."""
        return self.value.title()
