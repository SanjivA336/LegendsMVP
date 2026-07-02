from fastapi import APIRouter, HTTPException
from firebase_admin import firestore as fs
from ..firebase import get_db
from ..models.character import Character, CharacterCreate, CharacterUpdate, default_max_hp
from ..models.item import ItemInstance, ItemTemplate, ResolvedItemInstance, merge_with_template

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _doc_to_character(doc) -> Character:
    """Convert a Firestore document snapshot to a Character."""
    data = doc.to_dict()
    data["id"] = doc.id
    return Character(**data)


def resolve_inventory(character: Character, db) -> list[ResolvedItemInstance]:
    """Resolve a character's inventory into a list of ResolvedItemInstances."""
    
    inventory: list[ResolvedItemInstance] = []

    for item_id in character.inventory_ids:
        # Fetch the ItemInstance document
        instance_doc = db.collection("item_instances").document(item_id).get()
        if not instance_doc.exists:
            continue  # Skip orphaned instances

        instance = ItemInstance(**instance_doc.to_dict() | {"id": instance_doc.id})

        # Fetch the corresponding ItemTemplate document
        template_doc = db.collection("item_templates").document(instance.template_id).get()
        if not template_doc.exists:
            continue  # Skip orphaned templates

        template = ItemTemplate(**template_doc.to_dict() | {"id": template_doc.id})

        # Merge the instance with its template to get the resolved item
        resolved_item = merge_with_template(instance, template)

        inventory.append(resolved_item)

    return inventory


# ── Character Endpoints ────────────────────────────────────────────────────────

@router.post("/characters", response_model=Character, status_code=201)
async def create_character(payload: CharacterCreate):
    db = get_db()

    # Compute max_hp and hp from stats if the caller didn't provide them
    data = payload.model_dump()
    if data["max_hp"] is None:
        data["max_hp"] = default_max_hp(payload.stats)
    if data["hp"] is None:
        data["hp"] = data["max_hp"]

    character = Character(**data)
    db.collection("characters").document(character.id).set(character.model_dump())
    return character


@router.get("/characters", response_model=list[Character])
async def list_characters(adventure_id: str):
    db = get_db()
    docs = db.collection("characters").where("adventure_id", "==", adventure_id).stream()
    return [_doc_to_character(d) for d in docs]


@router.get("/characters/{character_id}", response_model=Character)
async def get_character(character_id: str):
    db = get_db()
    doc = db.collection("characters").document(character_id).get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")
    return _doc_to_character(doc)


@router.get("/characters/{character_id}/inventory", response_model=list[ResolvedItemInstance])
async def get_inventory(character_id: str):
    db = get_db()
    doc = db.collection("characters").document(character_id).get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    # Resolve each inventory ID into a full merged item (implemented by you!)
    return resolve_inventory(_doc_to_character(doc), db)


@router.patch("/characters/{character_id}", response_model=Character)
async def update_character(character_id: str, updates: CharacterUpdate):
    db = get_db()
    ref = db.collection("characters").document(character_id)

    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Character not found")

    # Only send fields that were actually provided; flatten nested Stats to a dict
    changes = {}
    for k, v in updates.model_dump().items():
        if v is not None:
            changes[k] = v

    ref.update(changes)
    return _doc_to_character(ref.get())


@router.patch("/characters/{character_id}/equip/{item_id}", response_model=Character)
async def equip_item(character_id: str, item_id: str):
    db = get_db()
    char_doc = db.collection("characters").document(character_id).get()

    if not char_doc.exists:
        raise HTTPException(status_code=404, detail="Character not found")

    character = _doc_to_character(char_doc)

    # Enforce that the item is actually in the character's inventory
    if item_id not in character.inventory_ids:
        raise HTTPException(status_code=400, detail="Item is not in character's inventory")

    db.collection("characters").document(character_id).update({"equipped_weapon_id": item_id})
    return _doc_to_character(db.collection("characters").document(character_id).get())


@router.patch("/characters/{character_id}/unequip", response_model=Character)
async def unequip_item(character_id: str):
    db = get_db()
    ref = db.collection("characters").document(character_id)

    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Character not found")

    ref.update({"equipped_weapon_id": None})
    return _doc_to_character(ref.get())


@router.delete("/characters/{character_id}", status_code=204)
async def delete_character(character_id: str):
    db = get_db()

    if not db.collection("characters").document(character_id).get().exists:
        raise HTTPException(status_code=404, detail="Character not found")

    db.collection("characters").document(character_id).delete()
