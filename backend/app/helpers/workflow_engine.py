"""Workflow automation engine — runs chained CRM / AI actions."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.helpers.llm.provider import generate_completion
from app.helpers.prompts import EMAIL_SYSTEM, MEETING_SYSTEM
from app.models.ai import EmailHistory, Notification, Workflow, WorkflowExecution
from app.models.crm import Deal, Lead, Meeting, Task
from app.models.user import User

WORKFLOW_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "lead_follow_up": {
        "name": "Lead Follow-up",
        "description": "Create follow-up task → draft email → notify salesperson",
        "trigger": "manual_or_lead_created",
        "steps": [
            {"action": "create_task", "title": "Follow up with {lead_name}", "priority": "high"},
            {"action": "generate_email", "subject": "Following up — {lead_name}", "prompt": "Write a professional follow-up email to {lead_name} at {company}. Mention our Enterprise CRM offering."},
            {"action": "notify", "title": "Lead follow-up workflow", "body": "Task and email draft created for {lead_name}."},
        ],
    },
    "meeting_summary": {
        "name": "Meeting Summary",
        "description": "Summarize latest meeting → create action tasks → notify",
        "trigger": "manual_or_meeting_saved",
        "steps": [
            {"action": "summarize_meeting"},
            {"action": "create_task", "title": "Send follow-up after meeting: {meeting_title}", "priority": "medium"},
            {"action": "notify", "title": "Meeting processed", "body": "Summary ready for {meeting_title}."},
        ],
    },
    "deal_won": {
        "name": "Deal Closed Won",
        "description": "Create onboarding task → thank-you email → notify manager",
        "trigger": "manual_or_deal_closed",
        "steps": [
            {"action": "create_task", "title": "Onboard customer for deal: {deal_title}", "priority": "high"},
            {"action": "generate_email", "subject": "Thank you for your business", "prompt": "Write a thank-you email for closing the deal: {deal_title} worth ${deal_value}."},
            {"action": "notify", "title": "Deal closed workflow", "body": "Onboarding started for {deal_title}."},
        ],
    },
}


def list_templates() -> List[Dict[str, Any]]:
    return [
        {"key": key, "name": t["name"], "description": t["description"], "trigger": t["trigger"], "steps": t["steps"]}
        for key, t in WORKFLOW_TEMPLATES.items()
    ]


def _fmt(text: str, ctx: Dict[str, str]) -> str:
    out = text
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", v)
    return out


async def _build_context(user: User, payload: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    ctx: Dict[str, str] = {
        "lead_name": "New Lead",
        "company": "Unknown",
        "meeting_title": "Recent Meeting",
        "deal_title": "New Deal",
        "deal_value": "0",
    }
    if payload:
        for k, v in payload.items():
            if v is not None:
                ctx[k] = str(v)

    lead = await Lead.filter(owner_id=user.id).order_by("-created_at").first()
    if lead and ctx["lead_name"] == "New Lead":
        ctx["lead_name"] = lead.name
        ctx["company"] = lead.company or "Unknown"

    meeting = await Meeting.filter(owner_id=user.id).order_by("-created_at").first()
    if meeting:
        ctx["meeting_title"] = meeting.title

    deal = await Deal.filter(owner_id=user.id).order_by("-updated_at").first()
    if deal:
        ctx["deal_title"] = deal.title
        ctx["deal_value"] = str(float(deal.value or 0))

    return ctx


async def _run_step(user: User, step: Dict[str, Any], ctx: Dict[str, str]) -> Dict[str, Any]:
    action = step.get("action")

    if action == "create_task":
        title = _fmt(step.get("title", "Workflow task"), ctx)
        task = await Task.create(
            owner_id=user.id,
            title=title,
            status="pending",
            priority=step.get("priority", "medium"),
        )
        return {"action": action, "success": True, "task_id": task.id, "title": task.title}

    if action == "generate_email":
        subject = _fmt(step.get("subject", "Follow-up"), ctx)
        prompt = _fmt(step.get("prompt", "Write a sales follow-up email."), ctx)
        body = await generate_completion(prompt, EMAIL_SYSTEM)
        if body.startswith("AI response (configure OPENAI_API_KEY") or body.startswith("LLM error"):
            body = f"Hi {ctx.get('lead_name', 'there')},\n\nThank you for your interest. I wanted to follow up on our conversation.\n\nBest regards"
        record = await EmailHistory.create(owner_id=user.id, subject=subject, body=body, email_type="workflow")
        return {"action": action, "success": True, "email_id": record.id, "subject": subject}

    if action == "notify":
        title = _fmt(step.get("title", "Workflow notification"), ctx)
        body = _fmt(step.get("body", "A workflow step completed."), ctx)
        note = await Notification.create(owner_id=user.id, title=title, body=body, notification_type="workflow")
        return {"action": action, "success": True, "notification_id": note.id, "title": title}

    if action == "summarize_meeting":
        meeting = await Meeting.filter(owner_id=user.id).order_by("-created_at").first()
        if not meeting or not meeting.transcript:
            return {"action": action, "success": False, "error": "No meeting with transcript found."}
        summary = await generate_completion(f"Transcript:\n{meeting.transcript}", MEETING_SYSTEM)
        if summary.startswith("AI response (configure OPENAI_API_KEY") or summary.startswith("LLM error"):
            summary = f"Meeting: {meeting.title}\n\nKey points from transcript:\n{meeting.transcript[:500]}..."
        meeting.summary = summary
        await meeting.save()
        ctx["meeting_title"] = meeting.title
        return {"action": action, "success": True, "meeting_id": meeting.id, "summary_preview": summary[:200]}

    if action == "create_deal":
        title = _fmt(step.get("title", ctx.get("deal_title", "New Opportunity")), ctx)
        deal = await Deal.create(
            owner_id=user.id,
            title=title,
            value=Decimal(str(step.get("value", ctx.get("deal_value", 0)))),
            stage="lead",
            probability=50,
        )
        return {"action": action, "success": True, "deal_id": deal.id, "title": deal.title}

    return {"action": action or "unknown", "success": False, "error": "Unsupported action"}


async def run_workflow(
    user: User,
    workflow: Workflow,
    context: Optional[Dict[str, Any]] = None,
) -> WorkflowExecution:
    execution = await WorkflowExecution.create(
        workflow_id=workflow.id,
        owner_id=user.id,
        status="running",
        result={"steps": []},
    )

    ctx = await _build_context(user, context)
    steps = workflow.steps or []
    results: List[Dict[str, Any]] = []
    all_ok = True

    for step in steps:
        if step.get("_meta"):
            continue
        try:
            result = await _run_step(user, step, ctx)
            results.append(result)
            if not result.get("success"):
                all_ok = False
        except Exception as exc:
            results.append({"action": step.get("action"), "success": False, "error": str(exc)})
            all_ok = False

    execution.status = "completed" if all_ok else "failed"
    execution.result = {
        "workflow_name": workflow.name,
        "steps_run": len(results),
        "actions": results,
        "summary": _summarize_results(results),
    }
    execution.completed_at = datetime.now(timezone.utc)
    await execution.save()

    if workflow.status == "draft":
        workflow.status = "active"
        await workflow.save()

    return execution


def _summarize_results(results: List[Dict[str, Any]]) -> str:
    parts = []
    for r in results:
        if r.get("success"):
            parts.append(f"✓ {r.get('action')}: {r.get('title') or r.get('subject') or 'done'}")
        else:
            parts.append(f"✗ {r.get('action')}: {r.get('error', 'failed')}")
    return "\n".join(parts) if parts else "No steps executed."


def _workflow_trigger(workflow: Workflow) -> Optional[str]:
    for step in workflow.steps or []:
        if step.get("_meta"):
            return step.get("trigger")
    return None


async def trigger_workflows_for_event(user: User, event: str, context: Optional[Dict[str, Any]] = None) -> List[int]:
    """Run active workflows whose trigger matches event (e.g. lead_created)."""
    workflows = await Workflow.filter(owner_id=user.id, status="active")
    execution_ids: List[int] = []
    for wf in workflows:
        trigger = _workflow_trigger(wf) or ""
        if event not in trigger.split("_or_"):
            continue
        ex = await run_workflow(user, wf, context)
        execution_ids.append(ex.id)
    return execution_ids
