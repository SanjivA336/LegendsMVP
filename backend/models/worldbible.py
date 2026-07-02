from pydantic import BaseModel, Field
from .shared import BaseDocument

DEFAULT_ATTRIBUTE_NAMES: dict[str, str] = {
    "strength": "Strength",
    "dexterity": "Dexterity",
    "intelligence": "Intelligence",
    "fortitude": "Fortitude",
    "charisma": "Charisma",
    "reflex": "Reflex",
}


class WorldBibleCreate(BaseModel):
    adventure_id: str
    attribute_names: dict[str, str] = Field(
        default_factory=lambda: dict(DEFAULT_ATTRIBUTE_NAMES)
    )
    currency_name: str = "Gold"
    biome_name_overrides: dict[str, str] = Field(default_factory=dict)  # "biome_id" → display name


class WorldBible(BaseDocument):
    attribute_names: dict[str, str] = Field(
        default_factory=lambda: dict(DEFAULT_ATTRIBUTE_NAMES)
    )
    currency_name: str = "Gold"
    biome_name_overrides: dict[str, str] = Field(default_factory=dict)
