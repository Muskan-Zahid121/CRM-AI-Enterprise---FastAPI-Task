"""Natural-language field extraction for CRM chat commands."""

import json
import re
from typing import Any, Dict, Optional

from app.config import settings

# Lookahead stops name capture before trailing clauses (no bare $ — avoids swallowing full string)
_NAME_STOP = (
    r"(?=\s+from\s+|\s+at\s+|\s+interested\s+in\s+|\s+with\s+|\s+email\b|\s+phone\b|\s+company\b|"
    r",\s*company|\s+company:|\s+email:|\s+phone:|\s+source\b|\s+worth\b|\s+value\b|\.(?:\s|$))"
)


def _field(patterns: list[str], text: str) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().strip(".,;")
            return val or None
    return None


def _clean_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name = name.strip().strip(".,;")
    for prefix in ("the ", "a "):
        if name.lower().startswith(prefix):
            name = name[len(prefix) :].strip()
    for suffix in (" customer", " lead"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name or None


def _parse_person_name(query: str, entity: str) -> Optional[str]:
    entity_pat = entity.replace("|", "|")
    return _clean_name(
        _field(
            [
                rf"(?:add|create|new|register)\s+(?:a\s+)?(?:{entity_pat})\s+(?:named|called)\s+([A-Za-z][A-Za-z\s\-'.]+?){_NAME_STOP}",
                rf"(?:{entity_pat})\s+(?:named|called)\s+([A-Za-z][A-Za-z\s\-'.]+?){_NAME_STOP}",
                rf"(?:add|create)\s+(?:a\s+)?(?:{entity_pat})\s+for\s+([A-Za-z][A-Za-z\s\-'.]+?){_NAME_STOP}",
            ],
            query,
        )
    )


def _parse_email(text: str) -> Optional[str]:
    return _field(
        [
            r"email\s+(?:is\s+|:|to\s+)\s*([\w.+-]+@[\w.-]+\.\w+)",
            r"email[:\s]+([\w.+-]+@[\w.-]+\.\w+)",
        ],
        text,
    )


def _parse_phone(text: str) -> Optional[str]:
    return _field(
        [
            r"(?:phone\s+number|phone)\s+(?:to\s+|is\s+|:\s*)([+()\d\- ]+?)(?:\s+for\b|\s+and\b|\s+from\b|\s*$|\.)",
            r"phone\s+(?:is\s+|:)\s*([+\d\-() ]+?)(?:\s+for\b|\s+and\b|\s+from\b|\s*$|\.)",
            r"phone[:\s]+([+\d\-() ]+)",
        ],
        text,
    )


def _parse_company(text: str) -> Optional[str]:
    return _field(
        [
            r"interested\s+in\s+(.+?)(?:\.|$)",
            r"(?:works\s+at|at)\s+([A-Za-z0-9][A-Za-z0-9\s\-'.&]+?)(?:\s+interested|\s+from|\s+email|\s+phone|\.|$)",
            r"(?:add\s+(?:the\s+)?)?company\s+(?:is\s+|to\s+)?([A-Za-z0-9][A-Za-z0-9\s\-'.&]*?)(?:\s+and\s|\s+email|\s+phone|\s+for\b|\s*$|\.(?:\s|$))",
            r"company[:\s]+([^,\n]+?)(?:\s+and\s|\s+email|\s+phone|\s+for\b|$)",
        ],
        text,
    )


def _parse_source(text: str) -> Optional[str]:
    return _field(
        [
            r"from\s+(.+?)(?:\s+interested\s+in|\s+at\s+|\s+with\s+|\s+email\b|\s+phone\b|\.|$)",
            r"source[:\s]+(.+?)(?:\.|,|\s+interested|\s+company|$)",
        ],
        text,
    )


def parse_lead_fields(query: str) -> Dict[str, Optional[str]]:
    name = _parse_person_name(query, "lead")
    company = _parse_company(query)
    source = _parse_source(query)

    return {
        "name": name,
        "company": company,
        "source": source,
        "email": _parse_email(query),
        "phone": _parse_phone(query),
        "notes": f"Interested in {company}" if company else None,
    }


def parse_customer_fields(query: str) -> Dict[str, Optional[str]]:
    name = _parse_person_name(query, "customer")
    if not name:
        name = _clean_name(
            _field(
                [
                    rf"for\s+(?:the\s+)?([A-Za-z][A-Za-z\s\-'.]+?){_NAME_STOP}",
                ],
                query,
            )
        )

    return {
        "name": name,
        "company": _parse_company(query),
        "email": _parse_email(query),
        "phone": _parse_phone(query),
    }


def parse_customer_reference(query: str) -> Optional[str]:
    return _clean_name(
        _field(
            [
                r"(?:update|edit|change|set|delete|remove)\s+(?:the\s+)?customer\s+(?:named\s+|called\s+)?([A-Za-z][A-Za-z\s\-'.]+?)(?:[''']s|\.\s|$|\s+(?:phone|email|company))",
                r"(?:update|edit|change|set)\s+([A-Za-z][A-Za-z\s\-'.]+?)[''']s\s+(?:phone|email|company)",
                r"(?:update|edit|change|set)\s+([A-Za-z][A-Za-z\s\-'.]+?)\s+(?:phone|email|company)",
                r"for\s+(?:the\s+)?([A-Za-z][A-Za-z\s\-'.]+?)\s+customer\b",
                r"(?:delete|remove)\s+(?:customer\s+)?([A-Za-z][A-Za-z\s\-'.]+?)(?:\.\s|$|\s+customer\b)",
            ],
            query,
        )
    )


def parse_deal_fields(query: str) -> Dict[str, Any]:
    title = _field(
        [
            r"(?:deal|opportunity)\s+(?:for|named|called|titled)\s+(.+?)(?:\s+worth|\s+value|\s+at\s+\$|\.|,|$)",
            r"(?:create|add)\s+(?:a\s+)?deal\s+(?:for\s+)?(.+?)(?:\s+worth|\s+value|\.|,|$)",
            r"deal[:\s]+(.+?)(?:\s+worth|\s+value|\.|,|$)",
        ],
        query,
    )
    value_m = re.search(r"(?:worth|value|at)\s+\$?\s*([\d,]+(?:\.\d+)?)", query, re.I)
    stage = _field([r"stage[:\s]+(\w+)"], query)
    return {
        "title": (title or "New Opportunity").strip(),
        "value": float(value_m.group(1).replace(",", "")) if value_m else 0,
        "stage": stage,
    }


def parse_task_fields(query: str) -> Dict[str, Optional[str]]:
    title = _field(
        [
            r"(?:create|add)\s+(?:a\s+)?task\s+(?:to\s+)?(.+?)(?:\.|$)",
            r"(?:task|todo|reminder)\s+(?:to\s+)?(.+?)(?:\.|$)",
        ],
        query,
    )
    priority = _field([r"priority[:\s]+(low|medium|high|urgent)", r"(high|urgent)\s+priority"], query)
    return {"title": title, "priority": (priority or "medium").lower()}


async def enrich_with_llm(query: str, regex_fields: Dict[str, Any], action: str) -> Dict[str, Any]:
    """Optional LLM pass to fill gaps when OpenAI is configured."""
    if not settings.OPENAI_API_KEY:
        return regex_fields

    try:
        from app.helpers.llm.provider import generate_completion

        prompt = (
            f"Extract structured CRM data from this message. Action hint: {action}\n"
            f"Message: {query}\n\n"
            "Return ONLY valid JSON with keys: name, company, email, phone, source, notes, title, value.\n"
            "Use null for missing fields. Do not include explanation."
        )
        raw = await generate_completion(prompt, "You extract CRM fields from natural language. JSON only.")
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        merged = {**regex_fields}
        for key, val in data.items():
            if val and not merged.get(key):
                merged[key] = val
        return merged
    except Exception:
        return regex_fields


def format_rag_answer(
    query: str,
    chunks: list[dict],
    stats: dict | None = None,
    doc_titles: list[str] | None = None,
) -> str:
    """Readable knowledge answer without requiring an LLM."""
    if not chunks:
        if stats is not None:
            from app.helpers.agents.orchestration import format_knowledge_empty

            return format_knowledge_empty(query, stats, doc_titles or [])
        return (
            "I couldn't find relevant content in your knowledge base. "
            "Upload documents on the **Knowledge Base** page first."
        )

    parts = ["📚 **From your knowledge base:**\n"]
    seen: set[str] = set()
    for i, chunk in enumerate(chunks[:4], 1):
        content = (chunk.get("content") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)
        meta = chunk.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}
        title = (meta or {}).get("title", f"Document {chunk.get('document_id', '?')}")
        score = chunk.get("score")
        score_txt = f" (relevance: {float(score):.0%})" if score is not None else ""
        snippet = content if len(content) <= 400 else content[:400] + "..."
        parts.append(f"**{i}. {title}**{score_txt}\n{snippet}")

    parts.append("\n*Upload more docs on Knowledge Base for richer answers.*")
    return "\n\n".join(parts)
