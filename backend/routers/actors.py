from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ..firebase import get_db
from ..models.actor import Actor, ActorCreate, ActorUpdate, AdventureActorSlot, AdventureActorSlotCreate
from ..utils.auth import get_current_uid, require_member

router = APIRouter()


# ── User-level actor CRUD ──────────────────────────────────────────────────────

@router.get("/actors")
async def list_actors(request: Request):
    uid = await get_current_uid(request)
    db = get_db()
    docs = db.collection("actors").where("owner_uid", "==", uid).stream()
    return [Actor(**{**d.to_dict(), "id": d.id}).model_dump() for d in docs]


@router.post("/actors", status_code=201)
async def create_actor(payload: ActorCreate, request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    actor = Actor(owner_uid=uid, **payload.model_dump())
    db.collection("actors").document(actor.id).set(actor.model_dump())
    return actor.model_dump()


@router.patch("/actors/{actor_id}")
async def update_actor(actor_id: str, payload: ActorUpdate, request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    doc = db.collection("actors").document(actor_id).get()
    if not doc.exists:
        raise HTTPException(404, "Actor not found")

    actor = Actor(**{**doc.to_dict(), "id": doc.id})
    if actor.owner_uid != uid:
        raise HTTPException(403, "Not your actor")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if updates:
        db.collection("actors").document(actor_id).update(updates)

    return Actor(**{**doc.to_dict(), **updates, "id": actor_id}).model_dump()


@router.delete("/actors/{actor_id}", status_code=204)
async def delete_actor(actor_id: str, request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    doc = db.collection("actors").document(actor_id).get()
    if not doc.exists:
        raise HTTPException(404, "Actor not found")

    actor = Actor(**{**doc.to_dict(), "id": doc.id})
    if actor.owner_uid != uid:
        raise HTTPException(403, "Not your actor")

    db.collection("actors").document(actor_id).delete()


# ── Adventure actor slots ──────────────────────────────────────────────────────

@router.get("/adventures/{adventure_id}/actor-slots")
async def list_actor_slots(adventure_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "viewer")
    db = get_db()

    docs = db.collection("adventure_actor_slots").where("adventure_id", "==", adventure_id).stream()
    return [AdventureActorSlot(**{**d.to_dict(), "id": d.id}).model_dump() for d in docs]


@router.post("/adventures/{adventure_id}/actor-slots", status_code=201)
async def add_actor_slot(adventure_id: str, payload: AdventureActorSlotCreate, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "player")
    db = get_db()

    actor_doc = db.collection("actors").document(payload.actor_id).get()
    if not actor_doc.exists:
        raise HTTPException(404, "Actor not found")

    slot = AdventureActorSlot(
        adventure_id=adventure_id,
        actor_id=payload.actor_id,
        owner_uid=uid,
        added_at=datetime.now(timezone.utc).isoformat(),
    )
    db.collection("adventure_actor_slots").document(slot.id).set(slot.model_dump())
    return slot.model_dump()


@router.delete("/adventures/{adventure_id}/actor-slots/{slot_id}", status_code=204)
async def remove_actor_slot(adventure_id: str, slot_id: str, request: Request):
    uid = await get_current_uid(request)
    caller = await require_member(adventure_id, uid, "player")
    db = get_db()

    doc = db.collection("adventure_actor_slots").document(slot_id).get()
    if not doc.exists:
        raise HTTPException(404, "Slot not found")

    slot = AdventureActorSlot(**{**doc.to_dict(), "id": doc.id})
    if slot.adventure_id != adventure_id:
        raise HTTPException(404, "Slot not found")

    from ..models.member import ROLE_RANK
    if slot.owner_uid != uid and ROLE_RANK.get(caller.role, 0) < ROLE_RANK["admin"]:
        raise HTTPException(403, "Cannot remove another member's actor slot")

    db.collection("adventure_actor_slots").document(slot_id).delete()
