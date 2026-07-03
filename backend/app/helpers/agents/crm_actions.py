import json
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.database.redis_client import cache_get, cache_set
from app.helpers.workflow_engine import trigger_workflows_for_event
from app.helpers.agents.query_parser import (
    _clean_name,
    enrich_with_llm,
    parse_customer_fields,
    parse_customer_reference,
    parse_deal_fields,
    parse_lead_fields,
    parse_task_fields,
)
from app.models.crm import Activity, Customer, Deal, Lead, Task
from app.models.user import User

PENDING_ACTION_KEY = "chat:pending_action:{user_id}"


def _is_valid_customer_name(name: Optional[str]) -> bool:
    if not name or len(name) < 2:
        return False
    lower = name.lower()
    if " customer" in lower or lower.endswith(" customer"):
        return False
    if lower in {"customer", "the", "a", "new"}:
        return False
    return True


def _is_update_customer_query(q: str) -> bool:
    if any(w in q for w in ("update", "set", "change", "edit")):
        if any(w in q for w in ("phone", "email", "company", "customer")):
            return True
        if re.search(r"update\s+[\w\s'-]+[''']s\s+(phone|email|company)", q):
            return True
    has_fields = any(w in q for w in ("company", "email", "phone"))
    if has_fields and re.search(r"for\s+(?:the\s+)?[\w\s'-]+\s+customer\b", q):
        return True
    if has_fields and re.search(r"\bfor\s+(?:the\s+)?[\w\s'-]+", q) and not re.search(
        r"(?:create|add|new|register)\s+(?:a\s+)?(?:new\s+)?customer\b", q
    ):
        return True
    return False


def _is_delete_customer_query(q: str) -> bool:
    if any(w in q for w in ("delete", "remove")) and "customer" in q:
        return True
    return bool(re.search(r"(?:delete|remove)\s+(?:the\s+)?customer\b", q))


def _is_create_customer_query(q: str) -> bool:
    if _is_update_customer_query(q) or _is_delete_customer_query(q):
        return False
    if re.search(r"(?:create|add|new|register)\s+(?:a\s+)?(?:new\s+)?customer\b", q):
        return True
    return bool(re.search(r"customer\s+(?:named|called)\s+", q))


def is_confirmation(query: str) -> bool:
    q = query.strip().lower()
    return bool(
        re.match(
            r"^(yes|yeah|yep|yup|sure|ok|okay|proceed|go ahead|confirm|do it|please do|yes proceed|yes, proceed)[\s!.]*$",
            q,
        )
    )


def is_crm_related(query: str) -> bool:
    return detect_crm_action(query) is not None or _is_update_customer_query(query.lower()) or _is_delete_customer_query(query.lower())


async def remember_pending_action(user_id: int, query: str) -> None:
    if is_crm_related(query) and not is_confirmation(query):
        await cache_set(PENDING_ACTION_KEY.format(user_id=user_id), query, ttl=3600)


async def get_pending_action(user_id: int) -> Optional[str]:
    raw = await cache_get(PENDING_ACTION_KEY.format(user_id=user_id))
    return raw if raw else None


async def clear_pending_action(user_id: int) -> None:
    await cache_set(PENDING_ACTION_KEY.format(user_id=user_id), "", ttl=1)


def detect_crm_action(query: str) -> Optional[str]:
    q = query.lower()
    if _is_delete_customer_query(q):
        return "delete_customer"
    if _is_update_customer_query(q):
        return "update_customer"
    if _is_create_customer_query(q):
        return "create_customer"
    if any(w in q for w in ("create", "add", "new")) and "lead" in q:
        return "create_lead"
    if any(w in q for w in ("create", "add", "new")) and "deal" in q:
        return "create_deal"
    if any(w in q for w in ("create", "add", "new")) and "task" in q:
        return "create_task"
    if any(w in q for w in ("latest", "recent", "newest", "last")) and "customer" in q:
        return "latest_customer"
    if any(w in q for w in ("list", "show", "get", "all")) and "customer" in q:
        return "list_customers"
    if any(w in q for w in ("how many", "count", "total")) and "customer" in q:
        return "count_customers"
    return None


def _score_customer_match(name_lower: str, customer_name: str) -> int:
    cn = customer_name.lower().strip()
    if cn == name_lower:
        return 100
    name_words = name_lower.split()
    cn_words = cn.split()
    if all(w in cn_words for w in name_words):
        return 70 - len(cn)
    if name_lower in cn:
        return 50 - len(cn)
    if cn in name_lower:
        return 40
    return 0


async def _find_customer_by_name(user: User, name: str) -> Optional[Customer]:
    name = _clean_name(name) or name.strip()
    if not name:
        return None

    exact = await Customer.filter(owner_id=user.id, name__iexact=name).first()
    if exact:
        return exact

    rows = await Customer.filter(owner_id=user.id).all()
    name_lower = name.lower()
    best: Optional[Tuple[Customer, int]] = None
    for c in rows:
        score = _score_customer_match(name_lower, c.name)
        if score > 0 and (best is None or score > best[1]):
            best = (c, score)

    if best and best[1] >= 40:
        return best[0]
    return None


async def _resolve_customer(user: User, query: str) -> Optional[Customer]:
    ref = parse_customer_reference(query)
    if ref:
        found = await _find_customer_by_name(user, ref)
        if found:
            return found

    raw = await cache_get(f"chat:memory:{user.id}")
    if raw:
        try:
            memory = json.loads(raw)
            if memory.get("type") == "customer" and memory.get("id"):
                customer = await Customer.filter(id=memory["id"], owner_id=user.id).first()
                if customer:
                    return customer
            if memory.get("type") == "customer" and memory.get("name"):
                found = await _find_customer_by_name(user, memory["name"])
                if found:
                    return found
        except json.JSONDecodeError:
            pass
    return None


def _customer_response(customer: Customer, heading: str) -> str:
    return (
        f"{heading}\n\n"
        f"• **Name:** {customer.name}\n"
        f"• **Company:** {customer.company or '—'}\n"
        f"• **Email:** {customer.email or '—'}\n"
        f"• **Phone:** {customer.phone or '—'}\n"
        f"• **ID:** {customer.id}"
    )


async def execute_crm_action(user: User, query: str) -> Optional[Dict[str, Any]]:
    action = detect_crm_action(query)
    if not action:
        return None

    if action == "delete_customer":
        customer = await _resolve_customer(user, query)
        if not customer:
            rows = await Customer.filter(owner_id=user.id).order_by("-created_at").limit(5)
            lines = "\n".join(f"• **{c.name}** (ID: {c.id})" for c in rows) or "No customers found."
            return {
                "action": action,
                "success": False,
                "response": f"I couldn't find that customer to delete.\n\n**Recent customers:**\n{lines}",
            }

        name = customer.name
        customer_id = customer.id
        await Activity.filter(customer_id=customer_id, owner_id=user.id).delete()
        await customer.delete()
        return {
            "action": action,
            "success": True,
            "response": f"🗑️ **Customer deleted:** {name} (ID: {customer_id})",
        }

    if action == "update_customer":
        customer = await _resolve_customer(user, query)
        if not customer:
            return {
                "action": action,
                "success": False,
                "response": "I couldn't find that customer. Try:\n\n*Update John Smith's phone number to +1-555-999-9999*",
            }

        fields = parse_customer_fields(query)
        fields = await enrich_with_llm(query, fields, "update_customer")
        updated: List[str] = []
        if fields.get("company"):
            customer.company = fields["company"]
            updated.append("company")
        if fields.get("email"):
            customer.email = fields["email"]
            updated.append("email")
        if fields.get("phone"):
            customer.phone = str(fields["phone"]).strip()
            updated.append("phone")

        if not updated:
            return {
                "action": action,
                "success": False,
                "response": f"Tell me what to update. Example:\n\n*Update {customer.name}'s phone number to +1-555-999-9999*",
            }

        await customer.save()
        await Activity.create(
            owner_id=user.id,
            customer_id=customer.id,
            activity_type="customer_updated",
            description=f"AI updated customer {customer.name}: {', '.join(updated)}",
        )
        return {
            "action": action,
            "success": True,
            "entity": {"type": "customer", "id": customer.id, "name": customer.name},
            "response": _customer_response(customer, f"✅ **Customer updated** ({', '.join(updated)})"),
        }

    if action == "create_customer":
        fields = parse_customer_fields(query)
        fields = await enrich_with_llm(query, fields, "create_customer")
        if not _is_valid_customer_name(fields.get("name")):
            return {
                "action": action,
                "success": False,
                "response": "I need a valid customer name. Example:\n\n"
                "*Create a customer named John Smith. Company: Acme. Email: john@acme.com*",
            }
        if fields.get("email"):
            existing = await Customer.filter(owner_id=user.id, email=fields["email"]).first()
            if existing:
                return {
                    "action": action,
                    "success": True,
                    "entity": {"type": "customer", "id": existing.id, "name": existing.name},
                    "response": f"Customer **{existing.name}** already exists with that email (ID: {existing.id}).",
                }
        existing_by_name = await _find_customer_by_name(user, fields["name"] or "")
        if existing_by_name and existing_by_name.name.lower() == (fields["name"] or "").lower():
            return {
                "action": action,
                "success": False,
                "response": f"Customer **{existing_by_name.name}** already exists (ID: {existing_by_name.id}). "
                f"Say *Update {existing_by_name.name}'s phone to ...* to edit instead.",
            }
        customer = await Customer.create(
            owner_id=user.id,
            name=fields["name"],
            email=fields.get("email"),
            phone=fields.get("phone"),
            company=fields.get("company"),
            status="active",
        )
        await Activity.create(
            owner_id=user.id,
            customer_id=customer.id,
            activity_type="customer_created",
            description=f"AI created customer {customer.name}",
        )
        return {
            "action": action,
            "success": True,
            "entity": {"type": "customer", "id": customer.id, "name": customer.name},
            "response": _customer_response(customer, "✅ **Customer created successfully**"),
        }

    if action == "create_lead":
        fields = parse_lead_fields(query)
        fields = await enrich_with_llm(query, fields, "create_lead")
        if not fields.get("name"):
            return {
                "action": action,
                "success": False,
                "response": "Please provide a lead name. Example:\n\n"
                "*Add a lead named Ali Hassan from Facebook Ads interested in Enterprise CRM*",
            }
        lead = await Lead.create(
            owner_id=user.id,
            name=fields["name"],
            email=fields.get("email"),
            company=fields.get("company"),
            source=fields.get("source"),
            notes=fields.get("notes"),
            stage="new",
            score=0,
        )
        await trigger_workflows_for_event(
            user,
            "lead_created",
            {"lead_name": lead.name, "company": lead.company or "Unknown"},
        )
        return {
            "action": action,
            "success": True,
            "entity": {"type": "lead", "id": lead.id, "name": lead.name},
            "response": (
                f"✅ **Lead created**\n\n"
                f"• **Name:** {lead.name}\n"
                f"• **Company / Interest:** {lead.company or '—'}\n"
                f"• **Source:** {lead.source or '—'}\n"
                f"• **Email:** {lead.email or '—'}\n"
                f"• **Stage:** {lead.stage}\n"
                f"• **ID:** {lead.id}"
            ),
        }

    if action == "create_deal":
        fields = parse_deal_fields(query)
        fields = await enrich_with_llm(query, fields, "create_deal")
        deal = await Deal.create(
            owner_id=user.id,
            title=fields["title"],
            value=Decimal(str(fields.get("value") or 0)),
            stage=fields.get("stage") or "lead",
            probability=50,
        )
        return {
            "action": action,
            "success": True,
            "entity": {"type": "deal", "id": deal.id, "title": deal.title},
            "response": (
                f"✅ **Deal created**\n\n"
                f"• **Title:** {deal.title}\n"
                f"• **Value:** ${float(deal.value or 0):,.2f}\n"
                f"• **Stage:** {deal.stage}\n"
                f"• **ID:** {deal.id}"
            ),
        }

    if action == "create_task":
        fields = parse_task_fields(query)
        title = fields.get("title") or query[:80]
        priority = fields.get("priority") or "medium"
        task = await Task.create(owner_id=user.id, title=title, status="pending", priority=priority)
        return {
            "action": action,
            "success": True,
            "entity": {"type": "task", "id": task.id, "title": task.title},
            "response": f"✅ **Task created:** {task.title} (ID: {task.id}, priority: {priority})",
        }

    if action == "latest_customer":
        customer = await Customer.filter(owner_id=user.id).order_by("-created_at").first()
        if not customer:
            return {"action": action, "success": True, "response": "You don't have any customers yet."}
        return {
            "action": action,
            "success": True,
            "entity": {"type": "customer", "id": customer.id, "name": customer.name},
            "response": _customer_response(customer, "📋 **Latest customer**"),
        }

    if action == "list_customers":
        rows = await Customer.filter(owner_id=user.id).order_by("-created_at").limit(10)
        if not rows:
            return {"action": action, "success": True, "response": "No customers found yet."}
        lines = [f"• **{c.name}** — {c.company or 'No company'} ({c.email or 'no email'})" for c in rows]
        return {"action": action, "success": True, "response": f"📋 **Your customers** ({len(rows)} shown)\n\n" + "\n".join(lines)}

    if action == "count_customers":
        count = await Customer.filter(owner_id=user.id).count()
        return {"action": action, "success": True, "response": f"You have **{count}** customer{'s' if count != 1 else ''} in the CRM."}

    return None
