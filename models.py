from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    RUNTIME_API = "runtime_api"
    PLATFORM_DOC = "platform_doc"
    INTERNAL_PDF = "internal_pdf"


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    UNKNOWN = "unknown"


class EvidenceStrength(str, Enum):
    HARD = "hard"
    MEDIUM = "medium"
    WEAK = "weak"


class Verdict(str, Enum):
    DOCUMENTED = "Documented"
    SUPPORTED_WITH_CONFIGURATION = "Supported with configuration"
    CUSTOM_ROUTE = "Custom route"
    UNSUPPORTED = "Unsupported"
    UNVERIFIED_LOCALLY = "Unverified locally"


class OperationalFlag(str, Enum):
    NEEDS_HUMAN_REVIEW = "Needs human review"


@dataclass(slots=True)
class SourceRecord:
    source_id: str
    source_type: SourceType
    title: str
    canonical_location: str
    summary: str
    fetched_at: str
    last_modified: str | None
    freshness_status: FreshnessStatus
    extraction_method: str
    truth_tier: str
    source_priority: float
    provenance_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceRecord":
        return cls(
            source_id=payload["source_id"],
            source_type=SourceType(payload["source_type"]),
            title=payload["title"],
            canonical_location=payload["canonical_location"],
            summary=payload["summary"],
            fetched_at=payload["fetched_at"],
            last_modified=payload.get("last_modified"),
            freshness_status=FreshnessStatus(payload["freshness_status"]),
            extraction_method=payload["extraction_method"],
            truth_tier=payload["truth_tier"],
            source_priority=float(payload["source_priority"]),
            provenance_notes=payload.get("provenance_notes", ""),
        )


@dataclass(slots=True)
class EvidenceFragment:
    fragment_id: str
    source_id: str
    source_type: SourceType
    title: str
    text: str
    location: str
    concept_tags: list[str]
    tokens: list[str]
    evidence_strength: EvidenceStrength
    freshness_status: FreshnessStatus
    fetched_at: str
    last_modified: str | None
    extraction_method: str
    truth_tier: str
    source_priority: float

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceFragment":
        return cls(
            fragment_id=payload["fragment_id"],
            source_id=payload["source_id"],
            source_type=SourceType(payload["source_type"]),
            title=payload["title"],
            text=payload["text"],
            location=payload["location"],
            concept_tags=list(payload.get("concept_tags", [])),
            tokens=list(payload.get("tokens", [])),
            evidence_strength=EvidenceStrength(payload["evidence_strength"]),
            freshness_status=FreshnessStatus(payload["freshness_status"]),
            fetched_at=payload["fetched_at"],
            last_modified=payload.get("last_modified"),
            extraction_method=payload["extraction_method"],
            truth_tier=payload["truth_tier"],
            source_priority=float(payload["source_priority"]),
        )


@dataclass(slots=True)
class EvidenceIndex:
    built_at: str
    sources: list[SourceRecord]
    fragments: list[EvidenceFragment]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceIndex":
        return cls(
            built_at=payload["built_at"],
            sources=[SourceRecord.from_dict(item) for item in payload.get("sources", [])],
            fragments=[EvidenceFragment.from_dict(item) for item in payload.get("fragments", [])],
            warnings=list(payload.get("warnings", [])),
        )


@dataclass(slots=True)
class RankedEvidence:
    fragment: EvidenceFragment
    score: float


@dataclass(slots=True)
class SupportPolicyDecision:
    technical_status: str
    documentation_status: str
    support_status: str
    needs_human_review: bool
    route_hint: str
    notes: list[str]
    review_reasons: list[str]
    evidence_coverage: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SupportPolicyDecision":
        return cls(
            technical_status=payload["technical_status"],
            documentation_status=payload["documentation_status"],
            support_status=payload["support_status"],
            needs_human_review=bool(payload["needs_human_review"]),
            route_hint=payload["route_hint"],
            notes=list(payload.get("notes", [])),
            review_reasons=list(payload.get("review_reasons", [])),
            evidence_coverage=dict(payload.get("evidence_coverage", {})),
        )


@dataclass(slots=True)
class EvidenceCitation:
    title: str
    location: str
    excerpt: str
    source_type: SourceType
    evidence_strength: EvidenceStrength
    freshness_status: FreshnessStatus
    score: float

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "EvidenceCitation":
        return cls(
            title=payload["title"],
            location=payload["location"],
            excerpt=payload["excerpt"],
            source_type=SourceType(payload["source_type"]),
            evidence_strength=EvidenceStrength(payload["evidence_strength"]),
            freshness_status=FreshnessStatus(payload["freshness_status"]),
            score=float(payload["score"]),
        )


@dataclass(slots=True)
class LocalValidationStatus:
    state: str
    summary: str
    details: list[str]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LocalValidationStatus":
        return cls(
            state=payload["state"],
            summary=payload["summary"],
            details=list(payload.get("details", [])),
            disclaimer=payload["disclaimer"],
        )


@dataclass(slots=True)
class BuildApproach:
    implementation_kind: str
    validation_posture: str
    platform_capability: str
    exact_item_check: str
    workflow_fit: str
    control_interaction_fit: str
    practical_summary: str
    format_support_confidence: str
    configuration_burden: str
    experience_risk: str
    review_requirement: str
    use_case_alignment: list[str]
    runtime_surfaces: list[str]
    native_platform_support: list[str]
    content_design_requirements: list[str]
    authoring_tools: list[str]
    candidate_routes: list[str]
    interaction_model: list[str]
    content_assumptions: list[str]
    custom_work_items: list[str]
    build_unknowns: list[str]
    route_confidence: str
    needs_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BuildApproach":
        return cls(
            implementation_kind=payload.get("implementation_kind", "configuration"),
            validation_posture=payload.get("validation_posture", "configuration-heavy workflow"),
            platform_capability=payload.get("platform_capability", "unclear"),
            exact_item_check=payload.get("exact_item_check", "not assessed"),
            workflow_fit=payload.get("workflow_fit", "unknown"),
            control_interaction_fit=payload.get("control_interaction_fit", "not applicable"),
            practical_summary=payload.get("practical_summary", ""),
            format_support_confidence=payload.get("format_support_confidence", "mixed"),
            configuration_burden=payload.get("configuration_burden", "medium"),
            experience_risk=payload.get("experience_risk", "medium"),
            review_requirement=payload.get("review_requirement", "recommended"),
            use_case_alignment=list(payload.get("use_case_alignment", [])),
            runtime_surfaces=list(payload.get("runtime_surfaces", [])),
            native_platform_support=list(payload.get("native_platform_support", [])),
            content_design_requirements=list(payload.get("content_design_requirements", [])),
            authoring_tools=list(payload.get("authoring_tools", [])),
            candidate_routes=list(payload.get("candidate_routes", [])),
            interaction_model=list(payload.get("interaction_model", [])),
            content_assumptions=list(payload.get("content_assumptions", [])),
            custom_work_items=list(payload.get("custom_work_items", [])),
            build_unknowns=list(payload.get("build_unknowns", [])),
            route_confidence=payload.get("route_confidence", "partial"),
            needs_human_review=bool(payload.get("needs_human_review", False)),
        )


@dataclass(slots=True)
class CapabilityAssessment:
    request: str
    verdict: Verdict
    confidence: float
    confidence_reasoning: list[str]
    support_policy: SupportPolicyDecision
    operational_flags: list[OperationalFlag]
    why: list[str]
    hard_evidence: list[EvidenceCitation]
    inference: list[str]
    build_approach: BuildApproach
    local_validation_status: LocalValidationStatus
    dependencies: list[str]
    risks: list[str]
    unresolved_unknowns: list[str]
    recommended_implementation_route: str
    recommended_next_step: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CapabilityAssessment":
        return cls(
            request=payload["request"],
            verdict=Verdict(payload["verdict"]),
            confidence=float(payload["confidence"]),
            confidence_reasoning=list(payload.get("confidence_reasoning", [])),
            support_policy=SupportPolicyDecision.from_dict(payload["support_policy"]),
            operational_flags=[OperationalFlag(item) for item in payload.get("operational_flags", [])],
            why=list(payload.get("why", [])),
            hard_evidence=[EvidenceCitation.from_dict(item) for item in payload.get("hard_evidence", [])],
            inference=list(payload.get("inference", [])),
            build_approach=BuildApproach.from_dict(payload["build_approach"]),
            local_validation_status=LocalValidationStatus.from_dict(payload["local_validation_status"]),
            dependencies=list(payload.get("dependencies", [])),
            risks=list(payload.get("risks", [])),
            unresolved_unknowns=list(payload.get("unresolved_unknowns", [])),
            recommended_implementation_route=payload["recommended_implementation_route"],
            recommended_next_step=payload["recommended_next_step"],
            created_at=payload["created_at"],
        )


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value
