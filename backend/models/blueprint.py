import re
from typing import Any, Literal
from pydantic import BaseModel, Field
from .shared import BaseDocument
from .combat import AIProfile


# ── CustomField ──────────────────────────────────────────────────────────────
# The atomic unit used everywhere a "field" appears (Template.fields, Instance.fields,
# Effect.parameters in status_effect.py). A self-describing object rather than a bare
# dict value, so metadata (hidden, dropdown options, which engine behavior it triggers)
# travels with the value instead of living in a separate lookup disconnected from the data.
#
# Named CustomField (not "Field") to avoid colliding with pydantic's own Field(...).

FieldType = Literal["string", "number", "boolean", "dice_roll"]


class CustomField(BaseModel):
    key: str
    label: str = ""
    field_type: FieldType = "string"
    value: Any = None
    is_enum: bool = False               # orthogonal to field_type -- a number field can be
                                         # enum-constrained too (e.g. die size: 4/6/8/10/12/20)
    options: list[Any] = Field(default_factory=list)   # only used when is_enum=True
    required: bool = False
    bound_behavior: str | None = None   # e.g. "stat", "weight", "defense" -- names an
                                         # engine-recognized behavior; None = pure flavor
    hidden: bool = False


def get_field(fields: list[CustomField], key: str, default: Any = None) -> Any:
    """Look up a field's value by key in a (possibly merged) field list."""
    for f in fields:
        if f.key == key:
            return f.value
    return default


# ── Kind + canonical field definitions ────────────────────────────────────────
# The engine never lets a DM invent a new Kind (pydantic's Literal enforces this at
# the type level), and each kind's required/bound_behavior fields are engine-defined
# constants, not authored by DMs.

Kind = Literal["character", "race", "class", "weapon", "consumable", "wearable", "custom"]

STAT_KEYS = ["strength", "dexterity", "intelligence", "fortitude", "charisma", "reflex"]


def _stat_field(key: str) -> CustomField:
    return CustomField(
        key=key, label=key.title(), field_type="number",
        required=True, bound_behavior="stat", value=10,
    )


KIND_FIELD_DEFS: dict[Kind, list[CustomField]] = {
    "character": [
        CustomField(key="name", label="Name", field_type="string", required=True),
        *[_stat_field(k) for k in STAT_KEYS],
        CustomField(key="hp", label="HP", field_type="number", required=True, bound_behavior="hp", value=10),
        CustomField(key="max_hp", label="Max HP", field_type="number", required=True, bound_behavior="max_hp", value=10),
        CustomField(key="description", label="Description", field_type="string", value=""),
        CustomField(key="tone", label="Speaking Tone", field_type="string", value=""),
        CustomField(key="age", label="Age", field_type="number"),
        CustomField(key="is_player", label="Is Player", field_type="boolean", bound_behavior="is_player", value=False),
    ],
    # race/class/weapon/consumable/wearable are item-like: many instances typically
    # share one named Template ("Rusty Sword", "Elf"), and Template.name (a required,
    # dedicated top-level field, guaranteed by pydantic itself) already covers that --
    # no "name" CustomField needed in these lists. "character" is different: every
    # instance IS unique (no shared template name makes sense for "Kael"), and Instance
    # has no top-level name field, so its name has to live in `fields` instead.
    "race": [],
    "class": [],
    "weapon": [
        CustomField(key="hit_roll", label="Hit Roll", field_type="dice_roll", required=True, bound_behavior="hit_roll"),
        CustomField(key="damage_roll", label="Damage Roll", field_type="dice_roll", required=True, bound_behavior="damage_roll"),
        CustomField(key="weight", label="Weight", field_type="number", bound_behavior="weight"),
    ],
    "consumable": [
        CustomField(key="heal_amount", label="Heal Amount", field_type="number", bound_behavior="heal_amount"),
        CustomField(key="grants_status_effect_id", label="Grants Status Effect", field_type="string", bound_behavior="grants_status_effect"),
        CustomField(key="consumed_on_use", label="Consumed On Use", field_type="boolean", bound_behavior="consumed_on_use", value=True),
    ],
    "wearable": [
        CustomField(key="defense", label="Defense", field_type="number", bound_behavior="defense"),
        CustomField(key="stat_key", label="Stat Modified", field_type="string", is_enum=True,
                    options=list(STAT_KEYS), bound_behavior="stat_modifier_key"),
        CustomField(key="stat_delta", label="Stat Delta", field_type="number", bound_behavior="stat_modifier_delta"),
        CustomField(key="slot", label="Equip Slot", field_type="string", is_enum=True,
                    options=["head", "body", "hands", "feet", "waist", "neck", "ring", "back"],
                    bound_behavior="equip_slot", value="body"),
    ],
    "custom": [],   # no canonical fields at all -- a DM adds whatever they want, unvalidated
}

UNIVERSAL_FIELD_DEFS: list[CustomField] = [
    CustomField(key="contains", label="Contains", field_type="string", bound_behavior="container"),
    CustomField(key="grants_context_card_id", label="Grants Context Card", field_type="string", bound_behavior="readable"),
    CustomField(key="unlocks_poi_id", label="Unlocks POI", field_type="string", bound_behavior="key"),
    CustomField(key="value", label="Value", field_type="number", bound_behavior="value"),
]
# Available on any kind on top of that kind's own fields -- single optional capabilities
# (container/readable/key/valuable-ness), not categories that need their own template variety.


def default_fields_for_kind(kind: Kind) -> list[CustomField]:
    """The canonical starting field set for a newly-created Template of this kind."""
    return [f.model_copy(deep=True) for f in (KIND_FIELD_DEFS.get(kind, []) + UNIVERSAL_FIELD_DEFS)]


# ── Template ───────────────────────────────────────────────────────────────────
# A Template is a definition -- the blueprint for a category of thing. Its `fields`
# are initialized from default_fields_for_kind() at creation, plus whatever extra
# CustomFields a DM adds beyond the canonical set.

class TemplateCreate(BaseModel):
    adventure_id: str
    kind: Kind
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    fields: list[CustomField] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Template(BaseDocument):
    kind: Kind
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    fields: list[CustomField] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    fields: list[CustomField] | None = None
    metadata: dict[str, Any] | None = None
    removed_field_keys: list[str] | None = None   # keys to drop from `fields` entirely --
                                                    # merge_fields only adds/overrides by key,
                                                    # it has no way to shrink a field list itself


# ── AttachedRef ────────────────────────────────────────────────────────────────
# References race/class/wearable/status_effect attachments on a character Instance.
# expires_at_round is None for permanent attachments (race/class/equipped wearables)
# and set for temporary ones (active status effects).

class AttachedRef(BaseModel):
    ref_id: str
    ref_kind: str
    expires_at_round: int | None = None


# ── Instance ───────────────────────────────────────────────────────────────────
# An Instance is one specific thing that exists in the world right now -- a specific
# sword, or (kind="character") an actual character. `fields` is a sparse override
# list: only entries for keys that differ from the template.

class InstanceCreate(BaseModel):
    adventure_id: str
    kind: Kind
    template_id: str | None = None
    fields: list[CustomField] = Field(default_factory=list)
    attached: list[AttachedRef] = Field(default_factory=list)
    inventory_ids: list[str] = Field(default_factory=list)
    equipped_weapon_id: str | None = None
    equipped_wearable_ids: list[str] = Field(default_factory=list)
    ai_profile: AIProfile | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    owner_id: str | None = None
    notes: str = ""


class Instance(BaseDocument):
    kind: Kind
    template_id: str | None = None
    fields: list[CustomField] = Field(default_factory=list)
    attached: list[AttachedRef] = Field(default_factory=list)
    inventory_ids: list[str] = Field(default_factory=list)   # meaningful for kind="character" only
    equipped_weapon_id: str | None = None                    # dedicated field, not part of `attached` --
                                                               # attack resolution needs exactly one
                                                               # authoritative weapon, not a list
    equipped_wearable_ids: list[str] = Field(default_factory=list)   # meaningful for kind="character"
                                                               # only -- always a subset of inventory_ids,
                                                               # mirroring how equipped_weapon_id points
                                                               # into inventory rather than sitting outside it
    ai_profile: AIProfile | None = None    # meaningful for kind="character" (NPC AI) only
    metadata: dict[str, Any] = Field(default_factory=dict)
    owner_id: str | None = None       # meaningful for item-like kinds
    notes: str = ""


class InstanceUpdate(BaseModel):
    template_id: str | None = None
    fields: list[CustomField] | None = None
    attached: list[AttachedRef] | None = None
    inventory_ids: list[str] | None = None
    equipped_weapon_id: str | None = None
    equipped_wearable_ids: list[str] | None = None
    ai_profile: AIProfile | None = None
    metadata: dict[str, Any] | None = None
    owner_id: str | None = None
    notes: str | None = None


# ── Resolved Instance + merge ────────────────────────────────────────────────

class ResolvedInstance(BaseModel):
    id: str
    adventure_id: str
    kind: Kind
    template_id: str | None
    name: str
    description: str
    tags: list[str]
    fields: list[CustomField]
    metadata: dict[str, Any]
    attached: list[AttachedRef]
    inventory_ids: list[str]
    equipped_weapon_id: str | None
    equipped_wearable_ids: list[str]
    ai_profile: AIProfile | None
    owner_id: str | None
    notes: str


def merge_fields(base: list[CustomField], overrides: list[CustomField]) -> list[CustomField]:
    """Merge two field lists by key -- entries in `overrides` win wholesale for shared
    keys. Shared by resolve_instance() (template fields + instance overrides) and the
    entities router (canonical kind defaults + a create/update payload's own fields).
    """
    by_key: dict[str, CustomField] = {f.key: f for f in base}
    for f in overrides:
        by_key[f.key] = f
    return list(by_key.values())


def resolve_instance(instance: Instance, template: Template | None) -> ResolvedInstance:
    """Merge a template's default fields with an instance's sparse overrides.
    The instance's field object wins wholesale for any shared key.
    """
    merged_fields = merge_fields(template.fields if template else [], instance.fields)
    # A "name" CustomField (character kind) means this instance is uniquely named and
    # wins over the template's (shared/generic) name; item-like kinds have no "name"
    # CustomField at all, so they fall through to template.name ("Rusty Sword").
    instance_name = get_field(merged_fields, "name")
    resolved_name = instance_name if instance_name else (template.name if template else "")

    return ResolvedInstance(
        id=instance.id,
        adventure_id=instance.adventure_id,
        kind=instance.kind,
        template_id=instance.template_id,
        name=resolved_name,
        description=template.description if template else "",
        tags=template.tags if template else [],
        fields=merged_fields,
        metadata={**(template.metadata if template else {}), **instance.metadata},
        attached=instance.attached,
        inventory_ids=instance.inventory_ids,
        equipped_weapon_id=instance.equipped_weapon_id,
        equipped_wearable_ids=instance.equipped_wearable_ids,
        ai_profile=instance.ai_profile,
        owner_id=instance.owner_id,
        notes=instance.notes,
    )


# ── Validation ─────────────────────────────────────────────────────────────────

class MissingRequiredFieldError(ValueError):
    def __init__(self, missing_keys: list[str]):
        self.missing_keys = missing_keys
        super().__init__(f"missing required field(s): {', '.join(missing_keys)}")


def missing_required_keys(defs: list[CustomField], merged_fields: list[CustomField]) -> list[str]:
    """Which of `defs`' required keys are absent or null in `merged_fields`.
    Shared by kind-level (Template/Instance) and effect_type-level (Effect.parameters)
    validation -- both are "a canonical field-def list vs. a provided field list".
    """
    required_keys = {f.key for f in defs if f.required}
    if not required_keys:
        return []
    values_by_key = {f.key: f.value for f in merged_fields}
    return [k for k in required_keys if values_by_key.get(k) is None]


def validate_required_fields(kind: Kind, merged_fields: list[CustomField]) -> None:
    """Raise MissingRequiredFieldError if any of kind's canonical required fields are
    absent or null in the merged (template + instance) field list. kind="custom" has
    no canonical fields, so it's always exempt.
    """
    missing = missing_required_keys(KIND_FIELD_DEFS.get(kind, []), merged_fields)
    if missing:
        raise MissingRequiredFieldError(missing)


# ── dice_roll parsing ────────────────────────────────────────────────────────
# dice_roll fields store a canonical "2d6+4"-style string, not a structured value --
# the creation UI collects count/sides/bonus as 3 separate inputs and combines them
# into this string; consumers parse it back apart before rolling.

_DICE_NOTATION_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


def format_dice_notation(count: int, sides: int, bonus: int = 0) -> str:
    suffix = f"{bonus:+d}" if bonus else ""
    return f"{count}d{sides}{suffix}"


def parse_dice_notation(notation: str) -> tuple[int, int, int]:
    """Parse '2d6+4' -> (count=2, sides=6, bonus=4). Raises ValueError if malformed."""
    match = _DICE_NOTATION_RE.match(notation.strip())
    if not match:
        raise ValueError(f"Invalid dice notation: {notation!r}")
    count_str, sides_str, bonus_str = match.groups()
    return int(count_str), int(sides_str), int(bonus_str) if bonus_str else 0
