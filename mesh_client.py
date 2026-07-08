"""
mesh_client.py — the ONLY place in this project that talks to AI.

Every single AI call in ModelSabha routes through the Mesh API
(https://api.meshapi.ai). This matters for the hackathon rule:
"Every AI call in your project must visibly route through the Mesh API."

Mesh exposes an OpenAI-compatible endpoint:
    POST https://api.meshapi.ai/v1/chat/completions
    Authorization: Bearer rsk_...

Docs: https://developers.meshapi.ai/docs/guides/quickstart
"""

import os
import asyncio
import httpx

# Base URL is configurable so we can point at a mock server in tests.
MESH_BASE_URL = os.getenv("MESH_BASE_URL", "https://api.meshapi.ai/v1")
MESH_API_KEY = os.getenv("MESH_API_KEY", "")

# One shared async client = connection reuse = faster parallel calls.
_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))


class MeshError(Exception):
    """A friendly error we can show in the UI instead of a raw traceback."""

    def __init__(self, message: str, status: int = 500):
        super().__init__(message)
        self.message = message
        self.status = status


def _friendly_error(status_code: int, body: str) -> MeshError:
    """Translate raw HTTP failures from Mesh into human-readable messages."""
    if status_code == 401:
        return MeshError("Mesh API key was rejected. Check MESH_API_KEY in your .env file.", 401)
    if status_code == 402:
        return MeshError("Your Mesh balance is empty. Add credits in the Mesh dashboard (Billing).", 402)
    if status_code == 404:
        return MeshError("Model not found on Mesh. Pick another model from the dropdown.", 404)
    if status_code == 429:
        return MeshError("Rate limited by Mesh. Wait a few seconds and try again.", 429)
    return MeshError(f"Mesh API error ({status_code}): {body[:200]}", status_code)


async def chat(model: str, messages: list[dict], temperature: float = 0.7,
               max_tokens: int = 700) -> str:
    """
    Send one chat completion request through Mesh and return the reply text.

    `model` uses Mesh's provider/model format, e.g. "openai/gpt-4o-mini".
    """
    if not MESH_API_KEY:
        raise MeshError("MESH_API_KEY is not set. Copy .env.example to .env and add your rsk_ key.", 401)

    try:
        response = await _client.post(
            f"{MESH_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {MESH_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
    except httpx.TimeoutException:
        raise MeshError(f"{model} took too long to answer. Try again or pick a faster model.", 504)
    except httpx.HTTPError as exc:
        raise MeshError(f"Could not reach the Mesh API: {exc}", 502)

    if response.status_code != 200:
        raise _friendly_error(response.status_code, response.text)

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise MeshError("Mesh returned an unexpected response shape.", 502)


async def chat_many(jobs: list[dict]) -> list[dict]:
    """
    Run several chat() calls IN PARALLEL — this is the heart of ModelSabha.

    Each job: {"model": str, "messages": list}.
    Returns one result per job: {"model", "ok", "content" | "error"}.
    A single failing model never crashes the whole debate.
    """
    async def run(job: dict) -> dict:
        try:
            content = await chat(job["model"], job["messages"],
                                 temperature=job.get("temperature", 0.7),
                                 max_tokens=job.get("max_tokens", 700))
            return {"model": job["model"], "ok": True, "content": content}
        except MeshError as err:
            return {"model": job["model"], "ok": False, "error": err.message}

    return list(await asyncio.gather(*(run(job) for job in jobs)))


async def list_models() -> list[str]:
    """Ask Mesh which models this key can use (GET /v1/models)."""
    response = await _client.get(
        f"{MESH_BASE_URL}/models",
        headers={"Authorization": f"Bearer {MESH_API_KEY}"},
    )
    if response.status_code != 200:
        raise _friendly_error(response.status_code, response.text)
    data = response.json()
    # Mesh may return {"data": [...]} (OpenAI style) or a plain list.
    items = data.get("data", []) if isinstance(data, dict) else data
    models = []
    for item in items:
        if isinstance(item, dict) and "id" in item:
            models.append(item["id"])
        elif isinstance(item, str):
            models.append(item)
    return models
