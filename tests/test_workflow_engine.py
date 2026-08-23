import unittest

from enterprise_workflow_lab.engine import WorkflowEngine, WorkflowError
from enterprise_workflow_lab.models import ApprovalDecision, Role, Status, WorkflowRequest


def make_request() -> WorkflowRequest:
    return WorkflowRequest(
        request_id="EWF-TEST-001",
        title="Workflow reporting improvement",
        business_unit="Operations",
        requester="Requester",
        value_band="medium",
        risk_level="moderate",
        systems_impacted=["workflow", "reporting"],
        business_reason="Improve approval visibility.",
    )


class WorkflowEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = WorkflowEngine()

    def test_happy_path_reaches_closed_with_audit_trail(self) -> None:
        request = make_request()

        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready for review.")
        self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.")
        self.engine.decide(request, ApprovalDecision(Role.DEPARTMENT_OWNER, "Department Owner", "Business need confirmed."))
        self.engine.decide(request, ApprovalDecision(Role.FINANCE_CONTROLLER, "Finance Controller", "Budget accepted."))
        self.engine.decide(request, ApprovalDecision(Role.IT_REVIEWER, "IT Reviewer", "Systems impact accepted."))
        self.engine.decide(request, ApprovalDecision(Role.TRANSFORMATION_LEAD, "Transformation Lead", "Roadmap fit confirmed."))
        self.engine.mark_implemented(request, "Implementation Owner", Role.IMPLEMENTATION_OWNER, "Released.")
        self.engine.close(request, "Transformation Lead", Role.TRANSFORMATION_LEAD, "Handover complete.")

        self.assertEqual(Status.CLOSED, request.status)
        self.assertEqual(8, len(request.audit_log))
        self.assertEqual(Status.DRAFT, request.audit_log[0].from_status)
        self.assertEqual(Status.CLOSED, request.audit_log[-1].to_status)

    def test_wrong_role_cannot_approve_gate(self) -> None:
        request = make_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.")
        self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.")

        with self.assertRaises(WorkflowError):
            self.engine.decide(request, ApprovalDecision(Role.IT_REVIEWER, "IT Reviewer", "Skipping ahead."))

    def test_rejection_is_terminal(self) -> None:
        request = make_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.")
        self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.")
        self.engine.decide(
            request,
            ApprovalDecision(Role.DEPARTMENT_OWNER, "Department Owner", "Business owner not ready.", approved=False),
        )

        self.assertEqual(Status.REJECTED, request.status)
        with self.assertRaises(WorkflowError):
            self.engine.decide(request, ApprovalDecision(Role.FINANCE_CONTROLLER, "Finance Controller", "Approved."))

    def test_implementation_requires_approved_status(self) -> None:
        request = make_request()

        with self.assertRaises(WorkflowError):
            self.engine.mark_implemented(request, "Implementation Owner", Role.IMPLEMENTATION_OWNER, "Done.")


if __name__ == "__main__":
    unittest.main()
