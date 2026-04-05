# Phase 2 Builder Research Note

This pass tightened the builder around real client-facing immersive use rather than generic software-demo advice.

## What changed in the reasoning

- Education / classroom briefs now bias toward:
  - one immersive hook
  - guided teaching beats
  - a small number of reveal or interaction moments
  - a clear reset path
- AECO briefs now bias toward:
  - one primary model-review surface first
  - secondary states for markups, dashboards, or comparison views
  - controlled hybrid/collaboration moments instead of everything running at once
- Heritage / museum / storytelling briefs now bias toward:
  - one strong scene
  - supporting archive or reference content
  - sparse operator switching
- Health and safety / immersive training briefs now bias toward:
  - explicit learning objective
  - scenario or hazard-driven beats
  - planned debrief and replay

## Search and content-finding upgrades

- The builder now supports optional YouTube Data API search via `YOUTUBE_API_KEY`.
- It can auto-search all planned content slots from the current draft instead of waiting for manual search prompts.
- It now stores direct links, thumbnails, provider/source metadata, and stronger match scores on chosen content.
- NASA education content is treated as a useful contextual source when the brief clearly points there.

## First draft session-package export

- The builder can now write a draft session package folder under `evidence/session_packages/`.
- Each package contains:
  - a draft `.iceSession` file
  - an `assets/` folder
  - `.url` shortcuts for selected web content
  - placeholder files where the asset is still missing
  - `package_manifest.json`
  - a short README

This is a practical starting point, not a guarantee that the exported session is immediately room-ready.

## External sources used as planning/context priors

- Igloo case studies:
  - [Case studies](https://www.igloovision.com/case-studies)
- Igloo installation and workflow patterns:
  - [What makes for an effective installation?](https://www.igloovision.com/Documents/Igloo%20effective%20installations.pdf)
- Igloo immersive education / medical learning example:
  - [Med Learning Group case study](https://www.igloovision.com/Documents/Med_Learning_Group_CaseStudy.pdf)
- AECO / Revizto workflow context:
  - [Autodesk University / Revizto coordination material](https://static.au-uw2-prd.autodesk.com/Additional_Class_Materials_SD135598-L_Revizto__Reducing_RFI_by_50_with_better_virtual_construction_Mark_Ciszewski_1.pdf)
- YouTube content-search integration:
  - [YouTube Data API search.list](https://developers.google.com/youtube/v3/docs/search/list)

These sources are used as planning priors and workflow context, not as replacements for the runtime/platform source of truth already used by the project.
