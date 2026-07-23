from typing import Any
from pydantic import BaseModel, Field
from .combat import AIProfile
from .blueprint import Instance, CustomField, AttachedRef, STAT_KEYS, get_field, merge_fields, default_fields_for_kind

# Character is no longer its own stored document shape -- a character is a
# kind="character" Instance (backend/models/blueprint.py). This file now holds only
# the stable API-facing contract (what /characters returns/accepts) plus the
# translation helpers that turn an Instance into that shape and back. A character's
# `fields` are always fully self-sufficient at creation time (every required field
# gets a real value, not just inherited from a template) -- so reading a character
# back never needs a template lookup, keeping every character read a single document
# fetch, same as before this migration.


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


# ── Character (API contract) ────────────────────────────────────────────────────
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
    race_template_id: str | None = None    # chosen from a kind="race" Template; a fresh
    class_template_id: str | None = None   # kind="race"/"class" Instance is created and
                                            # attached automatically (see create_character)
    custom_fields: list[CustomField] = Field(default_factory=list)   # values for a DM-authored
                                            # kind="character" Template's non-canonical fields --
                                            # snapshotted in, not linked (see character_fields_for_create)
    starting_inventory_ids: list[str] = Field(default_factory=list)      # unowned Instance ids to claim
    starting_equipped_wearable_ids: list[str] = Field(default_factory=list)  # subset of the above, worn


class Character(BaseModel):
    """The stable shape /characters endpoints return -- translated from a
    kind="character" Instance, not a literal stored document anymore."""
    id: str
    adventure_id: str
    name: str
    is_player: bool = False
    stats: Stats = Field(default_factory=Stats)
    hp: int
    max_hp: int
    equipped_weapon_id: str | None = None
    equipped_wearable_ids: list[str] = Field(default_factory=list)   # subset of inventory_ids
    inventory_ids: list[str] = Field(default_factory=list)
    description: str = ""
    tone: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    ai_profile: AIProfile | None = None   # None for players; drives combat AI for NPCs
    race_instance_id: str | None = None    # a kind="race"/"class" Instance id -- resolve
    class_instance_id: str | None = None   # via GET /instances/{id} to display its name


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


# ── Translation: Character API contract <-> kind="character" Instance ──────────

def character_fields_for_create(payload: CharacterCreate, hp: int, max_hp: int) -> list[CustomField]:
    """Build the complete field list for a new character Instance -- self-sufficient
    (every required field gets a real value here), so no template lookup is ever
    needed to read it back. A DM-authored kind="character" Template is never linked
    (no template_id on the resulting Instance) -- payload.custom_fields snapshots in
    whatever values the creator entered for it, sitting between the engine's canonical
    defaults and this call's own fields so the canonical ones can never be clobbered
    by a same-keyed custom field.
    """
    own_fields = [
        CustomField(key="name", label="Name", field_type="string", value=payload.name, required=True),
        CustomField(key="description", label="Description", field_type="string", value=payload.description),
        CustomField(key="tone", label="Speaking Tone", field_type="string", value=payload.tone),
        CustomField(key="is_player", label="Is Player", field_type="boolean", value=payload.is_player, bound_behavior="is_player"),
        CustomField(key="hp", label="HP", field_type="number", value=hp, required=True, bound_behavior="hp"),
        CustomField(key="max_hp", label="Max HP", field_type="number", value=max_hp, required=True, bound_behavior="max_hp"),
    ] + [
        CustomField(key=k, label=k.title(), field_type="number", value=getattr(payload.stats, k),
                    required=True, bound_behavior="stat")
        for k in STAT_KEYS
    ]
    with_custom = merge_fields(default_fields_for_kind("character"), payload.custom_fields)
    return merge_fields(with_custom, own_fields)


def character_from_instance(instance: Instance) -> Character:
    """Translate a kind="character" Instance into the stable Character API shape."""
    fields = instance.fields
    stats = Stats(**{k: int(get_field(fields, k, 10)) for k in STAT_KEYS})
    race_ref = next((a for a in instance.attached if a.ref_kind == "race"), None)
    class_ref = next((a for a in instance.attached if a.ref_kind == "class"), None)
    return Character(
        id=instance.id,
        adventure_id=instance.adventure_id,
        name=get_field(fields, "name", "Unknown") or "Unknown",
        is_player=bool(get_field(fields, "is_player", False)),
        stats=stats,
        hp=int(get_field(fields, "hp", 10)),
        max_hp=int(get_field(fields, "max_hp", 10)),
        equipped_weapon_id=instance.equipped_weapon_id,
        equipped_wearable_ids=instance.equipped_wearable_ids,
        inventory_ids=instance.inventory_ids,
        description=get_field(fields, "description", "") or "",
        tone=get_field(fields, "tone", "") or "",
        metadata=instance.metadata,
        ai_profile=instance.ai_profile,
        race_instance_id=race_ref.ref_id if race_ref else None,
        class_instance_id=class_ref.ref_id if class_ref else None,
    )


def attach_race_and_class(payload: "CharacterCreate", db) -> list[AttachedRef]:
    """If the payload chose a race/class Template, create a fresh (near-identical,
    per-character) Instance of it and attach that Instance's id -- permanent
    (expires_at_round=None), same mechanism active status effects use temporarily.
    """
    attached: list[AttachedRef] = []
    for template_id, ref_kind in ((payload.race_template_id, "race"), (payload.class_template_id, "class")):
        if not template_id:
            continue
        tmpl_doc = db.collection("templates").document(template_id).get()
        if not tmpl_doc.exists:
            continue
        trait_instance = Instance(adventure_id=payload.adventure_id, kind=ref_kind, template_id=template_id)
        db.collection("instances").document(trait_instance.id).set(trait_instance.model_dump())
        attached.append(AttachedRef(ref_id=trait_instance.id, ref_kind=ref_kind, expires_at_round=None))
    return attached


def character_field_from_doc(doc_dict: dict, key: str, default: Any = None) -> Any:
    """Extract one field's value from a raw kind="character" Instance Firestore dict --
    cheaper than a full character_from_instance() round-trip for hot paths that only
    need one value (round-status polling, narration prompt name lookups, filtering by
    is_player in Python since it's no longer a top-level document field to query on).
    """
    for f in doc_dict.get("fields", []) or []:
        if f.get("key") == key:
            value = f.get("value")
            return value if value is not None else default
    return default


def character_name_from_doc(doc_dict: dict, default: str = "Unknown") -> str:
    return character_field_from_doc(doc_dict, "name", default)


def write_character_field(character_id: str, field: CustomField, db) -> None:
    """Read-modify-write a single field on a character Instance's `fields` list --
    needed because Firestore can't patch one array element by key in place. Used for
    combat's HP write-back after a fight ends.
    """
    ref = db.collection("instances").document(character_id)
    doc = ref.get()
    if not doc.exists:
        return
    instance = Instance(**(doc.to_dict() | {"id": doc.id}))
    merged = merge_fields(instance.fields, [field])
    ref.update({"fields": [f.model_dump() for f in merged]})
