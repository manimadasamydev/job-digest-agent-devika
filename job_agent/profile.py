from __future__ import annotations

import re

NAME = "Manikandan Madasamy"
EMAIL = "manimadasamy.dev@gmail.com"
CITIES = ("Chennai", "Bengaluru")
CITY_ALIASES = {
    "chennai": "Chennai",
    "madras": "Chennai",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "blr": "Bengaluru",
}

RESUME_SUMMARY = """
Manikandan Madasamy, Java Developer targeting roles in Chennai and Bengaluru.
Target titles: Java Developer, Java Backend Developer, Java Full Stack Developer.
Stack focus: Java, Spring, Spring Boot, REST APIs, Hibernate/JPA, SQL, backend services;
full stack Java when needed (basic frontend OK). Open to Chennai and Bengaluru.
Target band: mid-level Java roles. Not intern/campus. Not 8+ year staff/principal-only.
Not pure frontend-only, mobile-only, Python/AI-only, or .NET-only.
""".strip()

BOARD_QUERIES = (
    "Java Developer",
    "Java Backend Developer",
    "Java Full Stack Developer",
    "Spring Boot Developer",
    "Java Microservices",
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
    "full stack",
    "fullstack",
    "full-stack",
    "rest api",
    "j2ee",
    "jakarta",
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
    "ui developer",
    "ux designer",
    "qa intern",
)

SENIOR_ONLY = re.compile(
    r"\b(10\+|12\+|15\+|8\+\s*years|principal engineer|staff engineer|distinguished engineer)\b",
    re.I,
)
MID_BAND = re.compile(r"\b([2-5])\s*[-–to]{1,3}\s*([5-7])\s*years\b", re.I)


def _blob(*parts: str) -> str:
    return " ".join(p or "" for p in parts).lower()


def location_ok(location: str, extra: str = "") -> bool:
    text = _blob(location, extra)
    if any(alias in text for alias in CITY_ALIASES):
        return True
    if "india" in text and any(w in text for w in ("remote", "work from home", "wfh", "hybrid")):
        return True
    return False


def title_prefilter(title: str, description: str = "") -> bool:
    blob = _blob(title, description[:1200])
    if any(bad in blob for bad in REJECT_TITLE) and not any(s in blob for s in JAVA_SIGNAL):
        return False
    if "intern" in blob or "internship" in blob or "campus hire" in blob:
        return False
    if SENIOR_ONLY.search(blob) and not MID_BAND.search(blob):
        return False
    if not any(k in blob for k in TITLE_KEEP):
        return False
    title_l = (title or "").lower()
    # Keep backend/full-stack titles only when Java stack is present
    if any(k in title_l for k in ("backend", "full stack", "fullstack", "full-stack")) and not any(
        s in blob for s in JAVA_SIGNAL
    ):
        return False
    return True


def city_label(location: str) -> str:
    text = (location or "").lower()
    for alias, label in CITY_ALIASES.items():
        if alias in text:
            return label
    return location or ""
