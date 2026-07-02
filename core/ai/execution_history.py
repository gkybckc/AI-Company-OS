"""
Execution History for AI Company OS Agent Executor.

The ExecutionHistory accumulates every ExecutionRecord produced by
AgentExecutor.execute(). It provides summary statistics and sequential
access to the full execution log.

Callers access the history via AgentExecutor.history() and
AgentExecutor.statistics(). Direct instantiation of ExecutionHistory
is for advanced use only.

Architecture reference: §2.10 LLM Gateway, §3 Layer 2 (Intelligence Layer).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.ai.execution_context import ExecutionContext
from core.ai.execution_result import ExecutionResult


# ---------------------------------------------------------------------------
# ExecutionRecord
# ---------------------------------------------------------------------------

@dataclass
class ExecutionRecord:
    """
    A single entry in the execution history.

    Bundles the context that triggered the execution with the result that
    was produced and a UTC timestamp of when the record was captured.

    Attributes:
        context:     The ExecutionContext that was passed to execute().
        result:      The ExecutionResult that was returned.
        recorded_at: UTC timestamp of when this record was created.
    """

    context: ExecutionContext
    result: ExecutionResult
    recorded_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict representation of this record."""
        return {
            "recorded_at": self.recorded_at.isoformat(),
            "context": self.context.to_dict(),
            "result": self.result.to_dict(),
        }

    def summary(self) -> str:
        """Return a one-line summary of this record."""
        ts = self.recorded_at.strftime("%H:%M:%S")
        ctx = self.context.summary()
        res = self.result.summary()
        return f"[{ts}] {ctx} -> {res}"


# ---------------------------------------------------------------------------
# ExecutionHistory
# ---------------------------------------------------------------------------

class ExecutionHistory:
    """
    Ordered log of every agent task execution.

    Records are appended by AgentExecutor after each execute() call.
    All reads return copies so callers cannot mutate the internal log.
    """

    def __init__(self) -> None:
        self._records: List[ExecutionRecord] = []

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        context: ExecutionContext,
        result: ExecutionResult,
    ) -> ExecutionRecord:
        """
        Append a new ExecutionRecord to the history.

        Args:
            context: The context that was executed.
            result:  The result that was produced.

        Returns:
            The newly created ExecutionRecord.
        """
        rec = ExecutionRecord(
            context=context,
            result=result,
            recorded_at=datetime.now(timezone.utc),
        )
        self._records.append(rec)
        return rec

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def all(self) -> List[ExecutionRecord]:
        """Return all records in execution order (oldest first)."""
        return list(self._records)

    def last(self) -> Optional[ExecutionRecord]:
        """Return the most recent record, or None if history is empty."""
        return self._records[-1] if self._records else None

    def count(self) -> int:
        """Return the total number of executions recorded."""
        return len(self._records)

    def successes(self) -> int:
        """Return the number of successful executions."""
        return sum(1 for r in self._records if r.result.success)

    def failures(self) -> int:
        """Return the number of failed executions."""
        return self.count() - self.successes()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """
        Return aggregate metrics over the full execution history.

        Returns a dict with keys:
            total, successes, failures, success_rate,
            avg_execution_time, total_artifacts, total_memory_entries,
            total_warnings, roles, departments, stages.
        """
        total = self.count()
        if total == 0:
            return {
                "total": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "total_artifacts": 0,
                "total_memory_entries": 0,
                "total_warnings": 0,
                "roles": [],
                "departments": [],
                "stages": [],
            }

        success_count = self.successes()
        total_time = sum(r.result.execution_time for r in self._records)
        total_artifacts = sum(r.result.artifact_count() for r in self._records)
        total_memory = sum(r.result.memory_count() for r in self._records)
        total_warnings = sum(r.result.warning_count() for r in self._records)

        roles = sorted({r.context.employee_role for r in self._records})
        departments = sorted({r.context.department for r in self._records})
        stages = sorted({r.context.workflow_stage for r in self._records})

        return {
            "total": total,
            "successes": success_count,
            "failures": total - success_count,
            "success_rate": round(success_count / total, 3),
            "avg_execution_time": round(total_time / total, 3),
            "total_artifacts": total_artifacts,
            "total_memory_entries": total_memory,
            "total_warnings": total_warnings,
            "roles": roles,
            "departments": departments,
            "stages": stages,
        }
