from typing import Literal
from pydantic import BaseModel, Field
from .shared import BaseDocument, new_id
from .event import EventCondition

QuestLength = Literal["short", "medium", "long"]
QuestStatus = Literal["active", "completed", "failed"]
StepStatus  = Literal["pending", "active", "completed", "failed"]

# Middle step counts by quest length (excludes first and last steps)
_MIDDLE_RANGES: dict[str, tuple[int, int]] = {
    "short":  (1, 2),   # 3–4  total steps
    "medium": (3, 5),   # 5–7  total steps
    "long":   (6, 10),  # 8–12 total steps
}

# Minimum pending middle steps to maintain between current position and last_step.
# When a step fails with fewer than this many steps remaining, recovery steps are generated.
FAILURE_BUFFER = 2


class QuestStep(BaseModel):
    id: str = Field(default_factory=new_id)
    description: str
    completion_condition: str                        # human-readable display text
    completion_event: EventCondition | None = None   # None → LLM judge via resolve-step
    failure_event: EventCondition | None = None      # optional: event that auto-fails this step
    status: StepStatus = "pending"
    narrative_on_complete: str | None = None


class QuestCreate(BaseModel):
    adventure_id: str
    length: QuestLength
    context_hint: str = ""   # optional DM nudge ("the stolen artifact", "find the heir", ...)


class Quest(BaseDocument):
    title: str
    length: QuestLength
    status: QuestStatus = "active"
    target_middle_count: int             # rolled at creation; controls when to stop generating middles
    first_step: QuestStep
    last_step: QuestStep
    middle_steps: list[QuestStep] = Field(default_factory=list)


class QuestUpdate(BaseModel):
    status: QuestStatus | None = None
    title: str | None = None


class QuestStepUpdate(BaseModel):
    status: StepStatus | None = None
    narrative_on_complete: str | None = None


class ResolveStepRequest(BaseModel):
    recent_context: str     # last 2–3 player actions as text — only used when completion_event is None
    world_state_id: str     # used to pull current facts for the DM prompt


class ResolveStepResult(BaseModel):
    quest: Quest
    step_completed: bool
    narrative: str
    quest_completed: bool = False
