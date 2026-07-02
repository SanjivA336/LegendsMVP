import hashlib
import random
from typing import TYPE_CHECKING

from .biomes import BiomeFamily

if TYPE_CHECKING:
    from ..models.poi import DungeonRoom, Exit

# ── Constants ─────────────────────────────────────────────────────────────────

_OPPOSITE: dict[str, str] = {
    "north": "south", "south": "north",
    "east": "west",   "west": "east",
    "down": "up",     "up": "down",
}
_LATERAL = ["north", "south", "east", "west"]
_DELTAS: dict[str, tuple[int, int]] = {
    "north": (0, 1), "south": (0, -1),
    "east": (1, 0),  "west": (-1, 0),
}

_MOUNTAIN_VOLCANIC = {BiomeFamily.MOUNTAIN.value, BiomeFamily.VOLCANIC.value}

# ── Deterministic RNG ─────────────────────────────────────────────────────────

def tile_rng(map_id: str, tile_x: int, tile_y: int, extra: int = 0) -> random.Random:
    """Seed a Random from tile identity so results are reproducible across restarts."""
    h = hashlib.sha256(f"{map_id}:{tile_x}:{tile_y}:{extra}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


# ── POI type selection ────────────────────────────────────────────────────────

# Weights by tier: [settlement, encampment, dungeon, ruins]
_POI_WEIGHTS: dict[int, list[int]] = {
    1: [35, 25, 20, 20],
    2: [15, 30, 30, 25],
    3: [0,  40, 50, 10],
}
_POI_TYPES = ["settlement", "encampment", "dungeon", "ruins"]


def select_poi_type(
    biome_id: int | None,
    tier: int,
    rng: random.Random,
) -> str:
    """Return a POIType string for the given tile, weighted by tier and biome family."""
    weights = list(_POI_WEIGHTS[tier])  # copy so we can mutate

    # Mountain/Volcanic tiles can't host settlements
    if biome_id is not None and (biome_id % 10) in _MOUNTAIN_VOLCANIC:
        weights[0] = 0

    return rng.choices(_POI_TYPES, weights=weights, k=1)[0]


# ── Settlement helpers ────────────────────────────────────────────────────────

def select_location_count(tier: int, rng: random.Random) -> int:
    ranges = {1: (3, 5), 2: (5, 8), 3: (8, 12)}
    lo, hi = ranges[tier]
    return rng.randint(lo, hi)


# ── Ruins helpers ─────────────────────────────────────────────────────────────

def select_structure_count(tier: int, rng: random.Random) -> int:
    ranges = {1: (2, 3), 2: (3, 5), 3: (4, 7)}
    lo, hi = ranges[tier]
    return rng.randint(lo, hi)


def select_structure_floors(rng: random.Random) -> int:
    return rng.randint(1, 3)


def select_structure_budget(floor_count: int, rng: random.Random) -> int:
    """Roll door budget for one floor within a ruin structure (smaller than dungeon)."""
    if floor_count == 1:
        return rng.randint(3, 5)
    return rng.randint(4, 7)


# ── Dungeon entrance ──────────────────────────────────────────────────────────

def _entrance_exits(
    rng: random.Random,
    floor_count: int,
    current_floor: int = 1,
) -> list["Exit"]:
    """1–3 random lateral exits for an entrance room, plus a down-stair if floors remain."""
    from ..models.poi import Exit

    directions = rng.sample(_LATERAL, k=rng.randint(1, min(3, len(_LATERAL))))
    exits = [Exit(direction=d) for d in directions]
    if current_floor < floor_count:
        exits.append(Exit(direction="down", leads_to_floor=current_floor + 1))
    return exits


# ── Room exit generation ──────────────────────────────────────────────────────

def generate_next_room_exits(
    current_x: int,
    current_y: int,
    current_floor: int,
    from_direction: str,
    existing_rooms: dict[tuple[int, int], "DungeonRoom"],
    door_budget: int,
    floor_count: int,
    stairs_placed: bool,
    is_boss_room: bool,
    rng: random.Random,
) -> tuple[list["Exit"], int]:
    """
    Determine exits for a newly generated dungeon room.

    Optimized port of POI.generate_room() from the original prototype.

    Exits are *promises*: a direction in this list means a door exists here,
    but the room behind it is only generated when a player walks through it.
    leads_to_room_id stays None until that happens.

    Rules:

    1. RETURN EXIT (always):
       Add Exit(direction=_OPPOSITE[from_direction]).
       The caller stamps leads_to_room_id = from_room.id after writing.

    2. FORCED NEIGHBOUR CONNECTIONS:
       For each direction d in _LATERAL:
         - neighbour_pos = (current_x + dx, current_y + dy)
         - If that neighbour exists AND already has an exit pointing back here,
           this room must also connect (free — does not consume budget).

    3. CANDIDATE DIRECTIONS:
       remaining = lateral directions not already added AND whose neighbour
       position is not already occupied by an existing room.

    4. RANDOM EXITS (skipped if is_boss_room or door_budget <= 0):
       k = min(rng.randint(1, 3), door_budget, len(remaining))
       chosen = rng.sample(remaining, k)
       Each chosen direction consumes 1 from door_budget.

    5. STAIR LOGIC (skipped if is_boss_room):
       For ("down", floor+1) and ("up", floor-1):
         - If target_floor is out of [1, floor_count]: skip.
         - Forced if a room at the same (x, y) on target_floor already has a
           stair pointing back — caller must pass that context via existing_rooms
           if needed (stair force is handled by the router for now).
         - Probabilistic: if door_budget < 2 and direction == "down" and not
           stairs_placed: rng.random() < 0.5 → add stair.

    Returns (exits_list, doors_consumed).
    """
    from ..models.poi import Exit

    exits: list[Exit] = []
    doors_consumed = 0
    added: set[str] = set()

    # Rule 1 — return exit (always present, free)
    return_dir = _OPPOSITE[from_direction]
    exits.append(Exit(direction=return_dir))
    added.add(return_dir)

    # Rule 2 — forced neighbour connections (free, no budget)
    for d in _LATERAL:
        if d in added:
            continue
        nx, ny = current_x + _DELTAS[d][0], current_y + _DELTAS[d][1]
        neighbor = existing_rooms.get((nx, ny))
        if neighbor is not None and any(e.direction == _OPPOSITE[d] for e in neighbor.exits):
            exits.append(Exit(direction=d, leads_to_room_id=neighbor.id))
            added.add(d)

    # Rule 3 — candidate directions (no existing room, not already added)
    remaining = [
        d for d in _LATERAL
        if d not in added
        and (current_x + _DELTAS[d][0], current_y + _DELTAS[d][1]) not in existing_rooms
    ]

    # Rule 4 — random exits (skipped entirely for boss rooms or empty budget)
    if not is_boss_room and door_budget > 0 and remaining:
        k = min(rng.randint(1, 3), door_budget, len(remaining))
        for d in rng.sample(remaining, k):
            exits.append(Exit(direction=d))
            added.add(d)
            doors_consumed += 1

    # Rule 5 — stair logic (generalised up/down loop, skipped for boss rooms)
    if not is_boss_room:
        for vertical_dir, target_floor in [("down", current_floor + 1), ("up", current_floor - 1)]:
            if not (1 <= target_floor <= floor_count):
                continue
            if vertical_dir in added:
                continue
            # Probabilistic pressure: nudge toward stairs when budget nearly gone
            if vertical_dir == "down" and not stairs_placed and door_budget < 2:
                if rng.random() < 0.5:
                    exits.append(Exit(direction=vertical_dir, leads_to_floor=target_floor))
                    added.add(vertical_dir)

    return exits, doors_consumed
