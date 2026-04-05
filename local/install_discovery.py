from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from igloo_experience_builder.builder.session_parser import IceSessionParser
from igloo_experience_builder.config import Settings


class LocalInstallDiscovery:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def discover(self) -> dict[str, Any]:
        root = self._resolve_root()
        if root is None:
            return {
                "configured_root": str(self.settings.local_install_root) if self.settings.local_install_root else None,
                "status": "not_found",
                "summary": "No nearby local Igloo Core Engine install was detected.",
                "write_actions_enabled": False,
            }

        config_path = root / "config.json"
        exe_path = root / "igloo-core-service.exe"
        logs_dir = root / "logs"
        layers_dir = root / "layers"
        db_path = root / "not_ice.db"

        config_payload = self._load_json(config_path)
        service_config = config_payload.get("service", {})
        ice_config = config_payload.get("ice", {})
        controllers = config_payload.get("controllers", {})
        control_panel = config_payload.get("controlPanel", {})
        open_stage_control = config_payload.get("openStageControl", {})
        file_browser = config_payload.get("fileBrowser", {})
        matterport = config_payload.get("matterport", {})
        streetview = config_payload.get("streetview", {})
        skybox = config_payload.get("skybox", {})

        return {
            "configured_root": str(self.settings.local_install_root) if self.settings.local_install_root else None,
            "detected_root": str(root),
            "status": "detected",
            "summary": "A nearby local Igloo Core Engine install was detected and inspected read-only.",
            "write_actions_enabled": False,
            "files": {
                "config_exists": config_path.exists(),
                "executable_exists": exe_path.exists(),
                "database_exists": db_path.exists(),
                "logs_dir_exists": logs_dir.exists(),
                "layers_dir_exists": layers_dir.exists(),
            },
            "executable": self._file_summary(exe_path),
            "database": self._file_summary(db_path),
            "ports": {
                "service_http": service_config.get("httpPort"),
                "service_https": service_config.get("httpsPort"),
                "service_osc": service_config.get("oscPort"),
                "ice_udp": ice_config.get("udpPort"),
                "controller_service": controllers.get("controllerServicePort"),
                "open_stage_control": open_stage_control.get("port"),
            },
            "features": {
                "controller_clients": controllers.get("clients", []),
                "control_panel_tabs": control_panel.get("tabs", []),
                "control_panel_apps": control_panel.get("apps", []),
                "content_folder_paths": file_browser.get("contentFolderPaths", []),
                "layer_files": self._directory_listing(layers_dir, pattern="*.iceLayer"),
                "recent_logs": self._directory_listing(logs_dir, pattern="*.log"),
                "parsed_layers": self._parsed_layers(layers_dir),
                "tabsets": self._tabset_summary(root / "tabsets"),
                "open_stage_control": self._open_stage_control_summary(root / "open-stage-control" / "default_session.json"),
                "saved_sessions": self._saved_sessions(),
            },
            "secrets_configured": {
                "streetview_api_key": bool(streetview.get("apiKey")),
                "matterport_api_key": bool(matterport.get("apiKey")),
                "skybox_api_key": bool(skybox.get("apiKey")),
            },
        }

    def _resolve_root(self) -> Path | None:
        candidates = []
        if self.settings.local_install_root is not None:
            candidates.append(self.settings.local_install_root)
        candidates.extend(
            [
                self.settings.cwd.parent,
                self.settings.cwd,
                self.settings.cwd.parent.parent,
            ]
        )
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if (resolved / "igloo-core-service.exe").exists() or (resolved / "config.json").exists():
                return resolved
        return None

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _file_summary(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False}
        stat = path.stat()
        return {
            "exists": True,
            "path": str(path),
            "size_bytes": stat.st_size,
            "last_modified": self._iso_from_stat(path),
        }

    def _directory_listing(self, path: Path, pattern: str) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False, "count": 0, "items": []}
        items = sorted(path.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
        return {
            "exists": True,
            "count": len(items),
            "items": [
                {
                    "name": item.name,
                    "size_bytes": item.stat().st_size,
                    "last_modified": self._iso_from_stat(item),
                }
                for item in items[:5]
            ],
        }

    def _iso_from_stat(self, path: Path) -> str:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()

    def _parsed_layers(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False, "count": 0, "items": []}
        items: list[dict[str, Any]] = []
        for item in sorted(path.glob("*.iceLayer"))[:10]:
            try:
                raw_text = item.read_text(encoding="utf-8", errors="ignore")
                sanitized = raw_text.replace("<?xml version=\"1.0\"?>", "").replace("<?xml version='1.0'?>", "").strip()
                root = ET.fromstring(f"<root>{sanitized}</root>")
                layer = root.find(".//Layer")
                if layer is None:
                    continue
                items.append(
                    {
                        "file": item.name,
                        "name": layer.findtext("Name"),
                        "type": layer.findtext("Type"),
                        "enabled": layer.findtext("IsEnabled") == "1",
                        "pinned": layer.findtext("IsPinned") == "1",
                        "background": layer.findtext("IsBackground") == "1",
                        "ui_enabled": layer.findtext("UiEnabled") == "1",
                        "uuid": layer.findtext("UUID"),
                        "size": {
                            "x": self._as_number(layer.findtext("SizeX")),
                            "y": self._as_number(layer.findtext("SizeY")),
                        },
                    }
                )
            except Exception:
                continue
        return {"exists": True, "count": len(items), "items": items}

    def _tabset_summary(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False, "count": 0, "items": []}
        items: list[dict[str, Any]] = []
        for item in sorted(path.glob("*.ivwts"))[:20]:
            try:
                root = ET.fromstring(f"<root>{item.read_text(encoding='utf-8', errors='ignore')}</root>")
                settings = root.find("./tabSettings/settings")
                if settings is None:
                    continue
                urls = [element.text for element in settings.findall(".//startURL") if element.text]
                if not urls:
                    urls = [element.text for element in settings.findall(".//URL_0") if element.text]
                items.append(
                    {
                        "file": item.name,
                        "tab_name": settings.findtext("tabName"),
                        "url_count": len(urls),
                        "primary_url": urls[0] if urls else None,
                        "capture_channel": settings.findtext("captureChannel"),
                        "max_browser_fps": self._as_number(settings.findtext("maxBrowserFPS")),
                        "equirectangular_output": settings.findtext("equirectangularOutput") == "1",
                        "off_axis_projection": settings.findtext("doOffAxisProjection") == "1",
                        "streetview_mode": settings.findtext("streetView") == "1",
                    }
                )
            except Exception:
                continue
        return {"exists": True, "count": len(items), "items": items}

    def _open_stage_control_summary(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"exists": False}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            counts = {"widgets": 0, "panels": 0, "buttons": 0}
            targets: set[str] = set()
            addresses: set[str] = set()
            sample_ids: list[str] = []

            def walk(node: dict[str, Any]) -> None:
                counts["widgets"] += 1
                widget_type = str(node.get("type", ""))
                if widget_type == "panel":
                    counts["panels"] += 1
                if widget_type == "button":
                    counts["buttons"] += 1
                address = str(node.get("address", ""))
                target = str(node.get("target", ""))
                if address and address != "auto":
                    addresses.add(address)
                if target:
                    targets.add(target)
                if len(sample_ids) < 20 and node.get("id"):
                    sample_ids.append(str(node["id"]))
                for child in node.get("widgets", []):
                    if isinstance(child, dict):
                        walk(child)

            content = payload.get("content")
            if isinstance(content, dict):
                walk(content)
            return {
                "exists": True,
                "file": str(path),
                "counts": counts,
                "targets": sorted(targets),
                "addresses": sorted(addresses),
                "sample_ids": sample_ids,
            }
        except Exception:
            return {"exists": True, "file": str(path), "error": "Failed to parse open stage control session."}

    def _saved_sessions(self) -> dict[str, Any]:
        roots = self._session_library_roots()
        if not roots:
            return {"exists": False, "count": 0, "roots": [], "items": []}

        parser = IceSessionParser()
        seen: set[Path] = set()
        session_files: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            try:
                candidates = list(root.rglob("*.iceSession"))
            except Exception:
                continue
            for candidate in candidates:
                resolved = candidate.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                session_files.append(resolved)

        session_files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        items: list[dict[str, Any]] = []
        for session_file in session_files[:20]:
            try:
                summary = parser.parse_text(session_file.name, session_file.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            asset_dir = session_file.parent / "Assets"
            asset_count = 0
            if asset_dir.exists():
                try:
                    asset_count = sum(1 for _ in asset_dir.rglob("*") if _.is_file())
                except Exception:
                    asset_count = 0
            items.append(
                {
                    "path": str(session_file),
                    "session_name": summary.session_name,
                    "product_version": summary.product_version,
                    "layer_count": summary.layer_count,
                    "inferred_session_type": summary.inferred_session_type,
                    "exported_with_assets": summary.exported_with_assets,
                    "trigger_action_enabled": summary.trigger_action_enabled,
                    "assets_dir_exists": asset_dir.exists(),
                    "asset_count": asset_count,
                    "layer_names": [layer.name for layer in summary.layers[:5]],
                    "content_types": sorted({layer.inferred_content_type for layer in summary.layers}),
                    "readiness": {
                        "average_score": round(
                            sum(layer.readiness_score for layer in summary.layers) / summary.layer_count,
                            1,
                        )
                        if summary.layer_count
                        else 0.0,
                        "statuses": sorted({layer.readiness_status for layer in summary.layers}),
                    },
                    "last_modified": self._iso_from_stat(session_file),
                }
            )

        return {
            "exists": True,
            "count": len(items),
            "roots": [str(root) for root in roots if root.exists()],
            "items": items,
        }

    def _session_library_roots(self) -> tuple[Path, ...]:
        if self.settings.session_library_roots:
            return self.settings.session_library_roots

        home = Path.home()
        candidates = [
            home / "OneDrive - igloovision" / "Desktop",
            home / "Desktop",
            home / "Documents",
        ]
        roots: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except Exception:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            roots.append(resolved)
        return tuple(roots)

    def _as_number(self, value: str | None) -> float | int | None:
        if value in {None, ""}:
            return None
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
