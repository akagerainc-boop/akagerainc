"""
Mobile Apps — admin-uploaded Android apps with icon, screenshots and an APK.

Public:  GET /api/mobile-apps, GET /api/mobile-apps/{slug}, GET /api/mobile-apps/{slug}/download
Admin:   /api/admin/mobile-apps  (CRUD)  +  POST /api/admin/mobile-apps/{id}/apk  (APK upload)

APKs are stored in the DB in CHUNK_SIZE pieces (see models.MobileAppFile) so they
survive restarts on ephemeral hosts. Downloads open a short DB session per chunk
instead of holding one of the few pooled connections for the whole transfer.
"""
import hashlib
import os
from datetime import datetime

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from admin import admin_guard, row_to_dict, _audit
from database import SessionLocal, get_db
from models import MobileApp, MobileAppFile, MobileAppFileChunk
from ratelimit import limiter
from serializers import media_url
from utils import slugify

router = APIRouter(prefix="/api", tags=["Mobile Apps"])

CHUNK_SIZE = 1024 * 1024
MAX_APK_MB = int(os.getenv("MAX_APK_MB", "150"))
MIN_SCREENSHOTS = 3
APK_MIME = "application/vnd.android.package-archive"

EDITABLE = ("name", "tagline", "description", "category", "version", "min_android", "whats_new",
            "icon", "screenshots", "apk_url", "is_published", "sort_order")


# --------------------------------------------------------------------------
#  Helpers
# --------------------------------------------------------------------------
def _size_label(n) -> str | None:
    if not n:
        return None
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{max(1, n // 1024)} KB"


def _has_apk(a: MobileApp) -> bool:
    return bool(a.apk_file_id or a.apk_url)


def _serialize(a: MobileApp, detail: bool = False) -> dict:
    out = {
        "id": a.id, "name": a.name, "slug": a.slug, "tagline": a.tagline,
        "category": a.category, "version": a.version,
        "icon": media_url(a.icon),
        "screenshots": [media_url(s) for s in (a.screenshots or []) if s],
        "apk_size": a.apk_size, "apk_size_label": _size_label(a.apk_size),
        "download_count": a.download_count or 0,
        "updated_at": (a.apk_uploaded_at or a.updated_at or a.created_at).isoformat()
        if (a.apk_uploaded_at or a.updated_at or a.created_at) else None,
    }
    if detail:
        out.update({
            "description": a.description, "whats_new": a.whats_new, "min_android": a.min_android,
            "apk_filename": a.apk_filename,
            "download_url": f"/api/mobile-apps/{a.slug}/download" if _has_apk(a) else None,
        })
    return out


def _validate(a: MobileApp):
    """Enforce the content rules: icon + >=3 screenshots always; an APK before publishing."""
    if not (a.name or "").strip():
        raise HTTPException(status_code=400, detail="App name is required.")
    if not a.icon:
        raise HTTPException(status_code=400, detail="An app icon is required.")
    shots = [s for s in (a.screenshots or []) if s]
    if len(shots) < MIN_SCREENSHOTS:
        raise HTTPException(status_code=400, detail=f"Add at least {MIN_SCREENSHOTS} screenshots ({len(shots)} so far).")
    if a.apk_url and not a.apk_url.startswith(("https://", "http://")):
        raise HTTPException(status_code=400, detail="The download link must start with https://")
    if a.is_published and not _has_apk(a):
        raise HTTPException(status_code=400, detail="Upload an APK (or set a download link) before publishing.")


def _unique_slug(db: Session, name: str, exclude_id: int | None = None) -> str:
    base = slugify(name) or "app"
    slug, n = base, 1
    while True:
        q = db.query(MobileApp).filter(MobileApp.slug == slug)
        if exclude_id:
            q = q.filter(MobileApp.id != exclude_id)
        if not q.first():
            return slug
        n += 1
        slug = f"{base}-{n}"


def _apply(a: MobileApp, payload: dict):
    for k in EDITABLE:
        if k not in payload:
            continue
        v = payload[k]
        if k == "screenshots":
            v = [s for s in (v or []) if s]
        elif k == "is_published":
            v = bool(v)
        elif k == "sort_order":
            v = int(v or 0)
        elif isinstance(v, str):
            v = v.strip() or None
        setattr(a, k, v)


def _delete_file(db: Session, file_id: int | None):
    if not file_id:
        return
    db.query(MobileAppFileChunk).filter(MobileAppFileChunk.file_id == file_id).delete(synchronize_session=False)
    db.query(MobileAppFile).filter(MobileAppFile.id == file_id).delete(synchronize_session=False)
    db.commit()


# --------------------------------------------------------------------------
#  Public
# --------------------------------------------------------------------------
@router.get("/mobile-apps")
def list_mobile_apps(db: Session = Depends(get_db)):
    rows = (db.query(MobileApp).filter(MobileApp.is_published == True)  # noqa: E712
            .order_by(MobileApp.sort_order, MobileApp.created_at.desc()).all())
    return [_serialize(a) for a in rows]


@router.get("/mobile-apps/{slug}")
def get_mobile_app(slug: str, db: Session = Depends(get_db)):
    a = db.query(MobileApp).filter(MobileApp.slug == slug, MobileApp.is_published == True).first()  # noqa: E712
    if not a:
        raise HTTPException(status_code=404, detail="App not found")
    return _serialize(a, detail=True)


def _stream_chunks(chunk_ids: list[int]):
    for cid in chunk_ids:
        s = SessionLocal()
        try:
            data = s.query(MobileAppFileChunk.data).filter(MobileAppFileChunk.id == cid).scalar()
        finally:
            s.close()
        if data:
            yield data


@router.get("/mobile-apps/{slug}/download", dependencies=[Depends(limiter("apk-download", 20, 600))])
def download_mobile_app(slug: str):
    # Manual session: a Depends(get_db) session would stay checked out for the whole stream.
    db = SessionLocal()
    try:
        a = db.query(MobileApp).filter(MobileApp.slug == slug, MobileApp.is_published == True).first()  # noqa: E712
        if not a or not _has_apk(a):
            raise HTTPException(status_code=404, detail="Download not available")
        a.download_count = (a.download_count or 0) + 1
        db.commit()
        if not a.apk_file_id:
            return RedirectResponse(a.apk_url)
        f = db.query(MobileAppFile).filter(MobileAppFile.id == a.apk_file_id).first()
        chunk_ids = [cid for (cid,) in db.query(MobileAppFileChunk.id)
                     .filter(MobileAppFileChunk.file_id == a.apk_file_id)
                     .order_by(MobileAppFileChunk.seq).all()]
        if not f or not chunk_ids:
            raise HTTPException(status_code=404, detail="APK file missing")
        filename = (f.filename or f"{a.slug}.apk").replace('"', "")
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(f.size),
            "Cache-Control": "no-store",
        }
    finally:
        db.close()
    return StreamingResponse(_stream_chunks(chunk_ids), media_type=APK_MIME, headers=headers)


# --------------------------------------------------------------------------
#  Admin
# --------------------------------------------------------------------------
@router.get("/admin/mobile-apps")
def admin_list(actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    rows = db.query(MobileApp).order_by(MobileApp.sort_order, MobileApp.created_at.desc()).all()
    return [{**row_to_dict(a), "has_apk": _has_apk(a), "apk_size_label": _size_label(a.apk_size)} for a in rows]


@router.post("/admin/mobile-apps")
def admin_create(payload: dict = Body(...), actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    a = MobileApp(download_count=0)
    _apply(a, payload)
    _validate(a)
    a.slug = _unique_slug(db, a.name)
    db.add(a)
    db.commit()
    db.refresh(a)
    _audit(db, actor, "create", "mobile-apps", a.id, {"name": a.name})
    return {**row_to_dict(a), "has_apk": _has_apk(a)}


@router.patch("/admin/mobile-apps/{app_id}")
def admin_update(app_id: int, payload: dict = Body(...),
                 actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    a = db.query(MobileApp).filter(MobileApp.id == app_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="App not found")
    old_name = a.name
    _apply(a, payload)
    _validate(a)
    if a.name != old_name:
        a.slug = _unique_slug(db, a.name, exclude_id=a.id)
    a.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(a)
    _audit(db, actor, "update", "mobile-apps", a.id, {"fields": [k for k in EDITABLE if k in payload]})
    return {**row_to_dict(a), "has_apk": _has_apk(a)}


@router.delete("/admin/mobile-apps/{app_id}")
def admin_delete(app_id: int, actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    a = db.query(MobileApp).filter(MobileApp.id == app_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="App not found")
    for (fid,) in db.query(MobileAppFile.id).filter(MobileAppFile.app_id == app_id).all():
        _delete_file(db, fid)
    db.delete(a)
    db.commit()
    _audit(db, actor, "delete", "mobile-apps", app_id)
    return {"message": "Deleted"}


@router.post("/admin/mobile-apps/{app_id}/apk")
def admin_upload_apk(app_id: int, file: UploadFile = File(...),
                     actor: dict = Depends(admin_guard), db: Session = Depends(get_db)):
    a = db.query(MobileApp).filter(MobileApp.id == app_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="App not found")
    if not (file.filename or "").lower().endswith(".apk"):
        raise HTTPException(status_code=400, detail="Only .apk files are allowed.")

    f = MobileAppFile(app_id=a.id, filename=os.path.basename(file.filename), size=0, chunk_count=0)
    db.add(f)
    db.commit()
    db.refresh(f)

    sha, size, seq = hashlib.sha256(), 0, 0
    try:
        file.file.seek(0)
        head = file.file.read(4)
        if head[:2] != b"PK":  # APKs are zip archives
            raise ValueError("This file is not a valid APK.")
        file.file.seek(0)
        while True:
            buf = file.file.read(CHUNK_SIZE)
            if not buf:
                break
            size += len(buf)
            if size > MAX_APK_MB * 1024 * 1024:
                raise ValueError(f"APK is larger than the {MAX_APK_MB} MB limit.")
            sha.update(buf)
            db.add(MobileAppFileChunk(file_id=f.id, seq=seq, data=buf))
            db.commit()  # one chunk per transaction keeps each INSERT under max_allowed_packet
            seq += 1
        if size == 0:
            raise ValueError("The uploaded file is empty.")
    except ValueError as e:
        db.rollback()
        _delete_file(db, f.id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        _delete_file(db, f.id)
        print(f"[mobile-apps] APK store failed: {e!r}")
        raise HTTPException(status_code=507, detail=(
            "Could not store the APK in the database (it may be full or the file too large for "
            "the host). Paste an external download link instead."))

    f.size, f.sha256, f.chunk_count = size, sha.hexdigest(), seq
    old_file_id = a.apk_file_id
    a.apk_file_id, a.apk_filename, a.apk_size = f.id, f.filename, size
    a.apk_uploaded_at = a.updated_at = datetime.utcnow()
    db.commit()
    if old_file_id and old_file_id != f.id:
        _delete_file(db, old_file_id)
    db.refresh(a)
    _audit(db, actor, "apk_upload", "mobile-apps", a.id, {"size": size, "filename": f.filename})
    return {**row_to_dict(a), "has_apk": True, "apk_size_label": _size_label(size), "sha256": f.sha256}
