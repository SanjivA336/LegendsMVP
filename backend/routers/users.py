from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from ..firebase import get_db
from ..models.user import User, UserCreate
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
        doc_ref.update({"display_name": payload.display_name})
        user = User(**{**existing, "uid": uid, "display_name": payload.display_name})
    else:
        user = User(
            uid=uid,
            email="",
            display_name=payload.display_name,
            created_at=datetime.now(timezone.utc).isoformat(),
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
