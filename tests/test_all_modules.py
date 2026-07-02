"""
Integration test suite for the WorldForge Engine — all 8 modules.

Run with:
    python -m pytest tests/test_all_modules.py -v
"""

# mock_infra stubs firebase_admin BEFORE any backend imports
from tests.mock_infra import MockDB, MockAIProvider

import pytest
import uuid
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


# ── Patch firebase init so the lifespan doesn't try to connect ─────────────────
@pytest.fixture(scope="session", autouse=True)
def _patch_firebase_init():
    with patch("backend.firebase.init_firestore", return_value=None):
        yield


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture()
def db():
    """Fresh in-memory Firestore for each test."""
    return MockDB()


@pytest.fixture()
def provider():
    return MockAIProvider()


@pytest.fixture()
def client(db, provider):
    """TestClient with Firebase and AI provider mocked for the duration of the test."""
    import backend.firebase as fb_module
    import backend.ai_provider as ai_module
    from backend.main import app

    original_db = fb_module._db
    fb_module._db = db

    original_provider_cls = ai_module.OllamaProvider

    async def _mock_generate(self, prompt: str) -> dict:
        return await provider.generate(prompt)

    with patch.object(ai_module.OllamaProvider, "generate", _mock_generate):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    fb_module._db = original_db


ADV = "adv-test-001"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1: Items
# ══════════════════════════════════════════════════════════════════════════════

class TestItems:
    def test_create_template(self, client):
        r = client.post("/item-templates", json={
            "adventure_id": ADV,
            "name": "Iron Sword",
            "item_type": "weapon",
            "properties": {"damage": 5},
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == "Iron Sword"
        assert data["properties"]["damage"] == 5
        return data["id"]

    def test_list_templates(self, client):
        # Create two templates
        for name in ["Axe", "Shield"]:
            client.post("/item-templates", json={"adventure_id": ADV, "name": name, "item_type": "weapon"})
        r = client.get(f"/item-templates?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_get_template_404(self, client):
        r = client.get("/item-templates/nonexistent-id")
        assert r.status_code == 404

    def test_update_template(self, client):
        r = client.post("/item-templates", json={"adventure_id": ADV, "name": "Dagger", "item_type": "weapon"})
        tid = r.json()["id"]
        r2 = client.patch(f"/item-templates/{tid}", json={"name": "Golden Dagger"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "Golden Dagger"

    def test_delete_template(self, client):
        r = client.post("/item-templates", json={"adventure_id": ADV, "name": "Junk", "item_type": "misc"})
        tid = r.json()["id"]
        r2 = client.delete(f"/item-templates/{tid}")
        assert r2.status_code == 204
        assert client.get(f"/item-templates/{tid}").status_code == 404

    def test_create_instance(self, client):
        tmpl = client.post("/item-templates", json={
            "adventure_id": ADV, "name": "Bow", "item_type": "weapon", "properties": {"damage": 3},
        }).json()
        r = client.post("/item-instances", json={
            "adventure_id": ADV, "template_id": tmpl["id"], "overrides": {"damage": 4},
        })
        assert r.status_code == 201
        data = r.json()
        assert data["template_id"] == tmpl["id"]

    def test_list_instances(self, client):
        tmpl = client.post("/item-templates", json={"adventure_id": ADV, "name": "Tome", "item_type": "misc"}).json()
        client.post("/item-instances", json={"adventure_id": ADV, "template_id": tmpl["id"]})
        r = client.get(f"/item-instances?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_update_instance(self, client):
        tmpl = client.post("/item-templates", json={"adventure_id": ADV, "name": "Staff", "item_type": "weapon"}).json()
        inst = client.post("/item-instances", json={"adventure_id": ADV, "template_id": tmpl["id"]}).json()
        r = client.patch(f"/item-instances/{inst['id']}", json={"overrides": {"enchanted": True}})
        assert r.status_code == 200

    def test_delete_instance(self, client):
        tmpl = client.post("/item-templates", json={"adventure_id": ADV, "name": "Trash", "item_type": "misc"}).json()
        inst = client.post("/item-instances", json={"adventure_id": ADV, "template_id": tmpl["id"]}).json()
        r = client.delete(f"/item-instances/{inst['id']}")
        assert r.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2: Characters
# ══════════════════════════════════════════════════════════════════════════════

_PLAYER_PAYLOAD = {
    "adventure_id": ADV,
    "name": "Aric",
    "is_player": True,
    "stats": {"strength": 14, "dexterity": 12, "intelligence": 10, "fortitude": 10, "charisma": 8, "reflex": 10},
    "max_hp": 20,
}

_NPC_PAYLOAD = {
    "adventure_id": ADV,
    "name": "Goblin Grunt",
    "is_player": False,
    "stats": {"strength": 8, "dexterity": 14, "intelligence": 6, "fortitude": 8, "charisma": 4, "reflex": 12},
    "max_hp": 10,
    "ai_profile": {
        "movement_type": "ground",
        "preferred_distance": 1,
        "target_selection": "closest",
        "intelligence": "drone",
        "last_assailant_id": None,
    },
}


class TestCharacters:
    def test_create_player(self, client):
        r = client.post("/characters", json=_PLAYER_PAYLOAD)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["name"] == "Aric"
        assert d["hp"] == d["max_hp"] == 20
        assert d["ai_profile"] is None

    def test_create_npc_with_ai_profile(self, client):
        r = client.post("/characters", json=_NPC_PAYLOAD)
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["ai_profile"]["intelligence"] == "drone"
        assert d["ai_profile"]["movement_type"] == "ground"

    def test_list_characters(self, client):
        client.post("/characters", json=_PLAYER_PAYLOAD)
        client.post("/characters", json=_NPC_PAYLOAD)
        r = client.get(f"/characters?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_get_character(self, client):
        cid = client.post("/characters", json=_PLAYER_PAYLOAD).json()["id"]
        r = client.get(f"/characters/{cid}")
        assert r.status_code == 200
        assert r.json()["id"] == cid

    def test_get_character_404(self, client):
        assert client.get("/characters/no-such-char").status_code == 404

    def test_update_character(self, client):
        cid = client.post("/characters", json=_PLAYER_PAYLOAD).json()["id"]
        r = client.patch(f"/characters/{cid}", json={"hp": 15, "name": "Aric the Bold"})
        assert r.status_code == 200
        assert r.json()["hp"] == 15
        assert r.json()["name"] == "Aric the Bold"

    def test_update_ai_profile(self, client):
        cid = client.post("/characters", json=_NPC_PAYLOAD).json()["id"]
        r = client.patch(f"/characters/{cid}", json={
            "ai_profile": {"movement_type": "air", "preferred_distance": 3,
                           "target_selection": "weakest", "intelligence": "alpha",
                           "last_assailant_id": None}
        })
        assert r.status_code == 200
        assert r.json()["ai_profile"]["intelligence"] == "alpha"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 3: Context (World State + Context Cards + Relationships)
# ══════════════════════════════════════════════════════════════════════════════

class TestContext:
    def test_create_world_state(self, client):
        r = client.post("/world-state", json={"adventure_id": ADV, "facts": ["The king is dead"]})
        assert r.status_code == 201, r.text
        assert "The king is dead" in r.json()["facts"]

    def test_get_world_state(self, client):
        client.post("/world-state", json={"adventure_id": ADV, "facts": ["Fact 1"]})
        # Endpoint is a list: GET /world-state?adventure_id=X
        r = client.get(f"/world-state?adventure_id={ADV}")
        assert r.status_code == 200
        states = r.json()
        assert len(states) >= 1
        assert states[0]["adventure_id"] == ADV

    def test_append_world_state_facts(self, client):
        state = client.post("/world-state", json={"adventure_id": ADV, "facts": ["Fact A"]}).json()
        # Endpoint: PATCH /world-state/{state_id}/facts
        r = client.patch(f"/world-state/{state['id']}/facts", json={"facts": ["Fact B", "Fact C"]})
        assert r.status_code == 200
        assert "Fact B" in r.json()["facts"]
        assert "Fact C" in r.json()["facts"]

    def test_create_context_card(self, client):
        r = client.post("/context-cards", json={
            "adventure_id": ADV,
            "label": "World Lore",
            "content": "The empire fell 100 years ago.",
            "always_inject": True,
        })
        assert r.status_code == 201, r.text
        assert r.json()["always_inject"] is True

    def test_list_context_cards(self, client):
        client.post("/context-cards", json={"adventure_id": ADV, "label": "L1", "content": "C1"})
        client.post("/context-cards", json={"adventure_id": ADV, "label": "L2", "content": "C2"})
        r = client.get(f"/context-cards?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_update_context_card(self, client):
        card = client.post("/context-cards", json={
            "adventure_id": ADV, "label": "Old", "content": "Old content"
        }).json()
        r = client.patch(f"/context-cards/{card['id']}", json={"content": "New content"})
        assert r.status_code == 200
        assert r.json()["content"] == "New content"

    def test_delete_context_card(self, client):
        card = client.post("/context-cards", json={
            "adventure_id": ADV, "label": "Temp", "content": "Disposable"
        }).json()
        r = client.delete(f"/context-cards/{card['id']}")
        assert r.status_code == 204

    def test_create_relationship_edge(self, client):
        # Fields are affinity/fear/submission directly, not nested under "weights"
        r = client.post("/relationships", json={
            "adventure_id": ADV,
            "from_id": "char-a",
            "to_id": "char-b",
            "affinity": 0.5,
            "fear": 0.2,
        })
        assert r.status_code == 201, r.text
        assert r.json()["affinity"] == 0.5
        assert r.json()["fear"] == 0.2

    def test_get_relationship_map(self, client):
        client.post("/relationships", json={
            "adventure_id": ADV, "source_id": "char-x", "target_id": "char-y",
            "weights": {"fear": 0.3},
        })
        r = client.get(f"/relationships?adventure_id={ADV}")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 4: World Map
# ══════════════════════════════════════════════════════════════════════════════

class TestWorldMap:
    def test_create_world_map(self, client):
        r = client.post("/world-maps", json={
            "adventure_id": ADV,
            "width": 32,
            "height": 32,
            "seed": 42,
        })
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["width"] == 32
        assert d["height"] == 32
        # Tiles are a flat list of {x, y, ...} dicts, not a 2D array
        assert len(d["tiles"]) == 32 * 32
        assert "x" in d["tiles"][0]
        assert "y" in d["tiles"][0]

    def test_list_world_maps(self, client):
        client.post("/world-maps", json={"adventure_id": ADV, "width": 16, "height": 16, "seed": 1})
        r = client.get(f"/world-maps?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_world_map(self, client):
        wm = client.post("/world-maps", json={"adventure_id": ADV, "width": 8, "height": 8, "seed": 7}).json()
        r = client.get(f"/world-maps/{wm['id']}")
        assert r.status_code == 200
        assert r.json()["seed"] == 7

    def test_get_world_map_404(self, client):
        assert client.get("/world-maps/no-such-map").status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 5: POIs
# ══════════════════════════════════════════════════════════════════════════════

def _discover_poi(client) -> dict | None:
    """Helper: create a world map, find a poi_candidate tile, discover a POI on it."""
    wm = client.post("/world-maps", json={"adventure_id": ADV, "width": 32, "height": 32, "seed": 99}).json()
    map_id = wm["id"]
    # Find a non-water poi_candidate tile
    candidate = next(
        (t for t in wm["tiles"] if not t.get("is_water") and t.get("poi_candidate")),
        None,
    )
    if candidate is None:
        return None
    r = client.post("/pois/discover", json={
        "adventure_id": ADV,
        "map_id": map_id,
        "tile_x": candidate["x"],
        "tile_y": candidate["y"],
    })
    if r.status_code != 201:
        return None
    return r.json()


class TestPOIs:
    def test_discover_poi(self, client):
        """POIs are created by discovering them on world map tiles."""
        wm = client.post("/world-maps", json={"adventure_id": ADV, "width": 32, "height": 32, "seed": 99}).json()
        candidate = next(
            (t for t in wm["tiles"] if not t.get("is_water") and t.get("poi_candidate")),
            None,
        )
        if candidate is None:
            pytest.skip("Seed produced no poi_candidate tiles")
        r = client.post("/pois/discover", json={
            "adventure_id": ADV,
            "map_id": wm["id"],
            "tile_x": candidate["x"],
            "tile_y": candidate["y"],
        })
        assert r.status_code == 201, r.text
        d = r.json()
        assert "id" in d
        assert d["type"] in ("dungeon", "settlement", "ruins", "encampment")

    def test_discover_poi_idempotent(self, client):
        """Discovering the same tile twice returns the same POI."""
        wm = client.post("/world-maps", json={"adventure_id": ADV, "width": 32, "height": 32, "seed": 99}).json()
        candidate = next(
            (t for t in wm["tiles"] if not t.get("is_water") and t.get("poi_candidate")), None
        )
        if candidate is None:
            pytest.skip("No poi_candidate tiles")
        payload = {"adventure_id": ADV, "map_id": wm["id"], "tile_x": candidate["x"], "tile_y": candidate["y"]}
        r1 = client.post("/pois/discover", json=payload)
        r2 = client.post("/pois/discover", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]

    def test_list_pois(self, client):
        poi = _discover_poi(client)
        if poi is None:
            pytest.skip("No poi_candidate tiles in map")
        r = client.get(f"/pois?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_poi(self, client):
        poi = _discover_poi(client)
        if poi is None:
            pytest.skip("No poi_candidate tiles")
        r = client.get(f"/pois/{poi['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == poi["id"]

    def test_get_poi_404(self, client):
        assert client.get("/pois/no-such-poi").status_code == 404

    def test_update_poi(self, client):
        poi = _discover_poi(client)
        if poi is None:
            pytest.skip("No poi_candidate tiles")
        r = client.patch(f"/pois/{poi['id']}", json={"discovered": True})
        assert r.status_code == 200

    def test_enter_dungeon(self, client):
        """POIs of type dungeon can be entered to create a Dungeon with an entrance room."""
        wm = client.post("/world-maps", json={"adventure_id": ADV, "width": 32, "height": 32, "seed": 99}).json()
        # Find a dungeon-type poi_candidate (may need to try multiple)
        dungeon_poi = None
        for t in wm["tiles"]:
            if t.get("is_water") or not t.get("poi_candidate"):
                continue
            r = client.post("/pois/discover", json={
                "adventure_id": ADV, "map_id": wm["id"],
                "tile_x": t["x"], "tile_y": t["y"],
            })
            if r.status_code == 201 and r.json()["type"] == "dungeon":
                dungeon_poi = r.json()
                break
        if dungeon_poi is None:
            pytest.skip("No dungeon POI found in map")

        r = client.post("/dungeons/enter", json={"adventure_id": ADV, "poi_id": dungeon_poi["id"]})
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["poi_id"] == dungeon_poi["id"]
        assert d["floor_count"] >= 1

        # Should be able to list rooms
        rooms = client.get(f"/dungeons/{d['id']}/rooms").json()
        assert len(rooms) >= 1
        assert rooms[0]["is_entrance"] is True


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 6: Events
# ══════════════════════════════════════════════════════════════════════════════

class TestEvents:
    def test_fire_event(self, client):
        r = client.post("/events", json={
            "adventure_id": ADV,
            "type": "reached",
            "poi_id": "some-poi",
        })
        assert r.status_code == 201, r.text
        d = r.json()
        assert "event_id" in d
        assert isinstance(d["quests_advanced"], list)

    def test_fire_kill_event(self, client):
        r = client.post("/events", json={
            "adventure_id": ADV,
            "type": "killed",
            "entity_id": "some-npc-id",
        })
        assert r.status_code == 201, r.text

    def test_list_events(self, client):
        client.post("/events", json={"adventure_id": ADV, "type": "acquired", "item_id": "item-1"})
        r = client.get(f"/events?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_list_events_filtered_by_type(self, client):
        client.post("/events", json={"adventure_id": ADV, "type": "acquired"})
        client.post("/events", json={"adventure_id": ADV, "type": "killed"})
        r = client.get(f"/events?adventure_id={ADV}&type=acquired")
        assert r.status_code == 200
        for ev in r.json():
            assert ev["type"] == "acquired"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 7: Quests
# ══════════════════════════════════════════════════════════════════════════════

class TestQuests:
    def test_create_quest(self, client):
        r = client.post("/quests", json={"adventure_id": ADV, "length": "short", "context_hint": "Find the sword"})
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["title"] == "The Lost Relic"
        assert d["status"] == "active"
        assert d["first_step"]["status"] == "active"
        assert d["last_step"]["status"] == "pending"

    def test_list_quests(self, client):
        client.post("/quests", json={"adventure_id": ADV, "length": "short"})
        r = client.get(f"/quests?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_quest(self, client):
        qid = client.post("/quests", json={"adventure_id": ADV, "length": "short"}).json()["id"]
        r = client.get(f"/quests/{qid}")
        assert r.status_code == 200
        assert r.json()["id"] == qid

    def test_get_quest_404(self, client):
        assert client.get("/quests/nonexistent").status_code == 404

    def test_update_quest_status(self, client):
        qid = client.post("/quests", json={"adventure_id": ADV, "length": "short"}).json()["id"]
        r = client.patch(f"/quests/{qid}", json={"status": "failed"})
        assert r.status_code == 200
        assert r.json()["status"] == "failed"

    def test_get_active_step(self, client):
        qid = client.post("/quests", json={"adventure_id": ADV, "length": "short"}).json()["id"]
        r = client.get(f"/quests/{qid}/active-step")
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_delete_quest(self, client):
        qid = client.post("/quests", json={"adventure_id": ADV, "length": "short"}).json()["id"]
        r = client.delete(f"/quests/{qid}")
        assert r.status_code == 204
        assert client.get(f"/quests/{qid}").status_code == 404

    def test_event_advances_quest(self, client):
        """Killing an NPC whose entity_id matches a quest step's completion_event should advance the quest."""
        import json as json_mod
        from backend.models.quest import Quest, QuestStep
        from backend.models.event import EventCondition
        import backend.firebase as fb_module

        target_id = str(uuid.uuid4())
        qid = str(uuid.uuid4())

        step = QuestStep(
            description="Kill the goblin leader",
            completion_condition="Entity dead",
            status="active",
            completion_event=EventCondition(type="killed", entity_id=target_id),
        )
        quest = Quest(
            id=qid,
            adventure_id=ADV,
            title="Slay the Goblin",
            length="short",
            target_middle_count=0,
            first_step=step,
            last_step=QuestStep(description="End", completion_condition="Done"),
            status="active",
        )
        fb_module._db.collection("quests").document(qid).set(quest.model_dump())

        r = client.post("/events", json={"adventure_id": ADV, "type": "killed", "entity_id": target_id})
        assert r.status_code == 201
        assert qid in r.json()["quests_advanced"]

    def test_resolve_step_not_complete(self, client, provider):
        from tests.mock_infra import MOCK_RESPONSES
        import tests.mock_infra as mi
        original = mi.MOCK_RESPONSES["resolve_step"]
        mi.MOCK_RESPONSES["resolve_step"] = MOCK_RESPONSES["resolve_step_incomplete"]

        try:
            qid = client.post("/quests", json={"adventure_id": ADV, "length": "short"}).json()["id"]
            ws = client.post("/world-state", json={"adventure_id": ADV}).json()
            r = client.post(f"/quests/{qid}/resolve-step", json={
                "recent_context": "We searched everywhere.", "world_state_id": ws["id"],
            })
            assert r.status_code == 200
            assert r.json()["step_completed"] is False
        finally:
            mi.MOCK_RESPONSES["resolve_step"] = original


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 8: Combat
# ══════════════════════════════════════════════════════════════════════════════

def _make_character(client, name: str, *, is_player: bool = True, hp: int = 20,
                    strength: int = 12, dexterity: int = 10, ai_profile=None) -> dict:
    payload = {
        "adventure_id": ADV, "name": name, "is_player": is_player,
        "max_hp": hp,
        "stats": {"strength": strength, "dexterity": dexterity,
                  "intelligence": 10, "fortitude": 10, "charisma": 10, "reflex": 10},
    }
    if ai_profile:
        payload["ai_profile"] = ai_profile
    return client.post("/characters", json=payload).json()


class TestEncounterCRUD:
    def test_create_encounter(self, client):
        r = client.post("/encounters", json={"adventure_id": ADV, "mode": "combat"})
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["status"] == "pending"
        assert d["adventure_id"] == ADV

    def test_list_encounters(self, client):
        client.post("/encounters", json={"adventure_id": ADV})
        r = client.get(f"/encounters?adventure_id={ADV}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_encounter(self, client):
        eid = client.post("/encounters", json={"adventure_id": ADV}).json()["id"]
        r = client.get(f"/encounters/{eid}")
        assert r.status_code == 200
        assert r.json()["id"] == eid

    def test_update_encounter_stage_ids(self, client):
        char = _make_character(client, "Hero")
        eid = client.post("/encounters", json={"adventure_id": ADV}).json()["id"]
        r = client.patch(f"/encounters/{eid}", json={"stage_ids": [char["id"]]})
        assert r.status_code == 200
        assert char["id"] in r.json()["stage_ids"]


class TestCombatFlow:
    """Full combat lifecycle: start → player turn → npc turn → end."""

    def _setup_encounter(self, client) -> tuple[dict, dict, str]:
        """Create player + NPC, build encounter, return (player, npc, encounter_id)."""
        player = _make_character(client, "Aric", is_player=True, hp=30, strength=14, dexterity=12)
        npc = _make_character(client, "Goblin", is_player=False, hp=10, strength=8, dexterity=14,
                              ai_profile={
                                  "movement_type": "ground", "preferred_distance": 1,
                                  "target_selection": "closest", "intelligence": "drone",
                                  "last_assailant_id": None,
                              })
        enc = client.post("/encounters", json={
            "adventure_id": ADV, "stage_ids": [player["id"], npc["id"]],
        }).json()
        return player, npc, enc["id"]

    def test_start_combat(self, client):
        player, npc, eid = self._setup_encounter(client)
        r = client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2},
            "arena_width": 12, "arena_height": 12,
        })
        assert r.status_code == 200, r.text
        arena = r.json()
        assert arena["width"] == 12
        assert arena["height"] == 12
        assert len(arena["combatants"]) == 2
        assert len(arena["turn_order"]) == 2
        # tile grid dimensions
        assert len(arena["tiles"]) == 12
        assert len(arena["tiles"][0]) == 12

    def test_get_arena(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 10, "arena_height": 10,
        })
        r = client.get(f"/encounters/{eid}/arena")
        assert r.status_code == 200
        assert r.json()["encounter_id"] == eid

    def test_arena_before_start_404(self, client):
        eid = client.post("/encounters", json={"adventure_id": ADV}).json()["id"]
        assert client.get(f"/encounters/{eid}/arena").status_code == 404

    def test_player_move(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()

        # Find who goes first and get their starting position
        first_id = arena["turn_order"][0]
        actor = next(c for c in arena["combatants"] if c["id"] == first_id)
        ax, ay = actor["x"], actor["y"]

        # Find a valid adjacent tile (guaranteed passable floor for team 1 spawn row)
        candidates = [(ax+1, ay), (ax-1, ay), (ax, ay+1), (ax, ay-1)]
        tx, ty = next(
            (x, y) for x, y in candidates
            if 0 <= x < 12 and 0 <= y < 12
        )
        r = client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": first_id,
            "action_type": "move",
            "to_x": tx, "to_y": ty,
        })
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["action"]["action_type"] == "move"
        assert result["action"]["outcome"] == "moved"

    def test_player_attack(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()
        first_id = arena["turn_order"][0]
        second_id = next(id_ for id_ in arena["turn_order"] if id_ != first_id)

        r = client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": first_id,
            "action_type": "attack",
            "target_id": second_id,
            "stat_key": "strength",
            "dc_stat_key": "reflex",
        })
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["action"]["outcome"] in ("hit", "miss")
        assert len(result["action"]["dice_results"]) == 1
        assert result["narrative"] != ""

    def test_player_end_turn(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()
        first_id = arena["turn_order"][0]

        r = client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": first_id, "action_type": "end_turn",
        })
        assert r.status_code == 200
        # After end_turn, current_turn_idx should have advanced
        new_arena = r.json()["arena"]
        assert new_arena["current_turn_idx"] != 0 or new_arena["round"] > 1

    def test_wrong_turn_rejected(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()
        # Try to move the second actor on the first actor's turn
        second_id = arena["turn_order"][1]
        r = client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": second_id, "action_type": "end_turn",
        })
        assert r.status_code == 400

    def test_npc_turn(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()

        # Skip past any player turns until it's the NPC's turn
        for _ in range(len(arena["turn_order"])):
            current_arena = client.get(f"/encounters/{eid}/arena").json()
            current_id = current_arena["turn_order"][current_arena["current_turn_idx"]]
            if current_id == npc["id"]:
                break
            client.post(f"/encounters/{eid}/player-turn", json={
                "actor_id": current_id, "action_type": "end_turn",
            })
        else:
            pytest.skip("NPC never got a turn in turn order")

        r = client.post(f"/encounters/{eid}/npc-turn")
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["action"]["actor_id"] == npc["id"]
        assert result["action"]["action_type"] in ("move", "attack", "end_turn")

    def test_end_combat(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        r = client.post(f"/encounters/{eid}/end-combat", json={"outcome": "completed"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["outcome"] == "completed"
        assert d["narrative"] != ""
        # Encounter status should be updated
        enc = client.get(f"/encounters/{eid}").json()
        assert enc["status"] == "completed"

    def test_hp_written_back_after_combat(self, client):
        """End combat should persist final HP to character documents."""
        import backend.firebase as fb_module
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        # Take a turn attacking (may or may not hit, but HP gets written regardless)
        arena = client.get(f"/encounters/{eid}/arena").json()
        first_id = arena["turn_order"][0]
        second_id = next(id_ for id_ in arena["turn_order"] if id_ != first_id)
        client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": first_id, "action_type": "attack", "target_id": second_id,
            "stat_key": "strength", "dc_stat_key": "reflex",
        })
        client.post(f"/encounters/{eid}/end-combat", json={"outcome": "completed"})

        # HP should be written back for both combatants
        p_doc = fb_module._db.collection("characters").document(player["id"]).get()
        n_doc = fb_module._db.collection("characters").document(npc["id"]).get()
        assert p_doc.exists
        assert n_doc.exists
        assert "hp" in p_doc.to_dict()

    def test_list_actions(self, client):
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()
        first_id = arena["turn_order"][0]
        second_id = next(id_ for id_ in arena["turn_order"] if id_ != first_id)
        client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": first_id, "action_type": "attack", "target_id": second_id,
            "stat_key": "strength", "dc_stat_key": "reflex",
        })
        r = client.get(f"/encounters/{eid}/actions")
        assert r.status_code == 200
        actions = r.json()
        assert len(actions) == 1
        assert actions[0]["encounter_id"] == eid

    def test_loot_cache(self, client):
        """Player should be able to loot a cache if adjacent."""
        import backend.firebase as fb_module
        player, npc, eid = self._setup_encounter(client)
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {player["id"]: 1, npc["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()

        # Find the cache object from the mock arena response
        caches = [o for o in arena["objects"] if o["object_type"] == "cache"]
        if not caches:
            pytest.skip("Mock arena response has no cache objects")

        cache = caches[0]

        # Add an item to the cache so we have something to loot
        from backend.routers.combat import _ARENAS
        from backend.models.combat import Arena as ArenaModel
        a = _ARENAS.get(eid)
        if a is None:
            pytest.skip("Arena not in memory cache")

        item_id = str(uuid.uuid4())
        cache_obj = next(o for o in a.objects if o.object_type == "cache")
        cache_obj.item_ids = [item_id]

        # Move the first actor adjacent to the cache
        first_id = arena["turn_order"][0]
        actor = next(c for c in arena["combatants"] if c["id"] == first_id)

        # Teleport the actor to a tile adjacent to the cache in-memory
        cache_combatant = next(c for c in a.combatants if c.id == first_id)
        cx, cy = cache_obj.x, cache_obj.y
        # Place actor right next to the cache
        cache_combatant.x = max(0, cx - 1)
        cache_combatant.y = cy

        r = client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": first_id,
            "action_type": "loot",
            "object_id": cache_obj.id,
        })
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["action"]["outcome"] == "looted"
        assert item_id in result["looted_items"]


# ══════════════════════════════════════════════════════════════════════════════
# Unit tests: Combat AI (pure functions, no network/DB)
# ══════════════════════════════════════════════════════════════════════════════

class TestCombatAI:
    def _make_arena(self, width=10, height=10):
        from backend.models.combat import Arena, ArenaTile, ArenaCombatant, AIProfile

        tiles = [[ArenaTile() for _ in range(width)] for _ in range(height)]
        player = ArenaCombatant(id="player", x=0, y=0, team=1, hp=30, max_hp=30,
                                stats={"strength": 14, "dexterity": 10, "reflex": 10})
        npc = ArenaCombatant(
            id="npc", x=9, y=9, team=2, hp=10, max_hp=10,
            stats={"strength": 8, "dexterity": 12, "reflex": 8},
            ai_profile=AIProfile(movement_type="ground", preferred_distance=1,
                                 target_selection="closest", intelligence="drone"),
        )
        arena = Arena(
            encounter_id="enc-1", adventure_id=ADV,
            width=width, height=height, tiles=tiles,
            combatants=[player, npc], turn_order=["player", "npc"], teams={"player": 1, "npc": 2},
        )
        return arena, player, npc

    def test_select_target_closest(self):
        from backend.utils.combat_ai import select_target
        from backend.models.combat import ArenaCombatant, AIProfile

        arena, player, npc = self._make_arena()
        # Place a second enemy farther away
        enemy2 = ArenaCombatant(id="e2", x=5, y=5, team=2, hp=10, max_hp=10,
                                stats={}, ai_profile=AIProfile(target_selection="closest"))
        arena.combatants.append(enemy2)

        # Player selects: closest enemy
        player.ai_profile = AIProfile(target_selection="closest")
        target = select_target(player, arena)
        assert target is not None
        assert target.id == "e2"  # (5,5) is closer to (0,0) than (9,9)

    def test_select_target_weakest(self):
        from backend.utils.combat_ai import select_target
        from backend.models.combat import ArenaCombatant, AIProfile

        arena, player, npc = self._make_arena()
        weak_enemy = ArenaCombatant(id="weak", x=5, y=5, team=2, hp=2, max_hp=10, stats={})
        arena.combatants.append(weak_enemy)

        player.ai_profile = AIProfile(target_selection="weakest")
        target = select_target(player, arena)
        assert target.id == "weak"

    def test_select_target_no_enemies(self):
        from backend.utils.combat_ai import select_target
        from backend.models.combat import ArenaCombatant

        arena, player, npc = self._make_arena()
        npc.hp = 0
        npc.status = ["dead"]
        target = select_target(player, arena)
        assert target is None

    def test_compute_move_toward_target(self):
        from backend.utils.combat_ai import compute_move
        from backend.models.combat import AIProfile

        arena, player, npc = self._make_arena()
        npc.ai_profile = AIProfile(movement_type="ground", preferred_distance=1, target_selection="closest")
        # NPC at (9,9), player at (0,0): should move left or up
        nx, ny = compute_move(npc, player, arena)
        assert (nx, ny) != (9, 9)  # should have moved
        assert abs(nx - 0) + abs(ny - 0) < abs(9 - 0) + abs(9 - 0)  # closer to player

    def test_should_flee_drone(self):
        from backend.utils.combat_ai import should_flee
        from backend.models.combat import ArenaCombatant, AIProfile

        npc = ArenaCombatant(id="n", x=0, y=0, team=2, hp=1, max_hp=10, stats={},
                             ai_profile=AIProfile(intelligence="drone"))
        assert should_flee(npc) is False  # drone never flees

    def test_should_flee_beast(self):
        from backend.utils.combat_ai import should_flee
        from backend.models.combat import ArenaCombatant, AIProfile

        npc = ArenaCombatant(id="n", x=0, y=0, team=2, hp=2, max_hp=10, stats={},
                             ai_profile=AIProfile(intelligence="beast"))
        assert should_flee(npc) is True  # hp < 25%

    def test_should_flee_beast_full_hp(self):
        from backend.utils.combat_ai import should_flee
        from backend.models.combat import ArenaCombatant, AIProfile

        npc = ArenaCombatant(id="n", x=0, y=0, team=2, hp=10, max_hp=10, stats={},
                             ai_profile=AIProfile(intelligence="beast"))
        assert should_flee(npc) is False

    def test_should_flee_alpha_never(self):
        from backend.utils.combat_ai import should_flee
        from backend.models.combat import ArenaCombatant, AIProfile

        npc = ArenaCombatant(id="n", x=0, y=0, team=2, hp=1, max_hp=10, stats={},
                             ai_profile=AIProfile(intelligence="alpha"))
        assert should_flee(npc) is False

    def test_apply_alpha_phase(self):
        from backend.utils.combat_ai import apply_alpha_phase
        from backend.models.combat import ArenaCombatant, AIProfile

        alpha = ArenaCombatant(id="a", x=0, y=0, team=2, hp=4, max_hp=10, stats={},
                               ai_profile=AIProfile(intelligence="alpha"))
        tags = apply_alpha_phase(alpha)
        assert "enraged" in tags
        assert "enraged" in alpha.status

        # At 25% threshold, berserk should be added
        alpha.hp = 2
        tags2 = apply_alpha_phase(alpha)
        assert "berserk" in tags2

    def test_npc_decide_action_drone_attacks(self):
        from backend.utils.combat_ai import npc_decide_action
        from backend.models.combat import ArenaCombatant, AIProfile

        arena, player, npc = self._make_arena()
        # Put NPC adjacent to player
        npc.x, npc.y = 1, 0
        npc.ai_profile = AIProfile(movement_type="ground", preferred_distance=1,
                                   target_selection="closest", intelligence="drone")
        decision = npc_decide_action(npc, arena)
        assert decision["action_type"] == "attack"
        assert decision["target_id"] == "player"

    def test_npc_decide_action_moves_when_far(self):
        from backend.utils.combat_ai import npc_decide_action
        from backend.models.combat import ArenaCombatant, AIProfile

        arena, player, npc = self._make_arena()
        # NPC at (9,9), player at (0,0): too far to attack, should move
        npc.ai_profile = AIProfile(movement_type="ground", preferred_distance=1,
                                   target_selection="closest", intelligence="drone")
        decision = npc_decide_action(npc, arena)
        assert decision["action_type"] == "move"

    def test_edge_consistency(self):
        """_effective_edge should return max(outgoing, incoming) for safety."""
        from backend.utils.combat_ai import _effective_edge
        from backend.models.combat import Arena, ArenaTile

        tiles = [[ArenaTile() for _ in range(5)] for _ in range(5)]
        # Set inconsistent edges: tile (2,2) east=2, but tile (3,2) west=0
        tiles[2][2].edges[1] = 2  # east
        tiles[2][3].edges[3] = 0  # west (missing/inconsistent)

        from backend.models.combat import ArenaCombatant
        arena = Arena(encounter_id="e", adventure_id=ADV, width=5, height=5,
                      tiles=tiles, combatants=[], turn_order=[], teams={})
        # effective edge from (2,2) going east should be max(2, 0) = 2
        assert _effective_edge(arena, 2, 2, 1) == 2
