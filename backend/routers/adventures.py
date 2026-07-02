import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ..firebase import get_db
from ..models.adventure import Adventure, AdventureCreate
from ..models.member import Member
from ..utils.auth import get_current_uid, require_member

router = APIRouter()

# Collections owned by an adventure, deleted in order during purge
_ADVENTURE_COLLECTIONS = [
    "adventure_actor_slots",
    "members",
    "actions",
    "encounters",
    "quests",
    "item_instances",
    "characters",
    "context_cards",
    "world_state",
    "world_bible",
    "pois",
    "world_maps",
    "dm_notes",
]


def _batch_delete(db, docs):
    """Delete documents in batches of 499."""
    docs = list(docs)
    for i in range(0, len(docs), 499):
        batch = db.batch()
        for doc in docs[i : i + 499]:
            batch.delete(doc.reference)
        batch.commit()


@router.post("/adventures", status_code=201)
async def create_adventure(payload: AdventureCreate, request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    adventure = Adventure(
        id=payload.adventure_id,
        name=payload.name,
        world_name=payload.world_name,
        world_map_id=payload.world_map_id,
        invite_code=secrets.token_urlsafe(6),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.collection("adventures").document(adventure.id).set(adventure.model_dump())

    member = Member(
        adventure_id=adventure.id,
        user_uid=uid,
        role="owner",
        joined_at=datetime.now(timezone.utc).isoformat(),
    )
    db.collection("members").document(member.id).set(member.model_dump())

    return {"adventure": adventure.model_dump(), "member": member.model_dump()}


@router.get("/adventures")
async def list_adventures(request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    member_docs = list(
        db.collection("members").where("user_uid", "==", uid).stream()
    )
    result = []
    for m_doc in member_docs:
        m_data = m_doc.to_dict() | {"id": m_doc.id}
        member = Member(**m_data)
        adv_doc = db.collection("adventures").document(member.adventure_id).get()
        if not adv_doc.exists:
            continue
        adv = Adventure(**adv_doc.to_dict())
        result.append({"adventure": adv.model_dump(), "member": member.model_dump()})

    return result


@router.get("/adventures/{adventure_id}")
async def get_adventure(adventure_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "viewer")
    db = get_db()

    doc = db.collection("adventures").document(adventure_id).get()
    if not doc.exists:
        raise HTTPException(404, "Adventure not found")

    return Adventure(**doc.to_dict()).model_dump()


@router.delete("/adventures/{adventure_id}", status_code=204)
async def delete_adventure(adventure_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "owner")
    db = get_db()

    for collection in _ADVENTURE_COLLECTIONS:
        docs = db.collection(collection).where("adventure_id", "==", adventure_id).stream()
        _batch_delete(db, docs)

    db.collection("adventures").document(adventure_id).delete()


@router.post("/adventures/{adventure_id}/invite")
async def regenerate_invite(adventure_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "admin")
    db = get_db()

    new_code = secrets.token_urlsafe(6)
    db.collection("adventures").document(adventure_id).update({"invite_code": new_code})
    return {"invite_code": new_code}


class JoinPayload(BaseModel):
    invite_code: str


@router.post("/adventures/join", status_code=201)
async def join_adventure(payload: JoinPayload, request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    adv_docs = list(
        db.collection("adventures").where("invite_code", "==", payload.invite_code).limit(1).stream()
    )
    if not adv_docs:
        raise HTTPException(404, "Invalid invite code")

    adv_doc = adv_docs[0]
    adventure_id = adv_doc.id

    existing = list(
        db.collection("members")
        .where("adventure_id", "==", adventure_id)
        .where("user_uid", "==", uid)
        .limit(1)
        .stream()
    )
    if existing:
        raise HTTPException(409, "Already a member")

    member = Member(
        adventure_id=adventure_id,
        user_uid=uid,
        role="player",
        joined_at=datetime.now(timezone.utc).isoformat(),
    )
    db.collection("members").document(member.id).set(member.model_dump())

    return {"adventure": Adventure(**adv_doc.to_dict()).model_dump(), "member": member.model_dump()}
