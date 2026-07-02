from typing import Any
from pydantic import BaseModel, Field
from .shared import BaseDocument
from .combat import AIProfile


# ── Stats ──────────────────────────────────────────────────────────────────────
# Six integer stats used for all mechanical calculations. Names are labels only —
# the World Bible defines what they mean in a given world (e.g. "Fortitude" → "Hull Integrity").

class Stats(BaseModel):
    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    fortitude: int = 10
    charisma: int = 10
    reflex: int = 10


# ── Character ──────────────────────────────────────────────────────────────────
# Player characters and NPCs share this schema; is_player is the only distinction.
# inventory_ids holds Item Instance IDs — no item data is embedded here.

class CharacterCreate(BaseModel):
    """Payload for POST /characters."""
    adventure_id: str
    name: str
    is_player: bool = False
    stats: Stats = Field(default_factory=Stats)
    hp: int | None = None       # defaults to max_hp if omitted
    max_hp: int | None = None   # defaults to 10 + fortitude if omitted
    equipped_weapon_id: str | None = None
    inventory_ids: list[str] = Field(default_factory=list)
    description: str = ""
    tone: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    ai_profile: AIProfile | None = None   # None for player characters


class Character(BaseDocument):
    """Full Character document as stored in Firestore."""
    name: str
    is_player: bool = False
    stats: Stats = Field(default_factory=Stats)
    hp: int
    max_hp: int
    equipped_weapon_id: str | None = None
    inventory_ids: list[str] = Field(default_factory=list)
    description: str = ""
    tone: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    ai_profile: AIProfile | None = None   # None for players; drives combat AI for NPCs


class CharacterUpdate(BaseModel):
    """Payload for PATCH /characters/{id}. All fields optional."""
    name: str | None = None
    is_player: bool | None = None
    stats: Stats | None = None
    hp: int | None = None
    max_hp: int | None = None
    equipped_weapon_id: str | None = None
    inventory_ids: list[str] | None = None
    description: str | None = None
    tone: str | None = None
    metadata: dict[str, Any] | None = None
    ai_profile: AIProfile | None = None


def default_max_hp(stats: Stats) -> int:
    """Compute starting max HP from stats. Base 10 + Fortitude."""
    return 10 + stats.fortitude
