from typing import Literal
from pydantic import BaseModel
from .shared import BaseDocument

# Game-fact events: fired by any module as things happen in the world.
GameEventType = Literal["killed", "acquired", "delivered", "reached", "talked_to", "survived"]

# Quest lifecycle meta-events: fired internally by the quest router.
# These are written to the event log for history / ContextCard triggering but
# never matched against quest step conditions (to prevent recursive loops).
QuestEventType = Literal[
    "quest_created",
    "quest_step_completed",
    "quest_step_failed",
    "quest_completed",
    "quest_failed",
]

EventType = GameEventType | QuestEventType

_META_EVENT_TYPES: frozenset[str] = frozenset([
    "quest_created",
    "quest_step_completed",
    "quest_step_failed",
    "quest_completed",
    "quest_failed",
])


class EventCondition(BaseModel):
    """Machine-readable completion/failure trigger embedded in a QuestStep.

    Only GameEventType events can trigger steps — quest meta-events are excluded
    to prevent recursive triggering.

    Matching rule: type must equal the fired event's type, and every non-None
    field on the condition must equal the corresponding field on the event.
    None fields are wildcards.
    """
    type: GameEventType
    entity_id: str | None = None      # killed, talked_to, delivered-to
    item_id: str | None = None        # acquired (specific item), delivered (the item)
    item_type: str | None = None      # acquired (by category, not specific instance)
    poi_id: str | None = None         # reached, delivered (destination)
    tile_x: int | None = None         # reached (specific tile, if no POI)
    tile_y: int | None = None         # reached (specific tile)
    encounter_id: str | None = None   # survived
    quantity: int = 1                 # for acquired: cumulative count required


class FireEventRequest(BaseModel):
    adventure_id: str
    type: EventType
    entity_id: str | None = None
    item_id: str | None = None
    item_type: str | None = None
    poi_id: str | None = None
    tile_x: int | None = None
    tile_y: int | None = None
    encounter_id: str | None = None
    quest_id: str | None = None       # set for quest lifecycle meta-events


class Event(BaseDocument):
    type: EventType
    entity_id: str | None = None
    item_id: str | None = None
    item_type: str | None = None
    poi_id: str | None = None
    tile_x: int | None = None
    tile_y: int | None = None
    encounter_id: str | None = None
    quest_id: str | None = None


class FireEventResult(BaseModel):
    event_id: str
    quests_advanced: list[str] = []   # quest IDs whose active step completed
    quests_failed: list[str] = []     # quest IDs that transitioned to "failed"
