from typing import Any
from pydantic import BaseModel, Field
from .shared import BaseDocument, new_id


# ── Item Template ──────────────────────────────────────────────────────────────
# A Template is a definition — the "blueprint" for a category of item.
# The engine never interprets tags or property keys; those are World Bible vocabulary.

class ItemTemplateCreate(BaseModel):
    """Payload for POST /item-templates."""
    adventure_id: str
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ItemTemplate(BaseDocument):
    """Full Item Template document as stored in Firestore."""
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Item Instance ──────────────────────────────────────────────────────────────
# An Instance is one specific copy of a Template that exists in the world right now.
# overrides contains only the properties that differ from the Template.

class ItemInstanceCreate(BaseModel):
    """Payload for POST /item-instances."""
    adventure_id: str
    template_id: str
    owner_id: str | None = None
    overrides: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class ItemInstance(BaseDocument):
    """Full Item Instance document as stored in Firestore."""
    template_id: str
    owner_id: str | None = None
    overrides: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class ItemInstanceUpdate(BaseModel):
    """Payload for PATCH /item-instances/{id}. All fields optional."""
    owner_id: str | None = None
    overrides: dict[str, float] | None = None
    notes: str | None = None


# ── Resolved Instance ──────────────────────────────────────────────────────────
# What GET /item-instances/{id} returns: the instance merged with its template.
# properties here is the final merged dict — template defaults + instance overrides applied.

class ResolvedItemInstance(BaseModel):
    id: str
    adventure_id: str
    template_id: str
    owner_id: str | None
    notes: str
    name: str
    description: str
    tags: list[str]
    properties: dict[str, float]   # merged: template base + instance overrides
    metadata: dict[str, Any]


# ── Merge Helper ───────────────────────────────────────────────────────────────
# Kept here (not in a router) so any module can import it without cross-router coupling.

def merge_with_template(instance: "ItemInstance", template: "ItemTemplate") -> ResolvedItemInstance:
    """Combine a template's base data with an instance's overrides into a ResolvedItemInstance."""
    return ResolvedItemInstance(
        id=instance.id,
        adventure_id=instance.adventure_id,
        template_id=template.id,
        owner_id=instance.owner_id,
        notes=instance.notes,
        name=template.name,
        description=template.description,
        tags=template.tags,
        properties={**template.properties, **instance.overrides},
        metadata=template.metadata,
    )
