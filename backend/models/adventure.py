from pydantic import BaseModel


class Adventure(BaseModel):
    id: str
    name: str
    world_name: str
    world_map_id: str | None = None
    invite_code: str
    created_at: str


class AdventureCreate(BaseModel):
    adventure_id: str
    name: str
    world_name: str
    world_map_id: str | None = None
