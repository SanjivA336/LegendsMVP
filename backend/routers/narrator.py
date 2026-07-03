import re
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from firebase_admin import firestore
from ..firebase import get_db
from ..ai_provider import get_provider, AIProvider
from ..routers.context import get_cards_for_prompt
from ..models.combat import Encounter, ActionRecord
from ..models.actor import Actor, AdventureActorSlot
from ..models.round import PendingRound, RoundEntry, ParticipantKind, EntryStatus, PendingCheck, CheckStatus
from ..utils.minigames import dice

router = APIRouter()

DEFAULT_SKILL_NAMES = {
    "strength": "Strength", "dexterity": "Dexterity", "intelligence": "Intelligence",
    "fortitude": "Fortitude", "charisma": "Charisma", "reflex": "Reflex",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _skill_display_name(skill_key: str, attr_names: dict) -> str:
    label = attr_names.get(skill_key) or DEFAULT_SKILL_NAMES.get(skill_key, skill_key.title())
    return f"{label} Roll"


def _result_hint(score: float) -> str:
    if score >= 0.66:
        return "succeeded decisively"
    if score > 0:
        return "succeeded"
    if score > -0.66:
        return "failed"
    return "failed badly"


# ── Opening Scene ──────────────────────────────────────────────────────────────

class OpeningSceneRequest(BaseModel):
    adventure_id: str
    character_name: str
    world_name: str


@router.post("/narrator/open")
async def opening_scene(payload: OpeningSceneRequest):
    db = get_db()
    provider = get_provider()

    cards = get_cards_for_prompt(payload.adventure_id, "adventure_started", "", db)

    bible_docs = list(
        db.collection("world_bible")
        .where("adventure_id", "==", payload.adventure_id)
        .limit(1)
        .stream()
    )
    bible = bible_docs[0].to_dict() if bible_docs else {}

    ws_docs = list(
        db.collection("world_state")
        .where("adventure_id", "==", payload.adventure_id)
        .limit(1)
        .stream()
    )
    world_facts: list[str] = ws_docs[0].to_dict().get("facts", []) if ws_docs else []

    prompt = _build_opening_prompt(payload, bible, world_facts, cards)
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    return {"narrative": result.get("narrative", "")}


# ── OOC Chat ──────────────────────────────────────────────────────────────────

class OOCRequest(BaseModel):
    adventure_id: str
    character_id: str
    player_text: str
    user_display_name: str = "the player"


@router.post("/narrator/ooc")
async def ooc_chat(payload: OOCRequest):
    """Out-of-character DM response. Nothing is persisted to Firestore."""
    db = get_db()
    provider = get_provider()

    bible_docs = list(
        db.collection("world_bible")
        .where("adventure_id", "==", payload.adventure_id)
        .limit(1)
        .stream()
    )
    bible = bible_docs[0].to_dict() if bible_docs else {}

    ws_docs = list(
        db.collection("world_state")
        .where("adventure_id", "==", payload.adventure_id)
        .limit(1)
        .stream()
    )
    world_facts: list[str] = ws_docs[0].to_dict().get("facts", []) if ws_docs else []

    notes_doc = db.collection("dm_notes").document(payload.adventure_id).get()
    public_notes: str = notes_doc.to_dict().get("public_notes", "") if notes_doc.exists else ""

    prompt = _build_ooc_prompt(
        payload.player_text,
        payload.user_display_name,
        bible,
        world_facts,
        public_notes,
    )

    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    return {"response": result.get("response", result.get("narrative", ""))}


# ── Actor Turn (legacy, unwired from frontend, left as-is) ────────────────────

class ActorTurnRequest(BaseModel):
    adventure_id: str
    encounter_id: str | None = None
    last_player_action: str


class ActorAction(BaseModel):
    actor_id: str
    character_name: str
    action: str
    narrative: str


class ActorTurnResponse(BaseModel):
    actions: list[ActorAction]
    narrative: str


_STANCE_LABELS = {1: "Pacifist", 2: "Defensive", 3: "Balanced", 4: "Aggressive", 5: "Berserker"}
_TACTICS_LABELS = {1: "Calculated", 2: "Methodical", 3: "Adaptive", 4: "Bold", 5: "Reckless"}
_DISPOSITION_LABELS = {1: "Noble", 2: "Principled", 3: "Pragmatic", 4: "Cunning", 5: "Ruthless"}


@router.post("/narrator/actor-turn", response_model=ActorTurnResponse)
async def actor_turn(payload: ActorTurnRequest):
    db = get_db()
    provider = get_provider()

    slot_docs = list(
        db.collection("adventure_actor_slots")
        .where("adventure_id", "==", payload.adventure_id)
        .stream()
    )
    if not slot_docs:
        return ActorTurnResponse(actions=[], narrative="")

    actors_data = []
    for slot_doc in slot_docs:
        slot = AdventureActorSlot(**{**slot_doc.to_dict(), "id": slot_doc.id})
        actor_doc = db.collection("actors").document(slot.actor_id).get()
        if not actor_doc.exists:
            continue
        actor = Actor(**{**actor_doc.to_dict(), "id": actor_doc.id})

        char_name = "Unknown"
        if slot.character_id:
            char_doc = db.collection("characters").document(slot.character_id).get()
            if char_doc.exists:
                char_name = char_doc.to_dict().get("name", "Unknown")

        actors_data.append({
            "slot": slot,
            "actor": actor,
            "character_name": char_name,
        })

    if not actors_data:
        return ActorTurnResponse(actions=[], narrative="")

    prompt = _build_actor_turn_prompt(payload.last_player_action, actors_data)
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    raw_actions = result.get("actions", [])
    actor_actions: list[ActorAction] = []

    for i, entry in enumerate(raw_actions):
        actor_id = actors_data[i]["slot"].actor_id if i < len(actors_data) else "unknown"
        char_name = actors_data[i]["character_name"] if i < len(actors_data) else "Unknown"
        action = ActorAction(
            actor_id=actor_id,
            character_name=char_name,
            action=entry.get("action", ""),
            narrative=entry.get("narrative", ""),
        )
        actor_actions.append(action)

        record = ActionRecord(
            adventure_id=payload.adventure_id,
            encounter_id=payload.encounter_id or "",
            actor_id=actor_id,
            action_type="narrative",
            description=action.action,
            narrative=action.narrative,
        )
        db.collection("actions").document(record.id).set(record.model_dump())

    return ActorTurnResponse(
        actions=actor_actions,
        narrative=result.get("narrative", ""),
    )


# ── Turn-Batching: Rounds ───────────────────────────────────────────────────────

class RoundSubmitRequest(BaseModel):
    adventure_id: str
    encounter_id: str | None = None
    character_id: str
    player_text: str | None = None
    passed: bool = False


class RoundSubmitResponse(BaseModel):
    encounter_id: str
    round_number: int
    resolved: bool
    narrative: str | None = None


class RoundEntryView(BaseModel):
    character_id: str
    character_name: str
    kind: ParticipantKind
    status: EntryStatus


class RoundStatusResponse(BaseModel):
    encounter_id: str
    round_number: int
    status: str
    entries: list[RoundEntryView]
    narrative: str | None = None
    resolved_at: str | None = None


class ForceResolveRequest(BaseModel):
    encounter_id: str


class ResolveCheckRequest(BaseModel):
    check_id: str
    raw_result: dict


class ResolveCheckResponse(BaseModel):
    check_id: str
    score: float
    resolved_round: bool
    narrative: str | None = None


def _get_or_create_narrative_encounter(adventure_id: str, encounter_id: str | None, db) -> Encounter:
    if encounter_id:
        enc_doc = db.collection("encounters").document(encounter_id).get()
        if enc_doc.exists:
            return Encounter(**{**enc_doc.to_dict(), "id": enc_doc.id})

    existing = list(
        db.collection("encounters")
        .where("adventure_id", "==", adventure_id)
        .where("mode", "==", "narrative")
        .where("status", "==", "active")
        .limit(1)
        .stream()
    )
    if existing:
        return Encounter(**{**existing[0].to_dict(), "id": existing[0].id})

    encounter = Encounter(adventure_id=adventure_id, mode="narrative", status="active")
    db.collection("encounters").document(encounter.id).set(encounter.model_dump())
    return encounter


def _populate_stage_ids_if_empty(encounter: Encounter, db) -> Encounter:
    if encounter.stage_ids:
        return encounter

    char_docs = list(
        db.collection("characters")
        .where("adventure_id", "==", encounter.adventure_id)
        .where("is_player", "==", True)
        .stream()
    )
    stage_ids = [d.id for d in char_docs]
    if stage_ids:
        db.collection("encounters").document(encounter.id).update({"stage_ids": stage_ids})
        encounter.stage_ids = stage_ids
    return encounter


def _find_actor_id_for_character(adventure_id: str, character_id: str, db) -> str | None:
    slot_docs = list(
        db.collection("adventure_actor_slots")
        .where("adventure_id", "==", adventure_id)
        .where("character_id", "==", character_id)
        .limit(1)
        .stream()
    )
    if not slot_docs:
        return None
    return slot_docs[0].to_dict().get("actor_id")


def _load_staged_actors(adventure_id: str, character_ids: list[str], db) -> list[dict]:
    actors_data = []
    for char_id in character_ids:
        slot_docs = list(
            db.collection("adventure_actor_slots")
            .where("adventure_id", "==", adventure_id)
            .where("character_id", "==", char_id)
            .limit(1)
            .stream()
        )
        if not slot_docs:
            continue
        slot = AdventureActorSlot(**{**slot_docs[0].to_dict(), "id": slot_docs[0].id})
        actor_doc = db.collection("actors").document(slot.actor_id).get()
        if not actor_doc.exists:
            continue
        actor = Actor(**{**actor_doc.to_dict(), "id": actor_doc.id})
        char_doc = db.collection("characters").document(char_id).get()
        char_name = char_doc.to_dict().get("name", "Unknown") if char_doc.exists else "Unknown"
        actors_data.append({"slot": slot, "actor": actor, "character_name": char_name})
    return actors_data


def _start_new_round(encounter: Encounter, db) -> PendingRound:
    entries = []
    for char_id in encounter.stage_ids:
        actor_id = _find_actor_id_for_character(encounter.adventure_id, char_id, db)
        entries.append(RoundEntry(
            character_id=char_id,
            kind="actor" if actor_id else "human",
            actor_id=actor_id,
        ))

    round_ref = db.collection("pending_rounds").document(encounter.id)
    prior = round_ref.get()
    round_number = (prior.to_dict().get("round_number", 0) + 1) if prior.exists else 1

    round_ = PendingRound(
        id=encounter.id,
        encounter_id=encounter.id,
        adventure_id=encounter.adventure_id,
        round_number=round_number,
        status="collecting",
        entries=entries,
        created_at=_now_iso(),
    )
    round_ref.set(round_.model_dump())
    return round_


@firestore.transactional
def _apply_entry_txn(transaction, round_ref, character_id: str, text: str | None, passed: bool):
    snapshot = round_ref.get(transaction=transaction)
    round_ = PendingRound(**snapshot.to_dict())

    entry = next((e for e in round_.entries if e.character_id == character_id), None)
    if entry is None or entry.status != "awaiting":
        return round_, False

    entry.status = "passed" if passed else "submitted"
    entry.text = None if passed else text
    entry.submitted_at = _now_iso()

    just_flipped = False
    if round_.status == "collecting" and all(e.status != "awaiting" for e in round_.entries):
        round_.status = "resolving"
        just_flipped = True

    transaction.set(round_ref, round_.model_dump())
    return round_, just_flipped


async def _resolve_round(round_: PendingRound, encounter: Encounter, db, provider: AIProvider) -> str:
    submitted = [e for e in round_.entries if e.status == "submitted"]

    bible_docs = list(
        db.collection("world_bible")
        .where("adventure_id", "==", encounter.adventure_id)
        .limit(1)
        .stream()
    )
    bible = bible_docs[0].to_dict() if bible_docs else {}

    ws_docs = list(
        db.collection("world_state")
        .where("adventure_id", "==", encounter.adventure_id)
        .limit(1)
        .stream()
    )
    world_facts: list[str] = ws_docs[0].to_dict().get("facts", []) if ws_docs else []

    combined_text = " ".join(e.text or "" for e in submitted)
    cards = get_cards_for_prompt(encounter.adventure_id, "narrative", combined_text, db)

    check_docs = list(
        db.collection("pending_checks")
        .where("encounter_id", "==", encounter.id)
        .where("round_number", "==", round_.round_number)
        .stream()
    )
    checks_by_char: dict[str, PendingCheck] = {}
    for d in check_docs:
        c = PendingCheck(**{**d.to_dict(), "id": d.id})
        checks_by_char[c.character_id] = c

    entries_data = []
    for e in round_.entries:
        char_doc = db.collection("characters").document(e.character_id).get()
        name = char_doc.to_dict().get("name", "Someone") if char_doc.exists else "Someone"
        check_hint = None
        check = checks_by_char.get(e.character_id)
        if check and check.score is not None:
            check_hint = _result_hint(check.score)
        entries_data.append({"name": name, "text": e.text, "passed": e.status == "passed", "check_hint": check_hint})

    prompt = _build_round_prompt(entries_data, bible, world_facts, cards)
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    dm_narrative = result.get("narrative", "")

    new_action_ids = []
    seq = 0
    for e in submitted:
        check = checks_by_char.get(e.character_id)
        dice_results: list[int] = []
        outcome = ""
        if check and check.raw_result:
            dice_results = check.raw_result.get("rolls", [])
            if check.minigame_id == "dice-roll":
                outcome = dice.tier_label(check.raw_result, check.target or 0)

        record = ActionRecord(
            adventure_id=encounter.adventure_id,
            encounter_id=encounter.id,
            actor_id=e.character_id,
            action_type="narrative",
            description=e.text or "",
            narrative=e.text or "",
            dice_results=dice_results,
            outcome=outcome,
            round_number=round_.round_number,
            sequence=seq,
        )
        db.collection("actions").document(record.id).set(record.model_dump())
        new_action_ids.append(record.id)
        seq += 1

    dm_record = ActionRecord(
        adventure_id=encounter.adventure_id,
        encounter_id=encounter.id,
        actor_id="narrator",
        action_type="narrate",
        description=dm_narrative,
        narrative=dm_narrative,
        round_number=round_.round_number,
        sequence=seq,
    )
    db.collection("actions").document(dm_record.id).set(dm_record.model_dump())
    new_action_ids.append(dm_record.id)
    seq += 1

    for npc in (result.get("npcs") or [])[:2]:
        name = (npc.get("name") or "").strip()
        speech = (npc.get("speech") or "").strip() or None
        action_text = (npc.get("action") or "").strip() or None
        if not name or (not speech and not action_text):
            continue

        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "npc"
        if speech and action_text:
            combined = f'"{speech}" {action_text}'
        elif speech:
            combined = f'"{speech}"'
        else:
            combined = action_text or ""

        npc_record = ActionRecord(
            adventure_id=encounter.adventure_id,
            encounter_id=encounter.id,
            actor_id=f"npc:{slug}",
            action_type="narrative",
            description=combined,
            narrative=combined,
            display_name=name,
            speech=speech,
            action_text=action_text,
            round_number=round_.round_number,
            sequence=seq,
        )
        db.collection("actions").document(npc_record.id).set(npc_record.model_dump())
        new_action_ids.append(npc_record.id)
        seq += 1

    db.collection("encounters").document(encounter.id).update({
        "action_ids": encounter.action_ids + new_action_ids
    })

    round_.status = "resolved"
    round_.narrative = dm_narrative
    round_.resolved_at = _now_iso()
    db.collection("pending_rounds").document(encounter.id).set(round_.model_dump())

    return dm_narrative


async def _determine_checks_and_maybe_resolve(
    round_: PendingRound, encounter: Encounter, db, provider: AIProvider
) -> str | None:
    """
    Decides which of this round's submitted actions need a skill check. If none do
    (or nothing was submitted), resolves the round immediately and returns its narrative.
    If checks are needed, creates PendingCheck docs (auto-rolling any Actor-owned ones),
    moves the round to 'awaiting_checks', and returns None -- narration happens later,
    once every check is resolved (see resolve_check).
    """
    submitted = [e for e in round_.entries if e.status == "submitted"]
    if not submitted:
        return await _resolve_round(round_, encounter, db, provider)

    bible_docs = list(
        db.collection("world_bible")
        .where("adventure_id", "==", encounter.adventure_id)
        .limit(1)
        .stream()
    )
    bible = bible_docs[0].to_dict() if bible_docs else {}
    attr_names = bible.get("attribute_names") or DEFAULT_SKILL_NAMES

    entries_data = []
    for e in submitted:
        char_doc = db.collection("characters").document(e.character_id).get()
        name = char_doc.to_dict().get("name", "Someone") if char_doc.exists else "Someone"
        entries_data.append({"character_id": e.character_id, "name": name, "text": e.text})

    prompt = _build_check_determination_prompt(entries_data, attr_names)
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception):
        result = {"checks": []}

    valid_char_ids = {e.character_id for e in submitted}
    raw_checks = [c for c in result.get("checks", []) if c.get("character_id") in valid_char_ids]

    if not raw_checks:
        return await _resolve_round(round_, encounter, db, provider)

    round_.status = "awaiting_checks"
    db.collection("pending_rounds").document(encounter.id).set(round_.model_dump())

    seen_char_ids: set[str] = set()
    for c in raw_checks:
        char_id = c["character_id"]
        if char_id in seen_char_ids:
            continue  # at most one check per action for now
        seen_char_ids.add(char_id)

        char_doc = db.collection("characters").document(char_id).get()
        char_name = char_doc.to_dict().get("name", "Someone") if char_doc.exists else "Someone"
        skill_key = c.get("skill_key") or "strength"
        target = float(c.get("target") or 12)
        show_target = bool(c.get("show_target", True))

        check = PendingCheck(
            encounter_id=encounter.id,
            round_number=round_.round_number,
            character_id=char_id,
            character_name=char_name,
            skill_key=skill_key,
            skill_name=_skill_display_name(skill_key, attr_names),
            show_target=show_target,
            target=target,
        )

        actor_id_for_char = _find_actor_id_for_character(encounter.adventure_id, char_id, db)
        if actor_id_for_char:
            # Actors only ever roll dice, and do so immediately -- no UI wait.
            raw_result, score = dice.roll_and_score(check.die_size, target, check.adv_disadv)
            check.status = "resolved"
            check.raw_result = raw_result
            check.score = score

        db.collection("pending_checks").document(check.id).set(check.model_dump())

    remaining = list(
        db.collection("pending_checks")
        .where("encounter_id", "==", encounter.id)
        .where("round_number", "==", round_.round_number)
        .where("status", "==", "pending")
        .stream()
    )
    if not remaining:
        # Every flagged check belonged to an Actor and already auto-resolved.
        return await _resolve_round(round_, encounter, db, provider)
    return None


async def _run_actor_auto_submit(adventure_id: str, encounter_id: str, round_number: int, db, provider: AIProvider):
    round_ref = db.collection("pending_rounds").document(encounter_id)
    round_doc = round_ref.get()
    if not round_doc.exists:
        return
    round_ = PendingRound(**round_doc.to_dict())
    if round_.round_number != round_number or round_.status != "collecting":
        return

    actor_char_ids = [e.character_id for e in round_.entries if e.kind == "actor" and e.status == "awaiting"]
    if not actor_char_ids:
        return

    actors_data = _load_staged_actors(adventure_id, actor_char_ids, db)
    if not actors_data:
        return

    prev_records = list(
        db.collection("actions")
        .where("encounter_id", "==", encounter_id)
        .where("actor_id", "==", "narrator")
        .stream()
    )
    prev_narrative = ""
    if prev_records:
        latest = max(prev_records, key=lambda d: d.to_dict().get("round_number", 0))
        prev_narrative = latest.to_dict().get("narrative", "")

    prompt = _build_actor_round_prompt(actors_data, prev_narrative)
    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception):
        result = {"actions": []}

    raw_actions = result.get("actions", [])
    for i, entry in enumerate(raw_actions):
        char_id = entry.get("character_id")
        valid_ids = {a["slot"].character_id for a in actors_data}
        if char_id not in valid_ids:
            char_id = actors_data[i]["slot"].character_id if i < len(actors_data) else None
        if not char_id:
            continue
        text = (entry.get("text") or "").strip()
        if not text:
            continue

        transaction = db.transaction()
        updated_round, just_flipped = _apply_entry_txn(transaction, round_ref, char_id, text, False)
        if just_flipped:
            encounter_doc = db.collection("encounters").document(encounter_id).get()
            encounter = Encounter(**{**encounter_doc.to_dict(), "id": encounter_doc.id})
            await _determine_checks_and_maybe_resolve(updated_round, encounter, db, provider)
            return


@router.post("/narrator/round/submit", response_model=RoundSubmitResponse)
async def round_submit(payload: RoundSubmitRequest, background_tasks: BackgroundTasks):
    if not payload.passed and not (payload.player_text and payload.player_text.strip()):
        raise HTTPException(400, "Provide player_text or set passed=true")

    db = get_db()
    provider = get_provider()

    encounter = _get_or_create_narrative_encounter(payload.adventure_id, payload.encounter_id, db)
    encounter = _populate_stage_ids_if_empty(encounter, db)

    round_ref = db.collection("pending_rounds").document(encounter.id)
    round_doc = round_ref.get()

    started_fresh = not round_doc.exists or round_doc.to_dict().get("status") == "resolved"
    if started_fresh:
        round_ = _start_new_round(encounter, db)
        actor_entries = [e for e in round_.entries if e.kind == "actor"]
        if actor_entries:
            background_tasks.add_task(
                _run_actor_auto_submit, payload.adventure_id, encounter.id, round_.round_number, db, provider
            )
    else:
        round_ = PendingRound(**round_doc.to_dict())

    if payload.character_id not in {e.character_id for e in round_.entries}:
        raise HTTPException(404, "Character is not part of this round")

    text = payload.player_text.strip() if payload.player_text else None
    if text and text[-1] not in ".!?":
        text += "."

    transaction = db.transaction()
    round_, just_flipped = _apply_entry_txn(transaction, round_ref, payload.character_id, text, payload.passed)

    if not just_flipped:
        return RoundSubmitResponse(encounter_id=encounter.id, round_number=round_.round_number, resolved=False)

    narrative = await _determine_checks_and_maybe_resolve(round_, encounter, db, provider)
    return RoundSubmitResponse(
        encounter_id=encounter.id, round_number=round_.round_number,
        resolved=narrative is not None, narrative=narrative
    )


@router.get("/narrator/round-status", response_model=RoundStatusResponse)
async def round_status(encounter_id: str):
    db = get_db()
    round_doc = db.collection("pending_rounds").document(encounter_id).get()
    if not round_doc.exists:
        return RoundStatusResponse(encounter_id=encounter_id, round_number=0, status="idle", entries=[])

    round_ = PendingRound(**round_doc.to_dict())
    entries_view = []
    for e in round_.entries:
        char_doc = db.collection("characters").document(e.character_id).get()
        name = char_doc.to_dict().get("name", "Someone") if char_doc.exists else "Someone"
        entries_view.append(RoundEntryView(character_id=e.character_id, character_name=name, kind=e.kind, status=e.status))

    return RoundStatusResponse(
        encounter_id=encounter_id,
        round_number=round_.round_number,
        status=round_.status,
        entries=entries_view,
        narrative=round_.narrative,
        resolved_at=round_.resolved_at,
    )


@router.post("/narrator/round/force-resolve", response_model=RoundSubmitResponse)
async def force_resolve(payload: ForceResolveRequest):
    db = get_db()
    provider = get_provider()

    round_ref = db.collection("pending_rounds").document(payload.encounter_id)
    round_doc = round_ref.get()
    if not round_doc.exists:
        raise HTTPException(404, "No active round for this encounter")

    round_ = PendingRound(**round_doc.to_dict())
    if round_.status != "collecting":
        raise HTTPException(400, "Round is not currently collecting")

    for e in round_.entries:
        if e.status == "awaiting":
            e.status = "passed"
            e.submitted_at = _now_iso()
    round_.status = "resolving"
    round_ref.set(round_.model_dump())

    encounter_doc = db.collection("encounters").document(payload.encounter_id).get()
    encounter = Encounter(**{**encounter_doc.to_dict(), "id": encounter_doc.id})
    narrative = await _resolve_round(round_, encounter, db, provider)

    return RoundSubmitResponse(
        encounter_id=payload.encounter_id, round_number=round_.round_number, resolved=True, narrative=narrative
    )


@router.get("/narrator/round-checks", response_model=list[PendingCheck])
async def round_checks(encounter_id: str, round_number: int):
    db = get_db()
    docs = list(
        db.collection("pending_checks")
        .where("encounter_id", "==", encounter_id)
        .where("round_number", "==", round_number)
        .stream()
    )
    return [PendingCheck(**{**d.to_dict(), "id": d.id}) for d in docs]


@router.post("/narrator/round/resolve-check", response_model=ResolveCheckResponse)
async def resolve_check(payload: ResolveCheckRequest):
    db = get_db()
    provider = get_provider()

    check_ref = db.collection("pending_checks").document(payload.check_id)
    check_doc = check_ref.get()
    if not check_doc.exists:
        raise HTTPException(404, "Check not found")
    check = PendingCheck(**{**check_doc.to_dict(), "id": check_doc.id})

    if check.status == "resolved":
        return ResolveCheckResponse(check_id=check.id, score=check.score or 0.0, resolved_round=False)

    target = check.target if check.target is not None else 0.0
    score = dice.score_from_raw(payload.raw_result, target)
    check_ref.update({"status": "resolved", "raw_result": payload.raw_result, "score": score})

    remaining = list(
        db.collection("pending_checks")
        .where("encounter_id", "==", check.encounter_id)
        .where("round_number", "==", check.round_number)
        .where("status", "==", "pending")
        .stream()
    )
    if remaining:
        return ResolveCheckResponse(check_id=check.id, score=score, resolved_round=False)

    round_doc = db.collection("pending_rounds").document(check.encounter_id).get()
    round_ = PendingRound(**round_doc.to_dict())
    encounter_doc = db.collection("encounters").document(check.encounter_id).get()
    encounter = Encounter(**{**encounter_doc.to_dict(), "id": encounter_doc.id})
    narrative = await _resolve_round(round_, encounter, db, provider)

    return ResolveCheckResponse(check_id=check.id, score=score, resolved_round=True, narrative=narrative)


# ── Prompt builders ────────────────────────────────────────────────────────────

def _build_opening_prompt(payload: OpeningSceneRequest, bible: dict, world_facts: list[str], cards) -> str:
    attr_names = bible.get("attribute_names", {})
    currency = bible.get("currency_name", "Gold")

    lines = [
        "You are the Dungeon Master for a tabletop RPG. Narrate the opening scene of a new adventure.",
        "",
        f"World: {payload.world_name}",
        f"Currency: {currency}",
    ]

    if attr_names:
        renamed = [f"{k} is called {v}" for k, v in attr_names.items() if v.lower() != k.lower()]
        if renamed:
            lines.append(f"Attribute names: {', '.join(renamed)}")

    if world_facts:
        lines.append("World facts:")
        for fact in world_facts[:6]:
            lines.append(f"  - {fact}")

    if cards:
        lines.append("World context:")
        for card in cards[:4]:
            lines.append(f"  [{card.label}]: {card.content}")

    lines += [
        "",
        f"The player's character is: {payload.character_name}",
        "",
        "Write 2-4 sentences that:",
        "- Place the character in a specific, vivid location",
        "- Establish atmosphere and immediate surroundings",
        "- End with a detail that invites the player to act",
        "",
        'Respond ONLY with valid JSON: {"narrative": "your narration here"}',
    ]
    return "\n".join(lines)


def _build_round_prompt(entries_data: list[dict], bible: dict, world_facts: list[str], cards) -> str:
    currency = bible.get("currency_name", "Gold")
    attr_names = bible.get("attribute_names", {})

    lines = [
        "You are the Dungeon Master for a tabletop RPG. Multiple participants acted this round.",
        "Narrate the combined outcome of ALL their actions together, considering how they interact.",
        "",
        f"Currency: {currency}",
    ]
    if attr_names:
        renamed = [f"{k} → {v}" for k, v in attr_names.items() if v.lower() != k.lower()]
        if renamed:
            lines.append(f"Attributes: {', '.join(renamed)}")

    if world_facts:
        lines.append("World state:")
        for fact in world_facts[:4]:
            lines.append(f"  - {fact}")

    if cards:
        lines.append("Context:")
        for card in cards[:3]:
            lines.append(f"  [{card.label}]: {card.content}")

    lines += ["", "This round's actions:"]
    for e in entries_data:
        if e["passed"]:
            lines.append(f"  - {e['name']}: (passed their turn)")
        elif e.get("check_hint"):
            lines.append(f"  - {e['name']}: {e['text']} — this action {e['check_hint']}")
        else:
            lines.append(f"  - {e['name']}: {e['text']}")

    lines += [
        "",
        "Write 2-4 sentences of DM narration describing what happens as a result of ALL these actions together.",
        "Stay in the world. No meta-commentary. End on a moment of tension or discovery.",
        "If it fits the scene, up to 2 NPCs may speak and/or act in reaction -- keep this rare and purposeful,",
        "not every round needs an NPC. Each NPC's speech (their own words, in quotes) and action",
        "(what they physically do, narrated in your voice) are both optional -- an NPC may only speak,",
        "only act, do both, or not appear at all.",
        "",
        "Respond ONLY with valid JSON:",
        '{"narrative": "your narration here", "npcs": [{"name": "...", "speech": "...or null", "action": "...or null"}]}',
        "Use an empty npcs list if no NPC speaks or acts this round.",
    ]
    return "\n".join(lines)


def _build_check_determination_prompt(entries_data: list[dict], attr_names: dict) -> str:
    skill_keys = list(DEFAULT_SKILL_NAMES.keys())
    lines = [
        "You are the Dungeon Master for a tabletop RPG. Multiple participants acted this round.",
        "Decide which actions are risky, uncertain, or opposed enough to require a skill check.",
        "Simple, safe, or clearly-successful actions do NOT need a check.",
        "",
        "This round's actions:",
    ]
    for e in entries_data:
        lines.append(f"  - {e['name']} (character_id: {e['character_id']}): {e['text']}")

    lines += [
        "",
        f"Available skills: {', '.join(skill_keys)}",
        "",
        "Respond ONLY with valid JSON:",
        '{"checks": [{"character_id": "...", "skill_key": "strength", "target": 12, "show_target": true}, ...]}',
        "Use an empty list if nothing needs a check.",
        "target is a difficulty number from 5 (easy) to 20 (very hard).",
        "show_target is whether the difficulty number should be revealed to the player before they roll.",
    ]
    return "\n".join(lines)


def _build_ooc_prompt(
    player_text: str,
    user_display_name: str,
    bible: dict,
    world_facts: list[str],
    public_notes: str = "",
) -> str:
    world_name = bible.get("world_name", "this world")
    lines = [
        f"You are the Dungeon Master for a tabletop RPG, speaking out-of-character with {user_display_name}.",
        "Answer their questions helpfully and honestly, like a game master would.",
        "",
        "RULES:",
        f"- Always refer to the player as {user_display_name}, never by their character's name.",
        "- Do NOT roleplay any in-world characters. You are the DM, not a character.",
        "- Only discuss things that have already happened in the adventure. No speculation about future events.",
        "- If asked about future events, unconfirmed plot, or secrets, politely deflect:",
        '  e.g. "That\'s not something I can share yet." — do not confirm or deny specifics.',
        "- For recap, lore, rules, or things that already happened: answer directly and helpfully.",
        "",
        f"World: {world_name}",
    ]

    if public_notes:
        lines.append("")
        lines.append("Confirmed events so far:")
        lines.append(public_notes)

    if world_facts:
        lines.append("")
        lines.append("Recent adventure history:")
        for fact in world_facts[:4]:
            lines.append(f"  - {fact}")

    lines += [
        "",
        f"{user_display_name} asks: {player_text}",
        "",
        "Respond conversationally in 1-3 sentences.",
        'Respond ONLY with valid JSON: {"response": "your reply here"}',
    ]
    return "\n".join(lines)


def _build_actor_turn_prompt(last_player_action: str, actors_data: list[dict]) -> str:
    lines = [
        "You are controlling multiple AI party members in a tabletop RPG.",
        "The player just took an action. Now each AI actor takes their turn.",
        "Actors may react to each other — their responses happen simultaneously.",
        "",
        f"Player's last action: {last_player_action}",
        "",
        "Actors in the party:",
    ]

    for i, entry in enumerate(actors_data):
        actor: Actor = entry["actor"]
        char_name: str = entry["character_name"]
        stance_label = _STANCE_LABELS.get(actor.stance, "Balanced")
        tactics_label = _TACTICS_LABELS.get(actor.tactics, "Adaptive")
        disposition_label = _DISPOSITION_LABELS.get(actor.disposition, "Pragmatic")

        lines.append(f"\nActor {i + 1}: {char_name}")
        lines.append(f"  Personality: {stance_label} stance, {tactics_label} tactics, {disposition_label} disposition")
        if actor.description:
            lines.append(f"  Description: {actor.description}")

    lines += [
        "",
        "For EACH actor, provide a brief action and a 1-2 sentence narration.",
        "Actors should feel distinct based on their personality axes.",
        "They may comment on each other's actions if it makes sense.",
        "",
        "Respond ONLY with valid JSON:",
        '{',
        '  "actions": [',
        '    {"action": "short action description", "narrative": "1-2 sentence narration"},',
        '    ...',
        '  ],',
        '  "narrative": "optional combined DM narration tying all actions together"',
        '}',
        f"Return exactly {len(actors_data)} action entries in the same order as the actors listed above.",
    ]
    return "\n".join(lines)


def _build_actor_round_prompt(actors_data: list[dict], prev_narrative: str) -> str:
    lines = [
        "You are controlling multiple AI party members in a tabletop RPG.",
        "Each actor is declaring their action for this round, before the DM narrates the outcome.",
    ]
    if prev_narrative:
        lines.append(f"\nWhat just happened: {prev_narrative}")

    lines.append("\nActors in the party:")
    for i, entry in enumerate(actors_data):
        actor: Actor = entry["actor"]
        char_name: str = entry["character_name"]
        char_id: str = entry["slot"].character_id
        stance_label = _STANCE_LABELS.get(actor.stance, "Balanced")
        tactics_label = _TACTICS_LABELS.get(actor.tactics, "Adaptive")
        disposition_label = _DISPOSITION_LABELS.get(actor.disposition, "Pragmatic")
        lines.append(f"\nActor {i + 1}: {char_name} (character_id: {char_id})")
        lines.append(f"  Personality: {stance_label} stance, {tactics_label} tactics, {disposition_label} disposition")
        if actor.description:
            lines.append(f"  Description: {actor.description}")

    lines += [
        "",
        "For EACH actor, decide a short in-character action they take this round.",
        "Respond ONLY with valid JSON:",
        '{"actions": [{"character_id": "...", "text": "short action description"}, ...]}',
        f"Return exactly {len(actors_data)} entries, one per actor listed above, using their exact character_id.",
    ]
    return "\n".join(lines)
