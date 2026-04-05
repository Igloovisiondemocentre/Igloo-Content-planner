from __future__ import annotations

import re
import unicodedata
from html import unescape

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "for",
    "from",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "use",
    "we",
    "what",
    "with",
}

TOKEN_RE = re.compile(r"[a-z0-9]+")
CAPITALIZED_ARTIFACT_RE = re.compile(r"\b([A-Z])\s+([A-Za-z]{2,})\b")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\s*\n+\s*")
GENERIC_NAVIGATION_PHRASES = (
    "skip to content",
    "main navigation",
    "return to top",
    "sidebar navigation",
    "appearance menu",
    "on this page",
    "table of contents",
    "index layer list api",
    "canvas ui - the canvas user interface",
    "desktop ui -",
)


def normalize_whitespace(text: str) -> str:
    cleaned = (
        unescape(text or "")
        .replace("\u200b", " ")
        .replace("\ufeff", " ")
        .replace("\u2060", " ")
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def collapse_capitalized_artifacts(text: str) -> str:
    normalized = normalize_whitespace(text)
    return CAPITALIZED_ARTIFACT_RE.sub(r"\1\2", normalized)


def tokenize(text: str) -> list[str]:
    normalized = collapse_capitalized_artifacts(text).lower()
    return [token for token in TOKEN_RE.findall(normalized) if token not in STOPWORDS and len(token) > 1]


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return normalized or "item"


def navigation_penalty(text: str) -> float:
    normalized = collapse_capitalized_artifacts(text).lower()
    penalty = 0.0
    for phrase in GENERIC_NAVIGATION_PHRASES:
        if phrase in normalized:
            penalty += 1.0
    if normalized.count("window") >= 4:
        penalty += 0.5
    if normalized.count("canvas ui -") >= 2:
        penalty += 2.0
    if normalized.count("desktop ui -") >= 2:
        penalty += 2.0
    return penalty


def select_excerpt(text: str, query_terms: list[str], max_chars: int = 240) -> str:
    normalized = collapse_capitalized_artifacts(text)
    parts = [part.strip() for part in SENTENCE_SPLIT_RE.split(normalized) if part.strip()]
    if not parts:
        return normalized[:max_chars].replace("\n", " ")
    scored: list[tuple[float, str]] = []
    lowered_terms = [term.lower() for term in query_terms if term]
    for part in parts:
        lowered = part.lower()
        term_hits = sum(1 for term in lowered_terms if term in lowered)
        token_hits = len(set(tokenize(part)) & set(lowered_terms))
        score = term_hits * 2.0 + token_hits * 1.0 - navigation_penalty(part)
        if ("canvas ui -" in lowered or "desktop ui -" in lowered) and len(tokenize(part)) >= 16:
            score -= 2.0
        if len(part) < 20:
            score -= 0.5
        scored.append((score, part))
    scored.sort(key=lambda item: item[0], reverse=True)
    excerpt = scored[0][1]
    return excerpt[:max_chars].replace("\n", " ")
