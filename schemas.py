"""
Pydantic
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class JobOfferOut(BaseModel):
    """Pojedyncza oferta pracy zwracana przez API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    source: str

    title: str
    company: str

    technology: str
    skills: str

    location: str
    experience_level: str
    work_mode: str

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str

    url: Optional[str] = None
    posted_at: Optional[datetime] = None


class JobsResponse(BaseModel):
    """Wynik listowania ofert wraz z informacjami o paginacji."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[JobOfferOut]


class SalaryStat(BaseModel):
    """Statystyki wynagrodzeń dla jakiejś grupy ofert (np. wszystkie oferty
    Pythonowe albo wszystkie oferty na poziomie Senior)."""

    count: int = Field(description="Liczba ofert z podaną informacją o wynagrodzeniu")
    salary_min_avg: Optional[float] = Field(None, description="Średnia z dolnych granic widełek (PLN)")
    salary_max_avg: Optional[float] = Field(None, description="Średnia z górnych granic widełek (PLN)")
    salary_avg: Optional[float] = Field(None, description="Średnie wynagrodzenie - środek widełek (PLN)")
    salary_median: Optional[float] = Field(None, description="Mediana wynagrodzenia (PLN)")
    salary_p25: Optional[float] = Field(None, description="25. percentyl wynagrodzenia (PLN)")
    salary_p75: Optional[float] = Field(None, description="75. percentyl wynagrodzenia (PLN)")


class SkillCount(BaseModel):
    skill: str
    count: int
    percent: float


class StatsResponse(BaseModel):
    total_offers: int
    offers_with_salary: int
    last_updated: Optional[datetime] = None
    currency_note: str = Field(
        "Wynagrodzenia z różnych źródeł (PLN/USD/EUR) zostały przeliczone na PLN "
        "po orientacyjnym, statycznym kursie - patrz tech_data.EXCHANGE_RATES_TO_PLN."
    )

    salary_by_technology: dict[str, SalaryStat]
    salary_by_experience: dict[str, SalaryStat]

    top_skills: list[SkillCount]

    offers_by_location: dict[str, int]
    offers_by_work_mode: dict[str, int]
    offers_by_experience: dict[str, int]
    offers_by_source: dict[str, int]


class MetaResponse(BaseModel):
    """Dostępne wartości filtrów - do dynamicznego budowania UI."""

    technologies: list[str]
    locations: list[str]
    experience_levels: list[str]
    work_modes: list[str]
    sources: list[str]


class UpdateRequest(BaseModel):
    sources: list[str] = Field(
        default_factory=lambda: ["remoteok", "arbeitnow", "generated"],
        description="Źródła do pobrania: 'remoteok', 'arbeitnow', 'generated'",
    )
    reset: bool = Field(False, description="Czy wyczyścić bazę przed aktualizacją")
    generated_count: int = Field(60, ge=0, le=500, description="Liczba syntetycznych ofert do wygenerowania")


class UpdateResponse(BaseModel):
    message: str
    total_offers: int
    details: dict
