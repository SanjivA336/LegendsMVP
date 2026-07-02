from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.worldbible import WorldBible, WorldBibleCreate

router = APIRouter()


def _doc_to_bible(doc) -> WorldBible:
    return WorldBible(**(doc.to_dict() | {"id": doc.id}))


@router.post("/world-bible", response_model=WorldBible, status_code=201)
async def create_world_bible(payload: WorldBibleCreate):
    db = get_db()
    bible = WorldBible(**payload.model_dump())
    db.collection("world_bible").document(bible.id).set(bible.model_dump())
    return bible


@router.get("/world-bible", response_model=WorldBible)
async def get_world_bible(adventure_id: str):
    db = get_db()
    docs = list(
        db.collection("world_bible")
        .where("adventure_id", "==", adventure_id)
        .limit(1)
        .stream()
    )
    if not docs:
        raise HTTPException(status_code=404, detail="World bible not found")
    return _doc_to_bible(docs[0])
