from typing import Literal
from pydantic import BaseModel


class Adventure(BaseModel):
    id: str
    name: str
    world_name: str
    world_map_id: str | None = None
    invite_code: str
    dm_mode: Literal["ai", "human"] | None = None
    created_at: str


class AdventureCreate(BaseModel):
    adventure_id: str
    name: str
    world_name: str
    world_map_id: str | None = None
    invite_code: str | None = None   # wizard generates this client-side at the Invite step;
                                      # falls back to server-generated when omitted


class AdventureUpdate(BaseModel):
    name: str | None = None
    world_name: str | None = None
    world_map_id: str | None = None   # set once the wizard's Launch step commits the
                                        # previewed map for real (adventure is created first,
                                        # since /world-maps requires an adventure_id)
    dm_mode: Literal["ai", "human"] | None = None
