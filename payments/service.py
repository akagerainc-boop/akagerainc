"""
Payment / order finalization — the single place that turns a successful payment into
an order, invoice, license, subscription, business token, and notification.

Every provider success path (Stripe webhook, PayPal capture, ITEC verify/callback,
free activation) should call `finalize_payment(db, payment)`. It is idempotent.
"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from models import (
    Payment, Order, OrderItem, Invoice, License, Subscription, Service, App,
    BusinessToken, Notification, User,
)
from utils import (
    generate_hex_license_key, slugify, make_ref, compute_expiry, duration_label,
)

SUBSCRIPTION_TYPES = {"subscription", "saas"}
BILLING_BY_UNIT = {"week": "weekly", "month": "monthly", "year": "annual"}


# --------------------------------------------------------------------------
def get_provider(name: str):
    """Return a provider adapter. Providers are thin wrappers over existing code."""
    from payments import providers
    return providers.REGISTRY.get((name or "").lower())


# --------------------------------------------------------------------------
def create_order(db: Session, user: User, service: Service, form_data: dict | None,
                 currency: str = "USD") -> Order:
    amount = Decimal(str(service.price or 0))
    order = Order(order_ref=make_ref("ORD"), user_id=user.id, status="pending",
                  subtotal=amount, total=amount, currency=currency or "USD")
    db.add(order)
    db.flush()
    db.add(OrderItem(
        order_id=order.id, item_type="service", ref_id=service.id, name=service.name,
        unit_amount=amount, quantity=1,
        duration_label=duration_label(service.duration_value, service.duration_unit, service.duration_label),
        form_data=form_data or {},
    ))
    db.commit()
    db.refresh(order)
    return order


# --------------------------------------------------------------------------
def _make_invoice_pdf(order: Order, user: User) -> str | None:
    try:
        from reportlab.pdfgen import canvas
    except Exception:
        return None
    inv_dir = Path("uploads/invoices")
    inv_dir.mkdir(parents=True, exist_ok=True)
    path = inv_dir / f"invoice_{order.order_ref}.pdf"
    try:
        buf = BytesIO()
        pdf = canvas.Canvas(buf)
        pdf.setTitle(f"Akagera Inc Invoice {order.order_ref}")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, 790, "AKAGERA INC — INVOICE")
        pdf.setFont("Helvetica", 11)
        y = 755
        lines = [
            f"Invoice / Order: {order.order_ref}",
            f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            f"Billed to: {user.name} <{user.email}>",
            "",
        ]
        for it in order.items:
            lines.append(f"{it.name}  x{it.quantity}   {order.currency} {float(it.unit_amount):.2f}")
            if it.duration_label:
                lines.append(f"   Duration: {it.duration_label}")
        lines += ["", f"TOTAL: {order.currency} {float(order.total):.2f}", "",
                  "Thank you for your purchase.", "Support: support@akagerainc.store"]
        for ln in lines:
            pdf.drawString(50, y, ln)
            y -= 16
        pdf.save()
        path.write_bytes(buf.getvalue())
        return str(path)
    except Exception as exc:  # pragma: no cover
        print(f"invoice pdf failed: {exc}")
        return None


def _notify(db: Session, user_id: int, ntype: str, title: str, body: str, link: str = "/dashboard"):
    db.add(Notification(user_id=user_id, type=ntype, title=title, body=body, link=link))


# --------------------------------------------------------------------------
def finalize_payment(db: Session, payment: Payment, form_data: dict | None = None) -> dict:
    """Idempotently create order artefacts for a completed payment."""
    result: dict = {"order_ref": None, "license_key": None, "subscription_id": None, "business_token": None}
    if payment.status != "completed":
        payment.status = "completed"

    user = db.query(User).filter(User.id == payment.user_id).first()
    service = db.query(Service).filter(Service.id == payment.service_id).first() if payment.service_id else None

    # ---- order ----
    order = None
    if payment.order_id:
        order = db.query(Order).filter(Order.id == payment.order_id).first()
    if not order and user:
        amount = Decimal(str(payment.amount or 0))
        order = Order(order_ref=make_ref("ORD"), user_id=user.id, status="pending",
                      subtotal=amount, total=amount, currency=payment.currency or "USD")
        db.add(order)
        db.flush()
        db.add(OrderItem(order_id=order.id, item_type="service",
                         ref_id=service.id if service else None,
                         name=service.name if service else "Akagera service",
                         unit_amount=amount, quantity=1,
                         duration_label=duration_label(
                             service.duration_value, service.duration_unit, service.duration_label) if service else None,
                         form_data=form_data or {}))
        payment.order_id = order.id
    if order:
        order.status = "completed"
        result["order_ref"] = order.order_ref
        # merge any late form_data
        if form_data and order.items:
            item = order.items[0]
            item.form_data = {**(item.form_data or {}), **form_data}

    # ---- license (idempotent per user+service) ----
    if user and service:
        existing = (db.query(License)
                    .filter(License.user_id == user.id, License.service_id == service.id)
                    .order_by(License.id.desc()).first())
        if not existing:
            key = generate_hex_license_key(16)
            expires = compute_expiry(datetime.utcnow(), service.duration_value, service.duration_unit)
            lic = License(
                user_id=user.id, license_key=key, service_id=service.id,
                app_id=None, license_type=_license_type(service), status="active",
                is_active=True, max_devices=1, starts_at=datetime.utcnow(), expires_at=expires,
            )
            db.add(lic)
            result["license_key"] = key
        else:
            result["license_key"] = existing.license_key

    # ---- subscription ----
    if user and service and (service.service_type in SUBSCRIPTION_TYPES):
        has_sub = (db.query(Subscription)
                   .filter(Subscription.user_id == user.id, Subscription.item_type == "service",
                           Subscription.ref_id == service.id, Subscription.status == "active")
                   .first())
        if not has_sub:
            expires = compute_expiry(datetime.utcnow(), service.duration_value, service.duration_unit)
            sub = Subscription(
                user_id=user.id, item_type="service", ref_id=service.id, plan_name=service.name,
                price=service.price, currency=service.currency or "USD",
                billing_period=BILLING_BY_UNIT.get(service.duration_unit, "monthly"),
                status="active", start_date=datetime.utcnow(), renewal_date=expires, expires_at=expires,
            )
            db.add(sub)
            db.flush()
            result["subscription_id"] = sub.id

    # ---- business token ----
    if user and service and getattr(service, "grants_business_portal_access", False):
        token = _create_business_token(db, user.id, service, payment.id)
        if token:
            result["business_token"] = token.token

    # ---- invoice ----
    if order and user:
        if not db.query(Invoice).filter(Invoice.order_id == order.id).first():
            pdf_path = _make_invoice_pdf(order, user)
            db.add(Invoice(invoice_ref=make_ref("INV"), order_id=order.id, user_id=user.id,
                           amount=order.total, currency=order.currency, pdf_path=pdf_path))

    # ---- notification ----
    if user:
        _notify(db, user.id, "payment", "Payment confirmed",
                f"Your payment for {service.name if service else 'your order'} was successful.",
                f"/dashboard/orders")

    db.commit()
    return result


def _license_type(service: Service) -> str:
    unit = (service.duration_unit or "").lower()
    return {"month": "monthly", "year": "annual", "lifetime": "lifetime"}.get(unit, "annual")


def _create_business_token(db: Session, user_id: int, service: Service, payment_id: int):
    import secrets as _s
    import string as _st
    from datetime import timedelta
    name = (service.portal_business_name or "Business Portal").strip()
    category = (service.portal_category or "General").strip()
    days = service.portal_access_duration_days or 365
    for _ in range(6):
        token = "".join(_s.choice(_st.ascii_uppercase + _st.digits) for _ in range(10))
        if not db.query(BusinessToken).filter(BusinessToken.token == token).first():
            bt = BusinessToken(user_id=user_id, service_id=service.id, payment_id=payment_id,
                               business_name=name, category=category, token=token,
                               status="active", expires_at=datetime.utcnow() + timedelta(days=days))
            db.add(bt)
            db.flush()
            return bt
    return None
