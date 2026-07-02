import os
import re
import json
import logging
from abc import ABC, abstractmethod
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> dict:
    """
    Best-effort JSON extraction from LLM output that may include markdown fences,
    preamble text, or minor syntax errors (trailing commas).
    """
    text = raw.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    # Extract outermost {...} block (model may prefix with prose)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    # Try as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip trailing commas before } or ] (another common LLM mistake)
    cleaned = re.sub(r",(\s*[}\]])", r"\1", text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error(
            "ai_provider: JSON parse failed after cleanup. raw snippet: %r",
            raw[:500],
        )
        raise ValueError(f"AI returned unparseable JSON: {exc}") from exc


class AIProvider(ABC):
    """
    All DM calls go through this interface. To swap providers (e.g. Ollama → Claude),
    add a new subclass and update get_provider() — callers never change.

    Every provider must return a dict matching the DM output contract:
    { "narrative": str, "updates": { "world_state_additions": [...], "relationship_changes": {...}, "quest_step_complete": bool } }
    """

    @abstractmethod
    async def generate(self, prompt: str) -> dict:
        """Send a prompt to the AI and return the parsed DM response dict."""
        ...


class OllamaProvider(AIProvider):

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def generate(self, prompt: str) -> dict:
        # POST to Ollama's generate endpoint and request JSON-mode output
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()

        # Ollama wraps the model output in a "response" field
        raw = response.json().get("response", "{}")
        return _extract_json(raw)


def get_provider() -> AIProvider:
    """Factory that reads .env and returns the configured AI provider."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama2")
    return OllamaProvider(base_url=base_url, model=model)
