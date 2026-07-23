"""
Pure and async helpers for quest state transitions.

Imported by both events.py and quests.py routers to share step completion
and failure logic without creating a circular import.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.quest import Quest, QuestStep
    from ..models.event import EventCondition

from ..models.quest import QuestStep, FAILURE_BUFFER
from ..models.event import EventCondition
from ..models.context import WorldState
from ..models.blueprint import Instance, CustomField, merge_fields, default_fields_for_kind
from ..models.shared import new_id
from .quest_prompts import build_next_step_prompt, build_recovery_steps_prompt
from ..routers.context import get_cards_for_prompt


# ── Firestore Helpers ─────────────────────────────────────────────────────────

def doc_to_quest(doc) -> "Quest":
    from ..models.quest import Quest
    return Quest(**(doc.to_dict() | {"id": doc.id}))


def _get_world_state(adventure_id: str, db) -> WorldState | None:
    docs = list(
        db.collection("world_state")
        .where("adventure_id", "==", adventure_id)
        .limit(1)
        .stream()
    )
    if not docs:
        return None
    return WorldState(**(docs[0].to_dict() | {"id": docs[0].id}))


def _create_character_stub(entity: dict, adventure_id: str, db) -> None:
    """Create a minimal NPC character (kind="character" Instance) for a quest-referenced
    entity. Fields must be fully self-sufficient here (no template lookup happens when
    a character is read back), so every required field gets a real value directly.
    """
    raw_id = entity.get("suggested_id")
    # LLMs sometimes return suggested_id as an integer — always coerce to string
    suggested = str(raw_id).strip() if raw_id is not None else None
    role = entity.get("role", "")
    own_fields = [
        CustomField(key="name", field_type="string", value=entity.get("name", "Unknown"), required=True),
        CustomField(key="description", field_type="string", value=role),
        CustomField(key="is_player", field_type="boolean", value=False, bound_behavior="is_player"),
        CustomField(key="hp", field_type="number", value=10, required=True, bound_behavior="hp"),
        CustomField(key="max_hp", field_type="number", value=10, required=True, bound_behavior="max_hp"),
    ]
    fields = merge_fields(default_fields_for_kind("character"), own_fields)
    instance = Instance(
        id=suggested or new_id(),
        adventure_id=adventure_id,
        kind="character",
        fields=fields,
        metadata={"role": role},
    )
    db.collection("instances").document(instance.id).set(instance.model_dump())


def _parse_quest_step(data: dict, status: str = "pending") -> QuestStep:
    """Parse a DM response dict into a QuestStep, gracefully handling bad event data."""
    cond_data = data.get("completion_event")
    completion_event = None
    if cond_data and isinstance(cond_data, dict) and "type" in cond_data:
        try:
            completion_event = EventCondition(**cond_data)
        except Exception:
            pass

    failure_data = data.get("failure_event")
    failure_event = None
    if failure_data and isinstance(failure_data, dict) and "type" in failure_data:
        try:
            failure_event = EventCondition(**failure_data)
        except Exception:
            pass

    return QuestStep(
        description=data.get("description", ""),
        completion_condition=data.get("completion_condition", ""),
        completion_event=completion_event,
        failure_event=failure_event,
        status=status,
    )


# ── Pure State Helpers ────────────────────────────────────────────────────────

def get_active_step(quest: "Quest") -> QuestStep | None:
    """Return the currently active step, or None if no step is active."""
    if quest.first_step.status == "active":
        return quest.first_step
    if quest.first_step.status == "completed":
        for step in quest.middle_steps:
            if step.status == "active":
                return step
        if quest.last_step.status == "active":
            return quest.last_step
    # Also handle last_step active even if first_step hasn't been explicitly completed
    # (edge case for manual overrides)
    if quest.last_step.status == "active":
        return quest.last_step
    return None


def needs_next_step(quest: "Quest") -> bool:
    """Return True if more middle steps should be generated before activating last_step."""
    return len(quest.middle_steps) < quest.target_middle_count


def count_remaining_buffer(quest: "Quest", after_step_id: str) -> int:
    """Count pending/active middle steps between after_step_id and last_step."""
    all_middles = quest.middle_steps
    found = False
    count = 0
    for step in all_middles:
        if found and step.status in ("pending", "active"):
            count += 1
        if step.id == after_step_id:
            found = True
    # If failed step is first_step, count all pending/active middles
    if not found and quest.first_step.id == after_step_id:
        count = sum(1 for s in all_middles if s.status in ("pending", "active"))
    return count


def _activate_next_pending(quest: "Quest", after_step_id: str) -> None:
    """Set the first 'pending' step after after_step_id to 'active'."""
    all_steps = [quest.first_step] + quest.middle_steps + [quest.last_step]
    found = False
    for step in all_steps:
        if found and step.status == "pending":
            step.status = "active"
            return
        if step.id == after_step_id:
            found = True


def _mark_step_in_quest(quest: "Quest", step_id: str, **kwargs) -> bool:
    """Apply field updates to the step with the given ID. Returns True if found."""
    candidates = [quest.first_step, quest.last_step] + quest.middle_steps
    for step in candidates:
        if step.id == step_id:
            for k, v in kwargs.items():
                setattr(step, k, v)
            return True
    return False


# ── Async State Transitions ───────────────────────────────────────────────────

async def advance_after_completion(
    quest: "Quest",
    active_step: QuestStep,
    event_type: str | None,
    narrative_on_complete: str | None,
    db,
    provider,
) -> "Quest":
    """Mark active_step as completed and advance the quest.

    If the next middle step needs to be generated, calls the DM (async).
    Returns the mutated quest — caller is responsible for writing to Firestore.
    """
    _mark_step_in_quest(
        quest,
        active_step.id,
        status="completed",
        narrative_on_complete=narrative_on_complete,
    )

    is_last = (active_step.id == quest.last_step.id)
    if is_last:
        quest.status = "completed"
        return quest

    if needs_next_step(quest):
        cards = get_cards_for_prompt(quest.adventure_id, event_type, "", db)
        world_state = _get_world_state(quest.adventure_id, db)
        completed = [s for s in [quest.first_step] + quest.middle_steps if s.status == "completed"]
        prompt = build_next_step_prompt(quest, completed, event_type or "", cards, world_state)
        result = await provider.generate(prompt)
        updates = result.get("updates", {})

        step_data = updates.get("new_quest_step")
        if step_data and isinstance(step_data, dict):
            new_step = _parse_quest_step(step_data, status="active")
            quest.middle_steps.append(new_step)

        for entity in updates.get("entities_to_create", []):
            _create_character_stub(entity, quest.adventure_id, db)
    else:
        quest.last_step.status = "active"

    return quest


async def advance_after_failure(
    quest: "Quest",
    failed_step: QuestStep,
    db,
    provider,
) -> "Quest":
    """Mark failed_step as failed and apply the buffer recovery mechanism.

    If fewer than FAILURE_BUFFER steps remain before last_step, generates
    recovery steps via DM. Returns the mutated quest — caller writes to Firestore.
    """
    _mark_step_in_quest(quest, failed_step.id, status="failed")

    is_last = (failed_step.id == quest.last_step.id)
    if is_last:
        quest.status = "failed"
        return quest

    remaining = count_remaining_buffer(quest, failed_step.id)
    buffer_needed = max(0, FAILURE_BUFFER - remaining)

    if buffer_needed > 0:
        cards = get_cards_for_prompt(quest.adventure_id, "quest_step_failed", "", db)
        world_state = _get_world_state(quest.adventure_id, db)
        prompt = build_recovery_steps_prompt(failed_step, quest, buffer_needed, cards, world_state)
        result = await provider.generate(prompt)
        updates = result.get("updates", {})

        recovery_data = updates.get("recovery_steps", [])
        recovery_steps = [_parse_quest_step(d) for d in recovery_data if isinstance(d, dict)]
        if recovery_steps:
            recovery_steps[0].status = "active"

        for entity in updates.get("entities_to_create", []):
            _create_character_stub(entity, quest.adventure_id, db)

        if quest.first_step.id == failed_step.id:
            quest.middle_steps = recovery_steps + quest.middle_steps
        else:
            idx = next(
                (i for i, s in enumerate(quest.middle_steps) if s.id == failed_step.id), -1
            )
            if idx >= 0:
                quest.middle_steps = (
                    quest.middle_steps[: idx + 1]
                    + recovery_steps
                    + quest.middle_steps[idx + 1 :]
                )
            else:
                quest.middle_steps.extend(recovery_steps)
    else:
        _activate_next_pending(quest, failed_step.id)

    return quest
