"""Real FreeLLMAPI provider adapter.

Implements the gateway's LLMProvider protocol against the FreeLLMAPI wire format
(https://github.com/tashfeenahmed/freellmapi):

  POST {base}/chat/completions
  Authorization: Bearer freellmapi-<key>
  body: {"model", "messages":[{role,content}], "stream", "temperature",
         "response_format":"json_object"}
  -> {"choices":[{"message":{"content"}, "finish_reason"}], "usage":{...}}
  response header: X-Routed-Via: <platform>/<model>

Only fields documented by FreeLLMAPI are sent — nothing is invented. The gateway
remains the ONLY caller; agents never touch this class.
"""

from __future__ import annotations

import httpx

from .providers import ProviderError, ProviderTimeout


class FreeLLMProvider:
    """route (logical tier) -> FreeLLMAPI model id via `model_map`; unknown routes pass through."""

    def __init__(self, base_url: str, api_key: str, model_map: dict[str, str], *,
                 timeout: float = 30.0, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_map = model_map
        self.timeout = timeout
        self._client = client
        self.last_routed_via: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def complete(self, *, route: str, system: str, user: str, params: dict) -> str:
        model = self.model_map.get(route, route)
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
            "temperature": float(params.get("temperature", 0.0)),
            "response_format": "json_object",     # documented string form
        }
        url = f"{self.base_url}/chat/completions"
        timeout = params.get("timeout", self.timeout)

        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=timeout)
        try:
            resp = await client.post(url, json=body, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc
        finally:
            if owns:
                await client.aclose()

        self.last_routed_via = resp.headers.get("X-Routed-Via")
        if resp.status_code >= 500:
            raise ProviderError(f"freellm {resp.status_code}")
        if resp.status_code >= 400:
            raise ProviderError(f"freellm {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"unexpected FreeLLMAPI response: {exc}") from exc


async def health_check(base_url: str, api_key: str, *, timeout: float = 5.0,
                       client: httpx.AsyncClient | None = None) -> bool:
    """GET {base}/models — True if the local FreeLLMAPI server answers 200."""
    url = f"{base_url.rstrip('/')}/models"
    owns = client is None
    client = client or httpx.AsyncClient(timeout=timeout)
    try:
        resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        return resp.status_code == 200
    except httpx.HTTPError:
        return False
    finally:
        if owns:
            await client.aclose()
