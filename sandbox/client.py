from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from igloo_experience_builder.config import Settings


@dataclass(slots=True)
class SandboxMessageResult:
    success: bool
    response: str
    error: str | None = None


@dataclass(slots=True)
class SandboxHttpResult:
    success: bool
    url: str
    status_code: int | None
    response: str
    content_type: str | None = None
    error: str | None = None


class IglooSandboxClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_message(self, message: str) -> SandboxMessageResult:
        if not self.settings.sandbox_is_configured:
            return SandboxMessageResult(False, "", "Sandbox host/port not configured.")
        if self.settings.sandbox_transport in {"http", "https"}:
            return SandboxMessageResult(
                False,
                "",
                "HTTP sandbox transport uses GET probes instead of raw message commands.",
            )
        terminator = self.settings.sandbox_terminator.encode("utf-8").decode("unicode_escape")
        payload = f"{message}{terminator}".encode("utf-8")
        if self.settings.sandbox_transport == "udp":
            return self._send_udp(payload)
        return self._send_tcp(payload)

    def http_get(
        self,
        path: str,
        *,
        query: dict[str, str] | None = None,
        port: int | None = None,
        transport: str | None = None,
    ) -> SandboxHttpResult:
        host = self.settings.sandbox_host
        scheme = (transport or self.settings.sandbox_transport or "http").lower()
        target_port = port or self.settings.sandbox_port
        if not host or not target_port:
            return SandboxHttpResult(False, "", None, "", error="Sandbox host/port not configured.")
        if scheme not in {"http", "https"}:
            return SandboxHttpResult(False, "", None, "", error=f"Unsupported HTTP transport: {scheme}")
        normalized_path = path if path.startswith("/") else f"/{path}"
        query_string = f"?{urlencode(query)}" if query else ""
        url = f"{scheme}://{host}:{target_port}{normalized_path}{query_string}"
        try:
            request = Request(url, method="GET")
            with urlopen(request, timeout=self.settings.sandbox_timeout_seconds) as response:
                body = response.read(8192).decode("utf-8", errors="ignore")
                return SandboxHttpResult(
                    success=True,
                    url=url,
                    status_code=getattr(response, "status", None),
                    response=body,
                    content_type=response.headers.get("Content-Type"),
                )
        except HTTPError as exc:
            body = exc.read(8192).decode("utf-8", errors="ignore")
            return SandboxHttpResult(
                success=False,
                url=url,
                status_code=exc.code,
                response=body,
                content_type=exc.headers.get("Content-Type"),
                error=str(exc),
            )
        except (URLError, OSError) as exc:
            return SandboxHttpResult(False, url, None, "", error=str(exc))

    def _send_tcp(self, payload: bytes) -> SandboxMessageResult:
        try:
            with socket.create_connection(
                (self.settings.sandbox_host, self.settings.sandbox_port),
                timeout=self.settings.sandbox_timeout_seconds,
            ) as connection:
                connection.sendall(payload)
                connection.settimeout(self.settings.sandbox_timeout_seconds)
                data = connection.recv(4096)
                return SandboxMessageResult(True, data.decode("utf-8", errors="ignore").strip())
        except Exception as exc:
            return SandboxMessageResult(False, "", str(exc))

    def _send_udp(self, payload: bytes) -> SandboxMessageResult:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.settings.sandbox_timeout_seconds)
                sock.sendto(payload, (self.settings.sandbox_host or "", self.settings.sandbox_port or 0))
                data, _ = sock.recvfrom(4096)
                return SandboxMessageResult(True, data.decode("utf-8", errors="ignore").strip())
        except Exception as exc:
            return SandboxMessageResult(False, "", str(exc))
