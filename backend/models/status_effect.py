from typing import Literal
from pydantic import BaseModel, Field
from .shared import BaseDocument
from .blueprint import CustomField, STAT_KEYS, missing_required_keys, MissingRequiredFieldError


# ── Status effects ─────────────────────────────────────────────────────────────
# Not Template/Instance-shaped -- there's no meaningful "many differently-configured
# instances of a Poison template". A status is a fixed, fully-specified definition
# (e.g. "Poison I", "Poison II" as distinct defs, not variants of one template).

EffectType = Literal["hp_delta_over_time", "stat_delta", "hp_delta", "damage_delta"]
# Closed, engine-defined set -- a DM configures parameters for an existing effect_type,
# can't invent a new one. Adding a new EffectType later is cheap (one Literal value +
# one EFFECT_TYPE_FIELD_DEFS entry).

EFFECT_TYPE_FIELD_DEFS: dict[EffectType, list[CustomField]] = {
    # Ticks each turn, doesn't revert (regen if positive, poison if negative).
    "hp_delta_over_time": [
        CustomField(key="amount_per_turn", label="Amount Per Turn", field_type="number", required=True),
    ],
    # Active while the status persists, reverts on expiry.
    "stat_delta": [
        CustomField(key="stat_key", label="Stat", field_type="string", is_enum=True, options=list(STAT_KEYS), required=True),
        CustomField(key="delta", label="Delta", field_type="number", required=True),
    ],
    # Temporary flat HP modifier, reverts on expiry.
    "hp_delta": [
        CustomField(key="amount", label="Amount", field_type="number", required=True),
    ],
    # Temporary outgoing-damage modifier, reverts on expiry.
    "damage_delta": [
        CustomField(key="amount", label="Amount", field_type="number", required=True),
    ],
}


class Effect(BaseModel):
    effect_type: EffectType
    parameters: list[CustomField] = Field(default_factory=list)


def validate_effect_parameters(effect: Effect) -> None:
    """Raise MissingRequiredFieldError if `effect.parameters` is missing any of its
    effect_type's required fields.
    """
    missing = missing_required_keys(EFFECT_TYPE_FIELD_DEFS.get(effect.effect_type, []), effect.parameters)
    if missing:
        raise MissingRequiredFieldError(missing)


class StatusEffectDefCreate(BaseModel):
    adventure_id: str
    name: str
    effects: list[Effect] = Field(default_factory=list)


class StatusEffectDef(BaseDocument):
    name: str
    effects: list[Effect] = Field(default_factory=list)   # a status can combine multiple effects


class StatusEffectDefUpdate(BaseModel):
    name: str | None = None
    effects: list[Effect] | None = None
