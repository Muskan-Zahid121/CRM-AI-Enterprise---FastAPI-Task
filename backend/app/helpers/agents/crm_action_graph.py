"""LangGraph + LangChain workflow for CRM action detection (no regex)."""

from __future__ import annotations

from typing import Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.config import settings
from app.helpers.llm.chat import get_chat_model
from app.helpers.prompts import CRM_ACTION_DETECTOR_SYSTEM

CrmActionName = Literal[
    "create_customer",
    "create_lead",
    "create_deal",
    "create_task",
    "update_customer",
    "delete_customer",
    "latest_customer",
    "list_customers",
    "count_customers",
]

VALID_CRM_ACTIONS = frozenset(
    {
        "create_customer",
        "create_lead",
        "create_deal",
        "create_task",
        "update_customer",
        "delete_customer",
        "latest_customer",
        "list_customers",
        "count_customers",
    }
)


class CrmActionClassification(BaseModel):
    """Structured CRM mutation classification from LangChain."""

    crm_action: Optional[CrmActionName] = Field(
        default=None,
        description="Explicit CRM mutation, or null when the message is not a CRM command.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence that crm_action is correct.",
    )
    reasoning: str = Field(default="", description="One sentence explaining the decision.")


class CrmActionState(TypedDict):
    query: str
    crm_action: Optional[str]
    confidence: float
    detection_source: Optional[str]
    reasoning: Optional[str]


async def _classify_node(state: CrmActionState) -> CrmActionState:
    if not settings.OPENAI_API_KEY:
        return {
            **state,
            "crm_action": None,
            "confidence": 0.0,
            "detection_source": None,
            "reasoning": "OPENAI_API_KEY not configured.",
        }

    try:
        classifier = get_chat_model().with_structured_output(CrmActionClassification)
        result: CrmActionClassification = await classifier.ainvoke(
            [
                ("system", CRM_ACTION_DETECTOR_SYSTEM),
                ("human", f"User message:\n{state['query']}"),
            ]
        )
        if (
            result.crm_action
            and result.confidence >= 0.7
            and result.crm_action in VALID_CRM_ACTIONS
        ):
            return {
                **state,
                "crm_action": result.crm_action,
                "confidence": result.confidence,
                "detection_source": "llm",
                "reasoning": result.reasoning,
            }
    except Exception:
        pass

    return {
        **state,
        "crm_action": None,
        "confidence": 0.0,
        "detection_source": None,
        "reasoning": None,
    }


def _build_crm_action_graph():
    workflow = StateGraph(CrmActionState)
    workflow.add_node("classify", _classify_node)
    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", END)
    return workflow.compile()


_crm_action_graph = None


def get_crm_action_graph():
    global _crm_action_graph
    if _crm_action_graph is None:
        _crm_action_graph = _build_crm_action_graph()
    return _crm_action_graph


async def run_crm_action_detection(query: str) -> CrmActionState:
    graph = get_crm_action_graph()
    return await graph.ainvoke(
        {
            "query": query,
            "crm_action": None,
            "confidence": 0.0,
            "detection_source": None,
            "reasoning": None,
        }
    )
