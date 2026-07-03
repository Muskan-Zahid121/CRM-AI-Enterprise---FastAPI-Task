"""LLM-based intent classification with keyword fallback."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings
from app.helpers.agents.crm_actions import detect_crm_action
from app.helpers.llm.provider import generate_json_completion
from app.helpers.prompts import INTENT_CLASSIFIER_SYSTEM

VALID_AGENTS = ("crm", "meeting", "email", "knowledge", "analytics", "task", "router")

INTENT_TO_AGENT = {
    "create_customer": "crm",
    "create_lead": "crm",
    "create_deal": "crm",
    "create_task": "crm",
    "update_customer": "crm",
    "delete_customer": "crm",
    "delete_deal": "crm",
    "show_pipeline": "crm",
    "list_customers": "crm",
    "crm_query": "crm",
    "revenue": "analytics",
    "forecast": "analytics",
    "report": "analytics",
    "analytics_query": "analytics",
    "meeting_summary": "meeting",
    "transcript": "meeting",
    "action_items": "meeting",
    "decisions": "meeting",
    "risks": "meeting",
    "meeting_query": "meeting",
    "pricing": "knowledge",
    "refund_policy": "knowledge",
    "company_policy": "knowledge",
    "product_manual": "knowledge",
    "knowledge_query": "knowledge",
    "write_email": "email",
    "followup_email": "email",
    "thank_you_email": "email",
    "proposal_email": "email",
    "reminder_email": "email",
    "general": "router",
}


@dataclass
class IntentClassification:
    intent: str
    primary_agent: str
    requires: List[str] = field(default_factory=list)
    entities: Dict[str, str] = field(default_factory=dict)
    confidence: Dict[str, float] = field(default_factory=dict)
    crm_action: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "primary_agent": self.primary_agent,
            "requires": self.requires,
            "entities": self.entities,
            "confidence": self.confidence,
            "crm_action": self.crm_action,
            "reasoning": self.reasoning,
        }


def _normalize_agent(agent: str) -> str:
    agent = (agent or "router").lower().strip()
    return agent if agent in VALID_AGENTS else "router"


def _normalize_requires(requires: Any) -> List[str]:
    if not isinstance(requires, list):
        return []
    out: List[str] = []
    for item in requires:
        key = str(item).lower().strip()
        if key in VALID_AGENTS and key not in out and key != "router":
            out.append(key)
    return out


def _normalize_entities(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for key, val in raw.items():
        if val is not None and str(val).strip():
            out[str(key).lower()] = str(val).strip()
    return out


def _normalize_confidence(raw: Any) -> Dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, float] = {}
    for key, val in raw.items():
        agent = str(key).lower()
        if agent not in VALID_AGENTS:
            continue
        try:
            score = float(val)
        except (TypeError, ValueError):
            continue
        out[agent] = max(0.0, min(1.0, score))
    return out


def _parse_classification(data: Dict[str, Any], query: str) -> IntentClassification:
    intent = str(data.get("intent") or "general").lower().strip()
    primary_agent = _normalize_agent(str(data.get("primary_agent") or INTENT_TO_AGENT.get(intent, "router")))
    requires = _normalize_requires(data.get("requires"))
    entities = _normalize_entities(data.get("entities"))
    confidence = _normalize_confidence(data.get("confidence"))
    crm_action = data.get("crm_action") or detect_crm_action(query)
    if crm_action:
        crm_action = str(crm_action)
    reasoning = str(data.get("reasoning") or "").strip()

    if not confidence:
        confidence = {primary_agent: 0.85}
        for req in requires:
            confidence[req] = confidence.get(req, 0.6)

    return IntentClassification(
        intent=intent,
        primary_agent=primary_agent,
        requires=requires,
        entities=entities,
        confidence=confidence,
        crm_action=crm_action if crm_action else None,
        reasoning=reasoning,
    )


def _fallback_classify(query: str, memory: Optional[Dict[str, Any]] = None) -> IntentClassification:
    """Smarter keyword fallback when LLM is unavailable."""
    q = query.lower()
    memory = memory or {}
    entities: Dict[str, str] = {}
    requires: List[str] = []

    crm_action = detect_crm_action(query)
    if crm_action:
        return IntentClassification(
            intent=crm_action,
            primary_agent="crm",
            requires=[],
            entities=entities,
            confidence={"crm": 0.95},
            crm_action=crm_action,
            reasoning="Explicit CRM mutation detected.",
        )

    email_patterns = (
        r"\b(write|draft|compose|send)\b.*\b(email|e-mail)\b",
        r"\b(follow[\s-]?up|thank[\s-]?you|proposal|reminder)\b.*\bemail\b",
        r"\bemail\b.*\b(to|for)\b",
    )
    if any(re.search(p, q) for p in email_patterns):
        intent = "followup_email" if "follow" in q else "write_email"
        if "thank" in q:
            intent = "thank_you_email"
        customer_match = re.search(r"\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", query)
        if customer_match:
            entities["customer"] = customer_match.group(1)
        meeting_match = re.search(
            r"(?:after|from)\s+(?:our\s+|the\s+)?(.+?\s+(?:demo|meeting|call))",
            query,
            re.I,
        )
        if meeting_match:
            entities["meeting"] = meeting_match.group(1).strip()
        if entities.get("customer"):
            requires.append("crm")
        if entities.get("meeting") or "demo" in q or "meeting" in q:
            requires.append("meeting")
        return IntentClassification(
            intent=intent,
            primary_agent="email",
            requires=requires,
            entities=entities,
            confidence={"email": 0.9, "crm": 0.3, "meeting": 0.5},
            reasoning="Email composition request.",
        )

    meeting_content_signals = (
        "action item",
        "action items",
        "transcript",
        "meeting summary",
        "from the meeting",
        "from our demo",
        "from the demo",
        "in the meeting",
        "in yesterday's meeting",
        "discussed in",
        "next steps from",
        "decisions from",
        "what did ",
        "what were ",
        "who said",
        "who asked",
    )
    has_meeting_context = any(s in q for s in ("meeting", "demo", "call", "transcript"))
    asks_about_content = any(s in q for s in meeting_content_signals) or (
        has_meeting_context
        and any(w in q for w in ("action", "summary", "decision", "risk", "discussed", "said", "asked", "items"))
    )
    if asks_about_content:
        intent = "action_items" if "action" in q else "meeting_summary"
        if "transcript" in q:
            intent = "transcript"
        demo_match = re.search(
            r"\b(?:from|after|during)\s+(?:the\s+|our\s+|yesterday'?s\s+)?([\w\s\-']+(?:demo|meeting|call))\b",
            query,
            re.I,
        )
        if demo_match:
            entities["meeting"] = demo_match.group(1).strip().title()
        return IntentClassification(
            intent=intent,
            primary_agent="meeting",
            requires=["meeting"],
            entities=entities,
            confidence={"meeting": 0.92, "crm": 0.15, "knowledge": 0.1},
            reasoning="User is asking about meeting content, not CRM records.",
        )

    if any(w in q for w in ("document", "policy", "policies", "pricing", "refund", "manual", "knowledge", "rag")) or any(
        p in q for p in ("what does", "according to", "tell me about our")
    ):
        intent = "refund_policy" if "refund" in q else "knowledge_query"
        return IntentClassification(
            intent=intent,
            primary_agent="knowledge",
            requires=["knowledge"],
            entities=entities,
            confidence={"knowledge": 0.88},
            reasoning="Document or policy lookup.",
        )

    if any(w in q for w in ("analytics", "forecast", "revenue", "report", "kpi", "conversion", "pipeline value")):
        if not any(w in q for w in ("create", "add", "update", "delete")):
            return IntentClassification(
                intent="analytics_query",
                primary_agent="analytics",
                requires=[],
                entities=entities,
                confidence={"analytics": 0.9},
                reasoning="Analytics or reporting question.",
            )

    crm_read_patterns = (
        r"\b(latest|recent|newest|last)\s+customer\b",
        r"\b(list|show|get)\s+(all\s+)?customers\b",
        r"\bhow many\s+customers\b",
        r"\bmy\s+(customers|leads|deals|pipeline)\b",
        r"\bshow\s+pipeline\b",
    )
    if any(re.search(p, q) for p in crm_read_patterns):
        return IntentClassification(
            intent="crm_query",
            primary_agent="crm",
            requires=["crm"],
            entities=entities,
            confidence={"crm": 0.85},
            reasoning="Direct CRM data lookup.",
        )

    if memory.get("name") and any(w in q for w in ("update", "change", "set")):
        entities["customer"] = memory["name"]
        return IntentClassification(
            intent="update_customer",
            primary_agent="crm",
            requires=["crm"],
            entities=entities,
            confidence={"crm": 0.7},
            reasoning="Likely follow-up CRM update using conversation memory.",
        )

    return IntentClassification(
        intent="general",
        primary_agent="router",
        requires=[],
        entities=entities,
        confidence={"router": 0.5},
        reasoning="No strong domain signal; general assistant.",
    )


async def classify_intent(query: str, memory: Optional[Dict[str, Any]] = None) -> IntentClassification:
    """Classify user intent using LLM with structured output, falling back to heuristics."""
    memory = memory or {}

    if not settings.OPENAI_API_KEY:
        return _fallback_classify(query, memory)

    memory_hint = json.dumps(memory) if memory else "{}"
    prompt = (
        f"User message:\n{query}\n\n"
        f"Conversation memory (last entity touched):\n{memory_hint}\n\n"
        "Classify intent. Return JSON only."
    )

    data = await generate_json_completion(prompt, INTENT_CLASSIFIER_SYSTEM)
    if not data:
        return _fallback_classify(query, memory)

    try:
        return _parse_classification(data, query)
    except Exception:
        return _fallback_classify(query, memory)
