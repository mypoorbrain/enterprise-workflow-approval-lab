from __future__ import annotations

from enterprise_workflow_lab.engine import WorkflowEngine
from enterprise_workflow_lab.models import ApprovalDecision, Role, WorkflowRequest


def make_demo_request() -> WorkflowRequest:
    return WorkflowRequest(
        request_id="EWF-2026-001",
        title="Procurement-to-payment reporting improvement",
        business_unit="Operations",
        requester="Demo Requester",
        value_band="high",
        risk_level="moderate",
        request_class="controlled_change",
        target_release_day=20,
        systems_impacted=["workflow", "reporting", "finance"],
        business_reason="Reduce manual follow-up and improve management visibility over approval aging.",
    )


def make_low_risk_request() -> WorkflowRequest:
    return WorkflowRequest(
        request_id="EWF-2026-LOW",
        title="Department checklist refresh",
        business_unit="Service",
        requester="Service Requester",
        value_band="low",
        risk_level="low",
        request_class="policy_update",
        target_release_day=10,
        systems_impacted=[],
        business_reason="Refresh a local operating checklist without system changes.",
    )


def run_demo() -> WorkflowRequest:
    request = make_demo_request()
    engine = WorkflowEngine()
    engine.submit(request, "Demo Requester", Role.REQUESTER, "Business owner has prepared the request.", business_day=0)
    engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Request is ready for structured review.", business_day=1)
    engine.decide(
        request,
        ApprovalDecision(
            Role.DEPARTMENT_OWNER,
            "Department Owner",
            "Benefits are clear, but reporting ownership and UAT scope need clarification.",
            approved=False,
            requires_changes=True,
            decision_id="DEC-001",
            conditions=("Add named reporting owner", "Confirm UAT participants"),
        ),
        business_day=2,
    )
    engine.revise(
        request,
        "Demo Requester",
        Role.REQUESTER,
        "Added reporting owner, UAT participants and adoption note.",
        business_day=4,
    )
    engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Revised request is ready for approval.", business_day=5)
    engine.decide(
        request,
        ApprovalDecision(
            Role.DEPARTMENT_OWNER,
            "Department Owner",
            "Ownership, adoption path and operating value confirmed.",
            decision_id="DEC-002",
            conditions=("Operations owner assigned", "UAT participants confirmed"),
        ),
        business_day=6,
    )
    engine.decide(
        request,
        ApprovalDecision(
            Role.FINANCE_CONTROLLER,
            "Finance Controller",
            "Value proxy and control impact accepted for planned release.",
            decision_id="DEC-003",
            conditions=("No new vendor spend", "Finance report owner named"),
        ),
        business_day=8,
    )
    engine.decide(
        request,
        ApprovalDecision(
            Role.IT_REVIEWER,
            "IT Reviewer",
            "Systems impact is supportable with reporting access controlled by role.",
            decision_id="DEC-004",
            conditions=("Access group reviewed", "Rollback plan documented"),
        ),
        business_day=10,
    )
    engine.decide(
        request,
        ApprovalDecision(
            Role.TRANSFORMATION_LEAD,
            "Transformation Lead",
            "Roadmap fit confirmed and implementation can proceed under release governance.",
            decision_id="DEC-005",
            conditions=("Release window agreed", "Handover owner confirmed"),
        ),
        business_day=12,
    )
    engine.confirm_readiness(
        request,
        "Implementation Owner",
        Role.IMPLEMENTATION_OWNER,
        "Readiness gates passed for UAT, rollback, handover and support.",
        {
            "uat_signed_off": True,
            "rollback_plan": True,
            "owner_handover": True,
            "support_model": True,
        },
        business_day=14,
    )
    engine.mark_implemented(
        request,
        "Implementation Owner",
        Role.IMPLEMENTATION_OWNER,
        "Workflow and reporting changes released to the synthetic operations group.",
        business_day=17,
    )
    engine.close(
        request,
        "Transformation Lead",
        Role.TRANSFORMATION_LEAD,
        "Adoption confirmed, evidence captured and handover complete.",
        business_day=19,
    )
    return request
