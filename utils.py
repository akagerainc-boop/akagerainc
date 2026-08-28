import os
import secrets
import string
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import re

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

LICENSE_KEY_LENGTH = int(os.getenv("LICENSE_KEY_LENGTH", 10))


def generate_license_key(length: int = LICENSE_KEY_LENGTH) -> str:
    """
    Generate a secure random license key.
    Format: Uppercase letters and numbers only
    Example: A7K9Z3P2QX
    """
    characters = string.ascii_uppercase + string.digits
    license_key = ''.join(secrets.choice(characters) for _ in range(length))
    return license_key


def generate_hex_license_key(length: int = 16) -> str:
    """Generate a ready-to-copy hex credential used by mobile/desktop apps."""
    return ''.join(secrets.choice('0123456789ABCDEF') for _ in range(length)).upper()


def slugify(value: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9]+', '-', (value or '').strip())
    return value.strip('-').lower() or 'service'


def hash_password(password: str) -> str:
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return hash_password(password) == hashed_password


def get_license_expiry_date(days: int = 365) -> datetime:
    """Get license expiry date (default 1 year from now)"""
    return datetime.utcnow() + timedelta(days=days)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount with currency"""
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "RWF":
        return f"RWF {amount:,.0f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_request_ip(request) -> str:
    """Extract client IP from request"""
    fwd = None
    try:
        fwd = request.headers.get("x-forwarded-for")
    except Exception:
        fwd = None
    if fwd:
        return fwd.split(",")[0].strip()
    if getattr(request, "client", None):
        return request.client.host
    return "Unknown"


# ---------------------------------------------------------------------------
#  Duration model helpers
# ---------------------------------------------------------------------------
_UNIT_DAYS = {
    "hour": 1 / 24,
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}


def duration_to_days(value, unit) -> int | None:
    """Convert a (value, unit) duration into a day count. None => no expiry."""
    if not unit:
        return None
    unit = str(unit).lower()
    if unit in ("lifetime", "one_time"):
        return None
    if unit == "custom":
        return int(value) if value else None
    per = _UNIT_DAYS.get(unit)
    if per is None:
        return None
    return int(round((value or 1) * per))


def duration_label(value, unit, fallback: str | None = None) -> str:
    """Human label, e.g. 'Valid for 1 year', 'Duration: 3 months', 'Lifetime access'."""
    if fallback:
        return fallback
    if not unit:
        return "One-time service"
    unit = str(unit).lower()
    if unit == "lifetime":
        return "Lifetime access"
    if unit == "one_time":
        return "One-time service"
    v = int(value) if value else 1
    noun = unit if v == 1 else unit + "s"
    return f"{v} {noun}"


def compute_expiry(start, value, unit):
    from datetime import datetime, timedelta
    start = start or datetime.utcnow()
    days = duration_to_days(value, unit)
    if days is None:
        return None
    return start + timedelta(days=days)


# ---------------------------------------------------------------------------
#  Upload validation
# ---------------------------------------------------------------------------
IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "svg", "avif"}
DOC_EXT = {"pdf", "doc", "docx", "txt", "rtf", "odt"}
INSTALLER_EXT = {"apk", "ipa", "exe", "msi", "dmg", "pkg", "zip", "appimage", "deb"}


def _ext(filename: str) -> str:
    return (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""


def validate_upload(filename: str, size_bytes: int, kind: str = "image"):
    """Raise ValueError when an upload is not acceptable for the given kind."""
    ext = _ext(filename)
    allowed = {
        "image": IMAGE_EXT,
        "doc": DOC_EXT | IMAGE_EXT,
        "installer": INSTALLER_EXT,
    }.get(kind, IMAGE_EXT)
    if ext not in allowed:
        raise ValueError(f"File type .{ext or '?'} not allowed for {kind}. Allowed: {', '.join(sorted(allowed))}")
    max_mb = int(os.getenv("MAX_INSTALLER_MB", "300")) if kind == "installer" else int(os.getenv("MAX_UPLOAD_MB", "25"))
    if size_bytes and size_bytes > max_mb * 1024 * 1024:
        raise ValueError(f"File too large ({size_bytes // (1024 * 1024)} MB). Max {max_mb} MB.")
    return ext


def make_ref(prefix: str) -> str:
    """Short human order/invoice/ticket reference, e.g. ORD-3F9K2A."""
    alphabet = string.ascii_uppercase + string.digits
    return f"{prefix}-" + "".join(secrets.choice(alphabet) for _ in range(6))
