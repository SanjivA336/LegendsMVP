from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.blueprint import (
    Kind, Template, TemplateCreate, TemplateUpdate, CustomField,
    Instance, InstanceCreate, InstanceUpdate, ResolvedInstance,
    default_fields_for_kind, merge_fields, resolve_instance,
    validate_required_fields, MissingRequiredFieldError,
)

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _doc_to_template(doc) -> Template:
    return Template(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_instance(doc) -> Instance:
    return Instance(**(doc.to_dict() | {"id": doc.id}))


def _get_template_or_404(template_id: str, db) -> Template:
    doc = db.collection("templates").document(template_id).get()
    if not doc.exists:
        raise HTTPException(404, "Template not found")
    return _doc_to_template(doc)


def _validate_or_400(kind: Kind, merged_fields) -> None:
    try:
        validate_required_fields(kind, merged_fields)
    except MissingRequiredFieldError as exc:
        raise HTTPException(400, str(exc)) from exc


# ── Template Endpoints ─────────────────────────────────────────────────────────

@router.post("/templates", response_model=Template, status_code=201)
async def create_template(payload: TemplateCreate):
    db = get_db()
    fields = merge_fields(default_fields_for_kind(payload.kind), payload.fields)
    _validate_or_400(payload.kind, fields)

    template = Template(**(payload.model_dump() | {"fields": fields}))
    db.collection("templates").document(template.id).set(template.model_dump())
    return template


@router.get("/templates", response_model=list[Template])
async def list_templates(adventure_id: str, kind: Kind | None = None):
    db = get_db()
    query = db.collection("templates").where("adventure_id", "==", adventure_id)
    if kind:
        query = query.where("kind", "==", kind)
    return [_doc_to_template(d) for d in query.stream()]


@router.get("/templates/default-fields", response_model=list[CustomField])
async def get_template_default_fields(kind: Kind):
    """Read-only, non-persisting -- lets the wizard's Template modal pre-seed a new
    draft with the server's actual canonical field set, with zero drift risk from a
    hand-maintained TS mirror of KIND_FIELD_DEFS."""
    return default_fields_for_kind(kind)


@router.get("/templates/{template_id}", response_model=Template)
async def get_template(template_id: str):
    db = get_db()
    return _get_template_or_404(template_id, db)


@router.patch("/templates/{template_id}", response_model=Template)
async def update_template(template_id: str, updates: TemplateUpdate):
    db = get_db()
    ref = db.collection("templates").document(template_id)
    template = _get_template_or_404(template_id, db)

    base_fields = template.fields
    if updates.removed_field_keys:
        removed = set(updates.removed_field_keys)
        base_fields = [f for f in base_fields if f.key not in removed]

    changes = {
        k: v for k, v in updates.model_dump().items()
        if v is not None and k != "removed_field_keys"
    }
    if updates.fields is not None:
        merged = merge_fields(base_fields, updates.fields)
        _validate_or_400(template.kind, merged)
        changes["fields"] = [f.model_dump() for f in merged]
    elif updates.removed_field_keys:
        _validate_or_400(template.kind, base_fields)
        changes["fields"] = [f.model_dump() for f in base_fields]
    ref.update(changes)

    # Cascade: an instance's own override for a since-deleted template field would
    # otherwise keep showing it forever (merge_fields always keeps override-only keys,
    # and this template edit doesn't touch instance docs on its own).
    if updates.removed_field_keys:
        removed = set(updates.removed_field_keys)
        for doc in db.collection("instances").where("template_id", "==", template_id).stream():
            inst_fields = doc.to_dict().get("fields", [])
            filtered = [f for f in inst_fields if f.get("key") not in removed]
            if len(filtered) != len(inst_fields):
                db.collection("instances").document(doc.id).update({"fields": filtered})

    return _doc_to_template(ref.get())


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(template_id: str):
    db = get_db()
    if not db.collection("templates").document(template_id).get().exists:
        raise HTTPException(404, "Template not found")

    referencing = list(
        db.collection("instances").where("template_id", "==", template_id).limit(1).stream()
    )
    if referencing:
        raise HTTPException(409, "Cannot delete template: instances exist")

    db.collection("templates").document(template_id).delete()


# ── Instance Endpoints ─────────────────────────────────────────────────────────

@router.post("/instances", response_model=Instance, status_code=201)
async def create_instance(payload: InstanceCreate):
    db = get_db()

    template = None
    if payload.template_id:
        template = _get_template_or_404(payload.template_id, db)
        if template.kind != payload.kind:
            raise HTTPException(400, f"template kind '{template.kind}' does not match instance kind '{payload.kind}'")

    merged = merge_fields(template.fields if template else [], payload.fields)
    _validate_or_400(payload.kind, merged)

    instance = Instance(**payload.model_dump())
    db.collection("instances").document(instance.id).set(instance.model_dump())
    return instance


@router.get("/instances", response_model=list[Instance])
async def list_instances(adventure_id: str, kind: Kind | None = None, owner_id: str | None = None):
    db = get_db()
    query = db.collection("instances").where("adventure_id", "==", adventure_id)
    if kind:
        query = query.where("kind", "==", kind)
    if owner_id:
        query = query.where("owner_id", "==", owner_id)
    return [_doc_to_instance(d) for d in query.stream()]


@router.get("/instances/{instance_id}", response_model=ResolvedInstance)
async def get_instance(instance_id: str):
    db = get_db()
    doc = db.collection("instances").document(instance_id).get()
    if not doc.exists:
        raise HTTPException(404, "Instance not found")
    instance = _doc_to_instance(doc)

    template = None
    if instance.template_id:
        tmpl_doc = db.collection("templates").document(instance.template_id).get()
        if tmpl_doc.exists:
            template = _doc_to_template(tmpl_doc)
        # An orphaned template_id resolves with template=None rather than erroring --
        # matches this codebase's existing tolerance for orphaned references
        # (resolve_inventory already skips orphaned item instances/templates the same way).

    return resolve_instance(instance, template)


@router.patch("/instances/{instance_id}", response_model=Instance)
async def update_instance(instance_id: str, updates: InstanceUpdate):
    db = get_db()
    ref = db.collection("instances").document(instance_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(404, "Instance not found")
    instance = _doc_to_instance(doc)

    changes = {k: v for k, v in updates.model_dump().items() if v is not None}

    override_fields = instance.fields
    if "fields" in changes:
        override_fields = merge_fields(instance.fields, updates.fields)
        changes["fields"] = [f.model_dump() for f in override_fields]

    # Re-validate whenever the override fields OR which template they're merged
    # against changes -- switching template_id alone can break validation just as
    # much as changing fields alone can.
    if "fields" in changes or "template_id" in changes:
        template = None
        template_id = changes.get("template_id", instance.template_id)
        if template_id:
            tmpl_doc = db.collection("templates").document(template_id).get()
            if tmpl_doc.exists:
                template = _doc_to_template(tmpl_doc)
        full_merge = merge_fields(template.fields if template else [], override_fields)
        _validate_or_400(instance.kind, full_merge)

    ref.update(changes)
    return _doc_to_instance(ref.get())


@router.delete("/instances/{instance_id}", status_code=204)
async def delete_instance(instance_id: str):
    db = get_db()
    if not db.collection("instances").document(instance_id).get().exists:
        raise HTTPException(404, "Instance not found")
    db.collection("instances").document(instance_id).delete()


# ── Starter Content Seeding ────────────────────────────────────────────────────
# Mirrors the existing /pois/seed-map precedent: one dedicated endpoint the wizard
# calls once per adventure, rather than a client-side loop of individual creates.

class SeedStarterContentRequest(BaseModel):
    adventure_id: str


_STARTER_RACES = [
    ("Human", {}),
    ("Elf", {"dexterity": 2}),
    ("Dwarf", {"fortitude": 2}),
    ("Halfling", {"charisma": 2}),
]

_STARTER_CLASSES = [
    ("Fighter", {"strength": 2}),
    ("Wizard", {"intelligence": 2}),
    ("Rogue", {"dexterity": 2}),
    ("Cleric", {"fortitude": 2}),
]


def _seed_stat_bonus_templates(adventure_id: str, kind: Kind, entries: list[tuple[str, dict[str, int]]], db) -> list[str]:
    ids = []
    for name, bonuses in entries:
        bonus_fields = [
            CustomField(key=stat, label=stat.title(), field_type="number", value=delta, bound_behavior="stat")
            for stat, delta in bonuses.items()
        ]
        template = Template(adventure_id=adventure_id, kind=kind, name=name, fields=bonus_fields)
        db.collection("templates").document(template.id).set(template.model_dump())
        ids.append(template.id)
    return ids


@router.post("/templates/seed-starter-content")
async def seed_starter_content(payload: SeedStarterContentRequest):
    """Create a small starter set of race/class Templates for a fresh adventure --
    a DM can accept these as-is (regular fantasy defaults) or add their own
    Templates alongside/instead of them; nothing here is exclusive or required.
    """
    db = get_db()
    race_ids = _seed_stat_bonus_templates(payload.adventure_id, "race", _STARTER_RACES, db)
    class_ids = _seed_stat_bonus_templates(payload.adventure_id, "class", _STARTER_CLASSES, db)
    return {"race_template_ids": race_ids, "class_template_ids": class_ids}
