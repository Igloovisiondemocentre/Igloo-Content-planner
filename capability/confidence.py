from __future__ import annotations

from statistics import mean

from igloo_experience_builder.models import BuildApproach, FreshnessStatus, RankedEvidence, SupportPolicyDecision

FRESHNESS_WEIGHTS = {
    FreshnessStatus.FRESH: 1.0,
    FreshnessStatus.AGING: 0.75,
    FreshnessStatus.STALE: 0.4,
    FreshnessStatus.UNKNOWN: 0.55,
}

POSTURE_CEILINGS = {
    ("documented media workflow", "validated"): 0.86,
    ("documented media workflow", "not_run"): 0.82,
    ("documented media workflow", "failed"): 0.66,
    ("configuration-heavy workflow", "validated"): 0.78,
    ("configuration-heavy workflow", "not_run"): 0.66,
    ("configuration-heavy workflow", "failed"): 0.58,
    ("app/integration-risk workflow", "validated"): 0.68,
    ("app/integration-risk workflow", "not_run"): 0.56,
    ("app/integration-risk workflow", "failed"): 0.48,
}


def calculate_confidence(
    ranked_evidence: list[RankedEvidence],
    policy: SupportPolicyDecision,
    build_approach: BuildApproach,
    local_validation_state: str,
) -> tuple[float, list[str]]:
    if not ranked_evidence:
        return 0.1, ["No relevant evidence fragments were retrieved."]

    top = ranked_evidence[:5]
    freshness_score = mean(FRESHNESS_WEIGHTS[item.fragment.freshness_status] for item in top)
    primary_count = sum(1 for item in top if item.fragment.truth_tier in {"runtime", "workflow"})
    secondary_count = sum(1 for item in top if item.fragment.truth_tier == "secondary")
    primary_ratio = primary_count / max(len(top), 1)
    coverage_total = max(len(policy.evidence_coverage), 1)
    primary_coverage = sum(1 for value in policy.evidence_coverage.values() if value == "primary") / coverage_total

    base = 0.18
    base += freshness_score * 0.18
    base += primary_ratio * 0.22
    base += primary_coverage * 0.14

    if policy.documentation_status == "documented":
        base += 0.08
    if policy.support_status == "supported for pre-sales / product use":
        base += 0.06
    if build_approach.platform_capability == "known working":
        base += 0.06
    if build_approach.platform_capability == "unsupported":
        base -= 0.1
    if build_approach.exact_item_check == "likely fine":
        base += 0.03
    if build_approach.exact_item_check == "needs checking":
        base -= 0.02
    if build_approach.exact_item_check == "likely problematic":
        base -= 0.08
    if build_approach.workflow_fit == "good fit":
        base += 0.03
    if build_approach.workflow_fit == "poor fit":
        base -= 0.08
    if build_approach.control_interaction_fit == "straightforward":
        base += 0.03
    if build_approach.control_interaction_fit == "needs review":
        base -= 0.03
    if build_approach.control_interaction_fit == "high risk":
        base -= 0.08

    if secondary_count:
        base -= min(secondary_count, 3) * 0.04
    if policy.review_reasons:
        base -= min(len(policy.review_reasons), 3) * 0.05
    if build_approach.route_confidence == "partial":
        base -= 0.08
    if build_approach.route_confidence == "speculative":
        base -= 0.16
    if build_approach.validation_posture == "configuration-heavy workflow":
        base -= 0.06
    if build_approach.validation_posture == "app/integration-risk workflow":
        base -= 0.14
    if build_approach.configuration_burden == "high":
        base -= 0.05
    if build_approach.experience_risk == "high":
        base -= 0.08
    if len(build_approach.content_assumptions) >= 3:
        base -= 0.04
    if len(build_approach.build_unknowns) >= 3:
        base -= 0.05
    if len(build_approach.candidate_routes) >= 2:
        base -= 0.03

    if local_validation_state == "validated":
        base += 0.08
    elif local_validation_state == "failed":
        base -= 0.08
    elif local_validation_state == "not_run" and build_approach.validation_posture != "documented media workflow":
        base -= 0.03

    ceiling = POSTURE_CEILINGS.get(
        (build_approach.validation_posture, local_validation_state),
        POSTURE_CEILINGS[(build_approach.validation_posture, "not_run")],
    )
    confidence = max(0.05, min(ceiling, round(base, 2)))

    reasoning = [
        f"Primary-source evidence count in top results: {primary_count}.",
        f"Secondary-source evidence count in top results: {secondary_count}.",
        f"Average freshness score across top evidence: {freshness_score:.2f}.",
        f"Primary concept coverage ratio: {primary_coverage:.2f}.",
        f"Validation posture: {build_approach.validation_posture}.",
        f"Platform capability: {build_approach.platform_capability}.",
        f"Exact item check: {build_approach.exact_item_check}.",
        f"Workflow fit: {build_approach.workflow_fit}.",
        f"Control / interaction fit: {build_approach.control_interaction_fit}.",
        f"Configuration burden: {build_approach.configuration_burden}.",
        f"Experience risk: {build_approach.experience_risk}.",
        f"Review requirement: {build_approach.review_requirement}.",
    ]
    if policy.review_reasons:
        reasoning.append(f"Human-review triggers: {len(policy.review_reasons)}.")
    if local_validation_state == "validated":
        reasoning.append("A local sandbox probe succeeded, which improves confidence but does not make the answer client-ready by itself.")
    elif local_validation_state == "not_run":
        if build_approach.validation_posture == "documented media workflow":
            reasoning.append("No live sandbox validation was run, but this posture is a documented media workflow, so confidence rests mainly on explicit workflow documentation and configuration assumptions.")
        else:
            reasoning.append("No live local sandbox validation was run, and this workflow depends on more than basic documented media support.")
    else:
        reasoning.append("A local sandbox probe failed or could not complete, so confidence is reduced.")
    reasoning.append(f"Documented-only confidence ceiling for this posture: {ceiling:.2f}.")
    return confidence, reasoning
