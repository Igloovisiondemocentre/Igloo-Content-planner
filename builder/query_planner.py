from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from igloo_experience_builder.builder.draft_builder import PhaseTwoDraftBuilder
from igloo_experience_builder.config.settings import Settings


@dataclass(slots=True)
class QueryPlan:
    query: str
    destination: str
    subject: str
    mode: str
    confidence: str
    planner: str
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "destination": self.destination,
            "subject": self.subject,
            "mode": self.mode,
            "confidence": self.confidence,
            "planner": self.planner,
            "notes": self.notes,
        }


class QueryPlannerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.builder = PhaseTwoDraftBuilder()

    def plan(
        self,
        brief: str,
        mode: str,
        *,
        target_title: str = "",
        target_content_type: str = "",
        existing_query: str = "",
        require_4k: bool = False,
    ) -> QueryPlan:
        if self.settings.openai_api_key:
            try:
                plan = self._plan_with_openai(
                    brief=brief,
                    mode=mode,
                    target_title=target_title,
                    target_content_type=target_content_type,
                    existing_query=existing_query,
                    require_4k=require_4k,
                )
                if plan.query.strip():
                    return plan
            except Exception as exc:
                fallback = self._fallback_plan(
                    brief=brief,
                    mode=mode,
                    target_title=target_title,
                    target_content_type=target_content_type,
                    existing_query=existing_query,
                    require_4k=require_4k,
                )
                fallback.notes.append(f"OpenAI planner fallback used after API error: {exc}")
                return fallback
        return self._fallback_plan(
            brief=brief,
            mode=mode,
            target_title=target_title,
            target_content_type=target_content_type,
            existing_query=existing_query,
            require_4k=require_4k,
        )

    def _fallback_plan(
        self,
        *,
        brief: str,
        mode: str,
        target_title: str,
        target_content_type: str,
        existing_query: str,
        require_4k: bool,
    ) -> QueryPlan:
        content_type = target_content_type or self._content_type_for_mode(mode)
        source_text = brief or existing_query or target_title
        query = self.builder._focused_query(source_text, content_type, title=target_title)
        destination = self.builder._topic_focus(brief or existing_query or target_title, fallback="")
        if require_4k and "4k" not in query.lower():
            query = f"{query} 4K".strip()
        notes = [
            "Deterministic planner used.",
            "This planner uses the full brief and the current target slot, not just the visible search box text.",
        ]
        if destination:
            notes.append(f"Detected destination or anchor: {destination}.")
        return QueryPlan(
            query=query,
            destination=destination,
            subject=target_title or content_type or "content",
            mode=mode,
            confidence="medium",
            planner="deterministic",
            notes=notes,
        )

    def _plan_with_openai(
        self,
        *,
        brief: str,
        mode: str,
        target_title: str,
        target_content_type: str,
        existing_query: str,
        require_4k: bool,
    ) -> QueryPlan:
        schema = {
            "name": "igloo_search_query_plan",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "query": {"type": "string"},
                    "destination": {"type": "string"},
                    "subject": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                    "notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query", "destination", "subject", "confidence", "notes"],
            },
        }
        payload = {
            "model": self.settings.openai_query_planner_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You turn natural-language creative briefs into concise provider-ready search queries for the "
                        "Igloo Experience Builder. Prioritise the actual place, subject, or entity mentioned by the user. "
                        "Do not reuse a previous city or generic filler words. Preserve unusual or fictional locations if "
                        "the user clearly names them, such as Area 51 or Hogwarts. If the target is immersive travel or "
                        "classroom trip content and the mode is YouTube 360, prefer a query like 'berlin YouTube 360 4K'."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "brief": brief,
                            "mode": mode,
                            "target_title": target_title,
                            "target_content_type": target_content_type,
                            "existing_query": existing_query,
                            "require_4k": require_4k,
                        }
                    ),
                },
            ],
            "response_format": {"type": "json_schema", "json_schema": schema},
        }
        request = Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.openai_api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.request_timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise RuntimeError(f"OpenAI query planner HTTP error: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"OpenAI query planner connection error: {exc}") from exc
        content = raw["choices"][0]["message"]["content"]
        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(str(part.get("text", "")))
            content = "".join(text_parts)
        parsed: dict[str, Any] = json.loads(content)
        query = self._normalize_query_text(str(parsed.get("query", "")).strip())
        if require_4k and "4k" not in query.lower():
            query = f"{query} 4K".strip()
        return QueryPlan(
            query=query,
            destination=self._normalize_query_text(str(parsed.get("destination", "")).strip()),
            subject=str(parsed.get("subject", target_title or target_content_type or "content")).strip(),
            mode=mode,
            confidence=str(parsed.get("confidence", "medium")),
            planner="openai",
            notes=[str(note) for note in parsed.get("notes", []) if str(note).strip()],
        )

    @staticmethod
    def _content_type_for_mode(mode: str) -> str:
        normalized = mode.strip().lower()
        mapping = {
            "youtube_360": "360 video",
            "website": "website",
            "immersive_web": "interactive web",
            "webxr": "interactive web",
            "interactive_model": "3d model",
            "review_app": "dashboard app",
        }
        return mapping.get(normalized, "website")

    @staticmethod
    def _normalize_query_text(value: str) -> str:
        cleaned = " ".join(value.split()).strip()
        lowered = cleaned.lower()
        lowered = lowered.replace("youtube", "YouTube")
        lowered = lowered.replace(" 4k", " 4K")
        return lowered
