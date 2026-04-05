from __future__ import annotations

import json
import re
from dataclasses import dataclass

from igloo_experience_builder.config import Settings
from igloo_experience_builder.models import LocalValidationStatus
from igloo_experience_builder.sandbox.auth import authenticate
from igloo_experience_builder.sandbox.client import IglooSandboxClient, SandboxHttpResult


@dataclass(slots=True)
class SandboxDiscoveryResult:
    ping_success: bool
    details: list[str]
    surfaces: list[dict[str, object]]
    validation_status: LocalValidationStatus


class SandboxDiscoveryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cached_result: SandboxDiscoveryResult | None = None

    def run(self) -> SandboxDiscoveryResult:
        if self._cached_result is not None:
            return self._cached_result
        disclaimer = (
            "Sandbox success means technically reproducible in this local environment. "
            "It does not mean ready to promise to a client."
        )
        if not self.settings.sandbox_is_configured:
            self._cached_result = SandboxDiscoveryResult(
                ping_success=False,
                details=["No sandbox host/port configured."],
                surfaces=[],
                validation_status=LocalValidationStatus(
                    state="not_run",
                    summary="Local sandbox not configured, so no live validation was run.",
                    details=["Configure IGLOO_SANDBOX_HOST and IGLOO_SANDBOX_PORT to enable read-only probing."],
                    disclaimer=disclaimer,
                ),
            )
            return self._cached_result
        client = IglooSandboxClient(self.settings)
        if self.settings.sandbox_transport in {"http", "https"}:
            self._cached_result = self._run_http_probe(client, disclaimer)
            return self._cached_result
        self._cached_result = self._run_message_probe(client, disclaimer)
        return self._cached_result

    def _run_message_probe(self, client: IglooSandboxClient, disclaimer: str) -> SandboxDiscoveryResult:
        details: list[str] = []
        auth_result = authenticate(client, self.settings.sandbox_api_key)
        if auth_result.error:
            details.append(f"Auth probe result: {auth_result.error}")
        elif auth_result.response:
            details.append(f"Auth probe response: {auth_result.response}")
        ping_result = client.send_message("app/ping")
        if ping_result.success:
            details.append(f"Ping response: {ping_result.response or 'received'}")
            return SandboxDiscoveryResult(
                ping_success=True,
                details=details,
                surfaces=[],
                validation_status=LocalValidationStatus(
                    state="validated",
                    summary="A safe sandbox ping probe succeeded.",
                    details=details,
                    disclaimer=disclaimer,
                ),
            )
        details.append(f"Ping probe failed: {ping_result.error or 'no response'}")
        return SandboxDiscoveryResult(
            ping_success=False,
            details=details,
            surfaces=[],
            validation_status=LocalValidationStatus(
                state="failed",
                summary="A sandbox probe was attempted but did not complete successfully.",
                details=details,
                disclaimer=disclaimer,
            ),
        )

    def _run_http_probe(self, client: IglooSandboxClient, disclaimer: str) -> SandboxDiscoveryResult:
        details: list[str] = []
        surfaces: list[dict[str, object]] = []
        success_count = 0

        control_panel = client.http_get("/")
        surfaces.append(self._surface_payload("control_panel_root", control_panel, self._html_title(control_panel.response)))
        if control_panel.success:
            success_count += 1
            details.append(
                f"Control panel root reachable at {control_panel.url}: {self._html_title(control_panel.response) or 'HTML response'}."
            )
        else:
            details.append(f"Control panel root probe failed: {control_panel.error or 'no response'}")

        ignore_list = client.http_get("/api/sources/ignoreList")
        ignore_excerpt = self._ignore_list_summary(ignore_list)
        surfaces.append(self._surface_payload("ignore_list_api", ignore_list, ignore_excerpt))
        if ignore_list.success:
            success_count += 1
            details.append(f"Read-only sources API reachable: {ignore_excerpt}.")
        else:
            details.append(f"Read-only sources API probe failed: {ignore_list.error or 'no response'}")

        socket_handshake = client.http_get("/socket.io/", query={"EIO": "4", "transport": "polling"})
        socket_excerpt = self._socket_summary(socket_handshake)
        surfaces.append(self._surface_payload("socketio_handshake", socket_handshake, socket_excerpt))
        if socket_handshake.success:
            success_count += 1
            details.append(f"Socket.IO handshake reachable: {socket_excerpt}.")
        else:
            details.append(f"Socket.IO handshake probe failed: {socket_handshake.error or 'no response'}")

        if (self.settings.sandbox_host or "").lower() in {"127.0.0.1", "localhost"}:
            for name, path in (
                ("streetview_root", "/"),
                ("streetview_control", "/control/"),
                ("streetview_iglooview", "/iglooview/"),
            ):
                probe = client.http_get(path, port=9070, transport="http")
                excerpt = self._html_title(probe.response)
                surfaces.append(self._surface_payload(name, probe, excerpt))
                if probe.success:
                    success_count += 1
            if any(surface["ok"] for surface in surfaces if str(surface.get("name", "")).startswith("streetview_")):
                details.append("Streetview sidecar surfaces are reachable on port 9070.")

        if success_count >= 3:
            return SandboxDiscoveryResult(
                ping_success=True,
                details=details,
                surfaces=surfaces,
                validation_status=LocalValidationStatus(
                    state="validated",
                    summary="Safe HTTP discovery probes succeeded against the local Igloo sandbox surfaces.",
                    details=details,
                    disclaimer=disclaimer,
                ),
            )
        return SandboxDiscoveryResult(
            ping_success=False,
            details=details,
            surfaces=surfaces,
            validation_status=LocalValidationStatus(
                state="failed",
                summary="HTTP sandbox discovery was attempted but the expected local surfaces were not all reachable.",
                details=details,
                disclaimer=disclaimer,
            ),
        )

    def _surface_payload(self, name: str, probe: SandboxHttpResult, excerpt: str | None) -> dict[str, object]:
        return {
            "name": name,
            "ok": probe.success,
            "url": probe.url,
            "status_code": probe.status_code,
            "content_type": probe.content_type,
            "excerpt": excerpt or "",
            "error": probe.error,
        }

    def _html_title(self, payload: str) -> str | None:
        if not payload:
            return None
        match = re.search(r"<title>(.*?)</title>", payload, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _ignore_list_summary(self, probe: SandboxHttpResult) -> str:
        if not probe.success:
            return ""
        try:
            payload = json.loads(probe.response)
        except json.JSONDecodeError:
            return "ignore list response received"
        ignore_list = payload.get("ignoreList", [])
        if not ignore_list:
            return "no ignored sources reported"
        return f"ignored sources = {', '.join(str(item) for item in ignore_list)}"

    def _socket_summary(self, probe: SandboxHttpResult) -> str:
        if not probe.success:
            return ""
        raw = probe.response.strip()
        if raw.startswith("0"):
            raw = raw[1:]
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return "handshake response received"
        upgrades = ", ".join(payload.get("upgrades", [])) or "none"
        ping_interval = payload.get("pingInterval")
        ping_timeout = payload.get("pingTimeout")
        return f"upgrades = {upgrades}; pingInterval = {ping_interval}ms; pingTimeout = {ping_timeout}ms"
