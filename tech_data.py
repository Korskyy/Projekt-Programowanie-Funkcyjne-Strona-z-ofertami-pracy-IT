"""
dane słownikowe
TECH_CATALOG:
    - keywords: rozpoznanie technologii przez tytul lub tagi
    - skills: lista umiejetnosci
    - title_template: tytul stanowiska wygenerowany
    - salary_multiplier: mnoznik widelek do testow

Kolejność kategorii w słowniku ma znaczenie, najpierw najwazniejsze potem ogolne
"""

from __future__ import annotations

TECH_CATALOG: dict[str, dict] = {
    "TypeScript": {
        "keywords": ["typescript", "angular", "nestjs", "next.js", "nuxt"],
        "skills": ["Angular", "NestJS", "Next.js", "RxJS", "GraphQL", "Jest"],
        "title_template": "{level} TypeScript Developer",
        "salary_multiplier": 1.05,
    },
    "JavaScript": {
        "keywords": ["javascript", "node.js", "nodejs", "react", "vue", "frontend", "front-end"],
        "skills": ["React", "Vue", "Node.js", "Webpack", "Redux", "Jest"],
        "title_template": "{level} JavaScript Developer",
        "salary_multiplier": 1.0,
    },
    "Python": {
        "keywords": ["python", "django", "flask", "fastapi", "pandas", "pyspark"],
        "skills": ["Django", "FastAPI", "Flask", "PostgreSQL", "Pandas", "Celery"],
        "title_template": "{level} Python Developer",
        "salary_multiplier": 1.05,
    },
    "Kotlin": {
        "keywords": ["kotlin"],
        "skills": ["Kotlin Coroutines", "Spring Boot", "Ktor", "Gradle", "PostgreSQL"],
        "title_template": "{level} Kotlin Developer",
        "salary_multiplier": 1.05,
    },
    "Java": {
        "keywords": ["java", "spring", "hibernate", "j2ee"],
        "skills": ["Spring Boot", "Hibernate", "Maven", "PostgreSQL", "Kafka"],
        "title_template": "{level} Java Developer",
        "salary_multiplier": 1.05,
    },
    "C#": {
        "keywords": ["c#", "csharp", ".net", "dotnet", "asp.net"],
        "skills": [".NET Core", "ASP.NET", "Entity Framework", "Azure", "MSSQL"],
        "title_template": "{level} C#/.NET Developer",
        "salary_multiplier": 1.0,
    },
    "Go": {
        "keywords": ["golang", "go-lang", "\"go\""],
        "skills": ["Goroutines", "gRPC", "PostgreSQL", "Docker", "Kubernetes"],
        "title_template": "{level} Go Developer",
        "salary_multiplier": 1.1,
    },
    "PHP": {
        "keywords": ["php", "laravel", "symfony", "wordpress"],
        "skills": ["Laravel", "Symfony", "MySQL", "Composer", "REST API"],
        "title_template": "{level} PHP Developer",
        "salary_multiplier": 0.9,
    },
    "Ruby": {
        "keywords": ["ruby", "rails"],
        "skills": ["Ruby on Rails", "RSpec", "PostgreSQL", "Sidekiq", "Redis"],
        "title_template": "{level} Ruby on Rails Developer",
        "salary_multiplier": 1.0,
    },
    "Swift": {
        "keywords": ["swift", "ios", "xcode"],
        "skills": ["SwiftUI", "UIKit", "Xcode", "Core Data", "Combine"],
        "title_template": "{level} iOS Developer",
        "salary_multiplier": 1.05,
    },
    "Mobile": {
        "keywords": ["android", "flutter", "react native", "mobile"],
        "skills": ["Flutter", "React Native", "Android SDK", "Kotlin", "Firebase"],
        "title_template": "{level} Mobile Developer",
        "salary_multiplier": 1.0,
    },
    "DevOps/Cloud": {
        "keywords": ["devops", "kubernetes", "terraform", "sre", "cloud", "aws", "azure", "gcp"],
        "skills": ["Kubernetes", "Terraform", "AWS", "Azure", "CI/CD", "Ansible"],
        "title_template": "{level} DevOps Engineer",
        "salary_multiplier": 1.15,
    },
    "Data/ML": {
        "keywords": ["machine learning", "data scientist", "data engineer", "data science", "artificial intelligence", "ml engineer", "ai"],
        "skills": ["Python", "SQL", "TensorFlow", "PyTorch", "Spark", "Airflow"],
        "title_template": "{level} Data/ML Engineer",
        "salary_multiplier": 1.2,
    },
    "QA/Testing": {
        "keywords": ["qa", "quality assurance", "tester", "test automation", "selenium", "cypress"],
        "skills": ["Selenium", "Cypress", "Postman", "TestRail", "Playwright"],
        "title_template": "{level} QA Engineer",
        "salary_multiplier": 0.9,
    },
}

FALLBACK_TECH = "Inne"

COMMON_SKILLS = [
    "Git", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "CI/CD",
    "Linux", "SQL", "REST API", "GraphQL", "Agile/Scrum", "Microservices",
]

EXPERIENCE_LEVELS = ["Junior", "Mid", "Senior", "Lead"]

EXPERIENCE_KEYWORDS = {
    "intern": "Junior",
    "trainee": "Junior",
    "junior": "Junior",
    "jr": "Junior",
    "mid": "Mid",
    "regular": "Mid",
    "senior": "Senior",
    "sr.": "Senior",
    "sr ": "Senior",
    "lead": "Lead",
    "principal": "Lead",
    "staff": "Lead",
    "head of": "Lead",
}

BASE_SALARY_RANGES = {
    "Junior": (5500, 9000),
    "Mid": (9500, 16000),
    "Senior": (16500, 25000),
    "Lead": (22000, 32000),
}

WORK_MODES = ["Remote", "Hybrid", "Office"]
WORK_MODE_WEIGHTS = [0.45, 0.4, 0.15]

LOCATIONS = [
    "Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań",
    "Łódź", "Katowice", "Szczecin", "Remote",
]

# Przeliczanie walut
EXCHANGE_RATES_TO_PLN = {
    "PLN": 1.0,
    "USD": 4.0,
    "EUR": 4.3,
    "GBP": 5.0,
}

# losowe nazwy firm do generowania
COMPANY_PREFIXES = [
    "Nova", "Quantum", "Bright", "Silver", "Net", "Code", "Data", "Cloud",
    "Pixel", "Logic", "Vertex", "Prime", "Northbyte", "Bluestack", "Redshift",
]
COMPANY_SUFFIXES = ["Soft", "Tech", "Labs", "Works", "Systems", "Solutions", "Group", "Software"]
COMPANY_FORMS = ["Sp. z o.o.", "S.A.", "Sp. j."]

#zgaduje jaka to technologia przez tagi i tytul
def detect_technology(tags: list[str], title: str = "") -> str:
    haystack = " ".join(tags).lower() + " " + (title or "").lower()
    for tech, info in TECH_CATALOG.items():
        for keyword in info["keywords"]:
            if keyword.strip('"') in haystack:
                return tech
    return FALLBACK_TECH

#zgaduje poziom doswiadczenia
def detect_experience_level(title: str) -> str:
    lowered = (title or "").lower()
    for keyword, level in EXPERIENCE_KEYWORDS.items():
        if keyword in lowered:
            return level
    return "Nieznany"
    lowered = (title or "").lower()
    for keyword, level in EXPERIENCE_KEYWORDS.items():
        if keyword in lowered:
            return level
    return "Nieznany"
