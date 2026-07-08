from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_query(db, sql: str, params: dict | None = None):
    """Executes raw SQL and returns list of dicts. We use raw SQL
    (not the ORM) throughout this project deliberately -- the whole
    point of the project is demonstrating SQL, and an ORM would hide
    the window functions/CTEs behind abstractions."""
    result = db.execute(text(sql), params or {})
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]
