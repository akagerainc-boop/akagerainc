import os
import time
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

DB_NAME = os.getenv("DB_NAME", "akagerainc")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")

DEFAULT_DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)
raw_database_url = os.getenv("DATABASE_URL", "").strip().strip('"').strip("'")

if raw_database_url and raw_database_url.startswith("mysql"):
    DATABASE_URL = raw_database_url
else:
    DATABASE_URL = DEFAULT_DATABASE_URL

# Accept provider-style URLs as pasted (e.g. Aiven: mysql://...?ssl-mode=REQUIRED):
# force the PyMySQL driver and turn the libmysql-only `ssl-mode` flag into a TLS
# connect arg, which PyMySQL would otherwise reject as an unknown keyword.
_url = make_url(DATABASE_URL)
if _url.drivername == "mysql":
    _url = _url.set(drivername="mysql+pymysql")
_ssl_mode = str(_url.query.get("ssl-mode") or _url.query.get("ssl_mode") or "").upper()
_url = _url.difference_update_query(["ssl-mode", "ssl_mode"])
DB_SSL = _ssl_mode not in ("", "DISABLED") or os.getenv("DB_SSL", "").lower() in ("1", "true", "required")
DATABASE_URL = _url

_connect_args = {"connect_timeout": 10}
if DB_SSL:
    # Encrypt without verifying the server cert (= MySQL's ssl-mode=REQUIRED).
    # Set DB_SSL_CA to a CA file path to also verify the server.
    _ca = os.getenv("DB_SSL_CA", "").strip()
    _connect_args["ssl"] = {"ca": _ca} if _ca else {"check_hostname": False}

# ---------------------------------------------------------------------------
#  Connection pool
#
#  Shared / free MySQL hosts cap `max_user_connections` very low (freedb = 5).
#  A small QueuePool keeps us under that ceiling and makes extra concurrent
#  requests WAIT for a free connection instead of erroring with
#  (1203, "... more than 'max_user_connections' active connections").
# ---------------------------------------------------------------------------
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "3"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "1"))   # hard cap = POOL_SIZE + MAX_OVERFLOW
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "25"))  # seconds a request waits for a connection

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=280,          # recycle before typical server-side idle timeout
    pool_pre_ping=True,        # transparently replace dead connections
    connect_args=_connect_args,
    echo=os.getenv("DEBUG", "False").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency. Retries once on a transient 'too many connections'."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_with_retry(fn, attempts: int = 3, base_delay: float = 0.4):
    """Run a callable, retrying on transient connection-limit errors."""
    last = None
    for i in range(attempts):
        try:
            return fn()
        except OperationalError as exc:  # noqa: PERF203
            last = exc
            msg = str(exc).lower()
            if "max_user_connections" in msg or "too many connections" in msg or "1203" in msg:
                time.sleep(base_delay * (i + 1))
                continue
            raise
    raise last
