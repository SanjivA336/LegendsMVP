"""
Shared test infrastructure: in-memory Firestore mock + deterministic AI provider mock.

Usage:
    from tests.mock_infra import MockDB, MockAIProvider, make_client
"""

import uuid
import sys
from unittest.mock import MagicMock


# ── Prevent firebase_admin from touching the network during import ──────────────
def _stub_firebase():
    fb = MagicMock()
    fb.credentials = MagicMock()
    fb.firestore = MagicMock()
    fb.auth = MagicMock()
    sys.modules.setdefault("firebase_admin", fb)
    sys.modules.setdefault("firebase_admin.credentials", fb.credentials)
    sys.modules.setdefault("firebase_admin.firestore", fb.firestore)
    sys.modules.setdefault("firebase_admin.auth", fb.auth)

_stub_firebase()


# ── In-memory Firestore ───────────────────────────────────────────────────────

class _Doc:
    """Simulates a Firestore DocumentSnapshot."""
    def __init__(self, id_: str, data: dict | None):
        self.id = id_
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict:
        return dict(self._data) if self._data else {}


class _Query:
    """Simulates a Firestore Query (supports chained where / limit / stream)."""
    def __init__(self, docs: list[_Doc]):
        self._docs = docs
        self._limit_n: int | None = None

    def where(self, field: str, op: str, value) -> "_Query":
        if op == "==":
            filtered = [d for d in self._docs if d._data and d._data.get(field) == value]
        elif op == "!=":
            filtered = [d for d in self._docs if d._data and d._data.get(field) != value]
        elif op == ">":
            filtered = [d for d in self._docs if d._data and d._data.get(field) is not None and d._data.get(field) > value]
        elif op == "<":
            filtered = [d for d in self._docs if d._data and d._data.get(field) is not None and d._data.get(field) < value]
        else:
            filtered = list(self._docs)
        return _Query(filtered)

    def limit(self, n: int) -> "_Query":
        q = _Query(self._docs)
        q._limit_n = n
        return q

    def order_by(self, field: str, **kwargs) -> "_Query":
        reverse = kwargs.get("direction") == "DESCENDING"
        sorted_docs = sorted(
            self._docs,
            key=lambda d: d._data.get(field, 0) if d._data else 0,
            reverse=reverse,
        )
        return _Query(sorted_docs)

    def stream(self):
        docs = self._docs
        if self._limit_n is not None:
            docs = docs[: self._limit_n]
        return iter(docs)


class _DocRef:
    """Simulates a Firestore DocumentReference."""
    def __init__(self, store: dict, col: str, id_: str):
        self._s = store
        self._c = col
        self._id = id_

    def set(self, data: dict):
        self._s.setdefault(self._c, {})[self._id] = dict(data)

    def get(self) -> _Doc:
        return _Doc(self._id, self._s.get(self._c, {}).get(self._id))

    def update(self, data: dict):
        col = self._s.setdefault(self._c, {})
        col.setdefault(self._id, {}).update(data)

    def delete(self):
        self._s.get(self._c, {}).pop(self._id, None)


class _Col:
    """Simulates a Firestore CollectionReference."""
    def __init__(self, store: dict, name: str):
        self._s = store
        self._n = name

    def document(self, id_: str | None = None) -> _DocRef:
        return _DocRef(self._s, self._n, id_ or str(uuid.uuid4()))

    def where(self, field: str, op: str, value) -> _Query:
        all_docs = [_Doc(k, d) for k, d in self._s.get(self._n, {}).items()]
        return _Query(all_docs).where(field, op, value)

    def stream(self) -> iter:
        all_docs = [_Doc(k, d) for k, d in self._s.get(self._n, {}).items()]
        return iter(all_docs)


class MockDB:
    """In-memory Firestore replacement. Each instance is isolated."""
    def __init__(self):
        self._store: dict[str, dict[str, dict]] = {}

    def collection(self, name: str) -> _Col:
        return _Col(self._store, name)

    def get_all(self, refs: list[_DocRef]) -> list[_Doc]:
        """Simulates Firestore's batched multi-get (Client.get_all)."""
        return [ref.get() for ref in refs]

    def dump(self) -> dict:
        """Debug helper — returns the full in-memory store."""
        return dict(self._store)


# ── Mock AI Provider ──────────────────────────────────────────────────────────

_QUEST_STEP = {
    "description": "Find the artifact",
    "completion_condition": "The artifact is retrieved",
    "completion_event": None,
    "failure_event": None,
}

MOCK_RESPONSES = {
    "arena": {
        "narrative": "A stone chamber with scattered rubble.",
        "updates": {
            "arena": {
                "tiles": [
                    {"x": 5, "y": 5, "terrain_tag": "water", "movement_cost": 2},
                ],
                "edges": [
                    {"x": 3, "y": 3, "direction": "east", "level": 1},
                    {"x": 4, "y": 3, "direction": "west", "level": 1},
                ],
                "objects": [
                    {"x": 10, "y": 10, "type": "cache", "item_ids": []},
                    {"x": 7, "y": 7, "type": "bulwark"},
                ],
            }
        },
    },
    "narrate": {"narrative": "The warrior strikes with fury, drawing blood."},
    "combat_end": {"narrative": "Silence falls over the arena. The battle is won."},
    "quest": {
        "narrative": "A perilous quest awaits.",
        "updates": {
            "new_quest": {
                "title": "The Lost Relic",
                "first_step": dict(_QUEST_STEP, description="Search the old ruins"),
                "last_step": dict(_QUEST_STEP, description="Return the relic to the elder"),
                "entities_to_create": [],
            }
        },
    },
    "resolve_step": {
        "narrative": "The hero has succeeded.",
        "updates": {"quest_step_complete": True, "narrative_on_complete": "Step done."},
    },
    "resolve_step_incomplete": {
        "narrative": "Not quite there yet.",
        "updates": {"quest_step_complete": False},
    },
    "next_step": {
        "narrative": "The next challenge emerges.",
        "updates": {
            "next_step": {
                "description": "Gather allies",
                "completion_condition": "Three allies joined",
                "completion_event": None,
                "failure_event": None,
            },
            "world_state_additions": [],
            "entities_to_create": [],
        },
    },
    "recovery_steps": {
        "narrative": "There is still a path forward.",
        "updates": {
            "recovery_steps": [
                {
                    "description": "Find another way",
                    "completion_condition": "Alternative route found",
                    "completion_event": None,
                    "failure_event": None,
                }
            ],
            "world_state_additions": [],
        },
    },
    "poi": {
        "narrative": "A dungeon of dark stone.",
        "updates": {
            "poi_data": {"description": "Dank corridors", "rooms": []},
            "world_state_additions": [],
        },
    },
    "world_map": {
        "narrative": "A vast land stretches before you.",
        "updates": {"world_state_additions": []},
    },
    "theme": {
        "world_name": "Aethermoor",
        "attribute_names": {
            "strength": "Might", "dexterity": "Grace", "intelligence": "Wit",
            "fortitude": "Vigor", "charisma": "Presence", "reflex": "Reflex",
        },
        "currency_name": "Sovereigns",
        "biome_family_names": {
            "arid": "Sunbaked Wastes", "grassland": "Windward Plains", "woodland": "Deep Timber",
            "tropical": "Verdant Reach", "wetland": "Mire", "arctic": "Frostlands",
            "ocean": "Sea", "mountain": "Highpeaks", "volcanic": "Ashfields",
        },
    },
    "default": {
        "narrative": "Something happens.",
        "updates": {"world_state_additions": []},
    },
}


class MockAIProvider:
    """Deterministic AI provider that returns canned responses keyed by prompt content."""

    def __init__(self, response_key: str = "default"):
        self._response_key = response_key
        self._call_log: list[str] = []

    async def generate(self, prompt: str) -> dict:
        self._call_log.append(prompt[:80])

        p = prompt.lower()
        if "arena" in p and ("generate" in p or "tactically" in p):
            return MOCK_RESPONSES["arena"]
        if "narrate the following combat action" in p:
            return MOCK_RESPONSES["narrate"]
        if "resolution of a combat encounter" in p:
            return MOCK_RESPONSES["combat_end"]
        if "new_quest" in p or "quest_creation" in p or "quest title" in p or "new quest" in p:
            return MOCK_RESPONSES["quest"]
        if "next_step" in p or "generate the next quest step" in p:
            return MOCK_RESPONSES["next_step"]
        if "recovery_steps" in p or "failure" in p and "quest" in p:
            return MOCK_RESPONSES["recovery_steps"]
        if "resolve" in p and "step" in p:
            return MOCK_RESPONSES["resolve_step"]
        if "poi" in p or "location" in p:
            return MOCK_RESPONSES["poi"]
        if "biome_family_names" in p:
            return MOCK_RESPONSES["theme"]
        return MOCK_RESPONSES[self._response_key]
