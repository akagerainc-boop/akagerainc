import os
import time
from pathlib import Path

from sqlalchemy import create_engine, event
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
    connect_args={"connect_timeout": 10},
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
