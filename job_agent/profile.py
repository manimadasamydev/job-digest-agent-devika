from __future__ import annotations

import re

NAME = "Devika Madasamy"
EMAIL = "devika120898@gmail.com"
# Used as board search locations (remote / India-wide).
CITIES = ("India", "Remote")
CITY_ALIASES = {
    "chennai": "Chennai",
    "madras": "Chennai",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "blr": "Bengaluru",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "mumbai": "Mumbai",
    "delhi": "Delhi",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurugram",
    "noida": "Noida",
    "india": "India",
}

REMOTE_WORDS = (
    "remote",
    "work from home",
    "work-from-home",
    "wfh",
    "w.f.h",
    "anywhere in india",
    "pan india",
    "pan-india",
    "panindia",
    "india remote",
    "remote india",
    "fully remote",
    "100% remote",
)

RESUME_SUMMARY = """
Devika Madasamy, Java Backend Developer with 6+ years experience.
Target titles: Java Backend Developer, Java Developer, Spring Boot Developer, Microservices Developer.
Stack focus: Java, Spring, Spring Boot, REST APIs, Hibernate/JPA, SQL, microservices, backend services.
Location: Remote only, anywhere in India (WFH / pan-India remote). Not office-only / onsite-only.
Experience band: 5-10 years mid-senior. Not intern/fresher/junior 0-3. Not principal/staff 12+ only.
Not pure frontend-only, mobile-only, Python/AI-only, .NET-only, or full-stack-frontend roles.
""".strip()

BOARD_QUERIES = (
    "Java Backend Developer",
    "Java Developer",
    "Spring Boot Developer",
    "Java Microservices",
    "Remote Java Backend",
)

TITLE_KEEP = (
    "java",
    "spring",
    "spring boot",
    "springboot",
    "hibernate",
    "jpa",
    "microservices",
    "backend",
    "rest api",
    "j2ee",
    "jakarta",
    "kafka",
    "api developer",
)

JAVA_SIGNAL = (
    "java",
    "spring",
    "spring boot",
    "springboot",
    "hibernate",
    "jpa",
    "j2ee",
    "jakarta ee",
    "microservices",
)

REJECT_TITLE = (
    "intern",
    "internship",
    "campus",
    "graduate trainee",
    "fresher",
    "junior developer",
    "android",
    "ios developer",
    "react native",
    "sales executive",
    "business development",
    "sap consultant",
    ".net developer",
    "python developer",
    "ai engineer",
    "genai",
    "data scientist",
    "frontend developer",
    "front end developer",
    "front-end developer",
    "ui developer",
    "ux designer",
    "react developer",
    "angular developer",
    "qa intern",
    "full stack developer",
    "fullstack developer",
    "full-stack developer",
)

# Reject very senior leadership / 12+ only postings.
TOO_SENIOR = re.compile(
    r"\b(12\+|15\+|principal engineer|staff engineer|distinguished engineer|"
    r"engineering manager|director of engineering|vp engineering)\b",
    re.I,
)
# Reject junior / early-career only postings.
TOO_JUNIOR = re.compile(
    r"\b(fresher|0\s*[-–to]{1,3}\s*[123]\s*years|1\s*[-–to]{1,3}\s*[23]\s*years|"
    r"2\s*[-–to]{1,3}\s*4\s*years|junior\s+java|entry\s*level)\b",
    re.I,
)
# Prefer mid-senior bands around 5-10 / 6+.
EXPERIENCE_OK = re.compile(
    r"\b([5-9]|10)\s*[-–to+]{0,3}\s*([6-9]|1[0-2])?\s*years?\b|\b6\+\s*years?\b|\b5\+\s*years?\b",
    re.I,
)


def _blob(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower()


def location_ok(location: str, extra: str = "") -> bool:
    """Remote-only, India-wide."""
    text = _blob(location, extra)
    if not text.strip():
        return False
    remote = any(w in text for w in REMOTE_WORDS)
    if not remote:
        return False
    # Prefer India / Indian cities / pan-India; allow generic "remote" if not clearly foreign-only.
    indiaish = (
        "india" in text
        or "pan india" in text
        or "pan-india" in text
        or any(alias in text for alias in CITY_ALIASES)
    )
    foreign_only = any(
        w in text
        for w in (
            "united states",
            " usa",
            "u.s.",
            "uk only",
            "united kingdom",
            "europe only",
            "canada only",
            "australia only",
        )
    )
    if foreign_only and "india" not in text:
        return False
    return indiaish or remote


def title_prefilter(title: str, description: str = "") -> bool:
    blob = _blob(title, description[:1200])
    if any(bad in blob for bad in REJECT_TITLE) and not any(s in blob for s in JAVA_SIGNAL):
        return False
    # Hard-reject frontend / full-stack title noise even if "java" appears in description.
    title_l = (title or "").lower()
    if any(
        bad in title_l
        for bad in (
            "frontend",
            "front-end",
            "front end",
            "full stack",
            "fullstack",
            "full-stack",
            "react developer",
            "angular developer",
            "ui developer",
        )
    ):
        return False
    if "intern" in blob or "internship" in blob or "campus hire" in blob or "fresher" in blob:
        return False
    if TOO_SENIOR.search(blob):
        return False
    if TOO_JUNIOR.search(blob) and not EXPERIENCE_OK.search(blob):
        return False
    if not any(k in blob for k in TITLE_KEEP):
        return False
    if any(k in title_l for k in ("backend", "api developer")) and not any(
        s in blob for s in JAVA_SIGNAL
    ):
        return False
    return True


def city_label(location: str) -> str:
    text = (location or "").lower()
    if any(w in text for w in REMOTE_WORDS):
        return "Remote India"
    for alias, label in CITY_ALIASES.items():
        if alias in text:
            return label
    return location or ""
