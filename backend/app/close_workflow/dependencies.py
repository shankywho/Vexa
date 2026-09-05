"""Deterministic task dependency resolver for close tasks (spec section 15).

Provides DAG validation, topological execution ordering, and dynamic evaluation
of ready vs. blocked tasks during workflow orchestration.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Mapping

from app.domain.enums import CloseTaskStatus, CloseTaskType

# Deterministic task dependency mapping (prerequisites required to start each task)
DEFAULT_TASK_DEPENDENCIES: dict[CloseTaskType, list[CloseTaskType]] = {
    CloseTaskType.INVOICE_VALIDATION: [],
    CloseTaskType.PAYMENT_RECONCILIATION: [CloseTaskType.INVOICE_VALIDATION],
    CloseTaskType.BANK_RECONCILIATION: [CloseTaskType.PAYMENT_RECONCILIATION],
    CloseTaskType.AP_RECONCILIATION: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.PAYMENT_RECONCILIATION,
    ],
    CloseTaskType.AR_RECONCILIATION: [CloseTaskType.BANK_RECONCILIATION],
    CloseTaskType.VARIANCE_ANALYSIS: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.PAYMENT_RECONCILIATION,
    ],
    CloseTaskType.ACCRUAL_REVIEW: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.AP_RECONCILIATION,
    ],
    CloseTaskType.EXCEPTION_REVIEW: [
        CloseTaskType.INVOICE_VALIDATION,
        CloseTaskType.PAYMENT_RECONCILIATION,
        CloseTaskType.BANK_RECONCILIATION,
        CloseTaskType.AP_RECONCILIATION,
        CloseTaskType.AR_RECONCILIATION,
        CloseTaskType.VARIANCE_ANALYSIS,
        CloseTaskType.ACCRUAL_REVIEW,
    ],
    CloseTaskType.FINAL_VERIFICATION: [CloseTaskType.EXCEPTION_REVIEW],
    CloseTaskType.CLOSE_PACKAGE: [CloseTaskType.FINAL_VERIFICATION],
}


class TaskDependencyResolver:
    """Evaluates and enforces task dependencies for close runs."""

    def __init__(
        self,
        dependencies: dict[CloseTaskType, list[CloseTaskType]] | None = None,
    ) -> None:
        self.dependencies = dependencies or DEFAULT_TASK_DEPENDENCIES
        self.validate_dag()

    def validate_dag(self) -> None:
        """Verify the task dependency graph is a valid Directed Acyclic Graph (no cycles)."""
        in_degree: dict[CloseTaskType, int] = {task: 0 for task in self.dependencies}
        adj: dict[CloseTaskType, list[CloseTaskType]] = defaultdict(list)

        for task, prereqs in self.dependencies.items():
            for p in prereqs:
                adj[p].append(task)
                in_degree[task] += 1

        queue = deque([task for task, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if visited_count != len(self.dependencies):
            raise ValueError(
                f"Cyclic dependency in close task DAG ({visited_count}/{len(self.dependencies)})"
            )

    def get_prerequisites(self, task_type: CloseTaskType) -> list[CloseTaskType]:
        """Return the direct prerequisites for a given task type."""
        return list(self.dependencies.get(task_type, []))

    def get_execution_order(self) -> list[CloseTaskType]:
        """Return a deterministic topological sort order of tasks."""
        in_degree: dict[CloseTaskType, int] = {task: 0 for task in self.dependencies}
        adj: dict[CloseTaskType, list[CloseTaskType]] = defaultdict(list)

        for task, prereqs in self.dependencies.items():
            for p in prereqs:
                adj[p].append(task)
                in_degree[task] += 1

        queue = deque([task for task, deg in in_degree.items() if deg == 0])
        ordered: list[CloseTaskType] = []

        while queue:
            curr = queue.popleft()
            ordered.append(curr)
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        return ordered

    def get_ready_tasks(
        self, task_statuses: Mapping[CloseTaskType, CloseTaskStatus]
    ) -> list[CloseTaskType]:
        """Return tasks that are in PENDING status and whose prerequisites are all COMPLETED."""
        ready: list[CloseTaskType] = []
        for task in self.get_execution_order():
            status = task_statuses.get(task, CloseTaskStatus.PENDING)
            if status != CloseTaskStatus.PENDING:
                continue

            prereqs = self.get_prerequisites(task)
            if all(task_statuses.get(p) == CloseTaskStatus.COMPLETED for p in prereqs):
                ready.append(task)
        return ready

    def get_blocked_tasks(
        self, task_statuses: Mapping[CloseTaskType, CloseTaskStatus]
    ) -> list[CloseTaskType]:
        """Return tasks that are PENDING but have at least one FAILED or BLOCKED prerequisite."""
        blocked: list[CloseTaskType] = []
        for task in self.get_execution_order():
            status = task_statuses.get(task, CloseTaskStatus.PENDING)
            if status != CloseTaskStatus.PENDING:
                continue

            prereqs = self.get_prerequisites(task)
            if any(
                task_statuses.get(p) in (CloseTaskStatus.FAILED, CloseTaskStatus.BLOCKED)
                for p in prereqs
            ):
                blocked.append(task)
        return blocked

    def get_downstream_dependents(self, task_type: CloseTaskType) -> set[CloseTaskType]:
        """Return all transitive downstream dependents of the given task."""
        dependents: set[CloseTaskType] = set()
        queue = deque([task_type])
        while queue:
            curr = queue.popleft()
            for t, prereqs in self.dependencies.items():
                if curr in prereqs and t not in dependents:
                    dependents.add(t)
                    queue.append(t)
        return dependents
