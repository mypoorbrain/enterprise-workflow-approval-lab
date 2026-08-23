from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class Role(StrEnum):
    REQUESTER = "requester"
    DEPARTMENT_OWNER = "department_owner"
    FINANCE_CONTROLLER = "finance_controller"
    IT_REVIEWER = "it_reviewer"
    TRANSFORMATION_LEAD = "transformation_lead"
    IMPLEMENTATION_OWNER = "implementation_owner"


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    DEPARTMENT_REVIEW = "department_review"
    FINANCE_REVIEW = "finance_review"
    IT_REVIEW = "it_review"
    TRANSFORMATION_REVIEW = "transformation_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"


@dataclass(frozen=True)
class ApprovalDecision:
    role: Role
    approver: str
    rationale: str
    approved: bool = True


@dataclass(frozen=True)
class AuditEvent:
    actor: str
    role: Role
    action: str
    from_status: Status
    to_status: Status
    rationale: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class WorkflowRequest:
    request_id: str
    title: str
    business_unit: str
    requester: str
    value_band: str
    risk_level: str
    systems_impacted: list[str]
    business_reason: str
    status: Status = Status.DRAFT
    decisions: list[ApprovalDecision] = field(default_factory=list)
    audit_log: list[AuditEvent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "WorkflowRequest":
        return cls(
            request_id=payload["request_id"],
            title=payload["title"],
            business_unit=payload["business_unit"],
            requester=payload["requester"],
            value_band=payload["value_band"],
            risk_level=payload["risk_level"],
            systems_impacted=list(payload["systems_impacted"]),
            business_reason=payload["business_reason"],
        )
