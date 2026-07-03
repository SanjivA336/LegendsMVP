from pydantic import BaseModel


class UserPreferences(BaseModel):
    accent_color: str | None = None
    player_colors: list[str] | None = None


class User(BaseModel):
    uid: str
    email: str
    display_name: str
    created_at: str
    preferences: UserPreferences = UserPreferences()


class UserCreate(BaseModel):
    display_name: str | None = None
    preferences: UserPreferences | None = None
