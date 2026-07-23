"""
Pure unit tests for the new kind-tagged Template/Instance system (Phase 0) --
no FastAPI app, no database, just the model/merge/validation logic in isolation.

Run with:
    python -m pytest tests/test_blueprint_models.py -v
"""

import pytest
from backend.models.blueprint import (
    CustomField, Template, Instance, AttachedRef,
    default_fields_for_kind, resolve_instance, get_field,
    validate_required_fields, MissingRequiredFieldError,
    format_dice_notation, parse_dice_notation,
    KIND_FIELD_DEFS, STAT_KEYS,
)
from backend.models.status_effect import (
    Effect, StatusEffectDef, validate_effect_parameters,
)


ADV = "adv-test-001"


# ── CustomField / default field sets ───────────────────────────────────────────

class TestDefaultFields:
    def test_weapon_defaults_have_no_name_field(self):
        fields = default_fields_for_kind("weapon")
        keys = [f.key for f in fields]
        assert "name" not in keys, "item-like kinds should rely on Template.name, not a name CustomField"
        assert "hit_roll" in keys and "damage_roll" in keys

    def test_character_defaults_include_name_and_all_six_stats(self):
        fields = default_fields_for_kind("character")
        keys = {f.key for f in fields}
        assert "name" in keys, "character kind needs its own name field -- Instance has no top-level name"
        assert set(STAT_KEYS).issubset(keys)

    def test_universal_fields_present_on_every_kind(self):
        for kind in KIND_FIELD_DEFS:
            keys = {f.key for f in default_fields_for_kind(kind)}
            assert {"contains", "grants_context_card_id", "unlocks_poi_id", "value"}.issubset(keys)

    def test_custom_kind_has_no_canonical_fields(self):
        assert default_fields_for_kind("custom") == [
            f for f in default_fields_for_kind("custom")
            if f.key in {"contains", "grants_context_card_id", "unlocks_poi_id", "value"}
        ]

    def test_is_enum_is_orthogonal_to_field_type(self):
        wearable_fields = default_fields_for_kind("wearable")
        stat_key_field = next(f for f in wearable_fields if f.key == "stat_key")
        assert stat_key_field.field_type == "string"
        assert stat_key_field.is_enum is True
        assert set(stat_key_field.options) == set(STAT_KEYS)


# ── resolve_instance merge-by-key semantics ────────────────────────────────────

class TestResolveInstance:
    def test_instance_field_overrides_template_field(self):
        template = Template(
            adventure_id=ADV, kind="weapon", name="Rusty Sword",
            fields=[CustomField(key="weight", field_type="number", value=3)],
        )
        instance = Instance(
            adventure_id=ADV, kind="weapon", template_id=template.id,
            fields=[CustomField(key="weight", field_type="number", value=99)],
        )
        resolved = resolve_instance(instance, template)
        assert get_field(resolved.fields, "weight") == 99

    def test_template_field_used_when_instance_has_no_override(self):
        template = Template(
            adventure_id=ADV, kind="weapon", name="Rusty Sword",
            fields=[CustomField(key="weight", field_type="number", value=3)],
        )
        instance = Instance(adventure_id=ADV, kind="weapon", template_id=template.id, fields=[])
        resolved = resolve_instance(instance, template)
        assert get_field(resolved.fields, "weight") == 3

    def test_item_like_kind_name_comes_from_template(self):
        template = Template(adventure_id=ADV, kind="weapon", name="Rusty Sword", fields=[])
        instance = Instance(adventure_id=ADV, kind="weapon", template_id=template.id, fields=[])
        resolved = resolve_instance(instance, template)
        assert resolved.name == "Rusty Sword"

    def test_character_name_comes_from_fields_not_template(self):
        template = Template(adventure_id=ADV, kind="character", name="Default Character", fields=[])
        instance = Instance(
            adventure_id=ADV, kind="character", template_id=template.id,
            fields=[CustomField(key="name", field_type="string", value="Kael")],
        )
        resolved = resolve_instance(instance, template)
        assert resolved.name == "Kael", "the character's own name must win over the generic template name"

    def test_resolve_with_no_template(self):
        instance = Instance(adventure_id=ADV, kind="custom", fields=[CustomField(key="foo", value="bar")])
        resolved = resolve_instance(instance, None)
        assert resolved.name == ""
        assert get_field(resolved.fields, "foo") == "bar"


# ── Required-field validation ──────────────────────────────────────────────────

class TestValidation:
    def test_missing_required_field_raises(self):
        fields = default_fields_for_kind("weapon")  # hit_roll/damage_roll present but value=None
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_required_fields("weapon", fields)
        assert set(exc_info.value.missing_keys) == {"hit_roll", "damage_roll"}

    def test_satisfied_required_fields_pass(self):
        fields = [
            CustomField(key="hit_roll", field_type="dice_roll", value="1d20+2"),
            CustomField(key="damage_roll", field_type="dice_roll", value="2d6+4"),
        ]
        validate_required_fields("weapon", fields)  # should not raise

    def test_custom_kind_is_exempt(self):
        validate_required_fields("custom", [])  # no canonical fields -- never raises

    def test_character_requires_name_but_stats_already_default_to_10(self):
        fields = default_fields_for_kind("character")
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_required_fields("character", fields)
        # stats/hp/max_hp already carry value=10 in KIND_FIELD_DEFS, so only "name" (which
        # has no default) should be reported missing.
        assert set(exc_info.value.missing_keys) == {"name"}


# ── Dice notation ───────────────────────────────────────────────────────────────

class TestDiceNotation:
    def test_format_and_parse_round_trip(self):
        assert format_dice_notation(2, 6, 4) == "2d6+4"
        assert parse_dice_notation("2d6+4") == (2, 6, 4)

    def test_negative_bonus(self):
        assert format_dice_notation(1, 20, -2) == "1d20-2"
        assert parse_dice_notation("1d20-2") == (1, 20, -2)

    def test_no_bonus(self):
        assert format_dice_notation(1, 20) == "1d20"
        assert parse_dice_notation("1d20") == (1, 20, 0)

    def test_malformed_notation_raises(self):
        with pytest.raises(ValueError):
            parse_dice_notation("not a dice roll")


# ── AttachedRef ──────────────────────────────────────────────────────────────

class TestAttachedRef:
    def test_permanent_vs_temporary(self):
        race_ref = AttachedRef(ref_id="race-elf", ref_kind="race", expires_at_round=None)
        poison_ref = AttachedRef(ref_id="status-poison-1", ref_kind="status_effect", expires_at_round=12)
        assert race_ref.expires_at_round is None
        assert poison_ref.expires_at_round == 12


# ── Status effects ───────────────────────────────────────────────────────────

class TestStatusEffects:
    def test_effect_with_satisfied_parameters_passes(self):
        effect = Effect(
            effect_type="stat_delta",
            parameters=[
                CustomField(key="stat_key", value="strength"),
                CustomField(key="delta", value=2),
            ],
        )
        validate_effect_parameters(effect)  # should not raise

    def test_effect_missing_parameter_raises(self):
        effect = Effect(effect_type="hp_delta_over_time", parameters=[])
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_effect_parameters(effect)
        assert exc_info.value.missing_keys == ["amount_per_turn"]

    def test_status_effect_def_can_combine_multiple_effects(self):
        poison = StatusEffectDef(
            adventure_id=ADV,
            name="Poison I",
            effects=[
                Effect(effect_type="hp_delta_over_time", parameters=[CustomField(key="amount_per_turn", value=-5)]),
                Effect(effect_type="stat_delta", parameters=[
                    CustomField(key="stat_key", value="strength"),
                    CustomField(key="delta", value=-1),
                ]),
            ],
        )
        assert len(poison.effects) == 2
        for effect in poison.effects:
            validate_effect_parameters(effect)
