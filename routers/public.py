"""Public, read-only content API (no auth)."""
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import (
    App, Service, Download, BlogPost, CaseStudy, Internship, JobPosition, DocPage,
    Industry, Testimonial, Faq, Image, NavigationItem, SiteContent, Category, ContactMessage,
)
from serializers import (
    serialize_product, serialize_service, serialize_download, serialize_blog,
    serialize_case_study, serialize_internship, serialize_job, serialize_doc,
    serialize_industry, serialize_testimonial, serialize_faq, serialize_nav, media_url,
)
import site_defaults as sd
from ratelimit import limiter
from utils import get_request_ip

router = APIRouter(prefix="/api", tags=["Public"])


def _content(db: Session, key: str):
    row = db.query(SiteContent).filter(SiteContent.content_key == key).first()
    if row and row.content_value is not None:
        return row.content_value
    return sd.DEFAULTS.get(key)


# ----------------------------- site settings / nav -----------------------------
_SETTINGS_KEYS = ["brand", "hero", "homepage_sections", "product_categories", "social_links",
                  "contact_info", "company_info", "whatsapp", "pricing", "seo_defaults",
                  "industries_intro", "legal_privacy", "legal_terms", "legal_refund", "legal_cookie"]


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    # The shell (nav/footer/hero/branding) must render even if the DB is down.
    try:
        return {k: _content(db, k) for k in _SETTINGS_KEYS}
    except Exception:
        return {k: sd.DEFAULTS.get(k) for k in _SETTINGS_KEYS}


@router.get("/navigation")
def get_navigation(db: Session = Depends(get_db)):
    try:
        items = db.query(NavigationItem).order_by(NavigationItem.sort_order).all()
    except Exception:
        items = []
    if not items:
        return {"header": sd.HEADER_NAV, "footer": sd.FOOTER_NAV}
    return {
        "header": serialize_nav([i for i in items if i.location == "header"]),
        "footer": serialize_nav([i for i in items if i.location == "footer"]),
    }


@router.get("/categories")
def get_categories(kind: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Category).filter(Category.is_active == True)  # noqa: E712
    if kind:
        q = q.filter(Category.kind == kind)
    return [{"id": c.id, "kind": c.kind, "name": c.name, "slug": c.slug} for c in q.order_by(Category.sort_order).all()]


# ----------------------------- products -----------------------------
@router.get("/products")
def list_products(category: str | None = None, platform: str | None = None,
                  featured: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(App).filter(or_(App.status == "published", App.status.is_(None)))
    if category:
        q = q.filter(App.category == category)
    if featured:
        q = q.filter(App.is_featured == True)  # noqa: E712
    items = [serialize_product(a) for a in q.order_by(App.sort_order, App.id.desc()).all()]
    if platform:
        items = [p for p in items if platform in (p["platforms"] or [])]
    return items


@router.get("/products/{slug}")
def get_product(slug: str, db: Session = Depends(get_db)):
    a = db.query(App).filter(or_(App.slug == slug, App.id == _as_int(slug))).first()
    if not a:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(a)


def _as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


# ----------------------------- downloads -----------------------------
@router.get("/downloads")
def list_downloads(platform: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Download).filter(Download.is_active == True)  # noqa: E712
    if platform:
        q = q.filter(Download.platform == platform)
    rows = q.order_by(Download.released_at.is_(None), Download.released_at.desc()).all()
    out = []
    for d in rows:
        item = serialize_download(d)
        prod = db.query(App).filter(App.id == d.product_id).first()
        item["product"] = {"name": prod.name, "slug": prod.slug, "icon": media_url(prod.app_icon)} if prod else None
        out.append(item)
    return out


@router.get("/downloads/{slug}")
def product_downloads(slug: str, db: Session = Depends(get_db)):
    a = db.query(App).filter(or_(App.slug == slug, App.id == _as_int(slug))).first()
    if not a:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"product": serialize_product(a),
            "downloads": [serialize_download(d) for d in a.downloads if d.is_active]}


# ----------------------------- services -----------------------------
@router.get("/services")
def list_services(category: str | None = None, featured: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Service).filter(or_(Service.status == "published", Service.status.is_(None)))
    if category:
        q = q.filter(Service.category == category)
    if featured:
        q = q.filter(Service.is_featured == True)  # noqa: E712
    return [serialize_service(s) for s in q.order_by(Service.sort_order, Service.id).all()]


@router.get("/services/{slug}")
def get_service(slug: str, db: Session = Depends(get_db)):
    s = db.query(Service).filter(or_(Service.slug == slug, Service.id == _as_int(slug))).first()
    if not s:
        raise HTTPException(status_code=404, detail="Service not found")
    data = serialize_service(s, include_fields=True)
    related = (db.query(Service)
               .filter(Service.id != s.id, Service.category == s.category,
                       or_(Service.status == "published", Service.status.is_(None)))
               .limit(3).all())
    data["related"] = [serialize_service(r) for r in related]
    return data


@router.get("/pricing")
def get_pricing(db: Session = Depends(get_db)):
    return {"plans": _content(db, "pricing") or [],
            "featured_services": [serialize_service(s) for s in
                                  db.query(Service).filter(Service.is_featured == True).order_by(Service.sort_order).all()]}  # noqa: E712


# ----------------------------- blog / docs / industries / misc -----------------------------
@router.get("/blog")
def list_blog(category: str | None = None, q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(BlogPost).filter(BlogPost.status == "published")
    if category:
        query = query.filter(BlogPost.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(BlogPost.title.ilike(like), BlogPost.excerpt.ilike(like)))
    rows = query.order_by(BlogPost.published_at.is_(None), BlogPost.published_at.desc()).all()
    return [serialize_blog(p) for p in rows]


@router.get("/blog/{slug}")
def get_blog(slug: str, db: Session = Depends(get_db)):
    p = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.status == "published").first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    data = serialize_blog(p, full=True)
    data["related"] = [serialize_blog(r) for r in
                       db.query(BlogPost).filter(BlogPost.id != p.id, BlogPost.category == p.category,
                                                 BlogPost.status == "published").limit(3).all()]
    return data


@router.get("/case-studies")
def list_case_studies(category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(CaseStudy).filter(CaseStudy.status == "published")
    if category:
        q = q.filter(CaseStudy.category == category)
    return [serialize_case_study(c) for c in q.order_by(CaseStudy.id.desc()).all()]


@router.get("/case-studies/{slug}")
def get_case_study(slug: str, db: Session = Depends(get_db)):
    c = db.query(CaseStudy).filter(CaseStudy.slug == slug).first()
    if not c:
        raise HTTPException(status_code=404, detail="Case study not found")
    return serialize_case_study(c, full=True)


@router.get("/internships")
def list_internships(db: Session = Depends(get_db)):
    return [serialize_internship(i) for i in
            db.query(Internship).order_by(Internship.status, Internship.id.desc()).all()]


@router.get("/internships/{slug}")
def get_internship(slug: str, db: Session = Depends(get_db)):
    i = db.query(Internship).filter(Internship.slug == slug).first()
    if not i:
        raise HTTPException(status_code=404, detail="Internship not found")
    return serialize_internship(i, full=True)


@router.get("/careers")
def list_jobs(db: Session = Depends(get_db)):
    return [serialize_job(j) for j in db.query(JobPosition).order_by(JobPosition.status, JobPosition.id.desc()).all()]


@router.get("/careers/{slug}")
def get_job(slug: str, db: Session = Depends(get_db)):
    j = db.query(JobPosition).filter(JobPosition.slug == slug).first()
    if not j:
        raise HTTPException(status_code=404, detail="Position not found")
    return serialize_job(j, full=True)


@router.get("/documentation")
def list_docs(section: str | None = None, db: Session = Depends(get_db)):
    q = db.query(DocPage).filter(DocPage.is_published == True)  # noqa: E712
    if section:
        q = q.filter(DocPage.section == section)
    rows = q.order_by(DocPage.section, DocPage.sort_order).all()
    sections: dict[str, list] = {}
    for d in rows:
        sections.setdefault(d.section or "General", []).append(serialize_doc(d))
    return {"sections": sections}


@router.get("/documentation/{slug}")
def get_doc(slug: str, db: Session = Depends(get_db)):
    d = db.query(DocPage).filter(DocPage.slug == slug, DocPage.is_published == True).first()  # noqa: E712
    if not d:
        raise HTTPException(status_code=404, detail="Doc not found")
    return serialize_doc(d, full=True)


@router.get("/industries")
def list_industries(db: Session = Depends(get_db)):
    rows = db.query(Industry).filter(Industry.is_active == True).order_by(Industry.sort_order).all()  # noqa: E712
    return [serialize_industry(x) for x in rows] or sd.INDUSTRIES


@router.get("/industries/{slug}")
def get_industry(slug: str, db: Session = Depends(get_db)):
    x = db.query(Industry).filter(Industry.slug == slug).first()
    if not x:
        raise HTTPException(status_code=404, detail="Industry not found")
    return serialize_industry(x, full=True)


@router.get("/testimonials")
def list_testimonials(db: Session = Depends(get_db)):
    return [serialize_testimonial(t) for t in
            db.query(Testimonial).filter(Testimonial.is_active == True).order_by(Testimonial.sort_order).all()]  # noqa: E712


@router.get("/faqs")
def list_faqs(category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Faq).filter(Faq.is_active == True)  # noqa: E712
    if category:
        q = q.filter(Faq.category == category)
    return [serialize_faq(f) for f in q.order_by(Faq.category, Faq.sort_order).all()]


# ----------------------------- images / media -----------------------------
@router.get("/images")
def public_images(page_type: str | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(Image).filter(Image.is_active == True)  # noqa: E712
    if page_type:
        q = q.filter(Image.page_type == page_type)
    rows = q.order_by(Image.order).all()
    return [{"id": i.id, "url": media_url(i.url) or f"/api/media/{i.id}",
             "alt": i.alt_text or i.filename or "Akagera Inc", "order": i.order or 0,
             "page_type": i.page_type} for i in rows]


@router.get("/media/{image_id}")
def get_media(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    if img.url:
        path = img.url if img.url.startswith("uploads/") else f"uploads/{img.url.lstrip('/')}"
        if os.path.exists(path):
            return FileResponse(path, media_type=img.mime_type or "image/jpeg",
                                headers={"Cache-Control": "public, max-age=31536000, immutable"})
    if img.data:
        from fastapi.responses import Response
        return Response(content=img.data, media_type=img.mime_type or "image/jpeg",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})
    raise HTTPException(status_code=404, detail="Image file missing")


# ----------------------------- global search -----------------------------
@router.get("/search")
def search(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    like = f"%{q}%"
    products = db.query(App).filter(App.name.ilike(like)).limit(6).all()
    services = db.query(Service).filter(or_(Service.name.ilike(like), Service.description.ilike(like))).limit(6).all()
    posts = db.query(BlogPost).filter(BlogPost.status == "published", BlogPost.title.ilike(like)).limit(6).all()
    docs = db.query(DocPage).filter(DocPage.is_published == True, DocPage.title.ilike(like)).limit(6).all()  # noqa: E712
    faqs = db.query(Faq).filter(Faq.question.ilike(like)).limit(6).all()
    cases = db.query(CaseStudy).filter(CaseStudy.title.ilike(like)).limit(6).all()
    return {
        "query": q,
        "products": [{"title": p.name, "url": f"/products/{p.slug}", "excerpt": p.short_description} for p in products],
        "services": [{"title": s.name, "url": f"/services/{s.slug}", "excerpt": s.short_description} for s in services],
        "blog": [{"title": p.title, "url": f"/blog/{p.slug}", "excerpt": p.excerpt} for p in posts],
        "documentation": [{"title": d.title, "url": f"/documentation/{d.slug}", "excerpt": d.section} for d in docs],
        "faqs": [{"title": f.question, "url": "/support?view=faq", "excerpt": (f.answer or "")[:120]} for f in faqs],
        "case_studies": [{"title": c.title, "url": f"/case-studies/{c.slug}", "excerpt": c.summary} for c in cases],
    }


# ----------------------------- contact -----------------------------
from pydantic import BaseModel, EmailStr


class ContactBody(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    subject: str | None = None
    inquiry_type: str | None = None
    service: str | None = None
    message: str


@router.post("/contact", dependencies=[Depends(limiter("contact", 6, 300))])
def submit_contact(body: ContactBody, request: Request, db: Session = Depends(get_db)):
    msg = ContactMessage(
        name=body.name.strip(), email=body.email.lower(), phone=(body.phone or "").strip() or None,
        company=(body.company or "").strip() or None, subject=(body.subject or "").strip() or None,
        inquiry_type=body.inquiry_type, service_required=body.service, message=body.message.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "status": msg.status, "message": "Thanks — we'll be in touch shortly."}
