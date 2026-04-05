from __future__ import annotations

import re

from igloo_experience_builder.knowledge.taxonomy import (
    KNOWN_WORKING_BASELINE_CONCEPTS,
    request_concepts,
    text_matches_concept,
)
from igloo_experience_builder.models import RankedEvidence, SourceType, SupportPolicyDecision

NEGATIVE_PATTERNS = re.compile(r"\b(not supported|unsupported|not available|cannot|can't)\b", re.IGNORECASE)
CUSTOM_ROUTE_HINTS = {"integration", "remote_workflow", "trigger_action"}
PRIMARY_SOURCE_TYPES = {SourceType.RUNTIME_API, SourceType.PLATFORM_DOC}

ACCESSIBILITY_REVIEW_HINTS = {
    "accessible",
    "accessibility",
    "inclusive",
    "wheelchair",
    "mobility",
    "neurodiverse",
    "low cognitive load",
    "caption",
    "subtitle",
}
AUDIENCE_REVIEW_HINTS = {
    "audience",
    "visitor",
    "children",
    "older adults",
    "school group",
    "public-facing",
    "public facing",
    "public-safe",
    "public safe",
    "audience fit",
}
OPERATIONAL_REVIEW_HINTS = {
    "operator-light",
    "operator light",
    "easy",
    "simple",
    "intuitive",
    "low maintenance",
    "low-maintenance",
    "unattended",
    "kiosk",
    "restart cleanly",
    "reset cleanly",
    "robust",
    "no custom content required",
}
APP_RISK_HINTS = {
    "webxr",
    "webgl",
    "unity",
    "unreal",
    "branching",
    "vote",
    "outcomes",
    "interactive journey",
}
CUSTOM_APP_RISK_HINTS = {"bespoke", "custom app", "custom web"}
NEGATED_CUSTOM_APP_HINTS = {"no custom app", "no custom web", "no bespoke app", "without a custom app", "no custom app preferred"}
LIVE_RISK_HINTS = {
    "live",
    "real-time",
    "real time",
    "dashboard",
    "camera",
    "feed",
    "teams",
    "remote participants",
    "hybrid",
    "collaborative",
    "comparison layout",
    "markups",
}
KNOWN_OPERATOR_LED_LIVE_HINTS = {
    "operator-driven",
    "operator driven",
    "operator-run",
    "operator run",
    "aeco",
    "bim",
    "revizto",
    "revistoo",
    "autodesk",
    "teams",
    "ndi",
}
SECONDARY_ONLY_HINTS = {"buyer's guide", "buyers guide", "only from a buyer", "only from the buyer", "only from the guide"}
GENERATIVE_AUTOMATION_HINTS = {
    "one prompt",
    "text prompt",
    "from a text prompt",
    "automatically",
    "fully ai-generated",
    "fully ai generated",
    "ai-generated",
    "ai generated",
    "no human content prep",
    "no human prep",
}


class SupportPolicyEngine:
    def evaluate(self, question: str, evidence: list[RankedEvidence]) -> SupportPolicyDecision:
        concepts = request_concepts(question)
        normalized = question.lower()
        coverage: dict[str, str] = {}
        negative_hits = False
        runtime_hits = 0
        workflow_hits = 0
        secondary_hits = 0

        for concept in concepts:
            state = "missing"
            concept_runtime = 0
            concept_workflow = 0
            concept_secondary = 0
            for item in evidence:
                if concept not in item.fragment.concept_tags and not text_matches_concept(f"{item.fragment.title} {item.fragment.text}", concept):
                    continue
                if NEGATIVE_PATTERNS.search(item.fragment.text):
                    negative_hits = True
                if item.fragment.source_type in PRIMARY_SOURCE_TYPES:
                    state = "primary"
                elif state == "missing":
                    state = "secondary"
                if item.fragment.source_type == SourceType.RUNTIME_API:
                    concept_runtime += 1
                elif item.fragment.source_type == SourceType.PLATFORM_DOC:
                    concept_workflow += 1
                else:
                    concept_secondary += 1
            runtime_hits += concept_runtime
            workflow_hits += concept_workflow
            secondary_hits += concept_secondary
            coverage[concept] = state

        primary_coverage = [concept for concept, state in coverage.items() if state == "primary"]
        secondary_only = [concept for concept, state in coverage.items() if state == "secondary"]
        missing = [concept for concept, state in coverage.items() if state == "missing"]

        notes: list[str] = []
        review_reasons: list[str] = []
        route_hint = "configuration"

        if negative_hits:
            notes.append("At least one retrieved source explicitly suggests the requested capability is not supported.")
            route_hint = "unsupported"
        material_missing = [concept for concept in missing if concept not in KNOWN_WORKING_BASELINE_CONCEPTS]
        contextual_workflow_missing = [concept for concept in material_missing if concept in {"local_workflow", "remote_workflow"}]
        material_missing = [concept for concept in material_missing if concept not in {"local_workflow", "remote_workflow"}]
        baseline_missing = [concept for concept in missing if concept in KNOWN_WORKING_BASELINE_CONCEPTS]

        if material_missing or (missing and not primary_coverage):
            missing_for_note = material_missing or missing
            notes.append(f"Primary evidence is missing for: {', '.join(missing_for_note)}.")
            route_hint = "unverified"
        elif contextual_workflow_missing:
            notes.append(
                "Some local/remote workflow details were not surfaced as separate primary snippets, but the retrieved evidence still covers the main platform route. "
                "Treat the remaining uncertainty as environment setup and operator-flow checking rather than baseline support doubt."
            )
        elif baseline_missing:
            notes.append(
                "Some requested concepts were not surfaced as separate retrieved snippets, but they belong to normal documented Igloo capability classes. "
                "Treat the remaining uncertainty as exact-item, workflow-fit, or control-fit checking rather than baseline platform doubt."
            )
        if secondary_only:
            notes.append("Some requested capability coverage comes only from internal PDFs, which are secondary evidence and not runtime truth.")
        if set(concepts) & CUSTOM_ROUTE_HINTS and workflow_hits == 0 and runtime_hits > 0:
            route_hint = "custom_route"
            notes.append("The capability leans on technical integration evidence without matching workflow guidance.")

        if self._contains_any(normalized, ACCESSIBILITY_REVIEW_HINTS):
            review_reasons.append("Accessibility, inclusion, or mobility-fit claims need human review beyond format support.")
        if self._contains_any(normalized, AUDIENCE_REVIEW_HINTS):
            review_reasons.append("Audience-fit or public-use claims need human review beyond runtime documentation.")
        if self._contains_any(normalized, OPERATIONAL_REVIEW_HINTS):
            review_reasons.append("Operational simplicity, unattended use, or reset/robustness claims need human review.")
        if self._contains_any(normalized, LIVE_RISK_HINTS):
            if self._contains_any(normalized, KNOWN_OPERATOR_LED_LIVE_HINTS):
                notes.append("The brief matches a known operator-led live or collaborative workflow class; the main checks are exact routing, environment setup, and operator flow.")
            else:
                review_reasons.append("Live, hybrid, or externally driven behavior depends on external systems and should be reviewed conservatively.")
        if self._contains_any(normalized, APP_RISK_HINTS):
            review_reasons.append("The brief depends on app-like, branching, or stateful behavior rather than only documented media support.")
            if route_hint == "configuration":
                route_hint = "custom_route"
        if self._contains_any(normalized, CUSTOM_APP_RISK_HINTS) and not self._contains_any(normalized, NEGATED_CUSTOM_APP_HINTS):
            review_reasons.append("The brief implies a bespoke app surface rather than a straightforward documented content workflow.")
            if route_hint == "configuration":
                route_hint = "custom_route"
        if self._contains_any(normalized, SECONDARY_ONLY_HINTS):
            review_reasons.append("The brief explicitly asks to rely on secondary commercial material rather than primary runtime or workflow truth.")
            route_hint = "unverified"
        if self._contains_any(normalized, GENERATIVE_AUTOMATION_HINTS):
            review_reasons.append("The brief asks for autonomous content generation or one-prompt production that sits outside the current Phase 1 boundary.")
            route_hint = "unsupported"

        if negative_hits:
            technical_status = "explicitly contradicted"
            documentation_status = "not supported in retrieved sources"
            support_status = "not supportable for pre-sales commitment"
            needs_human_review = True
        elif material_missing or (missing and not primary_coverage):
            technical_status = "uncertain"
            documentation_status = "partially documented"
            support_status = "ambiguous"
            needs_human_review = True
        elif secondary_only and not primary_coverage:
            technical_status = "plausible"
            documentation_status = "secondary evidence only"
            support_status = "risky / ambiguous"
            route_hint = "unverified"
            needs_human_review = True
        else:
            technical_status = "technically possible"
            documentation_status = "documented"
            support_status = "supported for pre-sales / product use"
            needs_human_review = False

        if runtime_hits > 0 and workflow_hits == 0 and route_hint == "configuration":
            route_hint = "custom_route"
            support_status = "risky / ambiguous"
            notes.append("The evidence is strong technically but light on workflow guidance.")
        if workflow_hits > 0 and runtime_hits > 0 and route_hint == "configuration":
            notes.append("Runtime and workflow sources both contribute evidence for this answer.")
        if secondary_hits and not primary_coverage:
            notes.append("Secondary evidence should inform context only and must not override runtime/platform truth.")
        if route_hint == "unsupported" and not negative_hits:
            support_status = "not supportable for pre-sales commitment"
            notes.append("Some platform building blocks are documented, but the full requested outcome goes beyond supported Phase 1 use.")

        if review_reasons:
            needs_human_review = True
            if support_status == "supported for pre-sales / product use":
                notes.append("The runtime path may be supportable, but broader experience-quality or operational claims still need human review.")

        return SupportPolicyDecision(
            technical_status=technical_status,
            documentation_status=documentation_status,
            support_status=support_status,
            needs_human_review=needs_human_review,
            route_hint=route_hint,
            notes=notes,
            review_reasons=list(dict.fromkeys(review_reasons)),
            evidence_coverage=coverage,
        )

    def _contains_any(self, normalized: str, phrases: set[str]) -> bool:
        return any(phrase in normalized for phrase in phrases)
