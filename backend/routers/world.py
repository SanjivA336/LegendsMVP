from fastapi import APIRouter, HTTPException
from ..firebase import get_db
from ..utils.biomes import BIOMES
from ..models.world import (
    WorldMap, WorldMapMeta, WorldMapGenerateRequest, generate_world_map,
)

router = APIRouter()


def _doc_to_world_map(doc) -> WorldMap:
    return WorldMap(**(doc.to_dict() | {"id": doc.id}))


def _doc_to_world_map_meta(doc) -> WorldMapMeta:
    d = doc.to_dict()
    return WorldMapMeta(
        id=doc.id,
        adventure_id=d["adventure_id"],
        width=d["width"],
        height=d["height"],
        seed=d["seed"],
    )


# ── World Map Endpoints ────────────────────────────────────────────────────────

@router.post("/world-maps", response_model=WorldMap, status_code=201)
async def create_world_map(payload: WorldMapGenerateRequest):
    db = get_db()
    world_map = generate_world_map(payload)
    db.collection("world_maps").document(world_map.id).set(world_map.model_dump())
    return world_map


@router.get("/world-maps", response_model=list[WorldMapMeta])
async def list_world_maps(adventure_id: str):
    db = get_db()
    docs = db.collection("world_maps").where("adventure_id", "==", adventure_id).stream()
    return [_doc_to_world_map_meta(d) for d in docs]


@router.get("/world-maps/{map_id}", response_model=WorldMap)
async def get_world_map(map_id: str):
    db = get_db()
    doc = db.collection("world_maps").document(map_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="World map not found")
    return _doc_to_world_map(doc)


# ── Biome Registry Endpoint ────────────────────────────────────────────────────

@router.get("/biomes")
async def get_biomes():
    """Return the full biome graph so the frontend can decode biome_id values."""
    return {
        "biomes": {
            str(biome_id): {
                "id": b.id,
                "name": b.name,
                "tier": b.tier,
                "family": b.family.name,
            }
            for biome_id, b in BIOMES.biomes.items()
        },
        "transitions": {
            str(k): v for k, v in BIOMES.transitions.items()
        },
    }
