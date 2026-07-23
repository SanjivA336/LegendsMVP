import type { WorldMap, WorldMapMeta, BiomeGraph } from "../types/world";

const BASE = "http://localhost:8000";

// Mirrors backend/models/world.py::WorldMapGenerateRequest -- the wizard's WorldGenStep
// sends this same body to /world-maps/preview on every "Regenerate" click, then sends
// the exact last-used body to /world-maps at Launch to reproduce the previewed map tile-for-tile.
export interface WorldMapGenerateRequest {
  adventure_id: string;
  seed: number;
  width?: number;
  height?: number;
  num_elevation_seeds?: number;
  percent_ocean?: number;
  percent_mountain?: number;
  volcano_chance?: number;
  num_land_biomes?: number;
  poi_density?: number;
  allowed_land_families?: number[];
  elevation_seed_positions?: [number, number][] | null;
  land_biome_seed_positions?: [number, number][] | null;
}

export async function createWorldMap(payload: WorldMapGenerateRequest): Promise<WorldMap> {
  const res = await fetch(`${BASE}/world-maps`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldMap>;
}

export async function previewWorldMap(payload: WorldMapGenerateRequest): Promise<WorldMap> {
  const res = await fetch(`${BASE}/world-maps/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldMap>;
}

export async function listWorldMaps(adventure_id: string): Promise<WorldMapMeta[]> {
  const res = await fetch(`${BASE}/world-maps?adventure_id=${adventure_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldMapMeta[]>;
}

export async function getWorldMap(map_id: string): Promise<WorldMap> {
  const res = await fetch(`${BASE}/world-maps/${map_id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<WorldMap>;
}

export async function getBiomes(): Promise<BiomeGraph> {
  const res = await fetch(`${BASE}/biomes`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<BiomeGraph>;
}
