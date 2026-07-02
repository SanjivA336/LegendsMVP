import random

from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.quest import (
    Quest, QuestCreate, QuestUpdate, QuestStep, QuestStepUpdate,
    ResolveStepRequest, ResolveStepResult, _MIDDLE_RANGES,
)
from ..models.context import WorldState
from ..ai_provider import get_provider
from ..utils.quest_prompts import build_quest_creation_prompt, build_step_resolution_prompt
from ..utils.quest_state import (
    doc_to_quest, get_active_step, needs_next_step,
    advance_after_completion, advance_after_failure,
    _create_character_stub, _mark_step_in_quest, _parse_quest_step, _get_world_state,
)
from ..routers.context import get_cards_for_prompt

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_quest_meta_event(adventure_id: str, event_type: str, quest_id: str, db) -> None:
    from ..models.event import Event
    meta = Event(adventure_id=adventure_id, type=event_type, quest_id=quest_id)
    db.collection("events").document(meta.id).set(meta.model_dump())


def _find_step(quest: Quest, step_id: str) -> QuestStep | None:
    candidates = [quest.first_step, quest.last_step] + quest.middle_steps
    return next((s for s in candidates if s.id == step_id), None)


# ── Quest Endpoints ────────────────────────────────────────────────────────────

@router.post("/quests", response_model=Quest, status_code=201)
async def create_quest(payload: QuestCreate):
    db = get_db()
    provider = get_provider()

    cards = get_cards_for_prompt(payload.adventure_id, "quest_created", "", db)
    world_state = _get_world_state(payload.adventure_id, db)

    lo, hi = _MIDDLE_RANGES[payload.length]
    target_middle_count = random.randint(lo, hi)

    prompt = build_quest_creation_prompt(
        payload.length, payload.context_hint, cards, world_state
    )
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(502, f"AI provider error during quest generation: {exc}") from exc
    updates = result.get("updates", {})
    new_quest_data = updates.get("new_quest", {})

    if not new_quest_data or "title" not in new_quest_data:
        raise HTTPException(500, "DM did not return a valid quest structure")

    first_step = _parse_quest_step(
        new_quest_data.get("first_step", {}), status="active"
    )
    last_step = _parse_quest_step(
        new_quest_data.get("last_step", {}), status="pending"
    )

    quest = Quest(
        adventure_id=payload.adventure_id,
        title=new_quest_data.get("title", "Untitled Quest"),
        length=payload.length,
        target_middle_count=target_middle_count,
        first_step=first_step,
        last_step=last_step,
    )

    db.collection("quests").document(quest.id).set(quest.model_dump())

    for entity in new_quest_data.get("entities_to_create", []):
        _create_character_stub(entity, payload.adventure_id, db)

    _write_quest_meta_event(payload.adventure_id, "quest_created", quest.id, db)

    return quest


@router.get("/quests", response_model=list[Quest])
async def list_quests(adventure_id: str, status: str | None = None):
    db = get_db()
    query = db.collection("quests").where("adventure_id", "==", adventure_id)
    if status:
        query = query.where("status", "==", status)
    return [doc_to_quest(d) for d in query.stream()]


@router.get("/quests/{quest_id}/active-step", response_model=QuestStep)
async def get_active_step_endpoint(quest_id: str):
    db = get_db()
    doc = db.collection("quests").document(quest_id).get()
    if not doc.exists:
        raise HTTPException(404, "Quest not found")
    quest = doc_to_quest(doc)
    step = get_active_step(quest)
    if step is None:
        raise HTTPException(404, "No active step")
    return step


@router.post("/quests/{quest_id}/resolve-step", response_model=ResolveStepResult)
async def resolve_step(quest_id: str, payload: ResolveStepRequest):
    """LLM fallback endpoint — only valid when the active step has completion_event = None."""
    db = get_db()
    doc = db.collection("quests").document(quest_id).get()
    if not doc.exists:
        raise HTTPException(404, "Quest not found")
    quest = doc_to_quest(doc)

    active_step = get_active_step(quest)
    if active_step is None:
        raise HTTPException(404, "No active step")
    if active_step.completion_event is not None:
        raise HTTPException(
            400,
            "This step uses event-based completion. Fire an event via POST /events instead.",
        )

    provider = get_provider()
    cards = get_cards_for_prompt(quest.adventure_id, None, payload.recent_context, db)
    # Use the world_state_id to fetch world state
    ws_doc = db.collection("world_state").document(payload.world_state_id).get()
    world_state = None
    if ws_doc.exists:
        world_state = WorldState(**(ws_doc.to_dict() | {"id": ws_doc.id}))

    prompt = build_step_resolution_prompt(active_step, quest, payload.recent_context, cards, world_state)
    result = await provider.generate(prompt)
    updates = result.get("updates", {})
    narrative = result.get("narrative", "")

    step_complete = updates.get("quest_step_complete", False)
    if not step_complete:
        return ResolveStepResult(
            quest=quest,
            step_completed=False,
            narrative=narrative,
        )

    narrative_on_complete = updates.get("narrative_on_complete") or narrative

    quest = await advance_after_completion(
        quest,
        active_step,
        event_type=None,
        narrative_on_complete=narrative_on_complete,
        db=db,
        provider=provider,
    )
    db.collection("quests").document(quest.id).set(quest.model_dump())

    if quest.status == "completed":
        _write_quest_meta_event(quest.adventure_id, "quest_completed", quest.id, db)
    else:
        _write_quest_meta_event(quest.adventure_id, "quest_step_completed", quest.id, db)

    return ResolveStepResult(
        quest=quest,
        step_completed=True,
        narrative=narrative,
        quest_completed=(quest.status == "completed"),
    )


@router.post("/quests/{quest_id}/fail-step", response_model=Quest)
async def fail_step(quest_id: str):
    """Manually fail the currently active step and trigger buffer recovery if needed."""
    db = get_db()
    doc = db.collection("quests").document(quest_id).get()
    if not doc.exists:
        raise HTTPException(404, "Quest not found")
    quest = doc_to_quest(doc)

    active_step = get_active_step(quest)
    if active_step is None:
        raise HTTPException(404, "No active step to fail")

    provider = get_provider()
    quest = await advance_after_failure(quest, active_step, db, provider)
    db.collection("quests").document(quest.id).set(quest.model_dump())

    if quest.status == "failed":
        _write_quest_meta_event(quest.adventure_id, "quest_failed", quest.id, db)
    else:
        _write_quest_meta_event(quest.adventure_id, "quest_step_failed", quest.id, db)

    return quest


@router.get("/quests/{quest_id}", response_model=Quest)
async def get_quest(quest_id: str):
    db = get_db()
    doc = db.collection("quests").document(quest_id).get()
    if not doc.exists:
        raise HTTPException(404, "Quest not found")
    return doc_to_quest(doc)


@router.patch("/quests/{quest_id}", response_model=Quest)
async def update_quest(quest_id: str, payload: QuestUpdate):
    db = get_db()
    ref = db.collection("quests").document(quest_id)
    if not ref.get().exists:
        raise HTTPException(404, "Quest not found")
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if changes:
        ref.update(changes)
    return doc_to_quest(ref.get())


@router.delete("/quests/{quest_id}", status_code=204)
async def delete_quest(quest_id: str):
    db = get_db()
    ref = db.collection("quests").document(quest_id)
    if not ref.get().exists:
        raise HTTPException(404, "Quest not found")
    ref.delete()


@router.patch("/quests/{quest_id}/steps/{step_id}", response_model=Quest)
async def update_step(quest_id: str, step_id: str, payload: QuestStepUpdate):
    """Manual override for a specific step. Triggers progression side-effects if needed."""
    db = get_db()
    doc = db.collection("quests").document(quest_id).get()
    if not doc.exists:
        raise HTTPException(404, "Quest not found")
    quest = doc_to_quest(doc)

    step = _find_step(quest, step_id)
    if step is None:
        raise HTTPException(404, "Step not found")

    new_status = payload.status

    if new_status == "completed":
        # Apply the update then run progression logic without DM next-step generation
        _mark_step_in_quest(
            quest,
            step_id,
            status="completed",
            narrative_on_complete=payload.narrative_on_complete,
        )
        is_last = (step_id == quest.last_step.id)
        if is_last:
            quest.status = "completed"
            _write_quest_meta_event(quest.adventure_id, "quest_completed", quest.id, db)
        elif not needs_next_step(quest):
            quest.last_step.status = "active"
        # If needs_next_step: leave it — caller must fire event or call resolve-step
        db.collection("quests").document(quest.id).set(quest.model_dump())

    elif new_status == "failed":
        # Apply the update then run the full failure / buffer-recovery logic
        provider = get_provider()
        quest = await advance_after_failure(quest, step, db, provider)
        db.collection("quests").document(quest.id).set(quest.model_dump())
        if quest.status == "failed":
            _write_quest_meta_event(quest.adventure_id, "quest_failed", quest.id, db)
        else:
            _write_quest_meta_event(quest.adventure_id, "quest_step_failed", quest.id, db)

    else:
        # Generic field update (narrative_on_complete, status → pending, etc.)
        changes: dict = {}
        if payload.status is not None:
            changes["status"] = payload.status
        if payload.narrative_on_complete is not None:
            changes["narrative_on_complete"] = payload.narrative_on_complete
        _mark_step_in_quest(quest, step_id, **changes)
        db.collection("quests").document(quest.id).set(quest.model_dump())

    return doc_to_quest(db.collection("quests").document(quest.id).get())
