# Final Phase 1 Reasoning Model

Phase 1 now keeps the stronger discrimination added during the pilot while making one practical correction from real Igloo use: some content and workflow classes are already known-working in normal documented Igloo use, so the system should not frame their baseline feasibility as doubtful just because a sandbox probe has not run.

## How the copilot now reasons

1. Platform capability
- `known working`: Igloo already supports this class of content or workflow in normal documented use.
- `unclear`: the building blocks are not clear enough from the retrieved evidence.
- `unsupported`: the retrieved evidence points away from support.

2. Exact item check
- Separates class-level support from the exact asset, link, model, URL, or app that still needs checking.
- This is where uncertainty now sits for common media workflows.

3. Workflow fit
- Separates “Igloo can run this class of thing” from “this actually fits the proposed operator, audience, and session flow.”

4. Control / interaction fit
- Distinguishes straightforward media/session delivery from interaction-heavy asks where control behavior matters more than simple display.

## Known-working baseline classes

For normal documented use, Phase 1 now treats these as baseline known-working platform classes when supported by the main product/runtime knowledge in the repo:

- standard video
- 360 video
- YouTube 360
- PDF
- images
- standard website / WebView content
- saved sessions
- Content Bank switching
- Home layer launching
- common model-viewer / common 3D model workflows
- standard prepared assets in expected formats

This does not mean every exact item is guaranteed. It means the main question becomes:

- does this exact file / link / model behave correctly?
- does it fit the proposed session or operator flow?
- are the controls simple enough for the intended experience?

## Contextual workflow priors

Phase 1 now also uses contextual workflow priors from Igloo's case studies, video gallery, and public LinkedIn examples.

These priors help the copilot recognise practical, already-common Igloo scenarios such as:

- immersive classrooms and repeatable teaching sessions
- heritage and exhibition storytelling
- AECO model review and collaborative design sessions
- hybrid workshops using live/shared content
- guided public-facing experiences with simple interactive reveals

These priors do not count as runtime truth and do not override the main support-policy layer.
They are used only to improve:

- route suggestions
- workflow-fit judgment
- control-fit judgment
- overall practical understanding of what an actual Igloo deployment often looks like

## Where Phase 1 still stays cautious

The copilot keeps the stronger caution already added for:

- WebXR or app-like workflows
- complex Triggers and Actions graphs
- live or hybrid integrations
- branching or stateful experiences
- unattended or kiosk-like public interaction
- requests where control behavior matters more than straightforward playback
- one-prompt or autonomous-generation asks outside the Phase 1 boundary

These cases should still lean more heavily on:

- `Needs human review`
- `Custom route`
- `Unsupported`
- lower confidence when the experience depends on external app logic or complex behavior

## What changed in report semantics

The report now makes it easier to say:

- “Yes, Igloo already supports this type of content. The main thing to check is whether this exact file, link, or model behaves as expected.”
- “Yes, this generally works in Igloo, but the controls or interaction flow need review.”
- “The platform building blocks are there, but the full ask goes beyond a straightforward configuration-led setup.”

That keeps the good distinction between:

- building-block support
- exact-item compatibility
- workflow fit
- control / interaction fit
- end-to-end supportability
