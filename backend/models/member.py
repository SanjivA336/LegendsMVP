from typing import Literal
from pydantic import BaseModel
from .shared import new_id
from pydantic import Field


MemberRole = Literal["owner", "admin", "player", "viewer"]

ROLE_RANK: dict[str, int] = {"viewer": 0, "player": 1, "admin": 2, "owner": 3}


class Member(BaseModel):
    id: str = Field(default_factory=new_id)
    adventure_id: str
    user_uid: str
    role: MemberRole
    character_id: str | None = None
    display_name: str | None = None
    joined_at: str


class MemberCreate(BaseModel):
    user_uid: str
    role: MemberRole
    character_id: str | None = None


class MemberUpdate(BaseModel):
    role: MemberRole | None = None
    character_id: str | None = None
