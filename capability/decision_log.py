from __future__ import annotations

import json
from pathlib import Path

from igloo_experience_builder.models import CapabilityAssessment


class DecisionLogger:
    def __init__(self, reports_dir: Path, decisions_dir: Path) -> None:
        self.reports_dir = reports_dir
        self.decisions_dir = decisions_dir

    def persist(self, assessment: CapabilityAssessment, markdown_report: str) -> tuple[Path, Path]:
        stamp = assessment.created_at.replace(":", "-")
        report_path = self._unique_path(self.reports_dir, f"report-{stamp}", ".md")
        decision_path = self._unique_path(self.decisions_dir, f"decision-{stamp}", ".json")
        report_path.write_text(markdown_report, encoding="utf-8")
        decision_path.write_text(json.dumps(assessment.to_dict(), indent=2), encoding="utf-8")
        (self.reports_dir / "last_report.md").write_text(markdown_report, encoding="utf-8")
        (self.decisions_dir / "last_assessment.json").write_text(
            json.dumps(assessment.to_dict(), indent=2),
            encoding="utf-8",
        )
        return report_path, decision_path

    def _unique_path(self, directory: Path, stem: str, suffix: str) -> Path:
        candidate = directory / f"{stem}{suffix}"
        if not candidate.exists():
            return candidate
        counter = 1
        while True:
            candidate = directory / f"{stem}-{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1
