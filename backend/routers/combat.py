import random
from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..models.combat import (
    Arena, ArenaCombatant, ArenaTile, ArenaObject,
    Encounter, EncounterCreate, EncounterUpdate,
    ActionRecord, StartCombatRequest, PlayerTurnRequest,
    EndCombatRequest, TurnResult,
)
from ..models.event import FireEventRequest
from ..models.character import Character, character_from_instance, character_name_from_doc, write_character_field
from ..models.blueprint import Instance, Template, CustomField, resolve_instance, get_field, parse_dice_notation
from ..ai_provider import get_provider
from ..utils.combat_ai import npc_decide_action, apply_alpha_phase, _effective_edge, _DIRS, _OPPOSITE
from ..utils.combat_prompts import (
    build_arena_generation_prompt, build_action_narration_prompt, build_combat_end_prompt,
)
from ..utils.event_dispatch import dispatch_event
from ..utils.quest_state import _get_world_state
from ..utils.minigames import dice
from ..routers.context import get_cards_for_prompt

router = APIRouter()

# In-memory arena store. Encampment arenas are also mirrored to Firestore.
_ARENAS: dict[str, Arena] = {}  # encounter_id → Arena


# ── Arena Construction Helpers ─────────────────────────────────────────────────

_DIR_NAMES: dict[str, int] = {"north": 0, "east": 1, "south": 2, "west": 3}


def _blank_grid(width: int, height: int) -> list[list[ArenaTile]]:
    return [[ArenaTile() for _ in range(width)] for _ in range(height)]


def _mirror_edges(tiles: list[list[ArenaTile]], width: int, height: int) -> None:
    """Enforce edge consistency: both sides of every barrier must agree."""
    for y in range(height):
        for x in range(width):
            for d, (dx, dy) in enumerate(_DIRS):
                level = tiles[y][x].edges[d]
                if level == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    tiles[ny][nx].edges[_OPPOSITE[d]] = max(
                        tiles[ny][nx].edges[_OPPOSITE[d]], level
                    )


def _validate_connectivity(tiles: list[list[ArenaTile]], width: int, height: int) -> None:
    """Flood-fill from first passable tile; make unreachable passable tiles impassable."""
    start = next(
        ((x, y) for y in range(height) for x in range(width) if tiles[y][x].passable),
        None,
    )
    if start is None:
        return

    visited: set[tuple[int, int]] = {start}
    queue: list[tuple[int, int]] = [start]
    while queue:
        cx, cy = queue.pop(0)
        for dx, dy in _DIRS:
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in visited:
                continue
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if tiles[ny][nx].passable:
                visited.add((nx, ny))
                queue.append((nx, ny))

    for y in range(height):
        for x in range(width):
            if tiles[y][x].passable and (x, y) not in visited:
                tiles[y][x].passable = False


def _parse_arena_from_llm(result: dict, width: int, height: int, indoor: bool) -> tuple[list[list[ArenaTile]], list[ArenaObject]]:
    """Parse the LLM's sparse arena description into a full tile grid and object list."""
    arena_data = result.get("updates", {}).get("arena", {})
    tiles = _blank_grid(width, height)

    for tile_data in arena_data.get("tiles", []):
        x, y = tile_data.get("x", 0), tile_data.get("y", 0)
        if not (0 <= x < width and 0 <= y < height):
            continue
        t = tiles[y][x]
        if "passable" in tile_data:
            t.passable = tile_data["passable"]
        if "terrain_tag" in tile_data:
            t.terrain_tag = tile_data["terrain_tag"]
        if "movement_cost" in tile_data:
            t.movement_cost = int(tile_data["movement_cost"])
        if "aura" in tile_data:
            t.aura = tile_data["aura"]
        if "hazard" in tile_data:
            t.hazard = int(tile_data["hazard"])

    for edge_data in arena_data.get("edges", []):
        x, y = edge_data.get("x", 0), edge_data.get("y", 0)
        dir_name = edge_data.get("direction", "north")
        level = int(edge_data.get("level", 0))
        if not (0 <= x < width and 0 <= y < height):
            continue
        d = _DIR_NAMES.get(dir_name, 0)
        tiles[y][x].edges[d] = level

    # Mirror edges for consistency
    _mirror_edges(tiles, width, height)

    objects: list[ArenaObject] = []
    for obj_data in arena_data.get("objects", []):
        x, y = obj_data.get("x", 0), obj_data.get("y", 0)
        obj_type = obj_data.get("type", "bulwark")
        if not (0 <= x < width and 0 <= y < height):
            continue
        obj = ArenaObject(x=x, y=y, object_type=obj_type)
        if obj_type == "cache":
            obj.item_ids = obj_data.get("item_ids", [])
        elif obj_type == "bulwark":
            tiles[y][x].passable = False  # bulwark makes tile impassable to all
        objects.append(obj)

    _validate_connectivity(tiles, width, height)
    return tiles, objects


def _place_combatants(
    tiles: list[list[ArenaTile]],
    characters: list[Character],
    teams: dict[str, int],
    width: int,
    height: int,
) -> list[ArenaCombatant]:
    """Place each character on the arena at their team's spawn edge."""
    team_members: dict[int, list[Character]] = {}
    for char in characters:
        t = teams.get(char.id, 1)
        team_members.setdefault(t, []).append(char)

    # Edge assignments: team 1 = top, 2 = bottom, 3 = left, 4 = right
    team_edges = {1: "top", 2: "bottom", 3: "left", 4: "right"}

    combatants: list[ArenaCombatant] = []
    occupied: set[tuple[int, int]] = set()

    def _find_spawn(x: int, y: int) -> tuple[int, int]:
        """Step inward until we find an unoccupied passable tile."""
        cx, cy = x, y
        for _ in range(max(width, height)):
            if tiles[cy][cx].passable and (cx, cy) not in occupied:
                return cx, cy
            # Step inward
            if cy == 0:
                cy += 1
            elif cy == height - 1:
                cy -= 1
            elif cx == 0:
                cx += 1
            elif cx == width - 1:
                cx -= 1
            else:
                cy += 1
        return cx, cy

    for team_num, members in sorted(team_members.items()):
        edge = team_edges.get(team_num, "top")
        count = len(members)
        for i, char in enumerate(members):
            if edge == "top":
                col = (i + 1) * width // (count + 1)
                sx, sy = col, 0
            elif edge == "bottom":
                col = (i + 1) * width // (count + 1)
                sx, sy = col, height - 1
            elif edge == "left":
                row = (i + 1) * height // (count + 1)
                sx, sy = 0, row
            else:  # right
                row = (i + 1) * height // (count + 1)
                sx, sy = width - 1, row

            fx, fy = _find_spawn(sx, sy)
            occupied.add((fx, fy))

            combatants.append(ArenaCombatant(
                id=char.id,
                x=fx,
                y=fy,
                team=team_num,
                hp=char.hp,
                max_hp=char.max_hp,
                stats={k: v for k, v in char.stats.model_dump().items()},
                equipped_weapon_id=char.equipped_weapon_id,
                ai_profile=char.ai_profile,
            ))

    return combatants


def _get_weapon_damage(weapon_id: str | None, db) -> int:
    """Roll the equipped weapon's damage_roll (a dice_roll CustomField, e.g. '2d6+4').
    Returns 1 if there's no weapon, no instance, or no template (unarmed/orphaned).
    """
    if not weapon_id:
        return 1
    inst_doc = db.collection("instances").document(weapon_id).get()
    if not inst_doc.exists:
        return 1
    instance = Instance(**(inst_doc.to_dict() | {"id": inst_doc.id}))

    template = None
    if instance.template_id:
        tmpl_doc = db.collection("templates").document(instance.template_id).get()
        if tmpl_doc.exists:
            template = Template(**(tmpl_doc.to_dict() | {"id": tmpl_doc.id}))

    resolved = resolve_instance(instance, template)
    damage_roll = get_field(resolved.fields, "damage_roll")
    if not damage_roll:
        return 1
    count, sides, bonus = parse_dice_notation(damage_roll)
    return max(dice.roll_sum(count, sides, bonus), 0)


def _save_arena(arena: Arena, db) -> None:
    """Persist arena to Firestore (encampments only)."""
    db.collection("arenas").document(arena.id).set(arena.model_dump())


def _check_combat_end(arena: Arena) -> tuple[bool, str | None]:
    """Return (combat_ended, outcome) based on current combatant HP."""
    living_by_team: dict[int, int] = {}
    for c in arena.combatants:
        if c.hp > 0 and "dead" not in c.status:
            living_by_team[c.team] = living_by_team.get(c.team, 0) + 1

    if len(living_by_team) <= 1:
        # All living combatants are on one team (or no one is alive)
        if 1 in living_by_team:
            return True, "victory"
        return True, "defeat"
    return False, None


def _advance_turn(arena: Arena) -> None:
    """Advance to the next combatant in turn order, skipping dead ones."""
    if not arena.turn_order:
        return
    arena.current_turn_idx = (arena.current_turn_idx + 1) % len(arena.turn_order)
    if arena.current_turn_idx == 0:
        arena.round += 1
    # Skip dead combatants
    for _ in range(len(arena.turn_order)):
        current_id = arena.turn_order[arena.current_turn_idx]
        combatant = next((c for c in arena.combatants if c.id == current_id), None)
        if combatant and "dead" not in combatant.status:
            break
        arena.current_turn_idx = (arena.current_turn_idx + 1) % len(arena.turn_order)


async def _resolve_action(
    encounter: Encounter,
    arena: Arena,
    actor: ArenaCombatant,
    action_type: str,
    target_id: str | None,
    to_x: int | None,
    to_y: int | None,
    item_id: str | None,
    object_id: str | None,
    stat_key: str,
    dc_stat_key: str,
    db,
    provider,
) -> dict:
    """Core action resolution. Returns result dict with outcome, dice_results, narrative context."""
    dice_results: list[int] = []
    outcome = "end_turn"
    damage = 0
    killed_ids: list[str] = []
    quests_advanced: list[str] = []
    looted_items: list[str] = []
    target: ArenaCombatant | None = None
    outcome_summary = ""

    if action_type == "move":
        if to_x is None or to_y is None:
            raise HTTPException(400, "Move action requires to_x and to_y")
        if not (0 <= to_x < arena.width and 0 <= to_y < arena.height):
            raise HTTPException(400, "Destination out of bounds")
        dest_tile = arena.tiles[to_y][to_x]
        if not dest_tile.passable:
            raise HTTPException(400, "Destination tile is not passable")

        # Check adjacency (one-step rule)
        if abs(to_x - actor.x) + abs(to_y - actor.y) > 1:
            raise HTTPException(400, "Can only move to adjacent tiles (one step)")

        # Determine direction and check edge barrier
        dx, dy = to_x - actor.x, to_y - actor.y
        direction = next(
            (i for i, (ddx, ddy) in enumerate(_DIRS) if ddx == dx and ddy == dy), -1
        )
        if direction >= 0:
            level = _effective_edge(arena, actor.x, actor.y, direction)
            mt = actor.ai_profile.movement_type if actor.ai_profile else "ground"
            if level == 2 and not (mt == "air" and not arena.indoor):
                raise HTTPException(400, "A barrier blocks movement in that direction")
            if level == 3:
                raise HTTPException(400, "A sealed barrier blocks movement in that direction")

        # Apply hazard damage if tile is dangerous
        if dest_tile.hazard > 0:
            actor.hp = max(0, actor.hp - dest_tile.hazard)
            outcome_summary += f" Entered hazard tile ({dest_tile.terrain_tag}), took {dest_tile.hazard} damage."

        # Apply aura status if tile has one
        if dest_tile.aura and dest_tile.aura not in actor.status:
            actor.status.append(dest_tile.aura)

        actor.x, actor.y = to_x, to_y
        outcome = "moved"
        outcome_summary = f"Moved to ({to_x}, {to_y})." + outcome_summary

    elif action_type == "attack":
        if not target_id:
            raise HTTPException(400, "Attack action requires target_id")
        target = next((c for c in arena.combatants if c.id == target_id), None)
        if target is None:
            raise HTTPException(404, "Target not found in arena")
        if "dead" in target.status or target.hp <= 0:
            raise HTTPException(400, "Target is already dead")

        attacker_stat = actor.stats.get(stat_key, 10)
        target_stat = target.stats.get(dc_stat_key, 10)
        raw_roll = random.randint(1, 20)
        roll = raw_roll + attacker_stat
        dc = target_stat + 10
        dice_results = [raw_roll]

        hit = roll >= dc
        if hit:
            weapon_dmg = _get_weapon_damage(actor.equipped_weapon_id, db)
            stat_bonus = max(0, (attacker_stat - 10) // 2)
            damage = max(1, weapon_dmg + stat_bonus)

            # Cover check: if target tile has a level-1 edge facing the attacker, reduce damage by 1
            dx = actor.x - target.x
            dy = actor.y - target.y
            if abs(dx) >= abs(dy) and dx != 0:
                cover_dir = 1 if dx > 0 else 3  # attacker is east/west of target
            elif dy != 0:
                cover_dir = 2 if dy > 0 else 0  # attacker is south/north of target
            else:
                cover_dir = -1
            if cover_dir >= 0 and arena.tiles[target.y][target.x].edges[cover_dir] == 1:
                damage = max(1, damage - 1)

            target.hp = max(0, target.hp - damage)
            outcome = "hit"
            outcome_summary = (
                f"Roll {roll} ({stat_key} {attacker_stat} + d20 {raw_roll}) "
                f"vs DC {dc} — HIT for {damage} damage. "
                f"Target at {target.hp}/{target.max_hp} HP."
            )
        else:
            outcome = "miss"
            outcome_summary = (
                f"Roll {roll} ({stat_key} {attacker_stat} + d20 {raw_roll}) "
                f"vs DC {dc} — MISS."
            )

        # Kill check
        if target.hp <= 0:
            if "dead" not in target.status:
                target.status.append("dead")
            killed_ids.append(target.id)
            # Alpha phase update on kill
            if actor.ai_profile and actor.ai_profile.intelligence == "alpha":
                apply_alpha_phase(actor)
            # Fire killed event
            kill_payload = FireEventRequest(
                adventure_id=encounter.adventure_id,
                type="killed",
                entity_id=target.id,
                encounter_id=encounter.id,
            )
            kill_result = await dispatch_event(kill_payload, db, provider)
            quests_advanced.extend(kill_result.quests_advanced)

    elif action_type == "use_item":
        # MVP: no engine-side HP effect; DM narrates the usage
        outcome = "used_item"
        outcome_summary = f"Used item (id: {item_id})."

    elif action_type == "loot":
        if not object_id:
            raise HTTPException(400, "Loot action requires object_id")
        cache = next((o for o in arena.objects if o.id == object_id and o.object_type == "cache"), None)
        if cache is None:
            raise HTTPException(404, "Cache not found in arena")
        if cache.looted:
            raise HTTPException(400, "Cache has already been looted")
        # Check adjacency (must be on the same tile or adjacent)
        if abs(actor.x - cache.x) + abs(actor.y - cache.y) > 1:
            raise HTTPException(400, "Must be adjacent to the cache to loot it")
        # Transfer items to actor's character inventory
        if cache.item_ids:
            char_ref = db.collection("instances").document(actor.id)
            char_doc = char_ref.get()
            if char_doc.exists:
                current_inv = char_doc.to_dict().get("inventory_ids", [])
                char_ref.update({"inventory_ids": current_inv + cache.item_ids})
        looted_items = list(cache.item_ids)
        cache.item_ids = []
        cache.looted = True
        outcome = "looted"
        outcome_summary = f"Looted cache, retrieved {len(looted_items)} item(s)."

    elif action_type == "end_turn":
        outcome = "ended_turn"
        outcome_summary = "Ended turn."

    # Apply aura from current tile each turn (for non-move actions)
    if action_type != "move":
        current_tile = arena.tiles[actor.y][actor.x]
        if current_tile.aura and current_tile.aura not in actor.status:
            actor.status.append(current_tile.aura)

    return {
        "outcome": outcome,
        "dice_results": dice_results,
        "damage": damage,
        "killed_ids": killed_ids,
        "quests_advanced": quests_advanced,
        "looted_items": looted_items,
        "target": target,
        "outcome_summary": outcome_summary,
    }


async def _run_turn(
    encounter_id: str,
    actor_id: str,
    action_type: str,
    target_id: str | None,
    to_x: int | None,
    to_y: int | None,
    item_id: str | None,
    object_id: str | None,
    stat_key: str,
    dc_stat_key: str,
    db,
    provider,
) -> TurnResult:
    """Shared logic for player-turn and npc-turn endpoints."""
    arena = _ARENAS.get(encounter_id)
    if arena is None:
        # Try reloading from Firestore (encampment arenas survive server restarts)
        enc_doc = db.collection("encounters").document(encounter_id).get()
        if not enc_doc.exists:
            raise HTTPException(404, "Encounter not found")
        encounter = Encounter(**(enc_doc.to_dict() | {"id": enc_doc.id}))
        if encounter.arena_id:
            a_doc = db.collection("arenas").document(encounter.arena_id).get()
            if a_doc.exists:
                arena = Arena(**a_doc.to_dict())
                _ARENAS[encounter_id] = arena
        if arena is None:
            raise HTTPException(404, "Arena not started or has expired")
    else:
        enc_doc = db.collection("encounters").document(encounter_id).get()
        encounter = Encounter(**(enc_doc.to_dict() | {"id": enc_doc.id}))

    # Validate it's this actor's turn
    if not arena.turn_order or arena.turn_order[arena.current_turn_idx] != actor_id:
        raise HTTPException(
            400,
            f"It is not {actor_id}'s turn. "
            f"Current: {arena.turn_order[arena.current_turn_idx] if arena.turn_order else 'none'}"
        )

    actor = next((c for c in arena.combatants if c.id == actor_id), None)
    if actor is None:
        raise HTTPException(404, "Actor not found in arena")
    if "dead" in actor.status:
        raise HTTPException(400, "Actor is dead and cannot take actions")

    # Resolve the action
    result = await _resolve_action(
        encounter, arena, actor,
        action_type, target_id, to_x, to_y, item_id, object_id,
        stat_key, dc_stat_key, db, provider,
    )

    # DM narration (skip for end_turn)
    narrative = ""
    if action_type != "end_turn":
        target_name = None
        if result["target"]:
            target_char = db.collection("instances").document(result["target"].id).get()
            target_name = character_name_from_doc(target_char.to_dict(), result["target"].id) if target_char.exists else result["target"].id
        actor_char = db.collection("instances").document(actor_id).get()
        actor_name = character_name_from_doc(actor_char.to_dict(), actor_id) if actor_char.exists else actor_id

        cards = get_cards_for_prompt(encounter.adventure_id, None, "", db)
        world_state = _get_world_state(encounter.adventure_id, db)
        prompt = build_action_narration_prompt(
            action_type, actor_name, target_name, result["outcome_summary"], cards, world_state
        )
        narration_result = await provider.generate(prompt)
        narrative = narration_result.get("narrative", "")

    # Persist ActionRecord
    action = ActionRecord(
        adventure_id=encounter.adventure_id,
        encounter_id=encounter_id,
        actor_id=actor_id,
        action_type=action_type,
        target_id=target_id,
        dice_results=result["dice_results"],
        outcome=result["outcome"],
        narrative=narrative,
        description=result["outcome_summary"],
    )
    db.collection("actions").document(action.id).set(action.model_dump())

    # Advance turn (after recording action)
    if action_type != "end_turn":
        _advance_turn(arena)
    else:
        _advance_turn(arena)

    # Check combat end conditions
    combat_ended, combat_outcome = _check_combat_end(arena)

    # Persist arena state if it's an encampment
    if arena.persisted:
        _save_arena(arena, db)

    return TurnResult(
        arena=arena,
        action=action,
        killed=result["killed_ids"],
        quests_advanced=result["quests_advanced"],
        combat_ended=combat_ended,
        combat_outcome=combat_outcome,
        narrative=narrative,
        looted_items=result["looted_items"],
    )


# ── Encounter CRUD ─────────────────────────────────────────────────────────────

@router.post("/encounters", response_model=Encounter, status_code=201)
async def create_encounter(payload: EncounterCreate):
    db = get_db()
    encounter = Encounter(**payload.model_dump())
    db.collection("encounters").document(encounter.id).set(encounter.model_dump())
    return encounter


@router.get("/encounters", response_model=list[Encounter])
async def list_encounters(adventure_id: str, status: str | None = None):
    db = get_db()
    query = db.collection("encounters").where("adventure_id", "==", adventure_id)
    if status:
        query = query.where("status", "==", status)
    return [
        Encounter(**(d.to_dict() | {"id": d.id}))
        for d in query.stream()
    ]


# ── Combat Flow Endpoints (registered before /{id}) ───────────────────────────

@router.post("/encounters/{encounter_id}/start-combat", response_model=Arena)
async def start_combat(encounter_id: str, payload: StartCombatRequest):
    db = get_db()
    enc_doc = db.collection("encounters").document(encounter_id).get()
    if not enc_doc.exists:
        raise HTTPException(404, "Encounter not found")
    encounter = Encounter(**(enc_doc.to_dict() | {"id": enc_doc.id}))
    if encounter.status != "pending":
        raise HTTPException(400, f"Combat already started (status: {encounter.status})")

    # Encampment check: if an arena already exists for this encounter, reload it
    is_encampment = False
    if encounter.location_id:
        poi_doc = db.collection("pois").document(encounter.location_id).get()
        if poi_doc.exists and poi_doc.to_dict().get("type") == "encampment":
            is_encampment = True

    if is_encampment and encounter.arena_id:
        existing = db.collection("arenas").document(encounter.arena_id).get()
        if existing.exists:
            arena = Arena(**existing.to_dict())
            _ARENAS[encounter_id] = arena
            db.collection("encounters").document(encounter_id).update({"status": "active"})
            return arena

    # Fetch characters on the stage
    if not encounter.stage_ids:
        raise HTTPException(400, "No characters in stage_ids")
    char_refs = [db.collection("instances").document(cid) for cid in encounter.stage_ids]
    docs_by_id = {d.id: d for d in db.get_all(char_refs)}
    characters: list[Character] = []
    for char_id in encounter.stage_ids:
        char_doc = docs_by_id.get(char_id)
        if char_doc is None or not char_doc.exists:
            raise HTTPException(404, f"Character {char_id} not found")
        characters.append(character_from_instance(Instance(**(char_doc.to_dict() | {"id": char_doc.id}))))

    # Validate all staged characters are assigned a team
    for char in characters:
        if char.id not in payload.teams:
            raise HTTPException(400, f"Character {char.id} has no team assignment in request")

    # Generate arena via LLM
    location_type = "wilderness"
    if encounter.location_id and not is_encampment:
        poi_doc = db.collection("pois").document(encounter.location_id).get()
        if poi_doc.exists:
            location_type = poi_doc.to_dict().get("type", "wilderness")
    elif is_encampment:
        location_type = "encampment"

    provider = get_provider()
    cards = get_cards_for_prompt(encounter.adventure_id, None, "", db)
    world_state = _get_world_state(encounter.adventure_id, db)
    arena_prompt = build_arena_generation_prompt(
        location_type, payload.arena_width, payload.arena_height,
        payload.indoor, cards, world_state,
    )
    llm_result = await provider.generate(arena_prompt)
    tiles, objects = _parse_arena_from_llm(llm_result, payload.arena_width, payload.arena_height, payload.indoor)

    # Place combatants and roll initiative
    combatants = _place_combatants(tiles, characters, payload.teams, payload.arena_width, payload.arena_height)
    initiatives: dict[str, int] = {
        c.id: c.stats.get("dexterity", 10) + random.randint(1, 20)
        for c in combatants
    }
    turn_order = sorted(combatants, key=lambda c: (-initiatives[c.id], c.id))

    arena = Arena(
        encounter_id=encounter_id,
        adventure_id=encounter.adventure_id,
        width=payload.arena_width,
        height=payload.arena_height,
        indoor=payload.indoor,
        tiles=tiles,
        objects=objects,
        combatants=combatants,
        turn_order=[c.id for c in turn_order],
        teams=payload.teams,
        persisted=is_encampment,
    )

    _ARENAS[encounter_id] = arena

    updates: dict = {"status": "active"}
    if is_encampment:
        _save_arena(arena, db)
        updates["arena_id"] = arena.id

    db.collection("encounters").document(encounter_id).update(updates)
    return arena


@router.get("/encounters/{encounter_id}/arena", response_model=Arena)
async def get_arena(encounter_id: str):
    db = get_db()
    if encounter_id in _ARENAS:
        return _ARENAS[encounter_id]
    enc_doc = db.collection("encounters").document(encounter_id).get()
    if not enc_doc.exists:
        raise HTTPException(404, "Encounter not found")
    encounter = Encounter(**(enc_doc.to_dict() | {"id": enc_doc.id}))
    if encounter.arena_id:
        a_doc = db.collection("arenas").document(encounter.arena_id).get()
        if a_doc.exists:
            arena = Arena(**a_doc.to_dict())
            _ARENAS[encounter_id] = arena
            return arena
    raise HTTPException(404, "Arena has not been started or has expired")


@router.get("/encounters/{encounter_id}/actions", response_model=list[ActionRecord])
async def list_actions(encounter_id: str):
    db = get_db()
    docs = (
        db.collection("actions")
        .where("encounter_id", "==", encounter_id)
        .stream()
    )
    return [ActionRecord(**(d.to_dict() | {"id": d.id})) for d in docs]


@router.post("/encounters/{encounter_id}/player-turn", response_model=TurnResult)
async def player_turn(encounter_id: str, payload: PlayerTurnRequest):
    db = get_db()
    provider = get_provider()
    return await _run_turn(
        encounter_id=encounter_id,
        actor_id=payload.actor_id,
        action_type=payload.action_type,
        target_id=payload.target_id,
        to_x=payload.to_x,
        to_y=payload.to_y,
        item_id=payload.item_id,
        object_id=payload.object_id,
        stat_key=payload.stat_key,
        dc_stat_key=payload.dc_stat_key,
        db=db,
        provider=provider,
    )


@router.post("/encounters/{encounter_id}/npc-turn", response_model=TurnResult)
async def npc_turn(encounter_id: str):
    db = get_db()
    provider = get_provider()

    arena = _ARENAS.get(encounter_id)
    if arena is None:
        raise HTTPException(404, "Arena not started or has expired")

    if not arena.turn_order:
        raise HTTPException(400, "No turn order in arena")

    current_id = arena.turn_order[arena.current_turn_idx]
    actor = next((c for c in arena.combatants if c.id == current_id), None)
    if actor is None or actor.ai_profile is None:
        raise HTTPException(400, "Current combatant is not an NPC (no ai_profile)")
    if "dead" in actor.status:
        raise HTTPException(400, "Current NPC is dead — call player-turn or skip")

    decision = npc_decide_action(actor, arena)

    return await _run_turn(
        encounter_id=encounter_id,
        actor_id=current_id,
        action_type=decision["action_type"],
        target_id=decision.get("target_id"),
        to_x=decision.get("to_x"),
        to_y=decision.get("to_y"),
        item_id=None,
        object_id=None,
        stat_key="strength",
        dc_stat_key="reflex",
        db=db,
        provider=provider,
    )


@router.post("/encounters/{encounter_id}/end-combat")
async def end_combat(encounter_id: str, payload: EndCombatRequest):
    db = get_db()
    provider = get_provider()

    enc_doc = db.collection("encounters").document(encounter_id).get()
    if not enc_doc.exists:
        raise HTTPException(404, "Encounter not found")
    encounter = Encounter(**(enc_doc.to_dict() | {"id": enc_doc.id}))

    arena = _ARENAS.get(encounter_id)

    narrative = ""
    if arena:
        # Gather surviving combatant summaries for the DM prompt
        survivors = [
            f"{c.id} (team {c.team}, {c.hp}/{c.max_hp} HP)"
            for c in arena.combatants
            if c.hp > 0 and "dead" not in c.status
        ]
        cards = get_cards_for_prompt(encounter.adventure_id, None, "", db)
        world_state = _get_world_state(encounter.adventure_id, db)
        prompt = build_combat_end_prompt(payload.outcome, survivors, cards, world_state)
        result = await provider.generate(prompt)
        narrative = result.get("narrative", "")

        # Fire survived events for living player-team combatants
        for c in arena.combatants:
            if c.hp > 0 and "dead" not in c.status and arena.teams.get(c.id) == 1:
                survived_payload = FireEventRequest(
                    adventure_id=encounter.adventure_id,
                    type="survived",
                    entity_id=c.id,
                    encounter_id=encounter_id,
                )
                await dispatch_event(survived_payload, db, provider)

        # Write final HP back to character Instances -- hp lives inside the `fields`
        # list now, not a top-level document field, so this is a read-modify-write
        # rather than a plain .update({"hp": ...}).
        for c in arena.combatants:
            write_character_field(c.id, CustomField(key="hp", field_type="number", value=c.hp, required=True, bound_behavior="hp"), db)

        # Discard arena from memory (encampment arenas stay in Firestore)
        if not arena.persisted:
            del _ARENAS[encounter_id]

    db.collection("encounters").document(encounter_id).update({"status": payload.outcome})
    return {"narrative": narrative, "encounter_id": encounter_id, "outcome": payload.outcome}


# ── Encounter CRUD (parameterized routes last) ─────────────────────────────────

@router.get("/encounters/{encounter_id}", response_model=Encounter)
async def get_encounter(encounter_id: str):
    db = get_db()
    doc = db.collection("encounters").document(encounter_id).get()
    if not doc.exists:
        raise HTTPException(404, "Encounter not found")
    return Encounter(**(doc.to_dict() | {"id": doc.id}))


@router.patch("/encounters/{encounter_id}", response_model=Encounter)
async def update_encounter(encounter_id: str, payload: EncounterUpdate):
    db = get_db()
    ref = db.collection("encounters").document(encounter_id)
    if not ref.get().exists:
        raise HTTPException(404, "Encounter not found")
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if changes:
        ref.update(changes)
    doc = ref.get()
    return Encounter(**(doc.to_dict() | {"id": doc.id}))
