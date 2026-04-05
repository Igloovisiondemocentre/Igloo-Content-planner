from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser

from igloo_experience_builder.models import FreshnessStatus


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def freshness_for(last_modified: str | None, fetched_at: str) -> FreshnessStatus:
    reference = parse_datetime(last_modified)
    if reference is None:
        return FreshnessStatus.UNKNOWN
    age_days = (datetime.now(tz=timezone.utc) - reference.astimezone(timezone.utc)).days
    if age_days <= 180:
        return FreshnessStatus.FRESH
    if age_days <= 365:
        return FreshnessStatus.AGING
    return FreshnessStatus.STALE


@dataclass(slots=True)
class HttpDocument:
    url: str
    text: str
    headers: dict[str, str]


def fetch_text(url: str, timeout_seconds: int) -> HttpDocument:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "igloo-experience-builder-pilot/0.1 (+local-first phase1)",
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain;q=0.8,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="ignore")
        headers = {key.lower(): value for key, value in response.headers.items()}
        return HttpDocument(url=url, text=body, headers=headers)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ignored_tags = {"script", "style", "svg", "path", "noscript", "iframe"}
        self.ignore_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.ignored_tags:
            self.ignore_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignored_tags and self.ignore_depth > 0:
            self.ignore_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.ignore_depth:
            return
        chunk = re.sub(r"\s+", " ", data).strip()
        if chunk:
            self.parts.append(chunk)


TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
META_RE_TEMPLATE = r'<meta[^>]+name="{name}"[^>]+content="(.*?)"'


def extract_title(html: str) -> str:
    match = TITLE_RE.search(html)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else "Untitled"


def extract_meta_content(html: str, name: str) -> str | None:
    pattern = re.compile(META_RE_TEMPLATE.format(name=re.escape(name)), re.IGNORECASE | re.DOTALL)
    match = pattern.search(html)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def extract_visible_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    return "\n".join(parser.parts)


def extract_links(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for href in re.findall(r'href="([^"]+)"', html, re.IGNORECASE):
        urls.append(urllib.parse.urljoin(base_url, href))
    return urls


def split_into_chunks(text: str, chunk_size: int = 700, max_chunks: int = 6) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.splitlines() if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current} {paragraph}"
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
        if len(chunks) >= max_chunks:
            break
    if current and len(chunks) < max_chunks:
        chunks.append(current)
    return chunks


def parse_sitemap_locations(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [element.text or "" for element in root.findall(".//sm:loc", namespace)]
    return [item.strip() for item in locations if item and item.strip()]
