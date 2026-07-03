from fastapi import APIRouter, Depends, Query

from app.middleware.auth import get_current_user
from app.models.ai import AuditLog, Notification
from app.models.crm import Customer, Deal, Document, Task
from app.models.user import User
from app.helpers.rag.retriever import rag_statistics
from app.helpers.dashboard import build_overview

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
users_router = APIRouter(prefix="/users", tags=["users"])


@dashboard_router.get("")
async def dashboard(user: User = Depends(get_current_user)):
    return {"success": True, **await build_overview(user)}


@dashboard_router.get("/stats")
async def dashboard_stats(user: User = Depends(get_current_user)):
    overview = await build_overview(user)
    rag = await rag_statistics(user.id)
    return {"success": True, "stats": {**overview, "rag": rag}}


@dashboard_router.get("/recent")
async def dashboard_recent(user: User = Depends(get_current_user)):
    overview = await build_overview(user)
    return {"success": True, "recent_deals": overview["recent_deals"], "recent_tasks": overview["recent_tasks"]}


@dashboard_router.get("/activity")
async def dashboard_activity(user: User = Depends(get_current_user)):
    from app.models.crm import Activity
    rows = await Activity.filter(owner_id=user.id).order_by("-created_at").limit(20)
    return {"success": True, "activity": [{"id": a.id, "type": a.activity_type, "description": a.description} for a in rows]}


@analytics_router.get("/dashboard")
async def analytics_dashboard(user: User = Depends(get_current_user)):
    return await dashboard_stats(user)


@analytics_router.get("/sales")
async def analytics_sales(user: User = Depends(get_current_user)):
    deals = await Deal.filter(owner_id=user.id)
    return {"success": True, "total_deals": len(deals), "won": sum(1 for d in deals if d.stage == "closed_won")}


@analytics_router.get("/revenue")
async def analytics_revenue(user: User = Depends(get_current_user)):
    deals = await Deal.filter(owner_id=user.id, stage="closed_won")
    revenue = sum(float(d.value or 0) for d in deals)
    return {"success": True, "revenue": revenue}


@analytics_router.get("/conversion")
async def analytics_conversion(user: User = Depends(get_current_user)):
    deals = await Deal.filter(owner_id=user.id)
    won = sum(1 for d in deals if d.stage == "closed_won")
    return {"success": True, "conversion_rate": (won / len(deals) * 100) if deals else 0}


@analytics_router.get("/customer")
async def analytics_customer(user: User = Depends(get_current_user)):
    return {"success": True, "customers": await Customer.filter(owner_id=user.id).count()}


@analytics_router.get("/deals")
async def analytics_deals(user: User = Depends(get_current_user)):
    return {"success": True, "deals": await Deal.filter(owner_id=user.id).count()}


@analytics_router.get("/tasks")
async def analytics_tasks(user: User = Depends(get_current_user)):
    pending = await Task.filter(owner_id=user.id, status="pending").count()
    completed = await Task.filter(owner_id=user.id, status="completed").count()
    return {"success": True, "pending": pending, "completed": completed}


@analytics_router.get("/forecast")
async def analytics_forecast(user: User = Depends(get_current_user)):
    deals = await Deal.filter(owner_id=user.id).exclude(stage__in=["closed_won", "closed_lost"])
    forecast = sum(float(d.value or 0) * (d.probability / 100) for d in deals)
    return {"success": True, "forecast": forecast}


@notifications_router.get("")
async def list_notifications(user: User = Depends(get_current_user)):
    rows = await Notification.filter(owner_id=user.id).order_by("-created_at").limit(50)
    return {"success": True, "notifications": [{"id": n.id, "title": n.title, "body": n.body, "read": n.read} for n in rows]}


@notifications_router.post("")
async def create_notification(title: str, body: str, user: User = Depends(get_current_user)):
    n = await Notification.create(owner_id=user.id, title=title, body=body)
    return {"success": True, "notification": {"id": n.id}}


@notifications_router.put("/{notification_id}")
async def mark_read(notification_id: int, user: User = Depends(get_current_user)):
    n = await Notification.filter(id=notification_id, owner_id=user.id).first()
    if n:
        n.read = True
        await n.save()
    return {"success": True}


@notifications_router.delete("/{notification_id}")
async def delete_notification(notification_id: int, user: User = Depends(get_current_user)):
    n = await Notification.filter(id=notification_id, owner_id=user.id).first()
    if n:
        await n.delete()
    return {"success": True}


@settings_router.get("")
async def get_settings(user: User = Depends(get_current_user)):
    return {"success": True, "settings": {"theme": "dark", "notifications": True, "role": user.role}}


@settings_router.put("")
async def update_settings(settings: dict, user: User = Depends(get_current_user)):
    return {"success": True, "settings": settings}


@admin_router.get("/users")
async def admin_users(user: User = Depends(get_current_user)):
    if user.role != "admin":
        return {"success": False, "message": "Admin access required."}
    rows = await User.all().limit(100)
    return {"success": True, "users": [{"id": u.id, "email": u.email, "role": u.role} for u in rows]}


@admin_router.get("/logs")
async def admin_logs(user: User = Depends(get_current_user)):
    rows = await AuditLog.filter(owner_id=user.id).order_by("-created_at").limit(100)
    return {"success": True, "logs": [{"id": l.id, "action": l.action, "resource": l.resource} for l in rows]}


@admin_router.get("/system")
async def admin_system(user: User = Depends(get_current_user)):
    return {"success": True, "system": {"status": "healthy", "vector_store": "pgvector"}}


@admin_router.get("/usage")
async def admin_usage(user: User = Depends(get_current_user)):
    return {"success": True, "usage": {"documents": await Document.filter(owner_id=user.id).count(), "chat_messages": await __import__("app.models.ai", fromlist=["ChatMessage"]).ChatMessage.filter(owner_id=user.id).count()}}


@admin_router.get("/agents")
async def admin_agents(user: User = Depends(get_current_user)):
    return {"success": True, "agents": ["router", "crm", "document", "meeting", "email", "task", "analytics", "workflow"]}


@admin_router.get("/vector-db")
async def admin_vector_db(user: User = Depends(get_current_user)):
    return {"success": True, "stats": await rag_statistics(user.id)}


@admin_router.get("/jobs")
async def admin_jobs(user: User = Depends(get_current_user)):
    return {"success": True, "jobs": []}


@users_router.get("")
async def list_users(user: User = Depends(get_current_user)):
    return {"success": True, "users": [{"id": user.id, "name": user.name, "email": user.email}]}


@users_router.get("/{user_id}")
async def get_user(user_id: int, current: User = Depends(get_current_user)):
    u = await User.filter(id=user_id).first()
    return {"success": True, "user": {"id": u.id, "name": u.name, "email": u.email} if u else None}


@users_router.get("/roles")
async def user_roles():
    return {"success": True, "roles": ["admin", "sales_rep", "manager"]}


@users_router.put("/assign-role")
async def assign_role(user_id: int = Query(...), role: str = Query(...), current: User = Depends(get_current_user)):
    if current.role != "admin":
        return {"success": False, "message": "Admin only."}
    u = await User.filter(id=user_id).first()
    if u:
        u.role = role
        await u.save()
    return {"success": True}
