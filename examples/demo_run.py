from enterprise_workflow_lab.cli import run_demo


if __name__ == "__main__":
    request = run_demo()
    for event in request.audit_log:
        print(f"{event.action}: {event.from_status} -> {event.to_status} by {event.role}")
