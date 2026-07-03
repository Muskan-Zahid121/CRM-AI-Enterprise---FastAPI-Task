import json
import re
from typing import Any, Dict, Optional

from app.config import settings


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def generate_completion(prompt: str, system: str = "") -> str:
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatOpenAI(model=settings.LLM_MODEL, api_key=settings.OPENAI_API_KEY, temperature=0.3)
            messages = []
            if system:
                messages.append(SystemMessage(content=system))
            messages.append(HumanMessage(content=prompt))
            result = await llm.ainvoke(messages)
            return result.content
        except Exception as exc:
            return f"LLM error: {exc}. Using fallback response."

    return (
        "AI response (configure OPENAI_API_KEY for live LLM):\n\n"
        + prompt[:1200]
    )


async def generate_json_completion(prompt: str, system: str = "") -> Optional[Dict[str, Any]]:
    """Return parsed JSON from the LLM, or None on failure."""
    raw = await generate_completion(prompt, system)
    if raw.startswith("AI response (configure OPENAI_API_KEY") or raw.startswith("LLM error"):
        return None
    try:
        return json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None
