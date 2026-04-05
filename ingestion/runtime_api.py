from __future__ import annotations

import json
import logging
import urllib.parse

from igloo_experience_builder.config import Settings
from igloo_experience_builder.ingestion.common import (
    extract_links,
    extract_meta_content,
    extract_title,
    extract_visible_text,
    fetch_text,
    freshness_for,
    split_into_chunks,
    utc_now_iso,
)
from igloo_experience_builder.knowledge.taxonomy import concepts_for_text
from igloo_experience_builder.knowledge.text_utils import slugify, tokenize
from igloo_experience_builder.models import EvidenceFragment, EvidenceStrength, SourceRecord, SourceType

logger = logging.getLogger(__name__)


class RuntimeApiIngestor:
    DEFAULT_HINTS = ("", "layer-list/", "layer/", "session/", "content/", "messages/")

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ingest(self) -> tuple[list[SourceRecord], list[EvidenceFragment]]:
        urls = self._discover_urls()
        sources: list[SourceRecord] = []
        fragments: list[EvidenceFragment] = []
        for url in urls[: self.settings.runtime_api_max_pages]:
            try:
                page_sources, page_fragments = self._ingest_page(url)
                sources.extend(page_sources)
                fragments.extend(page_fragments)
            except Exception as exc:
                logger.warning("Runtime API ingestion failed for %s: %s", url, exc)
        return sources, fragments

    def discover_sections(self) -> list[str]:
        return self._discover_urls()[: self.settings.runtime_api_max_pages]

    def _discover_urls(self) -> list[str]:
        manifest_urls: list[str] = []
        if self.settings.manifest_path.exists():
            payload = json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))
            manifest_urls = list(payload.get("runtime_api", {}).get("seed_urls", []))
        root_url = self.settings.runtime_api_root_url
        discovered = [root_url]
        try:
            root = fetch_text(root_url, self.settings.request_timeout_seconds)
            for link in extract_links(root.text, root_url):
                if link.startswith(root_url):
                    discovered.append(link)
        except Exception as exc:
            logger.warning("Could not discover runtime API links from %s: %s", root_url, exc)
        for hint in self.DEFAULT_HINTS:
            discovered.append(root_url + hint)
        discovered.extend(manifest_urls)
        unique: list[str] = []
        seen: set[str] = set()
        for url in discovered:
            clean = url.split("#", 1)[0]
            parsed = urllib.parse.urlparse(clean)
            suffix = parsed.path.rsplit("/", 1)[-1]
            has_file_extension = "." in suffix and not clean.endswith("/")
            if "/assets/" in parsed.path or has_file_extension:
                continue
            if clean not in seen and clean.startswith(root_url):
                unique.append(clean)
                seen.add(clean)
        return unique

    def _ingest_page(self, url: str) -> tuple[list[SourceRecord], list[EvidenceFragment]]:
        document = fetch_text(url, self.settings.request_timeout_seconds)
        fetched_at = utc_now_iso()
        last_modified = document.headers.get("last-modified")
        freshness = freshness_for(last_modified, fetched_at)
        title = extract_title(document.text)
        description = extract_meta_content(document.text, "description") or ""
        visible_text = extract_visible_text(document.text)
        source_id = f"runtime-api-{slugify(url.replace(self.settings.runtime_api_root_url, 'root-'))}"
        source = SourceRecord(
            source_id=source_id,
            source_type=SourceType.RUNTIME_API,
            title=title,
            canonical_location=url,
            summary=description or visible_text[:300],
            fetched_at=fetched_at,
            last_modified=last_modified,
            freshness_status=freshness,
            extraction_method="html+metadata",
            truth_tier="runtime",
            source_priority=1.0,
            provenance_notes="Primary runtime API source of truth for the pilot.",
        )
        fragments: list[EvidenceFragment] = [
            EvidenceFragment(
                fragment_id=f"{source_id}-summary",
                source_id=source_id,
                source_type=SourceType.RUNTIME_API,
                title=title,
                text=description or visible_text[:500],
                location=url,
                concept_tags=concepts_for_text(f"{title} {description} {visible_text[:300]}"),
                tokens=tokenize(f"{title} {description} {visible_text[:300]}"),
                evidence_strength=EvidenceStrength.HARD,
                freshness_status=freshness,
                fetched_at=fetched_at,
                last_modified=last_modified,
                extraction_method="meta-description",
                truth_tier="runtime",
                source_priority=1.0,
            )
        ]
        for index, chunk in enumerate(split_into_chunks(visible_text, chunk_size=900, max_chunks=4), start=1):
            fragments.append(
                EvidenceFragment(
                    fragment_id=f"{source_id}-chunk-{index}",
                    source_id=source_id,
                    source_type=SourceType.RUNTIME_API,
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
                    truth_tier="runtime",
                    source_priority=0.98,
                )
            )
        return [source], fragments
