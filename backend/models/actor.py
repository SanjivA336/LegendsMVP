from pydantic import BaseModel, Field
from .shared import new_id


class Actor(BaseModel):
    id: str = Field(default_factory=new_id)
    owner_uid: str
    name: str
    stance: int = 3       # 1=Pacifist → 5=Berserker
    tactics: int = 3      # 1=Calculated → 5=Reckless
    disposition: int = 3  # 1=Noble → 5=Ruthless
    description: str = ""


class ActorCreate(BaseModel):
    name: str
    stance: int = 3
    tactics: int = 3
    disposition: int = 3
    description: str = ""


class ActorUpdate(BaseModel):
    name: str | None = None
    stance: int | None = None
    tactics: int | None = None
    disposition: int | None = None
    description: str | None = None


class AdventureActorSlot(BaseModel):
    id: str = Field(default_factory=new_id)
    adventure_id: str
    actor_id: str
    character_id: str | None = None
    owner_uid: str
    added_at: str


class AdventureActorSlotCreate(BaseModel):
    actor_id: str
