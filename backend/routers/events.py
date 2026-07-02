from fastapi import APIRouter
from ..firebase import get_db
from ..models.event import Event, FireEventRequest, FireEventResult
from ..ai_provider import get_provider
from ..utils.event_dispatch import dispatch_event

router = APIRouter()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/events", response_model=FireEventResult, status_code=201)
async def fire_event(payload: FireEventRequest):
    db = get_db()
    provider = get_provider()
    return await dispatch_event(payload, db, provider)


@router.get("/events", response_model=list[Event])
async def list_events(adventure_id: str, type: str | None = None):
    db = get_db()
    query = db.collection("events").where("adventure_id", "==", adventure_id)
    if type:
        query = query.where("type", "==", type)
    return [
        Event(**(d.to_dict() | {"id": d.id}))
        for d in query.stream()
    ]
