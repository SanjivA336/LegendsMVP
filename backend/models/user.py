from pydantic import BaseModel


class User(BaseModel):
    uid: str
    email: str
    display_name: str
    created_at: str
    avatar_color: str = "#F8961E"


class UserCreate(BaseModel):
    display_name: str
