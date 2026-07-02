from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.item import (
    ItemTemplate, ItemTemplateCreate,
    ItemInstance, ItemInstanceCreate, ItemInstanceUpdate,
    ResolvedItemInstance, merge_with_template,
)

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _doc_to_template(doc) -> ItemTemplate:
    """Convert a Firestore document snapshot to an ItemTemplate."""
    data = doc.to_dict()
    data["id"] = doc.id
    return ItemTemplate(**data)


def _doc_to_instance(doc) -> ItemInstance:
    """Convert a Firestore document snapshot to an ItemInstance."""
    data = doc.to_dict()
    data["id"] = doc.id
    return ItemInstance(**data)


# ── Item Template Endpoints ────────────────────────────────────────────────────

@router.post("/item-templates", response_model=ItemTemplate, status_code=201)
async def create_template(payload: ItemTemplateCreate):
    db = get_db()
    template = ItemTemplate(**payload.model_dump())

    # Write to Firestore using the generated UUID as the document ID
    db.collection("item_templates").document(template.id).set(template.model_dump())
    return template


@router.get("/item-templates", response_model=list[ItemTemplate])
async def list_templates(adventure_id: str):
    db = get_db()
    docs = db.collection("item_templates").where("adventure_id", "==", adventure_id).stream()
    return [_doc_to_template(d) for d in docs]


@router.get("/item-templates/{template_id}", response_model=ItemTemplate)
async def get_template(template_id: str):
    db = get_db()
    doc = db.collection("item_templates").document(template_id).get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Item template not found")
    return _doc_to_template(doc)


@router.patch("/item-templates/{template_id}", response_model=ItemTemplate)
async def update_template(template_id: str, updates: dict):
    db = get_db()
    ref = db.collection("item_templates").document(template_id)

    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Item template not found")

    ref.update(updates)
    return _doc_to_template(ref.get())


@router.delete("/item-templates/{template_id}", status_code=204)
async def delete_template(template_id: str):
    db = get_db()

    # Refuse deletion if any instances reference this template
    instances = db.collection("item_instances").where("template_id", "==", template_id).limit(1).stream()
    if any(True for _ in instances):
        raise HTTPException(status_code=409, detail="Cannot delete template: instances exist")

    db.collection("item_templates").document(template_id).delete()


# ── Item Instance Endpoints ────────────────────────────────────────────────────

@router.post("/item-instances", response_model=ItemInstance, status_code=201)
async def create_instance(payload: ItemInstanceCreate):
    db = get_db()

    # Verify the referenced template exists before creating an instance
    template_doc = db.collection("item_templates").document(payload.template_id).get()
    if not template_doc.exists:
        raise HTTPException(status_code=404, detail="Item template not found")

    instance = ItemInstance(**payload.model_dump())
    db.collection("item_instances").document(instance.id).set(instance.model_dump())
    return instance


@router.get("/item-instances", response_model=list[ItemInstance])
async def list_instances(owner_id: str | None = None, adventure_id: str | None = None):
    db = get_db()
    query = db.collection("item_instances")

    # Apply filters — at least one must be provided
    if owner_id is not None:
        query = query.where("owner_id", "==", owner_id)
    elif adventure_id is not None:
        query = query.where("adventure_id", "==", adventure_id)
    else:
        raise HTTPException(status_code=400, detail="Provide owner_id or adventure_id")

    return [_doc_to_instance(d) for d in query.stream()]


@router.get("/item-instances/{instance_id}", response_model=ResolvedItemInstance)
async def get_instance(instance_id: str):
    db = get_db()
    inst_doc = db.collection("item_instances").document(instance_id).get()

    if not inst_doc.exists:
        raise HTTPException(status_code=404, detail="Item instance not found")

    instance = _doc_to_instance(inst_doc)
    tmpl_doc = db.collection("item_templates").document(instance.template_id).get()

    if not tmpl_doc.exists:
        raise HTTPException(status_code=500, detail="Orphaned instance: template missing")

    # Merge instance overrides onto template defaults (implemented by you!)
    return merge_with_template(instance, _doc_to_template(tmpl_doc))


@router.patch("/item-instances/{instance_id}", response_model=ItemInstance)
async def update_instance(instance_id: str, updates: ItemInstanceUpdate):
    db = get_db()
    ref = db.collection("item_instances").document(instance_id)

    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Item instance not found")

    # Only send fields that were actually provided in the request
    changes = {k: v for k, v in updates.model_dump().items() if v is not None}
    ref.update(changes)
    return _doc_to_instance(ref.get())


@router.delete("/item-instances/{instance_id}", status_code=204)
async def delete_instance(instance_id: str):
    db = get_db()

    if not db.collection("item_instances").document(instance_id).get().exists:
        raise HTTPException(status_code=404, detail="Item instance not found")

    db.collection("item_instances").document(instance_id).delete()
