from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import SupportTicket, TicketMessage, User, Notification
from auth_utils import get_optional_user, get_current_user
from serializers import serialize_ticket
from utils import make_ref
from ratelimit import limiter

router = APIRouter(prefix="/api/support", tags=["Support"])


class TicketBody(BaseModel):
    subject: str
    category: str | None = "general"
    priority: str | None = "normal"
    message: str
    name: str | None = None
    email: EmailStr | None = None


class MessageBody(BaseModel):
    body: str


@router.post("/tickets", dependencies=[Depends(limiter("ticket", 10, 300))])
def create_ticket(body: TicketBody, user: User | None = Depends(get_optional_user),
                  db: Session = Depends(get_db)):
    email = (user.email if user else (body.email or "")).lower()
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")
    ticket = SupportTicket(
        ticket_ref=make_ref("TIC"), user_id=user.id if user else None, email=email,
        name=body.name or (user.name if user else None), subject=body.subject.strip(),
        category=body.category, priority=body.priority, status="open",
    )
    db.add(ticket)
    db.flush()
    db.add(TicketMessage(ticket_id=ticket.id, sender="customer", body=body.message.strip()))
    if user:
        db.add(Notification(user_id=user.id, type="support", title="Support ticket created",
                            body=f"Ticket {ticket.ticket_ref}: {ticket.subject}",
                            link="/dashboard/support"))
    db.commit()
    db.refresh(ticket)
    return serialize_ticket(ticket, with_messages=True)


@router.get("/tickets/me")
def my_tickets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(SupportTicket).filter(SupportTicket.user_id == user.id).order_by(
        SupportTicket.created_at.desc()).all()
    return [serialize_ticket(t) for t in rows]


@router.get("/tickets/{ref}")
def get_ticket(ref: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(SupportTicket).filter(SupportTicket.ticket_ref == ref).first()
    if not t or (t.user_id and t.user_id != user.id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return serialize_ticket(t, with_messages=True)


@router.post("/tickets/{ref}/messages")
def add_message(ref: str, body: MessageBody, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    t = db.query(SupportTicket).filter(SupportTicket.ticket_ref == ref).first()
    if not t or (t.user_id and t.user_id != user.id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.add(TicketMessage(ticket_id=t.id, sender="customer", body=body.body.strip()))
    if t.status in ("waiting_customer", "resolved"):
        t.status = "in_progress"
    db.commit()
    db.refresh(t)
    return serialize_ticket(t, with_messages=True)
