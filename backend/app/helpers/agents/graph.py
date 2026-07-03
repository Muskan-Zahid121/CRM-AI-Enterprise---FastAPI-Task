"""LangGraph orchestrator for the multi-agent CRM assistant."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from app.database.redis_client import cache_get, cache_set
from app.helpers.agents.crm_actions import (
    clear_pending_action,
    execute_crm_action,
    get_pending_action,
    is_confirmation,
    remember_pending_action,
)
from app.helpers.agents.intent_classifier import IntentClassification, classify_intent
from app.helpers.agents.orchestration import (
    format_knowledge_empty,
    gather_crm_context,
    gather_knowledge_context,
    gather_meeting_context,
)
from app.helpers.agents.query_parser import format_rag_answer
from app.helpers.dashboard import build_overview
from app.helpers.llm.provider import generate_completion
from app.helpers.prompts import CRM_SYSTEM, EMAIL_SYSTEM, MEETING_SYSTEM, RAG_SYSTEM
from app.models.crm import Customer
from app.models.user import User


class AgentGraphState(TypedDict):
    user: User
    query: str
    effective_query: str
    memory: Dict[str, Any]
    classification: Optional[Dict[str, Any]]
    action_result: Optional[Dict[str, Any]]
    response: str
    agent: str
    intent: str
    citations: List[Dict[str, Any]]
    orchestration: Dict[str, str]
    actions: List[str]
    routing: str


async def _remember_entity(user_id: int, entity: Dict[str, Any]) -> None:
    if entity:
        await cache_set(f"chat:memory:{user_id}", json.dumps(entity), ttl=86400)


async def _get_memory(user_id: int) -> Dict[str, Any]:
    raw = await cache_get(f"chat:memory:{user_id}")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {}


def _llm_unconfigured(text: str) -> bool:
    return text.startswith("AI response (configure OPENAI_API_KEY") or text.startswith("LLM error")


async def _try_crm_action(user: User, query: str) -> Dict[str, Any] | None:
    action_result = await execute_crm_action(user, query)
    if action_result:
        if action_result.get("success"):
            await clear_pending_action(user.id)
        if action_result.get("entity"):
            await _remember_entity(user.id, action_result["entity"])
        return action_result
    return None


async def _run_crm_agent(user: User, query: str, memory: Dict[str, Any]) -> str:
    overview = await build_overview(user)
    customers = await Customer.filter(owner_id=user.id).order_by("-created_at").limit(5)
    customer_lines = "\n".join(
        f"- {c.name} ({c.company or 'N/A'}) — {c.email or 'no email'}" for c in customers
    )
    prompt = (
        f"CRM overview: {overview}\n\nRecent customers:\n{customer_lines or 'None'}\n\n"
        f"Conversation memory: {memory}\n\nUser question: {query}\n\n"
        "Answer using CRM data. Do NOT ask for confirmation — tell the user what command to use. "
        "Commands: create/update/delete customers, leads, deals, tasks."
    )
    llm_response = await generate_completion(prompt, CRM_SYSTEM)
    if _llm_unconfigured(llm_response):
        return (
            f"📊 **CRM Snapshot**\n\n"
            f"• Customers: {overview['customers']}\n"
            f"• Open deals: {overview['open_deals']}\n"
            f"• Pending tasks: {overview['pending_tasks']}\n"
            f"• Pipeline value: ${overview['pipeline_value']:,.2f}\n\n"
            f"**Recent customers:**\n{customer_lines or 'None yet.'}\n\n"
            f"💡 I can **create, update, and delete** customers directly. Try:\n"
            f"• *Create a customer named John Smith*\n"
            f"• *Update John Smith's phone number to +1-555-999-9999*\n"
            f"• *Delete customer John Smith*"
        )
    return llm_response


async def _run_meeting_agent(user: User, query: str, classification: IntentClassification) -> str:
    meeting_context = await gather_meeting_context(user, query, classification.entities)
    intent_hint = classification.intent.replace("_", " ")

    if "No meetings saved" in meeting_context or "No matching meeting found" in meeting_context:
        return f"📝 **Meeting Agent**\n\n{meeting_context}"

    prompt = (
        f"User request ({intent_hint}):\n{query}\n\n"
        f"Meeting context:\n{meeting_context}\n\n"
        "Answer the user's question using the meeting context above. "
        "If they asked for action items, list them clearly as bullet points."
    )
    llm_response = await generate_completion(prompt, MEETING_SYSTEM)
    if _llm_unconfigured(llm_response):
        if classification.intent == "action_items" and "Stored action items:" in meeting_context:
            return f"📝 **Action items**\n\n{meeting_context.split('Stored action items:')[-1].strip()}"
        return f"📝 **Meeting Agent**\n\n{meeting_context}"
    return llm_response


async def _run_email_agent(
    user: User,
    query: str,
    classification: IntentClassification,
    memory: Dict[str, Any],
    orchestration: Dict[str, str],
) -> str:
    context_parts = []
    if orchestration.get("crm"):
        context_parts.append(f"CRM context:\n{orchestration['crm']}")
    if orchestration.get("meeting"):
        context_parts.append(f"Meeting context:\n{orchestration['meeting']}")
    if memory:
        context_parts.append(f"Conversation memory: {memory}")

    prompt = (
        f"User request:\n{query}\n\n"
        + ("\n\n".join(context_parts) + "\n\n" if context_parts else "")
        + "Draft a complete email with Subject line and body."
    )
    llm_response = await generate_completion(prompt, EMAIL_SYSTEM)
    if _llm_unconfigured(llm_response):
        customer = classification.entities.get("customer") or memory.get("name", "there")
        meeting = classification.entities.get("meeting", "our recent conversation")
        return (
            f"✉️ **Email draft** (add OPENAI_API_KEY for AI-generated text)\n\n"
            f"**Subject:** Follow-up — {meeting}\n\n"
            f"Hi {customer},\n\n"
            f"Thank you for your time during {meeting}. "
            f"I wanted to follow up on our discussion and next steps.\n\n"
            f"Best regards"
        )
    return llm_response


async def _run_knowledge_agent(user: User, query: str) -> tuple[str, List[Dict[str, Any]]]:
    bundle = await gather_knowledge_context(user, query)
    citations = bundle["citations"]
    stats = bundle["stats"]
    doc_titles = bundle["doc_titles"]

    if not citations:
        return format_knowledge_empty(query, stats, doc_titles), citations

    context_text = "\n\n".join(
        f"[Doc {c['document_id']} chunk {c['chunk_index']}] {c['content']}" for c in citations
    )
    prompt = f"Context:\n{context_text}\n\nQuestion: {query}\n\nAnswer concisely using only the context."
    llm_response = await generate_completion(prompt, RAG_SYSTEM)
    if _llm_unconfigured(llm_response):
        return format_rag_answer(query, citations, stats, doc_titles), citations
    return llm_response, citations


async def _run_analytics_agent(user: User) -> str:
    overview = await build_overview(user)
    return (
        f"📈 **Analytics Snapshot**\n\n"
        f"• Total customers: {overview['customers']}\n"
        f"• Open deals: {overview['open_deals']}\n"
        f"• Pipeline value: ${overview['pipeline_value']:,.2f}\n"
        f"• Pending tasks: {overview['pending_tasks']}\n"
        f"• Documents indexed: {overview['documents']}"
    )


async def _gather_orchestration_context(
    user: User,
    query: str,
    classification: IntentClassification,
    memory: Dict[str, Any],
) -> Dict[str, str]:
    ctx: Dict[str, str] = {}
    agents_needed = set(classification.requires)
    if classification.primary_agent in ("email", "meeting"):
        agents_needed.add(classification.primary_agent)
    if classification.primary_agent == "email":
        agents_needed.update({"crm", "meeting"})

    if "crm" in agents_needed:
        ctx["crm"] = await gather_crm_context(user, classification.entities, memory)
    if "meeting" in agents_needed:
        ctx["meeting"] = await gather_meeting_context(user, query, classification.entities)
    return ctx


def _action_response(state: AgentGraphState, routing: str) -> AgentGraphState:
    action_result = state["action_result"]
    if not action_result:
        return state
    return {
        **state,
        "response": action_result["response"],
        "agent": "crm",
        "intent": action_result.get("action", "crm"),
        "actions": [action_result.get("action")] if action_result.get("action") else [],
        "routing": routing,
    }


async def _node_prepare(state: AgentGraphState) -> AgentGraphState:
    user = state["user"]
    query = state["query"]
    memory = await _get_memory(user.id)

    effective_query = query
    if is_confirmation(query):
        pending = await get_pending_action(user.id)
        if pending:
            effective_query = pending

    await remember_pending_action(user.id, query if not is_confirmation(query) else effective_query)

    return {
        **state,
        "memory": memory,
        "effective_query": effective_query,
        "citations": [],
        "orchestration": {},
        "actions": [],
        "response": "",
        "agent": "",
        "intent": "",
        "routing": "",
        "classification": None,
        "action_result": None,
    }


async def _node_crm_fast_path(state: AgentGraphState) -> AgentGraphState:
    user = state["user"]
    query = state["query"]
    effective_query = state["effective_query"]

    action_result = await _try_crm_action(user, effective_query)
    if not action_result and is_confirmation(query):
        action_result = await _try_crm_action(user, query)

    return {**state, "action_result": action_result}


def _route_after_fast_path(state: AgentGraphState) -> Literal["finish", "classify"]:
    return "finish" if state.get("action_result") else "classify"


async def _node_finalize_crm_action(state: AgentGraphState) -> AgentGraphState:
    return _action_response(state, "crm_action_fast_path")


async def _node_classify(state: AgentGraphState) -> AgentGraphState:
    classification = await classify_intent(state["query"], state["memory"])
    return {**state, "classification": classification.to_dict()}


async def _node_crm_classified_path(state: AgentGraphState) -> AgentGraphState:
    classification_data = state.get("classification") or {}
    if classification_data.get("crm_action") and classification_data.get("primary_agent") == "crm":
        action_result = await _try_crm_action(state["user"], state["query"])
        if action_result:
            return _action_response({**state, "action_result": action_result}, "classified_crm_action")
    return state


def _route_after_classified_crm(state: AgentGraphState) -> Literal["finish", "route_agent"]:
    if state.get("action_result"):
        return "finish"
    return "route_agent"


async def _node_route_agent(state: AgentGraphState) -> AgentGraphState:
    cd = state.get("classification") or {}
    classification = IntentClassification(
        intent=cd.get("intent", "general"),
        primary_agent=cd.get("primary_agent", "router"),
        requires=cd.get("requires", []),
        entities=cd.get("entities", {}),
        confidence=cd.get("confidence", {}),
        crm_action=cd.get("crm_action"),
        reasoning=cd.get("reasoning", ""),
    )
    user = state["user"]
    query = state["query"]
    memory = state["memory"]

    orchestration = await _gather_orchestration_context(user, query, classification, memory)
    agent = classification.primary_agent
    intent = classification.intent
    citations: List[Dict[str, Any]] = []
    actions: List[str] = []

    if agent == "crm":
        response = await _run_crm_agent(user, query, memory)
    elif agent == "meeting":
        response = await _run_meeting_agent(user, query, classification)
    elif agent == "email":
        response = await _run_email_agent(user, query, classification, memory, orchestration)
    elif agent == "knowledge":
        response, citations = await _run_knowledge_agent(user, query)
    elif agent == "task":
        task_result = await _try_crm_action(user, query)
        if task_result:
            response = task_result["response"]
            actions = [task_result.get("action", "create_task")]
        else:
            response = (
                "📋 **Task Agent** — I can create tasks for you. Try:\n"
                "*Create a task to call John tomorrow*"
            )
    elif agent == "analytics":
        response = await _run_analytics_agent(user)
    else:
        llm_response = await generate_completion(query, CRM_SYSTEM)
        response = (
            llm_response
            if not _llm_unconfigured(llm_response)
            else (
                "👋 **AI Sales Assistant**\n\n"
                "• **Create:** *Create a customer named John Smith*\n"
                "• **Update:** *Update John Smith's phone to +1-555-999-9999*\n"
                "• **Delete:** *Delete customer John Smith*\n"
                "• **Meetings:** *What were the action items from our demo?*\n"
                "• **Email:** *Write a follow-up email to John after our demo*\n"
                "• **Knowledge, analytics** — just ask"
            )
        )
        agent = "router"

    return {
        **state,
        "response": response,
        "agent": agent,
        "intent": intent,
        "citations": citations,
        "orchestration": orchestration,
        "actions": actions,
        "routing": "classified_agent",
    }


def _build_agent_graph():
    workflow = StateGraph(AgentGraphState)
    workflow.add_node("prepare", _node_prepare)
    workflow.add_node("crm_fast_path", _node_crm_fast_path)
    workflow.add_node("finalize_crm_action", _node_finalize_crm_action)
    workflow.add_node("classify", _node_classify)
    workflow.add_node("crm_classified_path", _node_crm_classified_path)
    workflow.add_node("route_agent", _node_route_agent)

    workflow.add_edge(START, "prepare")
    workflow.add_edge("prepare", "crm_fast_path")
    workflow.add_conditional_edges(
        "crm_fast_path",
        _route_after_fast_path,
        {"finish": "finalize_crm_action", "classify": "classify"},
    )
    workflow.add_edge("finalize_crm_action", END)
    workflow.add_edge("classify", "crm_classified_path")
    workflow.add_conditional_edges(
        "crm_classified_path",
        _route_after_classified_crm,
        {"finish": "finalize_crm_action", "route_agent": "route_agent"},
    )
    workflow.add_edge("route_agent", END)
    return workflow.compile()


_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = _build_agent_graph()
    return _agent_graph


async def run_agent_graph(user: User, query: str) -> Dict[str, Any]:
    """Multi-agent router powered by LangGraph."""
    graph = get_agent_graph()
    result = await graph.ainvoke(
        {
            "user": user,
            "query": query,
            "effective_query": query,
            "memory": {},
            "classification": None,
            "action_result": None,
            "response": "",
            "agent": "",
            "intent": "",
            "citations": [],
            "orchestration": {},
            "actions": [],
            "routing": "",
        }
    )

    context: Dict[str, Any] = {
        "user_id": user.id,
        "memory": result["memory"],
    }
    if result.get("classification"):
        context["classification"] = result["classification"]
    if result.get("orchestration"):
        context["orchestration"] = result["orchestration"]
    if result.get("action_result"):
        context["action"] = result["action_result"].get("action")
        context["success"] = result["action_result"].get("success")
    if result.get("routing"):
        context["routing"] = result["routing"]

    return {
        "response": result["response"],
        "agent": result["agent"],
        "intent": result["intent"],
        "citations": result["citations"],
        "context": context,
        "actions": result["actions"],
    }


async def stream_response_text(text: str, chunk_size: int = 24) -> AsyncIterator[str]:
    """Yield text in chunks for SSE streaming."""
    i = 0
    while i < len(text):
        yield text[i : i + chunk_size]
        i += chunk_size
