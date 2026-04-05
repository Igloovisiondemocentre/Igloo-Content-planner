from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from igloo_experience_builder.builder.sample_catalog import SampleContentCatalog
from igloo_experience_builder.config.settings import Settings


DDG_HTML_URL = "https://html.duckduckgo.com/html/"
YOUTUBE_SEARCH_API_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos"
NASA_SEARCH_API_URL = "https://images-api.nasa.gov/search"
RESULT_LINK_RE = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
    re.DOTALL,
)
SNIPPET_RE = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>', re.DOTALL)
TITLE_RE = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)
META_TAG_RE = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?P<name>[^"\']+)["\'][^>]+content=["\'](?P<content>[^"\']+)["\']',
    re.IGNORECASE,
)
RESOLUTION_TERMS = ("4k", "2160", "uhd", "4320", "8k", "maxres")
STOPWORDS = {
    "a",
    "an",
    "and",
    "best",
    "class",
    "content",
    "experience",
    "for",
    "from",
    "igloo",
    "in",
    "into",
    "lesson",
    "like",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "transported",
    "travel",
    "travelling",
    "traveling",
    "students",
    "student",
    "teachers",
    "teacher",
    "see",
    "show",
    "what",
    "video",
    "with",
}
GENERIC_QUERY_TOKENS = {
    "360",
    "4k",
    "8k",
    "youtube",
    "vr",
    "website",
    "webview",
    "web",
    "education",
    "lesson",
    "intro",
    "video",
    "pdf",
    "interactive",
    "dashboard",
    "model",
    "review",
    "app",
    "site",
    "scene",
    "content",
    "explainer",
}
TRUSTED_EDU_HINTS = (".edu", ".ac.uk", "nasa.gov", "museum", "nationalgeographic", "youtube.com", "youtu.be")
INTERACTIVE_MODEL_DOMAINS = ("sketchfab.com", "revizto.com", "autodesk.com", "aps.autodesk.com", "forge.autodesk.com")
IMMERSIVE_WEB_DOMAINS = ("thinglink.com", "kuula.co", "roundme.com", "tfl.gov.uk", "nasa.gov", "nationalgeographic.com")
REVIEW_APP_DOMAINS = ("powerbi.com", "tableau.com", "lookerstudio.google.com", "grafana.com", "teams.microsoft.com", "revizto.com")
GENERIC_HOST_PENALTIES = ("about", "contact", "blog", "news", "press", "careers")


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    source: str
    snippet: str
    content_type: str
    readiness_status: str
    resolution_label: str
    notes: list[str]
    thumbnail_url: str = ""
    provider: str = ""
    match_score: int = 0
    preview_caption: str = ""
    asset_location: str = ""
    recommended_layer_type: str = ""
    setup_archetype: str = ""
    layout_role: str = ""
    setup_summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "snippet": self.snippet,
            "content_type": self.content_type,
            "readiness_status": self.readiness_status,
            "resolution_label": self.resolution_label,
            "notes": self.notes,
            "thumbnail_url": self.thumbnail_url,
            "provider": self.provider,
            "match_score": self.match_score,
            "preview_caption": self.preview_caption,
            "asset_location": self.asset_location,
            "recommended_layer_type": self.recommended_layer_type,
            "setup_archetype": self.setup_archetype,
            "layout_role": self.layout_role,
            "setup_summary": self.setup_summary,
        }


def _strip_tags(value: str) -> str:
    return re.sub(r"<.*?>", "", html.unescape(value)).strip()


def _decode_ddg_url(href: str) -> str:
    if href.startswith("//"):
        href = f"https:{href}"
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        if "uddg" in query:
            return query["uddg"][0]
    return href


class ContentSearchService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings
        self.timeout_seconds = settings.request_timeout_seconds if settings else 20
        self.metadata_timeout_seconds = settings.site_metadata_timeout_seconds if settings else 6.0
        self.youtube_api_key = settings.youtube_api_key if settings else None
        self.sample_catalog = SampleContentCatalog(settings) if settings else None

    def search(self, query: str, mode: str, require_4k: bool = False, limit: int = 8) -> dict[str, object]:
        normalized_query = query.strip()
        if not normalized_query:
            return {"query": query, "mode": mode, "results": [], "notes": ["Enter a query before searching."]}
        search_queries = self._build_query_variants(normalized_query, mode, require_4k)
        search_query = search_queries[0]
        notes: list[str] = []
        results_by_url: dict[str, SearchResult] = {}
        for index, candidate_query in enumerate(search_queries):
            if mode == "youtube_360" and self.youtube_api_key:
                current_results = self._search_youtube_api(candidate_query, require_4k=require_4k, limit=limit)
                if index == 0:
                    notes.append("YouTube results are coming from the YouTube Data API when an API key is configured.")
            else:
                current_results = self._search_duckduckgo(candidate_query, mode=mode, require_4k=require_4k, limit=limit)
                if index == 0:
                    notes.append("Search results are coming from web search and still need exact-item checks.")
            if "nasa" in candidate_query.lower() and mode in {"youtube_360", "website", "immersive_web"}:
                current_results.extend(self._search_nasa(candidate_query, limit=max(2, min(4, limit))))
            for item in current_results:
                existing = results_by_url.get(item.url)
                if existing is None or item.match_score > existing.match_score:
                    results_by_url[item.url] = item
            if len(results_by_url) >= limit:
                break
        results = sorted(results_by_url.values(), key=lambda item: item.match_score, reverse=True)[:limit]
        fallback_notes: list[str] = []
        if self.sample_catalog is not None:
            fallback_entries = self.sample_catalog.search(
                query=normalized_query,
                mode=mode,
                scorer=self._score_result,
                require_4k=require_4k,
                limit=max(3, limit),
            )
            added_fallback = False
            for entry in fallback_entries:
                item = SearchResult(
                    title=str(entry.get("title", "")),
                    url=str(entry.get("url", "")),
                    source=str(entry.get("source", "sample catalog")),
                    snippet=str(entry.get("snippet", "")),
                    content_type=str(entry.get("content_type", "")),
                    readiness_status=str(entry.get("readiness_status", "usable with prep")),
                    resolution_label=str(entry.get("resolution_label", "Sample route")),
                    notes=[str(note) for note in entry.get("notes", []) if isinstance(note, str)],
                    thumbnail_url=str(entry.get("thumbnail_url", "")),
                    provider=str(entry.get("provider", "")),
                    match_score=int(entry.get("match_score", 0)),
                    preview_caption=str(entry.get("preview_caption", "")),
                    asset_location=str(entry.get("asset_location", "")),
                    recommended_layer_type=str(entry.get("recommended_layer_type", "")),
                    setup_archetype=str(entry.get("setup_archetype", "")),
                    layout_role=str(entry.get("layout_role", "")),
                    setup_summary=str(entry.get("setup_summary", "")),
                )
                existing = results_by_url.get(item.url)
                if existing is None or item.match_score > existing.match_score:
                    results_by_url[item.url] = item
                    added_fallback = True
            results = sorted(results_by_url.values(), key=lambda item: item.match_score, reverse=True)[:limit]
            if added_fallback and any(item.source == "sample catalog" for item in results):
                fallback_notes.append("Relevant local example sessions were merged into the search results so the builder can offer stronger known-good starting points, not just live web results.")
        if len(search_queries) > 1 and len(results) > 0:
            notes.append("The builder broadened the search terms automatically when the first exact phrasing looked too narrow.")
        if require_4k:
            notes.append("4K+ filtering still uses title, snippet, and available metadata cues. Exact playback resolution should be checked before client-facing use.")
        if mode in {"webxr", "immersive_web"}:
            notes.append("WebXR results are discovery aids only and should still be treated as app/integration-risk workflows in Phase 1/2.")
        notes.extend(fallback_notes)
        return {
            "query": normalized_query,
            "effective_query": search_query,
            "query_variants": search_queries,
            "mode": mode,
            "results": [item.to_dict() for item in results],
            "notes": notes,
        }

    def auto_search_candidates(self, candidates: list[dict[str, object]], limit_per_candidate: int = 4) -> dict[str, object]:
        groups: list[dict[str, object]] = []
        for candidate in candidates:
            query = str(candidate.get("query_hint", "")).strip() or str(candidate.get("title", "")).strip()
            if not query:
                continue
            mode = self._mode_for_candidate(candidate)
            require_4k = mode == "youtube_360"
            result = self.search(query=query, mode=mode, require_4k=require_4k, limit=limit_per_candidate)
            items = result.get("results", [])
            if not isinstance(items, list):
                items = []
            groups.append(
                {
                    "candidate_id": candidate.get("candidate_id", ""),
                    "title": candidate.get("title", ""),
                    "query": query,
                    "mode": mode,
                    "best_result": items[0] if items else None,
                    "alternatives": items[:limit_per_candidate],
                    "notes": result.get("notes", []),
                }
            )
        return {"groups": groups}

    def _mode_for_candidate(self, candidate: dict[str, object]) -> str:
        content_type = str(candidate.get("content_type", "")).lower()
        query_hint = str(candidate.get("query_hint", "")).lower()
        if "360" in content_type:
            return "youtube_360"
        if "image" in content_type:
            return "website"
        if "3d model" in content_type or any(token in query_hint for token in ("sketchfab", "revizto", "autodesk", "bim", "model viewer")):
            return "interactive_model"
        if "dashboard" in content_type or any(token in query_hint for token in ("powerbi", "tableau", "grafana", "dashboard", "sales review", "teams call")):
            return "review_app"
        if any(token in query_hint for token in ("webxr", "thinglink", "interactive", "virtual tour", "webapp", "web app", "360 bus")):
            return "immersive_web"
        if "webxr" in query_hint:
            return "webxr"
        return "website"

    def _build_query(self, query: str, mode: str, require_4k: bool) -> str:
        normalized = re.sub(r"\s+", " ", query).strip()
        if mode == "youtube_360":
            parts = [normalized]
            if "360" not in normalized.lower():
                parts.append("360")
            if "youtube" not in normalized.lower():
                parts.append("YouTube")
            if require_4k and not any(term in normalized.lower() for term in RESOLUTION_TERMS):
                parts.append("4K")
            return " ".join(parts)
        if mode == "webxr":
            if "webxr" in normalized.lower():
                return normalized
            return f"{normalized} WebXR"
        if mode == "interactive_model":
            if any(token in normalized.lower() for token in ("sketchfab", "revizto", "autodesk", "bim", "model viewer")):
                return normalized
            return f"{normalized} Sketchfab model"
        if mode == "immersive_web":
            if any(token in normalized.lower() for token in ("interactive", "webxr", "virtual tour", "thinglink", "360")):
                return normalized
            return f"{normalized} interactive 360 experience"
        if mode == "review_app":
            if any(token in normalized.lower() for token in ("powerbi", "tableau", "dashboard", "teams", "revizto")):
                return normalized
            return f"{normalized} Power BI dashboard"
        return normalized

    def _build_query_variants(self, query: str, mode: str, require_4k: bool) -> list[str]:
        base = self._build_query(query, mode, require_4k)
        variants: list[str] = [base]
        lowered = base.lower()

        def add_variant(value: str) -> None:
            cleaned = re.sub(r"\s+", " ", value).strip()
            if cleaned and cleaned.lower() not in {item.lower() for item in variants}:
                variants.append(cleaned)

        if mode == "youtube_360":
            softened = lowered.replace("archival", "").replace("archive", "").strip()
            softened = re.sub(r"\s+", " ", softened)
            if "heritage" in softened or "historic" in softened or "museum" in softened:
                add_variant(softened.replace("heritage", "heritage site").replace("historic", "historic site"))
                add_variant(softened.replace("heritage", "museum").replace("historic", "museum"))
                add_variant(softened.replace("archival", "").replace("heritage", "industrial heritage"))
            if "steel" in softened:
                add_variant(softened.replace("steel", "steelworks"))
                add_variant(softened.replace("steel", "industrial plant"))
            if "japan" in softened:
                add_variant(softened.replace("japan", "tokyo japan"))
                add_variant(softened.replace("japan", "kyoto japan"))
        elif mode == "interactive_model":
            add_variant(f"{query} Sketchfab")
            add_variant(f"{query} Revizto Autodesk")
        elif mode == "immersive_web":
            add_variant(f"{query} ThingLink")
            add_variant(f"{query} interactive 360 web app")
            add_variant(f"{query} WebXR")
        elif mode == "review_app":
            add_variant(f"{query} Power BI dashboard")
            add_variant(f"{query} product dashboard 3d model")
            add_variant(f"{query} Teams collaboration room")
        return variants[:4]

    def _search_youtube_api(self, query: str, require_4k: bool, limit: int) -> list[SearchResult]:
        if not self.youtube_api_key:
            return []
        search_payload = self._fetch_json(
            YOUTUBE_SEARCH_API_URL,
            {
                "key": self.youtube_api_key,
                "part": "snippet",
                "type": "video",
                "videoEmbeddable": "true",
                "maxResults": str(min(limit, 10)),
                "q": query,
            },
        )
        items = search_payload.get("items", [])
        if not isinstance(items, list) or not items:
            return []
        video_ids = [item.get("id", {}).get("videoId", "") for item in items if isinstance(item, dict)]
        video_ids = [video_id for video_id in video_ids if video_id]
        if not video_ids:
            return []
        details_payload = self._fetch_json(
            YOUTUBE_VIDEOS_API_URL,
            {
                "key": self.youtube_api_key,
                "part": "snippet,contentDetails,status",
                "id": ",".join(video_ids),
            },
        )
        details_lookup = {
            item.get("id", ""): item for item in details_payload.get("items", []) if isinstance(item, dict) and item.get("id")
        }
        results: list[SearchResult] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            video_id = item.get("id", {}).get("videoId", "")
            if not video_id:
                continue
            detail = details_lookup.get(video_id, {})
            snippet = detail.get("snippet", item.get("snippet", {}))
            if not isinstance(snippet, dict):
                snippet = {}
            title = str(snippet.get("title", "")).strip()
            description = str(snippet.get("description", "")).strip()
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = self._best_youtube_thumbnail(video_id, thumbnails if isinstance(thumbnails, dict) else {})
            url = f"https://www.youtube.com/watch?v={video_id}"
            text_blob = f"{title} {description} {url}".lower()
            if "360" not in text_blob and "vr" not in text_blob:
                continue
            match_score = self._score_result(query, title=title, snippet=description, url=url, mode="youtube_360", require_4k=require_4k)
            resolution_label = "Max thumbnail" if "maxres" in str(thumbnail_url).lower() else "High thumbnail"
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    source="youtube.com",
                    snippet=description,
                    content_type="YouTube 360",
                    readiness_status="usable with prep",
                    resolution_label=resolution_label,
                    notes=[
                        "Igloo already supports YouTube 360 as a workflow class when the hosted content behaves as expected.",
                        "Check the exact video resolution, playback behavior, and whether the content is suitable for the room.",
                    ],
                    thumbnail_url=thumbnail_url,
                    provider="YouTube Data API",
                    match_score=match_score,
                    preview_caption="Suggested immersive source",
                    asset_location=url,
                    recommended_layer_type="WebView",
                )
            )
        return results

    def _search_duckduckgo(self, query: str, mode: str, require_4k: bool, limit: int) -> list[SearchResult]:
        url = f"{DDG_HTML_URL}?{urlencode({'q': query})}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html_text = urlopen(request, timeout=self.timeout_seconds).read().decode("utf-8", errors="replace")
        snippet_matches = [_strip_tags(match.group("snippet")) for match in SNIPPET_RE.finditer(html_text)]
        results: list[SearchResult] = []
        for index, match in enumerate(RESULT_LINK_RE.finditer(html_text)):
            title = _strip_tags(match.group("title"))
            url_value = _decode_ddg_url(match.group("href"))
            snippet = snippet_matches[index] if index < len(snippet_matches) else ""
            if not title or not url_value:
                continue
            parsed = urlparse(url_value)
            if mode == "youtube_360" and not any(domain in parsed.netloc for domain in ("youtube.com", "youtu.be")):
                continue
            if mode in {"website", "immersive_web", "interactive_model", "review_app"} and any(domain in parsed.netloc for domain in ("youtube.com", "youtu.be")):
                continue
            text_blob = f"{title} {snippet} {url_value}".lower()
            if mode == "youtube_360" and "360" not in text_blob and "vr" not in text_blob:
                continue
            if mode == "interactive_model" and not self._looks_like_interactive_model(parsed.netloc.lower(), text_blob):
                continue
            if mode == "immersive_web" and not self._looks_like_immersive_web(parsed.netloc.lower(), text_blob):
                continue
            if mode == "review_app" and not self._looks_like_review_app(parsed.netloc.lower(), text_blob):
                continue
            thumbnail_url = ""
            provider = parsed.netloc.replace("www.", "")
            preview_caption = ""
            if any(domain in parsed.netloc for domain in ("youtube.com", "youtu.be")):
                video_id = self._extract_youtube_id(url_value)
                if video_id:
                    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    preview_caption = "Suggested immersive source"
            elif mode not in {"webxr"}:
                metadata = self._fetch_site_metadata(url_value)
                thumbnail_url = metadata.get("thumbnail_url", "")
                preview_caption = metadata.get("preview_caption", "")
            match_score = self._score_result(query, title=title, snippet=snippet, url=url_value, mode=mode, require_4k=require_4k)
            readiness_status = "needs checking"
            resolution_label = "Unknown"
            notes = ["Exact item compatibility still needs checking."]
            content_type = "website"
            if mode == "youtube_360":
                content_type = "YouTube 360"
                readiness_status = "usable with prep"
                resolution_label = "4K+ indicated" if any(term in text_blob for term in RESOLUTION_TERMS) else "Unknown"
                notes = [
                    "Igloo already supports YouTube 360 as a workflow class when the hosted content behaves as expected.",
                    "Confirm that the exact video is actually 4K+ and suitable for in-room playback.",
                ]
            elif mode == "interactive_model":
                content_type = "Interactive model"
                readiness_status = "usable with prep"
                resolution_label = "Viewer-dependent"
                notes = [
                    "This looks like a model-viewer route rather than a plain document website.",
                    "Check the exact model size, viewer controls, and whether the interaction is smooth enough in-room.",
                ]
            elif mode == "immersive_web":
                content_type = "Interactive web experience"
                readiness_status = "needs checking"
                resolution_label = "Web app"
                notes = [
                    "This looks closer to the interactive web route you would actually demo, not a generic brochure site.",
                    "Check the exact interaction quality, load behavior, and whether the experience is stable enough for the chosen room flow.",
                ]
            elif mode == "review_app":
                content_type = "Review app"
                readiness_status = "needs checking"
                resolution_label = "Live app"
                notes = [
                    "This looks like a strategic review or dashboard app route rather than a generic website.",
                    "Check login, reachability, refresh behavior, and whether the wall layout matches the intended meeting flow.",
                ]
            elif mode == "webxr":
                content_type = "WebXR experience"
                readiness_status = "high risk"
                resolution_label = "App-dependent"
                notes = [
                    "This is a discovery result for a WebXR-style experience.",
                    "Treat the underlying workflow as app/integration-risk rather than a straightforward media workflow.",
                ]
            elif any(hint in parsed.netloc.lower() for hint in TRUSTED_EDU_HINTS):
                notes = [
                    "This looks like a stronger contextual or educational source for a client-facing demo.",
                    "You still need to check that the exact page behaves correctly in the chosen WebView route.",
                ]
            results.append(
                SearchResult(
                    title=title,
                    url=url_value,
                    source=provider,
                    snippet=snippet,
                    content_type=content_type,
                    readiness_status=readiness_status,
                    resolution_label=resolution_label,
                    notes=notes,
                    thumbnail_url=thumbnail_url,
                    provider="DuckDuckGo web search",
                    match_score=match_score,
                    preview_caption=preview_caption,
                    asset_location=url_value,
                    recommended_layer_type="ModelViewer" if content_type == "Interactive model" else ("WebView" if content_type in {"website", "Interactive web experience", "Review app"} else ""),
                )
            )
            if len(results) >= limit * 2:
                break
        return results[:limit]

    def _search_nasa(self, query: str, limit: int) -> list[SearchResult]:
        payload = self._fetch_json(NASA_SEARCH_API_URL, {"q": query, "media_type": "video"})
        collection = payload.get("collection", {})
        items = collection.get("items", []) if isinstance(collection, dict) else []
        results: list[SearchResult] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            data_list = item.get("data", [])
            links = item.get("links", [])
            if not isinstance(data_list, list) or not data_list:
                continue
            data = data_list[0] if isinstance(data_list[0], dict) else {}
            title = str(data.get("title", "")).strip()
            description = str(data.get("description", "")).strip()
            nasa_url = ""
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, dict) and link.get("href"):
                        nasa_url = str(link["href"])
                        break
            if not title or not nasa_url:
                continue
            match_score = self._score_result(query, title=title, snippet=description, url=nasa_url, mode="website", require_4k=False) + 8
            results.append(
                SearchResult(
                    title=title,
                    url=nasa_url,
                    source="nasa.gov",
                    snippet=description,
                    content_type="website",
                    readiness_status="needs checking",
                    resolution_label="NASA media",
                    notes=[
                        "NASA is a strong source for immersive education content, but exact playback suitability still needs checking.",
                        "If this is a video reference rather than a direct room-ready file, confirm how it will be launched in the session.",
                    ],
                    thumbnail_url=nasa_url,
                    provider="NASA Images API",
                    match_score=match_score,
                    preview_caption="Official content source",
                    asset_location=nasa_url,
                    recommended_layer_type="WebView",
                )
            )
        return results

    def _fetch_json(self, base_url: str, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{base_url}?{urlencode(params)}",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        content = urlopen(request, timeout=self.timeout_seconds).read().decode("utf-8", errors="replace")
        payload = json.loads(content)
        if not isinstance(payload, dict):
            return {}
        return payload

    def _fetch_site_metadata(self, url: str) -> dict[str, str]:
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            html_text = urlopen(request, timeout=self.metadata_timeout_seconds).read(65536).decode("utf-8", errors="replace")
        except Exception:
            return {"thumbnail_url": "", "preview_caption": ""}
        metadata: dict[str, str] = {}
        for match in META_TAG_RE.finditer(html_text):
            name = str(match.group("name")).strip().lower()
            content = html.unescape(str(match.group("content")).strip())
            metadata[name] = content
        og_image = metadata.get("og:image") or metadata.get("twitter:image") or ""
        if og_image:
            og_image = urljoin(url, og_image)
        title_match = TITLE_RE.search(html_text)
        title = _strip_tags(title_match.group("title")) if title_match else ""
        description = metadata.get("og:description") or metadata.get("description") or ""
        preview_caption_parts = [part for part in (title, description) if part]
        return {
            "thumbnail_url": og_image,
            "preview_caption": " | ".join(preview_caption_parts[:2]),
        }

    def _best_youtube_thumbnail(self, video_id: str, thumbnails: dict[str, Any]) -> str:
        for key in ("maxres", "standard", "high", "medium", "default"):
            value = thumbnails.get(key, {})
            if isinstance(value, dict) and value.get("url"):
                return str(value["url"])
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    def _extract_youtube_id(self, url: str) -> str:
        parsed = urlparse(url)
        if "youtu.be" in parsed.netloc:
            return parsed.path.strip("/")
        if "youtube.com" in parsed.netloc:
            return parse_qs(parsed.query).get("v", [""])[0]
        return ""

    def _score_result(self, query: str, title: str, snippet: str, url: str, mode: str, require_4k: bool) -> int:
        tokens = [token for token in re.findall(r"[a-z0-9][a-z0-9\-]+", query.lower()) if token not in STOPWORDS]
        anchor_tokens = [token for token in tokens if token not in GENERIC_QUERY_TOKENS]
        text_blob = f"{title} {snippet} {url}".lower()
        score = 0
        score += sum(12 for token in tokens if token in text_blob)
        anchor_matches = sum(1 for token in anchor_tokens if token in text_blob)
        if anchor_tokens:
            if anchor_matches == 0:
                score -= min(42, 16 + (len(anchor_tokens) - 1) * 10)
            else:
                score += anchor_matches * 10
        if query.lower() in text_blob:
            score += 18
        if mode == "youtube_360":
            if "360" in text_blob or "vr" in text_blob:
                score += 24
            if any(term in text_blob for term in RESOLUTION_TERMS):
                score += 18
            if "youtube.com" in url or "youtu.be" in url:
                score += 10
            if any(term in text_blob for term in ("heritage", "historic", "museum", "castle", "unesco", "tour", "site")):
                score += 8
        if mode == "webxr":
            if "webxr" in text_blob:
                score += 24
            if "unity" in text_blob or "unreal" in text_blob:
                score += 6
        if mode == "interactive_model":
            parsed = urlparse(url)
            if any(domain in parsed.netloc.lower() for domain in INTERACTIVE_MODEL_DOMAINS):
                score += 28
            if any(term in text_blob for term in ("3d", "model", "viewer", "bim", "revizto", "sketchfab", "autodesk")):
                score += 24
        if mode == "immersive_web":
            parsed = urlparse(url)
            if any(domain in parsed.netloc.lower() for domain in IMMERSIVE_WEB_DOMAINS):
                score += 26
            if any(term in text_blob for term in ("interactive", "360", "virtual tour", "explore", "immersive", "thinglink", "webxr")):
                score += 22
        if mode == "review_app":
            parsed = urlparse(url)
            if any(domain in parsed.netloc.lower() for domain in REVIEW_APP_DOMAINS):
                score += 26
            if any(term in text_blob for term in ("dashboard", "power bi", "powerbi", "tableau", "grafana", "kpi", "model review", "teams")):
                score += 22
        if mode == "website":
            parsed = urlparse(url)
            if any(hint in parsed.netloc.lower() for hint in TRUSTED_EDU_HINTS):
                score += 12
        if any(token in text_blob for token in GENERIC_HOST_PENALTIES):
            score -= 10
        if require_4k and mode == "youtube_360" and not any(term in text_blob for term in RESOLUTION_TERMS):
            score -= 6
        return max(0, score)

    def _looks_like_interactive_model(self, netloc: str, text_blob: str) -> bool:
        return any(domain in netloc for domain in INTERACTIVE_MODEL_DOMAINS) or any(
            term in text_blob for term in ("3d model", "3d viewer", "sketchfab", "revizto", "bim", "autodesk", "viewer")
        )

    def _looks_like_immersive_web(self, netloc: str, text_blob: str) -> bool:
        return any(domain in netloc for domain in IMMERSIVE_WEB_DOMAINS) or any(
            term in text_blob for term in ("interactive 360", "virtual tour", "thinglink", "immersive", "webxr", "360 tour", "interactive")
        )

    def _looks_like_review_app(self, netloc: str, text_blob: str) -> bool:
        return any(domain in netloc for domain in REVIEW_APP_DOMAINS) or any(
            term in text_blob for term in ("dashboard", "power bi", "powerbi", "tableau", "grafana", "kpi", "teams", "sales review")
        )
