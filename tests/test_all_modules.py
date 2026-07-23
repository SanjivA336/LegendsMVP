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


@pytest.fixture()
def auth_headers():
    """Bypasses real Firebase ID-token verification, mirroring how `client`/`provider`
    stub their own external dependencies -- adventures.py's routes all require auth."""
    import firebase_admin.auth as fb_auth
    with patch.object(fb_auth, "verify_id_token", return_value={"uid": "test-uid"}):
        yield {"Authorization": "Bearer faketoken"}


ADV = "adv-test-001"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2: Characters
# ══════════════════════════════════════════════════════════════════════════════
# (Item template/instance coverage now lives in TestBlueprints/TestStatusEffects --
# items were migrated onto the kind-tagged Template/Instance system; see Phase 2
# of the blueprint migration plan.)

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

    def test_seed_starter_content_creates_races_and_classes(self, client):
        r = client.post("/templates/seed-starter-content", json={"adventure_id": ADV})
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["race_template_ids"]) == 4
        assert len(data["class_template_ids"]) == 4

        races = client.get(f"/templates?adventure_id={ADV}&kind=race").json()
        assert any(t["name"] == "Elf" for t in races)
        elf = next(t for t in races if t["name"] == "Elf")
        elf_dex = next(f for f in elf["fields"] if f["key"] == "dexterity")
        assert elf_dex["value"] == 2
        assert elf_dex["bound_behavior"] == "stat"

    def test_create_character_with_race_and_class_attaches_instances(self, client):
        seeded = client.post("/templates/seed-starter-content", json={"adventure_id": ADV}).json()
        races = client.get(f"/templates?adventure_id={ADV}&kind=race").json()
        classes = client.get(f"/templates?adventure_id={ADV}&kind=class").json()
        elf_template = next(t for t in races if t["name"] == "Elf")
        wizard_template = next(t for t in classes if t["name"] == "Wizard")

        r = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "Elf Wizard",
            "race_template_id": elf_template["id"], "class_template_id": wizard_template["id"],
        })
        assert r.status_code == 201, r.text
        char = r.json()
        assert char["race_instance_id"] is not None
        assert char["class_instance_id"] is not None

        # The attached race/class instance should resolve back to the chosen template's name
        race_instance = client.get(f"/instances/{char['race_instance_id']}").json()
        assert race_instance["name"] == "Elf"
        class_instance = client.get(f"/instances/{char['class_instance_id']}").json()
        assert class_instance["name"] == "Wizard"

    def test_create_character_without_race_or_class_leaves_them_null(self, client):
        r = client.post("/characters", json=_PLAYER_PAYLOAD)
        assert r.status_code == 201, r.text
        char = r.json()
        assert char["race_instance_id"] is None
        assert char["class_instance_id"] is None

    def test_create_character_with_custom_fields(self, client):
        r = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "Vex",
            "custom_fields": [{"key": "backstory", "field_type": "string", "value": "A wandering exile"}],
        })
        assert r.status_code == 201, r.text
        raw = client.get(f"/instances/{r.json()['id']}").json()
        field_values = {f["key"]: f["value"] for f in raw["fields"]}
        assert field_values["backstory"] == "A wandering exile"
        # canonical fields still come from the dedicated payload args, not custom_fields
        assert field_values["name"] == "Vex"

    def test_custom_fields_cannot_clobber_canonical_fields(self, client):
        r = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "Real Name",
            "custom_fields": [{"key": "name", "field_type": "string", "value": "Spoofed Name"}],
        })
        assert r.status_code == 201, r.text
        assert r.json()["name"] == "Real Name"

    def test_wearable_template_gets_default_slot(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "wearable", "name": "Leather Cap",
        }).json()
        field_values = {f["key"]: f["value"] for f in tmpl["fields"]}
        assert field_values["slot"] == "body"

    def test_wearable_instance_resolves_custom_slot(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "wearable", "name": "Iron Helm",
            "fields": [{"key": "slot", "field_type": "string", "value": "head"}],
        }).json()
        inst = client.post("/instances", json={
            "adventure_id": ADV, "kind": "wearable", "template_id": tmpl["id"],
        }).json()
        resolved = client.get(f"/instances/{inst['id']}").json()
        field_values = {f["key"]: f["value"] for f in resolved["fields"]}
        assert field_values["slot"] == "head"

    def _make_wearable_instance(self, client, slot="head"):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "wearable", "name": "Test Helm",
            "fields": [{"key": "slot", "field_type": "string", "value": slot}],
        }).json()
        return client.post("/instances", json={
            "adventure_id": ADV, "kind": "wearable", "template_id": tmpl["id"],
        }).json()

    def test_create_character_claims_starting_gear_ownership(self, client):
        helm = self._make_wearable_instance(client)
        r = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "Geared Up",
            "starting_inventory_ids": [helm["id"]],
            "starting_equipped_wearable_ids": [helm["id"]],
        })
        assert r.status_code == 201, r.text
        char = r.json()
        assert char["inventory_ids"] == [helm["id"]]
        assert char["equipped_wearable_ids"] == [helm["id"]]

        claimed = client.get(f"/instances/{helm['id']}").json()
        assert claimed["owner_id"] == char["id"]

    def test_create_character_starting_item_already_owned_409(self, client):
        helm = self._make_wearable_instance(client)
        client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "First Claimer", "starting_inventory_ids": [helm["id"]],
        })
        r = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "Second Claimer", "starting_inventory_ids": [helm["id"]],
        })
        assert r.status_code == 409

    def test_create_character_starting_item_not_found_404(self, client):
        r = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "starting_inventory_ids": ["no-such-item"],
        })
        assert r.status_code == 404

    def test_delete_character_releases_owned_items(self, client):
        helm = self._make_wearable_instance(client)
        char = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "starting_inventory_ids": [helm["id"]],
        }).json()

        r = client.delete(f"/characters/{char['id']}")
        assert r.status_code == 204

        released = client.get(f"/instances/{helm['id']}").json()
        assert released["owner_id"] is None

        # a second character can now claim the released item
        r2 = client.post("/characters", json={
            **_PLAYER_PAYLOAD, "name": "New Owner", "starting_inventory_ids": [helm["id"]],
        })
        assert r2.status_code == 201, r2.text

    def test_attach_and_detach_status_effect(self, client):
        cid = client.post("/characters", json=_PLAYER_PAYLOAD).json()["id"]
        status = client.post("/status-effects", json={
            "adventure_id": ADV, "name": "Poison I",
            "effects": [{"effect_type": "hp_delta_over_time", "parameters": [{"key": "amount_per_turn", "value": -5}]}],
        }).json()

        r = client.post(f"/characters/{cid}/status-effects", json={"status_effect_id": status["id"], "expires_at_round": 12})
        assert r.status_code == 200, r.text

        raw = client.get(f"/instances/{cid}").json()
        attached_ids = [a["ref_id"] for a in raw["attached"] if a["ref_kind"] == "status_effect"]
        assert status["id"] in attached_ids
        expiry = next(a["expires_at_round"] for a in raw["attached"] if a["ref_id"] == status["id"])
        assert expiry == 12

        r = client.delete(f"/characters/{cid}/status-effects/{status['id']}")
        assert r.status_code == 200, r.text
        raw_after = client.get(f"/instances/{cid}").json()
        attached_ids_after = [a["ref_id"] for a in raw_after["attached"] if a["ref_kind"] == "status_effect"]
        assert status["id"] not in attached_ids_after

    def test_attach_status_effect_404_for_unknown_status(self, client):
        cid = client.post("/characters", json=_PLAYER_PAYLOAD).json()["id"]
        r = client.post(f"/characters/{cid}/status-effects", json={"status_effect_id": "nonexistent"})
        assert r.status_code == 404


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

    def test_preview_world_map_does_not_persist(self, client):
        r = client.post("/world-maps/preview", json={
            "adventure_id": ADV, "width": 16, "height": 16, "seed": 55,
        })
        assert r.status_code == 200, r.text
        preview_id = r.json()["id"]
        # The preview must not show up in list results or be independently fetchable
        # as if it were a real, persisted map.
        listed_ids = [m["id"] for m in client.get(f"/world-maps?adventure_id={ADV}").json()]
        assert preview_id not in listed_ids
        assert client.get(f"/world-maps/{preview_id}").status_code == 404

    def test_preview_then_commit_reproduces_same_tiles(self, client):
        body = {"adventure_id": ADV, "width": 16, "height": 16, "seed": 123}
        preview = client.post("/world-maps/preview", json=body).json()
        committed = client.post("/world-maps", json=body).json()
        assert preview["tiles"] == committed["tiles"]
        assert preview["spawn_tile_x"] == committed["spawn_tile_x"]
        assert preview["spawn_tile_y"] == committed["spawn_tile_y"]

    def test_manual_elevation_seed_placement(self, client):
        r = client.post("/world-maps/preview", json={
            "adventure_id": ADV, "width": 32, "height": 32, "seed": 5,
            "elevation_seed_positions": [[16, 16]],
        })
        assert r.status_code == 200, r.text
        tiles = r.json()["tiles"]
        by_pos = {(t["x"], t["y"]): t for t in tiles}
        # A single elevation seed at the map center should produce mountainous
        # terrain right at that coordinate.
        assert by_pos[(16, 16)]["biome_id"] is not None
        assert not by_pos[(16, 16)]["is_water"]

    def test_manual_elevation_seed_out_of_bounds_rejected(self, client):
        r = client.post("/world-maps/preview", json={
            "adventure_id": ADV, "width": 16, "height": 16, "seed": 5,
            "elevation_seed_positions": [[999, 999]],
        })
        assert r.status_code == 422

    def test_percent_ocean_zero_produces_no_water(self, client):
        r = client.post("/world-maps/preview", json={
            "adventure_id": ADV, "width": 32, "height": 32, "seed": 9,
            "percent_ocean": 0.0,
        })
        assert r.status_code == 200, r.text
        assert not any(t["is_water"] for t in r.json()["tiles"])

    def test_percent_mountain_zero_produces_no_mountain_or_volcanic(self, client):
        r = client.post("/world-maps/preview", json={
            "adventure_id": ADV, "width": 32, "height": 32, "seed": 9,
            "percent_mountain": 0.0, "volcano_chance": 1.0,
        })
        assert r.status_code == 200, r.text
        from backend.utils.biomes import BIOMES, BiomeFamily
        for t in r.json()["tiles"]:
            if t["biome_id"] is not None:
                family = BIOMES.get_biome_by_id(t["biome_id"]).family
                assert family not in (BiomeFamily.MOUNTAIN, BiomeFamily.VOLCANIC)


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

    def test_equipped_weapon_damage_roll_is_used(self, client):
        """_get_weapon_damage should roll the weapon's damage_roll (kind-tagged
        Instance/Template) rather than falling back to the unarmed default. Uses a
        1-sided die (always rolls 1) so the resulting damage is deterministic, and an
        extreme stat gap so the to-hit roll always succeeds regardless of the d20.
        """
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "weapon", "name": "Deterministic Blade",
            "fields": [
                {"key": "hit_roll", "field_type": "dice_roll", "value": "1d1"},
                {"key": "damage_roll", "field_type": "dice_roll", "value": "1d1+5"},  # always rolls 6
            ],
        }).json()
        inst = client.post("/instances", json={
            "adventure_id": ADV, "kind": "weapon", "template_id": tmpl["id"],
        }).json()

        attacker = client.post("/characters", json={
            "adventure_id": ADV, "name": "Deterministic Attacker", "is_player": True, "max_hp": 20,
            # dexterity=100 vs target's 1: initiative is dexterity + d20 (1-20), so a 99-point
            # gap can never be overcome by the die (max swing is 19) -- turn order is
            # deterministic, not just overwhelmingly likely.
            "stats": {"strength": 30, "dexterity": 100, "intelligence": 10, "fortitude": 10, "charisma": 10, "reflex": 10},
            "inventory_ids": [inst["id"]],
        }).json()
        client.patch(f"/characters/{attacker['id']}/equip/{inst['id']}")

        target = client.post("/characters", json={
            "adventure_id": ADV, "name": "Deterministic Target", "is_player": False, "max_hp": 30,
            "stats": {"strength": 10, "dexterity": 1, "intelligence": 10, "fortitude": 10, "charisma": 10, "reflex": 1},
        }).json()

        eid = client.post("/encounters", json={
            "adventure_id": ADV, "stage_ids": [attacker["id"], target["id"]],
        }).json()["id"]
        client.post(f"/encounters/{eid}/start-combat", json={
            "teams": {attacker["id"]: 1, target["id"]: 2}, "arena_width": 12, "arena_height": 12,
        })
        arena = client.get(f"/encounters/{eid}/arena").json()
        assert arena["turn_order"][0] == attacker["id"], "attacker's dexterity gap should guarantee first turn"

        # attacker's huge strength vs target's low reflex guarantees a hit regardless
        # of the attack roll's own d20
        r = client.post(f"/encounters/{eid}/player-turn", json={
            "actor_id": attacker["id"], "action_type": "attack", "target_id": target["id"],
            "stat_key": "strength", "dc_stat_key": "reflex",
        })
        assert r.status_code == 200, r.text
        result = r.json()
        assert result["action"]["outcome"] == "hit", result

        # weapon_dmg=6 (1d1+5) + stat_bonus=(30-10)//2=10 = 16 total, minus up to 1 for
        # cover -- unarmed fallback would only ever total 11 (1 + 10) at most, so hp
        # dropping to <=16 conclusively shows the weapon's own roll was used. HP is only
        # written back to the character document at end_combat (see
        # test_hp_written_back_after_combat), so check the live arena state instead.
        arena_after = client.get(f"/encounters/{eid}/arena").json()
        target_combatant = next(c for c in arena_after["combatants"] if c["id"] == target["id"])
        assert target_combatant["hp"] <= 16, target_combatant

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
        """End combat should persist final HP to character documents (now kind="character"
        Instances) -- checked through the real API contract rather than poking storage
        directly, since characters no longer live in a dedicated "characters" collection.
        """
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
        p_after = client.get(f"/characters/{player['id']}").json()
        n_after = client.get(f"/characters/{npc['id']}").json()
        assert "hp" in p_after
        assert "hp" in n_after

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


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 9: Blueprints & Instances (kind-tagged Template/Instance system)
# ══════════════════════════════════════════════════════════════════════════════

class TestBlueprints:
    def test_create_template(self, client):
        r = client.post("/templates", json={
            "adventure_id": ADV, "kind": "weapon", "name": "Rusty Sword",
            "fields": [
                {"key": "hit_roll", "field_type": "dice_roll", "value": "1d20+2"},
                {"key": "damage_roll", "field_type": "dice_roll", "value": "2d6+4"},
            ],
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == "Rusty Sword"
        field_values = {f["key"]: f["value"] for f in data["fields"]}
        assert field_values["hit_roll"] == "1d20+2"
        assert field_values["damage_roll"] == "2d6+4"

    def test_create_template_missing_required_fields_400(self, client):
        r = client.post("/templates", json={"adventure_id": ADV, "kind": "weapon", "name": "Bare Sword"})
        assert r.status_code == 400
        assert "hit_roll" in r.text and "damage_roll" in r.text

    def test_create_template_custom_kind_needs_nothing(self, client):
        r = client.post("/templates", json={"adventure_id": ADV, "kind": "custom", "name": "Anything"})
        assert r.status_code == 201, r.text

    def test_list_templates_filtered_by_kind(self, client):
        client.post("/templates", json={"adventure_id": ADV, "kind": "race", "name": "Elf"})
        client.post("/templates", json={"adventure_id": ADV, "kind": "class", "name": "Barbarian"})
        r = client.get(f"/templates?adventure_id={ADV}&kind=race")
        assert r.status_code == 200
        assert all(t["kind"] == "race" for t in r.json())
        assert any(t["name"] == "Elf" for t in r.json())

    def test_get_template_404(self, client):
        r = client.get("/templates/nonexistent-id")
        assert r.status_code == 404

    def test_get_template_default_fields(self, client):
        r = client.get("/templates/default-fields?kind=weapon")
        assert r.status_code == 200, r.text
        keys = {f["key"] for f in r.json()}
        assert {"hit_roll", "damage_roll", "weight"} <= keys

    def test_update_template_merges_fields(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "wearable", "name": "Leather Vest",
            "fields": [{"key": "defense", "field_type": "number", "value": 2}],
        }).json()
        r = client.patch(f"/templates/{tmpl['id']}", json={
            "fields": [{"key": "stat_delta", "field_type": "number", "value": 1}],
        })
        assert r.status_code == 200, r.text
        field_values = {f["key"]: f["value"] for f in r.json()["fields"]}
        # the pre-existing "defense" field should survive an update that only
        # touches "stat_delta" -- fields merge, they don't replace wholesale
        assert field_values["defense"] == 2
        assert field_values["stat_delta"] == 1

    def test_update_template_new_field_visible_on_existing_instance(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "wearable", "name": "Cloak",
            "fields": [{"key": "defense", "field_type": "number", "value": 1}],
        }).json()
        inst = client.post("/instances", json={
            "adventure_id": ADV, "kind": "wearable", "template_id": tmpl["id"],
        }).json()

        client.patch(f"/templates/{tmpl['id']}", json={
            "fields": [{"key": "weight", "field_type": "number", "value": 3}],
        })

        # existing instance was never touched, but resolving it should show the
        # template's new field with its default value -- merge-at-read, not copy-on-write
        resolved = client.get(f"/instances/{inst['id']}").json()
        field_values = {f["key"]: f["value"] for f in resolved["fields"]}
        assert field_values["weight"] == 3

    def test_update_template_removed_field_clears_template_and_instance_override(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "wearable", "name": "Ring",
            "fields": [
                {"key": "defense", "field_type": "number", "value": 1},
                {"key": "stat_key", "field_type": "string", "value": "charisma"},
            ],
        }).json()
        # instance overrides "defense" itself -- the override must also be cleared
        # when the template field is deleted, or it'd leak the deleted field back in
        inst = client.post("/instances", json={
            "adventure_id": ADV, "kind": "wearable", "template_id": tmpl["id"],
            "fields": [{"key": "defense", "field_type": "number", "value": 5}],
        }).json()

        r = client.patch(f"/templates/{tmpl['id']}", json={"removed_field_keys": ["defense"]})
        assert r.status_code == 200, r.text
        assert "defense" not in {f["key"] for f in r.json()["fields"]}
        assert "stat_key" in {f["key"] for f in r.json()["fields"]}

        resolved = client.get(f"/instances/{inst['id']}").json()
        assert "defense" not in {f["key"] for f in resolved["fields"]}

    def test_delete_template(self, client):
        tmpl = client.post("/templates", json={"adventure_id": ADV, "kind": "custom", "name": "Junk"}).json()
        r = client.delete(f"/templates/{tmpl['id']}")
        assert r.status_code == 204
        assert client.get(f"/templates/{tmpl['id']}").status_code == 404

    def test_delete_template_blocked_by_instance(self, client):
        tmpl = client.post("/templates", json={"adventure_id": ADV, "kind": "race", "name": "Dwarf"}).json()
        client.post("/instances", json={"adventure_id": ADV, "kind": "race", "template_id": tmpl["id"]})
        r = client.delete(f"/templates/{tmpl['id']}")
        assert r.status_code == 409

    def test_create_instance_with_template(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "weapon", "name": "Bow",
            "fields": [
                {"key": "hit_roll", "field_type": "dice_roll", "value": "1d20"},
                {"key": "damage_roll", "field_type": "dice_roll", "value": "1d8"},
            ],
        }).json()
        r = client.post("/instances", json={"adventure_id": ADV, "kind": "weapon", "template_id": tmpl["id"]})
        assert r.status_code == 201, r.text
        assert r.json()["template_id"] == tmpl["id"]

    def test_create_instance_kind_mismatch_400(self, client):
        tmpl = client.post("/templates", json={"adventure_id": ADV, "kind": "race", "name": "Halfling"}).json()
        r = client.post("/instances", json={"adventure_id": ADV, "kind": "class", "template_id": tmpl["id"]})
        assert r.status_code == 400

    def test_create_instance_missing_required_400(self, client):
        r = client.post("/instances", json={"adventure_id": ADV, "kind": "weapon"})
        assert r.status_code == 400

    def test_create_instance_custom_kind_no_validation(self, client):
        r = client.post("/instances", json={"adventure_id": ADV, "kind": "custom"})
        assert r.status_code == 201, r.text

    def test_get_instance_resolves_merged_fields_and_template_name(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "weapon", "name": "Rusty Sword",
            "fields": [
                {"key": "hit_roll", "field_type": "dice_roll", "value": "1d20"},
                {"key": "damage_roll", "field_type": "dice_roll", "value": "1d6"},
            ],
        }).json()
        inst = client.post("/instances", json={
            "adventure_id": ADV, "kind": "weapon", "template_id": tmpl["id"],
            "fields": [{"key": "damage_roll", "field_type": "dice_roll", "value": "2d6+4"}],
        }).json()
        r = client.get(f"/instances/{inst['id']}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "Rusty Sword", "item-like kind: name comes from the template"
        field_values = {f["key"]: f["value"] for f in data["fields"]}
        assert field_values["hit_roll"] == "1d20", "un-overridden field falls through from template"
        assert field_values["damage_roll"] == "2d6+4", "instance override wins over template default"

    def test_character_instance_name_comes_from_fields_not_template(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "character", "name": "Default Character",
            # "name" is a required CustomField for kind="character" just like the stats
            # are -- it needs a value here the same way stats need theirs (which they
            # already have, defaulted to 10, via KIND_FIELD_DEFS).
            "fields": [{"key": "name", "field_type": "string", "value": "Unnamed", "required": True}],
        }).json()
        assert "id" in tmpl, tmpl
        inst = client.post("/instances", json={
            "adventure_id": ADV, "kind": "character", "template_id": tmpl["id"],
            "fields": [{"key": "name", "field_type": "string", "value": "Kael", "required": True}],
        }).json()
        r = client.get(f"/instances/{inst['id']}")
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "Kael"

    def test_list_instances_by_kind(self, client):
        tmpl = client.post("/templates", json={"adventure_id": ADV, "kind": "race", "name": "Gnome"}).json()
        client.post("/instances", json={"adventure_id": ADV, "kind": "race", "template_id": tmpl["id"]})
        r = client.get(f"/instances?adventure_id={ADV}&kind=race")
        assert r.status_code == 200
        assert all(i["kind"] == "race" for i in r.json())

    def test_update_instance_fields_and_revalidate(self, client):
        tmpl = client.post("/templates", json={
            "adventure_id": ADV, "kind": "weapon", "name": "Axe",
            "fields": [
                {"key": "hit_roll", "field_type": "dice_roll", "value": "1d20"},
                {"key": "damage_roll", "field_type": "dice_roll", "value": "1d8"},
            ],
        }).json()
        inst = client.post("/instances", json={"adventure_id": ADV, "kind": "weapon", "template_id": tmpl["id"]}).json()
        r = client.patch(f"/instances/{inst['id']}", json={
            "fields": [{"key": "damage_roll", "field_type": "dice_roll", "value": "2d8+2"}],
        })
        assert r.status_code == 200, r.text
        field_values = {f["key"]: f["value"] for f in r.json()["fields"]}
        assert field_values["damage_roll"] == "2d8+2"

    def test_delete_instance(self, client):
        r = client.post("/instances", json={"adventure_id": ADV, "kind": "custom"})
        inst = r.json()
        r2 = client.delete(f"/instances/{inst['id']}")
        assert r2.status_code == 204
        assert client.get(f"/instances/{inst['id']}").status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 10: Status Effects
# ══════════════════════════════════════════════════════════════════════════════

class TestStatusEffects:
    def test_create_status_effect_def(self, client):
        r = client.post("/status-effects", json={
            "adventure_id": ADV, "name": "Poison I",
            "effects": [
                {"effect_type": "hp_delta_over_time", "parameters": [{"key": "amount_per_turn", "value": -5}]},
            ],
        })
        assert r.status_code == 201, r.text
        assert r.json()["name"] == "Poison I"

    def test_create_status_effect_def_missing_param_400(self, client):
        r = client.post("/status-effects", json={
            "adventure_id": ADV, "name": "Broken Poison",
            "effects": [{"effect_type": "hp_delta_over_time", "parameters": []}],
        })
        assert r.status_code == 400
        assert "amount_per_turn" in r.text

    def test_status_effect_def_with_multiple_effects(self, client):
        r = client.post("/status-effects", json={
            "adventure_id": ADV, "name": "Weakening Poison",
            "effects": [
                {"effect_type": "hp_delta_over_time", "parameters": [{"key": "amount_per_turn", "value": -3}]},
                {"effect_type": "stat_delta", "parameters": [
                    {"key": "stat_key", "value": "strength"}, {"key": "delta", "value": -1},
                ]},
            ],
        })
        assert r.status_code == 201, r.text
        assert len(r.json()["effects"]) == 2

    def test_list_status_effect_defs(self, client):
        client.post("/status-effects", json={"adventure_id": ADV, "name": "Blessed", "effects": []})
        r = client.get(f"/status-effects?adventure_id={ADV}")
        assert r.status_code == 200
        assert any(s["name"] == "Blessed" for s in r.json())

    def test_get_status_effect_def_404(self, client):
        r = client.get("/status-effects/nonexistent-id")
        assert r.status_code == 404

    def test_update_status_effect_def(self, client):
        s = client.post("/status-effects", json={"adventure_id": ADV, "name": "Regen I", "effects": [
            {"effect_type": "hp_delta_over_time", "parameters": [{"key": "amount_per_turn", "value": 5}]},
        ]}).json()
        r = client.patch(f"/status-effects/{s['id']}", json={"name": "Regeneration I"})
        assert r.status_code == 200
        assert r.json()["name"] == "Regeneration I"

    def test_update_status_effect_def_rejects_invalid_effects(self, client):
        s = client.post("/status-effects", json={"adventure_id": ADV, "name": "Regen II", "effects": [
            {"effect_type": "hp_delta_over_time", "parameters": [{"key": "amount_per_turn", "value": 5}]},
        ]}).json()
        r = client.patch(f"/status-effects/{s['id']}", json={
            "effects": [{"effect_type": "stat_delta", "parameters": []}],
        })
        assert r.status_code == 400

    def test_delete_status_effect_def(self, client):
        s = client.post("/status-effects", json={"adventure_id": ADV, "name": "Temp", "effects": []}).json()
        r = client.delete(f"/status-effects/{s['id']}")
        assert r.status_code == 204
        assert client.get(f"/status-effects/{s['id']}").status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 10: World Creation Wizard v2 -- Phase 2 backend (adventure fields, theme)
# ══════════════════════════════════════════════════════════════════════════════

class TestAdventures:
    def test_create_adventure_with_client_invite_code(self, client, auth_headers):
        r = client.post("/adventures", json={
            "adventure_id": str(uuid.uuid4()), "name": "Test Campaign", "world_name": "Testonia",
            "invite_code": "WIZARD1",
        }, headers=auth_headers)
        assert r.status_code == 201, r.text
        assert r.json()["adventure"]["invite_code"] == "WIZARD1"

    def test_create_adventure_falls_back_to_generated_invite_code(self, client, auth_headers):
        r = client.post("/adventures", json={
            "adventure_id": str(uuid.uuid4()), "name": "Test Campaign", "world_name": "Testonia",
        }, headers=auth_headers)
        assert r.status_code == 201, r.text
        assert r.json()["adventure"]["invite_code"]   # non-empty, server-generated

    def test_update_adventure_dm_mode_roundtrip(self, client, auth_headers):
        created = client.post("/adventures", json={
            "adventure_id": str(uuid.uuid4()), "name": "Test Campaign", "world_name": "Testonia",
        }, headers=auth_headers).json()["adventure"]
        assert created["dm_mode"] is None

        r = client.patch(f"/adventures/{created['id']}", json={"dm_mode": "human"}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["dm_mode"] == "human"

    def test_update_adventure_world_map_id_roundtrip(self, client, auth_headers):
        created = client.post("/adventures", json={
            "adventure_id": str(uuid.uuid4()), "name": "Test Campaign", "world_name": "Testonia",
        }, headers=auth_headers).json()["adventure"]
        assert created["world_map_id"] is None

        r = client.patch(f"/adventures/{created['id']}", json={"world_map_id": "map-1"}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["world_map_id"] == "map-1"


class TestNarratorOpeningScene:
    def test_opening_scene_without_character_name(self, client):
        r = client.post("/narrator/open", json={
            "adventure_id": ADV, "world_name": "Testonia",
        })
        assert r.status_code == 200, r.text
        assert r.json()["narrative"]


class TestTheme:
    def test_expand_theme(self, client):
        r = client.post("/theme/expand", json={"pitch": "a rain-soaked cyberpunk megacity"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["world_name"]
        assert data["currency_name"]
        assert set(data["attribute_names"].keys()) == {
            "strength", "dexterity", "intelligence", "fortitude", "charisma", "reflex",
        }
        assert set(data["biome_family_names"].keys()) == {
            "arid", "grassland", "woodland", "tropical", "wetland",
            "arctic", "ocean", "mountain", "volcanic",
        }
