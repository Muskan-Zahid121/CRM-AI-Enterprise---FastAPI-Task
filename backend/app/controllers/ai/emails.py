from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.helpers.llm.provider import generate_completion
from app.helpers.prompts import EMAIL_SYSTEM
from app.middleware.auth import get_current_user
from app.models.ai import EmailHistory
from app.models.user import User

emails_router = APIRouter(prefix="/email", tags=["emails"])


class EmailPayload(BaseModel):
    subject: str
    body: str = ""
    customer_id: Optional[int] = None
    prompt: Optional[str] = None


@emails_router.post("/generate")
async def generate_email(payload: EmailPayload, user: User = Depends(get_current_user)):
    prompt = payload.prompt or f"Subject: {payload.subject}\nContext: {payload.body}"
    body = await generate_completion(prompt, EMAIL_SYSTEM)
    record = await EmailHistory.create(
        owner_id=user.id,
        customer_id=payload.customer_id,
        subject=payload.subject,
        body=body,
        email_type="generated",
    )
    return {"success": True, "email": {"id": record.id, "subject": record.subject, "body": record.body}}


@emails_router.post("/send")
async def send_email(email_id: int = Query(...), user: User = Depends(get_current_user)):
    record = await EmailHistory.filter(id=email_id, owner_id=user.id).first()
    if not record:
        raise HTTPException(404, "Email not found.")
    record.sent = True
    await record.save()
    return {"success": True, "message": "Email marked as sent. Connect SMTP for delivery."}


@emails_router.post("/reply")
async def reply_email(payload: EmailPayload, user: User = Depends(get_current_user)):
    body = await generate_completion(f"Write a reply.\n{payload.prompt or payload.body}", EMAIL_SYSTEM)
    return {"success": True, "body": body}


@emails_router.post("/template")
async def email_template(name: str = Query(...), user: User = Depends(get_current_user)):
    return {
        "success": True,
        "template": {"name": name, "body": "Hi {{name}},\n\nThank you for your time...\n\nBest regards"},
    }


@emails_router.get("/history")
async def email_history(user: User = Depends(get_current_user)):
    rows = await EmailHistory.filter(owner_id=user.id).order_by("-created_at").limit(50)
    return {"success": True, "emails": [{"id": e.id, "subject": e.subject, "sent": e.sent} for e in rows]}
