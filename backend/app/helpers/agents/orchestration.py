"""Gather context from CRM, meetings, and knowledge for multi-agent orchestration."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.helpers.rag.retriever import rag_statistics, retrieve_similar
from app.models.crm import Customer, Document, Meeting
from app.models.user import User


def _score_text_match(hint: str, text: str) -> int:
    hint_lower = hint.lower().strip()
    text_lower = text.lower().strip()
    if not hint_lower or not text_lower:
        return 0
    if hint_lower == text_lower:
        return 100
    if hint_lower in text_lower:
        return 80 - len(text_lower) // 10
    hint_words = [w for w in re.split(r"\W+", hint_lower) if len(w) > 2]
    if hint_words and all(w in text_lower for w in hint_words):
        return 60
    overlap = sum(1 for w in hint_words if w in text_lower)
    if overlap:
        return 20 + overlap * 10
    return 0


async def find_meeting(user: User, query: str, meeting_hint: Optional[str] = None) -> Optional[Meeting]:
    rows = await Meeting.filter(owner_id=user.id).order_by("-meeting_date", "-created_at")
    if not rows:
        return None

    hints: List[str] = []
    if meeting_hint:
        hints.append(meeting_hint)
    demo_match = re.search(
        r"\b(?:from|after|during)\s+(?:the\s+|our\s+|yesterday'?s\s+)?([\w\s\-']+(?:demo|meeting|call))\b",
        query,
        re.I,
    )
    if demo_match:
        hints.append(demo_match.group(0).strip())

    best: Optional[tuple[Meeting, int]] = None
    for meeting in rows:
        for hint in hints:
            score = _score_text_match(hint, meeting.title)
            if score > 0 and (best is None or score > best[1]):
                best = (meeting, score)
        if not hints:
            score = _score_text_match(query, meeting.title)
            if score > 0 and (best is None or score > best[1]):
                best = (meeting, score)

    if best and best[1] >= 20:
        return best[0]
    return rows[0] if rows else None


async def _find_customer_by_name(user: User, name: str) -> Optional[Customer]:
    name = name.strip()
    if not name:
        return None
    exact = await Customer.filter(owner_id=user.id, name__iexact=name).first()
    if exact:
        return exact
    rows = await Customer.filter(owner_id=user.id).all()
    name_lower = name.lower()
    best: Optional[tuple[Customer, int]] = None
    for customer in rows:
        cn = customer.name.lower()
        score = 0
        if cn == name_lower:
            score = 100
        elif name_lower in cn:
            score = 70
        elif cn in name_lower:
            score = 50
        elif all(w in cn for w in name_lower.split()):
            score = 40
        if score > 0 and (best is None or score > best[1]):
            best = (customer, score)
    return best[0] if best else None


async def gather_crm_context(user: User, entities: Dict[str, str], memory: Dict[str, Any]) -> str:
    lines: List[str] = []

    customer_name = entities.get("customer")
    if not customer_name and memory.get("type") == "customer":
        customer_name = memory.get("name")

    if customer_name:
        customer = await _find_customer_by_name(user, customer_name)
        if customer:
            lines.append(
                f"Customer: {customer.name} | Company: {customer.company or '—'} | "
                f"Email: {customer.email or '—'} | Phone: {customer.phone or '—'}"
            )
        else:
            lines.append(f"Customer '{customer_name}' not found in CRM.")
    elif memory.get("type") == "customer" and memory.get("name"):
        lines.append(f"Recent context customer: {memory['name']}")

    if not lines:
        recent = await Customer.filter(owner_id=user.id).order_by("-created_at").limit(3)
        if recent:
            lines.append("Recent customers: " + "; ".join(f"{c.name} ({c.company or 'no company'})" for c in recent))

    return "\n".join(lines) if lines else "No CRM context available."


def _format_action_items(action_items: Any) -> str:
    if not action_items:
        return ""
    if isinstance(action_items, str):
        return action_items
    if isinstance(action_items, list):
        parts = []
        for item in action_items:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("title") or json.dumps(item))
            else:
                parts.append(str(item))
        return "\n".join(f"- {p}" for p in parts if p)
    return str(action_items)


async def gather_meeting_context(user: User, query: str, entities: Dict[str, str]) -> str:
    meeting_hint = entities.get("meeting")
    meeting = await find_meeting(user, query, meeting_hint)
    if not meeting:
        count = await Meeting.filter(owner_id=user.id).count()
        if count == 0:
            return "No meetings saved. Add transcripts on the Meetings page."
        titles = await Meeting.filter(owner_id=user.id).order_by("-created_at").limit(5).values_list("title", flat=True)
        return f"No matching meeting found. Saved meetings: {', '.join(titles)}"

    parts = [f"Meeting: {meeting.title}"]
    if meeting.meeting_date:
        parts.append(f"Date: {meeting.meeting_date.isoformat()}")
    if meeting.summary:
        parts.append(f"Summary:\n{meeting.summary}")
    if meeting.action_items:
        parts.append(f"Stored action items:\n{_format_action_items(meeting.action_items)}")
    if meeting.transcript:
        excerpt = meeting.transcript if len(meeting.transcript) <= 3000 else meeting.transcript[:3000] + "..."
        parts.append(f"Transcript:\n{excerpt}")
    elif not meeting.summary:
        parts.append("No transcript or summary stored for this meeting.")

    return "\n\n".join(parts)


async def gather_knowledge_context(user: User, query: str) -> Dict[str, Any]:
    stats = await rag_statistics(user.id)
    citations = await retrieve_similar(user.id, query, limit=5)
    doc_titles: List[str] = []
    if stats.get("indexed_documents"):
        docs = await Document.filter(owner_id=user.id, indexed=True).limit(10).values_list("title", flat=True)
        doc_titles = list(docs)
    return {
        "stats": stats,
        "citations": citations,
        "doc_titles": doc_titles,
    }


def format_knowledge_empty(query: str, stats: Dict[str, Any], doc_titles: List[str]) -> str:
    indexed = int(stats.get("indexed_documents") or 0)
    total = int(stats.get("total_documents") or 0)
    topic = query.strip().rstrip("?")

    if indexed == 0:
        if total > 0:
            return (
                f"I searched your knowledge base ({total} document{'s' if total != 1 else ''} uploaded) "
                f"but none are indexed yet. Open the **Knowledge Base** page and re-index your documents."
            )
        return (
            "I searched your knowledge base but found no indexed documents. "
            "Upload policies, pricing sheets, or manuals on the **Knowledge Base** page first."
        )

    title_hint = ""
    if doc_titles:
        shown = doc_titles[:5]
        extra = f" (+{len(doc_titles) - 5} more)" if len(doc_titles) > 5 else ""
        title_hint = f" Indexed documents include: {', '.join(shown)}{extra}."

    return (
        f"I searched {indexed} indexed document{'s' if indexed != 1 else ''} "
        f"but couldn't find anything about **{topic}**.{title_hint}\n\n"
        "Try rephrasing your question or upload the relevant document on the **Knowledge Base** page."
    )
