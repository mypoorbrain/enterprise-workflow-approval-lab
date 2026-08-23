from __future__ import annotations

import argparse
import json
from pathlib import Path

from enterprise_workflow_lab.engine import WorkflowEngine
from enterprise_workflow_lab.models import ApprovalDecision, Role, WorkflowRequest


def load_request(path: Path) -> WorkflowRequest:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return WorkflowRequest.from_dict(payload)


def run_demo() -> WorkflowRequest:
    request = WorkflowRequest(
        request_id="EWF-2026-001",
        title="Procurement-to-payment reporting improvement",
        business_unit="Operations",
        requester="Demo Requester",
        value_band="medium",
        risk_level="moderate",
        systems_impacted=["workflow", "reporting", "finance"],
        business_reason="Reduce manual follow-up and improve management visibility over approval ageing.",
    )
    engine = WorkflowEngine()
    engine.submit(request, "Demo Requester", Role.REQUESTER, "Business owner has prepared the request.")
    engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Request is ready for structured review.")
    engine.decide(request, ApprovalDecision(Role.DEPARTMENT_OWNER, "Department Owner", "Need is valid and owned."))
    engine.decide(request, ApprovalDecision(Role.FINANCE_CONTROLLER, "Finance Controller", "Value and controls are acceptable."))
    engine.decide(request, ApprovalDecision(Role.IT_REVIEWER, "IT Reviewer", "Systems impact is understood and supportable."))
    engine.decide(request, ApprovalDecision(Role.TRANSFORMATION_LEAD, "Transformation Lead", "Fits the transformation roadmap."))
    engine.mark_implemented(request, "Implementation Owner", Role.IMPLEMENTATION_OWNER, "Workflow and reporting changes released.")
    engine.close(request, "Transformation Lead", Role.TRANSFORMATION_LEAD, "Adoption confirmed and handover complete.")
    return request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enterprise workflow approval lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("demo", help="Run the synthetic workflow demo")
    validate_parser = subparsers.add_parser("validate", help="Validate a synthetic request JSON file")
    validate_parser.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    if args.command == "demo":
        request = run_demo()
        print(f"Request {request.request_id} {request.status} after {len(request.audit_log)} audit events.")
        return 0

    if args.command == "validate":
        request = load_request(args.path)
        print(f"Request {request.request_id} loaded in {request.status} status.")
        return 0

    return 1
