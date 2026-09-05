"""Provider interface + a deterministic mock.

The real FreeLLMAPI adapter implements the same `LLMProvider.complete` surface and
is injected by configuration. Application code never imports a provider directly —
only the gateway does. The mock lets the whole gateway (routing, validation, audit,
fallback, degraded mode) run and be tested without network access or keys.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol


class ProviderError(Exception):
    """Retry-eligible provider failure (5xx, connection)."""


class ProviderTimeout(ProviderError):
    """Retry-eligible timeout."""


class LLMProvider(Protocol):
    async def complete(self, *, route: str, system: str, user: str, params: dict) -> str: ...


Responder = Callable[[dict], str]


class MockProvider:
    """Deterministic provider. `responder` maps a call dict to a raw JSON string.

    The call dict has keys: route, system, user, params. Raise ProviderError /
    ProviderTimeout from the responder to exercise retry/fallback/degraded paths.
    """

    def __init__(self, responder: Responder) -> None:
        self._responder = responder
        self.calls: list[dict] = []

    async def complete(self, *, route: str, system: str, user: str, params: dict) -> str:
        call = {"route": route, "system": system, "user": user, "params": params}
        self.calls.append(call)
        return self._responder(call)


class AsyncMockProvider:
    """Like MockProvider but with an async responder (for awaiting in tests)."""

    def __init__(self, responder: Callable[[dict], Awaitable[str]]) -> None:
        self._responder = responder
        self.calls: list[dict] = []

    async def complete(self, *, route: str, system: str, user: str, params: dict) -> str:
        call = {"route": route, "system": system, "user": user, "params": params}
        self.calls.append(call)
        return await self._responder(call)
