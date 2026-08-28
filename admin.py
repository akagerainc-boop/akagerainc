"""
Admin CMS API — /api/admin/*

Auth: Bearer admin JWT (from POST /api/admin/login). A legacy `?password=` query
param is still accepted during migration so older clients keep working.
"""
import os
import time
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, Body,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, App, Service, ServiceField, Download, Payment, License, Image, Order, OrderItem,
    Subscription, Invoice, SupportTicket, TicketMessage, BlogPost, Category, Testimonial,
    Faq, DocPage, Industry, Internship, InternshipApplication, JobPosition, JobApplication,
    CaseStudy, NavigationItem, SiteContent, AuditLog, ContactMessage, Notification,
)
from auth_utils import decode_token, verify_password, create_token, ADMIN_ROLES
from utils import slugify, validate_upload, generate_hex_license_key
import site_defaults as sd

admin_router = APIRouter(prefix="/api/admin", tags=["Admin"])
_bearer = HTTPBearer(auto_error=False)

LEGACY_PW = os.getenv("ADMIN_PASSWORD_LEGACY", "Admin@Akagera2024!")
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "")


# --------------------------------------------------------------------------
#  Auth
# --------------------------------------------------------------------------
def admin_guard(
    request: Request,
    password: Optional[str] = Query(None),
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> dict:
    # 1) Bearer admin JWT
    if creds and creds.scheme.lower() == "bearer":
        data = decode_token(creds.credentials)
        if data and data.get("role") in ADMIN_ROLES:
            return {"email": data.get("email", "admin"), "role": data["role"]}
    # 2) legacy password
    if password and (password == LEGACY_PW or (ADMIN_PW and password == ADMIN_PW)):
        return {"email": "legacy-admin", "role": "super_admin"}
    raise HTTPException(status_code=401, detail="Admin authentication required")


def _audit(db: Session, actor: dict, action: str, entity: str, entity_id, meta: dict | None = None):
    try:
        db.add(AuditLog(actor_email=actor.get("email"), action=action, entity=entity,
                        entity_id=str(entity_id), meta=meta or {}))
        db.commit()
    except Exception:
        db.rollback()


@admin_router.post("/login")
def admin_login(payload: dict = Body(...), db: Session = Depends(get_db)):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    # user-based admin
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user and user.role in ADMIN_ROLES and verify_password(password, user.password_hash):
            user.last_login_at = datetime.utcnow()
            db.commit()
            return {"access_token": create_token({"sub": str(user.id), "role": user.role, "email": user.email}),
                    "token_type": "bearer",
                    "admin": {"name": user.name, "email": user.email, "role": user.role}}
    # legacy password (no email or wrong email but correct master pw)
    if password and (password == LEGACY_PW or (ADMIN_PW and password == ADMIN_PW)):
        return {"access_token": create_token({"sub": "0", "role": "super_admin", "email": "legacy-admin"}),
                "token_type": "bearer",
                "admin": {"name": "Administrator", "email": "legacy-admin", "role": "super_admin"}}
    raise HTTPException(status_code=401, detail="Invalid admin credentials")


# --------------------------------------------------------------------------
#  Dashboard stats
# --------------------------------------------------------------------------
@admin_router.get("/stats")
def stats(actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "completed").scalar() or 0
    return {
        "total_users": db.query(User).count(),
        "total_orders": db.query(Order).count(),
        "total_revenue": float(revenue),
        "active_subscriptions": db.query(Subscription).filter(Subscription.status == "active").count(),
        "active_licenses": db.query(License).filter(License.is_active == True, License.status == "active").count(),  # noqa: E712
        "total_products": db.query(App).count(),
        "total_services": db.query(Service).count(),
        "total_downloads": db.query(Download).count(),
        "open_tickets": db.query(SupportTicket).filter(
            SupportTicket.status.in_(["open", "in_progress", "waiting_customer"])).count(),
        "new_messages": db.query(ContactMessage).filter(ContactMessage.status == "new").count(),
        "timestamp": datetime.utcnow().isoformat(),
    }


# --------------------------------------------------------------------------
#  Generic serialization for admin views
# --------------------------------------------------------------------------
def row_to_dict(obj) -> dict:
    out = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, (datetime, date)):
            v = v.isoformat()
        elif isinstance(v, bytes):
            v = None
        out[c.name] = v
    return out


# --------------------------------------------------------------------------
#  Generic CRUD registry
# --------------------------------------------------------------------------
SLUG_MODELS = {"services", "products", "blog", "case-studies", "internships", "careers", "docs", "industries"}

REGISTRY = {
    "services": Service,
    "service-fields": ServiceField,
    "products": App,
    "downloads": Download,
    "blog": BlogPost,
    "categories": Category,
    "testimonials": Testimonial,
    "faqs": Faq,
    "docs": DocPage,
    "industries": Industry,
    "internships": Internship,
    "careers": JobPosition,
    "case-studies": CaseStudy,
    "navigation": NavigationItem,
    "users": User,
    "licenses": License,
    "subscriptions": Subscription,
    "orders": Order,
    "contact-messages": ContactMessage,
    "internship-applications": InternshipApplication,
    "job-applications": JobApplication,
    "tickets": SupportTicket,
}

READONLY = {"orders", "contact-messages", "internship-applications", "job-applications"}
NO_CREATE = READONLY | {"users", "licenses", "subscriptions", "tickets"}


def _coerce_dates(model, data: dict) -> dict:
    for c in model.__table__.columns:
        if c.name in data and data[c.name] not in (None, "") and str(c.type).startswith("DATE"):
            try:
                data[c.name] = date.fromisoformat(str(data[c.name])[:10])
            except ValueError:
                data.pop(c.name, None)
    return data


@admin_router.get("/resources/{name}")
def list_resource(name: str, skip: int = 0, limit: int = 200,
                  actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    model = REGISTRY.get(name)
    if not model:
        raise HTTPException(status_code=404, detail="Unknown resource")
    q = db.query(model)
    order_col = getattr(model, "sort_order", None) or getattr(model, "id")
    rows = q.order_by(order_col).offset(skip).limit(limit).all()
    return {"total": q.count(), "items": [row_to_dict(r) for r in rows]}


@admin_router.post("/resources/{name}")
def create_resource(name: str, payload: dict = Body(...),
                    actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    model = REGISTRY.get(name)
    if not model or name in NO_CREATE:
        raise HTTPException(status_code=400, detail="Cannot create this resource")
    cols = {c.name for c in model.__table__.columns}
    data = {k: v for k, v in payload.items() if k in cols and k not in ("id", "created_at", "updated_at")}
    if name in SLUG_MODELS and not data.get("slug") and data.get("name" if "name" in cols else "title"):
        base = data.get("name") or data.get("title")
        slug = slugify(base)
        n = 1
        while db.query(model).filter(model.slug == slug).first():
            n += 1
            slug = f"{slugify(base)}-{n}"
        data["slug"] = slug
    _coerce_dates(model, data)
    obj = model(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    _audit(db, actor, "create", name, obj.id, {"name": data.get("name") or data.get("title")})
    return row_to_dict(obj)


@admin_router.patch("/resources/{name}/{item_id}")
def update_resource(name: str, item_id: int, payload: dict = Body(...),
                    actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    model = REGISTRY.get(name)
    if not model:
        raise HTTPException(status_code=404, detail="Unknown resource")
    obj = db.query(model).filter(model.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    cols = {c.name for c in model.__table__.columns}
    data = {k: v for k, v in payload.items() if k in cols and k not in ("id", "created_at")}
    _coerce_dates(model, data)
    for k, v in data.items():
        setattr(obj, k, v)
    if hasattr(obj, "updated_at"):
        obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    _audit(db, actor, "update", name, obj.id, {"fields": list(data.keys())})
    return row_to_dict(obj)


@admin_router.delete("/resources/{name}/{item_id}")
def delete_resource(name: str, item_id: int,
                    actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    model = REGISTRY.get(name)
    if not model or name in READONLY:
        raise HTTPException(status_code=400, detail="Cannot delete this resource")
    obj = db.query(model).filter(model.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    _audit(db, actor, "delete", name, item_id)
    return {"message": "Deleted"}


# --------------------------------------------------------------------------
#  Detail views with relations
# --------------------------------------------------------------------------
@admin_router.get("/services/{sid}/fields")
def service_fields(sid: int, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    rows = db.query(ServiceField).filter(ServiceField.service_id == sid).order_by(ServiceField.sort_order).all()
    return [row_to_dict(r) for r in rows]


@admin_router.get("/orders")
def admin_orders(status: str | None = None, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    q = db.query(Order)
    if status:
        q = q.filter(Order.status == status)
    rows = q.order_by(Order.created_at.desc()).limit(300).all()
    out = []
    for o in rows:
        u = db.query(User).filter(User.id == o.user_id).first()
        out.append({**row_to_dict(o), "customer": {"name": u.name, "email": u.email} if u else None,
                    "items": [row_to_dict(i) for i in o.items]})
    return out


@admin_router.patch("/orders/{oid}/status")
def set_order_status(oid: int, payload: dict = Body(...),
                     actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == oid).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.status = payload.get("status", o.status)
    db.commit()
    _audit(db, actor, "order_status", "orders", oid, {"status": o.status})
    return {"message": "Updated", "status": o.status}


@admin_router.patch("/users/{uid}/role")
def set_user_role(uid: int, payload: dict = Body(...),
                  actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.role = payload.get("role", u.role)
    if "is_active" in payload:
        u.is_active = bool(payload["is_active"])
    db.commit()
    _audit(db, actor, "user_role", "users", uid, {"role": u.role})
    return {"message": "Updated", "role": u.role, "is_active": u.is_active}


@admin_router.patch("/licenses/{lid}/status")
def set_license_status(lid: int, payload: dict = Body(...),
                       actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    l = db.query(License).filter(License.id == lid).first()
    if not l:
        raise HTTPException(status_code=404, detail="License not found")
    l.status = payload.get("status", l.status)
    l.is_active = l.status == "active"
    db.commit()
    _audit(db, actor, "license_status", "licenses", lid, {"status": l.status})
    return {"message": "Updated", "status": l.status}


@admin_router.post("/licenses")
def admin_issue_license(payload: dict = Body(...),
                        actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    l = License(
        user_id=payload["user_id"], license_key=generate_hex_license_key(16),
        service_id=payload.get("service_id"), app_id=payload.get("app_id"),
        license_type=payload.get("license_type", "annual"), status="active", is_active=True,
        max_devices=payload.get("max_devices", 1), starts_at=datetime.utcnow(),
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    _audit(db, actor, "create", "licenses", l.id)
    return row_to_dict(l)


@admin_router.get("/tickets/{ref}")
def admin_ticket(ref: str, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    t = db.query(SupportTicket).filter(SupportTicket.ticket_ref == ref).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {**row_to_dict(t), "messages": [row_to_dict(m) for m in t.messages]}


@admin_router.post("/tickets/{ref}/reply")
def admin_ticket_reply(ref: str, payload: dict = Body(...),
                       actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    t = db.query(SupportTicket).filter(SupportTicket.ticket_ref == ref).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.add(TicketMessage(ticket_id=t.id, sender="staff", body=payload["body"].strip()))
    t.status = payload.get("status", "waiting_customer")
    if t.user_id:
        db.add(Notification(user_id=t.user_id, type="support", title=f"Reply on ticket {t.ticket_ref}",
                            body=payload["body"][:140], link="/dashboard/support"))
    db.commit()
    return {"message": "Replied", "status": t.status}


# --------------------------------------------------------------------------
#  Navigation reorder / bulk
# --------------------------------------------------------------------------
@admin_router.post("/navigation/reorder")
def nav_reorder(payload: dict = Body(...),
                actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    for idx, nid in enumerate(payload.get("ids", [])):
        item = db.query(NavigationItem).filter(NavigationItem.id == nid).first()
        if item:
            item.sort_order = idx
    db.commit()
    return {"message": "Reordered"}


# --------------------------------------------------------------------------
#  Site content (key/JSON)
# --------------------------------------------------------------------------
@admin_router.get("/content")
def get_all_content(actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    rows = {r.content_key: r.content_value for r in db.query(SiteContent).all()}
    for k, v in sd.DEFAULTS.items():
        rows.setdefault(k, v)
    return rows


@admin_router.get("/content/{key}")
def get_content(key: str, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    r = db.query(SiteContent).filter(SiteContent.content_key == key).first()
    return {"key": key, "value": r.content_value if r else sd.DEFAULTS.get(key)}


@admin_router.put("/content/{key}")
def put_content(key: str, payload: dict = Body(...),
                actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    value = payload.get("value", payload)
    r = db.query(SiteContent).filter(SiteContent.content_key == key).first()
    if r:
        r.content_value = value
        r.updated_at = datetime.utcnow()
    else:
        db.add(SiteContent(content_key=key, content_value=value))
    db.commit()
    _audit(db, actor, "content", "site_content", key)
    return {"message": "Saved", "key": key, "value": value}


# Legacy pricing endpoints kept for older clients
@admin_router.get("/pricing")
def get_pricing(actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    r = db.query(SiteContent).filter(SiteContent.content_key == "pricing").first()
    return {"pricing": r.content_value if r else sd.PRICING}


@admin_router.put("/pricing")
def put_pricing(pricing: list = Body(...), actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    r = db.query(SiteContent).filter(SiteContent.content_key == "pricing").first()
    if r:
        r.content_value = pricing
    else:
        db.add(SiteContent(content_key="pricing", content_value=pricing))
    db.commit()
    return {"message": "Pricing updated", "pricing": pricing}


# --------------------------------------------------------------------------
#  File uploads
#
#  Images are stored in the DB (or Cloudinary if CLOUDINARY_URL is set) so they
#  survive redeploys on ephemeral hosts like Render. Installer binaries still go
#  to disk (too big for the DB) — prefer pasting an external download URL.
# --------------------------------------------------------------------------
from media_storage import store_image_bytes


def _persist_image(db: Session, raw: bytes, filename: str, profile: str = "misc",
                   page_type: str | None = None, app_id: int | None = None,
                   service_id: int | None = None, alt_text: str | None = None) -> Image:
    cloud_url, blob, mime = store_image_bytes(raw, filename, profile)  # raises ValueError if too big
    order = db.query(Image).filter(Image.page_type == page_type).count() if page_type else 0
    img = Image(url=cloud_url, data=blob, filename=filename, mime_type=mime or "image/jpeg",
                alt_text=alt_text or (filename or "image").rsplit(".", 1)[0],
                page_type=page_type, app_id=app_id, service_id=service_id,
                order=order, is_active=True)
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


async def _store(file: UploadFile, folder: str, kind: str = "image") -> dict:
    """Legacy disk store — used only for installer binaries now."""
    data = await file.read()
    validate_upload(file.filename, len(data), kind=kind)
    d = Path(f"uploads/{folder}")
    d.mkdir(parents=True, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    name = f"{folder.replace('/', '_')}_{int(time.time() * 1000)}.{ext}"
    (d / name).write_bytes(data)
    return {"path": f"uploads/{folder}/{name}", "size": len(data), "filename": file.filename}


_PROFILE_BY_FOLDER = {
    "products": "cover", "services": "cover", "logo": "logo", "logos": "logo",
    "icon": "icon", "icons": "icon", "avatars": "avatar", "testimonials": "avatar",
    "screenshots": "screenshot", "blog": "cover", "case-studies": "cover",
}


@admin_router.post("/upload")
async def upload_asset(file: UploadFile = File(...), folder: str = Form("misc"),
                       kind: str = Form("image"), actor: dict = Depends(admin_guard),
                       db: Session = Depends(get_db)):
    data = await file.read()
    profile = _PROFILE_BY_FOLDER.get(folder.strip("/"), "misc")
    try:
        validate_upload(file.filename, len(data), kind="image")
        img = _persist_image(db, data, file.filename, profile=profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _audit(db, actor, "upload", "images", img.id, {"folder": folder})
    url = img.url if (img.url and img.url.startswith("http")) else f"/api/media/{img.id}"
    return {"message": "Uploaded", "url": url, "path": url, "id": img.id, "filename": file.filename}


@admin_router.post("/downloads/upload")
async def upload_installer(
    product_id: int = Form(...), platform: str = Form(...), version: str = Form(None),
    architecture: str = Form(None), min_os: str = Form(None), label: str = Form(None),
    release_notes: str = Form(None), file: UploadFile = File(...),
    actor: dict = Depends(admin_guard), db: Session = Depends(get_db),
):
    try:
        info = await _store(file, "installers", kind="installer")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    d = Download(product_id=product_id, platform=platform, label=label or file.filename,
                 file_path=info["path"], version=version, architecture=architecture, min_os=min_os,
                 file_size=f"{info['size'] // (1024*1024)} MB" if info["size"] > 1024*1024 else f"{info['size']//1024} KB",
                 release_notes=release_notes, released_at=date.today(), is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    _audit(db, actor, "create", "downloads", d.id, {"platform": platform})
    return row_to_dict(d)


# --------------------------------------------------------------------------
#  Carousel / page images  (Image table)
# --------------------------------------------------------------------------
@admin_router.get("/images")
def list_images(page_type: str | None = None, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    q = db.query(Image)
    if page_type:
        q = q.filter(Image.page_type == page_type)
    rows = q.order_by(Image.page_type, Image.order).all()
    return {"total": q.count(), "images": [{
        "id": i.id, "filename": i.filename, "alt_text": i.alt_text, "page_type": i.page_type,
        "order": i.order, "is_active": i.is_active, "mime_type": i.mime_type,
        "url": ("/" + i.url) if i.url and not i.url.startswith(("http", "/")) else (i.url or f"/api/media/{i.id}"),
    } for i in rows]}


@admin_router.post("/images")
async def upload_image(
    file: UploadFile = File(...), alt_text: str = Form(""), page_type: str = Form("home"),
    app_id: int = Form(None), service_id: int = Form(None),
    actor: dict = Depends(admin_guard), db: Session = Depends(get_db),
):
    data = await file.read()
    try:
        validate_upload(file.filename, len(data), kind="image")
        img = _persist_image(db, data, file.filename, profile="carousel", page_type=page_type,
                             app_id=app_id, service_id=service_id, alt_text=alt_text or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _audit(db, actor, "create", "images", img.id, {"page_type": page_type})
    url = img.url if (img.url and img.url.startswith("http")) else f"/api/media/{img.id}"
    return {"message": "Image uploaded", "image_id": img.id, "url": url}


@admin_router.patch("/images/{image_id}")
def update_image(image_id: int, payload: dict = Body(...),
                 actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    for k in ("alt_text", "order", "is_active", "page_type"):
        if k in payload:
            setattr(img, k, payload[k])
    db.commit()
    return {"message": "Updated"}


@admin_router.delete("/images/{image_id}")
def delete_image(image_id: int, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        if img.url and img.url.startswith("uploads/") and os.path.exists(img.url):
            os.remove(img.url)
    except OSError:
        pass
    db.delete(img)
    db.commit()
    _audit(db, actor, "delete", "images", image_id)
    return {"message": "Deleted"}


@admin_router.post("/images/reorder")
def reorder_images(payload: dict = Body(...), actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    for idx, iid in enumerate(payload.get("image_ids", [])):
        img = db.query(Image).filter(Image.id == iid).first()
        if img:
            img.order = idx
    db.commit()
    return {"message": "Reordered"}


# --------------------------------------------------------------------------
#  Audit log + messages
# --------------------------------------------------------------------------
@admin_router.get("/audit")
def audit_log(limit: int = 200, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [row_to_dict(r) for r in rows]


@admin_router.get("/messages")
def contact_messages(actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    rows = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(300).all()
    return [row_to_dict(r) for r in rows]


# --------------------------------------------------------------------------
#  Applicants — internship + job applications with full detail
# --------------------------------------------------------------------------
def _media_url(v):
    if not v:
        return None
    return v if str(v).startswith(("http://", "https://")) else v  # already /api/media/N or a URL


@admin_router.get("/applications/{kind}")
def list_applications(kind: str, status: str | None = None,
                      actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    if kind not in ("internship", "job"):
        raise HTTPException(status_code=404, detail="Unknown application kind")

    if kind == "internship":
        q = db.query(InternshipApplication).order_by(InternshipApplication.created_at.desc())
        if status:
            q = q.filter(InternshipApplication.status == status)
        titles = {i.id: i.title for i in db.query(Internship).all()}
        out = []
        for a in q.limit(500).all():
            out.append({
                **row_to_dict(a),
                "position": titles.get(a.internship_id, "—"),
                "file_url": _media_url(a.cv_path),
                "file_label": "CV",
            })
        return out

    q = db.query(JobApplication).order_by(JobApplication.created_at.desc())
    if status:
        q = q.filter(JobApplication.status == status)
    titles = {j.id: j.title for j in db.query(JobPosition).all()}
    return [{
        **row_to_dict(a),
        "position": titles.get(a.job_id, "—"),
        "file_url": _media_url(a.resume_path),
        "file_label": "Resume",
    } for a in q.limit(500).all()]


APPLICATION_STATUSES = ["submitted", "reviewing", "shortlisted", "interview", "offered", "hired", "rejected"]


@admin_router.patch("/applications/{kind}/{app_id}")
def update_application(kind: str, app_id: int, payload: dict = Body(...),
                      actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    model = {"internship": InternshipApplication, "job": JobApplication}.get(kind)
    if not model:
        raise HTTPException(status_code=404, detail="Unknown application kind")
    a = db.query(model).filter(model.id == app_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Application not found")
    if "status" in payload:
        a.status = payload["status"]
    if "notes" in payload and hasattr(a, "message"):
        a.message = payload["notes"]
    db.commit()
    _audit(db, actor, "application_status", f"{kind}-applications", app_id, {"status": a.status})
    return {"message": "Updated", "status": a.status}


@admin_router.delete("/applications/{kind}/{app_id}")
def delete_application(kind: str, app_id: int,
                      actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    model = {"internship": InternshipApplication, "job": JobApplication}.get(kind)
    if not model:
        raise HTTPException(status_code=404, detail="Unknown application kind")
    a = db.query(model).filter(model.id == app_id).first()
    if a:
        db.delete(a)
        db.commit()
        _audit(db, actor, "delete", f"{kind}-applications", app_id)
    return {"message": "Deleted"}


@admin_router.post("/seed")
def run_seed(actor: dict = Depends(admin_guard)):
    import seed as seeder
    seeder.run()
    return {"message": "Seed complete"}
