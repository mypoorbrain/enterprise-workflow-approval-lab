from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from enterprise_workflow_lab.models import Status, WorkflowRequest
from enterprise_workflow_lab.policies import SLA_DAYS_BY_STATUS, approval_route_for
from enterprise_workflow_lab.scenarios import run_demo


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts"
PREVIEW_PATH = ROOT / "docs" / "workflow-preview.svg"


def build_showcase_artifacts(request: WorkflowRequest | None = None) -> dict[str, Any]:
    request = request or run_demo()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)

    files = {
        "workflow-walkthrough.html": render_walkthrough_html(request),
        "request-brief.md": render_request_brief(request),
        "raid-log.md": render_raid_log(request),
        "decision-log.md": render_decision_log(request),
        "readiness-checklist.md": render_readiness_checklist(request),
        "handover-record.md": render_handover_record(request),
        "workflow-summary.json": json.dumps(summary_payload(request), indent=2),
    }
    for filename, content in files.items():
        (ARTIFACT_DIR / filename).write_text(content, encoding="utf-8")
    PREVIEW_PATH.write_text(render_preview_svg(request), encoding="utf-8")
    return {"request_id": request.request_id, "artifact_dir": str(ARTIFACT_DIR), "files": sorted(files)}


def summary_payload(request: WorkflowRequest) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "title": request.title,
        "status": request.status,
        "route": approval_route_for(request),
        "audit_events": len(request.audit_log),
        "decisions": len(request.decisions),
        "resubmissions": request.resubmission_count,
        "readiness_checks": request.readiness_checks,
    }


def render_walkthrough_html(request: WorkflowRequest) -> str:
    route = approval_route_for(request)
    timeline = stage_timeline(request)
    escalation_count = sum(1 for item in timeline if item["sla_level"] in {"overdue", "escalate"})
    readiness_passed = sum(1 for passed in request.readiness_checks.values() if passed)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Enterprise Workflow Delivery Walkthrough</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1d2528;
      --muted: #59666b;
      --paper: #f5f6f2;
      --panel: #ffffff;
      --line: #d8e0df;
      --navy: #21394d;
      --teal: #2e766f;
      --gold: #b6822e;
      --rose: #b8564c;
      --green: #3f7d52;
      --shadow: 0 18px 44px rgba(33, 57, 77, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 34px 0 48px; }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(300px, 380px);
      gap: 22px;
      align-items: stretch;
      padding-bottom: 22px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 10px; color: var(--navy); font-size: clamp(32px, 4vw, 52px); line-height: 1; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; color: var(--navy); font-size: 18px; letter-spacing: 0; }}
    p {{ margin: 0; color: var(--muted); }}
    .kicker {{ display: block; margin-bottom: 9px; color: var(--teal); font-size: 12px; font-weight: 850; letter-spacing: .04em; text-transform: uppercase; }}
    .status-card, .panel, .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }}
    .status-card {{ padding: 18px; background: var(--navy); color: #eff5f2; }}
    .status-card p {{ color: #cbd9d7; }}
    .status-card strong {{ display: block; margin: 9px 0 8px; color: #fff; font-size: 28px; line-height: 1; }}
    .metrics {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }}
    .metric {{ padding: 14px; min-height: 104px; }}
    .metric span {{ color: var(--muted); font-size: 12px; font-weight: 800; }}
    .metric strong {{ display: block; margin-top: 9px; color: var(--navy); font-size: 26px; line-height: 1; }}
    .grid {{ display: grid; gap: 16px; }}
    .two {{ grid-template-columns: minmax(0, 1.1fr) minmax(320px, .9fr); }}
    .panel {{ padding: 18px; overflow: hidden; }}
    .state-strip {{
      display: grid;
      grid-template-columns: repeat(8, minmax(110px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
      overflow-x: auto;
      padding-bottom: 3px;
    }}
    .state-node {{
      min-height: 86px;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
    }}
    .state-node span {{ display: block; color: var(--muted); font-size: 11px; font-weight: 850; text-transform: uppercase; }}
    .state-node strong {{ display: block; margin-top: 7px; color: var(--navy); font-size: 13px; line-height: 1.2; }}
    .state-node.done {{ border-color: rgba(46, 118, 111, .35); box-shadow: inset 0 4px 0 var(--teal); }}
    .state-node.loop {{ border-color: rgba(182, 130, 46, .48); box-shadow: inset 0 4px 0 var(--gold); }}
    .state-node.current {{ border-color: rgba(63, 125, 82, .45); box-shadow: inset 0 4px 0 var(--green); }}
    .evidence-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 14px; }}
    .evidence-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
      padding: 12px;
      min-height: 100px;
    }}
    .evidence-card span {{ color: var(--muted); font-size: 11px; font-weight: 850; text-transform: uppercase; }}
    .evidence-card strong {{ display: block; margin-top: 7px; color: var(--navy); font-size: 13px; line-height: 1.25; }}
    .evidence-card p {{ margin-top: 7px; font-size: 12px; }}
    .artifact-links {{ display: grid; gap: 8px; margin-top: 14px; }}
    .artifact-links a {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 11px;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--navy);
      text-decoration: none;
      font-size: 13px;
      font-weight: 800;
      background: #fbfcfb;
    }}
    .artifact-links a span {{ color: var(--muted); font-weight: 700; }}
    .timeline {{ display: grid; gap: 10px; }}
    .event {{
      display: grid;
      grid-template-columns: 70px 1fr 104px;
      gap: 12px;
      align-items: start;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfb;
    }}
    .day {{ color: var(--navy); font-weight: 850; }}
    .event strong {{ display: block; color: var(--navy); }}
    .event small {{ display: block; margin-top: 3px; color: var(--muted); }}
    .chip {{ display: inline-flex; align-items: center; min-height: 26px; padding: 0 9px; border-radius: 999px; font-size: 11px; font-weight: 850; }}
    .chip.on_track, .chip.closed {{ background: #e2eee5; color: #285a37; }}
    .chip.watch {{ background: #f8ecd4; color: #815c1d; }}
    .chip.overdue, .chip.escalate {{ background: #f8dfdc; color: #8f332b; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 9px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ color: var(--navy); font-size: 11px; text-transform: uppercase; letter-spacing: .03em; }}
    .route {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .route .chip {{ background: #e7ece9; color: var(--navy); }}
    @media (max-width: 980px) {{
      header, .two {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .evidence-grid {{ grid-template-columns: 1fr; }}
      .event {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 620px) {{
      main {{ width: min(100% - 22px, 1180px); padding-top: 24px; }}
      .metrics {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <span class="kicker">Enterprise delivery workflow</span>
        <h1>Controlled Workflow Delivery Walkthrough</h1>
        <p>{escape(request.business_reason)}</p>
      </div>
      <aside class="status-card">
        <span class="kicker">Current state</span>
        <strong>{escape(request.status.value.replace("_", " ").title())}</strong>
        <p>{escape(request.request_id)} closed after {len(request.audit_log)} auditable events, {len(request.decisions)} approval decisions and {request.resubmission_count} resubmission.</p>
      </aside>
    </header>

    <section class="metrics" aria-label="Workflow metrics">
      <article class="metric"><span>Request class</span><strong>{escape(request.request_class.replace("_", " ").title())}</strong></article>
      <article class="metric"><span>Route gates</span><strong>{len(route)}</strong></article>
      <article class="metric"><span>Target release</span><strong>Day {request.target_release_day}</strong></article>
      <article class="metric"><span>Actual closure</span><strong>Day {request.current_day}</strong></article>
      <article class="metric"><span>Readiness checks</span><strong>{readiness_passed}/{len(request.readiness_checks)}</strong></article>
      <article class="metric"><span>SLA escalations</span><strong>{escalation_count}</strong></article>
    </section>

    <section class="state-strip" aria-label="Visible workflow state transitions">
      {render_state_strip(request)}
    </section>

    <section class="grid two">
      <article class="panel">
        <h2>Workflow Timeline And SLA Status</h2>
        <div class="timeline">
          {''.join(render_event(event) for event in timeline)}
        </div>
      </article>
      <article class="panel">
        <h2>Conditional Route</h2>
        <p style="margin-bottom: 12px;">Route is determined by request class, value band, risk level and impacted systems.</p>
        <div class="route">
          {''.join(f'<span class="chip">{escape(status.value.replace("_", " ").title())}</span>' for status in route)}
        </div>
        <h2 style="margin-top: 24px;">Readiness Gates</h2>
        <table>
          <tbody>
            {''.join(f'<tr><td>{escape(name.replace("_", " ").title())}</td><td><span class="chip on_track">Passed</span></td></tr>' for name, passed in request.readiness_checks.items() if passed)}
          </tbody>
        </table>
        <div class="evidence-grid">
          <article class="evidence-card">
            <span>Change / resubmission</span>
            <strong>{request.resubmission_count} loop completed</strong>
            <p>Department review requested clarification; requester resubmitted ownership, UAT and adoption evidence before approval continued.</p>
          </article>
          <article class="evidence-card">
            <span>SLA / escalation</span>
            <strong>{escalation_count} escalations</strong>
            <p>Every timeline event carries an SLA chip; overdue stages would move from watch to overdue or escalate.</p>
          </article>
          <article class="evidence-card">
            <span>Readiness</span>
            <strong>{readiness_passed}/{len(request.readiness_checks)} gates passed</strong>
            <p>Implementation cannot be marked complete until UAT, rollback, owner handover and support model evidence pass.</p>
          </article>
          <article class="evidence-card">
            <span>Handover</span>
            <strong>Closed on day {request.current_day}</strong>
            <p>Closure records adoption confirmation, evidence capture and transformation-lead handover.</p>
          </article>
        </div>
        <div class="artifact-links" aria-label="Artifact drill-down links">
          <a href="request-brief.md">Request brief <span>requirements</span></a>
          <a href="decision-log.md">Decision log <span>approvals</span></a>
          <a href="readiness-checklist.md">Readiness checklist <span>evidence</span></a>
          <a href="handover-record.md">Handover record <span>closure</span></a>
        </div>
      </article>
    </section>

    <section class="panel" style="margin-top: 16px;">
      <h2>Decision Log</h2>
      <table>
        <thead><tr><th>ID</th><th>Role</th><th>Decision</th><th>Rationale</th><th>Conditions</th></tr></thead>
        <tbody>
          {''.join(render_decision_row(decision) for decision in request.decisions)}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def render_state_strip(request: WorkflowRequest) -> str:
    nodes = []
    for index, event in enumerate(request.audit_log):
        css = "loop" if event.to_status == Status.CHANGES_REQUESTED else "current" if index == len(request.audit_log) - 1 else "done"
        nodes.append(
            f"""<article class="state-node {css}">
              <span>Day {event.business_day}</span>
              <strong>{escape(event.to_status.value.replace("_", " ").title())}</strong>
            </article>"""
        )
    return "".join(nodes)


def render_event(item: dict[str, Any]) -> str:
    event = item["event"]
    return (
        f'<div class="event">'
        f'<div class="day">Day {event.business_day}</div>'
        f'<div><strong>{escape(event.action.replace("_", " ").title())}: '
        f'{escape(event.from_status.value.replace("_", " ").title())} → {escape(event.to_status.value.replace("_", " ").title())}</strong>'
        f'<small>{escape(event.actor)} as {escape(event.role.value.replace("_", " "))}</small>'
        f'<small>{escape(event.rationale)}</small></div>'
        f'<div><span class="chip {escape(item["sla_level"])}">{escape(item["sla_label"])}</span></div>'
        f'</div>'
    )


def render_decision_row(decision: Any) -> str:
    decision_label = "Approved" if decision.approved else "Changes requested" if decision.requires_changes else "Rejected"
    conditions = ", ".join(decision.conditions) if decision.conditions else "None"
    return (
        f"<tr><td>{escape(decision.decision_id or 'n/a')}</td>"
        f"<td>{escape(decision.role.value)}</td>"
        f"<td>{escape(decision_label)}</td>"
        f"<td>{escape(decision.rationale)}</td>"
        f"<td>{escape(conditions)}</td></tr>"
    )


def stage_timeline(request: WorkflowRequest) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, event in enumerate(request.audit_log):
        next_day = request.audit_log[index + 1].business_day if index + 1 < len(request.audit_log) else event.business_day
        duration = max(0, next_day - event.business_day)
        sla_days = SLA_DAYS_BY_STATUS.get(event.to_status, 0)
        if event.to_status in {Status.CLOSED, Status.REJECTED}:
            level = "closed"
            label = "Closed"
        elif sla_days and duration > sla_days:
            level = "escalate" if duration >= sla_days + 2 else "overdue"
            label = f"{duration}d / SLA {sla_days}d"
        elif sla_days and duration >= max(0, sla_days - 1):
            level = "watch"
            label = f"{duration}d / SLA {sla_days}d"
        else:
            level = "on_track"
            label = f"{duration}d / SLA {sla_days}d" if sla_days else "On track"
        items.append({"event": event, "duration": duration, "sla_level": level, "sla_label": label})
    return items


def render_request_brief(request: WorkflowRequest) -> str:
    route = ", ".join(status.value for status in approval_route_for(request))
    return f"""# Request Brief

| Field | Value |
| --- | --- |
| Request ID | `{request.request_id}` |
| Title | {request.title} |
| Business unit | {request.business_unit} |
| Request class | `{request.request_class}` |
| Value band | `{request.value_band}` |
| Risk level | `{request.risk_level}` |
| Systems impacted | {', '.join(request.systems_impacted)} |
| Approval route | {route} |
| Target release day | Day {request.target_release_day} |

## Business Reason

{request.business_reason}
"""


def render_raid_log(request: WorkflowRequest) -> str:
    return f"""# RAID View

| Type | Item | Status | Owner | Evidence |
| --- | --- | --- | --- | --- |
| Risk | Reporting owner unclear before first review. | Mitigated | Department owner | Change request and resubmission in audit log. |
| Assumption | Finance reporting impact remains inside existing control model. | Accepted | Finance controller | Decision `DEC-003`. |
| Issue | Manual follow-up creates approval aging visibility gap. | Addressed | Transformation lead | Business reason for `{request.request_id}`. |
| Dependency | UAT, rollback, handover and support model must pass before release. | Closed | Implementation owner | Readiness checklist. |
"""


def render_decision_log(request: WorkflowRequest) -> str:
    rows = [
        "| Decision ID | Role | Outcome | Rationale | Conditions |",
        "| --- | --- | --- | --- | --- |",
    ]
    for decision in request.decisions:
        outcome = "Approved" if decision.approved else "Changes requested" if decision.requires_changes else "Rejected"
        rows.append(
            f"| `{decision.decision_id or 'n/a'}` | `{decision.role.value}` | {outcome} | {decision.rationale} | {', '.join(decision.conditions) if decision.conditions else 'None'} |"
        )
    return "# Decision Log\n\n" + "\n".join(rows) + "\n"


def render_readiness_checklist(request: WorkflowRequest) -> str:
    rows = [
        "# UAT And Readiness Checklist",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for name, passed in request.readiness_checks.items():
        rows.append(f"| {name.replace('_', ' ').title()} | {'Passed' if passed else 'Failed'} |")
    return "\n".join(rows) + "\n"


def render_handover_record(request: WorkflowRequest) -> str:
    return f"""# Implementation Handover Record

| Field | Value |
| --- | --- |
| Request | `{request.request_id}` |
| Final status | `{request.status.value}` |
| Closure day | Day {request.current_day} |
| Audit events | {len(request.audit_log)} |
| Resubmissions | {request.resubmission_count} |
| Handover owner | Transformation lead |

## Closure Note

Adoption confirmed, evidence captured and handover complete. This is a synthetic closure record for portfolio demonstration only.
"""


def render_preview_svg(request: WorkflowRequest) -> str:
    route = approval_route_for(request)
    events = request.audit_log
    event_cells = []
    for index, event in enumerate(events[:8]):
        x = 84 + index * 122
        fill = "#2e766f" if event.to_status not in {Status.CHANGES_REQUESTED, Status.REJECTED} else "#b6822e"
        label = short_status(event.to_status)
        event_cells.append(
            f'<rect x="{x}" y="358" width="92" height="54" rx="8" fill="{fill}"/>'
            f'<text x="{x + 10}" y="382" fill="#fff" font-size="11" font-weight="700">Day {event.business_day}</text>'
            f'<text x="{x + 10}" y="400" fill="#fff" font-size="10">{escape(label)}</text>'
        )
    route_cells = []
    for index, status in enumerate(route):
        x = 88 + index * 188
        route_cells.append(
            f'<rect x="{x}" y="528" width="154" height="40" rx="8" fill="#21394d"/>'
            f'<text x="{x + 14}" y="553" fill="#fff" font-size="12" font-weight="700">{escape(status.value.replace("_", " ").title())}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="680" viewBox="0 0 1180 680" role="img" aria-labelledby="title desc">
  <title id="title">Enterprise workflow delivery walkthrough preview</title>
  <desc id="desc">Generated preview of the workflow timeline, route, readiness gates and delivery artifacts.</desc>
  <rect width="1180" height="680" rx="18" fill="#f5f6f2"/>
  <rect x="34" y="34" width="1112" height="612" rx="18" fill="#ffffff" stroke="#d8e0df"/>
  <text x="70" y="84" fill="#21394d" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="700">Enterprise Workflow Delivery Walkthrough</text>
  <text x="70" y="116" fill="#59666b" font-family="Inter, Arial, sans-serif" font-size="16">Conditional approvals, SLA visibility, change handling, readiness gates and handover evidence.</text>

  <g font-family="Inter, Arial, sans-serif">
    <rect x="70" y="148" width="190" height="92" rx="8" fill="#f9fbfa" stroke="#d8e0df"/>
    <text x="88" y="178" fill="#59666b" font-size="13" font-weight="700">Route gates</text>
    <text x="88" y="213" fill="#21394d" font-size="31" font-weight="700">{len(route)}</text>
    <rect x="282" y="148" width="190" height="92" rx="8" fill="#f9fbfa" stroke="#d8e0df"/>
    <text x="300" y="178" fill="#59666b" font-size="13" font-weight="700">Audit events</text>
    <text x="300" y="213" fill="#21394d" font-size="31" font-weight="700">{len(events)}</text>
    <rect x="494" y="148" width="190" height="92" rx="8" fill="#f9fbfa" stroke="#d8e0df"/>
    <text x="512" y="178" fill="#59666b" font-size="13" font-weight="700">Resubmissions</text>
    <text x="512" y="213" fill="#21394d" font-size="31" font-weight="700">{request.resubmission_count}</text>
    <rect x="706" y="148" width="404" height="92" rx="8" fill="#21394d"/>
    <text x="728" y="178" fill="#cfd9d7" font-size="13" font-weight="700">Final state</text>
    <text x="728" y="213" fill="#ffffff" font-size="24" font-weight="700">{escape(request.status.value.replace("_", " ").title())} on day {request.current_day}</text>

    <rect x="70" y="270" width="1040" height="182" rx="8" fill="#ffffff" stroke="#d8e0df"/>
    <text x="94" y="306" fill="#21394d" font-size="18" font-weight="700">Timeline</text>
    {''.join(event_cells)}

    <rect x="70" y="486" width="1040" height="120" rx="8" fill="#ffffff" stroke="#d8e0df"/>
    <text x="94" y="520" fill="#21394d" font-size="18" font-weight="700">Conditional Approval Route</text>
    {''.join(route_cells)}
  </g>
</svg>
'''


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def short_status(status: Status) -> str:
    labels = {
        Status.SUBMITTED: "Submitted",
        Status.DEPARTMENT_REVIEW: "Dept review",
        Status.FINANCE_REVIEW: "Finance",
        Status.IT_REVIEW: "IT review",
        Status.TRANSFORMATION_REVIEW: "Transform",
        Status.CHANGES_REQUESTED: "Changes",
        Status.APPROVED: "Approved",
        Status.IMPLEMENTATION_READY: "Ready",
        Status.IMPLEMENTED: "Released",
        Status.CLOSED: "Closed",
        Status.REJECTED: "Rejected",
    }
    return labels.get(status, status.value)
