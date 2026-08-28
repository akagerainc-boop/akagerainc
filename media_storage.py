"""
Image storage that survives ephemeral hosting (Render, etc.).

Instead of writing to local disk (wiped on every deploy), images are resized,
compressed, and stored as bytes in the `images` table, then served from
`/api/media/{id}` with a long immutable cache.

If CLOUDINARY_URL is set we upload there instead and just keep the returned URL.
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

# max width (px) and JPEG quality per use
PROFILES = {
    "carousel": (1600, 78),
    "hero": (1600, 78),
    "cover": (1400, 80),
    "screenshot": (1400, 80),
    "logo": (512, 85),
    "icon": (256, 88),
    "avatar": (256, 88),
    "misc": (1400, 80),
}

PASSTHROUGH_EXT = {"svg", "gif"}   # don't re-encode


def process_image(raw: bytes, filename: str, profile: str = "misc") -> tuple[bytes, str, str]:
    """Return (bytes, mime_type, ext) — resized/compressed unless it's SVG/GIF."""
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else "jpg"
    if ext in PASSTHROUGH_EXT or not _PIL:
        mime = {"svg": "image/svg+xml", "gif": "image/gif", "png": "image/png",
                "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/jpeg")
        return raw, mime, ext

    max_w, quality = PROFILES.get(profile, PROFILES["misc"])
    try:
        im = PILImage.open(io.BytesIO(raw))
        im.load()
        has_alpha = im.mode in ("RGBA", "LA", "P")
        if im.width > max_w:
            ratio = max_w / float(im.width)
            im = im.resize((max_w, int(im.height * ratio)), _LANCZOS)
        out = io.BytesIO()
        if has_alpha and ext == "png":
            im.save(out, format="PNG", optimize=True)
            return out.getvalue(), "image/png", "png"
        im = im.convert("RGB")
        im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        return out.getvalue(), "image/jpeg", "jpg"
    except Exception:
        return raw, "image/jpeg", ext or "jpg"


def cloudinary_upload(raw: bytes, filename: str, resource_type: str = "image") -> str | None:
    """Upload to Cloudinary if CLOUDINARY_URL is configured. Returns the secure URL or None."""
    url = os.getenv("CLOUDINARY_URL", "")
    if not url:
        return None
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(cloudinary_url=url, secure=True)
        res = cloudinary.uploader.upload(io.BytesIO(raw), folder="akagerainc",
                                         resource_type=resource_type, overwrite=False,
                                         filename_override=filename, use_filename=True)
        return res.get("secure_url")
    except Exception as exc:  # pragma: no cover
        print(f"[cloudinary] upload failed, falling back to DB blob: {exc}")
        return None


def persist_file(db, raw: bytes, filename: str, tag: str = "file") -> str:
    """
    Store an arbitrary file (CV, resume, ...) so it survives redeploys.
    Reuses the `images` table as a generic blob store. Returns a URL.
    """
    from models import Image
    mime = mimetypes.guess_type(filename or "")[0] or "application/octet-stream"
    cloud = cloudinary_upload(raw, filename, resource_type="raw" if not mime.startswith("image/") else "image")
    row = Image(url=cloud, data=(None if cloud else raw), filename=filename or "file",
                mime_type=mime, page_type=tag, is_active=True)
    db.add(row)
    db.commit()
    db.refresh(row)
    return cloud or f"/api/media/{row.id}"
