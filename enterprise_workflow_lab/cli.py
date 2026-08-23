from __future__ import annotations

import argparse
import json
from pathlib import Path

from enterprise_workflow_lab.artifacts import build_showcase_artifacts
from enterprise_workflow_lab.models import WorkflowRequest
from enterprise_workflow_lab.scenarios import run_demo


def load_request(path: Path) -> WorkflowRequest:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return WorkflowRequest.from_dict(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enterprise workflow approval lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("demo", help="Run the synthetic workflow scenario")
    subparsers.add_parser("build", help="Generate portfolio walkthrough and delivery artifacts")
    validate_parser = subparsers.add_parser("validate", help="Validate a synthetic request JSON file")
    validate_parser.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    if args.command == "demo":
        request = run_demo()
        print(f"Request {request.request_id} {request.status} after {len(request.audit_log)} audit events.")
        return 0

    if args.command == "build":
        result = build_showcase_artifacts()
        print(f"Built workflow showcase artifacts for {result['request_id']} in {result['artifact_dir']}.")
        return 0

    if args.command == "validate":
        request = load_request(args.path)
        print(f"Request {request.request_id} loaded in {request.status} status.")
        return 0

    return 1
