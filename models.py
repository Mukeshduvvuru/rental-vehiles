"""
database.py — PostgreSQL connection & session management

WHY SQLAlchemy?
  SQLAlchemy is an ORM (Object Relational Mapper). Instead of writing raw SQL
  like "SELECT * FROM vehicles WHERE status='available'", we write Python:
      db.query(Vehicle).filter(Vehicle.status == 'available').all()
  Benefits:
    - No SQL injection risk (parameterized queries automatically)
    - Easier to read and maintain
    - Can swap to SQLite for tests without changing any other code
    - Connection pooling built-in (reuses DB connections = faster)

HOW IT WORKS:
  1. engine  → the single connection to PostgreSQL
  2. SessionLocal → a factory that creates individual DB sessions
  3. get_db()     → a FastAPI dependency; injects a fresh session per request
                    and GUARANTEES it's closed afterward (even on error)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Load .env file so os.getenv() picks up our secrets
load_dotenv()

# ---------------------------------------------------------------------------
# Connection string  (falls back to a local default if .env is missing)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:0000@localhost:5432/rental_db"
)

# pool_pre_ping=True: before handing a connection from the pool, SQLAlchemy
# sends a lightweight "ping" to verify the connection is still alive.
# This prevents "connection closed" errors after PostgreSQL restarts.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# autocommit=False  → we manually commit; gives us transaction control
# autoflush=False   → prevents accidental partial writes mid-transaction
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM model classes will inherit from this Base.
# Base.metadata.create_all(engine) will later create every table automatically.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency — provides a database session to every endpoint.

    Usage in any router:
        @router.get("/vehicles")
        def list_vehicles(db: Session = Depends(get_db)):
            ...

    The 'yield' pattern (generator) guarantees:
        1. A fresh session is opened for the request
        2. The session is ALWAYS closed in 'finally' — even if the
           endpoint raises an exception. No connection leaks!
    """
    db = SessionLocal()
    try:
        yield db          # <-- session handed to the endpoint
    finally:
        db.close()        # <-- always runs, keeps the pool healthy
