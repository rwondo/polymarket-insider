from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import settings


def make_engine(url: str):
    # SQLite connections are shared between the worker and the retraining thread
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
