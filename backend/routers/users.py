from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from ..firebase import get_db
from ..models.user import User, UserCreate, UserPreferences
from ..utils.auth import get_current_uid

router = APIRouter()


@router.post("/users/me", response_model=User, status_code=200)
async def upsert_user(payload: UserCreate, request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()

    if doc.exists:
        existing = doc.to_dict()
        updates = payload.model_dump(exclude_unset=True, exclude_none=True)
        if payload.preferences is not None:
            updates["preferences"] = payload.preferences.model_dump()
        if updates:
            doc_ref.update(updates)
        user = User(**{**existing, **updates, "uid": uid})
    else:
        if not payload.display_name:
            raise HTTPException(400, "display_name is required to create a user")
        user = User(
            uid=uid,
            email="",
            display_name=payload.display_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            preferences=payload.preferences or UserPreferences(),
        )
        doc_ref.set(user.model_dump())

    return user


@router.get("/users/me", response_model=User)
async def get_current_user(request: Request):
    uid = await get_current_uid(request)
    db = get_db()

    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        raise HTTPException(404, "User not found")

    data = doc.to_dict() | {"uid": uid}
    return User(**data)
