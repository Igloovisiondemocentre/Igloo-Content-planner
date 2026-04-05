from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


@dataclass(slots=True)
class StructureProfile:
    structure_id: str
    label: str
    description: str
    shape: str
    projection_style: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class ContentCandidate:
    candidate_id: str
    title: str
    content_type: str
    source: str
    location: str
    readiness_status: str
    readiness_score: int
    exact_item_status: str
    notes: list[str]
    recommended_layer_type: str
    query_hint: str
    resolution_label: str
    recommended_minutes: int
    selected: bool = False
    thumbnail_url: str = ""
    preview_caption: str = ""
    provider: str = ""
    match_score: int = 0
    setup_archetype: str = ""
    layout_role: str = ""
    setup_notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class LayerDraft:
    layer_id: str
    label: str
    layer_type: str
    purpose: str
    source_candidate_id: str | None
    key_settings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class WorkflowStep:
    step_id: str
    label: str
    minutes: int
    summary: str
    source_candidate_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class BuilderRecommendation:
    title: str
    detail: str
    priority: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class AssessmentSnapshot:
    verdict: str
    confidence: float
    confidence_percent: int
    operational_flags: list[str]
    validation_posture: str
    platform_capability: str
    exact_item_check: str
    workflow_fit: str
    control_interaction_fit: str
    recommended_route: str
    top_dependencies: list[str]
    top_unknowns: list[str]
    evidence: list[dict[str, Any]]
    practical_summary: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class SessionLayerSummary:
    layer_id: str
    name: str
    layer_type: str
    file_path: str
    source_field: str
    playback_flags: list[str]
    render_passes: list[str]
    inferred_content_type: str
    inferred_experience_type: str
    readiness_status: str
    readiness_score: int
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class SessionImportSummary:
    source_name: str
    product_version: str
    session_name: str
    session_id: str
    exported_with_assets: bool
    trigger_action_enabled: bool
    layer_count: int
    inferred_session_type: str
    notes: list[str]
    layers: list[SessionLayerSummary]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


@dataclass(slots=True)
class ExperienceDraft:
    brief: str
    structure: StructureProfile
    suggested_structure_id: str
    suggested_structure_reason: str
    setup_archetype: str
    setup_summary: str
    readiness_score: int
    readiness_label: str
    target_duration_minutes: int
    estimated_duration_minutes: int
    duration_gap_minutes: int
    assessment: AssessmentSnapshot
    selected_content: list[ContentCandidate]
    layer_drafts: list[LayerDraft]
    workflow_steps: list[WorkflowStep]
    recommendations: list[BuilderRecommendation]
    use_case_alignment: list[str]
    search_suggestions: list[dict[str, str]]
    session_import: SessionImportSummary | None = None
    demo_plan_notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)
