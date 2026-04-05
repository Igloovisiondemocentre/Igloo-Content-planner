from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from igloo_experience_builder.capability.classifier import CapabilityClassifier
from igloo_experience_builder.models import OperationalFlag, Verdict


DEFAULT_EVAL_FILES = (
    Path("tests/evals/core_eval_seed.json"),
    Path("tests/evals/hero_eval.json"),
)


class BatchEvaluationRunner:
    def __init__(self, classifier: CapabilityClassifier, evaluations_dir: Path) -> None:
        self.classifier = classifier
        self.evaluations_dir = evaluations_dir

    def evaluate_files(self, file_paths: list[Path]) -> dict[str, Any]:
        per_brief_results: list[dict[str, Any]] = []
        for file_path in file_paths:
            for brief_payload in self._load_briefs(file_path):
                assessment = self.classifier.assess(brief_payload["brief"])
                per_brief_results.append(
                    {
                        "brief_id": brief_payload["id"],
                        "brief": brief_payload["brief"],
                        "source_file": str(file_path),
                        "expected_verdict_hint": brief_payload.get("expected_verdict_hint"),
                        "goal": brief_payload.get("goal"),
                        "verdict": assessment.verdict.value,
                        "confidence": round(assessment.confidence, 2),
                        "evidence_count": len(assessment.hard_evidence),
                        "human_review_flag": OperationalFlag.NEEDS_HUMAN_REVIEW.value
                        in [flag.value for flag in assessment.operational_flags],
                        "validation_posture": assessment.build_approach.validation_posture,
                        "unresolved_unknown_count": len(assessment.unresolved_unknowns),
                        "recommended_next_step": assessment.recommended_next_step,
                    }
                )
        summary = self._summarize(per_brief_results)
        payload = {
            "evaluated_at": datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat(),
            "files": [str(path) for path in file_paths],
            "per_brief_results": per_brief_results,
            "summary": summary,
        }
        self._persist(payload)
        return payload

    def _load_briefs(self, file_path: Path) -> list[dict[str, Any]]:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Evaluation file must contain a list of briefs: {file_path}")
        briefs: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict) or "id" not in item or "brief" not in item:
                raise ValueError(f"Each evaluation item must contain 'id' and 'brief': {file_path}")
            briefs.append(item)
        return briefs

    def _summarize(self, per_brief_results: list[dict[str, Any]]) -> dict[str, Any]:
        verdict_distribution = Counter(result["verdict"] for result in per_brief_results)
        posture_distribution = Counter(result["validation_posture"] for result in per_brief_results)
        average_confidence = (
            round(sum(float(result["confidence"]) for result in per_brief_results) / len(per_brief_results), 2)
            if per_brief_results
            else 0.0
        )
        human_review_count = sum(1 for result in per_brief_results if result["human_review_flag"])
        unverified_count = sum(1 for result in per_brief_results if result["verdict"] == Verdict.UNVERIFIED_LOCALLY.value)
        return {
            "brief_count": len(per_brief_results),
            "verdict_distribution": dict(sorted(verdict_distribution.items())),
            "validation_posture_distribution": dict(sorted(posture_distribution.items())),
            "average_confidence": average_confidence,
            "needs_human_review_count": human_review_count,
            "unverified_locally_count": unverified_count,
        }

    def _persist(self, payload: dict[str, Any]) -> None:
        self.evaluations_dir.mkdir(parents=True, exist_ok=True)
        stamp = payload["evaluated_at"].replace(":", "-")
        json_path = self.evaluations_dir / f"evaluation-{stamp}.json"
        md_path = self.evaluations_dir / f"evaluation-{stamp}.md"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_path.write_text(self._to_markdown(payload), encoding="utf-8")
        (self.evaluations_dir / "last_evaluation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (self.evaluations_dir / "last_evaluation.md").write_text(self._to_markdown(payload), encoding="utf-8")

    def _to_markdown(self, payload: dict[str, Any]) -> str:
        summary = payload["summary"]
        lines = [
            "# Pilot Evaluation Summary",
            "",
            f"- Evaluated at: {payload['evaluated_at']}",
            f"- Files: {', '.join(payload['files'])}",
            "",
            "## Summary",
            f"- Brief count: {summary['brief_count']}",
            f"- Average confidence: {summary['average_confidence']:.2f}",
            f"- Needs human review count: {summary['needs_human_review_count']}",
            f"- Unverified locally count: {summary['unverified_locally_count']}",
            "",
            "## Verdict distribution",
        ]
        lines.extend(f"- {verdict}: {count}" for verdict, count in summary["verdict_distribution"].items())
        lines.extend(["", "## Validation posture distribution"])
        lines.extend(
            f"- {posture}: {count}" for posture, count in summary["validation_posture_distribution"].items()
        )
        lines.extend(
            [
                "",
                "## Per-brief results",
                "| ID | Verdict | Validation posture | Confidence | Evidence count | Needs human review | Unknown count |",
                "| --- | --- | --- | ---: | ---: | --- | ---: |",
            ]
        )
        for result in payload["per_brief_results"]:
            lines.append(
                "| {brief_id} | {verdict} | {validation_posture} | {confidence:.2f} | {evidence_count} | {human_review_flag} | {unresolved_unknown_count} |".format(
                    **result
                )
            )
        return "\n".join(lines) + "\n"
