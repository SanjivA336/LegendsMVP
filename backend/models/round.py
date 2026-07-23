from typing import Literal
from pydantic import BaseModel, Field
from .shared import new_id

ParticipantKind = Literal["human", "actor"]
EntryStatus = Literal["awaiting", "submitted", "passed"]
RoundStatus = Literal["collecting", "awaiting_checks", "resolving", "resolved"]


class RoundEntry(BaseModel):
    character_id: str
    character_name: str = "Unknown"
    kind: ParticipantKind
    actor_id: str | None = None
    status: EntryStatus = "awaiting"
    text: str | None = None
    submitted_at: str | None = None


class PendingRound(BaseModel):
    id: str = Field(default_factory=new_id)
    encounter_id: str
    adventure_id: str
    round_number: int = 1
    status: RoundStatus = "collecting"
    entries: list[RoundEntry] = Field(default_factory=list)
    created_at: str
    resolved_at: str | None = None
    narrative: str | None = None


CheckStatus = Literal["pending", "resolved"]


class PendingCheck(BaseModel):
    id: str = Field(default_factory=new_id)
    encounter_id: str
    round_number: int
    character_id: str
    character_name: str
    skill_key: str
    skill_name: str
    minigame_id: str = "dice-roll"
    show_target: bool = True
    target: float | None = None
    adv_disadv: int = 0
    die_size: int = 20
    status: CheckStatus = "pending"
    raw_result: dict | None = None
    score: float | None = None
