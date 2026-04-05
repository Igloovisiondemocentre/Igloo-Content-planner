from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from threading import Event, Lock
from typing import Any

from igloo_experience_builder.config import Settings

try:
    import socketio  # type: ignore
except ImportError:  # pragma: no cover - covered by runtime fallback
    socketio = None


KNOWN_STATE_EVENTS = [
    "capture-sources",
    "/capture/selected/name",
    "/capture/selected/enabled",
    "/capture/selected/playhead",
    "/capture/selected/size",
    "/capture/selected/pos",
    "/web/tab",
]


@dataclass(slots=True)
class SandboxLiveStateResult:
    state: str
    summary: str
    details: list[str]
    source_snapshot: dict[str, Any] | None
    selected_snapshot: dict[str, Any]
    event_names: list[str]


class SandboxLiveStateService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cached_result: SandboxLiveStateResult | None = None

    def snapshot(self) -> SandboxLiveStateResult:
        if self._cached_result is not None:
            return self._cached_result
        if not self.settings.sandbox_is_configured:
            self._cached_result = SandboxLiveStateResult(
                state="not_run",
                summary="Sandbox host/port is not configured, so no live state snapshot was collected.",
                details=[],
                source_snapshot=None,
                selected_snapshot={},
                event_names=[],
            )
            return self._cached_result
        if self.settings.sandbox_transport not in {"http", "https"}:
            self._cached_result = SandboxLiveStateResult(
                state="not_supported",
                summary="Live state snapshotting is currently only supported for HTTP sandbox surfaces.",
                details=[],
                source_snapshot=None,
                selected_snapshot={},
                event_names=[],
            )
            return self._cached_result
        if socketio is None:
            self._cached_result = SandboxLiveStateResult(
                state="dependency_missing",
                summary="python-socketio is not installed, so no live state snapshot was collected.",
                details=[],
                source_snapshot=None,
                selected_snapshot={},
                event_names=[],
            )
            return self._cached_result

        base_url = f"{self.settings.sandbox_transport}://{self.settings.sandbox_host}:{self.settings.sandbox_port}"
        sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False, request_timeout=self.settings.sandbox_timeout_seconds)
        done = Event()
        lock = Lock()
        details: list[str] = []
        event_names: list[str] = []
        selected_snapshot: dict[str, Any] = {}
        source_payload: dict[str, Any] | None = None

        def remember_event(name: str, payload: Any) -> None:
            nonlocal source_payload
            with lock:
                if name not in event_names:
                    event_names.append(name)
                if name == "capture-sources":
                    source_payload = _summarize_sources(payload)
                    if source_payload is not None:
                        details.append(source_payload["summary"])
                        done.set()
                    return
                selected_snapshot[name] = payload

        @sio.event
        def connect() -> None:
            details.append("Connected to the local sandbox Socket.IO surface.")
            sio.emit("ics-ready")

        @sio.event
        def connect_error(data: Any) -> None:
            details.append(f"Socket.IO connect error: {data}")
            done.set()

        @sio.event
        def disconnect() -> None:
            details.append("Socket.IO connection closed.")

        for event_name in KNOWN_STATE_EVENTS:
            sio.on(event_name, handler=lambda payload, event_name=event_name: remember_event(event_name, payload))

        try:
            sio.connect(base_url, transports=["polling"], wait_timeout=self.settings.sandbox_timeout_seconds)
            done.wait(self.settings.sandbox_timeout_seconds)
        except Exception as exc:
            details.append(f"Live state snapshot failed: {exc}")
        finally:
            try:
                sio.disconnect()
            except Exception:
                pass

        if source_payload is not None:
            self._cached_result = SandboxLiveStateResult(
                state="validated",
                summary="Read-only live source state was collected from the running sandbox.",
                details=details,
                source_snapshot=source_payload,
                selected_snapshot=selected_snapshot,
                event_names=event_names,
            )
            return self._cached_result
        self._cached_result = SandboxLiveStateResult(
            state="partial" if event_names else "failed",
            summary="A live sandbox connection was attempted, but no source snapshot was collected.",
            details=details,
            source_snapshot=None,
            selected_snapshot=selected_snapshot,
            event_names=event_names,
        )
        return self._cached_result


def _summarize_sources(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, list):
        return None
    normalized: list[dict[str, Any]] = []
    input_types: Counter[str] = Counter()
    available_count = 0
    enabled_count = 0
    selected_names: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("inputLabel") or item.get("id") or "Unknown")
        input_type = str(item.get("inputType") or "unknown")
        available = bool(item.get("available"))
        enabled = bool(item.get("enabled"))
        selected = bool(item.get("selected"))
        if available:
            available_count += 1
        if enabled:
            enabled_count += 1
        if selected:
            selected_names.append(name)
        input_types[input_type] += 1
        normalized.append(
            {
                "id": item.get("id"),
                "name": name,
                "input_type": input_type,
                "input_label": item.get("inputLabel"),
                "available": available,
                "enabled": enabled,
                "selected": selected,
            }
        )
    top_input_types = [
        {"input_type": name, "count": count}
        for name, count in input_types.most_common(8)
    ]
    if normalized:
        summary = (
            f"Live source snapshot captured {len(normalized)} sources; "
            f"{available_count} available, {enabled_count} enabled"
        )
        if selected_names:
            summary += f", selected = {', '.join(selected_names)}"
        else:
            summary += ", no source currently marked selected"
    else:
        summary = "Live source snapshot captured 0 sources; the sandbox is reachable but no capture sources are currently exposed."
    return {
        "summary": summary,
        "source_count": len(normalized),
        "available_count": available_count,
        "enabled_count": enabled_count,
        "selected_names": selected_names,
        "input_types": top_input_types,
        "sources": normalized,
    }
