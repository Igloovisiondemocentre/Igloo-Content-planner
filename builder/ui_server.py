from __future__ import annotations

import json
import logging
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from igloo_experience_builder.builder.content_search import ContentSearchService
from igloo_experience_builder.builder.draft_builder import PhaseTwoDraftBuilder
from igloo_experience_builder.builder.query_planner import QueryPlannerService
from igloo_experience_builder.builder.session_package import SessionPackageWriter
from igloo_experience_builder.builder.session_parser import IceSessionParser
from igloo_experience_builder.capability.classifier import CapabilityClassifier
from igloo_experience_builder.config.settings import Settings
from igloo_experience_builder.ingestion.source_manager import SourceManager
from igloo_experience_builder.sandbox.discovery import SandboxDiscoveryService


LOGGER = logging.getLogger(__name__)


class BuilderApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.source_manager = SourceManager(settings)
        self.index = self.source_manager.ensure_index(refresh=False)
        self.classifier = CapabilityClassifier(index=self.index, sandbox=SandboxDiscoveryService(settings))
        self.search = ContentSearchService(settings)
        self.query_planner = QueryPlannerService(settings)
        self.parser = IceSessionParser()
        self.drafts = PhaseTwoDraftBuilder()
        self.static_dir = Path(__file__).resolve().parent / "static"
        self.drafts_dir = settings.evidence_dir / "builder_drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.session_packages_dir = settings.evidence_dir / "session_packages"
        self.session_packages_dir.mkdir(parents=True, exist_ok=True)
        self.session_writer = SessionPackageWriter(self.session_packages_dir)

    def bootstrap_payload(self) -> dict[str, object]:
        return {
            "product_name": "Igloo Experience Builder Pilot",
            "phase_name": "Phase 2 Mixed-Media Session Builder",
            "logo_url": "https://www.igloovision.com/images/Layout/logo.png",
            "structures": [item.to_dict() for item in self.drafts.structures()],
            "theme": {
                "navy": "#002032",
                "blue": "#0063DC",
                "blueBright": "#285AEB",
                "cyan": "#1AB7EA",
                "aqua": "#38DEDF",
                "text": "#FFFFFF",
            },
            "query_planner": {
                "openai_enabled": bool(settings.openai_api_key),
                "google_maps_enabled": bool(settings.google_maps_api_key),
                "mapbox_enabled": bool(settings.mapbox_access_token),
                "serpapi_enabled": bool(settings.serpapi_api_key),
                "youtube_api_enabled": bool(settings.youtube_api_key),
            },
        }

    def assess(self, payload: dict[str, object]) -> dict[str, object]:
        brief = str(payload.get("brief", "")).strip()
        structure_id = str(payload.get("structure_id", "immersive-workspace"))
        import_mode = str(payload.get("import_mode", "none"))
        imported_payload = payload.get("session_import")
        imported_session = None
        if isinstance(imported_payload, dict):
            imported_session = self.parser.parse_text(
                str(imported_payload.get("filename", "Imported.iceSession")),
                str(imported_payload.get("content", "")),
            )
        assessment = self.classifier.assess(brief)
        draft = self.drafts.build(
            brief,
            assessment,
            structure_id=structure_id,
            session_import=imported_session,
            import_mode=import_mode,
        )
        self._apply_query_planner_to_draft(brief, draft)
        return draft.to_dict()

    def parse_session(self, payload: dict[str, object]) -> dict[str, object]:
        filename = str(payload.get("filename", "Imported.iceSession"))
        content = str(payload.get("content", ""))
        summary = self.parser.parse_text(filename, content)
        return summary.to_dict()

    def search_content(self, payload: dict[str, object]) -> dict[str, object]:
        query = str(payload.get("query", ""))
        mode = str(payload.get("mode", "website"))
        require_4k = bool(payload.get("require_4k", False))
        return self.search.search(query, mode, require_4k=require_4k)

    def plan_search_query(self, payload: dict[str, object]) -> dict[str, object]:
        brief = str(payload.get("brief", ""))
        mode = str(payload.get("mode", "website"))
        require_4k = bool(payload.get("require_4k", False))
        target_title = str(payload.get("target_title", ""))
        target_content_type = str(payload.get("target_content_type", ""))
        existing_query = str(payload.get("existing_query", ""))
        plan = self.query_planner.plan(
            brief=brief,
            mode=mode,
            target_title=target_title,
            target_content_type=target_content_type,
            existing_query=existing_query,
            require_4k=require_4k,
        )
        return plan.to_dict()

    def auto_search_content(self, payload: dict[str, object]) -> dict[str, object]:
        candidates = payload.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("Expected a list of content candidates.")
        brief = str(payload.get("brief", ""))
        if not brief:
            return self.search.auto_search_candidates(candidates)
        groups: list[dict[str, object]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            mode = self.search._mode_for_candidate(candidate)
            require_4k = mode == "youtube_360"
            plan = self.query_planner.plan(
                brief=brief,
                mode=mode,
                target_title=str(candidate.get("title", "")),
                target_content_type=str(candidate.get("content_type", "")),
                existing_query=str(candidate.get("query_hint", "")),
                require_4k=require_4k,
            )
            result = self.search.search(
                query=plan.query,
                mode=mode,
                require_4k=require_4k,
                limit=4,
            )
            items = result.get("results", [])
            if not isinstance(items, list):
                items = []
            notes = [*plan.notes, *[str(note) for note in result.get("notes", [])]]
            groups.append(
                {
                    "candidate_id": candidate.get("candidate_id", ""),
                    "title": candidate.get("title", ""),
                    "query": plan.query,
                    "mode": mode,
                    "best_result": items[0] if items else None,
                    "alternatives": items[:4],
                    "notes": notes,
                    "planner": plan.planner,
                    "destination": plan.destination,
                    "subject": plan.subject,
                }
            )
        return {"groups": groups}

    def save_draft(self, payload: dict[str, object]) -> dict[str, object]:
        name = str(payload.get("name", "builder-draft")).strip() or "builder-draft"
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_", " "}).strip().replace(" ", "-")
        path = self.drafts_dir / f"{safe_name}.json"
        counter = 1
        while path.exists():
            path = self.drafts_dir / f"{safe_name}-{counter}.json"
            counter += 1
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"saved": True, "path": str(path)}

    def export_session_package(self, payload: dict[str, object]) -> dict[str, object]:
        return self.session_writer.export(payload)

    def _apply_query_planner_to_draft(self, brief: str, draft: object) -> None:
        selected = getattr(draft, "selected_content", None)
        if not isinstance(selected, list):
            return
        for item in selected:
            mode = self._planner_mode_for_content(item.content_type)
            require_4k = mode == "youtube_360"
            plan = self.query_planner.plan(
                brief=brief,
                mode=mode,
                target_title=item.title,
                target_content_type=item.content_type,
                existing_query=getattr(item, "query_hint", ""),
                require_4k=require_4k,
            )
            item.query_hint = plan.query
        suggestions = getattr(draft, "search_suggestions", None)
        if isinstance(suggestions, list):
            for suggestion in suggestions:
                if not hasattr(suggestion, "query"):
                    continue
                title = getattr(suggestion, "label", "") or getattr(suggestion, "query", "")
                mode = getattr(suggestion, "mode", "website")
                require_4k = mode == "youtube_360"
                plan = self.query_planner.plan(
                    brief=brief,
                    mode=mode,
                    target_title=title,
                    target_content_type=self._content_type_for_mode(mode),
                    existing_query=getattr(suggestion, "query", ""),
                    require_4k=require_4k,
                )
                suggestion.query = plan.query

    @staticmethod
    def _planner_mode_for_content(content_type: str) -> str:
        normalized = (content_type or "").strip().lower()
        if normalized == "360 video":
            return "youtube_360"
        if normalized == "3d model":
            return "interactive_model"
        if normalized in {"dashboard app", "review app"}:
            return "review_app"
        if normalized == "interactive web":
            return "immersive_web"
        return "website"

    @staticmethod
    def _content_type_for_mode(mode: str) -> str:
        normalized = (mode or "").strip().lower()
        mapping = {
            "youtube_360": "360 video",
            "interactive_model": "3d model",
            "review_app": "dashboard app",
            "immersive_web": "interactive web",
        }
        return mapping.get(normalized, "website")


class BuilderRequestHandler(BaseHTTPRequestHandler):
    server_version = "IglooBuilder/0.1"

    @property
    def app(self) -> BuilderApp:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_file(self.app.static_dir / "index.html")
            return
        if parsed.path.startswith("/static/"):
            relative_path = parsed.path.removeprefix("/static/")
            self._serve_file(self.app.static_dir / relative_path)
            return
        if parsed.path == "/api/bootstrap":
            self._send_json(self.app.bootstrap_payload())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._read_json_body()
        if payload is None:
            return
        try:
            if parsed.path == "/api/assess":
                self._send_json(self.app.assess(payload))
                return
            if parsed.path == "/api/parse-session":
                self._send_json(self.app.parse_session(payload))
                return
            if parsed.path == "/api/search-content":
                self._send_json(self.app.search_content(payload))
                return
            if parsed.path == "/api/plan-search-query":
                self._send_json(self.app.plan_search_query(payload))
                return
            if parsed.path == "/api/auto-search-content":
                self._send_json(self.app.auto_search_content(payload))
                return
            if parsed.path == "/api/save-draft":
                self._send_json(self.app.save_draft(payload))
                return
            if parsed.path == "/api/export-session-package":
                self._send_json(self.app.export_session_package(payload))
                return
        except Exception as exc:  # pragma: no cover - surfaced to UI
            LOGGER.exception("Builder UI request failed")
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        LOGGER.info("Builder UI: " + format, *args)

    def _read_json_body(self) -> dict[str, object] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object body.")
            return payload
        except Exception as exc:
            self._send_json({"error": f"Invalid JSON body: {exc}"}, status=HTTPStatus.BAD_REQUEST)
            return None

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content_type, _ = mimetypes.guess_type(path.name)
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def serve_builder_ui(settings: Settings, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    app = BuilderApp(settings)
    server = ThreadingHTTPServer((host, port), BuilderRequestHandler)
    server.app = app  # type: ignore[attr-defined]
    url = f"http://{host}:{port}/"
    LOGGER.info("Starting Phase 2 builder UI at %s", url)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Stopping Phase 2 builder UI")
    finally:
        server.server_close()
