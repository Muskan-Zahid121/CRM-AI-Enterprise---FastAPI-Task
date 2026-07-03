"""Shared LangChain chat model factory."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI


@lru_cache
def get_chat_model() -> "ChatOpenAI":
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY or None,
        temperature=0,
    )
