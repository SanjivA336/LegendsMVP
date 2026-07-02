"""
Pure combat AI functions — no I/O, no async, no Firestore.

All functions take the current Arena state and return decisions. The router
applies those decisions mechanically and calls the DM for narration afterward.
"""

import random
from ..models.combat import Arena, ArenaCombatant, AIProfile

# Direction indices: N=0, E=1, S=2, W=3
# Deltas for each direction: (dx, dy)
_DIRS: list[tuple[int, int]] = [(0, -1), (1, 0), (0, 1), (-1, 0)]
_OPPOSITE: dict[int, int] = {0: 2, 1: 3, 2: 0, 3: 1}


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _living_enemies(combatant: ArenaCombatant, arena: Arena) -> list[ArenaCombatant]:
    return [
        c for c in arena.combatants
        if c.team != combatant.team and c.hp > 0 and "dead" not in c.status
    ]


def _manhattan(a: ArenaCombatant | tuple[int, int], b: ArenaCombatant | tuple[int, int]) -> int:
    ax, ay = (a.x, a.y) if isinstance(a, ArenaCombatant) else a
    bx, by = (b.x, b.y) if isinstance(b, ArenaCombatant) else b
    return abs(ax - bx) + abs(ay - by)


def _effective_edge(arena: Arena, x: int, y: int, direction: int) -> int:
    """Effective barrier level crossing from (x,y) in the given direction.

    Takes the max of the source tile's outgoing edge and the destination tile's
    incoming edge so that inconsistent LLM output never creates one-way walls.
    """
    outgoing = arena.tiles[y][x].edges[direction]
    dx, dy = _DIRS[direction]
    nx, ny = x + dx, y + dy
    if 0 <= nx < arena.width and 0 <= ny < arena.height:
        incoming = arena.tiles[ny][nx].edges[_OPPOSITE[direction]]
    else:
        incoming = 3  # out-of-bounds is always sealed
    return max(outgoing, incoming)


def _tile_enterable(arena: Arena, x: int, y: int, movement_type: str) -> bool:
    """True if the tile at (x,y) can be occupied by the given movement type."""
    if not (0 <= x < arena.width and 0 <= y < arena.height):
        return False
    tile = arena.tiles[y][x]
    if not tile.passable:
        return False
    if movement_type == "sea" and not tile.terrain_tag.startswith("water"):
        return False
    return True


def _edge_passable(arena: Arena, x: int, y: int, direction: int, movement_type: str) -> bool:
    """True if the combatant's movement type can cross the edge in the given direction."""
    level = _effective_edge(arena, x, y, direction)
    if level <= 1:
        return True  # open or cover: always passable (cover adds movement cost)
    if level == 2:
        # barrier: only air in outdoor arenas can cross
        return movement_type == "air" and not arena.indoor
    # level 3 (sealed): blocks everyone including air
    return False


def _valid_adjacent(
    combatant: ArenaCombatant,
    arena: Arena,
) -> list[tuple[int, int, int]]:
    """Return [(x, y, cost)] for each valid adjacent tile the combatant can step to."""
    mt = combatant.ai_profile.movement_type if combatant.ai_profile else "ground"
    results = []
    for direction, (dx, dy) in enumerate(_DIRS):
        nx, ny = combatant.x + dx, combatant.y + dy
        if not _tile_enterable(arena, nx, ny, mt):
            continue
        if mt not in ("air", "teleport") and not _edge_passable(arena, combatant.x, combatant.y, direction, mt):
            continue
        # air units crossing level-2 edge in indoor arenas is already blocked by _edge_passable
        edge_lv = _effective_edge(arena, combatant.x, combatant.y, direction)
        tile_cost = arena.tiles[ny][nx].movement_cost
        cover_cost = 1 if edge_lv == 1 else 0
        results.append((nx, ny, tile_cost + cover_cost))
    return results


# ── Target Selection ──────────────────────────────────────────────────────────

def select_target(combatant: ArenaCombatant, arena: Arena) -> ArenaCombatant | None:
    """Pick a target based on the combatant's configured target_selection mode."""
    enemies = _living_enemies(combatant, arena)
    if not enemies:
        return None

    prof = combatant.ai_profile
    mode = prof.target_selection if prof else "closest"

    if mode == "closest":
        return min(enemies, key=lambda e: _manhattan(combatant, e))
    if mode == "furthest":
        return max(enemies, key=lambda e: _manhattan(combatant, e))
    if mode == "strongest":
        return max(enemies, key=lambda e: e.hp)
    if mode == "weakest":
        return min(enemies, key=lambda e: e.hp)
    if mode == "last_assailant":
        if prof and prof.last_assailant_id:
            match = next((e for e in enemies if e.id == prof.last_assailant_id), None)
            if match:
                return match
        return min(enemies, key=lambda e: _manhattan(combatant, e))
    if mode == "random":
        return random.choice(enemies)

    return min(enemies, key=lambda e: _manhattan(combatant, e))


# ── Movement Computation ──────────────────────────────────────────────────────

def compute_move(
    combatant: ArenaCombatant,
    target: ArenaCombatant,
    arena: Arena,
) -> tuple[int, int]:
    """Return the best adjacent (x, y) to step toward preferred_distance from target.

    Returns current position if stuck or already optimally placed.
    """
    prof = combatant.ai_profile
    mt = prof.movement_type if prof else "ground"
    pref = prof.preferred_distance if prof else 1

    if mt == "teleport":
        best = (combatant.x, combatant.y)
        best_diff = abs(_manhattan(combatant, target) - pref)
        for cy in range(arena.height):
            for cx in range(arena.width):
                if (cx, cy) == (combatant.x, combatant.y):
                    continue
                if not _tile_enterable(arena, cx, cy, mt):
                    continue
                diff = abs(abs(cx - target.x) + abs(cy - target.y) - pref)
                if diff < best_diff:
                    best_diff = diff
                    best = (cx, cy)
        return best

    if mt == "air":
        # Step directly toward/away from target; one tile per call
        dx = target.x - combatant.x
        dy = target.y - combatant.y
        current_dist = abs(dx) + abs(dy)
        if current_dist <= pref:
            # Too close: step away
            dx, dy = -dx, -dy
        # Prefer whichever axis reduces the distance-to-preferred more
        candidates = []
        if dx != 0:
            sx = 1 if dx > 0 else -1
            nx, ny = combatant.x + sx, combatant.y
            if _tile_enterable(arena, nx, ny, mt):
                candidates.append((nx, ny))
        if dy != 0:
            sy = 1 if dy > 0 else -1
            nx, ny = combatant.x, combatant.y + sy
            if _tile_enterable(arena, nx, ny, mt):
                candidates.append((nx, ny))
        if not candidates:
            return (combatant.x, combatant.y)
        return min(candidates, key=lambda p: abs(abs(p[0] - target.x) + abs(p[1] - target.y) - pref))

    # Ground / sea: pick valid adjacent tile that best reaches preferred_distance
    valid = _valid_adjacent(combatant, arena)
    if not valid:
        return (combatant.x, combatant.y)

    def _score(move: tuple[int, int, int]) -> tuple[int, int]:
        nx, ny, cost = move
        diff = abs(abs(nx - target.x) + abs(ny - target.y) - pref)
        return (diff, cost)  # minimize diff, then cost

    best = min(valid, key=_score)
    return (best[0], best[1])


# ── Intelligence / Self-Preservation ──────────────────────────────────────────

def should_flee(combatant: ArenaCombatant, last_hit_damage: int = 0) -> bool:
    """Return True if this combatant's intelligence triggers a self-preservation response."""
    prof = combatant.ai_profile
    if not prof:
        return False
    intel = prof.intelligence
    if intel == "beast":
        return (
            combatant.hp < combatant.max_hp * 0.25
            or last_hit_damage > combatant.max_hp * 0.4
        )
    if intel in ("lurker", "soldier"):
        return combatant.hp < combatant.max_hp * 0.4
    # drone and alpha never flee
    return False


def _retreat_move(
    combatant: ArenaCombatant,
    enemies: list[ArenaCombatant],
    arena: Arena,
) -> tuple[int, int]:
    """Pick the adjacent tile that maximizes total distance from all enemies (beast flee)."""
    valid = _valid_adjacent(combatant, arena)
    if not valid:
        return (combatant.x, combatant.y)
    best = max(valid, key=lambda m: sum(abs(m[0] - e.x) + abs(m[1] - e.y) for e in enemies))
    return (best[0], best[1])


def _cover_move(
    combatant: ArenaCombatant,
    nearest_enemy: ArenaCombatant,
    arena: Arena,
) -> tuple[int, int]:
    """Find nearest valid adjacent tile that is adjacent to a level-1 edge (soldier cover-seek)."""
    valid = _valid_adjacent(combatant, arena)
    cover = [
        (nx, ny, cost) for nx, ny, cost in valid
        if any(e == 1 for e in arena.tiles[ny][nx].edges)
    ]
    if cover:
        best = min(cover, key=lambda m: m[2])
        return (best[0], best[1])
    # Fallback: step away from enemy if no cover tile reachable
    return _retreat_move(combatant, [nearest_enemy], arena)


def apply_alpha_phase(combatant: ArenaCombatant) -> list[str]:
    """Add phase status tags to alpha at HP thresholds. Returns new tags added (for narration)."""
    added = []
    hp_pct = combatant.hp / combatant.max_hp if combatant.max_hp > 0 else 0
    if hp_pct <= 0.25 and "berserk" not in combatant.status:
        combatant.status.append("berserk")
        added.append("berserk")
    elif hp_pct <= 0.50 and "enraged" not in combatant.status:
        combatant.status.append("enraged")
        added.append("enraged")
    return added


# ── Main NPC Decision ─────────────────────────────────────────────────────────

def npc_decide_action(
    combatant: ArenaCombatant,
    arena: Arena,
    last_hit_damage: int = 0,
) -> dict:
    """Determine the NPC's chosen action for this turn.

    Returns a dict with:
        action_type: "attack" | "move" | "end_turn"
        target_id: str (for attack)
        to_x, to_y: int (for move)
    """
    prof = combatant.ai_profile
    intel = prof.intelligence if prof else "drone"
    pref = prof.preferred_distance if prof else 1

    enemies = _living_enemies(combatant, arena)
    if not enemies:
        return {"action_type": "end_turn"}

    # Alpha: push phase status tags (DM narrates the change)
    if intel == "alpha":
        apply_alpha_phase(combatant)

    # ── Self-preservation ─────────────────────────────────────────────────────
    if should_flee(combatant, last_hit_damage):
        if intel == "beast":
            tx, ty = _retreat_move(combatant, enemies, arena)
            return {"action_type": "move", "to_x": tx, "to_y": ty}

        if intel == "lurker":
            nearest = min(enemies, key=lambda e: _manhattan(combatant, e))
            tx, ty = compute_move(combatant, nearest, arena)
            return {"action_type": "move", "to_x": tx, "to_y": ty}

        if intel == "soldier":
            nearest = min(enemies, key=lambda e: _manhattan(combatant, e))
            tx, ty = _cover_move(combatant, nearest, arena)
            if (tx, ty) != (combatant.x, combatant.y):
                return {"action_type": "move", "to_x": tx, "to_y": ty}

    # ── Target selection ──────────────────────────────────────────────────────
    if intel == "drone":
        target = min(enemies, key=lambda e: _manhattan(combatant, e))
    elif intel == "lurker":
        # Prefer the most isolated enemy (fewest living allies within 3 tiles)
        def _isolation(e: ArenaCombatant) -> int:
            return sum(
                1 for a in arena.combatants
                if a.team == e.team and a.id != e.id
                and a.hp > 0 and "dead" not in a.status
                and _manhattan(a, e) <= 3
            )
        target = min(enemies, key=_isolation)
    else:
        target = select_target(combatant, arena)

    if target is None:
        return {"action_type": "end_turn"}

    dist = _manhattan(combatant, target)

    # Lurker distance guard: already within preferred_distance → attack, don't overadvance
    if intel == "lurker" and dist <= pref:
        return {"action_type": "attack", "target_id": target.id}

    # General: attack if at preferred_distance, else move
    if dist <= pref:
        return {"action_type": "attack", "target_id": target.id}

    tx, ty = compute_move(combatant, target, arena)
    if (tx, ty) == (combatant.x, combatant.y):
        # Stuck: attack anyway if barely out of range
        if dist <= pref + 1:
            return {"action_type": "attack", "target_id": target.id}
        return {"action_type": "end_turn"}

    return {"action_type": "move", "to_x": tx, "to_y": ty}
