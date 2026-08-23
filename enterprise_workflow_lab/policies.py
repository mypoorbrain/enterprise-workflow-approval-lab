from __future__ import annotations

from dataclasses import dataclass

from enterprise_workflow_lab.models import Role, Status, WorkflowRequest


@dataclass(frozen=True)
class ApprovalGate:
    current_status: Status
    required_role: Role
    decision_focus: str


BASE_GATES: dict[Status, ApprovalGate] = {
    Status.DEPARTMENT_REVIEW: ApprovalGate(
        Status.DEPARTMENT_REVIEW,
        Role.DEPARTMENT_OWNER,
        "Business ownership, adoption readiness and process fit.",
    ),
    Status.FINANCE_REVIEW: ApprovalGate(
        Status.FINANCE_REVIEW,
        Role.FINANCE_CONTROLLER,
        "Budget impact, value proxy, control exposure and commercial risk.",
    ),
    Status.IT_REVIEW: ApprovalGate(
        Status.IT_REVIEW,
        Role.IT_REVIEWER,
        "Systems impact, data, integration, security and supportability.",
    ),
    Status.TRANSFORMATION_REVIEW: ApprovalGate(
        Status.TRANSFORMATION_REVIEW,
        Role.TRANSFORMATION_LEAD,
        "Roadmap fit, delivery governance, release readiness and handover path.",
    ),
}

TERMINAL_STATUSES = {Status.REJECTED, Status.CLOSED}
REQUIRED_READINESS_CHECKS = {
    "uat_signed_off",
    "rollback_plan",
    "owner_handover",
    "support_model",
}
SLA_DAYS_BY_STATUS = {
    Status.SUBMITTED: 2,
    Status.DEPARTMENT_REVIEW: 3,
    Status.FINANCE_REVIEW: 2,
    Status.IT_REVIEW: 3,
    Status.TRANSFORMATION_REVIEW: 2,
    Status.CHANGES_REQUESTED: 4,
    Status.APPROVED: 3,
    Status.IMPLEMENTATION_READY: 5,
    Status.IMPLEMENTED: 2,
}


def approval_route_for(request: WorkflowRequest) -> list[Status]:
    route = [Status.DEPARTMENT_REVIEW]
    if request.value_band in {"medium", "high"} or request.request_class in {"procurement_change", "controlled_change"}:
        route.append(Status.FINANCE_REVIEW)
    if request.systems_impacted:
        route.append(Status.IT_REVIEW)
    if (
        request.risk_level in {"moderate", "high", "critical"}
        or request.value_band == "high"
        or len(request.systems_impacted) > 1
        or request.request_class in {"cross_functional_change", "controlled_change"}
    ):
        route.append(Status.TRANSFORMATION_REVIEW)
    return route


def gate_for_status(request: WorkflowRequest, status: Status) -> ApprovalGate | None:
    if status not in approval_route_for(request):
        return None
    return BASE_GATES[status]


def next_status_after_approval(request: WorkflowRequest, status: Status) -> Status:
    route = approval_route_for(request)
    if status not in route:
        raise ValueError(f"Status '{status}' is not in the configured route.")
    index = route.index(status)
    if index == len(route) - 1:
        return Status.APPROVED
    return route[index + 1]
