from __future__ import annotations

import json
import logging

from igloo_experience_builder.config import Settings
from igloo_experience_builder.ingestion.common import (
    extract_meta_content,
    extract_title,
    extract_visible_text,
    fetch_text,
    freshness_for,
    parse_sitemap_locations,
    split_into_chunks,
    utc_now_iso,
)
from igloo_experience_builder.knowledge.taxonomy import concepts_for_text
from igloo_experience_builder.knowledge.text_utils import slugify, tokenize
from igloo_experience_builder.models import EvidenceFragment, EvidenceStrength, SourceRecord, SourceType

logger = logging.getLogger(__name__)


class PlatformDocsIngestor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.priority_keywords = self._load_priority_keywords()
        self.seed_urls = self._load_seed_urls()

    def ingest(self) -> tuple[list[SourceRecord], list[EvidenceFragment]]:
        urls = self._discover_urls()
        sources: list[SourceRecord] = []
        fragments: list[EvidenceFragment] = []
        for url in urls:
            try:
                page_sources, page_fragments = self._ingest_page(url)
                sources.extend(page_sources)
                fragments.extend(page_fragments)
            except Exception as exc:
                logger.warning("Platform doc ingestion failed for %s: %s", url, exc)
        return sources, fragments

    def _load_priority_keywords(self) -> list[str]:
        if not self.settings.manifest_path.exists():
            return ["session", "layer", "webview", "pdf", "video", "content", "canvas", "desktop"]
        payload = json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))
        return list(
            payload.get(
                "platform_docs",
                {},
            ).get("priority_keywords", ["session", "layer", "webview", "pdf", "video", "content", "canvas", "desktop"])
        )

    def _load_seed_urls(self) -> list[str]:
        if not self.settings.manifest_path.exists():
            return []
        payload = json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))
        return list(payload.get("platform_docs", {}).get("seed_urls", []))

    def _discover_urls(self) -> list[str]:
        sitemap_urls = parse_sitemap_locations(fetch_text(self.settings.platform_docs_sitemap_url, self.settings.request_timeout_seconds).text)
        nested_urls: list[str] = []
        for sitemap_url in sitemap_urls:
            if sitemap_url.endswith(".xml"):
                nested_urls.extend(parse_sitemap_locations(fetch_text(sitemap_url, self.settings.request_timeout_seconds).text))
        candidates = [
            url
            for url in nested_urls
            if "/documentation/current" in url and url.startswith(self.settings.platform_docs_root_url.rsplit("/", 1)[0])
        ]
        candidates.extend(self.seed_urls)
        if self.settings.platform_docs_root_url not in candidates:
            candidates.insert(0, self.settings.platform_docs_root_url)
        ranked = sorted(set(candidates), key=self._priority_score, reverse=True)
        return ranked[: self.settings.platform_docs_max_pages]

    def _priority_score(self, url: str) -> int:
        score = 0
        lowered = url.lower()
        if lowered == self.settings.platform_docs_root_url.lower():
            score += 50
        for keyword in self.priority_keywords:
            if keyword in lowered:
                score += 10
        if "current" in lowered:
            score += 2
        return score

    def _ingest_page(self, url: str) -> tuple[list[SourceRecord], list[EvidenceFragment]]:
        document = fetch_text(url, self.settings.request_timeout_seconds)
        fetched_at = utc_now_iso()
        last_modified = extract_meta_content(document.text, "page-last-modified") or document.headers.get("last-modified")
        freshness = freshness_for(last_modified, fetched_at)
        title = extract_title(document.text)
        description = extract_meta_content(document.text, "description") or ""
        visible_text = extract_visible_text(document.text)
        source_id = f"platform-doc-{slugify(url.replace(self.settings.platform_docs_root_url.rsplit('/', 1)[0], 'docs'))}"
        source = SourceRecord(
            source_id=source_id,
            source_type=SourceType.PLATFORM_DOC,
            title=title,
            canonical_location=url,
            summary=description or visible_text[:300],
            fetched_at=fetched_at,
            last_modified=last_modified,
            freshness_status=freshness,
            extraction_method="html+metadata",
            truth_tier="workflow",
            source_priority=0.9,
            provenance_notes="Primary platform and workflow source of truth for the pilot.",
        )
        fragments: list[EvidenceFragment] = [
            EvidenceFragment(
                fragment_id=f"{source_id}-summary",
                source_id=source_id,
                source_type=SourceType.PLATFORM_DOC,
                title=title,
                text=description or visible_text[:500],
                location=url,
                concept_tags=concepts_for_text(f"{title} {description} {visible_text[:400]}"),
                tokens=tokenize(f"{title} {description} {visible_text[:400]}"),
                evidence_strength=EvidenceStrength.HARD,
                freshness_status=freshness,
                fetched_at=fetched_at,
                last_modified=last_modified,
                extraction_method="meta-description",
                truth_tier="workflow",
                source_priority=0.9,
            )
        ]
        for index, chunk in enumerate(split_into_chunks(visible_text, chunk_size=900, max_chunks=5), start=1):
            fragments.append(
                EvidenceFragment(
                    fragment_id=f"{source_id}-chunk-{index}",
                    source_id=source_id,
                    source_type=SourceType.PLATFORM_DOC,
                    title=title,
                    text=chunk,
                    location=url,
                    concept_tags=concepts_for_text(f"{title} {chunk}"),
                    tokens=tokenize(f"{title} {chunk}"),
                    evidence_strength=EvidenceStrength.HARD,
                    freshness_status=freshness,
                    fetched_at=fetched_at,
                    last_modified=last_modified,
                    extraction_method="html-chunk",
                    truth_tier="workflow",
                    source_priority=0.88,
                )
            )
        return [source], fragments
