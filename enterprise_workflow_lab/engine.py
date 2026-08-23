from __future__ import annotations

from enterprise_workflow_lab.models import ApprovalDecision, AuditEvent, Role, Status, WorkflowRequest
from enterprise_workflow_lab.policies import GATE_BY_STATUS, TERMINAL_STATUSES


class WorkflowError(ValueError):
    """Raised when a workflow transition breaks the governance rules."""


class WorkflowEngine:
    def submit(self, request: WorkflowRequest, actor: str, role: Role, rationale: str) -> WorkflowRequest:
        if request.status != Status.DRAFT:
            raise WorkflowError("Only draft requests can be submitted.")
        if role != Role.REQUESTER:
            raise WorkflowError("Only a requester can submit the request.")
        return self._transition(request, actor, role, "submit", Status.SUBMITTED, rationale)

    def begin_review(self, request: WorkflowRequest, actor: str, role: Role, rationale: str) -> WorkflowRequest:
        if request.status != Status.SUBMITTED:
            raise WorkflowError("Only submitted requests can enter department review.")
        if role != Role.DEPARTMENT_OWNER:
            raise WorkflowError("A department owner must begin review.")
        return self._transition(request, actor, role, "begin_department_review", Status.DEPARTMENT_REVIEW, rationale)

    def decide(self, request: WorkflowRequest, decision: ApprovalDecision) -> WorkflowRequest:
        self._ensure_active(request)
        gate = GATE_BY_STATUS.get(request.status)
        if gate is None:
            raise WorkflowError(f"No approval gate is configured for status '{request.status}'.")
        if decision.role != gate.required_role:
            raise WorkflowError(f"Status '{request.status}' requires role '{gate.required_role}'.")

        next_status = gate.approved_status if decision.approved else Status.REJECTED
        action = "approve" if decision.approved else "reject"
        request.decisions.append(decision)
        return self._transition(request, decision.approver, decision.role, action, next_status, decision.rationale)

    def mark_implemented(self, request: WorkflowRequest, actor: str, role: Role, rationale: str) -> WorkflowRequest:
        if request.status != Status.APPROVED:
            raise WorkflowError("Only approved requests can be marked implemented.")
        if role != Role.IMPLEMENTATION_OWNER:
            raise WorkflowError("Only the implementation owner can mark implementation complete.")
        return self._transition(request, actor, role, "mark_implemented", Status.IMPLEMENTED, rationale)

    def close(self, request: WorkflowRequest, actor: str, role: Role, rationale: str) -> WorkflowRequest:
        if request.status != Status.IMPLEMENTED:
            raise WorkflowError("Only implemented requests can be closed.")
        if role != Role.TRANSFORMATION_LEAD:
            raise WorkflowError("Only the transformation lead can close the workflow.")
        return self._transition(request, actor, role, "close", Status.CLOSED, rationale)

    def _transition(
        self,
        request: WorkflowRequest,
        actor: str,
        role: Role,
        action: str,
        to_status: Status,
        rationale: str,
    ) -> WorkflowRequest:
        from_status = request.status
        request.status = to_status
        request.audit_log.append(
            AuditEvent(
                actor=actor,
                role=role,
                action=action,
                from_status=from_status,
                to_status=to_status,
                rationale=rationale,
            )
        )
        return request

    @staticmethod
    def _ensure_active(request: WorkflowRequest) -> None:
        if request.status in TERMINAL_STATUSES:
            raise WorkflowError(f"Request is already terminal: {request.status}.")
