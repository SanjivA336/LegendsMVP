"""
Shared event dispatch logic used by both routers/events.py and routers/combat.py.

Writes the event to Firestore and checks all active quest steps for matches.
Extracted here to avoid duplicating ~40 lines of quest-check logic across routers.
"""

from ..models.event import Event, FireEventRequest, FireEventResult, _META_EVENT_TYPES
from ..utils.quest_prompts import event_matches_condition
from ..utils.quest_state import (
    doc_to_quest, get_active_step, advance_after_completion, advance_after_failure,
)


def _write_meta_event(adventure_id: str, event_type: str, quest_id: str, db) -> None:
    meta = Event(adventure_id=adventure_id, type=event_type, quest_id=quest_id)
    db.collection("events").document(meta.id).set(meta.model_dump())


async def dispatch_event(
    payload: FireEventRequest,
    db,
    provider,
    *,
    existing_event_id: str | None = None,
) -> FireEventResult:
    """Write a game event to Firestore and check all active quest steps for matches.

    Args:
        payload: The event to fire.
        db: Firestore client.
        provider: AI provider (used by quest advancement if a new step must be generated).
        existing_event_id: If the event was already written by the caller (e.g. events router),
            pass its ID to skip the write. Defaults to None (this function writes it).

    Returns:
        FireEventResult with the event ID and lists of quest IDs that advanced or failed.
    """
    if existing_event_id is None:
        event = Event(**payload.model_dump())
        db.collection("events").document(event.id).set(event.model_dump())
        event_id = event.id
    else:
        event_id = existing_event_id

    # Meta-events are logged but never trigger quest step matching
    if payload.type in _META_EVENT_TYPES:
        return FireEventResult(event_id=event_id)

    quest_docs = (
        db.collection("quests")
        .where("adventure_id", "==", payload.adventure_id)
        .where("status", "==", "active")
        .stream()
    )
    quests = [doc_to_quest(d) for d in quest_docs]

    quests_advanced: list[str] = []
    quests_failed: list[str] = []

    for quest in quests:
        active_step = get_active_step(quest)
        if active_step is None:
            continue

        ref = db.collection("quests").document(quest.id)

        # ── Failure check (takes priority) ─────────────────────────────────
        if (
            active_step.failure_event is not None
            and event_matches_condition(payload, active_step.failure_event)
        ):
            quest = await advance_after_failure(quest, active_step, db, provider)
            ref.set(quest.model_dump())
            if quest.status == "failed":
                _write_meta_event(payload.adventure_id, "quest_failed", quest.id, db)
                quests_failed.append(quest.id)
            else:
                _write_meta_event(payload.adventure_id, "quest_step_failed", quest.id, db)
            continue

        # ── Completion check ────────────────────────────────────────────────
        if (
            active_step.completion_event is None
            or not event_matches_condition(payload, active_step.completion_event)
        ):
            continue

        if active_step.completion_event.quantity > 1:
            existing_count = len(list(
                db.collection("events")
                .where("adventure_id", "==", payload.adventure_id)
                .where("type", "==", payload.type)
                .stream()
            ))
            if existing_count < active_step.completion_event.quantity:
                continue

        quest = await advance_after_completion(
            quest,
            active_step,
            event_type=payload.type,
            narrative_on_complete=None,
            db=db,
            provider=provider,
        )
        ref.set(quest.model_dump())

        if quest.status == "completed":
            _write_meta_event(payload.adventure_id, "quest_completed", quest.id, db)
        else:
            _write_meta_event(payload.adventure_id, "quest_step_completed", quest.id, db)
        quests_advanced.append(quest.id)

    return FireEventResult(
        event_id=event_id,
        quests_advanced=quests_advanced,
        quests_failed=quests_failed,
    )
