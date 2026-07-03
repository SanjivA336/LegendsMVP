from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from ..firebase import get_db
from ..models.member import Member, MemberCreate, MemberUpdate, ROLE_RANK
from ..utils.auth import get_current_uid, require_member

router = APIRouter()


@router.get("/adventures/{adventure_id}/members")
async def list_members(adventure_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "viewer")
    db = get_db()

    docs = db.collection("members").where("adventure_id", "==", adventure_id).stream()
    return [Member(**{**d.to_dict(), "id": d.id}).model_dump() for d in docs]


@router.post("/adventures/{adventure_id}/members", status_code=201)
async def add_member(adventure_id: str, payload: MemberCreate, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "admin")

    if payload.role == "owner":
        raise HTTPException(400, "Use the ownership transfer endpoint to grant ownership")

    db = get_db()
    existing = list(
        db.collection("members")
        .where("adventure_id", "==", adventure_id)
        .where("user_uid", "==", payload.user_uid)
        .limit(1)
        .stream()
    )
    if existing:
        raise HTTPException(409, "User is already a member")

    member = Member(
        adventure_id=adventure_id,
        user_uid=payload.user_uid,
        role=payload.role,
        character_id=payload.character_id,
        joined_at=datetime.now(timezone.utc).isoformat(),
    )
    db.collection("members").document(member.id).set(member.model_dump())
    return member.model_dump()


@router.patch("/adventures/{adventure_id}/members/{member_id}")
async def update_member(adventure_id: str, member_id: str, payload: MemberUpdate, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "admin")
    db = get_db()

    doc = db.collection("members").document(member_id).get()
    if not doc.exists:
        raise HTTPException(404, "Member not found")

    target = Member(**{**doc.to_dict(), "id": doc.id})

    if target.adventure_id != adventure_id:
        raise HTTPException(404, "Member not found")
    if target.user_uid == uid and payload.role is not None:
        raise HTTPException(403, "Cannot change your own role")
    if target.role == "owner" and payload.role is not None:
        raise HTTPException(403, "Cannot change the owner's role")
    if payload.role == "owner":
        raise HTTPException(400, "Use the ownership transfer endpoint to grant ownership")

    updates: dict = {}
    if payload.role is not None:
        updates["role"] = payload.role
    if payload.character_id is not None:
        updates["character_id"] = payload.character_id

    if updates:
        db.collection("members").document(member_id).update(updates)

    return Member(**{**doc.to_dict(), **updates, "id": member_id}).model_dump()


@router.delete("/adventures/{adventure_id}/members/{member_id}", status_code=204)
async def remove_member(adventure_id: str, member_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "admin")
    db = get_db()

    doc = db.collection("members").document(member_id).get()
    if not doc.exists:
        raise HTTPException(404, "Member not found")

    target = Member(**{**doc.to_dict(), "id": doc.id})

    if target.adventure_id != adventure_id:
        raise HTTPException(404, "Member not found")
    if target.role == "owner":
        raise HTTPException(403, "Cannot remove the owner")

    db.collection("members").document(member_id).delete()


@router.post("/adventures/{adventure_id}/members/{member_id}/transfer-ownership")
async def transfer_ownership(adventure_id: str, member_id: str, request: Request):
    uid = await get_current_uid(request)
    caller = await require_member(adventure_id, uid, "owner")
    db = get_db()

    doc = db.collection("members").document(member_id).get()
    if not doc.exists:
        raise HTTPException(404, "Member not found")

    target = Member(**{**doc.to_dict(), "id": doc.id})

    if target.adventure_id != adventure_id:
        raise HTTPException(404, "Member not found")
    if target.user_uid == uid:
        raise HTTPException(400, "You are already the owner")
    if target.role == "owner":
        raise HTTPException(400, "Member is already the owner")

    batch = db.batch()
    batch.update(db.collection("members").document(caller.id), {"role": "admin"})
    batch.update(db.collection("members").document(target.id), {"role": "owner"})
    batch.commit()

    return {
        "previous_owner": {**caller.model_dump(), "role": "admin"},
        "new_owner": {**target.model_dump(), "role": "owner"},
    }
