"""
napełnianie/aktualizowanie bazy ofert pracy
   - RemoteOK (https://remoteok.com/api)
   - Arbeitnow (https://www.arbeitnow.com/api/job-board-api)
   - generuje swoje, syntetyczne dane (source = "Generated") 
    Robi UPSERT po (source, external_id) jak oferta już jest w bazie, to
   się aktualizuje, a nie wstawia drugi raz.

    python update_db.py                          # ściągnij wszystko, dopisz/zaktualizuj
    python update_db.py --reset                   # wyczyść bazę i wczytaj od nowa
    python update_db.py --sources generated       # tylko dane wygenerowane
    python update_db.py --sources remoteok arbeitnow --count 0
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

import requests

from db import JobOffer, SessionLocal, init_db
from tech_data import (
    BASE_SALARY_RANGES,
    COMMON_SKILLS,
    COMPANY_FORMS,
    COMPANY_PREFIXES,
    COMPANY_SUFFIXES,
    EXPERIENCE_LEVELS,
    LOCATIONS,
    TECH_CATALOG,
    WORK_MODE_WEIGHTS,
    WORK_MODES,
    detect_experience_level,
    detect_technology,
)

USER_AGENT = "Mozilla/5.0 (compatible; ITJobBoard/1.0; +https://example.local)"
REQUEST_TIMEOUT = 15

REMOTEOK_URL = "https://remoteok.com/api"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

IT_TITLE_HINTS = [
    "developer", "engineer", "programmer", "software", "data", "devops",
    "qa", "tester", "it ", "architect", "administrator", "analyst",
    "scrum", "product owner", "sysadmin", "sre", "ux", "ui designer",
    "frontend", "backend", "fullstack", "full stack",
]


def fetch_remoteok(limit: int = 100) -> list[dict]:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(REMOTEOK_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    raw_items = response.json()

    offers: list[dict] = []
    for item in raw_items:
        if "id" not in item or "position" not in item:
            continue

        tags = item.get("tags") or []
        title = item.get("position") or "Brak tytułu"
        technology = detect_technology(tags, title)

        posted_at = _parse_iso_date(item.get("date"))

        offers.append({
            "external_id": str(item["id"]),
            "source": "RemoteOK",
            "title": title,
            "company": item.get("company") or "Nieznana firma",
            "technology": technology,
            "skills": ", ".join(tags[:6]) if tags else technology,
            "location": item.get("location") or "Remote",
            "experience_level": detect_experience_level(title),
            "work_mode": "Remote",
            "salary_min": _to_float(item.get("salary_min")),
            "salary_max": _to_float(item.get("salary_max")),
            "salary_currency": "USD",
            "url": item.get("url"),
            "posted_at": posted_at,
        })

        if len(offers) >= limit:
            break

    return offers


def fetch_arbeitnow(limit: int = 100) -> list[dict]:
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(ARBEITNOW_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    offers: list[dict] = []
    for item in payload.get("data", []):
        title = item.get("title") or "Brak tytułu"
        tags = item.get("tags") or []

        if not _is_it_related(title, tags):
            continue

        technology = detect_technology(tags, title)
        is_remote = bool(item.get("remote"))
        posted_at = _parse_unix_timestamp(item.get("created_at"))

        offers.append({
            "external_id": item.get("slug") or f"arbeitnow-{abs(hash(title + item.get('company_name', '')))}",
            "source": "Arbeitnow",
            "title": title,
            "company": item.get("company_name") or "Nieznana firma",
            "technology": technology,
            "skills": ", ".join(tags[:6]) if tags else technology,
            "location": item.get("location") or ("Remote" if is_remote else "Nieznana"),
            "experience_level": detect_experience_level(title),
            "work_mode": "Remote" if is_remote else "Nieznany",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "EUR",
            "url": item.get("url"),
            "posted_at": posted_at,
        })

        if len(offers) >= limit:
            break

    return offers

def generate_offer() -> dict:
    technology = random.choice(list(TECH_CATALOG.keys()))
    info = TECH_CATALOG[technology]

    level = random.choice(EXPERIENCE_LEVELS)
    base_min, base_max = BASE_SALARY_RANGES[level]
    multiplier = info["salary_multiplier"]

    salary_min = round(base_min * multiplier * random.uniform(0.92, 1.05), -2)
    salary_max = round(base_max * multiplier * random.uniform(1.0, 1.18), -2)
    if salary_max <= salary_min:
        salary_max = salary_min + 1000

    posted_at = datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, 45), hours=random.randint(0, 23)
    )

    return {
        "external_id": f"gen-{uuid.uuid4().hex[:12]}",
        "source": "Generated",
        "title": info["title_template"].format(level=level),
        "company": _random_company_name(),
        "technology": technology,
        "skills": _random_skills(technology),
        "location": random.choice(LOCATIONS),
        "experience_level": level,
        "work_mode": random.choices(WORK_MODES, weights=WORK_MODE_WEIGHTS, k=1)[0],
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": "PLN",
        "url": None,
        "posted_at": posted_at,
    }


def _random_company_name() -> str:
    return f"{random.choice(COMPANY_PREFIXES)}{random.choice(COMPANY_SUFFIXES)} {random.choice(COMPANY_FORMS)}"


def _random_skills(technology: str) -> str:
    pool = TECH_CATALOG.get(technology, {}).get("skills", [technology])
    chosen = random.sample(pool, k=min(3, len(pool)))
    chosen += random.sample(COMMON_SKILLS, k=min(2, len(COMMON_SKILLS)))

    seen: set[str] = set()
    unique: list[str] = []
    for skill in chosen:
        if skill not in seen:
            seen.add(skill)
            unique.append(skill)
    return ", ".join(unique)


def upsert_offer(db, data: dict) -> str:
    existing = (
        db.query(JobOffer)
        .filter_by(source=data["source"], external_id=data["external_id"])
        .first()
    )
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        return "updated"

    db.add(JobOffer(**data))
    return "added"


def run_update(
    sources: list[str] | tuple[str, ...] = ("remoteok", "arbeitnow", "generated"),
    reset: bool = False,
    generated_count: int = 60,
) -> dict:

    init_db()
    db = SessionLocal()
    details: dict = {}

    try:
        if reset:
            deleted = db.query(JobOffer).delete()
            details["reset"] = {"deleted_rows": deleted}

        for source in sources:
            source = source.lower().strip()

            if source == "generated":
                offers = [generate_offer() for _ in range(generated_count)]
            elif source == "remoteok":
                try:
                    offers = fetch_remoteok()
                except Exception as exc:  # np. nie ma neta albo API nie odpowiada
                    details[source] = {"error": str(exc)}
                    continue
            elif source == "arbeitnow":
                try:
                    offers = fetch_arbeitnow()
                except Exception as exc:
                    details[source] = {"error": str(exc)}
                    continue
            else:
                details[source] = {"error": f"Nieznane źródło: {source!r}"}
                continue

            added = updated = 0
            for offer in offers:
                if upsert_offer(db, offer) == "added":
                    added += 1
                else:
                    updated += 1

            details[source] = {"fetched": len(offers), "added": added, "updated": updated}

        db.commit()
        total = db.query(JobOffer).count()
    finally:
        db.close()

    return {"total_offers": total, "details": details}

def _is_it_related(title: str, tags: list[str]) -> bool:
    text = (title or "").lower() + " " + " ".join(tags).lower()
    return any(hint in text for hint in IT_TITLE_HINTS)


def _to_float(value) -> float | None:
    try:
        if value in (None, "", 0, "0"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_unix_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aktualizacja bazy ofert pracy IT")
    parser.add_argument(
        "--sources", nargs="+", default=["remoteok", "arbeitnow", "generated"],
        choices=["remoteok", "arbeitnow", "generated"],
        help="Źródła danych do pobrania/wygenerowania (domyślnie wszystkie)",
    )
    parser.add_argument("--reset", action="store_true", help="Wyczyść bazę przed aktualizacją")
    parser.add_argument(
        "--count", type=int, default=60,
        help="Liczba syntetycznych ofert dla źródła 'generated' (domyślnie 60)",
    )
    args = parser.parse_args()

    result = run_update(sources=args.sources, reset=args.reset, generated_count=args.count)

    print(f"Baza zaktualizowana. Liczba ofert w bazie: {result['total_offers']}")
    for source, info in result["details"].items():
        print(f"  - {source}: {info}")
