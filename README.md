(filtrowanie ofert najlepiej działa na generowanych ofertach pracy)
# IT Job Board
Aplikacja web do przeszukiwania ofert pracy w IT i analizy rynku

Backend: FastAPI + SQLAlchemy + SQLite.
Frontend: plik HTML (Tailwind CSS + Chart.js z CDN), serwowany przez
backend pod /.

## 1. Wymagania

- Python 3.10+
- dostęp do internetu do pobierania ofert z RemoteOK / Arbeitnow 

## 2. Instalacja
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## 3. Pierwsze zasilenie bazy danymi

Baza it_jobs.db, SQLite jest tworzona automatycznie przy pierwszym
uruchomieniu. Żeby coś w niej było, trzeba ją zasilić skryptem update_db.py:

# pobiera oferty z RemoteOK, Arbeitnow oraz dogenerowuje 60 syntetycznych ofert
python3 update_db.py
# tylko generator syntetyczny, np. 100 ofert, z czyszczeniem bazy
python3 update_db.py --sources generated --count 100 --reset
# tylko realne API, bez generatora
python3 update_db.py --sources remoteok arbeitnow
Flagi:
- --sources - lista źródeł: remoteok, arbeitnow, generated
- --reset - czyści bazę przed aktualizacją
- --count N- liczba ofert generowanych syntetycznie (domyślnie 60)

## 4. Uruchomienie serwera
uvicorn main:app --reload
Aplikacja pod adresem: http://127.0.0.1:8000
- / - dashboard (wyszukiwanie, filtry, statystyki, panel admina)
- /docs - automatyczna dokumentacja API (Swagger UI)

## 5. Aktualizacja bazy z panelu administratora

W dashboardzie, w sekcji "Panel administratora - aktualizacja bazy ofert",
można odświeżyć dane bez terminala. Wymaga klucza administratora
podanego w nagłówku X-Admin-Key.

Domyślny klucz: admin123

Aby ustawić własny klucz, przed uruchomieniem serwera:
export ADMIN_KEY="moj-tajny-klucz"      
Windows: set ADMIN_KEY=moj-tajny-klucz
uvicorn main:app --reload


## 6. Struktura 

it-job-board/
    main.py          # API
    db.py             # model SQLAlchemy (JobOffer) + konfiguracja SQLite
    schemas.py        # Pydantic
    update_db.py      # pobieranie ofert i generator
    tech_data.py      # baza wiedzy
    requirements.txt
    static/
        index.html    # front
    it_jobs.db        # baza SQLite
