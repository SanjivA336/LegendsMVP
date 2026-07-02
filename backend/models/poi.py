from typing import Literal
from pydantic import BaseModel, Field
from .shared import BaseDocument, new_id


POIType = Literal["settlement", "encampment", "dungeon", "ruins"]


# ── POI ───────────────────────────────────────────────────────────────────────

class POICreate(BaseModel):
    adventure_id: str
    map_id: str
    tile_x: int
    tile_y: int
    type: POIType
    tier: int
    detail_card_id: str | None = None


class POI(BaseDocument):
    map_id: str
    tile_x: int
    tile_y: int
    type: POIType
    tier: int
    detail_card_id: str | None = None
    generated: bool = False


class POIUpdate(BaseModel):
    detail_card_id: str | None = None
    generated: bool | None = None


# ── Dungeon ───────────────────────────────────────────────────────────────────

class Exit(BaseModel):
    direction: Literal["north", "south", "east", "west", "down", "up"]
    leads_to_room_id: str | None = None   # None = promise
    leads_to_floor: int | None = None     # stair exits only


class Dungeon(BaseDocument):
    poi_id: str | None = None             # None if this dungeon belongs to a ruin structure
    ruin_structure_id: str | None = None  # None if standalone dungeon POI
    floor_count: int
    door_budget_per_floor: dict[str, int]
    stairs_placed: dict[str, bool] = Field(default_factory=dict)
    floors_initialized: list[int] = Field(default_factory=list)


class DungeonRoom(BaseModel):
    id: str = Field(default_factory=new_id)
    adventure_id: str
    dungeon_id: str
    floor: int
    x: int
    y: int
    is_entrance: bool = False
    is_boss_room: bool = False
    exits: list[Exit] = Field(default_factory=list)
    content: list[str] = Field(default_factory=list)


class DungeonRoomUpdate(BaseModel):
    exits: list[Exit] | None = None
    content: list[str] | None = None


# ── Settlement ────────────────────────────────────────────────────────────────

class SettlementLocation(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str | None = None
    detail_card_id: str | None = None


class Settlement(BaseDocument):
    poi_id: str
    location_count: int
    locations: list[SettlementLocation] = Field(default_factory=list)
    generated: bool = False


class SettlementUpdate(BaseModel):
    locations: list[SettlementLocation] | None = None
    generated: bool | None = None


# ── Ruins ─────────────────────────────────────────────────────────────────────

class RuinStructure(BaseModel):
    id: str = Field(default_factory=new_id)
    label: str | None = None
    floor_count: int
    dungeon_id: str | None = None


class Ruin(BaseDocument):
    poi_id: str
    structures: list[RuinStructure] = Field(default_factory=list)
    generated: bool = False


class RuinUpdate(BaseModel):
    structures: list[RuinStructure] | None = None


# ── Request bodies ────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    adventure_id: str
    map_id: str
    tile_x: int
    tile_y: int


class EnterRequest(BaseModel):
    adventure_id: str
    poi_id: str


class ExploreRequest(BaseModel):
    from_room_id: str
    direction: str


class SettlementEnterRequest(BaseModel):
    adventure_id: str
    poi_id: str


class RuinEnterRequest(BaseModel):
    adventure_id: str
    poi_id: str
