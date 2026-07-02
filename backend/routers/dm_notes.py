from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from ..firebase import get_db
from ..models.dm_notes import DmNotes, DmNotesUpdate
from ..utils.auth import get_current_uid, require_member

router = APIRouter()


@router.get("/adventures/{adventure_id}/dm-notes")
async def get_dm_notes(adventure_id: str, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "viewer")
    db = get_db()

    doc = db.collection("dm_notes").document(adventure_id).get()
    if not doc.exists:
        return DmNotes(
            adventure_id=adventure_id,
            public_notes="",
            updated_at=datetime.now(timezone.utc).isoformat(),
        ).model_dump()

    return DmNotes(**{**doc.to_dict(), "adventure_id": adventure_id}).model_dump()


@router.patch("/adventures/{adventure_id}/dm-notes")
async def update_dm_notes(adventure_id: str, payload: DmNotesUpdate, request: Request):
    uid = await get_current_uid(request)
    await require_member(adventure_id, uid, "admin")
    db = get_db()

    updated_at = datetime.now(timezone.utc).isoformat()
    data = {
        "adventure_id": adventure_id,
        "public_notes": payload.public_notes,
        "updated_at": updated_at,
    }
    db.collection("dm_notes").document(adventure_id).set(data)
    return DmNotes(**data).model_dump()
