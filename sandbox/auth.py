from __future__ import annotations

from igloo_experience_builder.sandbox.client import IglooSandboxClient, SandboxMessageResult


def authenticate(client: IglooSandboxClient, api_key: str | None) -> SandboxMessageResult:
    if not api_key:
        return SandboxMessageResult(False, "", "No sandbox API key configured.")
    return client.send_message(f"apikey?value={api_key}")
