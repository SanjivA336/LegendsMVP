import type {
  POI, POIUpdate,
  Dungeon, DungeonRoom, DungeonRoomUpdate,
  Settlement, SettlementUpdate,
  Ruin,
  DiscoverRequest, EnterRequest, ExploreRequest,
  SettlementEnterRequest, RuinEnterRequest,
} from "../types/poi";

const BASE = "http://localhost:8000";

// ── POIs ──────────────────────────────────────────────────────────────────────

export async function seedMapPOIs(payload: { adventure_id: string; map_id: string }): Promise<POI[]> {
  const res = await fetch(`${BASE}/pois/seed-map`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<POI[]>;
}

export async function discoverPOI(payload: DiscoverRequest): Promise<POI> {
  const res = await fetch(`${BASE}/pois/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<POI>;
}

export async function listPOIs(adventure_id: string, map_id?: string): Promise<POI[]> {
  const params = new URLSearchParams({ adventure_id });
  if (map_id) params.set("map_id", map_id);
  const res = await fetch(`${BASE}/pois?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<POI[]>;
}

export async function getPOI(poi_id: string): Promise<POI> {
  const res = await fetch(`${BASE}/pois/${poi_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<POI>;
}

export async function updatePOI(poi_id: string, payload: POIUpdate): Promise<POI> {
  const res = await fetch(`${BASE}/pois/${poi_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<POI>;
}

// ── Dungeons ──────────────────────────────────────────────────────────────────

export async function enterDungeon(payload: EnterRequest): Promise<Dungeon> {
  const res = await fetch(`${BASE}/dungeons/enter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Dungeon>;
}

export async function getDungeonByPOI(poi_id: string): Promise<Dungeon> {
  const res = await fetch(`${BASE}/dungeons/by-poi/${poi_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Dungeon>;
}

export async function getDungeon(dungeon_id: string): Promise<Dungeon> {
  const res = await fetch(`${BASE}/dungeons/${dungeon_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Dungeon>;
}

export async function listRooms(dungeon_id: string, floor?: number): Promise<DungeonRoom[]> {
  const params = new URLSearchParams();
  if (floor !== undefined) params.set("floor", String(floor));
  const query = params.toString() ? `?${params}` : "";
  const res = await fetch(`${BASE}/dungeons/${dungeon_id}/rooms${query}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<DungeonRoom[]>;
}

export async function exploreRoom(dungeon_id: string, payload: ExploreRequest): Promise<DungeonRoom> {
  const res = await fetch(`${BASE}/dungeons/${dungeon_id}/rooms/explore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<DungeonRoom>;
}

export async function updateRoom(room_id: string, payload: DungeonRoomUpdate): Promise<DungeonRoom> {
  const res = await fetch(`${BASE}/dungeons/rooms/${room_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<DungeonRoom>;
}

// ── Settlements ───────────────────────────────────────────────────────────────

export async function enterSettlement(payload: SettlementEnterRequest): Promise<Settlement> {
  const res = await fetch(`${BASE}/settlements/enter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Settlement>;
}

export async function getSettlementByPOI(poi_id: string): Promise<Settlement> {
  const res = await fetch(`${BASE}/settlements/by-poi/${poi_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Settlement>;
}

export async function getSettlement(settlement_id: string): Promise<Settlement> {
  const res = await fetch(`${BASE}/settlements/${settlement_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Settlement>;
}

export async function updateSettlement(settlement_id: string, payload: SettlementUpdate): Promise<Settlement> {
  const res = await fetch(`${BASE}/settlements/${settlement_id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Settlement>;
}

// ── Ruins ─────────────────────────────────────────────────────────────────────

export async function enterRuin(payload: RuinEnterRequest): Promise<Ruin> {
  const res = await fetch(`${BASE}/ruins/enter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Ruin>;
}

export async function getRuinByPOI(poi_id: string): Promise<Ruin> {
  const res = await fetch(`${BASE}/ruins/by-poi/${poi_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Ruin>;
}

export async function getRuin(ruin_id: string): Promise<Ruin> {
  const res = await fetch(`${BASE}/ruins/${ruin_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Ruin>;
}

export async function enterRuinStructure(ruin_id: string, structure_id: string): Promise<Dungeon> {
  const res = await fetch(`${BASE}/ruins/${ruin_id}/structures/${structure_id}/enter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<Dungeon>;
}
