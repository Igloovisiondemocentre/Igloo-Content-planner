from __future__ import annotations

import logging

from igloo_experience_builder.config import Settings
from igloo_experience_builder.ingestion.common import utc_now_iso
from igloo_experience_builder.ingestion.pdf_docs import PdfDocsIngestor
from igloo_experience_builder.ingestion.platform_docs import PlatformDocsIngestor
from igloo_experience_builder.ingestion.runtime_api import RuntimeApiIngestor
from igloo_experience_builder.knowledge.index_store import EvidenceIndexStore
from igloo_experience_builder.models import EvidenceIndex

logger = logging.getLogger(__name__)


class SourceManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = EvidenceIndexStore(settings.index_path)
        self.runtime_api = RuntimeApiIngestor(settings)
        self.platform_docs = PlatformDocsIngestor(settings)
        self.pdf_docs = PdfDocsIngestor(settings)

    def ensure_index(self, refresh: bool = False) -> EvidenceIndex:
        if not refresh and self.settings.manifest_path.exists() and self.store.exists():
            if self.settings.manifest_path.stat().st_mtime > self.settings.index_path.stat().st_mtime:
                refresh = True
        if not refresh and not self.store.is_stale(self.settings.index_ttl_hours):
            index = self.store.load()
            if index is not None:
                return index
        return self.build_index()

    def build_index(self) -> EvidenceIndex:
        sources = []
        fragments = []
        warnings: list[str] = []
        for label, ingestor in (
            ("runtime_api", self.runtime_api),
            ("platform_docs", self.platform_docs),
            ("pdf_docs", self.pdf_docs),
        ):
            try:
                new_sources, new_fragments = ingestor.ingest()
                sources.extend(new_sources)
                fragments.extend(new_fragments)
            except Exception as exc:
                warning = f"{label} ingestion failed: {exc}"
                logger.warning(warning)
                warnings.append(warning)
        index = EvidenceIndex(
            built_at=utc_now_iso(),
            sources=sources,
            fragments=fragments,
            warnings=warnings,
        )
        self.store.save(index)
        return index
