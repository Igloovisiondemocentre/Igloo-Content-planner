from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _parse_path_list(value: str | None) -> tuple[Path, ...]:
    if not value:
        return ()
    paths: list[Path] = []
    for raw_part in value.split(os.pathsep):
        part = raw_part.strip().strip("\"'")
        if not part:
            continue
        try:
            paths.append(Path(part).resolve())
        except Exception:
            continue
    return tuple(paths)


@dataclass(slots=True)
class Settings:
    cwd: Path
    runtime_api_root_url: str
    platform_docs_root_url: str
    platform_docs_sitemap_url: str
    runtime_api_max_pages: int
    platform_docs_max_pages: int
    pdf_max_pages: int
    request_timeout_seconds: int
    index_ttl_hours: int
    index_path: Path
    evidence_dir: Path
    reports_dir: Path
    decisions_dir: Path
    evaluations_dir: Path
    snapshots_dir: Path
    manifest_path: Path
    log_level: str
    sandbox_host: str | None
    sandbox_port: int | None
    sandbox_transport: str
    sandbox_api_key: str | None
    sandbox_timeout_seconds: float
    sandbox_terminator: str
    sandbox_enable_write_probes: bool
    local_install_root: Path | None
    session_library_roots: tuple[Path, ...]
    youtube_api_key: str | None
    openai_api_key: str | None
    openai_query_planner_model: str
    google_maps_api_key: str | None
    mapbox_access_token: str | None
    serpapi_api_key: str | None
    site_metadata_timeout_seconds: float

    @classmethod
    def from_env(cls, cwd: Path) -> "Settings":
        env_file = _load_dotenv(cwd / ".env")

        def pick(name: str, default: str | None = None) -> str | None:
            return os.environ.get(name, env_file.get(name, default))

        evidence_dir = cwd / "evidence"
        settings = cls(
            cwd=cwd,
            runtime_api_root_url=pick("IGLOO_RUNTIME_API_ROOT_URL", "https://api.igloovision.com/1.5.0/") or "",
            platform_docs_root_url=pick(
                "IGLOO_PLATFORM_DOCS_ROOT_URL",
                "https://docs.igloovision.com/documentation/current",
            )
            or "",
            platform_docs_sitemap_url=pick("IGLOO_PLATFORM_DOCS_SITEMAP_URL", "https://docs.igloovision.com/sitemap.xml")
            or "",
            runtime_api_max_pages=int(pick("IGLOO_RUNTIME_API_MAX_PAGES", "8") or "8"),
            platform_docs_max_pages=int(pick("IGLOO_PLATFORM_DOCS_MAX_PAGES", "28") or "28"),
            pdf_max_pages=int(pick("IGLOO_PDF_MAX_PAGES", "16") or "16"),
            request_timeout_seconds=int(pick("IGLOO_REQUEST_TIMEOUT_SECONDS", "20") or "20"),
            index_ttl_hours=int(pick("IGLOO_INDEX_TTL_HOURS", "24") or "24"),
            index_path=cwd / (pick("IGLOO_INDEX_PATH", "evidence/source_index.json") or "evidence/source_index.json"),
            evidence_dir=evidence_dir,
            reports_dir=evidence_dir / "reports",
            decisions_dir=evidence_dir / "decisions",
            evaluations_dir=evidence_dir / "evaluations",
            snapshots_dir=evidence_dir / "snapshots",
            manifest_path=cwd / (pick("IGLOO_SOURCE_MANIFEST_PATH", "config/source_manifest.json") or "config/source_manifest.json"),
            log_level=pick("IGLOO_LOG_LEVEL", "INFO") or "INFO",
            sandbox_host=pick("IGLOO_SANDBOX_HOST"),
            sandbox_port=int(pick("IGLOO_SANDBOX_PORT") or 0) or None,
            sandbox_transport=(pick("IGLOO_SANDBOX_TRANSPORT", "tcp") or "tcp").lower(),
            sandbox_api_key=pick("IGLOO_SANDBOX_API_KEY"),
            sandbox_timeout_seconds=float(pick("IGLOO_SANDBOX_TIMEOUT_SECONDS", "2.0") or "2.0"),
            sandbox_terminator=pick("IGLOO_SANDBOX_TERMINATOR", "\\n") or "\\n",
            sandbox_enable_write_probes=_parse_bool(pick("IGLOO_SANDBOX_ENABLE_WRITE_PROBES"), False),
            local_install_root=Path(pick("IGLOO_LOCAL_INSTALL_ROOT")).resolve()
            if pick("IGLOO_LOCAL_INSTALL_ROOT")
            else None,
            session_library_roots=_parse_path_list(pick("IGLOO_SESSION_LIBRARY_ROOTS")),
            youtube_api_key=pick("YOUTUBE_API_KEY"),
            openai_api_key=pick("OPENAI_API_KEY"),
            openai_query_planner_model=pick("OPENAI_QUERY_PLANNER_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
            google_maps_api_key=pick("GOOGLE_MAPS_API_KEY"),
            mapbox_access_token=pick("MAPBOX_ACCESS_TOKEN"),
            serpapi_api_key=pick("SERPAPI_API_KEY"),
            site_metadata_timeout_seconds=float(pick("IGLOO_SITE_METADATA_TIMEOUT_SECONDS", "6.0") or "6.0"),
        )
        settings.ensure_directories()
        return settings

    def ensure_directories(self) -> None:
        for path in (
            self.evidence_dir,
            self.reports_dir,
            self.decisions_dir,
            self.evaluations_dir,
            self.snapshots_dir,
            self.index_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def sandbox_is_configured(self) -> bool:
        return bool(self.sandbox_host and self.sandbox_port)
