from __future__ import annotations

from igloo_experience_builder.models import CapabilityAssessment


class ReportGenerator:
    def to_markdown(self, assessment: CapabilityAssessment) -> str:
        def add_bullets(lines: list[str], values: list[str], default: str = "None") -> None:
            if values:
                lines.extend(f"- {value}" for value in values)
            else:
                lines.append(f"- {default}")

        lines = [
            "# Experience Feasibility Copilot Report",
            "",
            "## Request",
            assessment.request,
            "",
            "## Verdict",
            assessment.verdict.value,
            "",
            "## Operational flags",
        ]
        if assessment.operational_flags:
            lines.extend(f"- {flag.value}" for flag in assessment.operational_flags)
        else:
            lines.append("- None")
        lines.extend(["", "## Confidence", f"{assessment.confidence:.2f}"])
        add_bullets(lines, assessment.confidence_reasoning)
        lines.extend(["", "## Why"])
        add_bullets(lines, assessment.why)
        lines.extend(["", "## Hard evidence"])
        if assessment.hard_evidence:
            lines.extend(
                f"- [{citation.source_type.value}] {citation.title} | {citation.location} | "
                f"{citation.evidence_strength.value} | {citation.freshness_status.value}\n"
                f"  Excerpt: {citation.excerpt}"
                for citation in assessment.hard_evidence
            )
        else:
            lines.append("- None")
        lines.extend(["", "## Inference"])
        add_bullets(lines, assessment.inference)
        lines.extend(["", "## Practical fit assessment"])
        lines.append(f"- Platform capability: {assessment.build_approach.platform_capability}")
        lines.append(f"- Exact item check: {assessment.build_approach.exact_item_check}")
        lines.append(f"- Workflow fit: {assessment.build_approach.workflow_fit}")
        lines.append(f"- Control / interaction fit: {assessment.build_approach.control_interaction_fit}")
        if assessment.build_approach.practical_summary:
            lines.extend(["", "## Practical read", assessment.build_approach.practical_summary])
        lines.extend(["", "## Validation posture"])
        lines.append(f"- Validation posture: {assessment.build_approach.validation_posture}")
        lines.append(f"- Format support confidence: {assessment.build_approach.format_support_confidence}")
        lines.append(f"- Configuration burden: {assessment.build_approach.configuration_burden}")
        lines.append(f"- Experience risk: {assessment.build_approach.experience_risk}")
        lines.append(f"- Review requirement: {assessment.build_approach.review_requirement}")
        lines.extend(["", "## Comparable documented use-case patterns"])
        add_bullets(lines, assessment.build_approach.use_case_alignment)
        lines.extend(["", "## What the platform natively supports"])
        add_bullets(lines, assessment.build_approach.native_platform_support)
        lines.extend(["", "## What still requires content creation or experience design"])
        add_bullets(lines, assessment.build_approach.content_design_requirements)
        lines.extend(["", "## Proposed build approach"])
        lines.append(f"- Implementation kind: {assessment.build_approach.implementation_kind}")
        lines.append(f"- Route confidence: {assessment.build_approach.route_confidence}")
        if assessment.build_approach.needs_human_review:
            lines.append("- Build route itself needs human review.")
        lines.extend(["", "### Runtime surfaces"])
        add_bullets(lines, assessment.build_approach.runtime_surfaces)
        lines.extend(["", "### Authoring tools / content prep"])
        add_bullets(lines, assessment.build_approach.authoring_tools)
        lines.extend(["", "### Alternative routes / integrations"])
        add_bullets(lines, assessment.build_approach.candidate_routes)
        lines.extend(["", "### Interaction model"])
        add_bullets(lines, assessment.build_approach.interaction_model)
        lines.extend(["", "### Content assumptions"])
        add_bullets(lines, assessment.build_approach.content_assumptions)
        lines.extend(["", "### Custom work items"])
        add_bullets(lines, assessment.build_approach.custom_work_items)
        lines.extend(["", "### Build unknowns"])
        add_bullets(lines, assessment.build_approach.build_unknowns)
        lines.extend(["", "## Suggested implementation route", assessment.recommended_implementation_route])
        lines.extend(["", "## Local validation status", f"- {assessment.local_validation_status.summary}"])
        add_bullets(lines, assessment.local_validation_status.details)
        lines.append(f"- {assessment.local_validation_status.disclaimer}")
        lines.extend(["", "## Dependencies"])
        add_bullets(lines, assessment.dependencies)
        lines.extend(["", "## Risks / unknowns"])
        add_bullets(lines, assessment.risks)
        lines.extend(["", "## Unresolved unknowns"])
        add_bullets(lines, assessment.unresolved_unknowns)
        lines.extend(["", "## Recommended next step", assessment.recommended_next_step, ""])
        return "\n".join(lines)
