from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..firebase import get_db
from ..ai_provider import get_provider
from ..routers.context import get_cards_for_prompt
from ..models.combat import Encounter, ActionRecord
from ..models.actor import Actor, AdventureActorSlot

router = APIRouter()


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


# ── Narrative Action ───────────────────────────────────────────────────────────

class NarratorActRequest(BaseModel):
    adventure_id: str
    encounter_id: str | None = None
    player_text: str
    character_id: str


@router.post("/narrator/act")
async def narrator_act(payload: NarratorActRequest):
    db = get_db()
    provider = get_provider()

    # 1. Get or create narrative encounter
    encounter: Encounter | None = None
    encounter_id = payload.encounter_id

    if encounter_id:
        enc_doc = db.collection("encounters").document(encounter_id).get()
        if enc_doc.exists:
            encounter = Encounter(**enc_doc.to_dict())

    if encounter is None:
        encounter = Encounter(
            adventure_id=payload.adventure_id,
            mode="narrative",
            status="active",
        )
        db.collection("encounters").document(encounter.id).set(encounter.model_dump())
        encounter_id = encounter.id

    # 2. Build player action text (auto-add period if missing punctuation)
    player_text = payload.player_text.strip()
    if player_text and player_text[-1] not in ".!?":
        player_text += "."

    player_action = ActionRecord(
        adventure_id=payload.adventure_id,
        encounter_id=encounter_id,
        actor_id=payload.character_id,
        action_type="narrative",
        description=player_text,
        narrative=player_text,
    )
    db.collection("actions").document(player_action.id).set(player_action.model_dump())

    # 3. Fetch context for DM prompt
    cards = get_cards_for_prompt(payload.adventure_id, "narrative", player_text, db)

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

    char_doc = db.collection("characters").document(payload.character_id).get()
    char_name = char_doc.to_dict().get("name", "The hero") if char_doc.exists else "The hero"

    prompt = _build_act_prompt(player_text, char_name, bible, world_facts, cards)

    try:
        result = await provider.generate(prompt)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=502, detail=f"AI provider error: {exc}") from exc

    dm_narrative = result.get("narrative", "")

    # 4. Persist DM response as an action record
    dm_action = ActionRecord(
        adventure_id=payload.adventure_id,
        encounter_id=encounter_id,
        actor_id="narrator",
        action_type="narrate",
        description=dm_narrative,
        narrative=dm_narrative,
    )
    db.collection("actions").document(dm_action.id).set(dm_action.model_dump())

    # 5. Append both action IDs to the encounter
    db.collection("encounters").document(encounter_id).update({
        "action_ids": encounter.action_ids + [player_action.id, dm_action.id]
    })

    return {"encounter_id": encounter_id, "narrative": dm_narrative}


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


# ── Actor Turn ─────────────────────────────────────────────────────────────────

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


def _build_act_prompt(
    player_text: str, char_name: str, bible: dict, world_facts: list[str], cards
) -> str:
    currency = bible.get("currency_name", "Gold")
    attr_names = bible.get("attribute_names", {})

    lines = [
        "You are the Dungeon Master for a tabletop RPG. A player has taken an action. Respond with vivid, grounded narration.",
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

    lines += [
        "",
        f"Character: {char_name}",
        f"Player action: {player_text}",
        "",
        "Write 1-3 sentences of DM narration describing what happens as a result.",
        "Stay in the world. No meta-commentary. End on a moment of tension or discovery.",
        "",
        'Respond ONLY with valid JSON: {"narrative": "your narration here"}',
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
