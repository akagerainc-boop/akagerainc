"""Plain-dict serializers shared by public + admin routers."""
import os
from datetime import datetime, date

from utils import duration_label as _duration_label


def _iso(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _num(v):
    return float(v) if v is not None else None


def media_url(path: str | None) -> str | None:
    """Normalise a stored media reference to a browser URL."""
    if not path:
        return None
    if path.startswith(("http://", "https://", "data:")):
        return path
    p = path.replace("\\", "/").lstrip("/")
    if p.startswith(("api/", "uploads/")):
        return "/" + p
    return "/uploads/" + p


def serialize_product(a) -> dict:
    return {
        "id": a.id,
        "slug": a.slug or f"product-{a.id}",
        "name": a.name,
        "description": a.description,
        "short_description": a.short_description,
        "category": a.category,
        "status": a.status or "published",
        "version": a.version,
        "release_date": _iso(a.release_date),
        "platforms": a.platforms or [],
        "features": a.features or [],
        "how_it_works": a.how_it_works,
        "installation_steps": a.installation_steps or [],
        "requires_license": bool(a.requires_license),
        "pricing_model": a.pricing_model or "free",
        "price": _num(a.price),
        "subscription_options": a.subscription_options or [],
        "download_url": a.download_url,
        "play_store_url": a.play_store_url,
        "app_store_url": a.app_store_url,
        "website_url": a.website_url,
        "documentation_url": a.documentation_url,
        "screenshots": [media_url(s) for s in (a.screenshots or [])],
        "app_icon": media_url(a.app_icon),
        "app_logo": media_url(a.app_logo),
        "app_image": media_url(a.app_image),
        "is_featured": bool(a.is_featured),
        "sort_order": a.sort_order or 0,
        "created_at": _iso(a.created_at),
        "downloads": [serialize_download(d) for d in getattr(a, "downloads", []) if d.is_active],
    }


def serialize_download(d) -> dict:
    return {
        "id": d.id,
        "product_id": d.product_id,
        "platform": d.platform,
        "label": d.label,
        "url": media_url(d.file_path) or d.external_url,
        "version": d.version,
        "architecture": d.architecture,
        "file_size": d.file_size,
        "min_os": d.min_os,
        "release_notes": d.release_notes,
        "released_at": _iso(d.released_at),
        "is_active": bool(d.is_active),
    }


def serialize_service_field(f) -> dict:
    return {
        "id": f.id,
        "label": f.label,
        "field_key": f.field_key,
        "field_type": f.field_type or "text",
        "options": f.options or [],
        "required": bool(f.required),
        "help_text": f.help_text,
        "sort_order": f.sort_order or 0,
    }


def serialize_service(s, include_fields: bool = False) -> dict:
    data = {
        "id": s.id,
        "slug": s.slug or f"service-{s.id}",
        "name": s.name,
        "description": s.description,
        "short_description": s.short_description,
        "price": _num(s.price),
        "currency": s.currency or "USD",
        "icon": s.icon,
        "image_url": media_url(s.image_url),
        "category": s.category,
        "service_type": s.service_type,
        "duration_value": s.duration_value,
        "duration_unit": s.duration_unit,
        "duration_label": _duration_label(s.duration_value, s.duration_unit, s.duration_label),
        "features": s.features or [],
        "requirements": s.requirements or [],
        "process_steps": s.process_steps or [],
        "faqs": s.faqs or [],
        "terms": s.terms,
        "delivery_method": s.delivery_method,
        "status": s.status or "published",
        "availability": s.availability or "available",
        "is_featured": bool(s.is_featured),
        "popular": bool(s.popular),
        "sort_order": s.sort_order or 0,
        "grants_business_portal_access": bool(s.grants_business_portal_access),
        "created_at": _iso(s.created_at),
    }
    if include_fields:
        data["fields"] = [serialize_service_field(f) for f in sorted(s.fields, key=lambda x: x.sort_order or 0)]
    return data


def serialize_blog(p, full: bool = False) -> dict:
    data = {
        "id": p.id,
        "slug": p.slug,
        "title": p.title,
        "excerpt": p.excerpt,
        "cover_image": media_url(p.cover_image),
        "author": p.author,
        "category": p.category,
        "tags": p.tags or [],
        "reading_time": p.reading_time or 3,
        "is_featured": bool(p.is_featured),
        "status": p.status,
        "published_at": _iso(p.published_at or p.created_at),
    }
    if full:
        data["body"] = p.body
    return data


def serialize_case_study(c, full: bool = False) -> dict:
    data = {
        "id": c.id, "slug": c.slug, "title": c.title, "client": c.client,
        "category": c.category, "summary": c.summary,
        "cover_image": media_url(c.cover_image),
        "technologies": c.technologies or [], "platforms": c.platforms or [],
        "is_featured": bool(c.is_featured), "link": c.link,
    }
    if full:
        data.update({
            "challenge": c.challenge, "solution": c.solution, "results": c.results,
            "screenshots": [media_url(s) for s in (c.screenshots or [])],
        })
    return data


def serialize_internship(i, full: bool = False) -> dict:
    data = {
        "id": i.id, "slug": i.slug, "title": i.title, "department": i.department,
        "duration_label": i.duration_label, "positions": i.positions,
        "is_free": bool(i.is_free), "price": _num(i.price),
        "deadline": _iso(i.deadline), "status": i.status,
        "start_date": _iso(i.start_date), "end_date": _iso(i.end_date),
    }
    if full:
        data.update({"description": i.description, "requirements": i.requirements or []})
    return data


def serialize_job(j, full: bool = False) -> dict:
    data = {
        "id": j.id, "slug": j.slug, "title": j.title, "department": j.department,
        "location": j.location, "employment_type": j.employment_type, "status": j.status,
    }
    if full:
        data.update({
            "description": j.description,
            "responsibilities": j.responsibilities or [],
            "requirements": j.requirements or [],
            "benefits": j.benefits or [],
        })
    return data


def serialize_doc(d, full: bool = False) -> dict:
    data = {"id": d.id, "slug": d.slug, "section": d.section, "title": d.title,
            "sort_order": d.sort_order or 0}
    if full:
        data["body"] = d.body
    return data


def serialize_industry(x, full: bool = False) -> dict:
    data = {"id": x.id, "slug": x.slug, "name": x.name, "icon": x.icon, "summary": x.summary}
    if full:
        data["body"] = x.body
    return data


def serialize_testimonial(t) -> dict:
    return {"id": t.id, "name": t.name, "role": t.role, "company": t.company,
            "quote": t.quote, "avatar": media_url(t.avatar), "rating": t.rating or 5}


def serialize_faq(f) -> dict:
    return {"id": f.id, "category": f.category, "question": f.question, "answer": f.answer}


def serialize_order(o) -> dict:
    return {
        "id": o.id,
        "order_ref": o.order_ref,
        "status": o.status,
        "subtotal": _num(o.subtotal),
        "total": _num(o.total),
        "currency": o.currency,
        "created_at": _iso(o.created_at),
        "items": [{
            "id": it.id, "item_type": it.item_type, "ref_id": it.ref_id, "name": it.name,
            "unit_amount": _num(it.unit_amount), "quantity": it.quantity,
            "duration_label": it.duration_label, "form_data": it.form_data or {},
        } for it in o.items],
        "invoices": [{"invoice_ref": iv.invoice_ref, "amount": _num(iv.amount),
                      "issued_at": _iso(iv.issued_at)} for iv in getattr(o, "invoices", [])],
    }


def serialize_subscription(s) -> dict:
    return {
        "id": s.id, "item_type": s.item_type, "ref_id": s.ref_id, "plan_name": s.plan_name,
        "price": _num(s.price), "currency": s.currency, "billing_period": s.billing_period,
        "status": s.status, "start_date": _iso(s.start_date), "renewal_date": _iso(s.renewal_date),
        "expires_at": _iso(s.expires_at),
    }


def serialize_license(l) -> dict:
    return {
        "id": l.id, "license_key": l.license_key, "license_type": l.license_type,
        "status": l.status, "is_active": bool(l.is_active), "max_devices": l.max_devices,
        "service_id": l.service_id, "app_id": l.app_id,
        "starts_at": _iso(l.starts_at), "expires_at": _iso(l.expires_at),
        "created_at": _iso(l.created_at),
    }


def serialize_ticket(t, with_messages: bool = False) -> dict:
    data = {
        "id": t.id, "ticket_ref": t.ticket_ref, "subject": t.subject, "category": t.category,
        "priority": t.priority, "status": t.status, "created_at": _iso(t.created_at),
        "email": t.email, "name": t.name,
    }
    if with_messages:
        data["messages"] = [{
            "id": m.id, "sender": m.sender, "body": m.body,
            "attachment": media_url(m.attachment_path), "created_at": _iso(m.created_at),
        } for m in t.messages]
    return data


def serialize_nav(items) -> list:
    """Build a nested header/footer nav tree from flat NavigationItem rows."""
    by_id = {i.id: {
        "id": i.id, "label": i.label, "url": i.url, "location": i.location,
        "column_group": i.column_group, "sort_order": i.sort_order or 0,
        "children": [],
    } for i in items if i.is_enabled}
    roots = []
    for i in items:
        if not i.is_enabled:
            continue
        node = by_id[i.id]
        if i.parent_id and i.parent_id in by_id:
            by_id[i.parent_id]["children"].append(node)
        else:
            roots.append(node)
    for n in by_id.values():
        n["children"].sort(key=lambda x: x["sort_order"])
    roots.sort(key=lambda x: x["sort_order"])
    return roots
