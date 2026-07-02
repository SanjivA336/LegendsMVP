import firebase_admin.auth
from fastapi import Request, HTTPException
from ..models.member import Member, ROLE_RANK
from ..firebase import get_db


async def get_current_uid(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "Missing auth token")
    try:
        decoded = firebase_admin.auth.verify_id_token(header[7:])
        return decoded["uid"]
    except Exception:
        raise HTTPException(401, "Invalid auth token")


async def require_member(adventure_id: str, uid: str, min_role: str) -> Member:
    db = get_db()
    docs = list(
        db.collection("members")
        .where("adventure_id", "==", adventure_id)
        .where("user_uid", "==", uid)
        .limit(1)
        .stream()
    )
    if not docs:
        raise HTTPException(403, "Not a member of this adventure")
    data = docs[0].to_dict() | {"id": docs[0].id}
    member = Member(**data)
    if ROLE_RANK.get(member.role, -1) < ROLE_RANK[min_role]:
        raise HTTPException(403, "Insufficient role")
    return member
