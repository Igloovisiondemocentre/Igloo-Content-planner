from __future__ import annotations

from igloo_experience_builder.knowledge.taxonomy import KNOWN_WORKING_BASELINE_CONCEPTS, request_concepts
from igloo_experience_builder.knowledge.text_utils import collapse_capitalized_artifacts, normalize_whitespace
from igloo_experience_builder.models import BuildApproach, RankedEvidence, SupportPolicyDecision

ROUTE_CONFIDENCE_ORDER = {"concrete": 0, "partial": 1, "speculative": 2}

LOW_RISK_MEDIA_CONCEPTS = {
    "session",
    "layer",
    "360_content",
    "content_bank",
    "home",
    "audio",
    "webview",
    "pdf",
    "website",
    "video",
    "playback",
    "content_library",
    "local_workflow",
    "image",
    "model_viewer",
}

KNOWN_WORKING_PLATFORM_CONCEPTS = KNOWN_WORKING_BASELINE_CONCEPTS

ITEM_SENSITIVE_CONCEPTS = {
    "video",
    "360_content",
    "pdf",
    "image",
    "website",
    "webview",
    "model_viewer",
}

NARRATIVE_HINTS = {"storytelling", "narrative", "heritage", "education", "showroom", "training", "simulation", "event", "museum", "demo-centre", "demo centre"}
INTERACTION_HINTS = {"interactive", "interact", "icon", "icons", "trigger", "triggers", "action", "actions", "button", "buttons", "workspace", "workspaces", "home", "content bank", "tile", "tiles", "menu", "launch"}
HOTSPOT_HINTS = {"hotspot", "hotspots", "overlay", "overlays", "clickable", "info popup", "info popups", "popup", "popups", "tap", "taps", "reveal", "reveals", "on-screen object", "on-screen objects"}
BESPOKE_WEB_HINTS = {"web app", "custom app", "custom web", "bespoke", "microsite", "web form", "custom form", "survey"}
NEGATED_CUSTOM_APP_HINTS = {"no custom app", "no custom web", "no bespoke app", "without a custom app", "no custom app preferred"}
ACCESSIBILITY_HINTS = {"accessible", "accessibility", "inclusive", "wheelchair", "mobility", "neurodiverse", "subtitles", "subtitle", "captions", "caption", "low cognitive load", "inclusion"}
AUDIENCE_HINTS = {"audience", "audiences", "audience-fit", "audience fit", "visitor", "visitors", "school group", "school groups", "children", "older adults", "public use", "public-use", "public facing", "public-facing", "public safe", "public-safe", "visitor suitability"}
OPERATIONAL_REVIEW_HINTS = {"easy", "simple", "simplicity", "intuitive", "operator-light", "operator light", "operator simplicity", "operator-friendly", "low maintenance", "low-maintenance", "unattended", "kiosk", "restart cleanly", "reset cleanly", "reset behavior", "robust", "no custom content required"}
NAVIGATION_HINTS = {"navigation", "navigate", "simplified navigation", "simple navigation", "guided", "guided flow", "low cognitive load"}
SWITCHING_HINTS = {"switch", "switching", "switchable", "adaptable", "reusable", "repeatable", "multi-use", "multi use", "future-proof", "future proof", "multi-audience", "multi audience"}
SCENARIO_SWITCHING_HINTS = {
    "switch",
    "switching",
    "switchable",
    "adaptable",
    "multi-use",
    "multi use",
    "future-proof",
    "future proof",
    "multi-audience",
    "multi audience",
    "scenario",
    "scenarios",
    "workspace",
    "workspaces",
    "section",
    "sections",
    "menu",
}
TRAINING_HINTS = {"training", "education", "learning", "school", "classroom", "simulation", "vr training", "hazard", "high-hazard", "interactive vr", "scenario"}
MODEL_HINTS = {"aeco", "architecture", "architectural", "design review", "bim", "revit", "revizto", "autodesk", "dwg", "3d model", "3d models", "model review", "model viewer", "digital twin", "point cloud", "onshape"}
TOUR_HINTS = {"virtual tour", "site walk", "site walkthrough", "tour", "street view", "streetview", "safari"}
COMPLEX_INTERACTION_HINTS = {"branching", "branch", "branches", "decision", "decisions", "vote", "votes", "outcome", "outcomes", "multi-state", "multistate", "interactive journey"}
LIVE_INTEGRATION_HINTS = {"live", "real-time", "real time", "dashboard", "dashboards", "camera", "feed", "teams", "remote participants", "hybrid", "comparison layout", "comparison layouts", "markups", "markup", "collaborative", "remote"}
APP_RISK_HINTS = {"webxr", "webgl", "unity", "unreal", "multi-user"}
OPERATOR_LED_HINTS = {"operator-driven", "operator driven", "operator-run", "operator run"}
PUBLIC_USE_HINTS = {"unattended", "kiosk", "public-facing", "public facing"}
SIMPLE_REVEAL_HINTS = {"tap", "taps", "reveal", "reveals", "large on-screen", "on-screen object", "on-screen objects"}
HERITAGE_USE_CASE_HINTS = {"heritage", "historic", "history", "museum", "archive", "archival", "exhibition", "storytelling"}
EDUCATION_USE_CASE_HINTS = {"education", "classroom", "school", "student", "students", "teacher", "teachers", "curriculum", "learning"}
AECO_USE_CASE_HINTS = {"aeco", "architecture", "architectural", "bim", "revit", "revizto", "revistoo", "autodesk", "navisworks", "design review", "markups", "markup", "comparison layout", "comparison layouts"}
HYBRID_COLLABORATION_HINTS = {"collaboration", "collaborative", "hybrid", "teams", "remote participants", "dashboard", "dashboards", "workshop", "operator-driven", "operator driven", "operator-run", "operator run", "ndi"}
STRUCTURE_TYPE_HINTS = {"cylinder", "cube", "dome", "domes", "cave", "caves", "immersive workspace", "retrofit", "custom build", "custom retrofit"}
GENERATIVE_ASSEMBLY_LIMIT_HINTS = {"one prompt", "text prompt", "fully ai-generated", "fully ai generated", "no human content prep", "automatically"}


class BuildApproachPlanner:
    def plan(self, question: str, evidence: list[RankedEvidence], policy: SupportPolicyDecision) -> BuildApproach:
        normalized = normalize_whitespace(question).lower()
        concepts = request_concepts(question)
        evidence_titles = " ".join(item.fragment.title.lower() for item in evidence[:12])
        evidence_text = collapse_capitalized_artifacts(" ".join(item.fragment.text for item in evidence[:12])).lower()
        evidence_surface = f"{evidence_titles} {evidence_text}"

        has_triggers_actions = self._contains_any(
            evidence_surface,
            {
                "triggers and actions",
                "trigger tile",
                "layout tile",
                "active tile",
                "go home",
                "set url",
                "session loaded",
                "layer selected",
                "layer deselected",
                "generic igloo core engine message",
            },
        )
        has_content_bank = "content bank" in evidence_surface
        has_home_controls = self._contains_any(evidence_surface, {"home layer", "home layout", "home components", "go home"})
        has_true_perspective = self._contains_any(evidence_surface, {"true perspective", "custom head position", "head positions", "true perspective manager"})
        has_audio_support = self._contains_any(evidence_surface, {"audio window", "set volume", "audio file", "audio files", "5.1", "surround"})
        has_youtube_360_route = "youtube 360" in evidence_surface
        has_thinglink_route = "thinglink" in evidence_surface
        has_ndi_route = self._contains_any(evidence_surface, {"ndi", "canvas sharing", "video conferencing", "teams", "zoom"})
        negates_custom_app = self._contains_any(normalized, NEGATED_CUSTOM_APP_HINTS)
        requests_complex_control = self._contains_any(
            normalized,
            HOTSPOT_HINTS
            | COMPLEX_INTERACTION_HINTS
            | LIVE_INTEGRATION_HINTS
            | {"interactive", "clickable", "tap", "taps", "icon", "icons", "button", "buttons", "trigger", "triggers", "action", "actions"},
        )

        runtime_surfaces: list[str] = []
        native_platform_support: list[str] = []
        content_design_requirements: list[str] = []
        authoring_tools: list[str] = []
        candidate_routes: list[str] = []
        interaction_model: list[str] = []
        content_assumptions: list[str] = []
        custom_work_items: list[str] = []
        build_unknowns: list[str] = []
        use_case_alignment: list[str] = []

        implementation_kind = "configuration"
        route_confidence = "concrete"
        needs_human_review = policy.needs_human_review
        matches_heritage_pattern = self._contains_any(normalized, HERITAGE_USE_CASE_HINTS)
        matches_education_pattern = self._contains_any(normalized, EDUCATION_USE_CASE_HINTS)
        matches_aeco_pattern = self._contains_any(normalized, AECO_USE_CASE_HINTS)
        matches_hybrid_pattern = self._contains_any(normalized, HYBRID_COLLABORATION_HINTS | LIVE_INTEGRATION_HINTS)
        matches_public_pattern = self._contains_any(normalized, PUBLIC_USE_HINTS | {"visitor", "visitors", "children", "older adults"})
        matches_simple_public_interaction = matches_public_pattern and self._contains_any(normalized, SIMPLE_REVEAL_HINTS | HOTSPOT_HINTS) and not self._contains_any(normalized, COMPLEX_INTERACTION_HINTS)

        if "session" in concepts or self._contains_any(normalized, {"reusable", "repeatable", "session"}):
            runtime_surfaces.append("Assemble the experience as a saved Igloo session so an operator can relaunch it consistently.")
            native_platform_support.append("Igloo can save prepared layers as sessions and relaunch them later.")
            interaction_model.append("Use Canvas UI or the Home layer to launch the prepared session during the demo.")
            build_unknowns.append("The exact session structure and relaunch flow still need to be chosen for the target operator journey.")

        if "pdf" in concepts:
            runtime_surfaces.append("Use a WebView layer to display a local or hosted PDF document.")
            native_platform_support.append("Igloo can display PDF documents through a WebView workflow.")
            authoring_tools.append("Prepare documents in a PDF-capable authoring tool such as PowerPoint or Canva, then export to PDF before loading them into Igloo.")
            content_assumptions.append("The PDF must exist on the media player or at a reachable URL.")
            content_design_requirements.append("The PDF still needs to be authored, exported, and laid out for in-room readability.")
            build_unknowns.append("The exact PDF source, hosting path, and display scale still need to be confirmed.")

        if "image" in concepts or self._contains_any(normalized, {"image", "images", "still image", "jpg", "jpeg", "png"}):
            runtime_surfaces.append("Use an image-capable layer or Content Bank reference for prepared still imagery.")
            native_platform_support.append("Igloo can display prepared still images as a normal documented media workflow.")
            authoring_tools.append("Prepare still images in a standard image-editing tool and export them in an expected format such as JPG or PNG.")
            content_assumptions.append("The image asset must be prepared in a format and location the Igloo system can access.")
            content_design_requirements.append("The image selection, resolution, and in-room readability still need to be checked for the intended experience.")
            build_unknowns.append("The exact image files and their final quality in-room still need to be checked.")

        if "website" in concepts or "webview" in concepts:
            runtime_surfaces.append("Use a WebView layer for website content or a hosted microsite.")
            native_platform_support.append("Igloo can display URL-based content through a WebView layer.")
            authoring_tools.append("Use an existing website directly, or host a lightweight web app if the experience needs bespoke interaction.")
            content_assumptions.append("The target website or web app must be reachable from the Igloo environment.")
            content_design_requirements.append("The web content still needs to be reachable, readable in-room, and suitable for the operator flow.")
            build_unknowns.append("The final hosting, reachability, and fallback behavior for the website path still need confirmation.")

        if "model_viewer" in concepts or self._contains_any(normalized, MODEL_HINTS):
            runtime_surfaces.append("Use Igloo Model Viewer or a supported BIM/model-viewer route for in-room 3D model review.")
            native_platform_support.append("Igloo documents model-viewer and named AECO integration routes for supported review workflows.")
            authoring_tools.append("Prepare the 3D model or BIM source in a format supported by the chosen model-viewer workflow.")
            content_assumptions.append("The model source and permissions must support the intended in-room review workflow.")
            content_design_requirements.append("The AECO review still needs the right viewer choice, markup workflow, and meeting choreography.")
            build_unknowns.append("The exact model viewer, markup flow, and participant-control model still need to be chosen.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if "video" in concepts or self._contains_any(normalized, {"video", "film", "360 video"}):
            runtime_surfaces.append("Use a video-capable layer or Content Bank reference for the prepared media asset.")
            native_platform_support.append("Igloo can play prepared video content inside documented media workflows.")
            authoring_tools.append("Prepare video in a media-editing tool and export it in a format the target environment can access.")
            content_assumptions.append("The video asset must be pre-authored and stored where the Igloo system can reach it.")
            content_design_requirements.append("The experience still needs source media, timing, captions if needed, and the right playback-ready export.")
            build_unknowns.append("The exact media asset, codec/access path, and playback source still need to be confirmed.")

        if "360_content" in concepts or self._contains_any(normalized, {"360", "immersive", "panoramic"}):
            runtime_surfaces.append("Use the documented 360-degree content workflow for panoramic imagery or 360 video.")
            native_platform_support.append("Igloo documents a 360 image and 360 video workflow for immersive media.")
            authoring_tools.append("Source or create the 360 imagery/video before loading it into Igloo.")
            content_assumptions.append("A suitable 360 asset must already exist; the current Phase 1 system does not source it automatically.")
            content_design_requirements.append("Someone still needs to choose or create the 360 content and align it to the intended narrative or teaching outcome.")
            build_unknowns.append("The final 360 asset source and whether to use hosted or local media still need to be chosen.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if has_youtube_360_route and ("360_content" in concepts or self._contains_any(normalized, TOUR_HINTS | {"youtube", "youtube 360", "360"})):
            runtime_surfaces.append("A likely supported route is the dedicated YouTube 360 workflow, or a hosted/browser-based YouTube 360 path, for readily available immersive video content.")
            native_platform_support.append("Igloo documentation references a YouTube 360 route for hosted immersive video playback.")
            content_assumptions.append("If suitable source content exists, YouTube 360 can be used as a quick content route instead of commissioning bespoke 360 footage.")
            build_unknowns.append("The team still needs to decide whether hosted YouTube 360 or locally prepared media is the better operational choice.")

        supports_360_video_route = "video" in concepts and (
            "360_content" in concepts
            or self._contains_any(normalized, {"360", "immersive", "panoramic"})
            or any("360-degree content workflow" in surface.lower() for surface in runtime_surfaces)
        )

        if supports_360_video_route:
            candidate_routes.append("Alternative content route: if a suitable 360 video is available locally, load it as a prepared media asset instead of relying on hosted YouTube content.")
            if has_youtube_360_route or self._contains_any(normalized, TOUR_HINTS | ACCESSIBILITY_HINTS | NARRATIVE_HINTS | {"heritage", "storytelling", "immersive"}):
                candidate_routes.append("Alternative hosted-content route: if suitable public footage already exists, use the documented YouTube 360 workflow rather than commissioning bespoke 360 capture.")

        if matches_heritage_pattern:
            use_case_alignment.append("Comparable Igloo use-case pattern: heritage and exhibition experiences commonly combine prepared 360 media, archival imagery, narration, and guided storytelling.")
            if supports_360_video_route or has_youtube_360_route or self._contains_any(normalized, {"immersive", "heritage", "storytelling"}):
                runtime_surfaces.append("A practical heritage route is to combine prepared 360 media or YouTube 360, archival images, and audio inside a saved operator-led session.")
                interaction_model.append("Keep the heritage experience operator-led or menu-led so the story remains controlled and repeatable for group visitors.")

        if matches_education_pattern:
            use_case_alignment.append("Comparable Igloo use-case pattern: immersive classrooms and teaching spaces use repeatable sessions, virtual field trips, and operator-guided learning content.")
            if self._contains_any(normalized, {"repeatable", "reusable", "school group", "classroom", "teacher", "operator-light", "operator light"}):
                runtime_surfaces.append("A practical education route is to package the experience as repeatable sessions with Home or Content Bank launch points for the facilitator.")

        if "content_bank" in concepts or self._contains_any(normalized, SCENARIO_SWITCHING_HINTS):
            runtime_surfaces.append("Use Content Bank entries and saved sessions to switch between prepared scenarios or media states.")
            native_platform_support.append("Igloo can use Content Bank and saved sessions for prepared content switching.")
            interaction_model.append("Keep switching operator-led rather than promising automatic narrative logic.")
            content_design_requirements.append("The operator flow and content grouping still need to be designed so the switching feels intentional.")
            build_unknowns.append("The content grouping and switching order still need to be designed for the intended audience and operator.")

        if has_content_bank and self._contains_any(normalized, {"content bank", "switch", "switching", "adaptable", "multi-use", "multi use", "scenario", "scenarios", "workspace", "workspaces"}):
            runtime_surfaces.append("Use Content Bank tiles to launch or swap prepared media, documents, or other sources without leaving the main experience flow.")
            native_platform_support.append("Igloo Content Bank tiles can launch prepared media, documents, and sessions.")

        if has_home_controls and self._contains_any(normalized, {"home", "menu", "section", "icons", "button", "buttons", "workspace", "workspaces"} | SCENARIO_SWITCHING_HINTS | NAVIGATION_HINTS):
            runtime_surfaces.append("Use the Home layer and Home components to build simple on-screen launch tiles, menus, or section navigation.")
            native_platform_support.append("Igloo Home can present launch tiles and section-based navigation for prepared workflows.")
            content_design_requirements.append("The Home layout, labels, icons, and section structure still need UX design and operator testing.")
            build_unknowns.append("The Home layout and menu structure still need to be designed for clarity and repeatable use.")

        if has_triggers_actions and self._contains_any(
            normalized,
            INTERACTION_HINTS
            | HOTSPOT_HINTS
            | NAVIGATION_HINTS
            | SCENARIO_SWITCHING_HINTS
            | {"trigger", "triggers", "action", "actions", "scenario", "scenarios"},
        ):
            runtime_surfaces.append("Use Triggers and Actions to link on-screen tiles, layer events, session loads, or other simple inputs to workspace, session, layer, WebView, and Content Bank actions.")
            native_platform_support.append("Igloo documents Triggers and Actions for simple event-driven session, layer, URL, and tile behaviors.")
            interaction_model.append("A light-touch interactive flow can be built natively by pressing tiles or simple icons that trigger sessions, layouts, active tiles, URLs, or layer actions.")
            custom_work_items.append("Configure the Triggers and Actions graph, Home tiles, or Content Bank actions for the intended visitor journey.")
            content_design_requirements.append("The trigger graph, state transitions, and reset behavior still need explicit design.")
            build_unknowns.append("The exact Triggers and Actions graph, failure cases, and reset behavior still need to be worked through.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if has_triggers_actions and self._contains_any(normalized, HOTSPOT_HINTS | {"machinery", "equipment", "overlay", "overlays", "diagram", "diagrams"}):
            interaction_model.append("Use simple on-screen icons or trigger tiles over the scene to open supporting PDFs, swap layers, reveal web content, or move to another prepared workspace.")

        if has_thinglink_route and self._contains_any(normalized, HOTSPOT_HINTS):
            runtime_surfaces.append("For direct hotspot-style annotations or popups on a 360 scene, a ThingLink-style route is a credible integration option.")
            candidate_routes.append("Alternative integration route: ThingLink provides a more direct hotspot-and-popup workflow when the interaction needs to sit visibly on the scene itself.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if (self._contains_any(normalized, BESPOKE_WEB_HINTS) and not negates_custom_app) or (
            self._contains_any(normalized, HOTSPOT_HINTS) and not has_triggers_actions and not has_thinglink_route
        ):
            runtime_surfaces.append("Deliver the bespoke interaction through a hosted web app loaded inside a WebView.")
            authoring_tools.append("Build or adapt a lightweight web app or microsite for the interactive layer.")
            interaction_model.append("Use operator or audience interaction inside the web experience to reveal information states.")
            custom_work_items.append("Implement and test the bespoke interactive layer as a custom web app.")
            content_design_requirements.append("The app logic, UI states, and recovery behavior still need engineering and UX work outside documented media setup.")
            build_unknowns.append("This interaction goes beyond the clearly documented Home / Content Bank / Triggers and Actions workflows, so it should be treated as a custom route.")
            implementation_kind = "custom_web_app"
            route_confidence = self._raise_route_confidence(route_confidence, "partial")
            needs_human_review = True

        if self._contains_any(normalized, {"audio", "spatial audio", "surround sound"}):
            content_assumptions.append("The media and room setup must provide the required audio mix and playback path.")
            content_design_requirements.append("The audio mix, routing, and room playback behavior still need to be confirmed for the target setup.")
            build_unknowns.append("The exact audio routing and whether the requested mix works in the target room still need confirmation.")
            if has_audio_support:
                runtime_surfaces.append("Use the documented audio and playback controls to manage volume and output routing alongside the visual experience.")
                native_platform_support.append("Igloo documents playback and audio controls for supported media workflows.")
            else:
                build_unknowns.append("Current evidence is stronger on visual layers than on the exact authoring path for the requested audio experience.")
                route_confidence = self._raise_route_confidence(route_confidence, "partial")
                needs_human_review = True

        if self._contains_any(normalized, LIVE_INTEGRATION_HINTS) and has_ndi_route:
            runtime_surfaces.append("Use the documented sharing or integration route, such as NDI, video conferencing, or canvas-sharing pathways, to bring live dashboards, camera feeds, or remote-call windows into the room.")
            native_platform_support.append("Igloo documents video-conferencing and integration layer routes that can be used for operator-led live content sharing.")
            build_unknowns.append("The exact live routing choice, network path, and operator switching flow still need to be confirmed for the target room.")

        if matches_aeco_pattern:
            use_case_alignment.append("Comparable Igloo use-case pattern: AECO teams use immersive workspaces for BIM/model review, markups, design comparison, and faster collaborative decision-making.")
            runtime_surfaces.append("A practical AECO route is to use Igloo Model Viewer, Revizto, or Autodesk-connected content for the main view, with dashboards or conferencing content brought in as supporting layers when needed.")
            interaction_model.append("For AECO review, keep one operator or presenter in charge of the main immersive view while the wider group collaborates around markups, dashboards, or comparison states.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if matches_hybrid_pattern and self._contains_any(normalized, OPERATOR_LED_HINTS):
            use_case_alignment.append("Comparable Igloo use-case pattern: operator-led hybrid workshops and collaborative sessions can mix live/shared content with prepared immersive material in one room workflow.")

        if self._contains_any(normalized, ACCESSIBILITY_HINTS):
            authoring_tools.append("Build accessibility into the source content itself, for example by using captions/subtitles in the source platform or burning subtitles into the prepared video.")
            content_design_requirements.append("Accessibility still depends on content preparation, captioning choices, layout clarity, and testing with the intended audience.")
            build_unknowns.append("The accessibility implementation still needs explicit design and human review; runtime support alone does not prove audience suitability.")
            needs_human_review = True
            if has_true_perspective and self._contains_any(normalized, {"wheelchair", "seated", "mobility"}):
                runtime_surfaces.append("Use True Perspective custom head positions to tune the view for seated or wheelchair-height audiences.")
                native_platform_support.append("Igloo supports True Perspective head positions for calibrated viewing setups.")
                route_confidence = self._raise_route_confidence(route_confidence, "partial")
            else:
                build_unknowns.append("Accessibility outcomes still depend on content design, operator flow, and room layout, even when the core platform route is supported.")
                route_confidence = self._raise_route_confidence(route_confidence, "partial")
            if has_home_controls or has_content_bank:
                runtime_surfaces.append("Use Home or Content Bank tiles to keep navigation simple, repeatable, and low-cognitive-load for the audience and operator.")

        if self._contains_any(normalized, AUDIENCE_HINTS):
            needs_human_review = True
            content_design_requirements.append("Audience fit still depends on content tone, pacing, readability, and facilitation rather than runtime support alone.")
            build_unknowns.append("The final audience fit still needs human review against the actual visitor or classroom context.")

        if self._contains_any(normalized, OPERATIONAL_REVIEW_HINTS):
            needs_human_review = True
            content_design_requirements.append("Operational quality claims such as simplicity, robustness, or unattended reliability still need human design and testing.")
            build_unknowns.append("Operational reset behavior, robustness, and ease-of-use still need to be validated for the intended environment.")

        if self._contains_any(normalized, {"unattended", "kiosk", "public-facing", "public facing"}) and (
            has_triggers_actions or has_content_bank or has_home_controls or self._contains_any(normalized, INTERACTION_HINTS | HOTSPOT_HINTS)
        ):
            if self._contains_any(normalized, COMPLEX_INTERACTION_HINTS) or not matches_simple_public_interaction:
                implementation_kind = "custom_integration"
                build_unknowns.append("Unattended public interaction and restart-cleanly behavior push this beyond a simple documented configuration workflow.")
            else:
                use_case_alignment.append("Comparable Igloo use-case pattern: public-facing experience spaces often rely on simple reveal actions, guided menus, or hotspot-style content rather than bespoke application logic.")
                runtime_surfaces.append("A practical public-experience route is to use Home, Triggers and Actions, Content Bank, or a ThingLink-style layer for simple tap-to-reveal interaction.")
                interaction_model.append("Keep the public interaction shallow and resettable, with large touch targets and a small number of reliable state changes.")
                route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if self._contains_any(normalized, NARRATIVE_HINTS):
            content_assumptions.append("Narrative sequencing, storytelling quality, and audience fit depend on prepared content, not just documented layer support.")
            content_design_requirements.append("The narrative still needs content selection, pacing, sequencing, and presentation design.")
            build_unknowns.append("The storytelling quality and how well the assets support the intended story still need human review.")
            if not runtime_surfaces:
                build_unknowns.append("The requested experience outcome is broader than the documented runtime features, so the content plan still needs human scoping.")
                route_confidence = self._raise_route_confidence(route_confidence, "partial")
                needs_human_review = True
            else:
                needs_human_review = True

        if self._contains_any(normalized, COMPLEX_INTERACTION_HINTS):
            needs_human_review = True
            content_design_requirements.append("Branching logic, decision points, and stateful experience behavior still need explicit interaction design.")
            build_unknowns.append("The branching logic, vote handling, and state transitions still need detailed design and test coverage.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")
            if has_triggers_actions or self._contains_any(normalized, {"branching", "vote", "outcomes"}):
                implementation_kind = "custom_integration"

        if self._contains_any(normalized, LIVE_INTEGRATION_HINTS):
            needs_human_review = True
            content_design_requirements.append("Live feeds, remote participants, dashboards, or comparison layouts still need operational choreography and integration testing.")
            build_unknowns.append("The live integration behavior, latency tolerance, and operator workflow still need confirmation.")
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if self._contains_any(normalized, APP_RISK_HINTS):
            implementation_kind = "custom_integration"
            needs_human_review = True
            build_unknowns.append("The requested experience depends on external app logic or engine behavior rather than just documented Igloo media configuration.")

        candidate_routes.extend(self._candidate_routes(normalized, evidence_text))
        if candidate_routes:
            route_confidence = self._raise_route_confidence(route_confidence, "partial")
            if policy.documentation_status != "documented":
                needs_human_review = True
                build_unknowns.append("Alternative integration routes below come from integration documentation and approved-reference material, so they should inform implementation options without replacing primary runtime validation.")

        if self._contains_any(normalized, {"diagram", "diagrams", "plan", "plans", "overlay", "overlays"}):
            authoring_tools.append("Prepare diagrams or plan graphics in PowerPoint, Canva, or similar tools, then export them as PDF or image assets for runtime use.")
            content_design_requirements.append("Overlay graphics and diagrams still need to be authored so they remain legible and well-positioned in-room.")

        if "no custom content required" in normalized:
            build_unknowns.append("A compelling heritage, education, or narrative demo still needs prepared assets even if no bespoke application is built.")
            needs_human_review = True
            route_confidence = self._raise_route_confidence(route_confidence, "partial")

        if self._contains_any(normalized, GENERATIVE_ASSEMBLY_LIMIT_HINTS):
            content_design_requirements.append("The overall experience still needs prepared or externally generated assets before Igloo can assemble them into a session.")
            build_unknowns.append("Igloo can assemble prepared assets and session structure, but it does not natively generate the full experience package from one prompt.")
            needs_human_review = True

        if not runtime_surfaces:
            runtime_surfaces.append("The runtime surface is still unclear from the request alone, so this should be scoped before treating it as supported.")
            build_unknowns.append("The target runtime surface and layer choice are still unclear.")
            route_confidence = self._raise_route_confidence(route_confidence, "speculative")
            needs_human_review = True

        if not authoring_tools:
            authoring_tools.append("Use the existing content source directly if it already matches a documented Igloo runtime surface.")

        if not interaction_model:
            interaction_model.append("Assume operator-led control unless the request explicitly justifies a more custom interaction model.")

        if implementation_kind == "configuration" and route_confidence == "speculative":
            implementation_kind = "configuration_with_human_design"

        validation_posture = self._validation_posture(normalized, concepts, implementation_kind, requests_complex_control, candidate_routes, custom_work_items)
        platform_capability = self._platform_capability(policy, concepts, implementation_kind)
        exact_item_check = self._exact_item_check(normalized, concepts, platform_capability, implementation_kind, validation_posture)
        workflow_fit = self._workflow_fit(policy, validation_posture, implementation_kind, normalized, use_case_alignment)
        control_interaction_fit = self._control_interaction_fit(normalized, validation_posture, implementation_kind, requests_complex_control, has_triggers_actions)
        practical_summary = self._practical_summary(platform_capability, exact_item_check, workflow_fit, control_interaction_fit, validation_posture)
        configuration_burden = self._configuration_burden(validation_posture, runtime_surfaces, content_design_requirements, custom_work_items, normalized)
        experience_risk = self._experience_risk(normalized, validation_posture, needs_human_review)
        format_support_confidence = self._format_support_confidence(policy, validation_posture, route_confidence, platform_capability)
        review_requirement = self._review_requirement(needs_human_review, validation_posture, experience_risk)

        return BuildApproach(
            implementation_kind=implementation_kind,
            validation_posture=validation_posture,
            platform_capability=platform_capability,
            exact_item_check=exact_item_check,
            workflow_fit=workflow_fit,
            control_interaction_fit=control_interaction_fit,
            practical_summary=practical_summary,
            format_support_confidence=format_support_confidence,
            configuration_burden=configuration_burden,
            experience_risk=experience_risk,
            review_requirement=review_requirement,
            use_case_alignment=self._dedupe(use_case_alignment),
            runtime_surfaces=self._dedupe(runtime_surfaces),
            native_platform_support=self._dedupe(native_platform_support),
            content_design_requirements=self._dedupe(content_design_requirements),
            authoring_tools=self._dedupe(authoring_tools),
            candidate_routes=self._dedupe(candidate_routes),
            interaction_model=self._dedupe(interaction_model),
            content_assumptions=self._dedupe(content_assumptions),
            custom_work_items=self._dedupe(custom_work_items),
            build_unknowns=self._dedupe(build_unknowns),
            route_confidence=route_confidence,
            needs_human_review=needs_human_review,
        )

    def _validation_posture(self, normalized: str, concepts: list[str], implementation_kind: str, requests_complex_control: bool, candidate_routes: list[str], custom_work_items: list[str]) -> str:
        if implementation_kind in {"custom_web_app", "custom_integration"}:
            return "app/integration-risk workflow"
        if self._contains_any(normalized, COMPLEX_INTERACTION_HINTS | APP_RISK_HINTS):
            return "app/integration-risk workflow"
        high_risk_routes = [route for route in candidate_routes if "integration route" in route or "Custom developer route" in route]
        if requests_complex_control or custom_work_items or high_risk_routes or self._contains_any(normalized, LIVE_INTEGRATION_HINTS) or not set(concepts).issubset(LOW_RISK_MEDIA_CONCEPTS):
            return "configuration-heavy workflow"
        return "documented media workflow"

    def _platform_capability(self, policy: SupportPolicyDecision, concepts: list[str], implementation_kind: str) -> str:
        known_working_hits = set(concepts) & KNOWN_WORKING_PLATFORM_CONCEPTS
        if policy.route_hint == "unsupported" and not known_working_hits:
            return "unsupported"
        if known_working_hits and policy.documentation_status != "not supported in retrieved sources":
            return "known working"
        if implementation_kind in {"custom_web_app", "custom_integration"} and known_working_hits:
            return "known working"
        return "unclear"

    def _exact_item_check(self, normalized: str, concepts: list[str], platform_capability: str, implementation_kind: str, validation_posture: str) -> str:
        if platform_capability == "unsupported" or implementation_kind in {"custom_web_app", "custom_integration"}:
            return "likely problematic"
        if not (set(concepts) & ITEM_SENSITIVE_CONCEPTS) and not self._contains_any(normalized, {"url", "link", "model", "models", "website", "youtube", "revizto", "autodesk", "teams"}):
            return "not assessed"
        if self._contains_any(normalized, LIVE_INTEGRATION_HINTS | APP_RISK_HINTS | MODEL_HINTS | {"youtube", "website", "webview", "url", "link", "dashboard", "camera", "feed", "teams"}):
            return "needs checking"
        if platform_capability == "known working" and validation_posture == "documented media workflow":
            return "likely fine"
        return "needs checking"

    def _workflow_fit(self, policy: SupportPolicyDecision, validation_posture: str, implementation_kind: str, normalized: str, use_case_alignment: list[str]) -> str:
        if policy.route_hint == "unsupported":
            return "poor fit"
        if policy.route_hint == "unverified" and validation_posture != "documented media workflow":
            return "unknown"
        if implementation_kind in {"custom_web_app", "custom_integration"} and self._contains_any(normalized, COMPLEX_INTERACTION_HINTS | LIVE_INTEGRATION_HINTS | OPERATIONAL_REVIEW_HINTS):
            return "poor fit"
        if self._contains_any(normalized, AECO_USE_CASE_HINTS) and self._contains_any(normalized, OPERATOR_LED_HINTS) and self._contains_any(normalized, {"teams", "remote participants", "markups", "dashboard", "comparison layout", "comparison layouts"}):
            return "good fit"
        if validation_posture == "documented media workflow" and not policy.needs_human_review:
            return "good fit"
        if use_case_alignment and validation_posture == "configuration-heavy workflow" and not self._contains_any(normalized, COMPLEX_INTERACTION_HINTS | {"one prompt", "text prompt"}):
            return "possible with caveats"
        if validation_posture in {"configuration-heavy workflow", "app/integration-risk workflow"} or policy.needs_human_review:
            return "possible with caveats"
        return "unknown"

    def _control_interaction_fit(self, normalized: str, validation_posture: str, implementation_kind: str, requests_complex_control: bool, has_triggers_actions: bool) -> str:
        if implementation_kind in {"custom_web_app", "custom_integration"} or self._contains_any(normalized, COMPLEX_INTERACTION_HINTS):
            return "high risk"
        if self._contains_any(normalized, {"unattended", "kiosk"}) and not (
            has_triggers_actions and self._contains_any(normalized, SIMPLE_REVEAL_HINTS | HOTSPOT_HINTS)
        ):
            return "high risk"
        if self._contains_any(normalized, LIVE_INTEGRATION_HINTS):
            if self._contains_any(normalized, AECO_USE_CASE_HINTS | OPERATOR_LED_HINTS):
                return "straightforward"
            return "needs review"
        if requests_complex_control or (has_triggers_actions and self._contains_any(normalized, {"trigger", "triggers", "action", "actions", "interactive", "clickable", "tap", "button", "buttons"})):
            return "needs review"
        if validation_posture == "documented media workflow":
            return "straightforward"
        if self._contains_any(normalized, {"home", "content bank", "switch", "switching", "launch", "reusable", "repeatable"}):
            return "straightforward"
        return "not applicable"

    def _practical_summary(self, platform_capability: str, exact_item_check: str, workflow_fit: str, control_interaction_fit: str, validation_posture: str) -> str:
        if platform_capability == "known working" and workflow_fit == "good fit" and control_interaction_fit == "straightforward":
            return "Yes, Igloo already supports this class of content/workflow. The main thing to check is that the exact file, link, or prepared asset behaves as expected."
        if platform_capability == "known working" and control_interaction_fit in {"needs review", "high risk"}:
            return "Yes, Igloo generally supports the underlying content or building blocks, but the controls or interaction flow need review."
        if platform_capability == "known working" and workflow_fit == "possible with caveats":
            return "Yes, the platform building blocks are there, but the proposed workflow still has caveats around fit, operation, or presentation."
        if validation_posture == "app/integration-risk workflow":
            return "The runtime building blocks exist, but the full ask goes beyond a straightforward configuration-led setup."
        if platform_capability == "unsupported":
            return "This ask goes beyond what Phase 1 should position as supported."
        if exact_item_check == "likely problematic":
            return "The general idea may be plausible, but this exact app, build, or behavior is still likely to be problematic."
        return "Some relevant building blocks are documented, but the exact item, workflow fit, or control behavior still needs checking."

    def _configuration_burden(self, validation_posture: str, runtime_surfaces: list[str], content_design_requirements: list[str], custom_work_items: list[str], normalized: str) -> str:
        if validation_posture == "app/integration-risk workflow":
            return "high"
        if len(runtime_surfaces) >= 5 or len(content_design_requirements) >= 4 or custom_work_items:
            return "high" if self._contains_any(normalized, COMPLEX_INTERACTION_HINTS | LIVE_INTEGRATION_HINTS) else "medium"
        if validation_posture == "configuration-heavy workflow":
            return "medium"
        return "low"

    def _experience_risk(self, normalized: str, validation_posture: str, needs_human_review: bool) -> str:
        if validation_posture == "app/integration-risk workflow":
            return "high"
        if self._contains_any(normalized, ACCESSIBILITY_HINTS | AUDIENCE_HINTS | OPERATIONAL_REVIEW_HINTS | COMPLEX_INTERACTION_HINTS):
            return "high"
        if needs_human_review:
            return "medium"
        return "low"

    def _format_support_confidence(self, policy: SupportPolicyDecision, validation_posture: str, route_confidence: str, platform_capability: str) -> str:
        primary_coverage = [value for value in policy.evidence_coverage.values() if value == "primary"]
        if platform_capability == "known working" and validation_posture == "documented media workflow":
            return "clear"
        if policy.documentation_status == "documented" and route_confidence == "concrete" and len(primary_coverage) == len(policy.evidence_coverage):
            return "clear"
        if policy.documentation_status == "documented" and validation_posture != "app/integration-risk workflow":
            return "mixed"
        return "unclear"

    def _review_requirement(self, needs_human_review: bool, validation_posture: str, experience_risk: str) -> str:
        if needs_human_review or experience_risk == "high":
            return "required"
        if validation_posture == "configuration-heavy workflow":
            return "recommended"
        return "not routinely required"

    def _candidate_routes(self, normalized: str, evidence_text: str) -> list[str]:
        routes: list[str] = []
        if self._contains_any(normalized, TRAINING_HINTS):
            if "cenario vr" in evidence_text or "cenario vr" in normalized:
                routes.append("Alternative integration route: CenarioVR appears in the integration documentation as a training-authoring tool for immersive, interactive 360 simulations.")
            if "warpvr" in evidence_text or "warpvr" in normalized or "training" in normalized:
                routes.append("Alternative integration route: WarpVR appears in the integration documentation as a platform for creating and scaling immersive 360 VR training scenarios.")
            if "wonda vr" in evidence_text or "wonda vr" in normalized or "interactive vr" in normalized:
                routes.append("Alternative integration route: Wonda appears in the integration documentation as a platform for crafting interactive VR training simulations.")
            if "webxr" in evidence_text or "webgl" in evidence_text or "webxr" in normalized or "webgl" in normalized:
                routes.append("Custom developer route: the documentation calls out WebXR and WebGL as guided routes for compatible web-based immersive experiences.")

        if self._contains_any(normalized, MODEL_HINTS):
            routes.append("Alternative Igloo route: the documentation says 3D models can be viewed in Igloo Model Viewer, including GLB/GLTF, FBX, OBJ, and similar model formats.")
            if "revizto" in evidence_text or "revizto" in normalized:
                routes.append("Alternative integration route: Revizto appears in the integration documentation as a digital twin / model-viewer platform for collaborative BIM review.")
            if "vrex" in evidence_text or "vrex" in normalized:
                routes.append("Alternative integration route: VREX appears in the integration documentation as a VR platform for collaborative BIM model reviews and issue tracking.")
            if "autodesk bim 360" in evidence_text or "autodesk bim 360" in normalized or "autodesk" in normalized:
                routes.append("Alternative web-content route: Autodesk BIM 360 and Autodesk DWG TrueView appear in the documentation's web-content and integration references, suggesting a browser-based AECO review path when the client already uses those tools.")
            if "revit" in normalized:
                routes.append("Alternative implementation route: if the client's Revit workflow already exports into a supported viewer or model format, use that downstream viewer in Igloo rather than treating native Revit itself as the runtime surface.")

        if self._contains_any(normalized, TOUR_HINTS):
            if "matterport" in evidence_text or "matterport" in normalized:
                routes.append("Alternative integration route: Matterport appears in the integration documentation as a virtual-tour platform that can serve as the experience source.")
            if "streetview" in evidence_text or "street view" in normalized:
                routes.append("Alternative integration route: Street View appears in the documentation as an interactive 360 map route for location-based experiences.")
            if "youtube 360" in evidence_text or "youtube 360" in normalized:
                routes.append("Alternative hosted-content route: YouTube 360 appears in the documentation as a supported source for hosted 360 immersive videos.")

        if self._contains_any(normalized, HERITAGE_USE_CASE_HINTS | {"safari", "virtual field trip", "field trip"}):
            if "youtube 360" in evidence_text or "youtube 360" in normalized:
                routes.append("Practical content route: use the documented YouTube 360 workflow when suitable public immersive footage already exists for the destination or heritage topic.")
            if "streetview" in evidence_text or "street view" in normalized:
                routes.append("Alternative location-based route: use the documented Street View workflow when the experience is better served by a navigable real-world location view than by linear video.")

        if self._contains_any(normalized, HOTSPOT_HINTS) and "thinglink" in evidence_text:
            routes.append("Alternative integration route: ThingLink appears in the documentation as an interactive-tour platform with hotspot-style info popups.")
        if self._contains_any(normalized, LIVE_INTEGRATION_HINTS) and self._contains_any(normalized, {"ndi", "teams", "zoom", "dashboard", "camera", "feed"} | AECO_USE_CASE_HINTS):
            if "ndi" in evidence_text or "video conferencing" in evidence_text or "canvas sharing" in evidence_text or "teams" in normalized or "ndi" in normalized:
                routes.append("Alternative live-input route: use the documented NDI, video-conferencing, or canvas-sharing path to bring live feeds, shared apps, or collaboration windows into the room.")
        return self._dedupe(routes)

    def _contains_any(self, normalized: str, values: set[str]) -> bool:
        return any(value in normalized for value in values)

    def _raise_route_confidence(self, current: str, candidate: str) -> str:
        if ROUTE_CONFIDENCE_ORDER[candidate] > ROUTE_CONFIDENCE_ORDER[current]:
            return candidate
        return current

    def _dedupe(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
