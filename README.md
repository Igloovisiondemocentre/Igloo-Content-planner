# Igloo Experience Builder Pilot

`Igloo Experience Builder Pilot` is a local-first Python project for the first wedge of a broader internal product vision. Phase 1 is the `Experience Feasibility Copilot`: a CLI that ingests the Igloo Core Engine runtime API docs, Igloo workflow/platform docs, and secondary internal PDFs, then returns an evidence-backed feasibility verdict with provenance, confidence, risks, and next steps.

The codebase is intentionally narrow. Phase 1 only covers:

- source ingestion
- taxonomy
- deterministic evidence retrieval
- capability verdict generation
- report generation
- sandbox discovery and safe validation skeleton
- lightweight pilot evaluation workflows
- read-only local install discovery for nearby sandbox files

It does not attempt blueprint generation, content sourcing, transfer packaging, UI automation, or always-on orchestration.

## Source hierarchy

- Primary runtime truth: `https://api.igloovision.com/1.5.0/`
- Primary workflow/platform truth: `https://docs.igloovision.com/documentation/current`
- Secondary evidence only: local internal PDFs such as the Buyer's Guide and pre-sales packs

The support-policy layer exists to prevent the system from calling something "supported" only because an API path exists.
The local install discovery layer is read-only and discovery-only; it does not write to the nearby Igloo Core Engine install.

## Quickstart

1. Create a virtual environment and activate it.
2. Install the package:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

3. Copy `.env.example` to `.env` if you want to tune source limits or enable a local sandbox probe.

For a local Igloo Core Engine sandbox running on the same machine, the practical starting point is:

```env
IGLOO_LOCAL_INSTALL_ROOT=C:\igloo\igloo-core-service
IGLOO_SESSION_LIBRARY_ROOTS=C:\Users\AshtonKehinde\OneDrive - igloovision\Desktop
IGLOO_SANDBOX_HOST=127.0.0.1
IGLOO_SANDBOX_PORT=800
IGLOO_SANDBOX_TRANSPORT=http
IGLOO_SANDBOX_TIMEOUT_SECONDS=4.0
IGLOO_SANDBOX_ENABLE_WRITE_PROBES=false
```

4. Run the CLI:

```powershell
igloo-experience-builder health-check
igloo-experience-builder discover-api
igloo-experience-builder ask "Can Igloo display a PDF, website, and video in one reusable session?"
igloo-experience-builder evaluate
igloo-experience-builder report last
igloo-experience-builder builder-ui
```

## Output model

Every answer separates:

- hard evidence
- inference
- validation posture
- what the platform natively supports
- what still requires content creation or experience design
- proposed build approach
- local validation status
- unresolved unknowns

The proposed build approach is intentionally explicit about:

- likely runtime surfaces inside Igloo
- likely upstream authoring tools such as PowerPoint, Canva, websites, or custom web apps
- alternative implementation routes such as named integrations when the evidence supports them
- whether interaction would require a custom web layer
- what content assumptions still need human confirmation

Confidence is tied to source quality, freshness, evidence strength, and sandbox outcome. It is not based only on model judgment.
The classifier now also distinguishes:

- `documented media workflow`
- `configuration-heavy workflow`
- `app/integration-risk workflow`

This keeps straightforward documented format support separate from workflows whose actual success depends on trigger logic, external apps, live integrations, audience-fit assumptions, accessibility design, or operational robustness.

If the sandbox is configured and responds, the report still uses this warning:

> Sandbox success means technically reproducible in this local environment. It does not mean ready to promise to a client.

## Repo layout

- `PLANS.md`: living roadmap and decision log
- `config/source_manifest.json`: Phase 1 source manifest and crawl hints
- `docs/`: taxonomy, support-policy notes, pilot metrics, source inventory, and pilot review template
- `src/igloo_experience_builder/`: implementation
- `tests/evals/`: evaluation seeds and hero briefs
- `evidence/`: generated indices, reports, decisions, and evaluation summaries

## Phase 1 commands

### `health-check`

Verifies:

- source reachability
- local PDF presence
- index presence
- optional sandbox configuration and safe read-only probe
- read-only discovery of a nearby local Igloo Core Engine install when present

### `discover-api`

Builds or reuses the local evidence index, then reports:

- discovered runtime API sections
- optional read-only sandbox probe result, including the live HTTP surfaces when configured
- read-only local install metadata such as detected config, ports, layer files, and recent logs
- read-only saved-session summaries when `.iceSession` files are found in the configured or default session-library roots

### `ask "<question>"`

Builds or reuses the local evidence index, retrieves matching evidence, applies the support-policy engine, and writes:

- `evidence/reports/last_report.md`
- `evidence/decisions/last_assessment.json`

### `evaluate [files...]`

Batch-runs saved briefs for pilot evaluation. If no files are provided, it uses:

- `tests/evals/core_eval_seed.json`
- `tests/evals/hero_eval.json`

For each brief it outputs:

- verdict
- confidence
- evidence count
- human-review flag
- unresolved unknown count

It also writes summary artifacts under `evidence/evaluations/` with:

- verdict distribution
- average confidence
- count of `Needs human review`
- count of `Unverified locally`

### `report last`

Prints the most recent generated report.

## Phase 2 builder wedge

The first Phase 2 implementation is a local mixed-media session builder UI.

Launch it with:

```powershell
igloo-experience-builder builder-ui
```

Optional flags:

```powershell
igloo-experience-builder builder-ui --port 8766
igloo-experience-builder builder-ui --no-browser
```

Current wedge capabilities:

- start from a brief and generate an initial preview template
- import a real `.iceSession` file and inspect its session/layer structure
- view a compact assessment summary pulled from Phase 1
- review selected content and per-item readiness
- switch between flat preview, structure preview, and layer map
- choose a target Igloo structure profile
- auto-search planned content slots from the current draft
- search for candidate content through YouTube 360, websites, or WebXR discovery
- keep direct links, provider metadata, and thumbnails on selected content where available
- suggest a more relevant room structure from the brief when the current selection is still generic
- export a draft session package under `evidence/session_packages/`
- save the current builder draft locally under `evidence/builder_drafts/`

Optional richer search integration:

- set `YOUTUBE_API_KEY` in `.env` to use the YouTube Data API for stronger YouTube 360 search
- set `OPENAI_API_KEY` to enable the structured brief-to-query planner for cleaner natural-language search intent extraction
- set `OPENAI_QUERY_PLANNER_MODEL` to choose the planner model, default `gpt-4.1-mini`
- set `GOOGLE_MAPS_API_KEY` to enable a future geocoding-backed place-normalization layer for search anchors
- set `MAPBOX_ACCESS_TOKEN` if you later want external place normalization for geographic search anchors
- set `SERPAPI_API_KEY` if you later want stronger interactive-web, model, and dashboard discovery beyond the built-in search paths

The UI is intentionally still a narrow Phase 2 wedge. The generated session package is a practical draft starting point, not a guaranteed production-ready room export, and it still does not write into the sandbox install.

## Pilot review workflow

- Run `igloo-experience-builder evaluate` on the saved brief sets.
- Review the batch summary in `evidence/evaluations/last_evaluation.md`.
- Compare agent output with expert review using [pilot_evaluation.md](C:/igloo/igloo-core-service/Igloo Agent/docs/pilot_evaluation.md).

## Nearby local install support

If this project sits alongside a local Igloo Core Engine install, `health-check` and `discover-api` now surface a read-only summary of nearby install artifacts. By default the tool looks at the parent folder first, and you can override that with `IGLOO_LOCAL_INSTALL_ROOT`.

The discovery output is intentionally limited to metadata such as:

- whether `igloo-core-service.exe`, `config.json`, logs, layers, and the local database exist
- port configuration and controller client endpoints
- content folder paths and installed layer/log file names
- saved `.iceSession` files found in likely user workspace folders, plus whether they were exported with assets
- whether optional API keys appear configured, without printing the secret values

When the sandbox is configured on an HTTP control surface such as `127.0.0.1:800`, the CLI also attempts a read-only live source snapshot through Socket.IO after `ics-ready`. This remains non-destructive and is only used to confirm what the running sandbox is actively exposing.

If you want the CLI to look in specific user folders for real saved sessions, set `IGLOO_SESSION_LIBRARY_ROOTS` as a semicolon-separated list of roots to scan.

## Planned pilot path

The first usable Phase 1 version should be built quickly. The rest of the 12-week pilot is for validation, trust-building, KPI tracking, refinement, and the Phase 2 go/no-go decision. The current implementation is aligned to that wedge and not to the later blueprint-building phases.
