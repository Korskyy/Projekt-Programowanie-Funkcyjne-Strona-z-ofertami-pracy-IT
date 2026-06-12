"""
backend
Endpointy:
    GET  /                 - zwraca frontend (static/index.html)
    GET  /api/jobs         - lista ofert, można filtrować, sortować, są strony (paginacja)
    GET  /api/jobs/{id}    - jedna konkretna oferta
    GET  /api/stats        - statystyki: widełki płacowe, top umiejętności, różne rozkłady
    GET  /api/meta         - jakie wartości filtrów są dostępne (do selectów na froncie)
    POST /api/admin/update - odświeża bazę (to jest pod panelem admina)

Uruchomienie:
    uvicorn main:app --reload
    http://127.0.0.1:8000
"""

from __future__ import annotations

import os
import pathlib
from math import ceil
from typing import Optional

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from db import JobOffer, SessionLocal
from schemas import (
    JobOfferOut,
    JobsResponse,
    MetaResponse,
    SalaryStat,
    SkillCount,
    StatsResponse,
    UpdateRequest,
    UpdateResponse,
)
from tech_data import EXCHANGE_RATES_TO_PLN
from update_db import run_update

# Klucz do /api/admin/update
ADMIN_KEY = os.environ.get("ADMIN_KEY", "admin123")

BASE_DIR = pathlib.Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="IT Job Board API",
    description="API do przeszukiwania ofert pracy IT i analizy rynku.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")

# /api/jobs @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
SORTABLE_COLUMNS = {
    "posted_at": JobOffer.posted_at,
    "salary_min": JobOffer.salary_min,
    "salary_max": JobOffer.salary_max,
    "title": JobOffer.title,
    "company": JobOffer.company,
}


@app.get("/api/jobs", response_model=JobsResponse)
def get_jobs(
    db: Session = Depends(get_db),
    keyword: Optional[str] = Query(None, description="Szukana fraza w tytule, firmie lub umiejętnościach"),
    technology: Optional[str] = Query(None, description="Dokładna nazwa technologii, np. 'Python'"),
    location: Optional[str] = Query(None, description="Fragment lokalizacji, np. 'Warszawa'"),
    experience_level: Optional[str] = Query(None, description="Junior / Mid / Senior / Lead / Nieznany"),
    work_mode: Optional[str] = Query(None, description="Remote / Hybrid / Office / Nieznany"),
    source: Optional[str] = Query(None, description="RemoteOK / Arbeitnow / Generated"),
    salary_min: Optional[float] = Query(None, ge=0, description="Pokaż oferty płacące co najmniej tyle"),
    salary_max: Optional[float] = Query(None, ge=0, description="Pokaż oferty z dolną granicą widełek nie większą niż to"),
    sort_by: str = Query("posted_at", description=f"Jedno z: {', '.join(SORTABLE_COLUMNS)}"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(JobOffer)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(
            JobOffer.title.ilike(like),
            JobOffer.company.ilike(like),
            JobOffer.skills.ilike(like),
        ))
    if technology:
        query = query.filter(JobOffer.technology == technology)
    if location:
        query = query.filter(JobOffer.location.ilike(f"%{location}%"))
    if experience_level:
        query = query.filter(JobOffer.experience_level == experience_level)
    if work_mode:
        query = query.filter(JobOffer.work_mode == work_mode)
    if source:
        query = query.filter(JobOffer.source == source)
    if salary_min is not None:
        query = query.filter(func.coalesce(JobOffer.salary_max, JobOffer.salary_min) >= salary_min)
    if salary_max is not None:
        query = query.filter(func.coalesce(JobOffer.salary_min, JobOffer.salary_max) <= salary_max)

    total = query.count()

    sort_column = SORTABLE_COLUMNS.get(sort_by, JobOffer.posted_at)
    sort_column = sort_column.desc().nullslast() if order == "desc" else sort_column.asc().nullslast()
    query = query.order_by(sort_column)

    total_pages = ceil(total / page_size) if total else 0
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return JobsResponse(total=total, page=page, page_size=page_size, total_pages=total_pages, items=items)


@app.get("/api/jobs/{job_id}", response_model=JobOfferOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobOffer).filter(JobOffer.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Oferta o podanym id nie istnieje")
    return job


# /api/meta @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@app.get("/api/meta", response_model=MetaResponse)
def get_meta(db: Session = Depends(get_db)):
    def distinct_values(column) -> list[str]:
        return sorted(value for (value,) in db.query(column).distinct().all() if value)

    return MetaResponse(
        technologies=distinct_values(JobOffer.technology),
        locations=distinct_values(JobOffer.location),
        experience_levels=distinct_values(JobOffer.experience_level),
        work_modes=distinct_values(JobOffer.work_mode),
        sources=distinct_values(JobOffer.source),
    )

# /api/stats @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def _row_salary_avg(row: pd.Series) -> Optional[float]:
    """Liczy "środek" widełek dla jednej oferty (czyli (min+max)/2). Jeśli
    jest tylko jedna granica, to ją bierzemy jako przybliżenie wynagrodzenia.
    Jak nie ma żadnej, zwracamy None."""
    salary_min, salary_max = row["salary_min"], row["salary_max"]
    if pd.notna(salary_min) and pd.notna(salary_max):
        return (salary_min + salary_max) / 2
    if pd.notna(salary_min):
        return salary_min
    if pd.notna(salary_max):
        return salary_max
    return None


def _build_salary_stat(group: pd.DataFrame) -> SalaryStat:
    subset = group.dropna(subset=["salary_avg"])
    if subset.empty:
        return SalaryStat(count=0)

    return SalaryStat(
        count=len(subset),
        salary_min_avg=round(subset["salary_min"].mean(), 2) if subset["salary_min"].notna().any() else None,
        salary_max_avg=round(subset["salary_max"].mean(), 2) if subset["salary_max"].notna().any() else None,
        salary_avg=round(subset["salary_avg"].mean(), 2),
        salary_median=round(subset["salary_avg"].median(), 2),
        salary_p25=round(subset["salary_avg"].quantile(0.25), 2),
        salary_p75=round(subset["salary_avg"].quantile(0.75), 2),
    )


def _value_counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().items()}


@app.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    jobs = db.query(JobOffer).all()

    if not jobs:
        return StatsResponse(
            total_offers=0,
            offers_with_salary=0,
            last_updated=None,
            salary_by_technology={},
            salary_by_experience={},
            top_skills=[],
            offers_by_location={},
            offers_by_work_mode={},
            offers_by_experience={},
            offers_by_source={},
        )

    df = pd.DataFrame([{
        "technology": j.technology,
        "experience_level": j.experience_level,
        "location": j.location,
        "work_mode": j.work_mode,
        "source": j.source,
        "skills": j.skills or "",
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "salary_currency": j.salary_currency,
        "fetched_at": j.fetched_at,
    } for j in jobs])

    # przeliczenie do jednej waluty
    rate = df["salary_currency"].map(EXCHANGE_RATES_TO_PLN).fillna(1.0)
    df["salary_min"] = df["salary_min"] * rate
    df["salary_max"] = df["salary_max"] * rate

    df["salary_avg"] = df.apply(_row_salary_avg, axis=1)

    salary_by_technology = {
        str(tech): _build_salary_stat(group) for tech, group in df.groupby("technology")
    }
    salary_by_experience = {
        str(level): _build_salary_stat(group) for level, group in df.groupby("experience_level")
    }

    skills_series = df["skills"].str.split(",").explode().str.strip()
    skills_series = skills_series[skills_series != ""]
    top_skills_counts = skills_series.value_counts().head(10)
    top_skills = [
        SkillCount(skill=skill, count=int(count), percent=round(count / len(df) * 100, 1))
        for skill, count in top_skills_counts.items()
    ]

    last_updated = df["fetched_at"].dropna().max()
    if pd.isna(last_updated):
        last_updated = None

    return StatsResponse(
        total_offers=len(df),
        offers_with_salary=int(df["salary_avg"].notna().sum()),
        last_updated=last_updated,
        salary_by_technology=salary_by_technology,
        salary_by_experience=salary_by_experience,
        top_skills=top_skills,
        offers_by_location=_value_counts(df["location"]),
        offers_by_work_mode=_value_counts(df["work_mode"]),
        offers_by_experience=_value_counts(df["experience_level"]),
        offers_by_source=_value_counts(df["source"]),
    )


# /api/admin/update @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@app.post("/api/admin/update", response_model=UpdateResponse)
def admin_update(payload: UpdateRequest, x_admin_key: Optional[str] = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Nieprawidłowy lub brakujący nagłówek X-Admin-Key",
        )

    result = run_update(
        sources=payload.sources,
        reset=payload.reset,
        generated_count=payload.generated_count,
    )

    return UpdateResponse(
        message="Baza danych została zaktualizowana",
        total_offers=result["total_offers"],
        details=result["details"],
    )
