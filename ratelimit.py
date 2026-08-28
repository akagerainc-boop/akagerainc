"""Tiny in-memory sliding-window rate limiter (per-process). Good enough for Phase 1."""
import time
from collections import deque
from fastapi import Request, HTTPException

_BUCKETS: dict[str, deque] = {}


def rate_limit(key: str, limit: int, window_seconds: int):
    now = time.time()
    dq = _BUCKETS.setdefault(key, deque())
    while dq and dq[0] < now - window_seconds:
        dq.popleft()
    if len(dq) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down and try again.")
    dq.append(now)


def limiter(prefix: str, limit: int = 10, window_seconds: int = 60):
    """FastAPI dependency factory keyed by client IP."""
    def _dep(request: Request):
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown")
        rate_limit(f"{prefix}:{ip}", limit, window_seconds)
    return _dep
