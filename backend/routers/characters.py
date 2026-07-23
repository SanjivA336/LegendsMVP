from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..firebase import get_db
from ..models.character import (
    Character, CharacterCreate, CharacterUpdate, Stats, default_max_hp,
    character_fields_for_create, character_from_instance, attach_race_and_class,
)
from ..models.blueprint import Instance, Template, CustomField, AttachedRef, STAT_KEYS, merge_fields, resolve_instance

router = APIRouter()


# The frontend's inventory contract predates the kind-tagged Template/Instance system
# and is kept stable here rather than changed -- resolve_inventory() below translates
# the new storage into this shape. `properties` is best-effort (whichever merged fields
# happen to be numeric), since it was always numeric-only and nothing on the frontend
# reads it for real logic, only for display.
class ResolvedItemInstance(BaseModel):
    id: str
    adventure_id: str
    template_id: str
    owner_id: str | None
    notes: str
    name: str
    description: str
    tags: list[str]
    properties: dict[str, float]
    metadata: dict[str, Any]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _doc_to_instance(doc) -> Instance:
    return Instance(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_character(doc) -> Character:
    """Convert a kind="character" Instance Firestore document snapshot to a Character."""
    return character_from_instance(_doc_to_instance(doc))


def resolve_inventory(character: Character, db) -> list[ResolvedItemInstance]:
    """Resolve a character's inventory (now kind-tagged Instances/Templates) into the
    ResolvedItemInstance shape the frontend already expects -- `properties` is
    reconstructed from whichever merged fields happen to be numeric, since that shape
    was always numeric-only anyway and nothing on the frontend reads it for real logic.
    """
    if not character.inventory_ids:
        return []

    instance_refs = [db.collection("instances").document(iid) for iid in character.inventory_ids]
    instances_by_id = {
        d.id: Instance(**d.to_dict() | {"id": d.id}) for d in db.get_all(instance_refs) if d.exists
    }  # skip orphaned instances

    template_ids = {inst.template_id for inst in instances_by_id.values() if inst.template_id}
    template_refs = [db.collection("templates").document(tid) for tid in template_ids]
    templates_by_id = (
        {d.id: Template(**d.to_dict() | {"id": d.id}) for d in db.get_all(template_refs) if d.exists}
        if template_refs else {}
    )  # skip orphaned templates

    inventory: list[ResolvedItemInstance] = []
    for item_id in character.inventory_ids:
        instance = instances_by_id.get(item_id)
        if instance is None:
            continue
        template = templates_by_id.get(instance.template_id) if instance.template_id else None
        resolved = resolve_instance(instance, template)
        properties = {f.key: f.value for f in resolved.fields if isinstance(f.value, (int, float))}
        inventory.append(ResolvedItemInstance(
            id=resolved.id, adventure_id=resolved.adventure_id, template_id=resolved.template_id or "",
            owner_id=resolved.owner_id, notes=resolved.notes,
            name=resolved.name, description=resolved.description, tags=resolved.tags,
            properties=properties, metadata=resolved.metadata,
        ))

    return inventory


# ── Character Endpoints ────────────────────────────────────────────────────────

@router.post("/characters", response_model=Character, status_code=201)
async def create_character(payload: CharacterCreate):
    db = get_db()

    # Claim starting gear before creating anything -- fail fast (404/409) with zero
    # side effects if any requested item doesn't exist or is already owned.
    # equipped_wearable_ids is always a subset of inventory_ids (mirrors how
    # equipped_weapon_id already points into inventory rather than sitting outside it),
    # so both lists are validated and claimed as one deduped set.
    starting_ids = list(dict.fromkeys(payload.starting_inventory_ids + payload.starting_equipped_wearable_ids))
    if starting_ids:
        item_refs = [db.collection("instances").document(iid) for iid in starting_ids]
        items_by_id = {d.id: Instance(**d.to_dict() | {"id": d.id}) for d in db.get_all(item_refs) if d.exists}
        for iid in starting_ids:
            item = items_by_id.get(iid)
            if item is None:
                raise HTTPException(404, f"Starting item not found: {iid}")
            if item.owner_id is not None:
                raise HTTPException(409, f"Item already owned: {iid}")

    max_hp = payload.max_hp if payload.max_hp is not None else default_max_hp(payload.stats)
    hp = payload.hp if payload.hp is not None else max_hp
    fields = character_fields_for_create(payload, hp=hp, max_hp=max_hp)
    attached = attach_race_and_class(payload, db)

    instance = Instance(
        adventure_id=payload.adventure_id, kind="character", template_id=None,
        fields=fields, attached=attached,
        inventory_ids=list(dict.fromkeys(payload.inventory_ids + starting_ids)),
        equipped_weapon_id=payload.equipped_weapon_id,
        equipped_wearable_ids=payload.starting_equipped_wearable_ids,
        ai_profile=payload.ai_profile, metadata=payload.metadata,
    )
    db.collection("instances").document(instance.id).set(instance.model_dump())

    for iid in starting_ids:
        db.collection("instances").document(iid).update({"owner_id": instance.id})

    return character_from_instance(instance)


@router.get("/characters", response_model=list[Character])
async def list_characters(adventure_id: str):
    db = get_db()
    docs = (
        db.collection("instances")
        .where("adventure_id", "==", adventure_id)
        .where("kind", "==", "character")
        .stream()
    )
    return [_doc_to_character(d) for d in docs]


@router.get("/characters/{character_id}", response_model=Character)
async def get_character(character_id: str):
    db = get_db()
    doc = db.collection("instances").document(character_id).get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")
    return _doc_to_character(doc)


@router.get("/characters/{character_id}/inventory", response_model=list[ResolvedItemInstance])
async def get_inventory(character_id: str):
    db = get_db()
    doc = db.collection("instances").document(character_id).get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    return resolve_inventory(_doc_to_character(doc), db)


@router.patch("/characters/{character_id}", response_model=Character)
async def update_character(character_id: str, updates: CharacterUpdate):
    db = get_db()
    ref = db.collection("instances").document(character_id)
    doc = ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")
    instance = _doc_to_instance(doc)

    # Translate the flat CharacterUpdate payload into CustomField overrides, merged
    # into the instance's existing (self-sufficient) field list. Firestore can't patch
    # one array element by key, so the whole `fields` array gets rewritten together.
    override_fields: list[CustomField] = []
    if updates.name is not None:
        override_fields.append(CustomField(key="name", field_type="string", value=updates.name, required=True))
    if updates.description is not None:
        override_fields.append(CustomField(key="description", field_type="string", value=updates.description))
    if updates.tone is not None:
        override_fields.append(CustomField(key="tone", field_type="string", value=updates.tone))
    if updates.is_player is not None:
        override_fields.append(CustomField(key="is_player", field_type="boolean", value=updates.is_player, bound_behavior="is_player"))
    if updates.hp is not None:
        override_fields.append(CustomField(key="hp", field_type="number", value=updates.hp, required=True, bound_behavior="hp"))
    if updates.max_hp is not None:
        override_fields.append(CustomField(key="max_hp", field_type="number", value=updates.max_hp, required=True, bound_behavior="max_hp"))
    if updates.stats is not None:
        for k in STAT_KEYS:
            override_fields.append(CustomField(
                key=k, field_type="number", value=getattr(updates.stats, k), required=True, bound_behavior="stat",
            ))

    changes: dict = {}
    if override_fields:
        merged = merge_fields(instance.fields, override_fields)
        changes["fields"] = [f.model_dump() for f in merged]
    if updates.equipped_weapon_id is not None:
        changes["equipped_weapon_id"] = updates.equipped_weapon_id
    if updates.inventory_ids is not None:
        changes["inventory_ids"] = updates.inventory_ids
    if updates.metadata is not None:
        changes["metadata"] = updates.metadata
    if updates.ai_profile is not None:
        changes["ai_profile"] = updates.ai_profile.model_dump()

    ref.update(changes)
    return _doc_to_character(ref.get())


@router.patch("/characters/{character_id}/equip/{item_id}", response_model=Character)
async def equip_item(character_id: str, item_id: str):
    db = get_db()
    char_doc = db.collection("instances").document(character_id).get()

    if not char_doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    instance = _doc_to_instance(char_doc)

    # Enforce that the item is actually in the character's inventory
    if item_id not in instance.inventory_ids:
        raise HTTPException(status_code=400, detail="Item is not in character's inventory")

    db.collection("instances").document(character_id).update({"equipped_weapon_id": item_id})
    return _doc_to_character(db.collection("instances").document(character_id).get())


@router.patch("/characters/{character_id}/unequip", response_model=Character)
async def unequip_item(character_id: str):
    db = get_db()
    ref = db.collection("instances").document(character_id)

    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Character not found")

    ref.update({"equipped_weapon_id": None})
    return _doc_to_character(ref.get())


@router.delete("/characters/{character_id}", status_code=204)
async def delete_character(character_id: str):
    db = get_db()

    doc = db.collection("instances").document(character_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    # Release owned items back to the unowned pool -- otherwise create-then-delete
    # (the standalone NPC-creation modal makes this a realistic flow) permanently
    # strands them with a dangling owner_id.
    character = Instance(**doc.to_dict() | {"id": doc.id})
    if character.inventory_ids:
        item_refs = [db.collection("instances").document(iid) for iid in character.inventory_ids]
        existing_ids = {d.id for d in db.get_all(item_refs) if d.exists}
        for item_id in existing_ids:
            db.collection("instances").document(item_id).update({"owner_id": None})

    db.collection("instances").document(character_id).delete()


# ── Status effect attach/detach ─────────────────────────────────────────────────
# Basic mechanism for manually applying/removing a status effect on a character
# (testing/DM use). The automatic game-loop trigger (a consumable/attack applying one,
# hp_delta_over_time ticking each round, expiry auto-pruning) is a separate, later piece
# of work -- this only makes attaching/detaching one correctly possible and inspectable.

class AttachStatusEffectRequest(BaseModel):
    status_effect_id: str
    expires_at_round: int | None = None


@router.post("/characters/{character_id}/status-effects", response_model=Character)
async def attach_status_effect(character_id: str, payload: AttachStatusEffectRequest):
    db = get_db()
    ref = db.collection("instances").document(character_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    if not db.collection("status_effect_defs").document(payload.status_effect_id).get().exists:
        raise HTTPException(status_code=404, detail="Status effect not found")

    instance = _doc_to_instance(doc)
    attached = [a for a in instance.attached if not (a.ref_kind == "status_effect" and a.ref_id == payload.status_effect_id)]
    attached.append(AttachedRef(
        ref_id=payload.status_effect_id, ref_kind="status_effect", expires_at_round=payload.expires_at_round,
    ))
    ref.update({"attached": [a.model_dump() for a in attached]})
    return _doc_to_character(ref.get())


@router.delete("/characters/{character_id}/status-effects/{status_effect_id}", response_model=Character)
async def detach_status_effect(character_id: str, status_effect_id: str):
    db = get_db()
    ref = db.collection("instances").document(character_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    instance = _doc_to_instance(doc)
    attached = [a for a in instance.attached if not (a.ref_kind == "status_effect" and a.ref_id == status_effect_id)]
    ref.update({"attached": [a.model_dump() for a in attached]})
    return _doc_to_character(ref.get())
