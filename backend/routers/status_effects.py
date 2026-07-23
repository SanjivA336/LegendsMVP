from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.status_effect import (
    StatusEffectDef, StatusEffectDefCreate, StatusEffectDefUpdate,
    validate_effect_parameters,
)
from ..models.blueprint import MissingRequiredFieldError

router = APIRouter()


def _doc_to_status_effect_def(doc) -> StatusEffectDef:
    return StatusEffectDef(**(doc.to_dict() | {"id": doc.id}))


def _validate_effects_or_400(status_def: StatusEffectDef) -> None:
    try:
        for effect in status_def.effects:
            validate_effect_parameters(effect)
    except MissingRequiredFieldError as exc:
        raise HTTPException(400, f"invalid effect: {exc}") from exc


@router.post("/status-effects", response_model=StatusEffectDef, status_code=201)
async def create_status_effect_def(payload: StatusEffectDefCreate):
    db = get_db()
    status_def = StatusEffectDef(**payload.model_dump())
    _validate_effects_or_400(status_def)
    db.collection("status_effect_defs").document(status_def.id).set(status_def.model_dump())
    return status_def


@router.get("/status-effects", response_model=list[StatusEffectDef])
async def list_status_effect_defs(adventure_id: str):
    db = get_db()
    docs = db.collection("status_effect_defs").where("adventure_id", "==", adventure_id).stream()
    return [_doc_to_status_effect_def(d) for d in docs]


@router.get("/status-effects/{status_effect_id}", response_model=StatusEffectDef)
async def get_status_effect_def(status_effect_id: str):
    db = get_db()
    doc = db.collection("status_effect_defs").document(status_effect_id).get()
    if not doc.exists:
        raise HTTPException(404, "Status effect not found")
    return _doc_to_status_effect_def(doc)


@router.patch("/status-effects/{status_effect_id}", response_model=StatusEffectDef)
async def update_status_effect_def(status_effect_id: str, updates: StatusEffectDefUpdate):
    db = get_db()
    ref = db.collection("status_effect_defs").document(status_effect_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(404, "Status effect not found")

    changes = {k: v for k, v in updates.model_dump().items() if v is not None}
    if "effects" in changes:
        _validate_effects_or_400(StatusEffectDef(**(doc.to_dict() | changes)))

    ref.update(changes)
    return _doc_to_status_effect_def(ref.get())


@router.delete("/status-effects/{status_effect_id}", status_code=204)
async def delete_status_effect_def(status_effect_id: str):
    db = get_db()
    if not db.collection("status_effect_defs").document(status_effect_id).get().exists:
        raise HTTPException(404, "Status effect not found")
    db.collection("status_effect_defs").document(status_effect_id).delete()
