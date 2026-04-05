# Phase 1 Calibration Update

## What changed

- Strengthened `Needs human review` so it now triggers more often for accessibility, audience-fit, public-use, operational simplicity, unattended/kiosk, branching, and live/integration-heavy briefs.
- Added explicit `Validation posture` classification:
  - `documented media workflow`
  - `configuration-heavy workflow`
  - `app/integration-risk workflow`
- Split report output between:
  - what the platform natively supports
  - what still requires content creation or experience design
- Lowered documented-only confidence ceilings, especially for configuration-heavy and app/integration-risk workflows when no live sandbox validation has run.
- Improved evidence precision by penalizing generic page chrome and preferring excerpts that directly mention the requested concept.
- Expanded the evaluation fixture set with harder briefs that should not collapse into a single verdict shape.

## Why

The earlier Phase 1 outputs were coherent but too uniform. They could correctly identify many feasible workflows, yet they often underplayed the difference between:

- supported runtime delivery
- content/design burden
- operational risk
- interactive/app behavior risk

This update keeps Phase 1 inside the same scope while making it more trustworthy for pilot use. The system is still answering feasibility questions, but it is now more explicit about when:

- format support is clear
- the workflow is configuration-heavy rather than simple
- the experience depends on app logic or external integration behavior
- human review is needed even though the underlying platform path is plausible

## Intended pilot effect

- fewer uniformly high-confidence `Supported with configuration` answers
- more `Needs human review` on briefs that make audience, accessibility, operational, or robustness claims
- clearer separation between low-risk documented media workflows and higher-risk interactive or integration-heavy workflows
- more practical reports that distinguish runtime support from the effort of actually making the experience good
