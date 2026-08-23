from __future__ import annotations

from typing import Any

from enterprise_workflow_lab.models import ApprovalDecision, AuditEvent, Role, Status, WorkflowRequest
from enterprise_workflow_lab.policies import (
    REQUIRED_READINESS_CHECKS,
    SLA_DAYS_BY_STATUS,
    TERMINAL_STATUSES,
    approval_route_for,
    gate_for_status,
    next_status_after_approval,
)


class WorkflowError(ValueError):
    """Raised when a workflow transition breaks the governance rules."""


class WorkflowEngine:
    def submit(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        rationale: str,
        business_day: int | None = None,
    ) -> WorkflowRequest:
        if request.status != Status.DRAFT:
            raise WorkflowError("Only draft requests can be submitted.")
        if role != Role.REQUESTER:
            raise WorkflowError("Only a requester can submit the request.")
        return self._transition(request, actor, role, "submit", Status.SUBMITTED, rationale, business_day)

    def begin_review(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        rationale: str,
        business_day: int | None = None,
    ) -> WorkflowRequest:
        self._ensure_active(request)
        if request.status != Status.SUBMITTED:
            raise WorkflowError("Only submitted requests can enter department review.")
        if role != Role.DEPARTMENT_OWNER:
            raise WorkflowError("A department owner must begin review.")
        return self._transition(
            request,
            actor,
            role,
            "begin_department_review",
            Status.DEPARTMENT_REVIEW,
            rationale,
            business_day,
        )

    def decide(
        self,
        request: WorkflowRequest,
        decision: ApprovalDecision,
        business_day: int | None = None,
    ) -> WorkflowRequest:
        self._ensure_active(request)
        gate = gate_for_status(request, request.status)
        if gate is None:
            raise WorkflowError(f"No approval gate is configured for status '{request.status}'.")
        if decision.role != gate.required_role:
            raise WorkflowError(f"Status '{request.status}' requires role '{gate.required_role}'.")
        if decision.approved and decision.requires_changes:
            raise WorkflowError("An approved decision cannot also request changes.")

        if decision.approved:
            next_status = next_status_after_approval(request, request.status)
            action = "approve"
        elif decision.requires_changes:
            next_status = Status.CHANGES_REQUESTED
            action = "request_changes"
        else:
            next_status = Status.REJECTED
            action = "reject"

        request.decisions.append(decision)
        return self._transition(request, decision.approver, decision.role, action, next_status, decision.rationale, business_day)

    def revise(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        rationale: str,
        business_day: int | None = None,
    ) -> WorkflowRequest:
        self._ensure_active(request)
        if request.status != Status.CHANGES_REQUESTED:
            raise WorkflowError("Only change-requested workflows can be revised.")
        if role != Role.REQUESTER:
            raise WorkflowError("Only the requester can resubmit changes.")
        request.resubmission_count += 1
        return self._transition(request, actor, role, "resubmit_changes", Status.SUBMITTED, rationale, business_day)

    def confirm_readiness(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        rationale: str,
        checks: dict[str, bool],
        business_day: int | None = None,
    ) -> WorkflowRequest:
        self._ensure_active(request)
        if request.status != Status.APPROVED:
            raise WorkflowError("Only approved requests can enter implementation readiness.")
        if role != Role.IMPLEMENTATION_OWNER:
            raise WorkflowError("Only the implementation owner can confirm readiness.")
        missing = REQUIRED_READINESS_CHECKS.difference(checks)
        if missing:
            raise WorkflowError(f"Missing readiness checks: {', '.join(sorted(missing))}.")
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise WorkflowError(f"Readiness checks failed: {', '.join(sorted(failed))}.")
        request.readiness_checks = dict(checks)
        return self._transition(
            request,
            actor,
            role,
            "confirm_readiness",
            Status.IMPLEMENTATION_READY,
            rationale,
            business_day,
        )

    def mark_implemented(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        rationale: str,
        business_day: int | None = None,
    ) -> WorkflowRequest:
        self._ensure_active(request)
        if request.status != Status.IMPLEMENTATION_READY:
            raise WorkflowError("Only implementation-ready requests can be marked implemented.")
        if role != Role.IMPLEMENTATION_OWNER:
            raise WorkflowError("Only the implementation owner can mark implementation complete.")
        return self._transition(request, actor, role, "mark_implemented", Status.IMPLEMENTED, rationale, business_day)

    def close(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        rationale: str,
        business_day: int | None = None,
    ) -> WorkflowRequest:
        self._ensure_active(request)
        if request.status != Status.IMPLEMENTED:
            raise WorkflowError("Only implemented requests can be closed.")
        if role != Role.TRANSFORMATION_LEAD:
            raise WorkflowError("Only the transformation lead can close the workflow.")
        return self._transition(request, actor, role, "close", Status.CLOSED, rationale, business_day)

    def sla_snapshot(self, request: WorkflowRequest) -> dict[str, Any]:
        if request.status in TERMINAL_STATUSES:
            return {
                "status": request.status,
                "stage_age_days": 0,
                "sla_days": 0,
                "days_to_due": 0,
                "is_overdue": False,
                "escalation_level": "closed",
                "route": approval_route_for(request),
            }
        stage_started_day = request.audit_log[-1].business_day if request.audit_log else 0
        stage_age = max(0, request.current_day - stage_started_day)
        sla_days = SLA_DAYS_BY_STATUS.get(request.status, 0)
        days_to_due = sla_days - stage_age
        is_overdue = sla_days > 0 and stage_age > sla_days
        if is_overdue:
            escalation_level = "escalate" if stage_age >= sla_days + 2 else "overdue"
        elif sla_days > 0 and days_to_due <= 1:
            escalation_level = "watch"
        else:
            escalation_level = "on_track"
        return {
            "status": request.status,
            "stage_age_days": stage_age,
            "sla_days": sla_days,
            "days_to_due": days_to_due,
            "is_overdue": is_overdue,
            "escalation_level": escalation_level,
            "route": approval_route_for(request),
        }

    def _transition(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        action: str,
        to_status: Status,
        rationale: str,
        business_day: int | None,
    ) -> WorkflowRequest:
        if request.status in TERMINAL_STATUSES:
            raise WorkflowError(f"Request is already terminal: {request.status}.")
        if not rationale.strip():
            raise WorkflowError("A transition rationale is required.")
        if business_day is None:
            business_day = request.current_day + 1
        if business_day < request.current_day:
            raise WorkflowError("Business day cannot move backwards.")

        from_status = request.status
        request.current_day = business_day
        request.status = to_status
        request.audit_log.append(
            AuditEvent(
                actor=actor,
                role=role,
                action=action,
                from_status=from_status,
                to_status=to_status,
                rationale=rationale,
                business_day=business_day,
            )
        )
        return request

    @staticmethod
    def _ensure_active(request: WorkflowRequest) -> None:
        if request.status in TERMINAL_STATUSES:
            raise WorkflowError(f"Request is already terminal: {request.status}.")
