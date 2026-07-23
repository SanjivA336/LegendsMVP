from typing import Literal
from pydantic import BaseModel, Field
from .shared import BaseDocument, new_id


# ── AI Component Types ─────────────────────────────────────────────────────────

MovementType     = Literal["ground", "air", "sea", "teleport"]
TargetSelection  = Literal["closest", "furthest", "strongest", "weakest", "last_assailant", "random"]
IntelligenceType = Literal["drone", "beast", "lurker", "soldier", "alpha"]


class AIProfile(BaseModel):
    movement_type: MovementType = "ground"
    preferred_distance: int = 1
    target_selection: TargetSelection = "closest"
    intelligence: IntelligenceType = "drone"
    last_assailant_id: str | None = None


# ── Tile System ───────────────────────────────────────────────────────────────

class ArenaTile(BaseModel):
    passable: bool = True
    terrain_tag: str = "floor"
    elevation: int = 0
    movement_cost: int = 1               # cost for ground/sea movement; 2 = difficult terrain
    aura: str | None = None              # status tag applied each round to any unit standing here
    hazard: int = 0                      # HP damage dealt when a unit enters this tile
    edges: list[int] = Field(default_factory=lambda: [0, 0, 0, 0])
    # edges = [N, E, S, W]; indices 0-3 correspond to directions
    # 0 = open; 1 = cover (partial block, +1 move cost, -1 damage die vs units here)
    # 2 = barrier (blocks ground/sea; air passes unless arena.indoor)
    # 3 = sealed (blocks all including air; underground / enclosed spaces)


# ── Arena Objects ─────────────────────────────────────────────────────────────

ArenaObjectType = Literal["bulwark", "cache"]


class ArenaObject(BaseModel):
    id: str = Field(default_factory=new_id)
    x: int
    y: int
    object_type: ArenaObjectType
    item_ids: list[str] = Field(default_factory=list)  # cache only
    looted: bool = False                                 # cache only


# ── Arena Combatant ───────────────────────────────────────────────────────────

class ArenaCombatant(BaseModel):
    id: str                               # references characters collection
    x: int
    y: int
    team: int                             # 1 = players, 2 = enemies, 3+ = third parties
    hp: int
    max_hp: int
    stats: dict[str, int] = Field(default_factory=dict)  # snapshot of Stats at arena creation
    equipped_weapon_id: str | None = None                 # snapshot for weapon damage lookup
    ai_profile: AIProfile | None = None   # copied from Character.ai_profile; None for players
    status: list[str] = Field(default_factory=list)


# ── Arena (in-memory, Firestore only for encampments) ─────────────────────────

class Arena(BaseModel):
    id: str = Field(default_factory=new_id)
    encounter_id: str
    adventure_id: str
    width: int
    height: int
    indoor: bool = False                  # True → level-2 edges also block air units
    tiles: list[list[ArenaTile]]          # [y][x] indexed
    objects: list[ArenaObject] = Field(default_factory=list)
    combatants: list[ArenaCombatant]
    turn_order: list[str]                 # character IDs sorted by initiative descending
    current_turn_idx: int = 0
    round: int = 1
    teams: dict[str, int]                 # char_id → team number
    persisted: bool = False               # True only for encampment arenas


# ── Persisted Models ──────────────────────────────────────────────────────────

EncounterStatus = Literal["pending", "active", "completed", "fled"]


class EncounterCreate(BaseModel):
    adventure_id: str
    mode: str = "combat"
    location_id: str | None = None
    stage_ids: list[str] = Field(default_factory=list)


class Encounter(BaseDocument):
    mode: str = "combat"
    location_id: str | None = None
    stage_ids: list[str] = Field(default_factory=list)
    status: EncounterStatus = "pending"
    arena_id: str | None = None           # set when arena is persisted (encampments only)
    last_dm_narrative: str | None = None  # denormalized so actor auto-submit doesn't need to scan action history


class EncounterUpdate(BaseModel):
    stage_ids: list[str] | None = None
    status: EncounterStatus | None = None


class ActionRecord(BaseDocument):
    encounter_id: str
    actor_id: str
    action_type: str
    target_id: str | None = None
    description: str = ""
    dice_results: list[int] = Field(default_factory=list)
    outcome: str = ""
    narrative: str = ""
    round_number: int = 0
    sequence: int = 0
    display_name: str | None = None
    speech: str | None = None
    action_text: str | None = None


# ── Request / Response Bodies ─────────────────────────────────────────────────

class StartCombatRequest(BaseModel):
    teams: dict[str, int]                 # character_id → team number
    arena_width: int = 16
    arena_height: int = 16
    indoor: bool = False


class PlayerTurnRequest(BaseModel):
    actor_id: str
    action_type: Literal["move", "attack", "use_item", "loot", "end_turn"]
    target_id: str | None = None
    to_x: int | None = None
    to_y: int | None = None
    item_id: str | None = None
    object_id: str | None = None          # which cache to loot
    stat_key: str = "strength"            # attacker stat for roll
    dc_stat_key: str = "reflex"           # defender stat that sets DC (DC = stat + 10)


class EndCombatRequest(BaseModel):
    outcome: Literal["completed", "fled"] = "completed"


class TurnResult(BaseModel):
    arena: Arena
    action: ActionRecord
    killed: list[str] = Field(default_factory=list)
    quests_advanced: list[str] = Field(default_factory=list)
    combat_ended: bool = False
    combat_outcome: str | None = None     # "victory", "defeat", "fled"
    narrative: str = ""
    looted_items: list[str] = Field(default_factory=list)
