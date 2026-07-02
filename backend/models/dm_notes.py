from pydantic import BaseModel


class DmNotes(BaseModel):
    adventure_id: str
    public_notes: str = ""
    updated_at: str


class DmNotesUpdate(BaseModel):
    public_notes: str
