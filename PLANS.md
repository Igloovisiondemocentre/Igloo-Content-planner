# Igloo Experience Builder Pilot

## Summary

- Product name: `Igloo Experience Builder Pilot`
- Phase 1 name: `Experience Feasibility Copilot`
- Phase 1 is the first wedge of a broader internal-first product vision
- Phase 1 should be built quickly
- The 12-week period is for pilot validation, trust-building, KPI tracking, refinement, internal discussion, and phase-gate decisions, not just implementation
- Primary runtime source of truth: `https://api.igloovision.com/1.5.0/`
- Primary workflow/platform source of truth: `https://docs.igloovision.com/documentation/current`
- Internal PDFs are secondary evidence and must not override runtime truth

## 12-Week Pilot, Validation, and Phase-Gate Plan

### Weeks 1-2: rapid Phase 1 build and setup

- Build the first usable `Experience Feasibility Copilot` prototype quickly
- Deliver source inventory and snapshot pipeline for runtime API docs, platform docs, and internal PDFs
- Implement ingestion, taxonomy, deterministic retrieval, verdict generation, report generation, and initial sandbox discovery
- Define evidence ranking, freshness metadata, provenance capture, and decision logging
- Create:
  - `core_eval`: 30-50 real pre-sales briefs during pilot operation
  - `hero_eval`: 5-10 high-value briefs representing the long-term product vision

### Weeks 3-6: live pilot usage and evaluation

- Use the prototype on real pre-sales and demo-centre briefs
- Compare outputs against expert review and record misses or overstatements
- Refine `SupportPolicyEngine` rules so “possible” does not get mistaken for “supported”
- Improve evidence quality, reporting consistency, and next-step usefulness
- Track trust and pilot KPI signals

### Weeks 7-10: hardening and sandbox expansion

- Strengthen provenance and freshness handling
- Improve confidence scoring against evidence quality and sandbox findings
- Expand safe sandbox discovery and validation coverage without broadening Phase 1 scope
- Reduce false positives and overstated supportability

### Weeks 11-12: pilot review and phase-gate decision

- Review KPIs, expert agreement, and operational usefulness
- Perform failure analysis on weak or wrong answers
- Hold internal discussion on whether the pilot has earned progression to Phase 2
- Produce a go/no-go recommendation and entry criteria for blueprint authoring

## Phase 1 scope

Phase 1 only includes:

- source ingestion
- taxonomy
- deterministic evidence retrieval
- capability verdict generation
- report generation
- sandbox discovery and safe validation skeleton

Phase 1 explicitly excludes:

- autonomous content sourcing
- always-on orchestration
- transfer packaging
- UI automation
- session blueprint generation

## Key decision rules

- `SupportPolicyEngine` must distinguish:
  - technically possible
  - documented
  - supported for pre-sales / product use
  - risky / ambiguous
- The verdict set remains:
  - `Documented`
  - `Supported with configuration`
  - `Custom route`
  - `Unsupported`
  - `Unverified locally`
- Non-verdict operational state:
  - `Needs human review`
- Every answer must separate:
  - hard evidence
  - inference
  - local validation status
  - unresolved unknowns
- Sandbox wording must remain explicit:
  - sandbox success means “technically reproducible in this local environment”
  - sandbox success does not mean “ready to promise to a client”

## Decision log

### 2026-04-04

- Confirmed the runtime API source of truth is `api.igloovision.com/1.5.0`
- Confirmed the workflow/platform source of truth is `docs.igloovision.com/documentation/current`
- Confirmed internal PDFs are secondary evidence only
- Confirmed Phase 1 should stay narrow and focus on trusted feasibility answers before any blueprint generation
