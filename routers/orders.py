"""Orders, invoices, and the customer dashboard data feed."""
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Order, Invoice, Service, License, Subscription, Payment, Notification, App, Download,
    BusinessToken, User,
)
from auth_utils import get_current_user
from serializers import (
    serialize_order, serialize_subscription, serialize_license, serialize_download,
    serialize_service, media_url,
)
from payments.service import create_order
from payments.providers import available_providers

router = APIRouter(prefix="/api", tags=["Orders & Account"])


class OrderBody(BaseModel):
    service_id: int
    form_data: dict | None = None
    currency: str = "USD"


@router.post("/orders")
def start_order(body: OrderBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == body.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    # validate required dynamic fields
    provided = body.form_data or {}
    missing = [f.label for f in service.fields if f.required and not str(provided.get(f.field_key, "")).strip()]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required fields: {', '.join(missing)}")
    order = create_order(db, user, service, provided, body.currency)
    return {"order": serialize_order(order), "service": serialize_service(service),
            "providers": available_providers()}


@router.get("/orders/me")
def my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).all()
    return [serialize_order(o) for o in rows]


@router.get("/orders/{ref}")
def get_order(ref: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_ref == ref, Order.user_id == user.id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return serialize_order(o)


@router.get("/invoices/me")
def my_invoices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Invoice).filter(Invoice.user_id == user.id).order_by(Invoice.issued_at.desc()).all()
    return [{"invoice_ref": i.invoice_ref, "amount": float(i.amount or 0), "currency": i.currency,
             "issued_at": i.issued_at.isoformat() if i.issued_at else None,
             "has_pdf": bool(i.pdf_path and os.path.exists(i.pdf_path))} for i in rows]


@router.get("/invoices/{ref}/pdf")
def invoice_pdf(ref: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_ref == ref, Invoice.user_id == user.id).first()
    if not inv or not inv.pdf_path or not os.path.exists(inv.pdf_path):
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    return FileResponse(inv.pdf_path, media_type="application/pdf", filename=f"{ref}.pdf")


# ----------------------------- dashboard feed -----------------------------
@router.get("/dashboard/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.user_id == user.id).order_by(Order.created_at.desc()).limit(5).all()
    licenses = db.query(License).filter(License.user_id == user.id).all()
    subs = db.query(Subscription).filter(Subscription.user_id == user.id).all()
    notes = db.query(Notification).filter(Notification.user_id == user.id).order_by(
        Notification.created_at.desc()).limit(8).all()
    tokens = db.query(BusinessToken).filter(BusinessToken.user_id == user.id).all()
    return {
        "stats": {
            "orders": db.query(Order).filter(Order.user_id == user.id).count(),
            "active_licenses": sum(1 for l in licenses if l.is_active and l.status == "active"),
            "active_subscriptions": sum(1 for s in subs if s.status == "active"),
            "total_spent": float(sum(float(p.amount or 0) for p in db.query(Payment).filter(
                Payment.user_id == user.id, Payment.status == "completed").all())),
        },
        "recent_orders": [serialize_order(o) for o in orders],
        "licenses": [serialize_license(l) for l in licenses],
        "subscriptions": [serialize_subscription(s) for s in subs],
        "business_tokens": [{"business_name": t.business_name, "category": t.category, "token": t.token,
                             "status": t.status,
                             "expires_at": t.expires_at.isoformat() if t.expires_at else None} for t in tokens],
        "notifications": [{"id": n.id, "type": n.type, "title": n.title, "body": n.body,
                           "link": n.link, "is_read": n.is_read,
                           "created_at": n.created_at.isoformat() if n.created_at else None} for n in notes],
    }


@router.get("/dashboard/downloads")
def my_downloads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Downloads the user can access: free products + products they hold a license for."""
    licensed_service_ids = {l.service_id for l in db.query(License).filter(
        License.user_id == user.id, License.is_active == True).all() if l.service_id}  # noqa: E712
    products = db.query(App).filter(App.status == "published").all()
    out = []
    for p in products:
        accessible = (not p.requires_license) or bool(licensed_service_ids)
        out.append({
            "product": {"name": p.name, "slug": p.slug, "icon": media_url(p.app_icon),
                        "requires_license": bool(p.requires_license)},
            "accessible": accessible,
            "downloads": [serialize_download(d) for d in p.downloads if d.is_active],
        })
    return out


@router.get("/notifications/me")
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(Notification.user_id == user.id).order_by(
        Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "body": n.body, "link": n.link,
             "is_read": n.is_read, "created_at": n.created_at.isoformat() if n.created_at else None}
            for n in rows]


@router.post("/notifications/{note_id}/read")
def mark_read(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == note_id, Notification.user_id == user.id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"ok": True}
