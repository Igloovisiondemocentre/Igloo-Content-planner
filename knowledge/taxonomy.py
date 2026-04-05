from __future__ import annotations

from igloo_experience_builder.knowledge.text_utils import collapse_capitalized_artifacts, normalize_whitespace

CANONICAL_CONCEPTS: dict[str, tuple[str, ...]] = {
    "session": ("session", "sessions", "save session", "reusable session", "content library"),
    "layer": ("layer", "layers", "webview layer", "video layer", "pinned layer"),
    "360_content": (
        "360",
        "360-degree",
        "360 degree",
        "360 video",
        "360 image",
        "360 imagery",
        "immersive",
        "panoramic",
        "virtual tour",
        "youtube 360",
        "street view",
    ),
    "image": (
        "image",
        "images",
        "still image",
        "still images",
        "photo",
        "photos",
        "jpg",
        "jpeg",
        "png",
    ),
    "model_viewer": (
        "3d model",
        "3d models",
        "model viewer",
        "bim",
        "digital twin",
        "revizto",
        "revistoo",
        "revit",
        "autodesk",
        "dwg",
        "aeco",
        "architectural",
        "architecture",
        "design review",
        "point cloud",
        "glb",
        "gltf",
        "fbx",
        "obj",
        "onshape",
    ),
    "content_bank": (
        "content bank",
        "tile",
        "tiles",
        "active tile",
        "playlist",
        "session launcher",
    ),
    "home": (
        "home",
        "home layer",
        "home layout",
        "layout tile",
        "trigger tile",
        "home components",
        "homescreen",
    ),
    "true_perspective": (
        "true perspective",
        "custom head position",
        "head position",
        "wheelchair height",
    ),
    "audio": (
        "audio",
        "spatial audio",
        "surround sound",
        "5.1",
    ),
    "training_workflow": (
        "training",
        "education",
        "learning",
        "simulation",
        "school",
        "classroom",
        "hazard",
        "industrial training",
        "interactive vr",
    ),
    "webview": ("webview", "web view", "browser layer", "website"),
    "pdf": ("pdf", "document", "pdf document", "documents in pdf format"),
    "website": ("website", "web site", "url", "webview", "browser"),
    "video": ("video", "movie", "youtube", "playback", "media"),
    "playback": ("playback", "play", "media", "video", "volume"),
    "content_library": ("content library", "content bank", "media library", "session library"),
    "control_surface": ("control panel", "canvas toolbar", "desktop ui", "canvas ui", "control surface"),
    "integration": ("integration", "matterport", "street view", "osc", "uri", "api", "udp", "tcp"),
    "local_workflow": ("local", "sandbox", "media player", "igloo core service", "igloo core engine"),
    "remote_workflow": ("remote", "transfer", "export", "import", "bundle"),
    "trigger_action": (
        "trigger",
        "triggers",
        "action",
        "actions",
        "trigger and action",
        "triggers and actions",
        "interactive",
        "clickable",
        "tap",
        "taps",
        "hotspot",
        "hotspots",
        "reveal",
        "icon",
        "icons",
        "button",
        "buttons",
        "subscribe",
        "set url",
        "active tile",
    ),
}


PRIMARY_REQUEST_CONCEPTS = {
    "session",
    "layer",
    "360_content",
    "model_viewer",
    "content_bank",
    "home",
    "true_perspective",
    "audio",
    "image",
    "webview",
    "pdf",
    "website",
    "video",
    "content_library",
    "control_surface",
    "integration",
    "local_workflow",
    "remote_workflow",
    "trigger_action",
}

KNOWN_WORKING_BASELINE_CONCEPTS = {
    "audio",
    "content_bank",
    "content_library",
    "home",
    "image",
    "layer",
    "model_viewer",
    "pdf",
    "playback",
    "session",
    "video",
    "website",
    "webview",
    "360_content",
}


def concepts_for_text(text: str) -> list[str]:
    normalized = collapse_capitalized_artifacts(text).lower()
    matches = [concept for concept, aliases in CANONICAL_CONCEPTS.items() if any(alias in normalized for alias in aliases)]
    return sorted(set(matches))


def text_matches_concept(text: str, concept: str) -> bool:
    normalized = collapse_capitalized_artifacts(text).lower()
    aliases = CANONICAL_CONCEPTS.get(concept, (concept,))
    return any(alias in normalized for alias in aliases)


def request_concepts(text: str) -> list[str]:
    concepts = [concept for concept in concepts_for_text(text) if concept in PRIMARY_REQUEST_CONCEPTS]
    return concepts or concepts_for_text(text)


def feature_dependencies(concepts: list[str]) -> list[str]:
    dependencies: list[str] = []
    concept_set = set(concepts)
    if "pdf" in concept_set:
        dependencies.append("A PDF asset stored on the Igloo Media Player or exposed by a reachable URL.")
    if "360_content" in concept_set:
        dependencies.append("A compatible 360 image, 360 video, or hosted 360 content source that the chosen layer can access.")
    if "image" in concept_set:
        dependencies.append("Prepared image assets in expected formats such as JPG or PNG that the target Igloo environment can access.")
    if "model_viewer" in concept_set:
        dependencies.append("A supported 3D model, BIM viewer, or model-viewer workflow that the target Igloo environment can load.")
    if "content_bank" in concept_set:
        dependencies.append("Configured Content Bank or Home content tiles that point to the intended media, layers, or sessions.")
    if "home" in concept_set:
        dependencies.append("A Home layout or trigger-tile structure configured for the intended operator or visitor interaction flow.")
    if "true_perspective" in concept_set:
        dependencies.append("True Perspective calibration data and head-position settings appropriate to the intended viewing position.")
    if "website" in concept_set or "webview" in concept_set:
        dependencies.append("A WebView-capable layer with a reachable website URL.")
    if "audio" in concept_set:
        dependencies.append("An audio-capable layer and output path configured for the required playback or surround routing.")
    if "video" in concept_set:
        dependencies.append("A compatible video source or streaming target that the configured layer can access.")
    if "session" in concept_set:
        dependencies.append("A saved session in the content/session library so the workflow can be reused.")
    if "integration" in concept_set:
        dependencies.append("Any external integration endpoint must remain reachable from the target Igloo environment.")
    dependencies.append("Operator review before client-facing commitment if the answer carries ambiguity or risk.")
    return list(dict.fromkeys(dependencies))
