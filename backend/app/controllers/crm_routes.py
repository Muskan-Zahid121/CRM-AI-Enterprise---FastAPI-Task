from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from app.helpers.workflow_engine import trigger_workflows_for_event
from app.middleware.auth import get_current_user
from app.models.crm import Activity, Contact, Customer, Deal, Lead, Note
from app.models.user import User

router = APIRouter(tags=["crm"])


def _dt(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


def _d(v: Optional[date]) -> Optional[str]:
    return v.isoformat() if v else None


customers_router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerPayload(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None


async def _customer(user: User, cid: int) -> Customer:
    c = await Customer.filter(id=cid, owner_id=user.id).first()
    if not c:
        raise HTTPException(404, "Customer not found.")
    return c


def customer_out(c: Customer) -> dict[str, Any]:
    return {
        "id": c.id, "name": c.name, "email": c.email, "phone": c.phone,
        "company": c.company, "industry": c.industry, "status": c.status,
        "notes": c.notes, "created_at": _dt(c.created_at), "updated_at": _dt(c.updated_at),
    }


@customers_router.get("")
async def list_customers(user: User = Depends(get_current_user), search: Optional[str] = None):
    q = Customer.filter(owner_id=user.id)
    if search:
        q = q.filter(name__icontains=search)
    rows = await q.order_by("-updated_at")
    return {"success": True, "customers": [customer_out(c) for c in rows]}


@customers_router.get("/search")
async def search_customers(q: str = Query(min_length=1), user: User = Depends(get_current_user)):
    rows = await Customer.filter(owner_id=user.id, name__icontains=q)
    return {"success": True, "customers": [customer_out(c) for c in rows]}


@customers_router.get("/history")
async def customer_history(user: User = Depends(get_current_user)):
    activities = await Activity.filter(owner_id=user.id, customer_id__not_isnull=True).order_by("-created_at").limit(50)
    return {"success": True, "history": [{"id": a.id, "customer_id": a.customer_id, "type": a.activity_type, "description": a.description, "created_at": _dt(a.created_at)} for a in activities]}


@customers_router.get("/activity")
async def customer_activity(user: User = Depends(get_current_user)):
    return await customer_history(user)


@customers_router.get("/interactions")
async def customer_interactions(user: User = Depends(get_current_user)):
    notes = await Note.filter(owner_id=user.id).order_by("-created_at").limit(50)
    return {"success": True, "interactions": [{"id": n.id, "customer_id": n.customer_id, "content": n.content, "created_at": _dt(n.created_at)} for n in notes]}


@customers_router.get("/timeline")
async def customer_timeline(user: User = Depends(get_current_user)):
    activities = await Activity.filter(owner_id=user.id).order_by("-created_at").limit(100)
    return {"success": True, "timeline": [{"id": a.id, "customer_id": a.customer_id, "type": a.activity_type, "description": a.description, "created_at": _dt(a.created_at)} for a in activities]}


@customers_router.post("", status_code=201)
async def create_customer(payload: CustomerPayload, user: User = Depends(get_current_user)):
    c = await Customer.create(owner_id=user.id, **payload.model_dump())
    await Activity.create(owner_id=user.id, customer_id=c.id, activity_type="customer_created", description=f"Created customer {c.name}")
    return {"success": True, "customer": customer_out(c)}


@customers_router.get("/{customer_id}")
async def get_customer(customer_id: int, user: User = Depends(get_current_user)):
    return {"success": True, "customer": customer_out(await _customer(user, customer_id))}


@customers_router.put("/{customer_id}")
async def update_customer(customer_id: int, payload: CustomerPayload, user: User = Depends(get_current_user)):
    c = await _customer(user, customer_id)
    for k, v in payload.model_dump().items():
        setattr(c, k, v)
    await c.save()
    return {"success": True, "customer": customer_out(c)}


@customers_router.delete("/{customer_id}")
async def delete_customer(customer_id: int, user: User = Depends(get_current_user)):
    await (await _customer(user, customer_id)).delete()
    return {"success": True, "message": "Customer deleted."}


# ---------- Contacts ----------

contacts_router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactPayload(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    customer_id: Optional[int] = None
    is_primary: bool = False


@contacts_router.get("")
async def list_contacts(user: User = Depends(get_current_user)):
    rows = await Contact.filter(owner_id=user.id).order_by("-updated_at")
    return {"success": True, "contacts": [{"id": c.id, "name": c.name, "email": c.email, "phone": c.phone, "title": c.title, "customer_id": c.customer_id, "is_primary": c.is_primary} for c in rows]}


@contacts_router.post("", status_code=201)
async def create_contact(payload: ContactPayload, user: User = Depends(get_current_user)):
    c = await Contact.create(owner_id=user.id, customer_id=payload.customer_id, name=payload.name, email=payload.email, phone=payload.phone, title=payload.title, is_primary=payload.is_primary)
    return {"success": True, "contact": {"id": c.id, "name": c.name}}


@contacts_router.put("/{contact_id}")
async def update_contact(contact_id: int, payload: ContactPayload, user: User = Depends(get_current_user)):
    c = await Contact.filter(id=contact_id, owner_id=user.id).first()
    if not c:
        raise HTTPException(404, "Contact not found.")
    for k, v in payload.model_dump().items():
        setattr(c, k if k != "customer_id" else "customer_id", v)
    await c.save()
    return {"success": True, "contact": {"id": c.id, "name": c.name}}


@contacts_router.delete("/{contact_id}")
async def delete_contact(contact_id: int, user: User = Depends(get_current_user)):
    c = await Contact.filter(id=contact_id, owner_id=user.id).first()
    if not c:
        raise HTTPException(404, "Contact not found.")
    await c.delete()
    return {"success": True}


leads_router = APIRouter(prefix="/leads", tags=["leads"])


class LeadPayload(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    company: Optional[str] = None
    source: Optional[str] = None
    stage: str = "new"
    score: int = 0
    notes: Optional[str] = None


@leads_router.get("")
async def list_leads(user: User = Depends(get_current_user)):
    rows = await Lead.filter(owner_id=user.id).order_by("-updated_at")
    return {"success": True, "leads": [{"id": l.id, "name": l.name, "email": l.email, "company": l.company, "stage": l.stage, "score": l.score} for l in rows]}


@leads_router.get("/pipeline")
async def leads_pipeline(user: User = Depends(get_current_user)):
    rows = await Lead.filter(owner_id=user.id)
    stages: dict[str, int] = {}
    for l in rows:
        stages[l.stage] = stages.get(l.stage, 0) + 1
    return {"success": True, "pipeline": stages}


@leads_router.get("/stages")
async def lead_stages():
    return {"success": True, "stages": ["new", "contacted", "qualified", "proposal", "converted", "lost"]}


@leads_router.post("", status_code=201)
async def create_lead(payload: LeadPayload, user: User = Depends(get_current_user)):
    l = await Lead.create(owner_id=user.id, **payload.model_dump())
    await trigger_workflows_for_event(
        user,
        "lead_created",
        {"lead_name": l.name, "company": l.company or "Unknown"},
    )
    return {"success": True, "lead": {"id": l.id, "name": l.name, "stage": l.stage}}


@leads_router.put("/{lead_id}/convert")
async def convert_lead(lead_id: int, user: User = Depends(get_current_user)):
    l = await Lead.filter(id=lead_id, owner_id=user.id).first()
    if not l:
        raise HTTPException(404, "Lead not found.")
    customer = await Customer.create(owner_id=user.id, name=l.name, email=l.email, company=l.company, notes=l.notes)
    l.stage = "converted"
    l.converted_customer_id = customer.id
    await l.save()
    return {"success": True, "customer": customer_out(customer)}


@leads_router.put("/{lead_id}")
async def update_lead(lead_id: int, payload: LeadPayload, user: User = Depends(get_current_user)):
    l = await Lead.filter(id=lead_id, owner_id=user.id).first()
    if not l:
        raise HTTPException(404, "Lead not found.")
    for k, v in payload.model_dump().items():
        setattr(l, k, v)
    await l.save()
    return {"success": True, "lead": {"id": l.id, "name": l.name}}


@leads_router.delete("/{lead_id}")
async def delete_lead(lead_id: int, user: User = Depends(get_current_user)):
    l = await Lead.filter(id=lead_id, owner_id=user.id).first()
    if not l:
        raise HTTPException(404, "Lead not found.")
    await l.delete()
    return {"success": True}


# ---------- Deals ----------

deals_router = APIRouter(prefix="/deals", tags=["deals"])


class DealPayload(BaseModel):
    title: str
    customer_id: Optional[int] = None
    lead_id: Optional[int] = None
    value: float = 0
    stage: str = "lead"
    probability: int = 0
    expected_close_date: Optional[date] = None
    notes: Optional[str] = None


@deals_router.get("")
async def list_deals(user: User = Depends(get_current_user), stage: Optional[str] = None):
    q = Deal.filter(owner_id=user.id)
    if stage:
        q = q.filter(stage=stage)
    rows = await q.order_by("-updated_at")
    return {"success": True, "deals": [{"id": d.id, "title": d.title, "value": float(d.value or 0), "stage": d.stage, "customer_id": d.customer_id, "probability": d.probability} for d in rows]}


@deals_router.get("/pipeline")
async def deals_pipeline(user: User = Depends(get_current_user)):
    rows = await Deal.filter(owner_id=user.id)
    pipeline: dict[str, int] = {}
    for d in rows:
        pipeline[d.stage] = pipeline.get(d.stage, 0) + 1
    return {"success": True, "pipeline": pipeline}


@deals_router.get("/forecast")
async def deals_forecast(user: User = Depends(get_current_user)):
    rows = await Deal.filter(owner_id=user.id).exclude(stage__in=["closed_won", "closed_lost"])
    forecast = sum(float(d.value or 0) * (d.probability / 100) for d in rows)
    return {"success": True, "forecast": forecast}


@deals_router.get("/high-priority")
async def high_priority_deals(user: User = Depends(get_current_user)):
    rows = await Deal.filter(owner_id=user.id, probability__gte=70).exclude(stage__in=["closed_won", "closed_lost"])
    return {"success": True, "deals": [{"id": d.id, "title": d.title, "value": float(d.value or 0), "probability": d.probability} for d in rows]}


@deals_router.get("/analytics")
async def deals_analytics(user: User = Depends(get_current_user)):
    rows = await Deal.filter(owner_id=user.id)
    won = sum(1 for d in rows if d.stage == "closed_won")
    lost = sum(1 for d in rows if d.stage == "closed_lost")
    return {"success": True, "analytics": {"total": len(rows), "won": won, "lost": lost, "win_rate": (won / len(rows) * 100) if rows else 0}}


@deals_router.post("", status_code=201)
async def create_deal(payload: DealPayload, user: User = Depends(get_current_user)):
    d = await Deal.create(owner_id=user.id, customer_id=payload.customer_id, lead_id=payload.lead_id, title=payload.title, value=Decimal(str(payload.value)), stage=payload.stage, probability=payload.probability, expected_close_date=payload.expected_close_date, notes=payload.notes)
    return {"success": True, "deal": {"id": d.id, "title": d.title}}


@deals_router.put("/change-stage")
async def change_deal_stage(deal_id: int = Query(...), stage: str = Query(...), user: User = Depends(get_current_user)):
    d = await Deal.filter(id=deal_id, owner_id=user.id).first()
    if not d:
        raise HTTPException(404, "Deal not found.")
    d.stage = stage
    await d.save()
    if stage in ("closed_won", "won"):
        await trigger_workflows_for_event(
            user,
            "deal_closed",
            {"deal_title": d.title, "deal_value": str(float(d.value or 0))},
        )
    return {"success": True, "deal": {"id": d.id, "stage": d.stage}}


@deals_router.put("/{deal_id}")
async def update_deal(deal_id: int, payload: DealPayload, user: User = Depends(get_current_user)):
    d = await Deal.filter(id=deal_id, owner_id=user.id).first()
    if not d:
        raise HTTPException(404, "Deal not found.")
    data = payload.model_dump()
    data["value"] = Decimal(str(data["value"]))
    for k, v in data.items():
        setattr(d, k if k != "customer_id" else "customer_id", v)
    await d.save()
    return {"success": True, "deal": {"id": d.id, "title": d.title}}


@deals_router.delete("/{deal_id}")
async def delete_deal(deal_id: int, user: User = Depends(get_current_user)):
    d = await Deal.filter(id=deal_id, owner_id=user.id).first()
    if not d:
        raise HTTPException(404, "Deal not found.")
    await d.delete()
    return {"success": True}


# ---------- Notes ----------

notes_router = APIRouter(prefix="/notes", tags=["notes"])


class NotePayload(BaseModel):
    content: str
    customer_id: Optional[int] = None
    deal_id: Optional[int] = None


@notes_router.get("")
async def list_notes(user: User = Depends(get_current_user)):
    rows = await Note.filter(owner_id=user.id).order_by("-created_at")
    return {"success": True, "notes": [{"id": n.id, "content": n.content, "customer_id": n.customer_id, "deal_id": n.deal_id} for n in rows]}


@notes_router.post("", status_code=201)
async def create_note(payload: NotePayload, user: User = Depends(get_current_user)):
    n = await Note.create(owner_id=user.id, customer_id=payload.customer_id, deal_id=payload.deal_id, content=payload.content)
    return {"success": True, "note": {"id": n.id, "content": n.content}}


@notes_router.put("/{note_id}")
async def update_note(note_id: int, payload: NotePayload, user: User = Depends(get_current_user)):
    n = await Note.filter(id=note_id, owner_id=user.id).first()
    if not n:
        raise HTTPException(404, "Note not found.")
    n.content = payload.content
    n.customer_id = payload.customer_id
    n.deal_id = payload.deal_id
    await n.save()
    return {"success": True, "note": {"id": n.id}}


@notes_router.delete("/{note_id}")
async def delete_note(note_id: int, user: User = Depends(get_current_user)):
    n = await Note.filter(id=note_id, owner_id=user.id).first()
    if not n:
        raise HTTPException(404, "Note not found.")
    await n.delete()
    return {"success": True}
