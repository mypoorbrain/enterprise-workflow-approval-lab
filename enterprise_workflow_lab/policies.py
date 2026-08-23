from __future__ import annotations

from dataclasses import dataclass

from enterprise_workflow_lab.models import Role, Status


@dataclass(frozen=True)
class ApprovalGate:
    current_status: Status
    required_role: Role
    approved_status: Status


APPROVAL_GATES: tuple[ApprovalGate, ...] = (
    ApprovalGate(Status.DEPARTMENT_REVIEW, Role.DEPARTMENT_OWNER, Status.FINANCE_REVIEW),
    ApprovalGate(Status.FINANCE_REVIEW, Role.FINANCE_CONTROLLER, Status.IT_REVIEW),
    ApprovalGate(Status.IT_REVIEW, Role.IT_REVIEWER, Status.TRANSFORMATION_REVIEW),
    ApprovalGate(Status.TRANSFORMATION_REVIEW, Role.TRANSFORMATION_LEAD, Status.APPROVED),
)

GATE_BY_STATUS = {gate.current_status: gate for gate in APPROVAL_GATES}

TERMINAL_STATUSES = {Status.REJECTED, Status.CLOSED}
