from typing import Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.helpers.agents.graph import run_agent_graph, stream_response_text
from app.database.redis_client import cache_get, cache_set
from app.helpers.llm.provider import generate_completion
from app.middleware.auth import get_current_user
from app.models.ai import ChatMessage, ChatSession, EmailHistory
from app.models.crm import Customer, Document
from app.models.user import User
from app.helpers.prompts import EMAIL_SYSTEM
from app.helpers.rag.retriever import retrieve_similar
from tortoise.expressions import Q

chat_router = APIRouter(prefix="/chat", tags=["chat"])
agents_router = APIRouter(prefix="/agents", tags=["agents"])
search_router = APIRouter(prefix="/search", tags=["search"])
emails_router = APIRouter(prefix="/email", tags=["emails"])


class ChatPayload(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[int] = None


async def _get_session(user: User, session_id: Optional[int]) -> ChatSession:
    if not session_id:
        raise HTTPException(400, "session_id is required. Create a chat session first.")
    session = await ChatSession.filter(id=session_id, owner_id=user.id).first()
    if not session:
        raise HTTPException(404, "Chat session not found.")
    return session


@chat_router.post("/sessions")
async def create_session(user: User = Depends(get_current_user)):
    session = await ChatSession.create(owner_id=user.id, title="New conversation")
    return {
        "success": True,
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        },
    }


@chat_router.get("/sessions")
async def list_sessions(user: User = Depends(get_current_user)):
    rows = await ChatSession.filter(owner_id=user.id).order_by("-updated_at")
    return {
        "success": True,
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in rows
        ],
    }


@chat_router.get("/sessions/{session_id}/messages")
async def session_messages(session_id: int, user: User = Depends(get_current_user)):
    await _get_session(user, session_id)
    rows = await ChatMessage.filter(session_id=session_id, owner_id=user.id).order_by("created_at")
    return {
        "success": True,
        "messages": [
            {
                "id": m.id,
                "message": m.message,
                "response": m.response,
                "agent": m.agent,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in rows
        ],
    }


@chat_router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, user: User = Depends(get_current_user)):
    session = await _get_session(user, session_id)
    await ChatMessage.filter(session_id=session_id, owner_id=user.id).delete()
    await session.delete()
    return {"success": True, "message": "Session deleted."}


@chat_router.post("")
async def chat(payload: ChatPayload, user: User = Depends(get_current_user)):
    session = await _get_session(user, payload.session_id)

    result = await run_agent_graph(user, payload.message)
    record = await ChatMessage.create(
        session_id=session.id,
        owner_id=user.id,
        role="user",
        message=payload.message,
        response=result["response"],
        agent=result["agent"],
        citations=result["citations"],
        context=result["context"],
    )
    if session.title == "New conversation":
        session.title = payload.message[:60]
    session.updated_at = record.created_at
    await session.save()
    return {
        "success": True,
        "session_id": session.id,
        "response": result["response"],
        "agent": result["agent"],
        "citations": result["citations"],
        "actions": result.get("actions", []),
        "chat": {"id": record.id},
    }


@chat_router.post("/stream")
async def chat_stream(payload: ChatPayload, user: User = Depends(get_current_user)):
    session = await _get_session(user, payload.session_id)

    result = await run_agent_graph(user, payload.message)

    async def event_generator():
        full = result["response"]
        async for chunk in stream_response_text(full):
            yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
        record = await ChatMessage.create(
            session_id=session.id,
            owner_id=user.id,
            role="user",
            message=payload.message,
            response=full,
            agent=result["agent"],
            citations=result["citations"],
            context=result["context"],
        )
        if session.title == "New conversation":
            session.title = payload.message[:60]
        session.updated_at = record.created_at
        await session.save()
        yield f"data: {json.dumps({'done': True, 'session_id': session.id, 'session_title': session.title, 'agent': result['agent'], 'citations': result['citations'], 'chat_id': record.id, 'actions': result.get('actions', [])})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@chat_router.get("/history")
async def chat_history(limit: int = Query(default=20, le=100), user: User = Depends(get_current_user)):
    rows = await ChatMessage.filter(owner_id=user.id).order_by("-created_at").limit(limit)
    return {"success": True, "messages": [{"id": m.id, "message": m.message, "response": m.response, "agent": m.agent, "created_at": m.created_at.isoformat() if m.created_at else None} for m in rows]}


@chat_router.delete("/history")
async def delete_chat_history(user: User = Depends(get_current_user)):
    await ChatMessage.filter(owner_id=user.id).delete()
    await ChatSession.filter(owner_id=user.id).delete()
    return {"success": True, "message": "Chat history cleared."}


@chat_router.post("/clear-memory")
async def clear_memory(user: User = Depends(get_current_user)):
    cache_key = f"chat:memory:{user.id}"
    await cache_set(cache_key, "", ttl=1)
    return {"success": True, "message": "Conversation memory cleared."}


class AgentPayload(BaseModel):
    query: str


@agents_router.post("/router")
async def agent_router(payload: AgentPayload, user: User = Depends(get_current_user)):
    return {"success": True, **await run_agent_graph(user, payload.query)}


@agents_router.post("/crm")
async def agent_crm(payload: AgentPayload, user: User = Depends(get_current_user)):
    from app.helpers.dashboard import build_overview
    overview = await build_overview(user)
    response = await generate_completion(f"CRM data: {overview}\n\nQuery: {payload.query}")
    return {"success": True, "response": response, "agent": "crm"}


@agents_router.post("/document")
async def agent_document(payload: AgentPayload, user: User = Depends(get_current_user)):
    chunks = await retrieve_similar(user.id, payload.query, limit=5)
    return {"success": True, "response": f"Found {len(chunks)} relevant chunks.", "citations": chunks, "agent": "document"}


@agents_router.post("/meeting")
async def agent_meeting(payload: AgentPayload, user: User = Depends(get_current_user)):
    response = await generate_completion(payload.query, "You are a meeting analysis agent.")
    return {"success": True, "response": response, "agent": "meeting"}


@agents_router.post("/email")
async def agent_email(payload: AgentPayload, user: User = Depends(get_current_user)):
    response = await generate_completion(payload.query, EMAIL_SYSTEM)
    return {"success": True, "response": response, "agent": "email"}


@agents_router.post("/task")
async def agent_task(payload: AgentPayload, user: User = Depends(get_current_user)):
    return {"success": True, "response": f"Task agent received: {payload.query}", "agent": "task"}


@agents_router.post("/analytics")
async def agent_analytics(payload: AgentPayload, user: User = Depends(get_current_user)):
    from app.helpers.dashboard import build_overview
    return {"success": True, "response": str(await build_overview(user)), "agent": "analytics"}


@agents_router.post("/workflow")
async def agent_workflow(payload: AgentPayload, user: User = Depends(get_current_user)):
    return {"success": True, "response": f"Workflow agent: {payload.query}", "agent": "workflow"}


@agents_router.post("/tool-call")
async def agent_tool_call(tool: str = Query(...), query: str = Query(...), user: User = Depends(get_current_user)):
    cached = await cache_get(f"tool:{user.id}:{tool}:{query[:50]}")
    if cached:
        return {"success": True, "response": cached, "cached": True}
    result = await run_agent_graph(user, query)
    await cache_set(f"tool:{user.id}:{tool}:{query[:50]}", result["response"])
    return {"success": True, **result, "cached": False}


class SearchPayload(BaseModel):
    query: str


@search_router.post("")
async def global_search(payload: SearchPayload, user: User = Depends(get_current_user)):
    q = payload.query
    customers = await Customer.filter(owner_id=user.id).filter(Q(name__icontains=q) | Q(company__icontains=q)).limit(5)
    docs = await retrieve_similar(user.id, q, limit=5)
    return {"success": True, "customers": [{"id": c.id, "name": c.name} for c in customers], "documents": docs}


@search_router.post("/document")
async def search_document(payload: SearchPayload, user: User = Depends(get_current_user)):
    return {"success": True, "results": await retrieve_similar(user.id, payload.query, limit=10)}


@search_router.post("/customer")
async def search_customer(payload: SearchPayload, user: User = Depends(get_current_user)):
    rows = await Customer.filter(owner_id=user.id).filter(name__icontains=payload.query)
    return {"success": True, "customers": [{"id": c.id, "name": c.name} for c in rows]}


@search_router.post("/email")
async def search_email(payload: SearchPayload, user: User = Depends(get_current_user)):
    rows = await EmailHistory.filter(owner_id=user.id).filter(subject__icontains=payload.query).limit(10)
    return {"success": True, "emails": [{"id": e.id, "subject": e.subject} for e in rows]}


@search_router.post("/global")
async def search_global(payload: SearchPayload, user: User = Depends(get_current_user)):
    return await global_search(payload, user)


class EmailPayload(BaseModel):
    subject: str
    body: str = ""
    customer_id: Optional[int] = None
    prompt: Optional[str] = None


@emails_router.post("/generate")
async def generate_email(payload: EmailPayload, user: User = Depends(get_current_user)):
    prompt = payload.prompt or f"Subject: {payload.subject}\nContext: {payload.body}"
    body = await generate_completion(prompt, EMAIL_SYSTEM)
    record = await EmailHistory.create(owner_id=user.id, customer_id=payload.customer_id, subject=payload.subject, body=body, email_type="generated")
    return {"success": True, "email": {"id": record.id, "subject": record.subject, "body": record.body}}


@emails_router.post("/send")
async def send_email(email_id: int = Query(...), user: User = Depends(get_current_user)):
    record = await EmailHistory.filter(id=email_id, owner_id=user.id).first()
    if not record:
        raise HTTPException(404, "Email not found.")
    record.sent = True
    await record.save()
    return {"success": True, "message": "Email marked as sent. Connect SMTP for delivery."}


@emails_router.post("/reply")
async def reply_email(payload: EmailPayload, user: User = Depends(get_current_user)):
    body = await generate_completion(f"Write a reply.\n{payload.prompt or payload.body}", EMAIL_SYSTEM)
    return {"success": True, "body": body}


@emails_router.post("/template")
async def email_template(name: str = Query(...), user: User = Depends(get_current_user)):
    return {"success": True, "template": {"name": name, "body": "Hi {{name}},\n\nThank you for your time...\n\nBest regards"}}


@emails_router.get("/history")
async def email_history(user: User = Depends(get_current_user)):
    rows = await EmailHistory.filter(owner_id=user.id).order_by("-created_at").limit(50)
    return {"success": True, "emails": [{"id": e.id, "subject": e.subject, "sent": e.sent} for e in rows]}
