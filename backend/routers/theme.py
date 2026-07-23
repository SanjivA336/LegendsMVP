from pydantic import BaseModel, ValidationError
from fastapi import APIRouter, HTTPException
from ..ai_provider import get_provider
from ..utils.theme_prompts import build_theme_expand_prompt

router = APIRouter()


class ThemeExpandRequest(BaseModel):
    pitch: str


class ThemeExpandResponse(BaseModel):
    world_name: str
    attribute_names: dict[str, str]
    currency_name: str
    biome_family_names: dict[str, str]


@router.post("/theme/expand", response_model=ThemeExpandResponse)
async def expand_theme(payload: ThemeExpandRequest):
    """Read-only, non-persisting -- lets the wizard's custom-theme path pre-fill Basic
    Info / World Bible with AI-suggested naming, exactly like map preview pre-fills
    WorldGen. Nothing here is saved; the wizard just holds the returned bundle in
    local draft state until Launch."""
    provider = get_provider()
    prompt = build_theme_expand_prompt(payload.pitch)
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(502, f"AI provider error during theme expansion: {exc}") from exc
    try:
        return ThemeExpandResponse(**result)
    except ValidationError as exc:
        raise HTTPException(500, f"DM did not return a valid theme bundle: {exc}") from exc
