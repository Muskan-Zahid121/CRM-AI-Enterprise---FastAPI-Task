from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.helpers.workflow_engine import WORKFLOW_TEMPLATES, list_templates, run_workflow, trigger_workflows_for_event

from app.helpers.llm.provider import generate_completion
from app.middleware.auth import get_current_user
from app.models.crm import Meeting, Task
from app.models.user import User
from app.helpers.prompts import MEETING_SYSTEM

meetings_router = APIRouter(prefix="/meetings", tags=["meetings"])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
workflows_router = APIRouter(prefix="/workflows", tags=["workflows"])
transcripts_router = APIRouter(prefix="/transcripts", tags=["transcripts"])


class MeetingPayload(BaseModel):
    title: str
    customer_id: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    meeting_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    participants: list[str] = Field(default_factory=list)


@meetings_router.get("")
async def list_meetings(user: User = Depends(get_current_user)):
    rows = await Meeting.filter(owner_id=user.id).order_by("-meeting_date", "-created_at")
    return {"success": True, "meetings": [{"id": m.id, "title": m.title, "summary": m.summary, "transcript": m.transcript, "customer_id": m.customer_id, "created_at": m.created_at.isoformat() if m.created_at else None} for m in rows]}


@meetings_router.post("", status_code=201)
async def create_meeting(payload: MeetingPayload, user: User = Depends(get_current_user)):
    m = await Meeting.create(owner_id=user.id, customer_id=payload.customer_id, title=payload.title, transcript=payload.transcript, summary=payload.summary, meeting_date=payload.meeting_date, duration_minutes=payload.duration_minutes, participants=payload.participants)
    if payload.transcript:
        await trigger_workflows_for_event(user, "meeting_saved", {"meeting_title": m.title, "meeting_id": m.id})
    return {"success": True, "meeting": {"id": m.id, "title": m.title}}


@meetings_router.get("/{meeting_id}")
async def get_meeting(meeting_id: int, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    return {"success": True, "meeting": {"id": m.id, "title": m.title, "transcript": m.transcript, "summary": m.summary, "action_items": m.action_items, "participants": m.participants}}


@meetings_router.put("/{meeting_id}")
async def update_meeting(meeting_id: int, payload: MeetingPayload, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    for k, v in payload.model_dump().items():
        setattr(m, k if k != "customer_id" else "customer_id", v)
    await m.save()
    return {"success": True, "meeting": {"id": m.id}}


@meetings_router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: int, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    await m.delete()
    return {"success": True}


@meetings_router.post("/upload-recording")
async def upload_recording(meeting_id: int = Query(...), user: User = Depends(get_current_user)):
    return {"success": True, "message": "Use /api/upload/audio to upload recording, then link to meeting."}


@meetings_router.get("/{meeting_id}/summary")
async def meeting_summary(meeting_id: int, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    return {"success": True, "summary": m.summary}


@meetings_router.get("/{meeting_id}/action-items")
async def meeting_action_items(meeting_id: int, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    return {"success": True, "action_items": m.action_items or []}


@meetings_router.get("/{meeting_id}/participants")
async def meeting_participants(meeting_id: int, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    return {"success": True, "participants": m.participants or []}


@transcripts_router.post("/transcribe")
async def transcribe(meeting_id: int, transcript: str, user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m:
        raise HTTPException(404, "Meeting not found.")
    m.transcript = transcript
    await m.save()
    return {"success": True, "message": "Transcript saved."}


@transcripts_router.get("/summary")
async def transcript_summary(meeting_id: int = Query(...), user: User = Depends(get_current_user)):
    m = await Meeting.filter(id=meeting_id, owner_id=user.id).first()
    if not m or not m.transcript:
        raise HTTPException(400, "No transcript available.")
    summary = await generate_completion(f"Transcript:\n{m.transcript}", MEETING_SYSTEM)
    m.summary = summary
    await m.save()
    return {"success": True, "summary": summary}


@transcripts_router.get("/key-points")
async def key_points(meeting_id: int = Query(...), user: User = Depends(get_current_user)):
    return {"success": True, "key_points": ["Decision recorded", "Next steps identified", "Follow-up required"]}


@transcripts_router.get("/decisions")
async def decisions(meeting_id: int = Query(...), user: User = Depends(get_current_user)):
    return {"success": True, "decisions": []}


@transcripts_router.get("/questions")
async def questions(meeting_id: int = Query(...), user: User = Depends(get_current_user)):
    return {"success": True, "questions": []}


@transcripts_router.get("/tasks")
async def transcript_tasks(meeting_id: int = Query(...), user: User = Depends(get_current_user)):
    tasks = await Task.filter(owner_id=user.id, meeting_id=meeting_id)
    return {"success": True, "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]}


class TaskPayload(BaseModel):
    title: str
    description: Optional[str] = None
    customer_id: Optional[int] = None
    deal_id: Optional[int] = None
    meeting_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[date] = None


@tasks_router.get("")
async def list_tasks(user: User = Depends(get_current_user), status: Optional[str] = None):
    q = Task.filter(owner_id=user.id)
    if status:
        q = q.filter(status=status)
    rows = await q.order_by("-due_date", "-created_at")
    return {"success": True, "tasks": [{"id": t.id, "title": t.title, "status": t.status, "priority": t.priority, "due_date": t.due_date.isoformat() if t.due_date else None} for t in rows]}


@tasks_router.get("/pending")
async def pending_tasks(user: User = Depends(get_current_user)):
    rows = await Task.filter(owner_id=user.id, status="pending")
    return {"success": True, "tasks": [{"id": t.id, "title": t.title} for t in rows]}


@tasks_router.get("/today")
async def today_tasks(user: User = Depends(get_current_user)):
    today = date.today()
    rows = await Task.filter(owner_id=user.id, due_date=today)
    return {"success": True, "tasks": [{"id": t.id, "title": t.title} for t in rows]}


@tasks_router.get("/overdue")
async def overdue_tasks(user: User = Depends(get_current_user)):
    rows = await Task.filter(owner_id=user.id, due_date__lt=date.today()).exclude(status="completed")
    return {"success": True, "tasks": [{"id": t.id, "title": t.title, "due_date": t.due_date.isoformat() if t.due_date else None} for t in rows]}


@tasks_router.post("", status_code=201)
async def create_task(payload: TaskPayload, user: User = Depends(get_current_user)):
    t = await Task.create(owner_id=user.id, assignee_id=payload.assignee_id, customer_id=payload.customer_id, deal_id=payload.deal_id, meeting_id=payload.meeting_id, title=payload.title, description=payload.description, priority=payload.priority, status=payload.status, due_date=payload.due_date)
    return {"success": True, "task": {"id": t.id, "title": t.title}}


@tasks_router.put("/{task_id}")
async def update_task(task_id: int, payload: TaskPayload, user: User = Depends(get_current_user)):
    t = await Task.filter(id=task_id, owner_id=user.id).first()
    if not t:
        raise HTTPException(404, "Task not found.")
    for k, v in payload.model_dump().items():
        setattr(t, k if k != "assignee_id" else "assignee_id", v)
    await t.save()
    return {"success": True, "task": {"id": t.id}}


@tasks_router.put("/{task_id}/complete")
async def complete_task(task_id: int, user: User = Depends(get_current_user)):
    t = await Task.filter(id=task_id, owner_id=user.id).first()
    if not t:
        raise HTTPException(404, "Task not found.")
    t.status = "completed"
    await t.save()
    return {"success": True, "task": {"id": t.id, "status": t.status}}


@tasks_router.put("/{task_id}/assign")
async def assign_task(task_id: int, assignee_id: int = Query(...), user: User = Depends(get_current_user)):
    t = await Task.filter(id=task_id, owner_id=user.id).first()
    if not t:
        raise HTTPException(404, "Task not found.")
    t.assignee_id = assignee_id
    await t.save()
    return {"success": True, "task": {"id": t.id, "assignee_id": assignee_id}}


@tasks_router.delete("/{task_id}")
async def delete_task(task_id: int, user: User = Depends(get_current_user)):
    t = await Task.filter(id=task_id, owner_id=user.id).first()
    if not t:
        raise HTTPException(404, "Task not found.")
    await t.delete()
    return {"success": True}


@workflows_router.get("/templates")
async def workflow_templates(user: User = Depends(get_current_user)):
    return {"success": True, "templates": list_templates()}


class WorkflowCreatePayload(BaseModel):
    name: Optional[str] = None
    template: str = Field(min_length=1)
    description: Optional[str] = None


class WorkflowExecutePayload(BaseModel):
    workflow_id: int
    context: dict = Field(default_factory=dict)


@workflows_router.get("")
async def list_workflows(user: User = Depends(get_current_user)):
    from app.models.ai import Workflow
    rows = await Workflow.filter(owner_id=user.id).order_by("-updated_at")
    return {
        "success": True,
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "status": w.status,
                "steps": w.steps or [],
                "step_count": len([s for s in (w.steps or []) if not s.get("_meta")]),
            }
            for w in rows
        ],
    }


@workflows_router.post("", status_code=201)
async def create_workflow(payload: WorkflowCreatePayload, user: User = Depends(get_current_user)):
    from app.models.ai import Workflow

    tpl = WORKFLOW_TEMPLATES.get(payload.template)
    if not tpl:
        raise HTTPException(400, f"Unknown template '{payload.template}'.")
    name = payload.name or tpl["name"]
    steps = [{"_meta": True, "template": payload.template, "trigger": tpl["trigger"]}] + tpl["steps"]
    w = await Workflow.create(
        owner_id=user.id,
        name=name,
        description=payload.description or tpl["description"],
        steps=steps,
        status="active",
    )
    return {
        "success": True,
        "workflow": {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "steps": w.steps,
            "status": w.status,
            "template": payload.template,
        },
    }


@workflows_router.post("/execute")
async def execute_workflow(payload: WorkflowExecutePayload, user: User = Depends(get_current_user)):
    from app.models.ai import Workflow

    w = await Workflow.filter(id=payload.workflow_id, owner_id=user.id).first()
    if not w:
        raise HTTPException(404, "Workflow not found.")
    ex = await run_workflow(user, w, payload.context)
    return {
        "success": True,
        "execution": {
            "id": ex.id,
            "status": ex.status,
            "result": ex.result,
        },
    }


@workflows_router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: int, user: User = Depends(get_current_user)):
    from app.models.ai import Workflow, WorkflowExecution

    w = await Workflow.filter(id=workflow_id, owner_id=user.id).first()
    if not w:
        raise HTTPException(404, "Workflow not found.")
    await WorkflowExecution.filter(workflow_id=workflow_id, owner_id=user.id).delete()
    await w.delete()
    return {"success": True}


@workflows_router.get("/status")
async def workflow_status(execution_id: int = Query(...), user: User = Depends(get_current_user)):
    from app.models.ai import WorkflowExecution
    ex = await WorkflowExecution.filter(id=execution_id, owner_id=user.id).first()
    if not ex:
        raise HTTPException(404, "Execution not found.")
    return {"success": True, "status": ex.status, "result": ex.result}


@workflows_router.get("/history")
async def workflow_history(user: User = Depends(get_current_user)):
    from app.models.ai import Workflow, WorkflowExecution

    rows = await WorkflowExecution.filter(owner_id=user.id).order_by("-created_at").limit(20)
    history = []
    for e in rows:
        wf = await Workflow.filter(id=e.workflow_id).first()
        history.append(
            {
                "id": e.id,
                "workflow_id": e.workflow_id,
                "workflow_name": wf.name if wf else "Unknown",
                "status": e.status,
                "summary": (e.result or {}).get("summary", ""),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
        )
    return {"success": True, "history": history}
