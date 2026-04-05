from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", value).strip().replace(" ", "-")
    return cleaned or "igloo-session-draft"


def _first_non_empty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _guess_extension(item: dict[str, object]) -> str:
    location = str(item.get("location", "")).strip()
    if location:
        suffix = Path(location).suffix
        if suffix:
            return suffix
    content_type = str(item.get("content_type", "")).lower()
    if content_type == "360 video" or content_type == "standard video":
        return ".mp4"
    if content_type == "pdf":
        return ".pdf"
    if content_type == "image":
        return ".jpg"
    if content_type == "3d model":
        return ".glb"
    if content_type in {"website", "interactive web", "dashboard app"}:
        return ".url"
    return ".txt"


def _layer_type_for_item(item: dict[str, object]) -> str:
    layer_type = str(item.get("recommended_layer_type", "")).strip()
    content_type = str(item.get("content_type", "")).lower()
    location = str(item.get("location", "")).strip().lower()
    if "youtube" in content_type or "youtube.com" in location or "youtu.be" in location:
        return "YouTube"
    if content_type == "pdf":
        return "PDF"
    if layer_type and layer_type.lower() not in {"modelviewer"}:
        return layer_type
    if content_type in {"website", "interactive web", "dashboard app", "interactive model", "3d model", "review app"} or "webxr" in content_type:
        return "WebView"
    if "image" in content_type:
        return "Image"
    return "Video"


def _format_bool(value: bool) -> str:
    return "1" if value else "0"


def _relative_windows_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("/", "\\")


def _content_is_url(item: dict[str, object]) -> bool:
    location = str(item.get("location", "")).strip()
    return location.startswith(("http://", "https://"))


def _content_is_local_file(item: dict[str, object]) -> bool:
    location = str(item.get("location", "")).strip()
    return bool(location) and not _content_is_url(item) and Path(location).exists()


def _is_media_like(item: dict[str, object]) -> bool:
    content_type = str(item.get("content_type", "")).lower()
    layer_type = _layer_type_for_item(item).lower()
    return content_type not in {"website", "interactive web", "dashboard app"} and layer_type not in {"webview", "home", "contentbank"}


def _position_for_index(index: int, total: int) -> tuple[float, float]:
    if total <= 1:
        return 0.5, 0.5
    if total == 2:
        return (0.32, 0.5) if index == 0 else (0.68, 0.5)
    if total >= 3:
        slots = [0.17, 0.5, 0.83]
        return slots[min(index, 2)], 0.5
    return 0.5, 0.5


def _layout_profile_for_layer(
    item: dict[str, object],
    index: int,
    total: int,
    has_immersive_background: bool,
    setup_archetype: str = "",
    overlay_index: int = 0,
) -> dict[str, object]:
    content_type = str(item.get("content_type", "")).lower()
    title = str(item.get("title", "")).lower()
    layout_role = str(item.get("layout_role", "")).lower()
    archetype = str(setup_archetype or item.get("setup_archetype", "")).lower()
    if content_type in {"360 video", "youtube 360"}:
        return {
            "position_x": 0.5,
            "position_y": 0.5,
            "scale": 1.0,
            "is_background": True,
            "is_pinned": False,
            "always_on_top": False,
            "autoplay": True,
            "loop": True,
            "ui_widget_x": 0.15,
            "ui_widget_y": 0.84,
        }

    if archetype in {"three_wall_canvas", "three_wall_presentation"}:
        return {
            "position_x": 0.5,
            "position_y": 0.5,
            "scale": 1.0 if index == 0 else 0.24,
            "is_background": False,
            "is_pinned": False if index == 0 else True,
            "always_on_top": False if index == 0 else True,
            "autoplay": content_type in {"standard video", "video"},
            "loop": content_type in {"standard video", "video"},
            "ui_widget_x": 0.5 if index == 0 else 0.84,
            "ui_widget_y": 0.88 if index == 0 else 0.16,
        }

    if archetype == "three_wall_dashboard":
        wall_positions = {
            "left wall": (0.17, 0.5),
            "center wall": (0.5, 0.5),
            "right wall": (0.83, 0.5),
            "launcher / support": (0.83, 0.82),
        }
        x, y = wall_positions.get(layout_role, _position_for_index(index, total))
        return {
            "position_x": x,
            "position_y": y,
            "scale": 0.32 if "launcher" not in layout_role else 0.18,
            "is_background": False,
            "is_pinned": "launcher" in layout_role,
            "always_on_top": "launcher" in layout_role,
            "autoplay": content_type in {"standard video", "video"},
            "loop": content_type in {"standard video", "video"},
            "ui_widget_x": x,
            "ui_widget_y": 0.84 if "launcher" not in layout_role else 0.94,
        }

    if archetype == "content_bank_gallery" and "content bank" in layout_role:
        return {
            "position_x": 0.5,
            "position_y": 0.5,
            "scale": 1.0,
            "is_background": False,
            "is_pinned": False,
            "always_on_top": False,
            "autoplay": content_type in {"standard video", "video"},
            "loop": content_type in {"standard video", "video"},
            "ui_widget_x": 0.5,
            "ui_widget_y": 0.88,
        }

    if has_immersive_background:
        overlay_positions = [
            (0.22, 0.26),
            (0.78, 0.26),
            (0.78, 0.74),
            (0.22, 0.74),
        ]
        overlay_index = min(overlay_index, len(overlay_positions) - 1)
        profile = {
            "position_x": overlay_positions[overlay_index][0],
            "position_y": overlay_positions[overlay_index][1],
            "scale": 0.32,
            "is_background": False,
            "is_pinned": True,
            "always_on_top": True,
            "autoplay": content_type in {"standard video", "video"},
            "loop": content_type in {"standard video", "video"},
            "ui_widget_x": overlay_positions[overlay_index][0],
            "ui_widget_y": max(0.08, overlay_positions[overlay_index][1] - 0.16),
        }
        if "pdf" in content_type or "document" in title:
            profile["scale"] = 0.3
        if content_type in {"website", "interactive web", "dashboard app"}:
            profile["scale"] = 0.34
        return profile

    x, y = _position_for_index(index, total)
    return {
        "position_x": x,
        "position_y": y,
        "scale": 0.42 if total > 1 else 1.0,
        "is_background": False,
        "is_pinned": total > 1,
        "always_on_top": total > 1,
        "autoplay": content_type in {"standard video", "video"},
        "loop": content_type in {"standard video", "video"},
        "ui_widget_x": x,
        "ui_widget_y": max(0.08, y - 0.18),
    }


def _ratio_for_content(item: dict[str, object]) -> tuple[int, int]:
    content_type = str(item.get("content_type", "")).lower()
    layout_role = str(item.get("layout_role", "")).lower()
    if layout_role == "three-wall span":
        return 64, 9
    if content_type in {"360 video", "youtube 360"}:
        return 2, 1
    if content_type in {"dashboard app", "website", "interactive web", "pdf"}:
        return 16, 9
    if content_type == "image":
        return 3, 2
    if content_type == "3d model":
        return 1, 1
    return 16, 9


def _render_passes_for_item(item: dict[str, object]) -> str:
    content_type = str(item.get("content_type", "")).lower()
    location = str(item.get("location", "")).lower()
    if content_type not in {"360 video", "youtube 360"} and "youtube.com" not in location and "youtu.be" not in location:
        return ""
    return """
      <RenderPasses>
        <RenderPass>
          <Type>PerspectiveExtraction</Type>
          <ClearColourR>0</ClearColourR>
          <ClearColourG>0</ClearColourG>
          <ClearColourB>0</ClearColourB>
          <ClearColourA>1</ClearColourA>
          <Heading>0</Heading>
          <Pitch>0</Pitch>
          <PitchDirection>0</PitchDirection>
          <Quality>1</Quality>
          <UseCustomHead>0</UseCustomHead>
          <CustomX>0</CustomX>
          <CustomY>0</CustomY>
          <CustomZ>0</CustomZ>
          <UseStretch>0</UseStretch>
        </RenderPass>
      </RenderPasses>"""


def _youtube_video_id(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/")
    if "youtube.com" in host:
        query = parse_qs(parsed.query)
        return query.get("v", [""])[0]
    return ""


class SessionPackageWriter:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def export(self, draft: dict[str, object]) -> dict[str, object]:
        brief = str(draft.get("brief", "")).strip() or "Igloo Session Draft"
        session_import = draft.get("session_import") if isinstance(draft.get("session_import"), dict) else {}
        session_name = _first_non_empty(session_import.get("session_name"), brief[:48]) or "Igloo Draft Session"
        slug = _safe_slug(session_name)
        package_dir = self.base_dir / slug
        counter = 1
        while package_dir.exists():
            package_dir = self.base_dir / f"{slug}-{counter}"
            counter += 1

        assets_dir = package_dir / "Assets"
        references_dir = package_dir / "References"
        assets_dir.mkdir(parents=True, exist_ok=True)
        references_dir.mkdir(parents=True, exist_ok=True)

        selected_content = draft.get("selected_content", [])
        if not isinstance(selected_content, list):
            selected_content = []
        selected_lookup = {
            str(item.get("candidate_id", "")): item
            for item in selected_content
            if isinstance(item, dict) and item.get("candidate_id")
        }
        layer_drafts = draft.get("layer_drafts", [])
        if not isinstance(layer_drafts, list):
            layer_drafts = []
        source_layers = layer_drafts or selected_content
        setup_archetype = str(draft.get("setup_archetype", "")).strip()
        source_items_for_layout: list[dict[str, object]] = []
        for layer_or_item in source_layers:
            if not isinstance(layer_or_item, dict):
                continue
            source_item = selected_lookup.get(str(layer_or_item.get("source_candidate_id", ""))) if layer_drafts else layer_or_item
            source_item = source_item if isinstance(source_item, dict) else {}
            source_items_for_layout.append(source_item)
        has_immersive_background = any(
            str(item.get("content_type", "")).lower() in {"360 video", "youtube 360"}
            for item in source_items_for_layout
        )

        exported_with_assets = True
        has_copied_assets = False
        has_disabled_placeholders = False
        asset_records: list[dict[str, Any]] = []
        layer_xml: list[str] = []
        overlay_counter = 0

        for index, layer_or_item in enumerate(source_layers):
            if not isinstance(layer_or_item, dict):
                continue
            source_item = selected_lookup.get(str(layer_or_item.get("source_candidate_id", ""))) if layer_drafts else layer_or_item
            source_item = source_item if isinstance(source_item, dict) else {}
            title = _first_non_empty(layer_or_item.get("label"), source_item.get("title"), f"Layer {index + 1}")
            layer_type = _layer_type_for_item({"recommended_layer_type": layer_or_item.get("layer_type", ""), **source_item})
            locator, state = self._materialize_source(source_item, title, package_dir, assets_dir, references_dir)
            exported_with_assets = exported_with_assets and state["exported_with_assets"]
            has_copied_assets = has_copied_assets or state["copied_asset"]
            has_disabled_placeholders = has_disabled_placeholders or state["uses_placeholder"]
            if state["record"] is not None:
                asset_records.append(state["record"])

            ratio_x, ratio_y = _ratio_for_content(source_item)
            is_immersive_item = str(source_item.get("content_type", "")).lower() in {"360 video", "youtube 360"}
            layout = _layout_profile_for_layer(
                source_item,
                index,
                len(source_layers),
                has_immersive_background,
                setup_archetype=setup_archetype,
                overlay_index=overlay_counter,
            )
            if has_immersive_background and not is_immersive_item:
                overlay_counter += 1
            position_x = float(layout["position_x"])
            position_y = float(layout["position_y"])
            scale = float(layout["scale"])
            is_background = bool(layout["is_background"])
            is_pinned = bool(layout["is_pinned"])
            always_on_top = bool(layout["always_on_top"])
            is_enabled = not state["uses_placeholder"]
            autoplay = bool(layout["autoplay"])
            loop = bool(layout["loop"])
            ui_widget_x = float(layout["ui_widget_x"])
            ui_widget_y = float(layout["ui_widget_y"])
            render_passes = _render_passes_for_item(source_item)
            layer_uuid = str(uuid.uuid4())
            source_xml = self._source_xml_for_layer(layer_type, source_item, locator, autoplay, loop, render_passes, state)

            layer_xml.append(
                f"""    <Layer streamReceiveBufferSize="100">
      <Metadata></Metadata>
      <Name>{escape(title)}</Name>
      <PositionX>{position_x:.2f}</PositionX>
      <PositionY>{position_y:.2f}</PositionY>
      <RatioX>{ratio_x}</RatioX>
      <RatioY>{ratio_y}</RatioY>
      <StartCropX>0</StartCropX>
      <StartCropY>0</StartCropY>
      <CropSizeX>1</CropSizeX>
      <CropSizeY>1</CropSizeY>
      <WrapX>0</WrapX>
      <WrapY>0</WrapY>
      <Scale>{scale:.3f}</Scale>
      <AspectRatio>0</AspectRatio>
      <ResizeMode>0</ResizeMode>
      <PositionMode>0</PositionMode>
      <ClearColourR>0</ClearColourR>
      <ClearColourG>0</ClearColourG>
      <ClearColourB>0</ClearColourB>
      <ClearColourA>0</ClearColourA>
      <IsPinned>{_format_bool(is_pinned)}</IsPinned>
      <IsBackground>{_format_bool(is_background)}</IsBackground>
      <IsTemplate>0</IsTemplate>
      <ExePath></ExePath>
      <UiEnabled>1</UiEnabled>
      <NamedByUser>1</NamedByUser>
      <AudioVolume>0.5</AudioVolume>
      <AudioMute>0</AudioMute>
      <AudioDelay>0</AudioDelay>
      <OnAddBat></OnAddBat>
      <OnRemoveBat></OnRemoveBat>
      <IsAlwaysOnTop>{_format_bool(always_on_top)}</IsAlwaysOnTop>
      <ControlScreenVis>0</ControlScreenVis>
      <IsEnabled>{_format_bool(is_enabled)}</IsEnabled>
      <StereoFormat>0</StereoFormat>
      <UiWidgetX>{ui_widget_x:.2f}</UiWidgetX>
      <UiWidgetY>{ui_widget_y:.2f}</UiWidgetY>
      <UUID>{layer_uuid}</UUID>
      <Type>{escape(layer_type)}</Type>{source_xml}
    </Layer>"""
            )

        if not has_copied_assets and not any(record.get("type") == "asset" for record in asset_records):
            exported_with_assets = False
        if has_disabled_placeholders:
            exported_with_assets = False

        trigger_enabled = any(
            str(layer.get("layer_type", "")).lower() in {"home", "contentbank"} for layer in layer_drafts if isinstance(layer, dict)
        ) or bool(session_import.get("trigger_action_enabled"))
        product_version = _first_non_empty(session_import.get("product_version"), "1.5.0.250527-1")
        thumbnail = self._thumbnail_for(selected_content)
        xml_content = f"""<?xml version="1.0"?>
<ProductVersion>
  <Major>1</Major>
  <Minor>5</Minor>
  <Patch>0</Patch>
  <VersionString>{escape(product_version)}</VersionString>
</ProductVersion>
<Session>
  <Id>{uuid.uuid4()}</Id>
  <Name>{escape(session_name)}</Name>
  <Description>{escape(brief)}</Description>
  <Thumbnail>{escape(thumbnail)}</Thumbnail>
  <ReadOnly>0</ReadOnly>
  <Tags></Tags>
  <ExportedWithAssets>{_format_bool(exported_with_assets)}</ExportedWithAssets>
  <Metadata></Metadata>
  <Layers>
    <ExportedWithAssets>{_format_bool(exported_with_assets)}</ExportedWithAssets>
{chr(10).join(layer_xml)}
  </Layers>
  <Layouts>
    <Layout name="Default Layout">
      <Region name="Front" left="0" right="0.236" bottom="0.3549" top="0" />
      <Region name="Right" left="0.236" right="0.5" bottom="0.3549" top="0" />
      <Region name="Back" left="0.5" right="0.736" bottom="0.3549" top="0" />
      <Region name="Left" left="0.736" right="1" bottom="0.3549" top="0" />
      <Region name="Walls" left="0" right="1" bottom="0.3549" top="0" />
      <Region name="Floor" left="0.5" right="0.736" bottom="1" top="0.3549" />
      <Region name="3 walls" left="0.236" right="1" bottom="0.3549" top="0" />
      <Region name="Touch walls" left="0.5" right="1" bottom="0.355" top="0" />
    </Layout>
  </Layouts>
</Session>
<ta>
  <enabled>{_format_bool(trigger_enabled)}</enabled>
  <triggers></triggers>
</ta>
"""
        session_path = package_dir / f"{_safe_slug(session_name)}.iceSession"
        session_path.write_text(xml_content, encoding="utf-8")

        package_summary = {
            "brief": brief,
            "session_name": session_name,
            "exported_with_assets": exported_with_assets,
            "asset_records": asset_records,
            "uses_placeholders": has_disabled_placeholders,
            "selected_content_count": len(selected_content),
            "layer_count": len(layer_xml),
            "session_import_basis": session_import.get("session_name") if session_import else None,
        }
        manifest_path = package_dir / "package_manifest.json"
        manifest_path.write_text(
            json.dumps({"draft": draft, "package_summary": package_summary}, indent=2),
            encoding="utf-8",
        )

        notes_path = package_dir / "README.txt"
        notes_path.write_text(
            "\n".join(
                [
                    "Igloo Experience Builder Pilot - Draft session package",
                    "",
                    f"Session name: {session_name}",
                    f"Exported with assets: {'yes' if exported_with_assets else 'no'}",
                    "",
                    "This package is shaped like a real Igloo session folder and is intended as a practical starting point.",
                    "Layers that still point to placeholder files are disabled in the draft session until you replace them with real assets.",
                    "WebView-style layers keep direct URLs in the session file and also get shortcut references under References.",
                    "Replace placeholders with final files, links, or apps before treating this as room-ready.",
                ]
            ),
            encoding="utf-8",
        )

        return {
            "saved": True,
            "package_dir": str(package_dir),
            "session_path": str(session_path),
            "manifest_path": str(manifest_path),
            "notes_path": str(notes_path),
            "exported_with_assets": exported_with_assets,
            "asset_records": asset_records,
        }

    def _source_xml_for_layer(
        self,
        layer_type: str,
        item: dict[str, object],
        locator: str,
        autoplay: bool,
        loop: bool,
        render_passes: str,
        state: dict[str, Any],
    ) -> str:
        ratio_x, ratio_y = _ratio_for_content(item)
        size_x = 8000 if ratio_x == 2 and ratio_y == 1 else 1920
        size_y = 4000 if ratio_x == 2 and ratio_y == 1 else 1080
        content_type = str(item.get("content_type", "")).lower()
        if layer_type == "YouTube":
            video_id = str(state.get("youtube_id", "")).strip()
            youtube_url = locator
            if video_id:
                youtube_url = f"http://localhost:800/icetube/?v={video_id}&autoplay={1 if autoplay else 0}&loop={1 if loop else 0}"
            return f"""
      <URL>{escape(youtube_url)}</URL>
      <SizeX>{size_x}</SizeX>
      <SizeY>{size_y}</SizeY>
      <AutoPlay>{_format_bool(autoplay)}</AutoPlay>
      <AutoLoop>{_format_bool(loop)}</AutoLoop>
      <DynamicRes>0</DynamicRes>
      <AudioVolume>0.5</AudioVolume>
      <AudioMute>0</AudioMute>
      <AudioDelay>0</AudioDelay>
      <AutoMaxResolution>1</AutoMaxResolution>{render_passes}"""
        if layer_type == "WebView":
            allow_popups = content_type in {"interactive web", "dashboard app", "interactive model", "3d model", "review app"}
            return f"""
      <URL>{escape(locator)}</URL>
      <SizeX>{size_x}</SizeX>
      <SizeY>{size_y}</SizeY>
      <DynamicRes>1</DynamicRes>
      <UseCustomFPS>0</UseCustomFPS>
      <CustomFPSValue>60</CustomFPSValue>
      <UseAlpha>0</UseAlpha>
      <AllowPopups>{_format_bool(allow_popups)}</AllowPopups>
      <AudioVolume>0.5</AudioVolume>
      <AudioMute>0</AudioMute>
      <AudioDelay>0</AudioDelay>
      <ZoomLevel>0</ZoomLevel>
      <BackgroundColourR>0</BackgroundColourR>
      <BackgroundColourG>0</BackgroundColourG>
      <BackgroundColourB>0</BackgroundColourB>
      <BackgroundColourA>1</BackgroundColourA>{render_passes}"""
        if layer_type == "PDF":
            return f"""
      <FilePath>{escape(locator)}</FilePath>
      <SizeX>{size_x}</SizeX>
      <SizeY>{size_y}</SizeY>{render_passes}"""
        return f"""
      <FilePath>{escape(locator)}</FilePath>
      <Loop>{_format_bool(loop)}</Loop>
      <AutoPlay>{_format_bool(autoplay)}</AutoPlay>
      <Speed>1</Speed>
      <StartTime>0</StartTime>
      <EndTime>0</EndTime>
      <AudioVolume>0.5</AudioVolume>
      <AudioMute>0</AudioMute>
      <AudioDelay>0</AudioDelay>
      <StreamBuffers>200</StreamBuffers>{render_passes}"""

    def _materialize_source(
        self,
        item: dict[str, object],
        title: str,
        package_dir: Path,
        assets_dir: Path,
        references_dir: Path,
    ) -> tuple[str, dict[str, Any]]:
        location = str(item.get("location", "")).strip()
        content_type = str(item.get("content_type", "")).lower()
        slug = _safe_slug(title)
        layer_type = _layer_type_for_item(item)

        if _content_is_url(item):
            shortcut_path = references_dir / f"{slug}.url"
            shortcut_path.write_text(f"[InternetShortcut]\nURL={location}\n", encoding="utf-8")
            youtube_id = _youtube_video_id(location)
            return location, {
                "exported_with_assets": False,
                "copied_asset": False,
                "uses_placeholder": False,
                "youtube_id": youtube_id,
                "record": {
                    "title": title,
                    "type": "url",
                    "path": location,
                    "reference_shortcut": str(shortcut_path),
                    "layer_type": layer_type,
                },
            }

        if _content_is_local_file(item):
            source_path = Path(location)
            target_path = assets_dir / f"{slug}{source_path.suffix}"
            if source_path.resolve() != target_path.resolve():
                shutil.copy2(source_path, target_path)
            return _relative_windows_path(target_path, package_dir), {
                "exported_with_assets": True,
                "copied_asset": True,
                "uses_placeholder": False,
                "youtube_id": "",
                "record": {
                    "title": title,
                    "type": "asset",
                    "source_path": str(source_path),
                    "package_path": str(target_path),
                    "layer_type": layer_type,
                },
            }

        extension = _guess_extension(item)
        if _is_media_like(item):
            placeholder_path = assets_dir / f"{slug}{extension}.placeholder.txt"
        else:
            placeholder_path = references_dir / f"{slug}.placeholder.txt"
        placeholder_path.write_text(
            "\n".join(
                [
                    f"Title: {title}",
                    f"Content type: {item.get('content_type', '')}",
                    f"Suggested query: {item.get('query_hint', '')}",
                    "",
                    "This is a builder placeholder. Replace it with the real file, URL, or app route before live use.",
                ]
            ),
            encoding="utf-8",
        )
        return _relative_windows_path(placeholder_path, package_dir), {
            "exported_with_assets": False,
            "copied_asset": False,
            "uses_placeholder": True,
            "youtube_id": "",
            "record": {
                "title": title,
                "type": "placeholder",
                "package_path": str(placeholder_path),
                "layer_type": layer_type,
            },
        }

    def _thumbnail_for(self, selected_content: list[dict[str, object]]) -> str:
        joined = " ".join(str(item.get("content_type", "")).lower() for item in selected_content if isinstance(item, dict))
        if "image" in joined:
            return "{default}images\\thumbnails\\layers\\image.png"
        if "website" in joined or "interactive web" in joined or "dashboard app" in joined:
            return "{default}images\\thumbnails\\layers\\browser.png"
        return "{default}images\\thumbnails\\layers\\video.png"
