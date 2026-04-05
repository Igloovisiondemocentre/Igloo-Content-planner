from __future__ import annotations

from datetime import datetime, timezone

from igloo_experience_builder.capability.build_approach import BuildApproachPlanner
from igloo_experience_builder.capability.confidence import calculate_confidence
from igloo_experience_builder.knowledge.retriever import DeterministicRetriever
from igloo_experience_builder.knowledge.taxonomy import (
    KNOWN_WORKING_BASELINE_CONCEPTS,
    feature_dependencies,
    request_concepts,
)
from igloo_experience_builder.knowledge.text_utils import select_excerpt, tokenize
from igloo_experience_builder.models import (
    BuildApproach,
    CapabilityAssessment,
    EvidenceCitation,
    EvidenceStrength,
    EvidenceIndex,
    LocalValidationStatus,
    OperationalFlag,
    RankedEvidence,
    Verdict,
)
from igloo_experience_builder.policy.support_policy import SupportPolicyEngine
from igloo_experience_builder.sandbox.discovery import SandboxDiscoveryService


class CapabilityClassifier:
    def __init__(self, index: EvidenceIndex, sandbox: SandboxDiscoveryService | None = None) -> None:
        self.index = index
        self.retriever = DeterministicRetriever(index)
        self.policy = SupportPolicyEngine()
        self.build_approach = BuildApproachPlanner()
        self.sandbox = sandbox

    def assess(self, question: str) -> CapabilityAssessment:
        evidence = self.retriever.search(question, limit=12)
        policy = self.policy.evaluate(question, evidence)
        local_validation = self.sandbox.run().validation_status if self.sandbox else self._default_validation()
        build_approach = self.build_approach.plan(question, evidence, policy)
        verdict = self._decide_verdict(question, evidence, policy, build_approach)
        confidence, confidence_reasoning = calculate_confidence(
            evidence,
            policy,
            build_approach,
            local_validation.state,
        )
        request_tags = request_concepts(question)
        hard_evidence = self._select_citations(evidence, request_tags, question)
        inference = self._build_inference(evidence, policy, build_approach, request_tags)
        why = self._build_why(policy, build_approach, request_tags)
        dependencies = feature_dependencies(request_tags)
        unresolved_unknowns = self._build_unknowns(policy, build_approach, local_validation.state)
        risks = self._build_risks(policy, build_approach, local_validation.state, verdict)
        implementation_route = self._implementation_route(verdict, build_approach)
        next_step = self._next_step(verdict, build_approach, local_validation.state)
        flags = [OperationalFlag.NEEDS_HUMAN_REVIEW] if (policy.needs_human_review or build_approach.needs_human_review) else []
        return CapabilityAssessment(
            request=question,
            verdict=verdict,
            confidence=confidence,
            confidence_reasoning=confidence_reasoning,
            support_policy=policy,
            operational_flags=flags,
            why=why,
            hard_evidence=hard_evidence,
            inference=inference,
            build_approach=build_approach,
            local_validation_status=local_validation,
            dependencies=dependencies,
            risks=risks,
            unresolved_unknowns=unresolved_unknowns,
            recommended_implementation_route=implementation_route,
            recommended_next_step=next_step,
            created_at=datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat(),
        )

    def _decide_verdict(
        self,
        question: str,
        evidence: list[RankedEvidence],
        policy,
        build_approach: BuildApproach,
    ) -> Verdict:
        concepts = request_concepts(question)
        coverage = policy.evidence_coverage
        if build_approach.implementation_kind in {"custom_web_app", "custom_integration"}:
            return Verdict.CUSTOM_ROUTE
        if policy.route_hint == "unsupported":
            return Verdict.UNSUPPORTED
        if policy.route_hint == "custom_route":
            return Verdict.CUSTOM_ROUTE
        if policy.route_hint == "unverified":
            return Verdict.UNVERIFIED_LOCALLY
        if not concepts:
            return Verdict.SUPPORTED_WITH_CONFIGURATION if evidence else Verdict.UNVERIFIED_LOCALLY
        missing = [concept for concept in concepts if coverage.get(concept, "missing") == "missing"]
        material_missing = [
            concept
            for concept in missing
            if concept not in KNOWN_WORKING_BASELINE_CONCEPTS and concept not in {"local_workflow", "remote_workflow"}
        ]
        primary_hits = [concept for concept in concepts if coverage.get(concept) == "primary"]
        exact_match = any(
            item.fragment.evidence_strength == EvidenceStrength.HARD
            and all(concept in item.fragment.concept_tags for concept in concepts)
            for item in evidence[:3]
        )
        if material_missing:
            return Verdict.UNVERIFIED_LOCALLY
        if exact_match and len(primary_hits) == len(concepts) and build_approach.route_confidence == "concrete":
            return Verdict.DOCUMENTED
        return Verdict.SUPPORTED_WITH_CONFIGURATION

    def _to_citation(self, item: RankedEvidence, query_terms: list[str]) -> EvidenceCitation:
        excerpt = select_excerpt(item.fragment.text, query_terms, max_chars=240)
        return EvidenceCitation(
            title=item.fragment.title,
            location=item.fragment.location,
            excerpt=excerpt,
            source_type=item.fragment.source_type,
            evidence_strength=item.fragment.evidence_strength,
            freshness_status=item.fragment.freshness_status,
            score=round(item.score, 2),
        )

    def _select_citations(self, evidence: list[RankedEvidence], request_tags: list[str], question: str) -> list[EvidenceCitation]:
        strength_rank = {
            EvidenceStrength.HARD: 3,
            EvidenceStrength.MEDIUM: 2,
            EvidenceStrength.WEAK: 1,
        }
        query_terms = list(dict.fromkeys(request_tags + tokenize(question)))
        ordered = sorted(
            evidence,
            key=lambda item: (strength_rank[item.fragment.evidence_strength], item.score),
            reverse=True,
        )
        citations: list[EvidenceCitation] = []
        seen_sources: set[str] = set()
        covered_concepts: set[str] = set()
        for item in ordered:
            source_key = (
                item.fragment.fragment_id
                if item.fragment.source_type.value == "internal_pdf"
                else item.fragment.source_id
            )
            if source_key in seen_sources:
                continue
            new_concepts = set(item.fragment.concept_tags) & set(request_tags)
            if citations and not (new_concepts - covered_concepts) and len(citations) < 3:
                continue
            citations.append(self._to_citation(item, query_terms))
            seen_sources.add(source_key)
            covered_concepts.update(new_concepts)
            if len(citations) >= 4:
                break
        if len(citations) < 4:
            for item in ordered:
                source_key = (
                    item.fragment.fragment_id
                    if item.fragment.source_type.value == "internal_pdf"
                    else item.fragment.source_id
                )
                if source_key in seen_sources:
                    continue
                citations.append(self._to_citation(item, query_terms))
                seen_sources.add(source_key)
                if len(citations) >= 4:
                    break
        return citations

    def _build_inference(
        self,
        evidence: list[RankedEvidence],
        policy,
        build_approach: BuildApproach,
        concepts: list[str],
    ) -> list[str]:
        inference: list[str] = []
        if evidence:
            inference.append(
                "The answer combines separately documented capabilities from the runtime API and workflow docs instead of relying on a model-only judgment."
            )
        if len(concepts) > 1:
            inference.append(
                "The request spans multiple concepts, so the verdict reflects combined evidence coverage rather than one isolated feature."
            )
        if build_approach.practical_summary:
            inference.append(build_approach.practical_summary)
        inference.append(
            f"Validation posture is classified as {build_approach.validation_posture}, which helps separate basic format support from higher-risk experience behavior."
        )
        if build_approach.use_case_alignment:
            inference.append(
                "Comparable Igloo case-study and video-gallery patterns were used as workflow priors only; they improve route selection and fit judgment without overriding runtime/platform truth."
            )
        if build_approach.runtime_surfaces:
            inference.append(f"Likely runtime build path: {build_approach.runtime_surfaces[0]}")
        if any("PowerPoint" in item or "Canva" in item for item in build_approach.authoring_tools):
            inference.append(
                "PowerPoint or Canva are treated as upstream authoring tools only; the evidence supports the exported runtime formats, not direct Canva/PowerPoint control inside Igloo."
            )
        inference.extend(policy.notes)
        return list(dict.fromkeys(inference))

    def _build_why(self, policy, build_approach: BuildApproach, concepts: list[str]) -> list[str]:
        why = [
            f"Technical status: {policy.technical_status}.",
            f"Documentation status: {policy.documentation_status}.",
            f"Support-policy status: {policy.support_status}.",
            f"Platform capability: {build_approach.platform_capability}.",
            f"Exact item check: {build_approach.exact_item_check}.",
            f"Workflow fit: {build_approach.workflow_fit}.",
            f"Control / interaction fit: {build_approach.control_interaction_fit}.",
            f"Review requirement: {build_approach.review_requirement}.",
        ]
        if concepts:
            why.append(f"Detected request concepts: {', '.join(concepts)}.")
        if policy.review_reasons:
            why.append(f"Human-review reasons: {'; '.join(policy.review_reasons)}.")
        return why

    def _build_unknowns(self, policy, build_approach: BuildApproach, local_validation_state: str) -> list[str]:
        missing = [concept for concept, state in policy.evidence_coverage.items() if state == "missing"]
        baseline_missing = [concept for concept in missing if concept in KNOWN_WORKING_BASELINE_CONCEPTS]
        material_missing = [
            concept
            for concept in missing
            if concept not in KNOWN_WORKING_BASELINE_CONCEPTS and concept not in {"local_workflow", "remote_workflow"}
        ]
        contextual_missing = [concept for concept in missing if concept in {"local_workflow", "remote_workflow"}]
        unknowns: list[str] = []
        if material_missing:
            unknowns.append(f"Coverage gaps by concept: {', '.join(f'{key}={value}' for key, value in policy.evidence_coverage.items())}.")
        elif contextual_missing and build_approach.platform_capability == "known working":
            unknowns.append(
                "Local or remote workflow details still need confirming, but the main platform route is supported by the retrieved evidence."
            )
            unknowns.append(f"Coverage map: {', '.join(f'{key}={value}' for key, value in policy.evidence_coverage.items())}.")
        elif baseline_missing and build_approach.platform_capability == "known working":
            unknowns.append(
                "Some low-risk known-working content classes were not separately surfaced in the retrieved excerpts, so the main checks are exact asset/link/model compatibility, workflow fit, and control simplicity."
            )
            unknowns.append(f"Coverage map: {', '.join(f'{key}={value}' for key, value in policy.evidence_coverage.items())}.")
        else:
            unknowns.append(f"Coverage gaps by concept: {', '.join(f'{key}={value}' for key, value in policy.evidence_coverage.items())}.")
        unknowns.extend(build_approach.build_unknowns)
        if local_validation_state != "validated" and build_approach.validation_posture != "documented media workflow":
            unknowns.append("No successful live sandbox validation has confirmed the workflow in this environment.")
        if policy.needs_human_review:
            unknowns.append("Commercial supportability still needs human review before client-facing use.")
        return unknowns

    def _build_risks(
        self,
        policy,
        build_approach: BuildApproach,
        local_validation_state: str,
        verdict: Verdict,
    ) -> list[str]:
        risks = list(policy.notes)
        risks.extend(policy.review_reasons)
        risks.extend(build_approach.build_unknowns)
        if local_validation_state != "validated" and build_approach.validation_posture != "documented media workflow":
            risks.append("Without a successful local sandbox probe, this remains a documented assessment rather than a proven local workflow.")
        if local_validation_state != "validated" and build_approach.validation_posture == "documented media workflow":
            risks.append("This is a documented media workflow, but the exact content format, hosting path, and operator setup still need confirmation.")
        if verdict in {Verdict.SUPPORTED_WITH_CONFIGURATION, Verdict.CUSTOM_ROUTE}:
            risks.append("Configuration details or environment assumptions may still change the implementation path.")
        return list(dict.fromkeys(risks))

    def _implementation_route(self, verdict: Verdict, build_approach: BuildApproach) -> str:
        runtime_summary = "; ".join(build_approach.runtime_surfaces[:2])
        authoring_summary = "; ".join(build_approach.authoring_tools[:2])
        if verdict == Verdict.SUPPORTED_WITH_CONFIGURATION:
            return (
                f"{build_approach.practical_summary} "
                "Treat this as a configuration-led workflow. "
                f"Likely runtime path: {runtime_summary} "
                f"Likely content-prep path: {authoring_summary}"
            )
        if verdict == Verdict.DOCUMENTED:
            return (
                f"{build_approach.practical_summary} "
                "Follow the documented workflow directly and validate the exact path in the local sandbox before broader reuse. "
                f"Likely runtime path: {runtime_summary}"
            )
        if verdict == Verdict.CUSTOM_ROUTE:
            return (
                f"{build_approach.practical_summary} "
                "Treat this as a custom implementation route with engineering and product review before any client commitment. "
                f"Most likely custom build path: {runtime_summary}"
            )
        if verdict == Verdict.UNSUPPORTED:
            return f"{build_approach.practical_summary} Do not position this as supported. Escalate only if product or engineering intends to change the capability boundary."
        return f"{build_approach.practical_summary} Treat this as unverified until stronger primary evidence or a successful local validation probe is available."

    def _next_step(self, verdict: Verdict, build_approach: BuildApproach, local_validation_state: str) -> str:
        if verdict in {Verdict.DOCUMENTED, Verdict.SUPPORTED_WITH_CONFIGURATION} and local_validation_state != "validated":
            if build_approach.validation_posture == "documented media workflow":
                if build_approach.exact_item_check in {"needs checking", "likely fine"}:
                    return "Confirm the exact file, link, model, or prepared asset behaves as expected, then lock the layer choice and playback/reachability assumptions; read-only sandbox probing is optional for this known-working documented media case."
                return "Confirm the final configuration assumptions for the prepared workflow; read-only sandbox probing is optional for this known-working documented media case."
            if build_approach.build_unknowns:
                return "Confirm the proposed content and authoring route with a human reviewer, then run a read-only local sandbox validation against that exact setup."
            return "Run a read-only local sandbox validation next so the documented workflow is checked in the current environment."
        if verdict == Verdict.CUSTOM_ROUTE:
            return "Confirm whether a custom web/app integration route is acceptable, then scope the exact build surface before promising support."
        if verdict == Verdict.UNSUPPORTED:
            return "Set expectation that this is outside the supported Phase 1 boundary and capture it as product feedback if needed."
        return "Gather stronger primary evidence or validate the workflow locally before treating it as supportable."

    def _default_validation(self) -> LocalValidationStatus:
        return LocalValidationStatus(
            state="not_run",
            summary="No local sandbox probe was run.",
            details=["Sandbox configuration was not provided to the classifier."],
            disclaimer=(
                "Sandbox success means technically reproducible in this local environment. "
                "It does not mean ready to promise to a client."
            ),
        )
