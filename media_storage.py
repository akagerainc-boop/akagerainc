"""
Media storage that survives ephemeral hosting (Render, etc.).

Order of preference:
  1. Cloudinary  — if CLOUDINARY_URL is set (recommended; free tier is 25 GB).
  2. DB blob     — resized/compressed bytes in the `images` table, served from
                   `/api/media/{id}`. Fine for a handful of small images; capped
                   so a huge upload can't blow a tiny shared DB.

Set CLOUDINARY_URL (looks like  cloudinary://<key>:<secret>@<cloud-name> ) on the
backend to store originals off-database.
"""
import io
import os
import mimetypes

try:
    from PIL import Image as PILImage
    _PIL = True
    _LANCZOS = getattr(getattr(PILImage, "Resampling", PILImage), "LANCZOS",
                       getattr(PILImage, "LANCZOS", 1))
except Exception:  # pragma: no cover
    _PIL = False
    _LANCZOS = 1

# (max width px, JPEG quality) per use
PROFILES = {
    "carousel": (1500, 74),
    "hero": (1500, 74),
    "cover": (1280, 76),
    "screenshot": (1280, 76),
    "logo": (512, 82),
    "icon": (256, 86),
    "avatar": (256, 86),
    "misc": (1280, 76),
}

PASSTHROUGH_EXT = {"svg"}

# hard caps for the DB-blob fallback (KB). Cloudinary path is unlimited.
DB_IMAGE_MAX_KB = int(os.getenv("DB_IMAGE_MAX_KB", "1200"))
DB_FILE_MAX_KB = int(os.getenv("DB_FILE_MAX_KB", "2500"))

_CLOUD_HINT = ("The file is too large to store in the database. Set a CLOUDINARY_URL "
               "environment variable on the backend (free at cloudinary.com) so uploads "
               "go to Cloudinary, or upload a smaller file.")


def cloudinary_configured() -> bool:
    return bool(os.getenv("CLOUDINARY_URL", "").strip())


def process_image(raw: bytes, filename: str, profile: str = "misc") -> tuple[bytes, str, str]:
    """Return (bytes, mime_type, ext) — resized/compressed unless SVG."""
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else "jpg"
    if ext in PASSTHROUGH_EXT or not _PIL:
        mime = {"svg": "image/svg+xml", "gif": "image/gif", "png": "image/png",
                "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/jpeg")
        return raw, mime, ext

    max_w, quality = PROFILES.get(profile, PROFILES["misc"])
    try:
        im = PILImage.open(io.BytesIO(raw))
        im.load()
        if getattr(im, "is_animated", False):  # first frame of a GIF/animated webp
            im.seek(0)
        if im.width > max_w:
            ratio = max_w / float(im.width)
            im = im.resize((max_w, int(im.height * ratio)), _LANCZOS)
        im = im.convert("RGB")
        for q in (quality, 66, 58, 50):
            out = io.BytesIO()
            im.save(out, format="JPEG", quality=q, optimize=True, progressive=True)
            data = out.getvalue()
            if len(data) <= DB_IMAGE_MAX_KB * 1024 or cloudinary_configured():
                return data, "image/jpeg", "jpg"
        return data, "image/jpeg", "jpg"
    except Exception:
        return raw, "image/jpeg", ext or "jpg"


def cloudinary_upload(raw: bytes, filename: str, resource_type: str = "image") -> str | None:
    url = os.getenv("CLOUDINARY_URL", "").strip()
    if not url:
        return None
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloudinary_url=url, secure=True)
        res = cloudinary.uploader.upload(io.BytesIO(raw), folder="akagerainc",
                                         resource_type=resource_type, overwrite=False,
                                         use_filename=True, unique_filename=True)
        return res.get("secure_url")
    except Exception as exc:  # pragma: no cover
        print(f"[cloudinary] upload failed: {exc}")
        return None


def store_image_bytes(raw: bytes, filename: str, profile: str = "misc") -> tuple[str | None, bytes | None, str]:
    """
    Returns (cloud_url, blob, mime). Exactly one of cloud_url / blob is set.
    Raises ValueError if it can't be stored (too big, no Cloudinary).
    """
    cloud = cloudinary_upload(raw, filename, resource_type="image")
    if cloud:
        return cloud, None, "image/jpeg"
    blob, mime, _ext = process_image(raw, filename, profile)
    if len(blob) > DB_IMAGE_MAX_KB * 1024:
        raise ValueError(_CLOUD_HINT)
    return None, blob, mime


def persist_file(db, raw: bytes, filename: str, tag: str = "file") -> str:
    """Store an arbitrary file (CV, resume...). Returns a URL. Raises ValueError if too big for the DB."""
    from models import Image
    mime = mimetypes.guess_type(filename or "")[0] or "application/octet-stream"
    is_img = mime.startswith("image/")
    cloud = cloudinary_upload(raw, filename, resource_type="image" if is_img else "raw")
    if not cloud and len(raw) > DB_FILE_MAX_KB * 1024:
        raise ValueError(_CLOUD_HINT)
    row = Image(url=cloud, data=(None if cloud else raw), filename=filename or "file",
                mime_type=mime, page_type=tag, is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return cloud or f"/api/media/{row.id}"
