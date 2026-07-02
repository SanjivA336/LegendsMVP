from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..firebase import get_db
from ..models.poi import (
    POI, POIUpdate, POICreate,
    Dungeon, DungeonRoom, DungeonRoomUpdate,
    Settlement, SettlementUpdate,
    Ruin, RuinUpdate, RuinStructure,
    DiscoverRequest, EnterRequest, ExploreRequest,
    SettlementEnterRequest, RuinEnterRequest,
)
from ..utils.poi_gen import (
    tile_rng, select_poi_type,
    select_location_count,
    select_structure_count, select_structure_floors, select_structure_budget,
    _entrance_exits,
)

router = APIRouter()


class SeedMapRequest(BaseModel):
    adventure_id: str
    map_id: str


@router.post("/pois/seed-map", response_model=list[POI], status_code=201)
async def seed_map_pois(payload: SeedMapRequest):
    """Auto-generate POI documents for every poi_candidate tile in a map. Idempotent."""
    db = get_db()
    map_doc = db.collection("world_maps").document(payload.map_id).get()
    if not map_doc.exists:
        raise HTTPException(status_code=404, detail="World map not found")

    tiles: list[dict] = map_doc.to_dict().get("tiles", [])
    created: list[POI] = []
    tiles_dirty = False

    for tile in tiles:
        if not tile.get("poi_candidate") or tile.get("is_water"):
            continue

        # Idempotent: return existing POI if already discovered
        if tile.get("poi_id"):
            poi_doc = db.collection("pois").document(tile["poi_id"]).get()
            if poi_doc.exists:
                created.append(_doc_to_poi(poi_doc))
                continue

        rng = tile_rng(payload.map_id, tile["x"], tile["y"])
        tier = tile.get("tier") or 1
        poi_type = select_poi_type(tile.get("biome_id"), tier, rng)

        poi = POI(
            adventure_id=payload.adventure_id,
            map_id=payload.map_id,
            tile_x=tile["x"],
            tile_y=tile["y"],
            type=poi_type,
            tier=tier,
        )
        db.collection("pois").document(poi.id).set(poi.model_dump())
        tile["poi_id"] = poi.id
        tiles_dirty = True
        created.append(poi)

    if tiles_dirty:
        db.collection("world_maps").document(payload.map_id).update({"tiles": tiles})

    return created


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_to_poi(doc) -> POI:
    return POI(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_dungeon(doc) -> Dungeon:
    return Dungeon(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_room(doc) -> DungeonRoom:
    return DungeonRoom(**doc.to_dict())


def _doc_to_settlement(doc) -> Settlement:
    return Settlement(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_ruin(doc) -> Ruin:
    return Ruin(**(doc.to_dict() | {"id": doc.id}))


def _stamp_tile_poi_id(map_id: str, tile_x: int, tile_y: int, poi_id: str, db) -> None:
    """Read full tile list, patch poi_id on the matching tile, write back entire array."""
    ref = db.collection("world_maps").document(map_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="World map not found")
    tiles = doc.to_dict().get("tiles", [])
    for tile in tiles:
        if tile["x"] == tile_x and tile["y"] == tile_y:
            tile["poi_id"] = poi_id
            ref.update({"tiles": tiles})
            return
    raise HTTPException(status_code=404, detail="Tile not found in map")


# ── POI Endpoints ─────────────────────────────────────────────────────────────

@router.post("/pois/discover", response_model=POI, status_code=201)
async def discover_poi(payload: DiscoverRequest):
    db = get_db()

    # Fetch the tile from the world map
    map_doc = db.collection("world_maps").document(payload.map_id).get()
    if not map_doc.exists:
        raise HTTPException(status_code=404, detail="World map not found")

    map_data = map_doc.to_dict()
    tile = next(
        (t for t in map_data.get("tiles", [])
         if t["x"] == payload.tile_x and t["y"] == payload.tile_y),
        None,
    )
    if tile is None:
        raise HTTPException(status_code=404, detail="Tile not found")
    if tile.get("is_water"):
        raise HTTPException(status_code=400, detail="Cannot place a POI on a water tile")
    if not tile.get("poi_candidate"):
        raise HTTPException(status_code=400, detail="Tile is not a POI candidate")

    # Idempotent: return existing POI if already discovered
    if tile.get("poi_id"):
        poi_doc = db.collection("pois").document(tile["poi_id"]).get()
        if poi_doc.exists:
            return _doc_to_poi(poi_doc)

    # Select type deterministically from tile coordinates
    rng = tile_rng(payload.map_id, payload.tile_x, payload.tile_y)
    tier = tile.get("tier") or 1
    poi_type = select_poi_type(tile.get("biome_id"), tier, rng)

    poi = POI(
        adventure_id=payload.adventure_id,
        map_id=payload.map_id,
        tile_x=payload.tile_x,
        tile_y=payload.tile_y,
        type=poi_type,
        tier=tier,
    )
    db.collection("pois").document(poi.id).set(poi.model_dump())
    _stamp_tile_poi_id(payload.map_id, payload.tile_x, payload.tile_y, poi.id, db)
    return poi


@router.get("/pois", response_model=list[POI])
async def list_pois(adventure_id: str, map_id: str | None = None):
    db = get_db()
    q = db.collection("pois").where("adventure_id", "==", adventure_id)
    if map_id:
        q = q.where("map_id", "==", map_id)
    return [_doc_to_poi(d) for d in q.stream()]


@router.get("/pois/{poi_id}", response_model=POI)
async def get_poi(poi_id: str):
    db = get_db()
    doc = db.collection("pois").document(poi_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="POI not found")
    return _doc_to_poi(doc)


@router.patch("/pois/{poi_id}", response_model=POI)
async def update_poi(poi_id: str, payload: POIUpdate):
    db = get_db()
    ref = db.collection("pois").document(poi_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="POI not found")
    updates = payload.model_dump(exclude_none=True)
    if updates:
        ref.update(updates)
    return _doc_to_poi(ref.get())


@router.delete("/pois/{poi_id}", status_code=204)
async def delete_poi(poi_id: str):
    db = get_db()
    doc = db.collection("pois").document(poi_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="POI not found")
    poi = _doc_to_poi(doc)

    # Cascade-delete dungeon + rooms for dungeon-type POIs
    if poi.type == "dungeon":
        dungeons = db.collection("dungeons").where("poi_id", "==", poi_id).stream()
        for d in dungeons:
            rooms = db.collection("dungeon_rooms").where("dungeon_id", "==", d.id).stream()
            for r in rooms:
                db.collection("dungeon_rooms").document(r.id).delete()
            db.collection("dungeons").document(d.id).delete()

    db.collection("pois").document(poi_id).delete()


# ── Dungeon Endpoints ─────────────────────────────────────────────────────────
# Literal paths BEFORE parameterized paths to avoid route shadowing.

@router.post("/dungeons/enter", response_model=Dungeon, status_code=201)
async def enter_dungeon(payload: EnterRequest):
    db = get_db()

    # Idempotent: return existing dungeon
    existing = list(db.collection("dungeons").where("poi_id", "==", payload.poi_id).limit(1).stream())
    if existing:
        return _doc_to_dungeon(existing[0])

    poi_doc = db.collection("pois").document(payload.poi_id).get()
    if not poi_doc.exists:
        raise HTTPException(status_code=404, detail="POI not found")
    poi = _doc_to_poi(poi_doc)
    if poi.type != "dungeon":
        raise HTTPException(status_code=400, detail="POI is not a dungeon")

    floor_count = poi.tier  # T1 = 1 floor, T2 = 2, T3 = 3
    budget_ranges = {1: (8, 12), 2: (9, 14), 3: (10, 16)}
    lo, hi = budget_ranges[poi.tier]

    rng = tile_rng(poi.map_id, poi.tile_x, poi.tile_y, extra=1)
    door_budget_per_floor = {
        str(f): rng.randint(lo, hi) for f in range(1, floor_count + 1)
    }

    dungeon = Dungeon(
        adventure_id=payload.adventure_id,
        poi_id=payload.poi_id,
        floor_count=floor_count,
        door_budget_per_floor=door_budget_per_floor,
    )
    db.collection("dungeons").document(dungeon.id).set(dungeon.model_dump())

    # Create entrance room on floor 1
    entrance_exits = _entrance_exits(rng, floor_count, current_floor=1)
    entrance = DungeonRoom(
        adventure_id=payload.adventure_id,
        dungeon_id=dungeon.id,
        floor=1,
        x=0,
        y=0,
        is_entrance=True,
        exits=entrance_exits,
    )
    db.collection("dungeon_rooms").document(entrance.id).set(entrance.model_dump())

    return dungeon


@router.get("/dungeons/by-poi/{poi_id}", response_model=Dungeon)
async def get_dungeon_by_poi(poi_id: str):
    db = get_db()
    docs = list(db.collection("dungeons").where("poi_id", "==", poi_id).limit(1).stream())
    if not docs:
        raise HTTPException(status_code=404, detail="Dungeon not yet entered")
    return _doc_to_dungeon(docs[0])


@router.get("/dungeons/{dungeon_id}", response_model=Dungeon)
async def get_dungeon(dungeon_id: str):
    db = get_db()
    doc = db.collection("dungeons").document(dungeon_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Dungeon not found")
    return _doc_to_dungeon(doc)


@router.get("/dungeons/{dungeon_id}/rooms", response_model=list[DungeonRoom])
async def list_rooms(dungeon_id: str, floor: int | None = None):
    db = get_db()
    q = db.collection("dungeon_rooms").where("dungeon_id", "==", dungeon_id)
    if floor is not None:
        q = q.where("floor", "==", floor)
    return [_doc_to_room(d) for d in q.stream()]


@router.post("/dungeons/{dungeon_id}/rooms/explore", response_model=DungeonRoom)
async def explore_room(dungeon_id: str, payload: ExploreRequest):
    from ..utils.poi_gen import generate_next_room_exits, _DELTAS, _OPPOSITE

    db = get_db()

    # Fetch the room we're leaving from
    from_doc = db.collection("dungeon_rooms").document(payload.from_room_id).get()
    if not from_doc.exists:
        raise HTTPException(status_code=404, detail="from_room not found")
    from_room = _doc_to_room(from_doc)

    dungeon_doc = db.collection("dungeons").document(dungeon_id).get()
    if not dungeon_doc.exists:
        raise HTTPException(status_code=404, detail="Dungeon not found")
    dungeon = _doc_to_dungeon(dungeon_doc)

    # Find the exit being used
    exit_obj = next((e for e in from_room.exits if e.direction == payload.direction), None)
    if exit_obj is None:
        raise HTTPException(status_code=404, detail="No exit in that direction")

    # Idempotent: room already generated
    if exit_obj.leads_to_room_id:
        new_doc = db.collection("dungeon_rooms").document(exit_obj.leads_to_room_id).get()
        if new_doc.exists:
            return _doc_to_room(new_doc)

    # Compute new position
    direction = payload.direction
    if direction in _DELTAS:
        new_x = from_room.x + _DELTAS[direction][0]
        new_y = from_room.y + _DELTAS[direction][1]
        new_floor = from_room.floor
    elif direction == "down":
        new_x, new_y = 0, 0
        new_floor = from_room.floor + 1
    elif direction == "up":
        new_x, new_y = 0, 0
        new_floor = from_room.floor - 1
    else:
        raise HTTPException(status_code=400, detail="Invalid direction")

    if not (1 <= new_floor <= dungeon.floor_count):
        raise HTTPException(status_code=400, detail="Target floor out of range")

    # Build existing_rooms map for the target floor
    floor_docs = [
        _doc_to_room(doc)
        for doc in db.collection("dungeon_rooms").where("dungeon_id", "==", dungeon_id).stream()
        if doc.to_dict().get("floor") == new_floor
    ]
    existing_rooms: dict[tuple[int, int], DungeonRoom] = {
        (r.x, r.y): r for r in floor_docs
    }

    budget_key = str(new_floor)
    door_budget = dungeon.door_budget_per_floor.get(budget_key, 0)
    stairs_placed = dungeon.stairs_placed.get(budget_key, False)

    # Boss room: deepest floor and budget exhausted
    is_boss_room = (new_floor == dungeon.floor_count and door_budget <= 0)

    # Deterministic RNG for this specific room position
    source_poi = dungeon.poi_id or dungeon.ruin_structure_id or dungeon.id
    rng = tile_rng(source_poi, new_x + new_floor * 1000, new_y, extra=2)

    exits, doors_consumed = generate_next_room_exits(
        current_x=new_x,
        current_y=new_y,
        current_floor=new_floor,
        from_direction=direction,
        existing_rooms=existing_rooms,
        door_budget=door_budget,
        floor_count=dungeon.floor_count,
        stairs_placed=stairs_placed,
        is_boss_room=is_boss_room,
        rng=rng,
    )

    new_room = DungeonRoom(
        adventure_id=from_room.adventure_id,
        dungeon_id=dungeon_id,
        floor=new_floor,
        x=new_x,
        y=new_y,
        is_boss_room=is_boss_room,
        exits=exits,
    )
    db.collection("dungeon_rooms").document(new_room.id).set(new_room.model_dump())

    # Stamp from_room's exit with the new room id
    updated_from_exits = [
        e.model_copy(update={"leads_to_room_id": new_room.id}) if e.direction == direction else e
        for e in from_room.exits
    ]
    db.collection("dungeon_rooms").document(from_room.id).update(
        {"exits": [e.model_dump() for e in updated_from_exits]}
    )

    # Stamp new room's return exit with from_room id
    return_dir = _OPPOSITE[direction]
    updated_new_exits = [
        e.model_copy(update={"leads_to_room_id": from_room.id}) if e.direction == return_dir else e
        for e in new_room.exits
    ]
    db.collection("dungeon_rooms").document(new_room.id).update(
        {"exits": [e.model_dump() for e in updated_new_exits]}
    )

    # Update dungeon budget and stair tracking
    dungeon_updates: dict = {
        f"door_budget_per_floor.{budget_key}": max(0, door_budget - doors_consumed)
    }
    if any(e.direction in ("down", "up") for e in exits):
        dungeon_updates[f"stairs_placed.{budget_key}"] = True
    db.collection("dungeons").document(dungeon_id).update(dungeon_updates)

    # Return with stamped exits
    final_doc = db.collection("dungeon_rooms").document(new_room.id).get()
    return _doc_to_room(final_doc)


@router.patch("/dungeons/rooms/{room_id}", response_model=DungeonRoom)
async def update_room(room_id: str, payload: DungeonRoomUpdate):
    db = get_db()
    ref = db.collection("dungeon_rooms").document(room_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Room not found")
    updates = payload.model_dump(exclude_none=True)
    if updates:
        ref.update(updates)
    return _doc_to_room(ref.get())


# ── Settlement Endpoints ──────────────────────────────────────────────────────

@router.post("/settlements/enter", response_model=Settlement, status_code=201)
async def enter_settlement(payload: SettlementEnterRequest):
    db = get_db()

    existing = list(db.collection("settlements").where("poi_id", "==", payload.poi_id).limit(1).stream())
    if existing:
        return _doc_to_settlement(existing[0])

    poi_doc = db.collection("pois").document(payload.poi_id).get()
    if not poi_doc.exists:
        raise HTTPException(status_code=404, detail="POI not found")
    poi = _doc_to_poi(poi_doc)
    if poi.type != "settlement":
        raise HTTPException(status_code=400, detail="POI is not a settlement")

    rng = tile_rng(poi.map_id, poi.tile_x, poi.tile_y, extra=3)
    location_count = select_location_count(poi.tier, rng)

    from ..models.poi import SettlementLocation
    settlement = Settlement(
        adventure_id=payload.adventure_id,
        poi_id=payload.poi_id,
        location_count=location_count,
        locations=[SettlementLocation() for _ in range(location_count)],
    )
    db.collection("settlements").document(settlement.id).set(settlement.model_dump())
    return settlement


@router.get("/settlements/by-poi/{poi_id}", response_model=Settlement)
async def get_settlement_by_poi(poi_id: str):
    db = get_db()
    docs = list(db.collection("settlements").where("poi_id", "==", poi_id).limit(1).stream())
    if not docs:
        raise HTTPException(status_code=404, detail="Settlement not yet entered")
    return _doc_to_settlement(docs[0])


@router.get("/settlements/{settlement_id}", response_model=Settlement)
async def get_settlement(settlement_id: str):
    db = get_db()
    doc = db.collection("settlements").document(settlement_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return _doc_to_settlement(doc)


@router.patch("/settlements/{settlement_id}", response_model=Settlement)
async def update_settlement(settlement_id: str, payload: SettlementUpdate):
    db = get_db()
    ref = db.collection("settlements").document(settlement_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Settlement not found")
    updates = payload.model_dump(exclude_none=True)
    if updates:
        ref.update(updates)
    return _doc_to_settlement(ref.get())


# ── Ruins Endpoints ───────────────────────────────────────────────────────────

@router.post("/ruins/enter", response_model=Ruin, status_code=201)
async def enter_ruin(payload: RuinEnterRequest):
    db = get_db()

    existing = list(db.collection("ruins").where("poi_id", "==", payload.poi_id).limit(1).stream())
    if existing:
        return _doc_to_ruin(existing[0])

    poi_doc = db.collection("pois").document(payload.poi_id).get()
    if not poi_doc.exists:
        raise HTTPException(status_code=404, detail="POI not found")
    poi = _doc_to_poi(poi_doc)
    if poi.type != "ruins":
        raise HTTPException(status_code=400, detail="POI is not a ruin")

    rng = tile_rng(poi.map_id, poi.tile_x, poi.tile_y, extra=4)
    structure_count = select_structure_count(poi.tier, rng)
    structures = [
        RuinStructure(floor_count=select_structure_floors(rng))
        for _ in range(structure_count)
    ]

    ruin = Ruin(
        adventure_id=payload.adventure_id,
        poi_id=payload.poi_id,
        structures=structures,
    )
    db.collection("ruins").document(ruin.id).set(ruin.model_dump())
    return ruin


@router.get("/ruins/by-poi/{poi_id}", response_model=Ruin)
async def get_ruin_by_poi(poi_id: str):
    db = get_db()
    docs = list(db.collection("ruins").where("poi_id", "==", poi_id).limit(1).stream())
    if not docs:
        raise HTTPException(status_code=404, detail="Ruin not yet entered")
    return _doc_to_ruin(docs[0])


@router.get("/ruins/{ruin_id}", response_model=Ruin)
async def get_ruin(ruin_id: str):
    db = get_db()
    doc = db.collection("ruins").document(ruin_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Ruin not found")
    return _doc_to_ruin(doc)


@router.post("/ruins/{ruin_id}/structures/{structure_id}/enter", response_model=Dungeon, status_code=201)
async def enter_ruin_structure(ruin_id: str, structure_id: str):
    db = get_db()

    ruin_doc = db.collection("ruins").document(ruin_id).get()
    if not ruin_doc.exists:
        raise HTTPException(status_code=404, detail="Ruin not found")
    ruin = _doc_to_ruin(ruin_doc)

    structure = next((s for s in ruin.structures if s.id == structure_id), None)
    if structure is None:
        raise HTTPException(status_code=404, detail="Structure not found in ruin")

    # Idempotent: structure already entered
    if structure.dungeon_id:
        dungeon_doc = db.collection("dungeons").document(structure.dungeon_id).get()
        if dungeon_doc.exists:
            return _doc_to_dungeon(dungeon_doc)

    # Roll door budgets (smaller than standalone dungeon)
    import hashlib as _hl
    _seed = int.from_bytes(_hl.md5(structure_id.encode()).digest()[:4], "big")
    rng = tile_rng(ruin_id, _seed, 0, extra=5)
    door_budget_per_floor = {
        str(f): select_structure_budget(structure.floor_count, rng)
        for f in range(1, structure.floor_count + 1)
    }

    dungeon = Dungeon(
        adventure_id=ruin.adventure_id,
        poi_id=None,
        ruin_structure_id=structure_id,
        floor_count=structure.floor_count,
        door_budget_per_floor=door_budget_per_floor,
    )
    db.collection("dungeons").document(dungeon.id).set(dungeon.model_dump())

    # Create entrance room
    entrance_exits = _entrance_exits(rng, structure.floor_count, current_floor=1)
    entrance = DungeonRoom(
        adventure_id=ruin.adventure_id,
        dungeon_id=dungeon.id,
        floor=1,
        x=0,
        y=0,
        is_entrance=True,
        exits=entrance_exits,
    )
    db.collection("dungeon_rooms").document(entrance.id).set(entrance.model_dump())

    # Stamp dungeon_id back onto the RuinStructure
    updated_structures = [
        s.model_copy(update={"dungeon_id": dungeon.id}) if s.id == structure_id else s
        for s in ruin.structures
    ]
    db.collection("ruins").document(ruin_id).update(
        {"structures": [s.model_dump() for s in updated_structures]}
    )

    return dungeon
