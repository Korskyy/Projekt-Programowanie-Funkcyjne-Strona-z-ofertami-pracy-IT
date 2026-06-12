"""
Baza danych + model SQLAlchemy dla jednej oferty pracy.

"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///it_jobs.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(Integer, primary_key=True, index=True)

    # Po tym poznaję skąd jest oferta i robię na tym upsert (patrz docstring wyżej)
    external_id = Column(String, index=True, nullable=False)
    source = Column(String, index=True, nullable=False, default="Generated")

    title = Column(String, index=True, nullable=False)
    company = Column(String, index=True, nullable=False)

    technology = Column(String, index=True, nullable=False, default="Inne")
    skills = Column(String, default="")

    location = Column(String, index=True, default="Remote")
    experience_level = Column(String, index=True, default="Nieznany")
    work_mode = Column(String, index=True, default="Nieznany")

    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String, default="PLN")

    url = Column(String, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_job_source_external_id"),
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


# Tabele tworzą się same przy imporcie tego modułu (tak jak na początku),
# żeby main.py mógł od razu korzystać z bazy bez dodatkowych kroków.
init_db()
