from decimal import Decimal
from typing import Any, Dict

from app.models.crm import Customer, Deal, Document, Meeting, Task
from app.models.user import User


async def build_overview(user: User) -> Dict[str, Any]:
    customers = await Customer.filter(owner_id=user.id).count()
    deals = await Deal.filter(owner_id=user.id).count()
    open_deals = await Deal.filter(owner_id=user.id).exclude(stage__in=["closed_won", "closed_lost"]).count()
    pending_tasks = await Task.filter(owner_id=user.id).exclude(status="completed").count()
    meetings = await Meeting.filter(owner_id=user.id).count()
    documents = await Document.filter(owner_id=user.id).count()

    all_deals = await Deal.filter(owner_id=user.id).exclude(stage="closed_lost")
    pipeline_value = sum((d.value or Decimal("0")) for d in all_deals)

    recent_deals = await Deal.filter(owner_id=user.id).order_by("-updated_at").limit(5)
    recent_tasks = await Task.filter(owner_id=user.id).order_by("-created_at").limit(5)

    return {
        "customers": customers,
        "deals": deals,
        "open_deals": open_deals,
        "pending_tasks": pending_tasks,
        "meetings": meetings,
        "documents": documents,
        "pipeline_value": float(pipeline_value),
        "recent_deals": [
            {"id": d.id, "title": d.title, "stage": d.stage, "value": float(d.value or 0)}
            for d in recent_deals
        ],
        "recent_tasks": [
            {"id": t.id, "title": t.title, "status": t.status, "priority": t.priority}
            for t in recent_tasks
        ],
    }
