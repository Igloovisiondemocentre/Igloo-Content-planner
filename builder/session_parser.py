from __future__ import annotations

import re
from pathlib import Path

from igloo_experience_builder.builder.models import SessionImportSummary, SessionLayerSummary


TAG_RE = re.compile(r"<(?P<tag>[A-Za-z0-9_:-]+)(?:\s[^>]*)?>(?P<body>.*?)</(?P=tag)>", re.DOTALL)


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _extract_first(text: str, tag: str) -> str:
    match = re.search(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", text, re.DOTALL)
    if match:
        return _clean(match.group(1))
    self_closing = re.search(rf"<{tag}(?:\s[^>]*)?/>", text)
    if self_closing:
        return ""
    return ""


def _extract_blocks(text: str, tag: str) -> list[str]:
    return [match.group(1) for match in re.finditer(rf"<{tag}(?:\s[^>]*)?>(.*?)</{tag}>", text, re.DOTALL)]


def _extract_bool(text: str, tag: str) -> bool:
    return _extract_first(text, tag) in {"1", "true", "True"}


def _extract_layer_source(block: str) -> tuple[str, str]:
    for tag in ("FilePath", "URL", "ExePath", "SenderName"):
        value = _extract_first(block, tag)
        if value:
            return value, tag
    return "", ""


def _infer_content_type(layer_type: str, file_path: str, render_passes: list[str]) -> str:
    extension = Path(file_path).suffix.lower()
    normalized_type = layer_type.lower()
    normalized_path = file_path.lower()
    if normalized_type == "youtube":
        return "YouTube 360" if "PerspectiveExtraction" in render_passes else "youtube"
    if normalized_type == "webview":
        if "PerspectiveExtraction" in render_passes:
            return "interactive web"
        if "skybox" in normalized_path or "webxr" in normalized_path:
            return "interactive web"
        return "website"
    if normalized_type == "pdf":
        return "pdf"
    if normalized_type == "spout":
        return "immersive media" if "PerspectiveExtraction" in render_passes else "app stream"
    if "PerspectiveExtraction" in render_passes or "InputTranslation" in render_passes:
        if extension in {".mp4", ".mov", ".mkv"}:
            return "360 video"
        return "immersive media"
    if normalized_type == "video" or extension in {".mp4", ".mov", ".mkv", ".avi"}:
        return "video"
    if extension in {".pdf"}:
        return "pdf"
    if extension in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        return "image"
    if file_path.startswith("http://") or file_path.startswith("https://"):
        return "website"
    return layer_type.lower() or "unknown"


def _infer_experience_type(content_type: str, render_passes: list[str]) -> str:
    if "PerspectiveExtraction" in render_passes:
        return "immersive"
    if "InputTranslation" in render_passes or "ISF" in render_passes:
        return "processed media"
    if content_type in {"video", "pdf", "image", "website", "youtube", "YouTube 360"}:
        return "flat"
    return "mixed"


def _score_layer_readiness(file_path: str, content_type: str, render_passes: list[str]) -> tuple[str, int, list[str]]:
    notes: list[str] = []
    score = 60
    status = "usable with prep"
    if not file_path:
        return "blocked", 20, ["The layer does not point to a file path or URL yet."]
    if file_path.startswith("http://") or file_path.startswith("https://"):
        notes.append("This layer points to a hosted source; reachability and playback still need checking.")
        score -= 5
    elif file_path.startswith("localhost:") or "localhost:" in file_path:
        notes.append("This layer points to a localhost route; confirm the local service behind it is available on the target machine.")
        score -= 8
    elif re.match(r"^[A-Za-z]:\\", file_path):
        if Path(file_path).exists():
            notes.append("The referenced local file exists on this machine.")
            score += 20
            status = "ready"
        else:
            notes.append("The referenced local file was not found on this machine.")
            score -= 15
    else:
        notes.append("This layer uses a relative media path; import/export packaging still needs checking.")
        score -= 5
    if content_type == "360 video":
        notes.append("Perspective extraction or cubemap-style processing suggests this is already configured for immersive playback.")
        score += 10
    if "PerspectiveExtraction" in render_passes:
        notes.append("Perspective extraction is configured on this layer.")
    if "ISF" in render_passes:
        notes.append("The layer uses a shader pre-processing pass.")
    if "InputTranslation" in render_passes:
        notes.append("The layer includes an input-translation step before perspective extraction.")
    score = max(0, min(100, score))
    if score >= 80:
        status = "ready"
    elif score >= 55:
        status = "usable with prep"
    elif score >= 35:
        status = "needs checking"
    else:
        status = "poor fit"
    return status, score, notes


class IceSessionParser:
    def parse_text(self, filename: str, content: str) -> SessionImportSummary:
        version = _extract_first(content, "VersionString")
        session_name = _extract_first(content, "Name")
        session_id = _extract_first(content, "Id")
        exported_with_assets = _extract_bool(content, "ExportedWithAssets")
        ta_match = re.search(r"<ta>(.*?)</ta>", content, re.DOTALL)
        trigger_action_enabled = _extract_bool(ta_match.group(1), "enabled") if ta_match else False

        layers: list[SessionLayerSummary] = []
        for index, block in enumerate(_extract_blocks(content, "Layer"), start=1):
            name = _extract_first(block, "Name") or f"Layer {index}"
            layer_type = _extract_first(block, "Type") or "Unknown"
            file_path, source_field = _extract_layer_source(block)
            autoplay = _extract_bool(block, "AutoPlay")
            loop = _extract_bool(block, "Loop") or _extract_bool(block, "AutoLoop")
            render_passes = [_extract_first(render_block, "Type") or "Unknown" for render_block in _extract_blocks(block, "RenderPass")]
            content_type = _infer_content_type(layer_type, file_path, render_passes)
            experience_type = _infer_experience_type(content_type, render_passes)
            readiness_status, readiness_score, notes = _score_layer_readiness(file_path, content_type, render_passes)
            playback_flags = []
            if autoplay:
                playback_flags.append("autoplay")
            if loop:
                playback_flags.append("loop")
            audio_volume = _extract_first(block, "AudioVolume")
            if audio_volume:
                playback_flags.append(f"audio {audio_volume}")
            if source_field:
                notes.append(f"Primary layer source is coming from <{source_field}>.")
            sender_name = _extract_first(block, "SenderName")
            exe_path = _extract_first(block, "ExePath")
            url = _extract_first(block, "URL")
            if url and source_field != "URL":
                notes.append(f"Layer also includes URL: {url}")
            if sender_name:
                notes.append(f"Layer uses sender: {sender_name}")
            if exe_path:
                notes.append(f"Layer executable path: {exe_path}")
            layers.append(
                SessionLayerSummary(
                    layer_id=_extract_first(block, "UUID") or f"layer-{index}",
                    name=name,
                    layer_type=layer_type,
                    file_path=file_path,
                    source_field=source_field,
                    playback_flags=playback_flags,
                    render_passes=render_passes,
                    inferred_content_type=content_type,
                    inferred_experience_type=experience_type,
                    readiness_status=readiness_status,
                    readiness_score=readiness_score,
                    notes=notes,
                )
            )

        inferred_session_type = "mixed media session"
        if layers and all(layer.inferred_content_type == "360 video" for layer in layers):
            inferred_session_type = "immersive 360 playback session"
        elif layers and all(layer.inferred_content_type == "video" for layer in layers):
            inferred_session_type = "video playback session"

        notes: list[str] = []
        if exported_with_assets:
            notes.append("This session was exported with assets, which makes it a stronger portability reference.")
        else:
            notes.append("This session references external or local paths without bundling assets.")
        if trigger_action_enabled:
            notes.append("Triggers and Actions are enabled at the session level.")
        if any("PerspectiveExtraction" in layer.render_passes for layer in layers):
            notes.append("The session includes perspective-extraction steps, which is a strong signal of immersive playback setup.")

        return SessionImportSummary(
            source_name=filename,
            product_version=version or "unknown",
            session_name=session_name or Path(filename).stem,
            session_id=session_id or "",
            exported_with_assets=exported_with_assets,
            trigger_action_enabled=trigger_action_enabled,
            layer_count=len(layers),
            inferred_session_type=inferred_session_type,
            notes=notes,
            layers=layers,
        )
