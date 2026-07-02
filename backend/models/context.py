from typing import Literal
from pydantic import BaseModel, Field
from .shared import BaseDocument


# ── ContextCard ────────────────────────────────────────────────────────────────
# Snippets of lore or rules injected into DM prompts based on triggers.
# A card with always_inject=True acts as the World Bible entry point.

class ContextCardCreate(BaseModel):
    """Payload for POST /context-cards."""
    adventure_id: str
    label: str
    content: str
    keyword_trigger: str | None = None
    event_trigger: str | None = None
    always_inject: bool = False


class ContextCard(BaseDocument):
    """Full ContextCard document as stored in Firestore."""
    label: str
    content: str
    keyword_trigger: str | None = None
    event_trigger: str | None = None
    always_inject: bool = False


class ContextCardUpdate(BaseModel):
    """Payload for PATCH /context-cards/{id}. All fields optional."""
    label: str | None = None
    content: str | None = None
    keyword_trigger: str | None = None
    event_trigger: str | None = None
    always_inject: bool | None = None


# ── WorldState ─────────────────────────────────────────────────────────────────
# Running log of canonical facts for one adventure. One document per adventure.
# token_count tracks prompt size; summarization is triggered at 1500 tokens.

class WorldStateCreate(BaseModel):
    """Payload for POST /world-state."""
    adventure_id: str
    facts: list[str] = Field(default_factory=list)


class WorldState(BaseDocument):
    """Full WorldState document as stored in Firestore."""
    facts: list[str] = Field(default_factory=list)
    token_count: int = 0


class WorldStateFactsAppend(BaseModel):
    """Payload for PATCH /world-state/{id}/facts — appends, never overwrites."""
    facts: list[str]


# ── RelationshipEdge ───────────────────────────────────────────────────────────
# One directed edge in the character relationship graph: A's perception of B.
# All weights are independent — fear and submission can coexist with high affinity.

class RelationshipEdgeCreate(BaseModel):
    """Payload for POST /relationships."""
    adventure_id: str
    from_id: str
    to_id: str
    affinity: float = 0.0    # -1.0 (hostile) to 1.0 (friendly)
    fear: float = 0.0        # 0.0 to 1.0
    submission: float = 0.0  # 0.0 to 1.0


class RelationshipEdge(BaseDocument):
    """Full RelationshipEdge document as stored in Firestore."""
    from_id: str
    to_id: str
    affinity: float = 0.0
    fear: float = 0.0
    submission: float = 0.0


class RelationshipEdgeUpdate(BaseModel):
    """Payload for PATCH /relationships/{id}. All fields optional."""
    affinity: float | None = None
    fear: float | None = None
    submission: float | None = None


# ── RelationshipMap ────────────────────────────────────────────────────────────
# Assembled on demand from all edges in an adventure — never stored in Firestore.

class RelationshipMap(BaseModel):
    nodes: list[str]
    edges: list[RelationshipEdge]


# ── Ripple ─────────────────────────────────────────────────────────────────────
# Propagate a single weight change from A→B transitively to all C who know both.

RIPPLE_WEIGHTS = Literal["affinity", "fear", "submission"]


class RippleRequest(BaseModel):
    adventure_id: str
    from_id: str
    to_id: str
    weight: RIPPLE_WEIGHTS
    delta: float
