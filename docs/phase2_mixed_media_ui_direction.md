# Phase 2 UI Direction: Mixed-Media Session Builder

## Goal

The first Phase 2 wedge should not be a generic chat window.
It should be a clear local-first builder for a reusable mixed-media Igloo session.

The operator should be able to:

- start from a brief
- see the current feasibility verdict
- see what content is proposed for the session
- inspect whether each content item is actually usable
- swap content in and out
- ask the system to find better content
- preview the session in a flat view or against a chosen Igloo structure
- understand the main risks without reading long walls of text

## What the UI should feel like

Do not build this as a basic AI tool shell.
Do not make the user read long markdown reports in the main workspace.

The right feel is closer to:

- a creative review tool
- a content curation workspace
- a session inspector
- a lightweight control-room prep surface

The interface should feel:

- visual first
- status rich
- sparse with words
- clear about what is selected, what is missing, and what needs review

## Visual direction from Igloo's public site

Using the public site and CSS as reference:

- primary dark: `rgb(0, 32, 50)` / `#002032`
- core blue: `#0063DC`
- brighter blue accent: `#285AEB`
- cyan accent: `#1AB7EA`
- aqua highlight: `#38DEDF`
- white: `#FFFFFF`

The site also uses Adobe Typekit-hosted `proxima-nova`.

Recommended application palette:

- page background: deep navy or blue-black
- content surfaces: darker raised panels with soft contrast
- primary action: Igloo blue
- supporting highlight: cyan / aqua
- caution: warm amber, not aggressive red by default
- error or blocked state: restrained red only for real incompatibility

Design guidance:

- keep the interface dark and cinematic so content previews feel natural
- use white and pale blue text, but do not make everything neon
- use one vivid accent at a time
- let media thumbnails and previews carry some of the visual energy

## Research-backed interaction principles

These patterns showed up repeatedly in enterprise and content-heavy UX references:

- progressive disclosure for complex workflows
- preview-first search results
- strong filtering and pre-applied category filters
- visible status metadata near each result
- minimal prose on the main page
- deeper detail available on demand, not all at once

Useful references:

- [NN/g Mobile Intranets and Enterprise Apps](https://media.nngroup.com/media/reports/free/Mobile_Intranets_and_Enterprise_Apps.pdf)
  - progressive disclosure
  - intermediate validation
  - guided workflow
- [NN/g Intranet Design Annual 2016](https://media.nngroup.com/media/reports/free/Intranet_Design_Annual_2016.pdf)
  - document previews
  - filters
  - result metadata
- [NN/g Intranet Design Annual 2021](https://media.nngroup.com/media/reports/free/Intranet_Design_Annual_2021.pdf)
  - category buttons leading to prefiltered results
  - result previews and modified-date context

## Igloo product context that should shape the UI

Public Igloo sources show that the product already spans multiple structures and use cases:

- [Igloo homepage](https://www.igloovision.com/)
- [Case studies](https://www.igloovision.com/case-studies)
- [Video gallery](https://www.igloovision.com/about/video-gallery)
- [Cylinders, cubes, and domes](https://www.igloovision.com/immersive-workspaces/cylinders-cubes-domes)

These sources reinforce that the UI should support:

- immersive workspaces
- CAVEs
- cylinders
- cubes
- domes
- retrofits or adapted rooms

They also reinforce common content and workflow classes:

- standard video
- 360 image and 360 video
- YouTube 360
- PDF
- WebView content
- Revizto
- Unity plug-in workflows
- Google Street View
- Power BI
- hybrid and collaborative sessions

## Core UI model

The Phase 2 UI should answer four questions at all times:

1. What are we trying to build?
2. What content is currently selected?
3. Is that content actually ready and compatible?
4. How will it play inside the chosen Igloo structure?

## Recommended top-level layout

Use a three-panel workspace with a compact header and a bottom action strip.

### Header

Keep this shallow and always visible:

- project / brief title
- overall build readiness score
- verdict chip
- `Needs human review` chip if present
- structure toggle
- primary actions:
  - `Find content`
  - `Import session`
  - `Save draft`

### Left panel: brief and build plan

Keep this as the decision panel.

Show:

- brief summary
- chosen use-case pattern
- top recommended route
- key status chips:
  - platform capability
  - exact item check
  - workflow fit
  - control fit
  - validation posture
- top 3 dependencies
- top 3 unknowns

This panel should use cards and chips, not paragraphs.

### Center panel: preview workspace

This is the heart of the interface.

Modes:

- `Flat preview`
- `Structure preview`
- `Layer map`

The default should be `Flat preview`.

#### Flat preview

Use for quick review of:

- video
- PDF
- website screenshot
- image
- content stack order

#### Structure preview

This should start simple.

Phase 2 first version should use a schematic toggle, not a fully realistic room simulator:

- immersive workspace
- CAVE
- cylinder
- cube
- dome
- retrofit room

The preview can begin as:

- a flat projection map
- a simplified room outline
- a placement overlay showing what content is likely to dominate the experience

Later, this can become a true 3D preview.

#### Layer map

Show the eventual session as cards or horizontal tracks:

- background layer
- media layers
- WebView layers
- overlay or trigger layers
- Home or Content Bank launch paths

This should make the build feel real before export exists.

### Right panel: content and inspector

Use tabbed panels:

- `Selected content`
- `Found content`
- `Inspector`
- `Evidence`

#### Selected content

This should be the main working list.

Each selected content card should show:

- thumbnail or icon
- content title
- content type
- source
- readiness badge
- exact item status
- remove
- replace
- inspect

#### Found content

This is where exact-content search results should land.

#### Inspector

This is for the currently selected item or layer.

Show concise facts:

- file or URL
- resolution
- duration
- 360 or flat
- subtitle status
- audio status
- host or local
- likely layer type
- known support class
- risks

#### Evidence

Do not show full reports by default.
Show only:

- 2 or 3 best evidence snippets
- a link to full report details

## Content readiness model

This is the most important UI improvement beyond Phase 1.

Do not rely only on one overall feasibility score.
The UI needs both:

- an overall build readiness score
- a per-item content readiness status

### Overall build readiness

Suggested dimensions:

- platform support
- exact item quality
- configuration burden
- workflow fit
- control risk
- missing content burden

### Per-item readiness

Each content item should be scored against:

- supported class
- exact item compatibility
- resolution and quality
- hosting or local availability
- playback suitability
- subtitle or accessibility readiness where relevant
- likely structure fit

Suggested statuses:

- ready
- usable with prep
- needs checking
- poor fit
- blocked

## Search and content acquisition UX

The UI should support both:

- `I already have content`
- `Find content for me`

### Search entry points

Add a `Find content` drawer or modal with source tabs:

- local files
- YouTube / YouTube 360
- websites
- WebXR experiences
- known integrations

### Search result cards

Each result should show:

- preview thumbnail
- title
- source site
- content type
- resolution
- duration if video
- 360 / non-360
- hosted / downloadable
- support route
- add button

### Important rule for 360 search

For public 360 content, do not treat the first plausible result as good enough.

The search UX should support filters for:

- `360 only`
- `4K+ only`
- subtitles preferred
- hosted vs local-prep route
- duration range

If the system cannot confirm real resolution, it should say so clearly instead of pretending.

### WebXR search

WebXR content should be shown in a separate risk class.
Even if a candidate looks good, the UI should tag it as:

- `app/integration-risk workflow`

This keeps exact content discovery and support-policy logic aligned.

## Allowing users to remove and replace content

This is essential.

Every selected content card should support:

- remove
- replace
- pin
- ask AI to find better
- ask AI to find a local alternative
- ask AI to find a 4K 360 alternative

This should feel like curating a playlist or moodboard, not editing raw JSON.

## What should come through from Phase 1 reports

Do not dump the full report on screen.
Pull forward only the most decision-useful parts:

- verdict
- confidence
- `Needs human review`
- validation posture
- platform capability
- exact item check
- workflow fit
- control / interaction fit
- top evidence count
- top dependencies
- top unresolved unknowns
- recommended route

These should appear as compact chips, cards, and expandable drawers.

## What the Quiddiya `.iceSession` file tells us

The example session is useful because it proves the editor will eventually need to represent real session mechanics, not just loose content ideas.

Important session concepts visible in the file:

- session metadata
  - id
  - name
  - thumbnail
  - exported-with-assets flag
- layer list
- per-layer type
  - example: `Video`
- file path
- loop / autoplay
- audio volume / mute / delay
- UI widget position
- crop / wrap / scale
- render passes
  - example: `PerspectiveExtraction`
- perspective settings
- custom head / stretch / shader settings

This means the eventual UI needs at least three levels:

- experience-level planning
- layer-level session composition
- low-level media and render inspection

Important note:

The file looks XML-like, but the sample also suggests import may need to be tolerant rather than strict.
That means the future session import flow should:

- parse defensively
- show warnings instead of just failing
- preserve unknown fields where possible

## Strong recommendation for the actual UI technology

Do not build the main product UI in Gradio or Streamlit.
They are fine for experiments, but they are too limiting for the kind of polished, inspectable, content-heavy builder you want.

Recommended direction:

- Python backend for the agent, scoring, parsing, and search orchestration
- local web app frontend for the actual builder experience

The frontend should support:

- fast previews
- inspector panels
- drag/reorder interactions
- chips and status badges
- strong layout control
- room/structure preview switching

## Smallest credible Phase 2 UI wedge

Do not start by trying to build the full end-state program.

Build this first:

1. Brief-to-build workspace for the mixed-media reusable session case
2. Selected-content panel with per-item readiness
3. `Find content` drawer with YouTube 360 and website search hooks
4. Flat preview plus simple structure toggle
5. Session/layer outline view
6. Assessment summary chips from Phase 1

That is enough to prove:

- the copilot can move from verdict to draft build plan
- the operator can review and change content
- the UI presents the session clearly
- the system is useful before full export/generation exists

## Immediate implementation recommendation

Before coding the UI itself, define these internal objects clearly:

- `ExperienceDraft`
- `ContentCandidate`
- `SelectedAsset`
- `ReadinessCheck`
- `StructureProfile`
- `LayerDraft`
- `SessionImportSummary`

Then build the UI around those objects rather than around raw reports or raw session XML.

That will keep the Phase 2 builder clean and extensible.
