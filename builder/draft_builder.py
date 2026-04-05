from __future__ import annotations

import re
from itertools import count

from igloo_experience_builder.builder.models import (
    AssessmentSnapshot,
    BuilderRecommendation,
    ContentCandidate,
    ExperienceDraft,
    LayerDraft,
    SessionImportSummary,
    StructureProfile,
    WorkflowStep,
)
from igloo_experience_builder.knowledge.taxonomy import request_concepts
from igloo_experience_builder.models import CapabilityAssessment, OperationalFlag


STRUCTURE_PROFILES = [
    StructureProfile(
        structure_id="immersive-workspace",
        label="Immersive workspace",
        description="A flexible general-purpose Igloo room suited to guided demos, storytelling, and workshops.",
        shape="rect",
        projection_style="panoramic walls",
    ),
    StructureProfile(
        structure_id="cave",
        label="CAVE",
        description="A multi-wall shared immersive environment with strong collaborative sight lines.",
        shape="cave",
        projection_style="multi-wall room",
    ),
    StructureProfile(
        structure_id="cylinder",
        label="Cylinder",
        description="A wraparound shared immersive surface for continuous panoramic content.",
        shape="cylinder",
        projection_style="continuous wrap",
    ),
    StructureProfile(
        structure_id="cube",
        label="Cube",
        description="A compact immersive room for focused demos, classrooms, and collaborative reviews.",
        shape="cube",
        projection_style="box room",
    ),
    StructureProfile(
        structure_id="dome",
        label="Dome",
        description="A dome-style surface suited to immersive sky, environmental, and cinematic experiences.",
        shape="dome",
        projection_style="curved dome",
    ),
    StructureProfile(
        structure_id="retrofit",
        label="Retrofit room",
        description="A practical adapted space where content choice and calibration matter more than theatrical geometry.",
        shape="retrofit",
        projection_style="adapted room",
    ),
]

DEFAULT_TARGET_DURATION = 10
TOPIC_PHRASES = (
    "steel production",
    "steel industry",
    "steelworks",
    "heritage storytelling",
    "heritage",
    "archival",
    "viking settlement",
    "viking",
    "classroom simulation",
    "classroom",
    "education",
    "stem",
    "museum kiosk",
    "museum",
    "aeco",
    "bim",
    "design review",
    "revizto",
    "autodesk",
    "dashboard",
    "timeline",
    "camera feed",
    "showroom",
    "training",
    "simulation",
    "nasa",
    "safari",
    "new product",
    "product model",
    "sales dashboard",
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "be",
    "brief",
    "build",
    "contain",
    "contains",
    "by",
    "can",
    "centre",
    "content",
    "create",
    "demo",
    "demo-centre",
    "designed",
    "environment",
    "display",
    "event",
    "experience",
    "for",
    "group",
    "groups",
    "igloo",
    "in",
    "inside",
    "interactive",
    "my",
    "layer",
    "layers",
    "main",
    "must",
    "needs",
    "no",
    "notes",
    "of",
    "on",
    "one",
    "operator",
    "operator-driven",
    "operator-light",
    "or",
    "play",
    "promise",
    "public",
    "presented",
    "proof",
    "repeatable",
    "reusable",
    "room",
    "session",
    "showing",
    "should",
    "simple",
    "suitable",
    "that",
    "the",
    "this",
    "to",
    "travel",
    "travelling",
    "traveling",
    "use",
    "used",
    "using",
    "website",
    "video",
    "pdf",
    "local",
    "using",
    "trip",
    "within",
    "with",
}
TOPIC_NORMALIZATIONS = {
    "japanese": "japan",
    "tokyo": "tokyo japan",
    "kyoto": "kyoto japan",
    "osaka": "osaka japan",
    "safari": "safari wildlife",
    "wheelchair": "wheelchair accessible",
    "neurodiverse": "neurodiverse accessible",
}
DEMO_NOTES = {
    "education": [
        "Start with one immersive hook that sets the scene in the first 60-90 seconds, then move into guided teaching beats.",
        "Keep the teacher or operator flow to a small number of clear states so the lesson feels structured rather than exploratory by accident.",
        "Use interaction sparingly: one reveal, vote, or branch moment is stronger than lots of small clicks in a classroom demo.",
    ],
    "aeco": [
        "Lead with one primary model route first, then bring in markups, comparison layouts, or dashboards as controlled secondary states.",
        "For client-facing AECO demos, smooth operator flow matters more than showing every tool at once.",
        "If hybrid participation is part of the demo, make that a planned beat rather than something always on in the background.",
    ],
    "heritage": [
        "Open with one strong visual scene, then use archive stills, PDF references, or narrated panels to deepen the story.",
        "Keep state changes sparse so the narrative still feels coherent and not like a product tour.",
        "End on a clean reset or launcher so the room is easy to rerun for the next audience.",
    ],
    "generic": [
        "Client-facing immersive demos usually work best with one hero moment, two or three supporting beats, and one obvious reset path.",
        "Use the room to show why the experience is spatial, not just to display more media types.",
    ],
}


class PhaseTwoDraftBuilder:
    def build(
        self,
        brief: str,
        assessment: CapabilityAssessment,
        structure_id: str,
        session_import: SessionImportSummary | None = None,
        import_mode: str = "replace",
    ) -> ExperienceDraft:
        structure = next((item for item in STRUCTURE_PROFILES if item.structure_id == structure_id), STRUCTURE_PROFILES[0])
        suggested_structure = self._suggest_structure(brief, assessment)
        target_duration_minutes = self._target_duration_minutes(brief)
        brief_content = self._content_from_brief(brief, assessment, target_duration_minutes)
        imported_content = self._content_from_import(session_import) if session_import is not None else []
        selected_content = self._merge_selected_content(
            brief_content=brief_content,
            imported_content=imported_content,
            import_mode=import_mode,
        )
        setup_archetype = self._setup_archetype(brief, selected_content, session_import)
        self._assign_setup_roles(selected_content, setup_archetype)
        layer_drafts = self._layer_drafts(brief, assessment, selected_content, session_import)
        workflow_steps = self._workflow_steps(brief, assessment, selected_content, layer_drafts)
        estimated_duration_minutes = sum(step.minutes for step in workflow_steps)
        duration_gap_minutes = max(0, target_duration_minutes - estimated_duration_minutes)
        recommendations = self._recommendations(
            brief=brief,
            assessment=assessment,
            selected_content=selected_content,
            layer_drafts=layer_drafts,
            target_duration_minutes=target_duration_minutes,
            estimated_duration_minutes=estimated_duration_minutes,
            duration_gap_minutes=duration_gap_minutes,
        )
        readiness_score = self._build_readiness_score(assessment, selected_content, recommendations, duration_gap_minutes)
        readiness_label = self._readiness_label(readiness_score)
        search_suggestions = self._search_suggestions(selected_content)
        demo_plan_notes = self._demo_plan_notes(brief)
        setup_summary = self._setup_summary(setup_archetype, selected_content)
        return ExperienceDraft(
            brief=brief,
            structure=structure,
            suggested_structure_id=suggested_structure.structure_id,
            suggested_structure_reason=self._suggested_structure_reason(brief, suggested_structure, setup_archetype),
            setup_archetype=setup_archetype,
            setup_summary=setup_summary,
            readiness_score=readiness_score,
            readiness_label=readiness_label,
            target_duration_minutes=target_duration_minutes,
            estimated_duration_minutes=estimated_duration_minutes,
            duration_gap_minutes=duration_gap_minutes,
            assessment=self._snapshot(assessment),
            selected_content=selected_content,
            layer_drafts=layer_drafts,
            workflow_steps=workflow_steps,
            recommendations=recommendations,
            use_case_alignment=list(assessment.build_approach.use_case_alignment),
            search_suggestions=search_suggestions,
            session_import=session_import,
            demo_plan_notes=demo_plan_notes,
        )

    def _merge_selected_content(
        self,
        brief_content: list[ContentCandidate],
        imported_content: list[ContentCandidate],
        import_mode: str,
    ) -> list[ContentCandidate]:
        normalized_mode = (import_mode or "none").strip().lower()
        if normalized_mode == "replace":
            return imported_content or brief_content
        if normalized_mode == "append":
            merged: list[ContentCandidate] = []
            seen: set[tuple[str, str, str]] = set()
            for item in [*brief_content, *imported_content]:
                key = (
                    (item.title or "").strip().lower(),
                    (item.content_type or "").strip().lower(),
                    (item.location or "").strip().lower(),
                )
                if key in seen:
                    continue
                merged.append(item)
                seen.add(key)
            return merged
        return brief_content

    def structures(self) -> list[StructureProfile]:
        return STRUCTURE_PROFILES

    def _snapshot(self, assessment: CapabilityAssessment) -> AssessmentSnapshot:
        return AssessmentSnapshot(
            verdict=assessment.verdict.value,
            confidence=assessment.confidence,
            confidence_percent=round(assessment.confidence * 100),
            operational_flags=[item.value for item in assessment.operational_flags],
            validation_posture=assessment.build_approach.validation_posture,
            platform_capability=assessment.build_approach.platform_capability,
            exact_item_check=assessment.build_approach.exact_item_check,
            workflow_fit=assessment.build_approach.workflow_fit,
            control_interaction_fit=assessment.build_approach.control_interaction_fit,
            recommended_route=assessment.recommended_implementation_route,
            top_dependencies=assessment.dependencies[:3],
            top_unknowns=assessment.unresolved_unknowns[:3],
            evidence=[
                {
                    "title": item.title,
                    "excerpt": item.excerpt,
                    "source_type": item.source_type.value,
                    "score": item.score,
                }
                for item in assessment.hard_evidence[:3]
            ],
            practical_summary=assessment.build_approach.practical_summary,
        )

    def _content_from_import(self, session_import: SessionImportSummary) -> list[ContentCandidate]:
        candidates: list[ContentCandidate] = []
        for layer in session_import.layers:
            content_type = layer.inferred_content_type
            candidates.append(
                ContentCandidate(
                    candidate_id=layer.layer_id,
                    title=layer.name,
                    content_type=content_type,
                    source="Imported session",
                    location=layer.file_path,
                    readiness_status=layer.readiness_status,
                    readiness_score=layer.readiness_score,
                    exact_item_status="needs checking" if layer.readiness_status != "ready" else "likely fine",
                    notes=list(layer.notes),
                    recommended_layer_type=layer.layer_type,
                    query_hint=self._focused_query(layer.name, content_type),
                    resolution_label=", ".join(layer.render_passes) if layer.render_passes else "Unknown",
                    recommended_minutes=self._base_minutes_for(content_type),
                    selected=True,
                    setup_archetype="",
                    layout_role="",
                    setup_notes=[],
                )
            )
        return candidates

    def _content_from_brief(self, brief: str, assessment: CapabilityAssessment, target_duration_minutes: int) -> list[ContentCandidate]:
        concepts = set(request_concepts(brief))
        normalized = brief.lower()
        items: list[ContentCandidate] = []
        index = count(1)

        def add_item(
            title: str,
            content_type: str,
            source: str,
            notes: list[str],
            layer_type: str,
            query_focus: str | None = None,
            recommended_minutes: int | None = None,
        ) -> None:
            item_id = f"candidate-{next(index)}"
            status = "needs source"
            score = 36
            if content_type in {"website", "pdf", "standard video", "360 video", "image", "3d model"} and assessment.build_approach.platform_capability == "known working":
                score = 58
                status = "usable with prep"
            items.append(
                ContentCandidate(
                    candidate_id=item_id,
                    title=title,
                    content_type=content_type,
                    source=source,
                    location="",
                    readiness_status=status,
                    readiness_score=score,
                    exact_item_status="not assessed",
                    notes=notes,
                    recommended_layer_type=layer_type,
                    query_hint=self._focused_query(brief if query_focus is None else query_focus, content_type, title=title),
                    resolution_label="Not selected yet",
                    recommended_minutes=recommended_minutes or self._base_minutes_for(content_type),
                    selected=True,
                    setup_archetype="",
                    layout_role="",
                    setup_notes=[],
                )
            )

        wants_model = "model_viewer" in concepts or self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk", "3d model", "comparison layout"})
        location_anchor = self._topic_focus(brief, fallback="")
        location_style_brief = bool(
            location_anchor
            and re.search(
                r"(trip|travel|journey|tour|visit|transport|take|bring|show|showing|explore|feel like|what .* is like|as if .* there|into|around|drops .* into|drop .* into|experience)",
                normalized,
            )
        )
        trip_style_brief = self._contains_any(normalized, {"trip", "travel", "journey", "tour", "what"}) and self._contains_any(
            normalized,
            {"immersive", "students", "student", "class", "classroom", "take me", "bring me", "showing them", "see what", "transported"},
        )
        wants_360 = self._contains_any(normalized, {"360", "youtube 360", "panoramic", "safari"}) or (
            "360_content" in concepts and self._contains_any(normalized, {"immersive"}) and not wants_model
        ) or (trip_style_brief and not wants_model) or (
            location_style_brief
            and not wants_model
            and self._contains_any(
                normalized,
                {"immersive", "class", "classroom", "students", "student", "school", "demo", "training", "visitors", "audience", "public", "vr", "shared vr", "exhibition", "room"},
            )
        )
        wants_video = "video" in concepts or self._contains_any(normalized, {"video", "narrated", "film", "explainer"})
        wants_website = "website" in concepts or "webview" in concepts or self._contains_any(normalized, {"dashboard", "website", "web content", "web", "teams"})
        wants_pdf = "pdf" in concepts or self._contains_any(normalized, {"timeline", "document", "specification", "specifications", "lesson plan"})
        wants_image = "image" in concepts or self._contains_any(normalized, {"archival", "imagery", "diagram", "diagrams", "overlay", "overlays", "visual"})
        wants_live_feed = self._contains_any(normalized, {"camera", "feed", "ndi", "teams", "real-time", "real time"})
        wants_switching = self._contains_any(normalized, {"switch", "switching", "switchable", "adaptable", "multi-use", "future-proof", "reusable", "repeatable", "content bank"})
        is_education = self._contains_any(normalized, {"education", "stem", "school", "classroom", "teacher", "students"})
        is_heritage = self._contains_any(normalized, {"heritage", "storytelling", "archival", "museum"})
        is_accessibility = self._contains_any(normalized, {"accessible", "inclusive", "subtitles", "wheelchair", "neurodiverse", "low cognitive load"})
        is_multi_use = self._contains_any(normalized, {"multi-use", "future-proof", "event use", "event"})
        wants_trigger_flow = self._contains_any(normalized, {"trigger", "triggers", "actions", "icon", "icons", "tap", "button", "buttons", "hotspot", "hotspots"})
        wants_interactive_web = self._contains_any(
            normalized,
            {"interactive website", "interactive web", "web app", "webapp", "virtual tour", "thinglink", "webxr", "touchscreen", "touch screen", "360 bus"},
        )
        wants_canvas_review = self._contains_any(
            normalized,
            {"miro", "shared board", "canvas", "whiteboard", "visual collaboration", "collaboration board"},
        )
        wants_dashboard_review = self._contains_any(
            normalized,
            {"dashboard", "dashboards", "powerbi", "power bi", "graphs", "kpi", "internal sales", "strategic review", "sales meeting", "three walls", "3 walls"},
        ) and not wants_canvas_review
        wants_multi_wall_review = wants_dashboard_review or wants_canvas_review or self._contains_any(
            normalized,
            {"three walls", "3 walls", "comparison layout", "comparison layouts", "wall", "walls"},
        )
        wants_product_model = self._contains_any(normalized, {"product model", "new product", "product review", "sketchfab"})

        if wants_360:
            add_item(
                title="Main immersive 360 scene",
                content_type="360 video",
                source="Planned asset",
                notes=[
                    "Use a local 360 master or the documented YouTube 360 route when suitable footage already exists.",
                    "Prefer 4K or higher for room-scale playback.",
                ],
                layer_type="Video",
                query_focus=self._topic_focus(brief, fallback="immersive scene"),
                recommended_minutes=4,
            )
        elif wants_video:
            add_item(
                title="Primary video segment",
                content_type="standard video",
                source="Planned asset",
                notes=["Prepare the final video in a playback-ready format and confirm audio behavior."],
                layer_type="Video",
                query_focus=self._topic_focus(brief, fallback="explainer"),
                recommended_minutes=3,
            )

        if wants_pdf:
            pdf_title = "Supporting PDF or lesson document"
            if "timeline" in normalized:
                pdf_title = "Timeline PDF"
            elif self._contains_any(normalized, {"machinery", "specification", "specifications"}):
                pdf_title = "Machinery specification PDF"
            add_item(
                title=pdf_title,
                content_type="pdf",
                source="Planned asset",
                notes=["Export this cleanly for in-room readability and quick operator recall."],
                layer_type="WebView",
                query_focus=self._topic_focus(brief, fallback="reference document"),
                recommended_minutes=2,
            )

        if wants_canvas_review:
            canvas_focus = "miro collaborative board" if "miro" in normalized else f"{self._topic_focus(brief, fallback='shared board')} collaboration board"
            add_item(
                title="Shared board or canvas surface",
                content_type="review app",
                source="Planned asset",
                notes=["Stretch one strong collaboration or canvas app across the main walls instead of treating it like separate dashboard tiles."],
                layer_type="WebView",
                query_focus=canvas_focus,
                recommended_minutes=5,
            )
        elif wants_dashboard_review:
            add_item(
                title="Primary dashboard wall",
                content_type="dashboard app",
                source="Planned asset",
                notes=["Use a live app or dashboard route here rather than a brochure-style website."],
                layer_type="WebView",
                query_focus=self._topic_focus(brief, fallback="sales dashboard"),
                recommended_minutes=3,
            )
            add_item(
                title="Supporting graph or comparison wall",
                content_type="dashboard app",
                source="Planned asset",
                notes=["Use this for the second live app state, comparison layout, or graph wall."],
                layer_type="WebView",
                query_focus=self._topic_focus(brief, fallback="comparison dashboard"),
                recommended_minutes=2,
            )
        elif wants_interactive_web:
            website_title = "Interactive web experience"
            if self._contains_any(normalized, {"thinglink"}):
                website_title = "ThingLink or hotspot web experience"
            elif is_education:
                website_title = "Interactive lesson web experience"
            elif is_heritage:
                website_title = "Interactive heritage web experience"
            add_item(
                title=website_title,
                content_type="interactive web",
                source="Planned asset",
                notes=["Prioritise a demo-worthy immersive or interactive web route instead of a generic brochure page."],
                layer_type="WebView",
                query_focus=self._topic_focus(brief, fallback="interactive experience"),
                recommended_minutes=3,
            )
        elif wants_website:
            website_title = "Supporting website or WebView content"
            if is_education:
                website_title = "Education website or explainer page"
            elif wants_model:
                website_title = "Model viewer or comparison web route"
            add_item(
                title=website_title,
                content_type="website",
                source="Planned asset",
                notes=["Confirm the URL, reachability, and whether the operator should switch in and out of it live."],
                layer_type="WebView",
                query_focus=self._topic_focus(brief, fallback="website"),
                recommended_minutes=2,
            )

        if wants_image:
            image_title = "Supporting stills or overlay graphics"
            if is_heritage:
                image_title = "Archival image set"
            elif self._contains_any(normalized, {"diagram", "diagrams"}):
                image_title = "Process diagram overlays"
            add_item(
                title=image_title,
                content_type="image",
                source="Planned asset",
                notes=["Use stills, diagrams, or overlays when a full interactive route is unnecessary."],
                layer_type="Image",
                query_focus=self._topic_focus(brief, fallback="supporting visuals"),
                recommended_minutes=2 if is_heritage else 1,
            )

        if wants_model or wants_product_model:
            model_query_focus = self._topic_focus(brief, fallback="bim model")
            if "new product" in normalized:
                model_query_focus = "new product"
            elif wants_product_model:
                model_query_focus = "product model"
            add_item(
                title="Model review source",
                content_type="3d model",
                source="Planned asset",
                notes=["Choose the viewer route first, then confirm markups, comparison views, and meeting control."],
                layer_type="ModelViewer",
                query_focus=model_query_focus,
                recommended_minutes=4,
            )

        if wants_live_feed:
            add_item(
                title="Live feed or collaboration source",
                content_type="standard video",
                source="Live route",
                notes=["Plan this as an NDI, camera, shared-canvas, or conferencing route rather than generic web content."],
                layer_type="Video",
                query_focus=f"{self._topic_focus(brief, fallback='live collaboration')} NDI live feed",
                recommended_minutes=2,
            )

        if is_education and not any(item.content_type == "website" for item in items):
            add_item(
                title="Education web explainer",
                content_type="interactive web" if wants_interactive_web else "website",
                source="Planned asset",
                notes=["Use this for the explainer page, process walkthrough, or lightweight interactive reference."],
                layer_type="WebView",
                query_focus=f"{self._topic_focus(brief, fallback='education')} education {'interactive experience' if wants_interactive_web else 'website'}",
                recommended_minutes=2,
            )

        if is_education and self._contains_any(normalized, {"diagram", "overlay", "overlays", "machinery"}) and not any(item.title == "Process diagram overlays" for item in items):
            add_item(
                title="Process diagram overlays",
                content_type="image",
                source="Planned asset",
                notes=["Use these as triggered callouts or supporting visuals over the main teaching content."],
                layer_type="Image",
                query_focus=f"{self._topic_focus(brief, fallback='process')} process diagram",
                recommended_minutes=1,
            )

        if is_accessibility and not any(item.title == "Accessible navigation graphics" for item in items):
            add_item(
                title="Accessible navigation graphics",
                content_type="image",
                source="Planned asset",
                notes=["Use large, simple labels or iconography if the experience needs a low-cognitive-load launch surface."],
                layer_type="Image",
                query_focus=f"{self._topic_focus(brief, fallback='accessible')} navigation graphics",
                recommended_minutes=1,
            )

        if wants_trigger_flow and not any("trigger" in item.title.lower() or "hotspot" in item.title.lower() for item in items):
            add_item(
                title="Trigger or hotspot graphic set",
                content_type="image",
                source="Planned asset",
                notes=["Use this for reveal icons, hotspot targets, or simple action-driven callouts over the main scene."],
                layer_type="Image",
                query_focus=f"{self._topic_focus(brief, fallback='interactive')} hotspot icons",
                recommended_minutes=1,
            )

        if is_multi_use and not any(item.title == "Alternate scenario media" for item in items):
            add_item(
                title="Alternate scenario media",
                content_type="standard video",
                source="Planned asset",
                notes=["Use this as a second scenario or fallback media state so the room can switch quickly between use cases."],
                layer_type="Video",
                query_focus=self._topic_focus(brief, fallback="event loop"),
                recommended_minutes=2,
            )

        if wants_switching and not any(item.title == "Launch menu graphics" for item in items):
            add_item(
                title="Launch menu graphics",
                content_type="image",
                source="Planned asset",
                notes=["Use this for the Home or Content Bank launch surface so switching remains clear and repeatable."],
                layer_type="Image",
                query_focus=f"{self._topic_focus(brief, fallback='launch')} menu graphics",
                recommended_minutes=1,
            )

        if not items:
            add_item(
                title="Main content item",
                content_type="mixed media",
                source="Planned asset",
                notes=["Select the final media path before locking the session build."],
                layer_type="Layer",
                query_focus=self._topic_focus(brief, fallback="immersive content"),
                recommended_minutes=3,
            )

        if sum(item.recommended_minutes for item in items) < min(target_duration_minutes - 1, 8):
            add_item(
                title="Intro or reset media segment",
                content_type="standard video",
                source="Planned asset",
                notes=["Add a short opener, branded reset loop, or recap segment so the room has a cleaner start/end state."],
                layer_type="Video",
                query_focus=f"{self._topic_focus(brief, fallback='intro')} intro video",
                recommended_minutes=2,
            )

        if wants_multi_wall_review and not any("Launch menu graphics" == item.title for item in items):
            add_item(
                title="Review launcher or layout labels",
                content_type="image",
                source="Planned asset",
                notes=["Use clear labels if the operator needs to move between review modes or wall layouts quickly."],
                layer_type="Image",
                query_focus=f"{self._topic_focus(brief, fallback='review')} menu graphics",
                recommended_minutes=1,
            )

        return items

    def _layer_drafts(
        self,
        brief: str,
        assessment: CapabilityAssessment,
        selected_content: list[ContentCandidate],
        session_import: SessionImportSummary | None,
    ) -> list[LayerDraft]:
        layers: list[LayerDraft] = []
        normalized = brief.lower()
        for index, item in enumerate(selected_content, start=1):
            layers.append(
                LayerDraft(
                    layer_id=f"draft-layer-{index}",
                    label=item.title,
                    layer_type=item.recommended_layer_type,
                    purpose=self._layer_purpose(item.content_type, item.title),
                    source_candidate_id=item.candidate_id,
                    key_settings=self._default_settings(item.content_type, item.title, session_import),
                )
            )

        if self._contains_any(normalized, {"switch", "switching", "switchable", "adaptable", "multi-use", "future-proof", "scenario"}) or any(
            "content bank" in surface.lower() for surface in assessment.build_approach.runtime_surfaces
        ):
            layers.append(
                LayerDraft(
                    layer_id=f"draft-layer-{len(layers) + 1}",
                    label="Content Bank switcher",
                    layer_type="ContentBank",
                    purpose="Switch between prepared content states without leaving the operator workflow.",
                    source_candidate_id=None,
                    key_settings=["Group content into clear scenarios", "Use large tiles", "Keep the order operator-friendly"],
                )
            )

        if self._contains_any(normalized, {"trigger", "triggers", "actions", "icon", "icons", "tap", "button", "buttons", "home"}) or any(
            "home" in surface.lower() for surface in assessment.build_approach.runtime_surfaces
        ):
            layers.append(
                LayerDraft(
                    layer_id=f"draft-layer-{len(layers) + 1}",
                    label="Home / trigger surface",
                    layer_type="Home",
                    purpose="Launch prepared scenes, reveal supporting material, or send the operator back to a clear start state.",
                    source_candidate_id=None,
                    key_settings=["Large launch targets", "Simple reset path", "Keep labels short and obvious"],
                )
            )

        return layers

    def _workflow_steps(
        self,
        brief: str,
        assessment: CapabilityAssessment,
        selected_content: list[ContentCandidate],
        layer_drafts: list[LayerDraft],
    ) -> list[WorkflowStep]:
        steps: list[WorkflowStep] = []
        step_index = count(1)
        normalized = brief.lower()

        if any(layer.layer_type in {"Home", "ContentBank"} for layer in layer_drafts):
            steps.append(
                WorkflowStep(
                    step_id=f"step-{next(step_index)}",
                    label="Open the session and orient the room",
                    minutes=1,
                    summary="Use the launch surface to start in a clean, repeatable state before switching into the main content.",
                    source_candidate_id=None,
                )
            )

        for item in selected_content:
            steps.append(
                WorkflowStep(
                    step_id=f"step-{next(step_index)}",
                    label=item.title,
                    minutes=item.recommended_minutes,
                    summary=self._workflow_summary(item, normalized),
                    source_candidate_id=item.candidate_id,
                )
            )

        if len(selected_content) > 1 or self._contains_any(normalized, {"operator-driven", "operator driven", "repeatable", "reusable"}):
            steps.append(
                WorkflowStep(
                    step_id=f"step-{next(step_index)}",
                    label="Reset or return to launcher",
                    minutes=1,
                    summary="End on a stable state so the next operator run starts cleanly.",
                    source_candidate_id=None,
                )
            )

        if assessment.build_approach.control_interaction_fit == "needs review":
            steps.append(
                WorkflowStep(
                    step_id=f"step-{next(step_index)}",
                    label="Check controls before client-facing use",
                    minutes=1,
                    summary="Dry-run the trigger flow, switching order, or interaction logic before treating the draft as presentation-ready.",
                    source_candidate_id=None,
                )
            )

        return steps

    def _recommendations(
        self,
        brief: str,
        assessment: CapabilityAssessment,
        selected_content: list[ContentCandidate],
        layer_drafts: list[LayerDraft],
        target_duration_minutes: int,
        estimated_duration_minutes: int,
        duration_gap_minutes: int,
    ) -> list[BuilderRecommendation]:
        normalized = brief.lower()
        recommendations: list[BuilderRecommendation] = []
        content_types = {item.content_type for item in selected_content}
        layer_types = {layer.layer_type for layer in layer_drafts}

        if duration_gap_minutes > 0:
            detail = f"This draft only covers about {estimated_duration_minutes} minutes. "
            if "360 video" in content_types:
                detail += f"Add another supporting beat such as archival stills, a PDF panel, or a reference website to reach at least {target_duration_minutes} minutes cleanly."
            elif "3d model" in content_types:
                detail += f"Add a markup, dashboard, or comparison state so the session lands closer to {target_duration_minutes} minutes without feeling repetitive."
            else:
                detail += f"Add another prepared segment or reference panel to reach at least {target_duration_minutes} minutes cleanly."
            recommendations.append(
                BuilderRecommendation(
                    title="Extend the runtime",
                    detail=detail,
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"heritage", "storytelling", "archival"}) and "image" not in content_types:
            recommendations.append(
                BuilderRecommendation(
                    title="Add archival support material",
                    detail="Pair the main immersive scene with archival stills, posters, or timeline documents so the story has clear reference moments rather than one continuous video pass.",
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"education", "stem", "classroom", "school"}) and not {"website", "image", "pdf"} & content_types:
            recommendations.append(
                BuilderRecommendation(
                    title="Add a teaching support layer",
                    detail="Bring in either a process diagram, a reference website, or a PDF handout so the session feels like a lesson rather than just media playback.",
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"trigger", "triggers", "actions", "icon", "icons", "tap", "button", "buttons"}) and "Home" not in layer_types:
            recommendations.append(
                BuilderRecommendation(
                    title="Add a simple trigger surface",
                    detail="Use a Home or trigger layer for the reveal actions instead of burying everything in the main media layer.",
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"multi-use", "future-proof", "switch", "switching", "adaptable"}) and "ContentBank" not in layer_types:
            recommendations.append(
                BuilderRecommendation(
                    title="Group the session into scenarios",
                    detail="Use Content Bank or a simple launch menu so heritage, education, and event states are clearly separated and easy to relaunch.",
                    priority="medium",
                )
            )

        if self._contains_any(normalized, {"accessible", "inclusive", "subtitles", "wheelchair", "neurodiverse"}) and not self._contains_any(
            " ".join(item.title.lower() for item in selected_content),
            {"navigation", "caption", "subtitle"},
        ):
            recommendations.append(
                BuilderRecommendation(
                    title="Design the accessibility layer explicitly",
                    detail="Treat subtitles, launch simplicity, and true-perspective setup as part of the build plan rather than assuming the media alone solves accessibility.",
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"accessible", "inclusive", "subtitles", "wheelchair", "neurodiverse"}):
            recommendations.append(
                BuilderRecommendation(
                    title="Lock the accessibility pass",
                    detail="Decide how subtitles, launch simplicity, and viewing-height assumptions will be handled before treating the draft as audience-ready.",
                    priority="medium",
                )
            )

        if self._contains_any(normalized, {"multi-use", "future-proof", "switch", "switching", "adaptable"}) and "ContentBank" in layer_types:
            recommendations.append(
                BuilderRecommendation(
                    title="Define the scenario states",
                    detail="Name the exact launch states you want, for example opener, main scene, reference panel, and reset state, so the Content Bank stays clear instead of becoming a loose media list.",
                    priority="medium",
                )
            )

        if self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk"}) and "3d model" not in content_types:
            recommendations.append(
                BuilderRecommendation(
                    title="Anchor the session on the main review surface",
                    detail="Pick one primary AECO runtime surface first, such as Revizto, a model viewer, or a BIM web route, then add dashboards and collaboration views around it.",
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"education", "stem", "classroom", "teacher", "students", "lesson"}):
            recommendations.append(
                BuilderRecommendation(
                    title="Keep the lesson to a few strong teaching beats",
                    detail="Plan the room like a class: immersive opener, guided explanation, one interaction or reveal moment, then recap/reset. Too many states make the lesson feel messy rather than immersive.",
                    priority="medium",
                )
            )

        if self._contains_any(normalized, {"health", "safety", "training", "simulation"}):
            recommendations.append(
                BuilderRecommendation(
                    title="Make the training objective explicit",
                    detail="For safety training, tie each scene or interaction to one hazard, decision, or learning outcome, and include a replay/debrief path instead of treating the room as passive media playback.",
                    priority="high",
                )
            )

        if self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk"}) and self._contains_any(normalized, {"teams", "remote", "hybrid", "dashboard"}):
            recommendations.append(
                BuilderRecommendation(
                    title="Stage the collaboration flow",
                    detail="Lead with the model first, then bring in dashboards or hybrid participation as a deliberate second beat so the review stays clear and professional.",
                    priority="medium",
                )
            )

        if assessment.build_approach.control_interaction_fit == "needs review":
            recommendations.append(
                BuilderRecommendation(
                    title="Dry-run the control flow",
                    detail="The content types are plausible, but the switching or reveal logic still needs a quick operator rehearsal before this becomes a polished demo.",
                    priority="medium",
                )
            )

        if not recommendations:
            detail = "The overall route is coherent. The next step is to replace placeholders with the real files, links, or apps you want to present."
            if {"standard video", "pdf", "website"} <= content_types:
                detail = "Replace the placeholder video, PDF, and website with the exact assets you want, then save them into one reusable session and test the switching order."
            elif "360 video" in content_types and "image" in content_types:
                detail = "Lock the main 360 source first, then choose the archive stills or supporting visuals that should appear between the immersive beats."
            elif "3d model" in content_types:
                detail = "Choose the primary AECO runtime surface first, then decide whether dashboards, markups, or collaboration views live beside it or in separate switch states."
            recommendations.append(
                BuilderRecommendation(
                    title="Lock the actual content sources",
                    detail=detail,
                    priority="medium",
                )
            )

        return recommendations[:5]

    def _setup_archetype(
        self,
        brief: str,
        selected_content: list[ContentCandidate],
        session_import: SessionImportSummary | None,
    ) -> str:
        normalized = brief.lower()
        imported_name = (session_import.session_name.lower() if session_import else "")
        combined = " ".join(
            [
                normalized,
                imported_name,
                " ".join(item.title.lower() for item in selected_content),
                " ".join(item.content_type.lower() for item in selected_content),
                " ".join((item.layout_role or "").lower() for item in selected_content),
            ]
        )
        content_types = {item.content_type.lower() for item in selected_content}
        if any((item.setup_archetype or "") for item in selected_content):
            ranked = [item.setup_archetype for item in selected_content if item.setup_archetype]
            if ranked:
                return ranked[0]
        if self._contains_any(combined, {"miro", "whiteboard", "board", "canvas", "workshop"}) and self._contains_any(combined, {"three walls", "3 walls", "collaboration", "display"}):
            return "three_wall_canvas"
        if self._contains_any(combined, {"dashboard", "powerbi", "power bi", "graph", "graphs", "strategic review", "sales dashboard", "internal sales"}) or (
            "dashboard app" in content_types and ("3d model" in content_types or self._contains_any(combined, {"sketchfab", "nasa", "esa"}))
        ):
            return "three_wall_dashboard"
        if self._contains_any(combined, {"content bank", "contentbank", "switch", "switching", "multi-use", "future-proof", "launcher", "home"}) and self._contains_any(combined, {"gallery", "bank", "scenario", "repeatable", "switchable"}):
            return "content_bank_gallery"
        if self._contains_any(combined, {"slides", "presentation", "deck", "briefing"}) and "website" in content_types:
            return "three_wall_presentation"
        if "3d model" in content_types or self._contains_any(combined, {"matterport", "model viewer", "revizto", "autodesk", "archvis"}):
            return "immersive_model_viewer"
        if self._contains_any(combined, {"thinglink", "streetview", "cenariovr", "avatour", "virtual tour", "webxr", "interactive web"}) or "interactive web" in content_types:
            return "interactive_tour_webapp"
        if "360 video" in content_types or self._contains_any(combined, {"youtube 360", "airpano", "travel", "trip", "heritage", "underwater", "space journey"}):
            return "immersive_hero_360"
        return "single_surface_reference"

    def _setup_summary(self, setup_archetype: str, selected_content: list[ContentCandidate]) -> str:
        content_titles = [item.title for item in selected_content[:3]]
        summaries = {
            "immersive_hero_360": "Use one main immersive hero scene, then keep any PDF, website, archive, or support clips as smaller reference panels or later switch states.",
            "three_wall_canvas": "Use one collaboration or canvas app stretched intentionally across the three main walls so the room becomes one larger shared working surface.",
            "three_wall_dashboard": "Assign one meaningful source per wall, for example dashboard, interactive model, and support site, so the room reads like a deliberate review environment rather than stacked panels.",
            "content_bank_gallery": "Treat the room as a bank of prepared states that the operator can switch between cleanly instead of leaving every media item visible at once.",
            "three_wall_presentation": "Use a wide front-facing presentation surface when the core experience is one slide deck, one board, or one long-format web presentation.",
            "immersive_model_viewer": "Anchor the room on a single model or pano viewer route, then add only the minimum support surfaces needed for markups, dashboards, or operator controls.",
            "interactive_tour_webapp": "Use one interactive tour surface as the main experience, not a generic brochure page, and keep any support material secondary.",
            "single_surface_reference": "Keep the room simple around one main surface first, then add support panels only if they improve the operator flow.",
        }
        summary = summaries.get(setup_archetype, summaries["single_surface_reference"])
        if content_titles:
            summary += f" Current lead items: {', '.join(content_titles)}."
        return summary

    def _assign_setup_roles(self, selected_content: list[ContentCandidate], setup_archetype: str) -> None:
        for item in selected_content:
            item.setup_archetype = setup_archetype
            item.setup_notes = list(item.setup_notes or [])

        if not selected_content:
            return

        if setup_archetype == "three_wall_canvas":
            selected_content[0].layout_role = "three-wall span"
            selected_content[0].setup_notes.append("This content should be stretched intentionally across the main walls as one shared canvas.")
            for item in selected_content[1:]:
                item.layout_role = item.layout_role or "support panel"
            return

        if setup_archetype == "three_wall_dashboard":
            role_order = ["left wall", "center wall", "right wall", "launcher / support"]
            for index, item in enumerate(selected_content):
                item.layout_role = role_order[min(index, len(role_order) - 1)]
            return

        if setup_archetype == "content_bank_gallery":
            if selected_content:
                selected_content[0].layout_role = "content bank hero"
                selected_content[0].setup_notes.append("Treat this as the first launch state in a bank of prepared scenarios.")
            for item in selected_content[1:]:
                item.layout_role = item.layout_role or "bank entry"
            return

        if setup_archetype == "immersive_model_viewer":
            selected_content[0].layout_role = "hero wall"
            selected_content[0].setup_notes.append("Keep the main viewer dominant and avoid cluttering the room with too many equal-weight panels.")
            for item in selected_content[1:]:
                item.layout_role = item.layout_role or "support panel"
            return

        if setup_archetype == "immersive_hero_360":
            selected_content[0].layout_role = "immersive background"
            selected_content[0].setup_notes.append("This should read as the main wraparound scene.")
            for item in selected_content[1:]:
                item.layout_role = item.layout_role or "pinned support"
            return

        if setup_archetype == "three_wall_presentation":
            selected_content[0].layout_role = "three-wall span"
            for item in selected_content[1:]:
                item.layout_role = item.layout_role or "support panel"
            return

        for item in selected_content:
            item.layout_role = item.layout_role or "main surface"

    def _build_readiness_score(
        self,
        assessment: CapabilityAssessment,
        selected_content: list[ContentCandidate],
        recommendations: list[BuilderRecommendation],
        duration_gap_minutes: int,
    ) -> int:
        content_component = round(sum(item.readiness_score for item in selected_content) / max(len(selected_content), 1))
        assessment_component = round(assessment.confidence * 100)
        score = round((assessment_component * 0.52) + (content_component * 0.48))
        if OperationalFlag.NEEDS_HUMAN_REVIEW in assessment.operational_flags:
            score -= 5
        if duration_gap_minutes > 0:
            score -= min(12, duration_gap_minutes * 2)
        if any(item.priority == "high" for item in recommendations):
            score -= 4
        return max(0, min(100, score))

    def _readiness_label(self, score: int) -> str:
        if score >= 80:
            return "Ready to configure"
        if score >= 60:
            return "Promising with checks"
        if score >= 40:
            return "Needs content and review"
        return "Not ready yet"

    def _search_suggestions(self, selected_content: list[ContentCandidate]) -> list[dict[str, str]]:
        suggestions: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in selected_content:
            mode = self._search_mode_for(item)
            query = item.query_hint
            key = (mode, query.lower())
            if query and key not in seen:
                suggestions.append({"mode": mode, "query": query})
                seen.add(key)
        return suggestions[:6] or [{"mode": "website", "query": "immersive content"}]

    def _target_duration_minutes(self, brief: str) -> int:
        match = re.search(r"(\d+)\s*-\s*minute|(\d+)\s*minute", brief.lower())
        if match:
            value = next((group for group in match.groups() if group), None)
            if value:
                return max(DEFAULT_TARGET_DURATION, int(value))
        return DEFAULT_TARGET_DURATION

    def _suggest_structure(self, brief: str, assessment: CapabilityAssessment) -> StructureProfile:
        normalized = brief.lower()
        if self._contains_any(normalized, {"miro", "dashboard", "powerbi", "power bi", "three walls", "3 walls", "collaboration board"}):
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "cave")
        if self._contains_any(normalized, {"dome", "planetarium", "sky", "astronomy"}):
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "dome")
        if self._contains_any(normalized, {"360", "panoramic", "surround", "wraparound"}):
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "cylinder")
        if self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk", "review", "collaboration", "dashboard", "powerbi", "sales meeting"}):
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "cave")
        if self._contains_any(normalized, {"classroom", "education", "stem", "teacher", "students"}):
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "cube")
        if self._contains_any(normalized, {"museum", "heritage", "storytelling", "showroom"}):
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "immersive-workspace")
        if assessment.build_approach.validation_posture == "app/integration-risk workflow":
            return next(item for item in STRUCTURE_PROFILES if item.structure_id == "cave")
        return STRUCTURE_PROFILES[0]

    def _suggested_structure_reason(self, brief: str, structure: StructureProfile, setup_archetype: str) -> str:
        normalized = brief.lower()
        if setup_archetype == "three_wall_canvas":
            return "A CAVE-style or multi-wall room is the right fit when one app like Miro should become a larger shared canvas across the main walls."
        if setup_archetype == "three_wall_dashboard":
            return "A CAVE-style setup is the best fit when each wall needs a distinct review surface, such as dashboard, 3D model, and support web content."
        if setup_archetype == "content_bank_gallery":
            return "A flexible immersive workspace is a strong fit when the operator needs to switch between prepared media states through Home or Content Bank."
        if structure.structure_id == "cylinder":
            return "A cylinder is a good fit when the brief is anchored around immersive 360 media and wraparound viewing."
        if structure.structure_id == "cave":
            if self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk"}):
                return "A CAVE-style setup is a strong fit for collaborative AECO reviews because it favors shared sight lines and controlled comparison states."
            if self._contains_any(normalized, {"dashboard", "powerbi", "sales meeting", "strategic review"}):
                return "A CAVE-style setup works well for strategic reviews because it can carry deliberate left, center, and right wall states without reducing the room to a single flat screen."
            return "A CAVE-style setup is a good fit when collaboration and multi-surface control matter more than a single cinematic wraparound scene."
        if structure.structure_id == "cube":
            return "A cube-style room works well for guided classes and compact operator-led sessions where the group needs a focused front-facing teaching flow."
        if structure.structure_id == "dome":
            return "A dome is best when the content is sky, environmental, or cinematic and the geometry itself is part of the effect."
        return "A general immersive workspace is the most flexible starting point for mixed-media storytelling, launch surfaces, and repeatable demos."

    def _demo_plan_notes(self, brief: str) -> list[str]:
        normalized = brief.lower()
        notes = list(DEMO_NOTES["generic"])
        if self._contains_any(normalized, {"education", "stem", "classroom", "teacher", "students", "lesson"}):
            notes = DEMO_NOTES["education"] + notes
        elif self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk", "markups", "dashboard"}):
            notes = DEMO_NOTES["aeco"] + notes
        elif self._contains_any(normalized, {"heritage", "museum", "storytelling", "archival"}):
            notes = DEMO_NOTES["heritage"] + notes
        if self._contains_any(normalized, {"health", "safety", "training", "simulation"}):
            notes.insert(0, "For immersive safety training, keep the learning objective explicit and make every branch or reveal map to a single training decision or hazard.")
            notes.insert(1, "Treat debrief and replay as part of the plan so the experience supports retention rather than just immersion.")
        return notes[:4]

    def _topic_focus(self, brief: str, fallback: str) -> str:
        normalized = self._normalized_brief_text(brief)
        for source, target in TOPIC_NORMALIZATIONS.items():
            normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
        trip_match = re.search(
            r"(?:trip to|travel to|visit to|journey to|tour of|tour to)\s+([a-z0-9\s-]{2,40}?)(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if trip_match:
            candidate = self._clean_topic_candidate(trip_match.group(1))
            if candidate:
                return candidate
        guided_trip_match = re.search(
            r"(?:take|bring|transport)(?:\s+[a-z0-9-]+){0,8}?\s+to\s+([a-z0-9\s-]{2,40}?)(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if guided_trip_match:
            candidate = self._clean_topic_candidate(guided_trip_match.group(1))
            if candidate:
                return candidate
        experience_to_match = re.search(
            r"(?:trip|travel|journey|tour|experience)(?:\s+[a-z0-9-]+){0,3}?\s+to\s+([a-z0-9\s-]{2,40}?)(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if experience_to_match:
            candidate = self._clean_topic_candidate(experience_to_match.group(1))
            if candidate:
                return candidate
        see_like_match = re.search(
            r"(?:see|show|showing|explore)(?:\s+[a-z0-9-]+){0,4}?\s+what\s+([a-z0-9\s-]{2,40}?)\s+is\s+like(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if see_like_match:
            candidate = self._clean_topic_candidate(see_like_match.group(1))
            if candidate:
                return candidate
        feel_like_match = re.search(
            r"feel\s+like(?:\s+[a-z0-9-]+){0,4}?\s+in\s+([a-z0-9\s-]{2,40}?)(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if feel_like_match:
            candidate = self._clean_topic_candidate(feel_like_match.group(1))
            if candidate:
                return candidate
        into_match = re.search(
            r"(?:drops?|drop|transport|transports?|take|takes|bring|brings)(?:\s+[a-z0-9-]+){0,8}?\s+(?:into|to)\s+([a-z0-9\s-]{2,40}?)(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if into_match:
            candidate = self._clean_topic_candidate(into_match.group(1))
            if candidate:
                return candidate
        around_match = re.search(
            r"(?:around|about)\s+([a-z0-9\s-]{2,40}?)(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if around_match:
            candidate = self._clean_topic_candidate(around_match.group(1))
            if candidate:
                return candidate
        there_match = re.search(
            r"([a-z0-9\s-]{2,40}?)\s+as\s+if(?:\s+[a-z0-9-]+){0,4}?\s+there(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if there_match:
            candidate = self._clean_topic_candidate(there_match.group(1))
            if candidate:
                return candidate
        plain_like_match = re.search(
            r"what\s+([a-z0-9\s-]{2,40}?)\s+is\s+like(?=\s+(?:using|with|via|for|and|where|that|which|so)\b|[,.]|$)",
            normalized,
        )
        if plain_like_match:
            candidate = self._clean_topic_candidate(plain_like_match.group(1))
            if candidate:
                return candidate
        travel_match = re.search(
            r"(?:transported to|set in|focused on|about|inside|around)\s+([a-z0-9\s-]{3,40}?)(?=\s+(?:using|with|via|for|and)\b|[,.]|$)",
            normalized,
        )
        if travel_match:
            candidate = self._clean_topic_candidate(travel_match.group(1))
            if candidate:
                return candidate
        hits: list[str] = []
        for phrase in TOPIC_PHRASES:
            if phrase in normalized and phrase not in hits:
                hits.append(phrase)
        if hits:
            return " ".join(hits[:2])
        tokens: list[str] = []
        for token in re.findall(r"[a-z0-9][a-z0-9\-]+", normalized):
            if token in STOPWORDS:
                continue
            token = TOPIC_NORMALIZATIONS.get(token, token)
            for part in token.split():
                if part in STOPWORDS:
                    continue
                if part.isdigit() and not tokens:
                    continue
                if part not in tokens:
                    tokens.append(part)
            if len(tokens) == 3:
                break
        return " ".join(tokens) if tokens else fallback

    def _clean_topic_candidate(self, value: str) -> str:
        cleaned = re.sub(
            r"\b(class|lesson|experience|session|demo|group|students?|student|teachers?|teacher|audience|immersive|travel|travelling|traveling|what|like|want|see|show|showing|explore|them)\b",
            " ",
            value,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
        tokens: list[str] = []
        for token in cleaned.split():
            if token not in tokens:
                tokens.append(token)
        return " ".join(tokens)

    def _focused_query(self, brief_or_focus: str, content_type: str, title: str = "") -> str:
        raw_focus = self._normalized_brief_text(brief_or_focus)
        if raw_focus.endswith("menu graphics") or raw_focus.endswith("navigation graphics") or raw_focus.endswith("ndi live feed") or raw_focus.endswith("process diagram") or raw_focus.endswith("education website") or raw_focus.endswith("intro video") or raw_focus.endswith("sales dashboard") or raw_focus.endswith("comparison dashboard"):
            return raw_focus
        focus = self._topic_focus(brief_or_focus, fallback=title or "immersive content")
        title_focus = self._topic_focus(title, fallback=title or "content") if title else ""
        if not focus or focus in {"pdf", "website", "video", "content", "explainer"}:
            focus = title_focus or focus or "content"
        normalized = self._normalized_brief_text(brief_or_focus)
        if content_type == "360 video":
            if self._contains_any(normalized, {"trip to", "travel to", "journey to", "tour of", "tour to", "visit to"}):
                return f"{focus} YouTube 360 4K"
            if self._contains_any(normalized, {"heritage", "archival", "museum", "historic"}):
                if "steel" in normalized or "industrial" in normalized:
                    return "industrial heritage site YouTube 360 4K"
                return "historic site YouTube 360 4K"
            if self._contains_any(normalized, {"youtube", "360", "immersive", "heritage", "safari", "nasa"}):
                return f"{focus} YouTube 360 4K"
            return f"{focus} YouTube 360 4K"
        if content_type == "standard video":
            if focus.endswith("video") or focus.endswith("feed"):
                return focus
            if self._contains_any(normalized, {"camera", "feed", "ndi", "teams"}):
                return f"{focus} NDI live feed"
            return f"{focus} explainer video"
        if content_type == "pdf":
            if focus.endswith("pdf"):
                return focus
            if "timeline" in normalized:
                return f"{focus} timeline pdf"
            if self._contains_any(normalized, {"machinery", "specification", "specifications"}):
                return f"{focus} machinery specification pdf"
            if "lesson" in normalized:
                return f"{focus} lesson plan pdf"
            return f"{focus} pdf"
        if content_type == "website":
            if focus.endswith("website") or focus.endswith("webview"):
                return focus
            if self._contains_any(normalized, {"education", "lesson", "classroom", "teacher", "students"}):
                return f"{focus} lesson website"
            if self._contains_any(normalized, {"revizto", "autodesk", "bim", "aeco"}):
                return f"{focus} revizto autodesk bim"
            if self._contains_any(normalized, {"webxr", "interactive 360"}):
                return f"{focus} WebXR"
            return f"{focus} website"
        if content_type == "interactive web":
            if self._contains_any(normalized, {"thinglink"}):
                return f"{focus} ThingLink interactive experience"
            if self._contains_any(normalized, {"bus", "transport", "tfl"}):
                return f"{focus} interactive 360 bus web app"
            if self._contains_any(normalized, {"heritage", "museum", "archival"}):
                return f"{focus} interactive museum virtual tour"
            if self._contains_any(normalized, {"education", "lesson", "classroom"}):
                return f"{focus} interactive 360 learning experience"
            if self._contains_any(normalized, {"webxr"}):
                return f"{focus} WebXR interactive experience"
            return f"{focus} interactive web experience"
        if content_type == "dashboard app":
            if self._contains_any(normalized, {"sales", "powerbi", "power bi", "dashboard", "graph", "graphs", "kpi"}):
                return f"{focus} Power BI dashboard"
            if self._contains_any(normalized, {"teams", "hybrid", "remote"}):
                return f"{focus} Teams collaboration dashboard"
            return f"{focus} dashboard app"
        if content_type == "image":
            if focus.endswith("menu graphics") or focus.endswith("navigation graphics") or focus.endswith("reference image") or focus.endswith("archival image") or focus.endswith("process diagram"):
                return focus
            if self._contains_any(normalized, {"archival", "heritage", "museum"}):
                heritage_focus = re.sub(r"\barchival\b", " ", focus).strip()
                heritage_focus = re.sub(r"\s+", " ", heritage_focus).strip()
                return f"{heritage_focus or 'historic'} archival image"
            if self._contains_any(normalized, {"diagram", "overlay", "overlays"}):
                return f"{focus} process diagram"
            if self._contains_any(normalized, {"navigation", "menu", "icon", "icons"}):
                return f"{focus} menu graphics"
            return f"{focus} reference image"
        if content_type == "3d model":
            if self._contains_any(normalized, {"aeco", "bim", "revizto", "autodesk"}):
                return f"{focus} Revizto Autodesk BIM"
            return f"{focus} Sketchfab model"
        return focus

    def _normalized_brief_text(self, brief: str) -> str:
        cleaned = re.sub(r"\bbrief:\b|\bnotes:\b", " ", brief, flags=re.IGNORECASE)
        cleaned = re.sub(r"[^\w\s\-]+", " ", cleaned.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _search_mode_for(self, item: ContentCandidate) -> str:
        if item.content_type == "360 video":
            return "youtube_360"
        if item.content_type == "interactive web":
            return "immersive_web"
        if item.content_type == "dashboard app":
            return "review_app"
        if item.content_type == "3d model":
            return "interactive_model"
        if "webxr" in item.query_hint.lower():
            return "webxr"
        return "website"

    def _layer_purpose(self, content_type: str, title: str) -> str:
        mapping = {
            "360 video": "Main immersive background layer",
            "standard video": "Primary playback or live-feed layer",
            "pdf": "Supporting document layer",
            "website": "WebView information layer",
            "interactive web": "Interactive WebView layer",
            "dashboard app": "Live review wall",
            "image": "Supporting still, menu, or overlay layer",
            "3d model": "Model review layer",
        }
        if "menu" in title.lower() or "navigation" in title.lower():
            return "Launch and navigation support layer"
        return mapping.get(content_type, "Supporting content layer")

    def _default_settings(self, content_type: str, title: str, session_import: SessionImportSummary | None) -> list[str]:
        settings = ["Confirm final operator flow"]
        if content_type == "360 video":
            settings.extend(["Prefer 4K+ source", "Check perspective route", "Check audio sync"])
        elif content_type == "pdf":
            settings.extend(["Use readable export", "Check zoom/scale in-room"])
        elif content_type == "website":
            settings.extend(["Confirm reachability", "Choose WebView route"])
        elif content_type == "interactive web":
            settings.extend(["Confirm WebView behavior", "Check touch or control affordance", "Check load time in-room"])
        elif content_type == "dashboard app":
            settings.extend(["Confirm login and refresh behavior", "Choose wall placement", "Check live data readability"])
        elif content_type == "3d model":
            settings.extend(["Confirm viewer route", "Confirm operator control model"])
        elif "menu" in title.lower() or "navigation" in title.lower():
            settings.extend(["Use large targets", "Keep labels short", "Test reset flow"])
        if session_import is not None:
            settings.append("Compare against imported session settings")
        return settings

    def _base_minutes_for(self, content_type: str) -> int:
        return {
            "360 video": 4,
            "standard video": 3,
            "pdf": 2,
            "website": 2,
            "interactive web": 3,
            "dashboard app": 3,
            "image": 1,
            "3d model": 4,
            "mixed media": 3,
        }.get(content_type, 2)

    def _workflow_summary(self, item: ContentCandidate, normalized_brief: str) -> str:
        if item.content_type == "360 video":
            return "Run the main immersive moment here, then use other layers or launch controls to branch into supporting material."
        if item.content_type == "website":
            if "dashboard" in item.title.lower():
                return "Use this when you need live operational context rather than a purely cinematic sequence."
            return "Use this as the supporting explainer, dashboard, or reference page in the room."
        if item.content_type == "interactive web":
            return "Use this as the live interactive surface, for example a ThingLink scene, virtual tour, or other demo-worthy web experience."
        if item.content_type == "dashboard app":
            return "Place this on one wall as part of a deliberate multi-surface review layout rather than treating it like generic web filler."
        if item.content_type == "pdf":
            return "Bring this in when you need a readable reference moment such as a lesson plan, timeline, or specification sheet."
        if item.content_type == "image":
            if self._contains_any(normalized_brief, {"archival", "heritage"}):
                return "Use this for archive stills or scene-setting support between larger media beats."
            return "Use this for diagrams, overlays, menu graphics, or other quick-support visuals."
        if item.content_type == "3d model":
            return "Anchor the collaborative review here before switching out to markups, dashboards, or meeting views."
        return "Use this as a supporting segment in the session."

    def _contains_any(self, text: str, values: set[str]) -> bool:
        return any(value in text for value in values)
