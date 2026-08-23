import unittest

from enterprise_workflow_lab.engine import WorkflowEngine, WorkflowError
from enterprise_workflow_lab.models import ApprovalDecision, Role, Status, WorkflowRequest
from enterprise_workflow_lab.policies import approval_route_for
from enterprise_workflow_lab.scenarios import make_demo_request, make_low_risk_request, run_demo


def make_request() -> WorkflowRequest:
    return make_demo_request()


class WorkflowEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = WorkflowEngine()

    def test_portfolio_scenario_reaches_closed_with_delivery_artifacts(self) -> None:
        request = run_demo()

        self.assertEqual(Status.CLOSED, request.status)
        self.assertEqual(12, len(request.audit_log))
        self.assertEqual(5, len(request.decisions))
        self.assertEqual(1, request.resubmission_count)
        self.assertTrue(all(request.readiness_checks.values()))
        self.assertEqual(Status.CHANGES_REQUESTED, request.audit_log[2].to_status)
        self.assertEqual(Status.IMPLEMENTATION_READY, request.audit_log[-3].to_status)
        self.assertEqual(19, request.current_day)

    def test_high_risk_route_includes_finance_it_and_transformation(self) -> None:
        request = make_request()
        self.assertEqual(
            [
                Status.DEPARTMENT_REVIEW,
                Status.FINANCE_REVIEW,
                Status.IT_REVIEW,
                Status.TRANSFORMATION_REVIEW,
            ],
            approval_route_for(request),
        )

    def test_low_risk_route_can_skip_finance_it_and_transformation(self) -> None:
        request = make_low_risk_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.", business_day=0)
        self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.", business_day=1)
        self.engine.decide(
            request,
            ApprovalDecision(Role.DEPARTMENT_OWNER, "Department Owner", "Local update approved."),
            business_day=2,
        )

        self.assertEqual([Status.DEPARTMENT_REVIEW], approval_route_for(request))
        self.assertEqual(Status.APPROVED, request.status)

    def test_wrong_role_cannot_approve_gate(self) -> None:
        request = make_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.")
        self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.")

        with self.assertRaises(WorkflowError):
            self.engine.decide(request, ApprovalDecision(Role.IT_REVIEWER, "IT Reviewer", "Skipping ahead."))

    def test_change_request_can_be_revised_and_resubmitted(self) -> None:
        request = make_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.", business_day=0)
        self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.", business_day=1)
        self.engine.decide(
            request,
            ApprovalDecision(
                Role.DEPARTMENT_OWNER,
                "Department Owner",
                "Need owner clarification.",
                approved=False,
                requires_changes=True,
            ),
            business_day=2,
        )
        self.engine.revise(request, "Requester", Role.REQUESTER, "Owner clarified.", business_day=3)

        self.assertEqual(Status.SUBMITTED, request.status)
        self.assertEqual(1, request.resubmission_count)

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
            self.engine.revise(request, "Requester", Role.REQUESTER, "Trying to revive terminal rejection.")

    def test_implementation_requires_readiness_gate(self) -> None:
        request = run_to_approved(self.engine, make_request())

        with self.assertRaises(WorkflowError):
            self.engine.mark_implemented(request, "Implementation Owner", Role.IMPLEMENTATION_OWNER, "Done.")

        with self.assertRaises(WorkflowError):
            self.engine.confirm_readiness(
                request,
                "Implementation Owner",
                Role.IMPLEMENTATION_OWNER,
                "Incomplete.",
                {"uat_signed_off": True},
            )

    def test_business_day_cannot_move_backwards(self) -> None:
        request = make_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.", business_day=4)
        with self.assertRaises(WorkflowError):
            self.engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Backdated.", business_day=3)

    def test_sla_snapshot_marks_overdue_stage(self) -> None:
        request = make_request()
        self.engine.submit(request, "Requester", Role.REQUESTER, "Ready.", business_day=0)
        request.current_day = 4

        snapshot = self.engine.sla_snapshot(request)
        self.assertTrue(snapshot["is_overdue"])
        self.assertEqual("escalate", snapshot["escalation_level"])


def run_to_approved(engine: WorkflowEngine, request: WorkflowRequest) -> WorkflowRequest:
    engine.submit(request, "Requester", Role.REQUESTER, "Ready.", business_day=0)
    engine.begin_review(request, "Department Owner", Role.DEPARTMENT_OWNER, "Review opened.", business_day=1)
    engine.decide(request, ApprovalDecision(Role.DEPARTMENT_OWNER, "Department Owner", "Approved."), business_day=2)
    engine.decide(request, ApprovalDecision(Role.FINANCE_CONTROLLER, "Finance Controller", "Approved."), business_day=3)
    engine.decide(request, ApprovalDecision(Role.IT_REVIEWER, "IT Reviewer", "Approved."), business_day=4)
    engine.decide(request, ApprovalDecision(Role.TRANSFORMATION_LEAD, "Transformation Lead", "Approved."), business_day=5)
    return request


if __name__ == "__main__":
    unittest.main()
