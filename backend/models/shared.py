import uuid
from pydantic import BaseModel, Field


def new_id() -> str:
    """Generate a fresh UUID string. Used as the default factory for all document IDs."""
    return str(uuid.uuid4())


class BaseDocument(BaseModel):
    """Fields every Firestore document has."""
    id: str = Field(default_factory=new_id)
    adventure_id: str

    class Config:
        # Allow population from Firestore dict keys like "adventure_id"
        populate_by_name = True
