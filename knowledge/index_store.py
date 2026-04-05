from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from igloo_experience_builder.models import EvidenceIndex


class EvidenceIndexStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def is_stale(self, ttl_hours: int) -> bool:
        if not self.exists():
            return True
        modified = datetime.fromtimestamp(self.path.stat().st_mtime, tz=timezone.utc)
        return datetime.now(tz=timezone.utc) - modified > timedelta(hours=ttl_hours)

    def load(self) -> EvidenceIndex | None:
        if not self.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return EvidenceIndex.from_dict(payload)

    def save(self, index: EvidenceIndex) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(index.to_dict(), indent=2), encoding="utf-8")
