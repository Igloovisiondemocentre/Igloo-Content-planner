from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from igloo_experience_builder.config import Settings
from igloo_experience_builder.ingestion.common import freshness_for, utc_now_iso
from igloo_experience_builder.knowledge.taxonomy import concepts_for_text
from igloo_experience_builder.knowledge.text_utils import slugify, tokenize
from igloo_experience_builder.models import EvidenceFragment, EvidenceStrength, SourceRecord, SourceType

logger = logging.getLogger(__name__)

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


class PdfDocsIngestor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ingest(self) -> tuple[list[SourceRecord], list[EvidenceFragment]]:
        if PdfReader is None:
            logger.warning("pypdf is not installed; internal PDF ingestion is disabled.")
            return [], []
        sources: list[SourceRecord] = []
        fragments: list[EvidenceFragment] = []
        for pdf_path in sorted(self.settings.cwd.glob("*.pdf")):
            try:
                page_sources, page_fragments = self._ingest_pdf(pdf_path)
                sources.extend(page_sources)
                fragments.extend(page_fragments)
            except Exception as exc:
                logger.warning("PDF ingestion failed for %s: %s", pdf_path, exc)
        return sources, fragments

    def _ingest_pdf(self, pdf_path: Path) -> tuple[list[SourceRecord], list[EvidenceFragment]]:
        reader = PdfReader(str(pdf_path))
        fetched_at = utc_now_iso()
        last_modified = datetime.fromtimestamp(pdf_path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()
        freshness = freshness_for(last_modified, fetched_at)
        normalized_stem = pdf_path.stem.lower()
        is_content_capability_guide = "what content can i use with igloo core engine" in normalized_stem
        first_pages: list[str] = []
        fragments: list[EvidenceFragment] = []
        source_id = f"internal-pdf-{slugify(pdf_path.stem)}"
        page_count = min(len(reader.pages), self.settings.pdf_max_pages)
        for page_number in range(page_count):
            text = (reader.pages[page_number].extract_text() or "").strip()
            if not text:
                continue
            first_pages.append(text[:800])
            fragments.append(
                EvidenceFragment(
                    fragment_id=f"{source_id}-page-{page_number + 1}",
                    source_id=source_id,
                    source_type=SourceType.INTERNAL_PDF,
                    title=pdf_path.stem,
                    text=text[:1600],
                    location=f"{pdf_path.name}#page-{page_number + 1}",
                    concept_tags=concepts_for_text(text),
                    tokens=tokenize(text),
                    evidence_strength=EvidenceStrength.MEDIUM if is_content_capability_guide else EvidenceStrength.WEAK,
                    freshness_status=freshness,
                    fetched_at=fetched_at,
                    last_modified=last_modified,
                    extraction_method="pdf-page-text",
                    truth_tier="secondary",
                    source_priority=0.75 if is_content_capability_guide else 0.45,
                )
            )
        source = SourceRecord(
            source_id=source_id,
            source_type=SourceType.INTERNAL_PDF,
            title=pdf_path.stem,
            canonical_location=str(pdf_path),
            summary=" ".join(first_pages)[:400],
            fetched_at=fetched_at,
            last_modified=last_modified,
            freshness_status=freshness,
            extraction_method="pypdf",
            truth_tier="secondary",
            source_priority=0.75 if is_content_capability_guide else 0.45,
            provenance_notes=(
                "Secondary internal evidence that acts as a baseline product-knowledge anchor for common known-working content classes; it does not override runtime or workflow truth."
                if is_content_capability_guide
                else "Secondary internal evidence for commercial context; not runtime truth."
            ),
        )
        return [source], fragments
