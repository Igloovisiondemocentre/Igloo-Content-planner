from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from igloo_experience_builder.builder.session_parser import IceSessionParser
from igloo_experience_builder.config.settings import Settings


@dataclass(slots=True)
class SampleCatalogEntry:
    session_name: str
    title: str
    query_text: str
    session_path: Path
    asset_location: str
    content_type: str
    recommended_layer_type: str
    resolution_label: str
    provider: str
    snippet: str
    notes: list[str]
    root_label: str
    curated_rank: int
    setup_archetype: str
    setup_summary: str
    layout_role: str


SESSION_PROFILES: dict[str, dict[str, object]] = {
    "archvis": {
        "hints": ["architecture", "aeco", "bim", "design review", "revizto", "autodesk", "model review", "collaboration"],
        "setup_archetype": "immersive_model_viewer",
        "setup_summary": "Single-focus immersive model review or realtime design stream.",
        "layout_role": "hero wall",
    },
    "around the world - airpano vr": {
        "hints": ["travel", "tourism", "city", "world", "landmark", "journey", "london", "japan"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero 360 travel scene suited to guided class trips or destination storytelling.",
        "layout_role": "immersive background",
    },
    "avatour": {
        "hints": ["remote tour", "hybrid collaboration", "guided tour", "live visit"],
        "setup_archetype": "interactive_tour_webapp",
        "setup_summary": "Guided interactive tour or hybrid visit web app.",
        "layout_role": "main interactive surface",
    },
    "blockade labs - skybox": {
        "hints": ["ai generated panorama", "skybox", "prompted world", "concept environment"],
        "setup_archetype": "interactive_tour_webapp",
        "setup_summary": "Prompted panorama or web-driven immersive concept scene.",
        "layout_role": "main interactive surface",
    },
    "cenariovr": {
        "hints": ["training", "scenario", "safety training", "learning", "interactive lesson"],
        "setup_archetype": "interactive_training_webapp",
        "setup_summary": "Interactive training or branching classroom scenario built in a specialist web platform.",
        "layout_role": "main interactive surface",
    },
    "fire safety": {
        "hints": ["fire safety", "health and safety", "immersive training", "hazard", "simulation"],
        "setup_archetype": "native_training_simulation",
        "setup_summary": "Immersive app-stream training or simulation scene.",
        "layout_role": "hero wall",
    },
    "fluid sim": {
        "hints": ["science", "stem", "simulation", "physics", "fluid dynamics"],
        "setup_archetype": "interactive_simulation_surface",
        "setup_summary": "Single simulation surface for STEM explanation or guided demo.",
        "layout_role": "main interactive surface",
    },
    "ice documentation": {
        "hints": ["documentation", "help", "reference", "platform guide"],
        "setup_archetype": "operator_reference_surface",
        "setup_summary": "Reference or explainer surface, not a hero immersive scene.",
        "layout_role": "support panel",
    },
    "igloo shoe store": {
        "hints": ["retail", "showroom", "product demo", "interactive experience"],
        "setup_archetype": "native_showroom_app",
        "setup_summary": "Realtime showroom or product experience driven by an app stream.",
        "layout_role": "hero wall",
    },
    "london - airpano vr": {
        "hints": ["london", "travel", "city", "tourism", "landmark", "airpano", "journey", "uk"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero 360 travel scene for London-focused immersive trips.",
        "layout_role": "immersive background",
    },
    "matterport": {
        "hints": ["matterport", "digital twin", "property walkthrough", "virtual tour", "building walkthrough"],
        "setup_archetype": "immersive_model_viewer",
        "setup_summary": "Multi-surface pano or digital-twin viewer that wraps the room rather than acting like a flat site.",
        "layout_role": "immersive background",
    },
    "miro - displays": {
        "hints": ["miro", "workshop", "collaboration", "strategic review", "planning board", "three walls", "canvas"],
        "setup_archetype": "three_wall_canvas",
        "setup_summary": "Single collaboration board stretched across three walls for a larger shared canvas.",
        "layout_role": "three-wall span",
    },
    "model viewer - simple": {
        "hints": ["3d model", "model viewer", "product review", "aeco", "bim", "interactive model"],
        "setup_archetype": "immersive_model_viewer",
        "setup_summary": "Single interactive 3D model review surface.",
        "layout_role": "hero wall",
    },
    "new york city 8k - vr 360 drive": {
        "hints": ["new york", "travel", "city", "street", "drive", "tourism"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero 360 travel or city-drive scene.",
        "layout_role": "immersive background",
    },
    "northern lights in norway": {
        "hints": ["norway", "nature", "travel", "education", "science", "sky"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero 360 environmental scene for awe-led education or tourism content.",
        "layout_role": "immersive background",
    },
    "slides.com example": {
        "hints": ["slides", "presentation", "meeting", "sales demo", "briefing"],
        "setup_archetype": "three_wall_presentation",
        "setup_summary": "Presentation-first web slide deck stretched as a wide front-facing surface.",
        "layout_role": "three-wall span",
    },
    "space journey": {
        "hints": ["space", "nasa", "science", "astronomy", "education", "journey"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero 360 science or space journey scene.",
        "layout_role": "immersive background",
    },
    "starry night": {
        "hints": ["art", "culture", "museum", "immersive art", "education"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero cultural or art-led immersive scene.",
        "layout_role": "immersive background",
    },
    "streetview": {
        "hints": ["streetview", "maps", "tour", "travel", "city", "navigation", "location"],
        "setup_archetype": "interactive_tour_webapp",
        "setup_summary": "Guided web-based location tour with interactive navigation.",
        "layout_role": "main interactive surface",
    },
    "underwater": {
        "hints": ["ocean", "marine", "science", "underwater", "education", "nature"],
        "setup_archetype": "immersive_hero_360",
        "setup_summary": "Hero 360 environmental scene suited to classroom or public wow moments.",
        "layout_role": "immersive background",
    },
}


class SampleContentCatalog:
    def __init__(self, settings: Settings, parser: IceSessionParser | None = None) -> None:
        self.settings = settings
        self.parser = parser or IceSessionParser()
        self.roots = self._discover_roots()

    def _discover_roots(self) -> tuple[Path, ...]:
        roots: list[Path] = []
        example_root = (self.settings.cwd / "Example Sessions").resolve()
        if example_root.exists():
            roots.append(example_root)
        for root in self.settings.session_library_roots:
            try:
                resolved = root.resolve()
            except Exception:
                continue
            if resolved.exists() and resolved not in roots:
                roots.append(resolved)
        return tuple(roots)

    @lru_cache(maxsize=1)
    def entries(self) -> tuple[SampleCatalogEntry, ...]:
        entries: list[SampleCatalogEntry] = []
        for root in self.roots:
            curated_rank = 2 if root.name.lower() == "example sessions" else 1
            for session_path in sorted(root.rglob("*.iceSession")):
                try:
                    content = session_path.read_text(encoding="utf-8", errors="replace")
                    summary = self.parser.parse_text(session_path.name, content)
                except Exception:
                    continue
                entry = self._entry_from_session(root, session_path, summary, content, curated_rank)
                if entry is not None:
                    entries.append(entry)
        return tuple(entries)

    def search(
        self,
        query: str,
        mode: str,
        scorer,
        require_4k: bool = False,
        limit: int = 4,
    ) -> list[dict[str, object]]:
        query_text = query.strip()
        if not query_text:
            return []
        results: list[dict[str, object]] = []
        query_tokens = set(re.findall(r"[a-z0-9][a-z0-9\-]+", query_text.lower()))
        anchor_tokens = {
            token
            for token in query_tokens
            if token
            and token
            not in {
                "360",
                "4k",
                "8k",
                "youtube",
                "vr",
                "website",
                "webview",
                "education",
                "lesson",
                "interactive",
                "dashboard",
                "model",
                "review",
                "app",
                "content",
            }
        }
        for entry in self.entries():
            if not self._mode_matches(entry, mode):
                continue
            url = entry.asset_location or entry.session_path.as_uri()
            score = scorer(
                query_text,
                title=entry.title,
                snippet=entry.query_text,
                url=url,
                mode=mode,
                require_4k=require_4k,
            )
            score += 14 + (entry.curated_rank * 4)
            if entry.root_label == "Example Sessions":
                score += 6
            entry_text = f"{entry.session_name} {entry.query_text} {entry.snippet}".lower()
            entry_tokens = set(re.findall(r"[a-z0-9][a-z0-9\-]+", entry_text))
            if query_tokens.intersection(set(re.findall(r"[a-z0-9][a-z0-9\-]+", entry_text))):
                score += 10
            if anchor_tokens and not anchor_tokens.intersection(entry_tokens):
                if mode == "youtube_360":
                    continue
                score -= 28
            if mode == "youtube_360" and any(token in entry_text for token in ("travel", "tour", "journey", "city", "london", "japan")):
                score += 8
            if require_4k and "4k" in entry.resolution_label.lower():
                score += 8
            if score < 18:
                continue
            results.append(
                {
                    "title": entry.title,
                    "url": url,
                    "asset_location": url,
                    "source": "sample catalog",
                    "snippet": entry.snippet,
                    "content_type": entry.content_type,
                    "readiness_status": "usable with prep",
                    "resolution_label": entry.resolution_label,
                    "notes": [
                        "Fallback from the local sample-session catalogue because live search was weak or too generic.",
                        *entry.notes,
                    ],
                    "thumbnail_url": "",
                    "provider": f"{entry.root_label}: {entry.session_name}",
                    "match_score": score,
                    "preview_caption": "Curated fallback example",
                    "recommended_layer_type": entry.recommended_layer_type,
                    "setup_archetype": entry.setup_archetype,
                    "layout_role": entry.layout_role,
                    "setup_summary": entry.setup_summary,
                }
            )
        results.sort(key=lambda item: int(item.get("match_score", 0)), reverse=True)
        unique: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in results:
            key = str(item.get("url", "")).lower()
            if key in seen:
                continue
            unique.append(item)
            seen.add(key)
            if len(unique) >= limit:
                break
        return unique

    def _entry_from_session(
        self,
        root: Path,
        session_path: Path,
        summary,
        raw_content: str,
        curated_rank: int,
    ) -> SampleCatalogEntry | None:
        tags = self._extract_first(raw_content, "Tags")
        description = self._extract_first(raw_content, "Description")
        layer = self._best_layer(summary.layers)
        if layer is None:
            return None
        session_name = summary.session_name or session_path.stem
        key = session_name.lower()
        profile = SESSION_PROFILES.get(key, {})
        hints = [str(item) for item in profile.get("hints", []) if isinstance(item, str)]
        title = session_name
        asset_location = self._normalise_asset_location(layer.file_path)
        content_type = self._display_content_type(layer.inferred_content_type, session_name, hints, asset_location)
        resolution_label = self._resolution_label(layer)
        provider = self._provider_label(layer, asset_location)
        query_parts = [
            session_name,
            layer.name,
            content_type,
            tags,
            description,
            " ".join(hints),
        ]
        query_text = " ".join(part for part in query_parts if part).strip()
        snippet = self._build_snippet(session_name, layer.name, tags, description, hints, content_type)
        notes = [
            f"Sample session path: {session_path}",
            f"Primary example layer: {layer.name}",
        ]
        if layer.source_field:
            notes.append(f"Sample route comes from <{layer.source_field}> in the exported session.")
        if summary.trigger_action_enabled:
            notes.append("This sample session also has Triggers and Actions enabled.")
        root_label = "Example Sessions" if root.name.lower() == "example sessions" else root.name
        setup_archetype = str(profile.get("setup_archetype", self._default_setup_archetype(content_type, session_name, hints, asset_location)))
        setup_summary = str(profile.get("setup_summary", self._default_setup_summary(setup_archetype, content_type)))
        layout_role = str(profile.get("layout_role", self._default_layout_role(setup_archetype, content_type)))
        notes.append(f"Setup archetype: {setup_archetype.replace('_', ' ')}.")
        return SampleCatalogEntry(
            session_name=session_name,
            title=title,
            query_text=query_text,
            session_path=session_path,
            asset_location=asset_location,
            content_type=content_type,
            recommended_layer_type=self._recommended_layer_type(layer, content_type),
            resolution_label=resolution_label,
            provider=provider,
            snippet=snippet,
            notes=notes,
            root_label=root_label,
            curated_rank=curated_rank,
            setup_archetype=setup_archetype,
            setup_summary=setup_summary,
            layout_role=layout_role,
        )

    def _best_layer(self, layers) -> object | None:
        if not layers:
            return None
        def rank(layer) -> tuple[int, int]:
            content = layer.inferred_content_type.lower()
            priority = 0
            if "360" in content or "immersive" in content:
                priority += 30
            if "interactive web" in content:
                priority += 24
            if "3d model" in content or "app stream" in content:
                priority += 22
            if "website" in content:
                priority += 12
            return (priority + int(layer.readiness_score), len(layer.notes))
        return sorted(layers, key=rank, reverse=True)[0]

    def _mode_matches(self, entry: SampleCatalogEntry, mode: str) -> bool:
        content = entry.content_type.lower()
        query = entry.query_text.lower()
        if mode == "youtube_360":
            return "360" in content or "youtube" in content
        if mode == "interactive_model":
            return "3d model" in content or "model" in query or "archvis" in query or "matterport" in query
        if mode == "immersive_web":
            return "interactive web" in content or any(term in query for term in ("thinglink", "streetview", "virtual tour", "cenariovr", "avatour"))
        if mode == "review_app":
            return any(term in query for term in ("miro", "slides", "dashboard", "collaboration", "review", "matterport"))
        if mode == "webxr":
            return any(term in query for term in ("webxr", "skybox", "interactive web"))
        return True

    def _normalise_asset_location(self, file_path: str) -> str:
        if not file_path:
            return ""
        parsed = urlparse(file_path)
        if "localhost:800" in file_path and "icetube" in file_path:
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
        return file_path

    def _resolution_label(self, layer) -> str:
        text = " ".join([layer.file_path, *layer.render_passes, layer.name]).lower()
        if "8k" in text or "4320" in text:
            return "8K indicated"
        if "4k" in text or "3840" in text:
            return "4K indicated"
        if "perspectiveextraction" in text:
            return "Immersive route"
        if "webview" in layer.layer_type.lower():
            return "Live web route"
        return "Sample route"

    def _provider_label(self, layer, asset_location: str) -> str:
        if "youtube.com" in asset_location:
            return "Sample session YouTube route"
        if asset_location.startswith("http://") or asset_location.startswith("https://"):
            parsed = urlparse(asset_location)
            return parsed.netloc.replace("www.", "") or "Sample session web route"
        if layer.layer_type.lower() == "spout":
            return "Sample session app stream"
        return "Sample session"

    def _build_snippet(
        self,
        session_name: str,
        layer_name: str,
        tags: str,
        description: str,
        hints: list[str],
        content_type: str,
    ) -> str:
        parts = [f"{session_name} is a local sample-session fallback."]
        if layer_name and layer_name.lower() != session_name.lower():
            parts.append(f"It uses {layer_name} as the main example layer.")
        if content_type:
            parts.append(f"Primary route: {content_type}.")
        if tags:
            parts.append(f"Tags: {tags}.")
        if description:
            parts.append(description)
        elif hints:
            parts.append(f"Useful for {', '.join(hints[:4])}.")
        return " ".join(part.strip() for part in parts if part).strip()

    def _default_setup_archetype(self, content_type: str, session_name: str, hints: list[str], asset_location: str) -> str:
        context = f"{content_type} {session_name} {' '.join(hints)} {asset_location}".lower()
        if "contentbank" in context or "content bank" in context:
            return "content_bank_gallery"
        if any(term in context for term in ("miro", "slides", "display", "presentation")):
            return "three_wall_presentation"
        if any(term in context for term in ("dashboard", "powerbi", "review", "comparison")):
            return "three_wall_dashboard"
        if any(term in context for term in ("model", "matterport", "archvis", "revizto", "autodesk", "sketchfab")):
            return "immersive_model_viewer"
        if any(term in context for term in ("thinglink", "streetview", "tour", "cenariovr", "avatour")):
            return "interactive_tour_webapp"
        if "360" in context or "immersive" in context:
            return "immersive_hero_360"
        return "single_surface_reference"

    def _default_setup_summary(self, setup_archetype: str, content_type: str) -> str:
        summaries = {
            "immersive_hero_360": "Hero immersive scene with optional supporting panels or overlays.",
            "interactive_tour_webapp": "Interactive guided web experience rather than a passive flat website.",
            "interactive_training_webapp": "Interactive learning surface designed around scenario progression.",
            "immersive_model_viewer": "Model or pano viewer that benefits from strong room coverage and simple controls.",
            "three_wall_canvas": "A single canvas or board stretched across multiple walls.",
            "three_wall_presentation": "A wide presentation surface spanning multiple walls.",
            "three_wall_dashboard": "Distinct dashboard or model surfaces assigned to specific walls.",
            "content_bank_gallery": "Content Bank-led switching between prepared media states.",
            "operator_reference_surface": "Reference or utility surface that supports a larger session.",
            "native_training_simulation": "Realtime app-stream simulation or specialist training build.",
            "native_showroom_app": "App-stream showroom or interactive branded environment.",
            "single_surface_reference": f"Single-surface {content_type.lower()} route.",
        }
        return summaries.get(setup_archetype, f"Single-surface {content_type.lower()} route.")

    def _default_layout_role(self, setup_archetype: str, content_type: str) -> str:
        if setup_archetype in {"immersive_hero_360", "immersive_model_viewer"}:
            return "hero wall"
        if setup_archetype in {"three_wall_canvas", "three_wall_presentation"}:
            return "three-wall span"
        if setup_archetype == "three_wall_dashboard":
            return "wall panel"
        if setup_archetype == "content_bank_gallery":
            return "content bank"
        if "pdf" in content_type.lower():
            return "support panel"
        return "main surface"

    def _display_content_type(self, content_type: str, session_name: str, hints: list[str], asset_location: str) -> str:
        normalized = content_type.lower()
        context_text = f"{session_name} {' '.join(hints)} {asset_location}".lower()
        if any(term in context_text for term in ("model viewer", "3d model", "sketchfab", "revizto", "autodesk", "matterport", "archvis")):
            return "3d model"
        if any(term in context_text for term in ("miro", "slides", "dashboard", "power bi", "sales review")):
            return "Review app"
        if normalized == "interactive web":
            return "Interactive web"
        if normalized == "youtube 360":
            return "YouTube 360"
        if normalized == "app stream":
            return "App stream"
        if normalized == "360 video":
            return "360 video"
        if normalized == "website":
            return "Website"
        if normalized == "pdf":
            return "PDF"
        return content_type.title()

    def _recommended_layer_type(self, layer, content_type: str) -> str:
        content = content_type.lower()
        layer_type = layer.layer_type.lower()
        if layer_type == "spout":
            return "Spout"
        if layer_type == "pdf" or content == "pdf":
            return "PDF"
        if content == "3d model":
            return "ModelViewer"
        if layer_type == "webview":
            return "WebView"
        if layer_type == "youtube":
            return "WebView"
        return "Video"

    def _extract_first(self, text: str, tag: str) -> str:
        match = re.search(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", text, re.DOTALL)
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()
