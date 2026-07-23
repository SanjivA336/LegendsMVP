import time
from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.context import (
    ContextCard, ContextCardCreate, ContextCardUpdate,
    WorldState, WorldStateCreate, WorldStateFactsAppend,
    RelationshipEdge, RelationshipEdgeCreate, RelationshipEdgeUpdate,
    RelationshipMap, RippleRequest,
)

router = APIRouter()

# get_cards_for_prompt() is on the hot path of nearly every AI narration call
# (opening scene, round resolution, every combat turn, quest advancement) but
# context cards themselves only change on rare DM edits -- cache the full
# per-adventure card list briefly instead of re-streaming the collection on
# every single call. Cleared on any card write so edits still take effect
# immediately rather than waiting out the TTL.
_CARD_CACHE_TTL_SECONDS = 30
_card_cache: dict[str, tuple[float, list[ContextCard]]] = {}


def _invalidate_card_cache() -> None:
    _card_cache.clear()

WEIGHT_RANGES: dict[str, tuple[float, float]] = {
    "affinity": (-1.0, 1.0),
    "fear": (0.0, 1.0),
    "submission": (0.0, 1.0),
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _doc_to_card(doc) -> ContextCard:
    return ContextCard(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_world_state(doc) -> WorldState:
    return WorldState(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_edge(doc) -> RelationshipEdge:
    return RelationshipEdge(**(doc.to_dict() | {"id": doc.id}))


def _all_cards_for_adventure(adventure_id: str, db) -> list[ContextCard]:
    cached = _card_cache.get(adventure_id)
    if cached and (time.monotonic() - cached[0]) < _CARD_CACHE_TTL_SECONDS:
        return cached[1]

    cards = [
        _doc_to_card(d)
        for d in db.collection("context_cards").where("adventure_id", "==", adventure_id).stream()
    ]
    _card_cache[adventure_id] = (time.monotonic(), cards)
    return cards


def get_cards_for_prompt(
    adventure_id: str,
    event: str | None,
    recent_text: str,
    db,
) -> list[ContextCard]:
    all_cards = _all_cards_for_adventure(adventure_id, db)

    seen: dict[str, ContextCard] = {}
    for card in all_cards:
        if card.always_inject:
            seen[card.id] = card
        elif event and card.event_trigger == event:
            seen[card.id] = card
        elif card.keyword_trigger and card.keyword_trigger.lower() in recent_text.lower():
            seen[card.id] = card

    return list(seen.values())


# ── ContextCard Endpoints ──────────────────────────────────────────────────────

@router.post("/context-cards", response_model=ContextCard, status_code=201)
async def create_context_card(payload: ContextCardCreate):
    db = get_db()
    card = ContextCard(**payload.model_dump())
    db.collection("context_cards").document(card.id).set(card.model_dump())
    _invalidate_card_cache()
    return card


@router.get("/context-cards", response_model=list[ContextCard])
async def list_context_cards(adventure_id: str):
    db = get_db()
    return _all_cards_for_adventure(adventure_id, db)


@router.get("/context-cards/for-prompt", response_model=list[ContextCard])
async def get_context_cards_for_prompt(
    adventure_id: str,
    recent_text: str = "",
    event: str | None = None,
):
    db = get_db()
    return get_cards_for_prompt(adventure_id, event, recent_text, db)


@router.get("/context-cards/{card_id}", response_model=ContextCard)
async def get_context_card(card_id: str):
    db = get_db()
    doc = db.collection("context_cards").document(card_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Context card not found")
    return _doc_to_card(doc)


@router.patch("/context-cards/{card_id}", response_model=ContextCard)
async def update_context_card(card_id: str, updates: ContextCardUpdate):
    db = get_db()
    ref = db.collection("context_cards").document(card_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Context card not found")
    changes = {k: v for k, v in updates.model_dump().items() if v is not None}
    ref.update(changes)
    _invalidate_card_cache()
    return _doc_to_card(ref.get())


@router.delete("/context-cards/{card_id}", status_code=204)
async def delete_context_card(card_id: str):
    db = get_db()
    if not db.collection("context_cards").document(card_id).get().exists:
        raise HTTPException(status_code=404, detail="Context card not found")
    db.collection("context_cards").document(card_id).delete()
    _invalidate_card_cache()


# ── WorldState Endpoints ───────────────────────────────────────────────────────

@router.post("/world-state", response_model=WorldState, status_code=201)
async def create_world_state(payload: WorldStateCreate):
    db = get_db()
    state = WorldState(**payload.model_dump())
    db.collection("world_state").document(state.id).set(state.model_dump())
    return state


@router.get("/world-state", response_model=list[WorldState])
async def list_world_states(adventure_id: str):
    db = get_db()
    docs = db.collection("world_state").where("adventure_id", "==", adventure_id).stream()
    return [_doc_to_world_state(d) for d in docs]


@router.patch("/world-state/{state_id}/facts", response_model=WorldState)
async def append_world_state_facts(state_id: str, payload: WorldStateFactsAppend):
    db = get_db()
    ref = db.collection("world_state").document(state_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="World state not found")

    # Append new facts to the existing list rather than overwriting
    existing = doc.to_dict().get("facts", [])
    ref.update({"facts": existing + payload.facts})
    return _doc_to_world_state(ref.get())


# ── Relationship Endpoints ─────────────────────────────────────────────────────

@router.post("/relationships", response_model=RelationshipEdge, status_code=201)
async def create_relationship(payload: RelationshipEdgeCreate):
    db = get_db()
    edge = RelationshipEdge(**payload.model_dump())
    db.collection("relationships").document(edge.id).set(edge.model_dump())
    return edge


@router.get("/relationships", response_model=list[RelationshipEdge])
async def list_relationships(adventure_id: str, from_id: str | None = None, to_id: str | None = None):
    db = get_db()
    query = db.collection("relationships").where("adventure_id", "==", adventure_id)
    if from_id:
        query = query.where("from_id", "==", from_id)
    if to_id:
        query = query.where("to_id", "==", to_id)
    return [_doc_to_edge(d) for d in query.stream()]


@router.get("/relationships/map", response_model=RelationshipMap)
async def get_relationship_map(adventure_id: str):
    db = get_db()
    edges = [
        _doc_to_edge(d)
        for d in db.collection("relationships").where("adventure_id", "==", adventure_id).stream()
    ]
    # Collect unique character IDs from all edges
    nodes = list({id_ for e in edges for id_ in (e.from_id, e.to_id)})
    return RelationshipMap(nodes=nodes, edges=edges)


@router.get("/relationships/{edge_id}", response_model=RelationshipEdge)
async def get_relationship(edge_id: str):
    db = get_db()
    doc = db.collection("relationships").document(edge_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return _doc_to_edge(doc)


@router.patch("/relationships/{edge_id}", response_model=RelationshipEdge)
async def update_relationship(edge_id: str, updates: RelationshipEdgeUpdate):
    db = get_db()
    ref = db.collection("relationships").document(edge_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Relationship not found")
    changes = {k: v for k, v in updates.model_dump().items() if v is not None}
    ref.update(changes)
    return _doc_to_edge(ref.get())


@router.delete("/relationships/{edge_id}", status_code=204)
async def delete_relationship(edge_id: str):
    db = get_db()
    if not db.collection("relationships").document(edge_id).get().exists:
        raise HTTPException(status_code=404, detail="Relationship not found")
    db.collection("relationships").document(edge_id).delete()


@router.post("/relationships/ripple", response_model=list[RelationshipEdge])
async def ripple_relationship(payload: RippleRequest):
    db = get_db()
    weight = payload.weight
    lo, hi = WEIGHT_RANGES[weight]

    # Find all C→A edges (characters who have a view of A = payload.from_id)
    c_to_a_docs = (
        db.collection("relationships")
        .where("adventure_id", "==", payload.adventure_id)
        .where("to_id", "==", payload.from_id)
        .stream()
    )
    c_to_a: dict[str, RelationshipEdge] = {d.to_dict()["from_id"]: _doc_to_edge(d) for d in c_to_a_docs}

    # Find existing C→B edges so we know which ones to update
    c_to_b_docs = (
        db.collection("relationships")
        .where("adventure_id", "==", payload.adventure_id)
        .where("to_id", "==", payload.to_id)
        .stream()
    )
    c_to_b: dict[str, RelationshipEdge] = {d.to_dict()["from_id"]: _doc_to_edge(d) for d in c_to_b_docs}

    updated: list[RelationshipEdge] = []
    for c_id, c_a_edge in c_to_a.items():
        if c_id not in c_to_b:
            continue  # C doesn't know B — ripple has no effect
        c_b_edge = c_to_b[c_id]
        ripple_delta = payload.delta * c_a_edge.affinity
        old_val = getattr(c_b_edge, weight)
        new_val = max(lo, min(hi, old_val + ripple_delta))
        ref = db.collection("relationships").document(c_b_edge.id)
        ref.update({weight: new_val})
        updated.append(_doc_to_edge(ref.get()))

    return updated
